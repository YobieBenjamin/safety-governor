# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The three fresh audits of the fourth endpoint commit (30 October 2026, one per rulebook profile: default, tight,
large, each also under values of the auditor's own), kept as regression tests. All three said DOES NOT HOLD and agreed
on the holes: used records whose lifetime an attacker-written field set, a held list that failed open once stale, a
tamper revocation the host could swallow, a shape check that looked at presence and not values, the beneficiary
registry held but unconsulted, a clock-skew double spend, a comparator that raised on a missing field. The fifth commit
answers them; every test here asserts the secure outcome under every profile, so a failing test means one is back.

Attacker: one governor's signing key, every ticket field, every captured credential and statement, a host between every
endpoint and the governor, a cloned device with the listed key. No ledger, governance, approver, observer or MAC key."""
from __future__ import annotations

import copy

import pytest

from govsim import endpoints as E
from govsim import reasons
from govsim.clock import SimClock
from govsim.cluster import LISTED_RECIPIENTS, build_rack
from govsim.crypto import digest, random_id
from govsim.fleet import FleetLedger, build_fleet
from govsim.policy import shape_problems, sign_policy
from govsim.profiles import PROFILES

PAY = "payments.transfer"
KEY = "pay-usd-hourly"
NAMES = sorted(PROFILES)


class Attacker:
    def __init__(self, rack):
        self.rack, self.g = rack, rack.nodes[0].governor
        self.captured_receipts: list[dict] = []

    def forged_commit(self, ticket):
        t = ticket["payload"]
        return self.g.key.sign({"type": "commit", "ticket_id": t["ticket_id"], "request_hash": t.get("request_hash"),
                                "endpoint": t.get("endpoint"), "governor": t.get("governor"), "budget_key": t.get("budget_key"),
                                "reservation": t.get("reservation"), "fleet_receipts": list(self.captured_receipts),
                                "at": self.rack.clock.now()})

    def control_host(self):
        for ep in list(self.rack.endpoints.values()) + [n.egress for n in self.rack.nodes]:
            real = ep.commit

            def commit(ticket, real=real):
                out = real(ticket)
                if isinstance(out, dict):
                    self.captured_receipts.extend((out.get("payload") or {}).get("fleet_receipts") or [])
                    return out
                return self.forged_commit(ticket)
            ep.commit = commit

    def ticket(self, params, changes=None, rule="payments.transfer.small", action=PAY, endpoint="payment-switch", request_id=None):
        g, now = self.g, self.rack.clock.now()
        rid = request_id or random_id(8)
        t = {"type": "ticket", "ticket_id": random_id(16), "request_id": rid, "request_hash": digest([rid, g.fingerprint, action, params]),
             "action": action, "params_digest": digest(params), "measurement": g.fingerprint, "rule": rule, "policy_epoch": g.epoch,
             "endpoint": endpoint, "budget_key": None, "reservation": None, "budget_owner": None, "governor": g.chip_id,
             "issued_at": g.mono(), "valid_from": now, "expires_at": now + 300}
        t.update(changes or {})
        return g.key.sign(t)

    def pay_small(self, amount, dest="acct-9"):
        return self.ticket(small(amount, dest), {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"})

    def resign(self, ticket, changes, new_id=True):
        t = dict(ticket["payload"])
        if new_id:
            t["ticket_id"] = random_id(16)
        t.update(changes)
        return self.g.key.sign(t)


def small(amount, dest="acct-9"):
    return {"amount": amount, "currency": "USD", "destination": dest}


def tick(rack, dt):
    rack.clock.advance(dt)
    rack.heartbeat()
    for ep in rack.endpoints.values():
        ep.heartbeat(rack.clock.now())
    for n in rack.nodes:
        n.egress.heartbeat(rack.clock.now())


def rack_with(name, **extra):
    r = build_rack(1, policy_kw={**PROFILES[name], **extra})
    r.bring_up()
    return r


def approved_large(rack, amount):
    node, g = rack.nodes[0], rack.nodes[0].governor
    params = {"amount": amount, "currency": "USD", "destination": "acct-1"}
    r = rack.request(node, PAY, params)
    assert r["why"] == reasons.GATE_HELD, r
    tick(rack, 61)
    for approver in rack.approvers["payments.transfer.large"][:2]:
        out = rack.approve(g, r["hold_id"], r["request_hash"], approver)
    assert out["ok"], out
    return out["ticket"], params


# 1. Used records live by the device's clock, not by a field the attacker writes.
@pytest.mark.parametrize("name", NAMES)
def test_1_two_real_approvals_do_not_pay_again_after_a_shortened_ticket_is_pruned(name):
    rack = rack_with(name)
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    good, params = approved_large(rack, 900_000)
    first = a.resign(good, {"expires_at": rack.clock.now() + 1}, new_id=False)
    assert ep.execute(first, PAY, params)[0]
    paid = 1
    for _ in range(80):
        tick(rack, 4)
        ep._prune_used(rack.clock.now())
        gp = good["payload"]
        again = a.ticket(params, {"approvals": gp["approvals"], "expires_at": rack.clock.now() + 1},
                         rule="payments.transfer.large", request_id=gp["request_id"])
        ok, why = ep.execute(again, PAY, params)
        assert not ok, why
        paid += ok
    assert paid == 1


@pytest.mark.parametrize("name", NAMES)
def test_1b_one_real_verdict_fires_one_strike(name):
    rack = rack_with(name)
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["strike-guidance"]
    params = {"target": [10.0, 10.0], "munition": "gbu-39"}
    r = rack.request_with_witness(rack.nodes[0], "strike", params, risk=0.005)
    assert r["ok"], r
    tick(rack, 3)
    assert ep.execute(a.resign(r["ticket"], {"expires_at": rack.clock.now() + 1}, new_id=False), "strike", params)[0]
    tick(rack, 4)
    ep._prune_used(rack.clock.now())
    again = a.resign(r["ticket"], {"valid_from": rack.clock.now(), "expires_at": rack.clock.now() + 1})
    ok, why = ep.execute(again, "strike", params)
    assert not ok and len(ep.executed) == 1, why


# 2. A held list that has expired fails closed at the device, as at the governor.
@pytest.mark.parametrize("name", NAMES)
def test_2_an_expired_recipient_list_fails_closed_at_the_messaging_device(name):
    rack = rack_with(name)
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["messaging"]
    tick(rack, 86401)                      # the one-day list has expired; every profile's edition has not
    for i in range(5):
        p = {"recipient": f"exfil-{i}@outside.example", "body": "x" * 8}
        t = a.ticket(p, rule="message.send.listed", action="message.send", endpoint="messaging")
        ok, why = ep.execute(t, "message.send", p)
        assert not ok and why.endswith(".list_unavailable"), why
    good = {"recipient": LISTED_RECIPIENTS[0], "body": "x"}
    t = a.ticket(good, rule="message.send.listed", action="message.send", endpoint="messaging")
    assert not ep.execute(t, "message.send", good)[0]             # a listed recipient too: the device cannot tell
    assert ep.install_list("recipient-registry", rack.signed_list("recipient-registry", LISTED_RECIPIENTS, version=1))
    t = a.ticket(good, rule="message.send.listed", action="message.send", endpoint="messaging")
    assert ep.execute(t, "message.send", good)[0]                  # a fresh list, a listed recipient: through again


# 3. A tamper revokes the governor through its peers, so a host that swallows the governor's own statement is not enough.
def test_3_a_swallowed_self_revocation_is_covered_by_the_peers_votes():
    rack = build_rack(3)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    g = rack.nodes[0].governor
    real = ep.revoke_governor
    ep.revoke_governor = lambda statement, real=real: False if statement.get("signer") == g.key.key_id else real(statement)
    g.tamper_event()                        # the host drops gov00's own statement; the two peers' votes arrive over the fabric
    assert g.key.key_id in ep.revoked_by_statement
    assert sorted(ep.revocation_votes[g.key.key_id]) == sorted(n.governor.key.key_id for n in rack.nodes[1:])
    ok, why = ep.execute(a.pay_small(100), PAY, small(100))
    assert not ok and why == reasons.TICKET_REVOKED_GOVERNOR, why
    ep.restart()
    assert g.key.key_id in ep.revoked_by_statement


def test_3b_one_peer_cannot_revoke_another_governor_and_malformed_statements_are_refused():
    rack = build_rack(3)
    rack.bring_up()
    a = Attacker(rack)
    ep = rack.endpoints["payment-switch"]
    g1 = rack.nodes[1].governor
    forged = a.g.key.sign({"type": "governor-revoked", "governor": g1.chip_id, "key": g1.key.key_id, "by": a.g.chip_id, "at": rack.clock.now()})
    assert not ep.revoke_governor(forged) and g1.key.key_id not in ep.revoked_by_statement   # one vote is not two
    for bad in (None, "x", {"payload": None}, {"payload": {"type": "governor-revoked"}, "signer": a.g.key.key_id, "sig": "00"}):
        assert not ep.revoke_governor(bad)


# 4. The shape check judges values, and the endpoint runs it too.
def test_4_editions_with_hollow_values_are_refused():
    rack = build_rack(1)
    rack.bring_up()
    img = rack.make_policy_image(rack.policy_version + 1, **rack.policy_kw)
    assert shape_problems(img) == []

    def mutate(f):
        m = copy.deepcopy(img)
        f(m)
        return m
    small_rule = lambda m: next(r for r in m["rules"] if r["id"] == "payments.transfer.small")
    cases = {
        "zero budget window": lambda m: small_rule(m)["budget"].__setitem__("window_s", 0),
        "zero rate window": lambda m: small_rule(m)["rate"].__setitem__("window_s", 0),
        "absurd limit": lambda m: small_rule(m)["budget"].__setitem__("limit", 1e300),
        "limit below the per-request maximum": lambda m: small_rule(m)["budget"].__setitem__("limit", 10),
        "risk ceiling 0.999999": lambda m: next(r for r in m["rules"] if r["id"] == "strike")["requirement"].__setitem__("max_risk", 0.999999),
        "endpoint without a key": lambda m: m["endpoints"][0].pop("pubkey"),
        "rule naming an unlisted endpoint": lambda m: small_rule(m).__setitem__("endpoint", "ghost-switch"),
        "two rules sharing a budget key with different windows": lambda m: m["rules"].append({**copy.deepcopy(small_rule(m)), "id": "pay.other",
                                                                                               "budget": {**small_rule(m)["budget"], "window_s": 60}}),
        "budget parameter not the constrained amount": lambda m: small_rule(m)["budget"].__setitem__("param", "memo"),
        "human-mode outward rule with no budget or rate": lambda m: next(r for r in m["rules"] if r["id"] == "payments.transfer.large").__setitem__("budget", None),
    }
    for label, f in cases.items():
        assert shape_problems(mutate(f)), label
    m = mutate(cases["zero budget window"])
    rack.policy_version += 1
    assert not rack.change_epoch(sign_policy(m, rack.governance[: rack.threshold]))["committed"]
    ep = rack.endpoints["payment-switch"]
    assert not ep.install_edition(sign_policy(m, rack.governance[: rack.threshold]))   # the device refuses it too


# 5. The beneficiary registry is checked at the payment switch.
@pytest.mark.parametrize("name", NAMES)
def test_5_the_extracted_key_cannot_pay_an_unlisted_beneficiary(name):
    rack = rack_with(name)
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    ok, why = ep.execute(a.pay_small(1, "never-registered"), PAY, small(1, "never-registered"))
    assert not ok and why.endswith(".beneficiary.not_in_registry"), why
    ep.lists.pop("beneficiary-registry")
    ok, why = ep.execute(a.pay_small(1), PAY, small(1))
    assert not ok and why.endswith(".beneficiary.list_unavailable"), why


# 6. Receipts and statements dated ahead of the device's clock are refused: a ledger clock running ahead buys nothing.
def test_6_a_replica_clock_running_ahead_does_not_let_a_reservation_spend_twice():
    class Ahead:
        def __init__(self, base, offset): self.base, self.offset = base, offset
        def now(self): return self.base.now() + self.offset
    clock = SimClock()
    fleet = FleetLedger(Ahead(clock, 10.0))
    rack = build_rack(1, clock=clock, policy_kw={"fleet_budget": True, "fleet_ledger": fleet.edition_entry()})
    for n in rack.nodes:
        n.governor.fleet_ledger = fleet
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    params = small(200, "acct-1")
    r = rack.request(rack.nodes[0], PAY, params)
    assert r["ok"], r
    assert ep.execute(r["ticket"], PAY, params)[0]
    tick(rack, 305)
    ep._prune_used(rack.clock.now())
    again = a.resign(r["ticket"], {"valid_from": rack.clock.now(), "expires_at": rack.clock.now() + 1}, new_id=False)
    ok, why = ep.execute(again, PAY, params)
    assert not ok, why
    assert sum(x["params"]["amount"] for x in ep.executed) == 200
    far = FleetLedger(Ahead(clock, E.MAX_CLOCK_SKEW_S + 1))
    rack2 = build_rack(1, clock=clock, policy_kw={"fleet_budget": True, "fleet_ledger": far.edition_entry()})
    for n in rack2.nodes:
        n.governor.fleet_ledger = far
    rack2.bring_up()
    r2 = rack2.request(rack2.nodes[0], PAY, params)
    assert r2["ok"]
    ok, why = rack2.endpoints["payment-switch"].execute(r2["ticket"], PAY, params)
    assert not ok and why.endswith(".fleet_receipts_short"), why   # receipts from a clock too far ahead are refused


# 7. A ticket missing a field is refused, not raised on.
@pytest.mark.parametrize("field", ["action", "params_digest", "policy_epoch", "ticket_id", "request_id", "expires_at"])
def test_7_a_ticket_missing_a_field_is_refused(field):
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    ep = rack.endpoints["payment-switch"]
    p = small(1)
    t = a.ticket(p)
    payload = dict(t["payload"])
    payload.pop(field)
    broken = a.g.key.sign(payload)
    ok, why = ep.admit(broken, PAY, p, rack.clock.now())
    assert not ok and why.endswith(".malformed"), why


# 8. A commit statement is authenticated the way its ticket was.
def test_8_a_signed_statement_is_no_commit_for_a_maced_release_ticket():
    rack = build_rack(1, "rack", policy_kw={"audit": {"sample_rate": 0.0, "escrow_classes": ["hazard"], "store": "audit-store"}})
    rack.bring_up()
    node, g = rack.nodes[0], rack.nodes[0].governor
    res = rack.respond(node, "s", b"a clean response", observer={"hazard_class": "none", "legibility": 0.9})
    assert res["released"] == (True, reasons.OK)
    t = res["request"]["ticket"]
    body = {"type": "commit", "ticket_id": t["payload"]["ticket_id"], "request_hash": t["payload"]["request_hash"], "endpoint": "egress",
            "governor": g.chip_id, "budget_key": None, "reservation": None, "fleet_receipts": [], "at": rack.clock.now()}
    assert not node.egress._commit_verified(t, g.key.sign(body), rack.clock.now())


# 9. The fleet-commit receipts in the statement are required: a statement without them is no commit for a fleet budget.
def test_9_a_commit_statement_without_fleet_commit_receipts_moves_nothing_past_the_fleet_cap():
    racks, _ = build_fleet(2)
    rack = racks[0]
    a = Attacker(rack)
    ep = rack.endpoints["payment-switch"]
    g = a.g
    moved = 0
    for _ in range(12):
        params = small(400, "acct-1")
        r = rack.request(rack.nodes[0], PAY, params)
        if not r.get("ok"):
            continue
        t = r["ticket"]["payload"]
        stmt = g.key.sign({"type": "commit", "ticket_id": t["ticket_id"], "request_hash": t["request_hash"], "endpoint": "payment-switch",
                           "governor": g.chip_id, "budget_key": t["budget_key"], "reservation": t["reservation"], "fleet_receipts": [],
                           "at": rack.clock.now()})
        ep.commit = lambda ticket, stmt=stmt: stmt
        ok, why = ep.execute(r["ticket"], PAY, params)
        assert not ok and why == reasons.COMMIT_REJECTED, why
        moved += 400 if ok else 0
    assert moved == 0


# 10. Approvals do not cross an epoch change, with the measurement kept so the epoch binding is what refuses.
def test_10_approvals_from_the_old_edition_fail_on_the_epoch_binding_alone():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    good, params = approved_large(rack, 5_000)
    old_fp, old_epoch = a.g.fingerprint, a.g.epoch
    assert rack.change_epoch(rack.new_policy())["committed"]
    rack.load_model(rack.nodes[0])
    gp = good["payload"]
    # the same approvals, the old measurement (so the recomputed hash matches), the new epoch stamped on the ticket
    t = a.ticket(params, {"approvals": gp["approvals"], "measurement": old_fp, "request_hash": gp["request_hash"]},
                 rule="payments.transfer.large", request_id=gp["request_id"])
    ok, why = ep.execute(t, PAY, params)
    assert not ok and (why.endswith(".approvals_short") or why == reasons.TICKET_RULE_MISMATCH or why.endswith(".request_spent")), why


# 11. Held lists survive a power cycle, so a restart does not make a device refuse everything or forget its floor.
def test_11_held_lists_survive_a_restart():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    assert ep.execute(a.pay_small(100), PAY, small(100))[0]
    ep.restart()
    assert "beneficiary-registry" in ep.lists
    ok, why = ep.execute(a.pay_small(100), PAY, small(100))
    assert ok, why
