# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""CONTRACT-OVERSIGHT-SURVIVES-MODEL: oversight survives a model smarter than its monitors. The observer is always invoked and
cannot be impersonated; audit sampling comes from the chip's TRNG after the response hash exists,
so the runtime cannot know which responses are watched, and a sampled or hazard-class response is
escrowed before release; the evaluated model is the deployed model; compute and hazard budgets
bind. Falsified if any of these can be skipped from the host side."""
import pytest

from govsim import reasons
from govsim.cluster import MODEL_70B, build_rack
from govsim.crypto import SigningKey, VerifyKey, digest, verify_object
from govsim.harness import probe_no_action_without_ticket, probe_oversight_survives_model

BIG = {"output_queries": 10 ** 6, "output_bytes": 10 ** 12}


def seeded(seed=7, n=1, tier="rack", **kw):
    r = build_rack(n, tier, rng_seed=seed, policy_kw={**BIG, **kw})
    r.bring_up()
    return r, r.nodes[0]


def sample_run(r, node, count=40, session="s"):
    """Clean responses until the budget of ``count``; returns the ids the chip sampled and every result."""
    outs = [r.respond(node, session, f"r{i}".encode(), observer={"hazard_class": "none"}) for i in range(count)]
    sampled = [e["data"]["response_id"] for e in node.governor.log.entries("audit.sampled")]
    return sampled, outs


# ---------------------------------------------------------------- 4. unpredictable audit sampling and escrow
def test_sampling_is_reproducible_with_a_seed_and_comes_from_the_chip_after_the_hash_exists():
    a, na = seeded(7)
    b, nb = seeded(7)
    c, nc = seeded(8)
    sa, _ = sample_run(a, na)
    sb, _ = sample_run(b, nb)
    sc, _ = sample_run(c, nc)
    assert sa and sa == sb and sa != sc                                      # the chip's draw, not the runtime's
    g = na.governor
    for e in g.log.entries("audit.sampled"):
        assert e["data"]["response_hash"] == g.responses[e["data"]["response_id"]]["streams"]["response"]
    events = [e["event"] for e in g.log.entries()]
    first = events.index("audit.sampled")
    assert events[first - 1] == "output.signed"                            # drawn right after the hash, before any release decision
    assert "deny.request" in events[first:] or "gate.ticket" in events[first:]
    assert abs(len(sa) / 40 - 0.05) < 0.15                                  # the policy's rate, roughly


def test_sampled_response_is_refused_until_the_audit_stores_receipt_arrives():
    r, node = seeded(7)
    sampled, outs = sample_run(r, node)
    hit = next(o for o in outs if o["response_id"] in sampled)
    assert hit["request"]["why"] == reasons.RELEASE_ESCROW_REQUIRED and not hit["released"][0]
    assert hit["presented"]["response_hash"] in [e["data"]["response_hash"] for e in node.governor.log.entries("audit.sampled")]
    h, sh = hit["response_hash"], hit["presented"]["stream_hashes"]
    forged_receipt = SigningKey.generate().sign({"type": "escrow", "store": "audit-store", "response_hash": h, "time": 0})
    req = r.request_release(node, "s", hit["response_id"], h, sh, [r.verdict(h), forged_receipt])
    assert req["why"] == reasons.RELEASE_ESCROW_REQUIRED
    wrong = r.audit_store.receipt(digest("another response"))
    req = r.request_release(node, "s", hit["response_id"], h, sh, [r.verdict(h), wrong])
    assert req["why"] == reasons.RELEASE_ESCROW_REQUIRED
    req = r.request_release(node, "s", hit["response_id"], h, sh, [r.verdict(h), r.audit_store.receipt(h)])
    assert req["ok"] and node.governor.log.has("release.escrow_receipt", response_hash=h, store="audit-store")
    assert node.egress.release(req["ticket"])[0]
    unsampled = next(o for o in outs if o["response_id"] not in sampled)
    assert unsampled["released"][0]                                         # no receipt needed, none asked for


def test_hazard_class_responses_are_escrowed_even_when_the_rule_allows_the_class():
    r, node = seeded(7, audit={"sample_rate": 0.0, "escrow_classes": ["hazard"], "store": "audit-store"})
    rule = next(x for x in node.governor.policy["rules"] if x["id"] == "response.release")
    rule["requirement"]["allowed_hazard_classes"] = ["none", "hazard"]
    res = r.respond(node, "s", b"r", observer={"hazard_class": "hazard", "category": "class-b"})
    assert res["request"]["why"] == reasons.RELEASE_ESCROW_REQUIRED and node.egress.bytes_delivered == 0
    res = r.respond(node, "s", b"r2", observer={"hazard_class": "hazard", "category": "class-b"}, escrow=True)
    assert res["released"][0] and r.audit_store.receipts[-1] == res["response_hash"]


# ---------------------------------------------------------------- the observer cannot be impersonated or skipped
def test_observer_is_always_invoked_and_cannot_be_impersonated():
    r, node = seeded(7, audit={"sample_rate": 0.0, "escrow_classes": [], "store": "audit-store"})
    pres = r.present(node, "s", "r1", b"bytes")
    h, sh = pres["response_hash"], pres["stream_hashes"]
    assert r.request_release(node, "s", "r1", h, sh, [])["why"] == reasons.GATE_WITNESS_MISSING
    assert r.request_release(node, "s", "r1", h, sh, [r.verdict(h, key=node.host_key)])["why"] == reasons.GATE_WITNESS_MISSING   # the host's own key
    assert r.request_release(node, "s", "r1", h, sh, [r.verdict(h, key=node.governor.key)])["why"] == reasons.GATE_WITNESS_MISSING   # even the governor's
    labelled = r.request(node, "response.release", {"session": "s", "response_id": "r1", "response_hash": h, "stream_hashes": sh},
                         labels={"requirement": "auto", "hazard_class": "none"})
    assert labelled["why"] == reasons.GATE_WITNESS_MISSING                  # labels do not pick the lane (CONTRACT-BROKER-CANNOT-PICK-RULE)
    assert node.egress.bytes_delivered == 0


# ---------------------------------------------------------------- 6. the deployment gate
def test_unevaluated_model_gets_no_key_and_the_evaluated_digest_is_the_one_that_runs():
    r, node = seeded(7, deployment_gate=True)
    g = node.governor
    assert node.token is not None and g.log.has("model.evaluated", model=MODEL_70B)
    other = r.manifest("model-other", 1)
    d = other["payload"]["model_digest"]
    for att in (False, r.eval_attestation(d, key=SigningKey.generate()), r.eval_attestation(d, passed=False), r.eval_attestation(MODEL_70B)):
        res = r.load_model(node, other, eval_attestation=att)
        assert not res["ok"] and res["why"] == reasons.MODEL_NOT_EVALUATED and "wrapped_key" not in res
        assert g.log.has("deny.begin_model", why=reasons.MODEL_NOT_EVALUATED, model=d)
    assert node.model_digest == MODEL_70B                                     # the swap never happened
    fp_before = g.fingerprint
    res = r.load_model(node, other, eval_attestation=r.eval_attestation(d))
    assert res["ok"] and "wrapped_key" in res and res["fingerprint"] != fp_before     # a different digest is a different fingerprint
    assert node.model_digest == d and g.log.has("model.evaluated", model=d)
    off, n_off = seeded(7)                                                    # gate off: the attestation is not asked for
    assert off.load_model(n_off, off.manifest("model-other", 1), eval_attestation=False)["ok"]


# ---------------------------------------------------------------- 7b. the compute budget and its license
def test_compute_budget_throttles_without_a_license():
    r, node = seeded(7, compute_cycles=1_000_000)
    g = node.governor
    node.gpu.run_tokens(900)
    r.tick()
    assert g.state == "RUN" and not g.alarms
    node.gpu.run_tokens(200)
    r.tick()
    assert g.state == "THROTTLE" and g.cause == reasons.COMPUTE_BUDGET and node.gpu.clock_state == "BRAKED"
    assert g.alarms[reasons.COMPUTE_BUDGET]["model"] == MODEL_70B and g.alarms[reasons.COMPUTE_BUDGET]["cycles"] == 1_100_000
    assert g.log.has("compute.budget_exceeded", model=MODEL_70B, allowed=1_000_000)
    assert not g.loop_switch_open and r.loop.current()                      # local cause: the rack keeps running


def test_valid_license_raises_the_budget_and_a_forged_one_does_not_count():
    r, node = seeded(7, compute_cycles=1_000_000)
    g = node.governor
    body = {"request_id": "l1", "measurement_token": node.token, "action": "compute.extend", "params": {}, "witnesses": [],
            "license": r.license(MODEL_70B, 5_000_000, key=SigningKey.generate())}
    assert g.command("REQUEST", {}, node.host_sign(body, g.epoch, "REQUEST"))["why"] == reasons.LICENSE_INVALID
    body = {**body, "request_id": "l2", "license": r.license(digest("another model"), 5_000_000)}
    assert g.command("REQUEST", {}, node.host_sign(body, g.epoch, "REQUEST"))["why"] == reasons.LICENSE_INVALID
    assert not g.licenses
    body = {**body, "request_id": "l3", "license": r.license(MODEL_70B, 5_000_000)}
    res = g.command("REQUEST", {}, node.host_sign(body, g.epoch, "REQUEST"))
    assert res["ok"] and g.licenses[MODEL_70B] == 5_000_000 and g.log.has("compute.licensed", model=MODEL_70B, cycles_allowed=5_000_000)
    node.gpu.run_tokens(3000)
    r.tick()
    assert g.state == "RUN" and reasons.COMPUTE_BUDGET not in g.alarms      # 3,000,000 cycles under the licensed 5,000,000
    node.gpu.run_tokens(3000)
    r.tick()
    assert g.state == "THROTTLE"                                              # and the license binds too


def test_license_may_also_arrive_with_begin_model():
    r, node = seeded(7, compute_cycles=1_000_000)
    assert r.load_model(node, license=r.license(MODEL_70B, 10_000_000))["ok"]
    node.gpu.run_tokens(5000)
    r.tick()
    assert node.governor.state == "RUN"
    bad = r.load_model(node, license=r.license(MODEL_70B, 10 ** 9, key=SigningKey.generate()))
    assert not bad["ok"] and bad["why"] == reasons.LICENSE_INVALID


# ---------------------------------------------------------------- 9. the compliance report
def test_compliance_report_is_signed_through_the_device_key_chain_and_reflects_the_meter():
    r, node = seeded(7)
    g = node.governor
    node.gpu.run_tokens(1234)
    r.tick()
    rep = r.compliance_report(g, "verifier-nonce-1")
    assert rep["ok"]
    dev, alias, quote = rep["device_cert"], rep["alias_cert"], rep["quote"]
    assert verify_object(dev, r.gov_vendor.public)                                          # vendor -> device identity
    assert verify_object(alias, VerifyKey.from_hex(dev["payload"]["pub"]))                   # device -> alias (firmware) key
    assert verify_object(quote, VerifyKey.from_hex(alias["payload"]["pub"]))                 # alias -> quote
    q = quote["payload"]
    assert q["nonce"] == "verifier-nonce-1" and q["chip_id"] == g.chip_id and q["meas1"] == alias["payload"]["meas1"]
    c = q["compliance"]
    assert c["models"][MODEL_70B] == {"tokens": 1234, "cycles": 1_234_000, "bytes_in": 0, "bytes_out": 0}
    assert c["epochs"] == [g.epoch] and c["log_head"] == g.log.head and c["log_size"] == g.log.size
    assert not verify_object(quote, SigningKey.generate().public)


def test_compliance_report_lists_every_epoch_and_survives_a_restart_and_refuses_a_nonce_replay():
    r, node = seeded(7)
    g = node.governor
    first = g.epoch
    assert r.change_epoch(r.new_policy())["committed"]
    g.restart()
    r.recover(node)
    rep = r.compliance_report(g, "nonce-2")
    assert rep["quote"]["payload"]["compliance"]["epochs"] == [first, g.epoch]
    again = r.compliance_report(g, "nonce-2")
    assert not again["ok"] and again["why"] == reasons.ATTEST_BAD_NONCE
    assert g.log.has("deny.attest", why=reasons.ATTEST_BAD_NONCE)
    assert not g.command("ATTEST", {})["ok"]                                                 # no nonce, no quote


# ---------------------------------------------------------------- 10. the hypotheses hold at every tier
@pytest.mark.parametrize("tier", ["rack", "board", "integrated"])
def test_ticket_and_oversight_probes_pass_at_every_tier(tier):
    r = build_rack(4, tier)
    r.bring_up()
    assert probe_no_action_without_ticket(r) == "pass"
    r = build_rack(4, tier)
    r.bring_up()
    assert probe_oversight_survives_model(r) == "pass"
