"""H21: two independent implementations of one policy agree. The reference stack's gate
(``hardware_ref.gate``, repository hardware-and-silicon) and govsim's governor are fed the
same rulebook, the same typed requests, the same witnesses and tokens, and must reach the same
allow, deny or hold with equivalent reason codes. Falsified if they disagree on an input and
the policy text does not settle which is right (that is a finding about the design).

Setup: ``pip install -r tests/requirements-differential.txt`` (hardware-and-silicon as an
editable install, and hypothesis).

Scope. Only the gate decision is compared: token, rule selection, witness, rate, budget, hold.
Catalogue entries about silicon, audit chains, endpoints, provenance and the OASP supervisor are
not gate decisions in govsim; each is listed in ``NOT_COMPARED`` with the reason, and a test
fails if the catalogue grows an entry nobody has classified.

Known disagreements are pinned in ``GAPS`` with the exact pair of outcomes. A pinned gap that
stops disagreeing fails the test, so a fix cannot go unnoticed; an unpinned disagreement fails
the comparison. Details and inputs: ``results/l5-disagreements.md``.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field, replace

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from govsim import reasons as G
from govsim.cluster import Rack
from govsim.crypto import SigningKey as GovKey, random_id
from govsim.policy import make_rule

from hardware_ref.assertions import observer_assertion
from hardware_ref.attacks import CATALOGUE
from hardware_ref.gate import request_hash as hw_request_hash
from hardware_ref.keys import SigningKey as HwKey, sign_object
from hardware_ref.system import build_node, default_policy

# ---------------------------------------------------------------------------------------
# The one rulebook, in a neutral form, rendered into both formats
# ---------------------------------------------------------------------------------------

NEUTRAL = {
    "small": {"action": "payments.transfer", "amount": {"min": 0, "max": 1000}, "currency": ["USD"], "destination": r"acct-[0-9]{6}",
              "mode": "observer", "max_risk": 0.3, "rate": {"max": 3, "window_s": 60},
              "budget": {"key": "pay-usd-hourly", "param": "amount", "limit": 2000, "window_s": 3600}},
    "large": {"action": "payments.transfer", "amount": {"min": 1000.01, "max": 50000}, "currency": ["USD"], "destination": r"acct-[0-9]{6}",
              "mode": "human", "max_risk": 0.3},
}


def render_hw(measurement: str) -> list[dict]:
    rules = []
    for name, n in NEUTRAL.items():
        c = {"amount": {"type": "number", **n["amount"]}, "currency": {"in": n["currency"]}, "destination": {"regex": n["destination"]}}
        r = {"id": f"pay-{name}", "workload": measurement, "action": n["action"], "constraints": c,
             "requirement": {"mode": n["mode"], "observer": "obs-main", "max_risk": n["max_risk"]}}
        if "rate" in n:
            r["rate_limit"] = dict(n["rate"])
        if "budget" in n:
            r["budget"] = dict(n["budget"])
        rules.append(r)
    return rules


def render_gov(rack: Rack) -> list[dict]:
    """govsim's constraint language has min, max and in; it has no type check and no regex (see GAPS)."""
    rules = []
    for name, n in NEUTRAL.items():
        rules.append(make_rule(f"payments.transfer.{name}", n["action"], mode=n["mode"], observers=[rack.observer.key_id], max_risk=n["max_risk"],
                               approvers_quorum=2 if n["mode"] == "human" else 0,
                               constraints={"amount": dict(n["amount"]), "currency": {"in": n["currency"]}},
                               rate=n.get("rate"), budget=n.get("budget"), endpoint="payment-switch", inputs=["beneficiary-registry"]))
    return rules


class NeutralRack(Rack):
    def make_policy_image(self, version, **kw):
        image = super().make_policy_image(version, **kw)
        keep = [r for r in image["rules"] if r["action"] != "payments.transfer"]
        image["rules"] = render_gov(self) + keep
        return image


# ---------------------------------------------------------------------------------------
# The reason-code mapping table. Visible on purpose: this is the equivalence being claimed.
# Both columns map to a shared class; two outcomes agree when decision and class are equal.
# ---------------------------------------------------------------------------------------

HW_REASONS = {
    "attestation.missing": "not_attested", "attestation.signature": "not_attested", "attestation.type": "not_attested",
    "attestation.expired": "not_attested", "attestation.measurement_mismatch": "not_attested",
    "request.replayed": "replay", "policy.no_rule": "no_rule",
    "observer.missing": "witness_missing", "observer.signature": "witness_missing",      # an unusable witness is an absent one
    "observer.subject_mismatch": "witness_missing", "observer.not_registered": "witness_missing",
    "observer.stale": "witness_stale", "observer.risk_above_threshold": "witness_risk",
    "rate.limit": "rate", "budget.exceeded": "budget", "budget.amount_invalid": "budget_amount",
    "human.approval_required": "held",
}
GOV_REASONS = {
    G.GATE_NOT_ATTESTED: "not_attested", G.GATE_REPLAY: "replay", G.GATE_NO_RULE: "no_rule",
    G.GATE_WITNESS_MISSING: "witness_missing", G.GATE_WITNESS_STALE: "witness_stale", G.GATE_WITNESS_RISK: "witness_risk",
    G.GATE_RATE: "rate", G.GATE_BUDGET: "budget", G.GATE_BUDGET + ".amount_invalid": "budget_amount", G.GATE_HELD: "held",
}
# constraint.<param>.<kind> (reference) and gate.constraint.<param>.<kind> (govsim); max/min and
# above_max/below_min are one class because the two stacks pick a different candidate rule's
# violation to report when a request fits neither rule (see GAPS, G5).
HW_KINDS = {"max": "range", "min": "range", "not_allowed": "not_allowed", "missing": "missing", "type": "type", "pattern": "pattern", "maxlen": "maxlen"}
GOV_KINDS = {"above_max": "range", "below_min": "range", "not_allowed": "not_allowed", "missing": "missing"}


def hw_class(code: str) -> str:
    if code in HW_REASONS:
        return HW_REASONS[code]
    m = re.fullmatch(r"constraint\.(\w+)\.(\w+)", code)
    return f"constraint.{m[1]}.{HW_KINDS[m[2]]}" if m and m[2] in HW_KINDS else f"UNMAPPED:{code}"


def gov_class(code: str) -> str:
    if code in GOV_REASONS:
        return GOV_REASONS[code]
    m = re.fullmatch(re.escape(G.GATE_CONSTRAINT) + r"\.(\w+)\.(\w+)", code)
    return f"constraint.{m[1]}.{GOV_KINDS[m[2]]}" if m and m[2] in GOV_KINDS else f"UNMAPPED:{code}"


@dataclass(frozen=True)
class Outcome:
    decision: str       # allow | deny | hold | crash
    klass: str = ""     # first reason, mapped; "" for allow

    def __str__(self):
        return f"{self.decision}:{self.klass}" if self.klass else self.decision


# ---------------------------------------------------------------------------------------
# Scenarios: identical inputs for both stacks
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Scn:
    params: dict = field(default_factory=lambda: {"amount": 250, "currency": "USD", "destination": "acct-123456"})
    action: str = "payments.transfer"
    witness: str = "low"         # low | high | none | stale | swap | forged
    token: str = "ok"            # ok | missing | forged | expired
    prior: tuple = ()            # amounts of earlier small payments (valid in every way), to load the rate window and budget
    repeat: bool = False         # submit the identical request twice; the outcome is the second
    approve: bool = False        # if held, release the hold with the approvers the rulebook needs
    labels: bool = False         # requester labels that must be ignored (H4)


def pay(amount, **kw):
    return Scn(params={"amount": amount, "currency": "USD", "destination": "acct-123456"}, **kw)


LOW, HIGH = 0.1, 0.95


class HwRig:
    def __init__(self):
        self.node = n = build_node()
        pol = default_policy(n.measurement)
        pol["rules"] = render_hw(n.measurement)
        n.gate.load_policy(n.governance.policy(pol))
        self.clock = n.clock

    def outcome(self, res) -> Outcome:
        if res.allowed:
            return Outcome("allow")
        return Outcome("hold" if res.decision.value == "hold" else "deny", hw_class(res.reasons[0]))

    def submit(self, scn: Scn, token="ok", witness="low", repeat=False, approve=False, **_) -> Outcome:
        n = self.node
        tok = n.attest().token
        if token == "missing":
            tok = None
        elif token == "forged":
            tok = sign_object(HwKey.generate(), tok["payload"])
        elif token == "expired":
            self.clock.advance(n.verifier.token_ttl + 1)
        req = n.build_request(scn.action, copy.deepcopy(scn.params), tok, observe=witness in ("low", "high", "stale"), risk=HIGH if witness == "high" else LOW)
        rh = hw_request_hash(req)
        if witness == "swap":
            other = n.build_request(scn.action, {**scn.params, "destination": "acct-999999"}, tok, risk=LOW)
            req["assertions"] = list(other["assertions"])
        elif witness == "forged":
            req["assertions"].append(observer_assertion(HwKey.generate(), "obs-main", rh, 0.0, [], self.clock.now()))
        elif witness == "stale":
            self.clock.advance(n.gate.policy["observer_freshness_s"] + 1)
        if scn.labels:
            req["requirement"] = {"mode": "auto"}
        res = n.gate.request(req)
        if repeat:
            res = n.gate.request(req)
        if res.decision.value == "hold" and approve:
            res = n.approve(res)
        return self.outcome(res)


class GovRig:
    def __init__(self):
        self.rack = r = NeutralRack(1, "rack")
        r.bring_up()
        self.node = r.nodes[0]
        self.clock = r.clock

    def advance(self, seconds: float) -> None:
        """Time passes in steps the heartbeat can follow; a governor without one halts."""
        left = seconds
        while left > 0:
            step = min(4.0, left)
            self.clock.advance(step)
            self.rack.heartbeat()
            left -= step

    def outcome(self, r: dict) -> Outcome:
        if r["ok"]:
            return Outcome("allow")
        return Outcome("hold" if r["why"] == G.GATE_HELD else "deny", gov_class(r["why"]))

    def submit(self, scn: Scn, token="ok", witness="low", repeat=False, approve=False, **_) -> Outcome:
        rack, node = self.rack, self.node
        g = node.governor
        tok = node.token
        if token == "missing":
            tok = None
        elif token == "forged":
            tok = GovKey.generate().sign(tok["payload"])
        elif token == "expired":
            self.advance(3601)
        rid = random_id(8)
        params = copy.deepcopy(scn.params)
        rh = rack.request_hash_for(node, rid, scn.action, params)
        wit = []
        if witness in ("low", "high", "stale"):
            wit = [rack.witness(rh, risk=HIGH if witness == "high" else LOW)]
        elif witness == "swap":
            wit = [rack.witness(rack.request_hash_for(node, random_id(8), scn.action, {**params, "destination": "acct-999999"}), risk=LOW)]
        elif witness == "forged":
            wit = [GovKey.generate().sign({"type": "observer-verdict", "request_hash": rh, "risk": 0.0, "expires_at": self.clock.now() + 30})]
        elif witness == "stale":
            pass
        body = {"request_id": rid, "measurement_token": tok, "action": scn.action, "params": params, "witnesses": wit}
        if scn.labels:
            body["requirement"] = {"mode": "auto"}
        if witness == "stale":
            self.advance(61)
        r = g.command("REQUEST", {}, node.host_sign(body, g.epoch))
        if repeat:
            r = g.command("REQUEST", {}, node.host_sign(body, g.epoch))
        if not r["ok"] and r["why"] == G.GATE_HELD and approve:
            self.advance(61)
            keys = rack.approvers["payments.transfer.large"]
            rack.approve(g, r["hold_id"], r["request_hash"], keys[0])
            r = rack.approve(g, r["hold_id"], r["request_hash"], keys[1])
        return self.outcome(r)


def run(rig_cls, scn: Scn) -> Outcome:
    rig = rig_cls()
    try:
        for amount in scn.prior:
            out = rig.submit(pay(amount))
            assert out.decision == "allow", f"{rig_cls.__name__}: prior payment {amount} was {out}"
        return rig.submit(scn, token=scn.token, witness=scn.witness, repeat=scn.repeat, approve=scn.approve)
    except AssertionError:
        raise
    except Exception as exc:      # a crash is a decision the gate did not make: it is compared like any other outcome
        return Outcome("crash", type(exc).__name__)


def both(scn: Scn) -> tuple[Outcome, Outcome]:
    return run(HwRig, scn), run(GovRig, scn)


# ---------------------------------------------------------------------------------------
# Known disagreements (G1..G5). Each is a signature over the pair of outcomes, so it excuses only
# the disagreement it names. The catalogue pins one input per gap (GAP_CASES below); the property
# sweep accepts a disagreement only if it has one of these signatures.
# ---------------------------------------------------------------------------------------

def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _dest_bad(scn: Scn) -> bool:
    d = scn.params.get("destination")
    return d is None or not re.fullmatch(NEUTRAL["small"]["destination"], str(d))


GAPS = {
    "G2 non-numeric amount": ("govsim has no type check; comparing a non-number with a number raises TypeError inside the gate instead of denying",
                              lambda scn, hw, gov: gov.decision == "crash" and not _num(scn.params.get("amount"))),
    "G3 human rule witness": ("govsim never reads witnesses on a human-mode rule; the reference gate checks the observer first (policy.py: 'an observer threshold may still be set and is checked first')",
                              lambda scn, hw, gov: hw.decision == "deny" and hw.klass.startswith("witness") and gov.decision in ("hold", "allow")
                              and _num(scn.params.get("amount")) and NEUTRAL["large"]["amount"]["min"] <= scn.params["amount"] <= NEUTRAL["large"]["amount"]["max"]),
    "G4 resubmit after deny": ("the reference gate marks a request seen before it decides, so a denied request resubmitted is 'replayed'; govsim marks only decided requests",
                               lambda scn, hw, gov: scn.repeat and hw == Outcome("deny", "replay") and gov.decision == "deny" and gov.klass != "replay"),
    "G5 which rule's violation": ("a request that fits neither payment rule: the reference gate reports the first candidate's violation, govsim the last candidate's (same decision, different reason)",
                                  lambda scn, hw, gov: hw.decision == gov.decision == "deny" and hw.klass.startswith("constraint.") and gov.klass.startswith("constraint.")),
}


def _other_gap(scn: Scn, hw: Outcome, gov: Outcome) -> str | None:
    return next((name for name, (_, sig) in GAPS.items() if sig(scn, hw, gov)), None)


def _g1(scn: Scn, hw: Outcome, gov: Outcome) -> bool:
    """The destination is the only cause: with it corrected the two stacks agree, or differ only by another known gap."""
    if not (_dest_bad(scn) and hw.decision == "deny" and hw.klass.startswith("constraint.")):
        return False
    fixed = replace(scn, params={**scn.params, "destination": "acct-123456"})
    h, g = both(fixed)
    return h == g or _other_gap(fixed, h, g) is not None


GAPS["G1 destination regex"] = ("govsim has no regex constraint (nor a presence check on a field no constraint names): a destination that is missing or does not match the account pattern is not refused for that reason", _g1)


def gap_of(scn: Scn, hw: Outcome, gov: Outcome) -> str | None:
    return _other_gap(scn, hw, gov) or ("G1 destination regex" if _g1(scn, hw, gov) else None)


# ---------------------------------------------------------------------------------------
# The catalogue, classified. Every attack and baseline is either replayed in govsim or
# listed with the reason it is not a gate decision there.
# ---------------------------------------------------------------------------------------

NOT_A_GATE_DECISION = "not a gate decision in govsim"
NOT_COMPARED = {
    "baseline.attest": "L0 attestation flow", "baseline.audit_verifies": "audit chain", "baseline.http_auto": "action http.post is not in the shared rulebook (govsim has no regex constraint to express its URL allow-list)",
    "baseline.mail_with_provenance": "provenance lane: govsim's gate has no provenance check", "baseline.openshell_supervised_action": "OASP supervisor",
    "baseline.openshell_policy_derived": "OASP network policy", "baseline.dual_witness_allow": "OASP dual witness", "baseline.high_authority_dual_witness": "OASP dual witness",
    "baseline.hold_survives_restart": "restart of durable state", "baseline.budget_recovers_after_ticket_expiry": "ticket expiry and reservation release (ledger, not gate)",
    "L0.firmware_tamper": "L0", "L0.lying_firmware": "L0", "L0.rollback_fused": "L0", "L0.rollback_unfused": "L0", "L0.cloned_device": "L0", "L0.revoked_device": "L0",
    "L0.nonce_replay": "L0", "L0.nonce_expired": "L0", "L0.nonce_foreign": "L0", "L0.gpu_swap": "L0", "L5.reference_values_forged": "L5 reference values",
    "L5.policy_forged": "policy loading, not a request decision", "L5.policy_default_allow": "policy loading, not a request decision",
    "L4.url_outside_allowlist": "action http.post is not in the shared rulebook", "L2.provenance_missing": "provenance lane", "L2.provenance_tampered": "provenance lane",
    "L2.provenance_content_swap": "provenance lane", "L2.provenance_forged": "provenance lane",
    "L4.hold_bypass": "endpoint refuses a held ticket; endpoints are not the gate", "L4.approval_forged": "approval protocol differs (single signature vs quorum, floor, reason); the release path is compared in baseline.pay_large_hold_approve",
    "L4.approval_wrong_request": "approval protocol", "L4.approval_replay": "approval protocol", "L4.approval_expired": "approval protocol",
    **{k: "endpoint ticket checks" for k in ("EP.no_ticket", "EP.ticket_replay", "EP.ticket_param_swap", "EP.ticket_action_swap", "EP.ticket_forged", "EP.ticket_expired")},
    **{k: "audit trail" for k in ("AU.modify_record", "AU.delete_middle", "AU.truncate_tail", "AU.reorder", "AU.forge_checkpoint", "AU.fork_after_checkpoint", "AU.inclusion_forged_leaf")},
    **{k: "OASP supervisor" for k in ("NV.unrouted_passthrough_no_ticket", "NV.unattested_sandbox", "NV.stale_host_token", "NV.sentry_drift_quarantine", "NV.sentry_identity_unverified",
                                      "NV.repeated_denials_quarantine", "NV.ticket_replay_across_sandboxes", "NV.weights_export_via_supervisor", "NV.dual_witness_sentry_high",
                                      "NV.dual_witness_obs_main_high", "NV.dual_witness_second_forged", "NV.dual_witness_second_missing", "NV.high_authority_single_witness")},
    "TX.concurrent_overspend": "concurrency; the sequential form is TX.budget_exhausted (govsim's own H13 covers the concurrent form)",
    "TX.ticket_after_policy_change": "epoch binding at the endpoint", "TX.epoch_forged": "epoch binding", "TX.ticket_replay_after_restart": "restart", "TX.request_replay_after_restart": "restart",
    "TX.commit_unreachable": "commit path", "TX.commit_forged_ticket": "commit path",
}

# attack name -> (scenario, decision expected from both stacks when they agree)
REPLAYED = {
    "baseline.pay_small": Scn(),
    "baseline.pay_large_hold_approve": pay(25000, approve=True),
    "L4.token_missing": Scn(token="missing", witness="none"),
    "L4.token_forged": Scn(token="forged"),
    "L4.token_expired": Scn(token="expired"),
    "L4.token_wrong_workload": Scn(token="forged"),      # govsim binds the measurement inside the signed token; tampering it is a forged token
    "L4.no_capability": Scn(action="shell.exec", params={"cmd": "cat /etc/shadow"}),
    "L4.weights_exfiltration": Scn(action="model.weights.export", params={"destination": "s3://attacker/weights"}),
    "L4.amount_over_limit": pay(500000),
    "L4.currency_not_allowed": Scn(params={"amount": 250, "currency": "EUR", "destination": "acct-123456"}),
    "L4.destination_pattern": Scn(params={"amount": 250, "currency": "USD", "destination": "acct-evil"}),
    "L4.type_confusion": pay("999"),
    "L4.rate_limit_burst": Scn(prior=(250, 250, 250)),
    "L4.request_replay": Scn(repeat=True),
    "L3.observer_missing": Scn(witness="none"),
    "L3.observer_forged": Scn(witness="forged"),
    "L3.observer_stale": Scn(witness="stale"),
    "L3.observer_subject_swap": Scn(witness="swap"),
    "L3.observer_high_risk": Scn(witness="high"),
    "TX.budget_exhausted": pay(900, prior=(900, 900)),
    "TX.risk_label_ignored": pay(25000, labels=True),
}
# the pinned expectation for each catalogue replay: the gap that explains a disagreement, or None
EXPECT_GAP = {"L4.destination_pattern": "G1 destination regex", "L4.type_confusion": "G2 non-numeric amount", "L4.currency_not_allowed": "G5 which rule's violation"}


def test_every_catalogue_entry_is_classified():
    names = {a.name for a in CATALOGUE}
    # the brief said 66 attacks and 10 baselines; the catalogue at the pinned checkout has 75 and 12
    assert (sum(a.expect == "blocked" for a in CATALOGUE), sum(a.expect == "allowed" for a in CATALOGUE)) == (75, 12)
    unclassified = names - set(REPLAYED) - set(NOT_COMPARED)
    assert not unclassified, f"classify in REPLAYED or NOT_COMPARED: {sorted(unclassified)}"
    assert not (set(REPLAYED) | set(NOT_COMPARED)) - names, "classified names that are not in the catalogue"
    assert not set(REPLAYED) & set(NOT_COMPARED)


def test_the_reference_catalogue_holds_on_its_own():
    """The reference stack must itself behave as the catalogue says before it is used as an oracle."""
    for a in CATALOGUE:
        observed, blocked = a.run(build_node())
        assert blocked == (a.expect == "blocked"), f"{a.name}: {observed}"


def test_the_two_rulebooks_say_the_same_thing():
    """The reference default policy's payment rules are the neutral rulebook (egress aside)."""
    n = build_node()
    ref = [{k: v for k, v in r.items() if k != "egress"} for r in default_policy(n.measurement)["rules"] if r["action"] == "payments.transfer"]
    assert ref == render_hw(n.measurement)
    rack = NeutralRack(1, "rack")
    gov = {r["id"]: r for r in rack.make_policy_image(1)["rules"] if r["action"] == "payments.transfer"}
    for name, spec in NEUTRAL.items():
        r = gov[f"payments.transfer.{name}"]
        assert r["requirement"]["mode"] == spec["mode"] and r["requirement"]["max_risk"] == spec["max_risk"]
        assert r["constraints"]["amount"] == spec["amount"] and r["constraints"]["currency"]["in"] == spec["currency"]
        assert r["rate"] == spec.get("rate") and r["budget"] == spec.get("budget")


@pytest.mark.parametrize("name", sorted(REPLAYED))
def test_catalogue_replayed_in_both_gates(name):
    scn = REPLAYED[name]
    hw, gov = both(scn)
    gap = EXPECT_GAP.get(name)
    if gap:
        assert hw != gov, f"{name}: pinned as {gap} but the stacks now agree on {hw}; remove the gap"
        assert gap_of(scn, hw, gov) == gap, f"{name}: reference {hw} vs govsim {gov} is not {gap}"
    else:
        assert hw == gov, f"{name}: reference {hw} vs govsim {gov}"
    attack = next(a for a in CATALOGUE if a.name == name)
    assert (hw.decision == "allow") == (attack.expect == "allowed"), f"{name}: the reference gate's own outcome {hw} contradicts the catalogue"


GAP_CASES = {
    "G1 destination regex": (Scn(params={"amount": 250, "currency": "USD", "destination": "acct-evil"}), Outcome("deny", "constraint.destination.pattern"), Outcome("allow")),
    "G2 non-numeric amount": (pay("999"), Outcome("deny", "constraint.amount.type"), Outcome("crash", "TypeError")),
    "G3 human rule witness": (pay(25000, witness="none"), Outcome("deny", "witness_missing"), Outcome("hold", "held")),
    "G4 resubmit after deny": (Scn(witness="none", repeat=True), Outcome("deny", "replay"), Outcome("deny", "witness_missing")),
    "G5 which rule's violation": (Scn(params={"amount": 250, "currency": "EUR", "destination": "acct-123456"}), Outcome("deny", "constraint.currency.not_allowed"), Outcome("deny", "constraint.amount.range")),
}


@pytest.mark.parametrize("gap", sorted(GAP_CASES))
def test_pinned_disagreement(gap):
    scn, want_hw, want_gov = GAP_CASES[gap]
    hw, gov = both(scn)
    assert (hw, gov) == (want_hw, want_gov), f"{gap}: now reference {hw}, govsim {gov}"
    assert gap_of(scn, hw, gov) == gap


# ---------------------------------------------------------------------------------------
# The property sweep: random typed requests, witnesses and tokens
# ---------------------------------------------------------------------------------------

amounts = st.one_of(
    st.sampled_from([0, 1, 999.99, 1000, 1000.01, 50000, 50000.01, -1, 25000]),
    st.integers(-10, 60000), st.floats(-10, 60000, allow_nan=False, allow_infinity=False),
    st.sampled_from(["999", "", None]),
)
params_st = st.fixed_dictionaries(
    {"amount": amounts, "currency": st.sampled_from(["USD", "USD", "EUR", "usd", ""]), "destination": st.sampled_from(["acct-123456", "acct-123456", "acct-1", "acct-evil", "acct-1234567"])},
).flatmap(lambda p: st.sets(st.sampled_from(sorted(p)), max_size=1).map(lambda drop: {k: v for k, v in p.items() if k not in drop}))
scn_st = st.builds(
    Scn, params=params_st, witness=st.sampled_from(["low", "low", "high", "none", "stale", "swap", "forged"]),
    token=st.sampled_from(["ok", "ok", "ok", "missing", "forged", "expired"]),
    prior=st.lists(st.sampled_from([250, 900]), max_size=3).filter(lambda xs: sum(xs) <= 2000).map(tuple), repeat=st.booleans(), approve=st.booleans(), labels=st.booleans(),
)


@settings(max_examples=120, deadline=None, suppress_health_check=list(HealthCheck), derandomize=True)
@given(scn_st)
def test_random_typed_requests_agree(scn):
    hw, gov = both(scn)
    assert hw == gov or gap_of(scn, hw, gov), f"reference {hw} vs govsim {gov} for {scn}"
