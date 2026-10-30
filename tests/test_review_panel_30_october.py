# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The review panel's probes of 30 October 2026 against the second endpoint commit, kept as regression tests.

A four-member panel (design/30-review-panel-decision.md in the project) broke the second commit with the audit's own
attacker and listed what must change before merge. Each test here asserts the secure outcome, so a failing test means
the weakness is back. The attacker is the strongest the panel described: one governor's key extracted, every field of
a ticket under the attacker's pen, captured receipts and captured commit statements reused, and a host that forwards
the commit to the governor and, when the governor refuses, answers with a commit statement the attacker signs itself,
carrying every captured fleet receipt it has ever seen."""
from __future__ import annotations

import pytest

from govsim import reasons
from govsim.cluster import build_rack
from govsim.crypto import digest, random_id
from govsim.endpoints import ActionEndpoint
from govsim.fleet import build_fleet
from govsim.governor import TICKET_TTL_S

PAY = "payments.transfer"
KEY = "pay-usd-hourly"


class Attacker:
    """Holds one governor's extracted key and everything it has captured on the host."""

    def __init__(self, rack, gov=None):
        self.rack = rack
        self.g = gov or rack.nodes[0].governor
        self.captured_receipts: list[dict] = []     # fleet-reserve and fleet-commit receipts seen on the host
        self.captured_statements: list[dict] = []   # commit statements the honest governor signed

    def forged_commit(self, ticket):
        t = ticket["payload"]
        return self.g.key.sign({"type": "commit", "ticket_id": t["ticket_id"], "request_hash": t.get("request_hash"),
                                "endpoint": t.get("endpoint"), "governor": t.get("governor"), "budget_key": t.get("budget_key"),
                                "reservation": t.get("reservation"), "fleet_receipts": list(self.captured_receipts),
                                "at": self.rack.clock.now()})

    def control_host(self):
        """The host forwards every commit, records what comes back, and lies with a forged statement on refusal."""
        for ep in self.rack.endpoints.values():
            real = ep.commit

            def commit(ticket, real=real):
                out = real(ticket)
                if isinstance(out, dict):
                    self.captured_statements.append(out)
                    self.captured_receipts.extend((out.get("payload") or {}).get("fleet_receipts") or [])
                    return out
                return self.forged_commit(ticket)
            ep.commit = commit

    def see(self, ticket):
        self.captured_receipts.extend(ticket["payload"].get("fleet_receipts") or [])

    def ticket(self, params, changes=None, rule="payments.transfer.small", action=PAY, endpoint="payment-switch", request_id=None):
        """A ticket built the way the governor builds one, with every field the attacker likes."""
        g, now = self.g, self.rack.clock.now()
        rid = request_id or random_id(8)
        t = {"type": "ticket", "ticket_id": random_id(16), "request_id": rid, "request_hash": digest([rid, g.fingerprint, action, params]),
             "action": action, "params_digest": digest(params), "measurement": g.fingerprint, "rule": rule, "policy_epoch": g.epoch,
             "endpoint": endpoint, "budget_key": None, "reservation": None, "budget_owner": None, "governor": g.chip_id,
             "issued_at": g.mono(), "valid_from": now, "expires_at": now + 300}
        t.update(changes or {})
        return g.key.sign(t)

    def resign(self, ticket, changes):
        t = dict(ticket["payload"])
        t["ticket_id"] = random_id(16)
        t.update(changes)
        return self.g.key.sign(t)


def honest(rack, amount=300, node=0, dest="acct-1"):
    params = {"amount": amount, "currency": "USD", "destination": dest}
    return rack.request(rack.nodes[node], PAY, params), params


def tick(rack, dt):
    rack.clock.advance(dt)
    rack.heartbeat()
    for ep in rack.endpoints.values():
        ep.heartbeat(rack.clock.now())


# 1. The commit check is keyed off the edition's rule, not the ticket's budget field.
def test_1_dropping_the_budget_key_from_a_ticket_does_not_skip_the_fleet_commit_check():
    racks, fleet = build_fleet(2)
    rack = racks[0]
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    first, params = honest(rack, 400)
    also = a.resign(first["ticket"], {"budget_key": None, "reservation": None, "budget_owner": None})
    ok, why = ep.execute(also, PAY, params)
    assert not ok and why.endswith(".no_reservation"), why
    moved = 0
    for _ in range(12):
        for _ in range(5):
            r, params = honest(rack, 400)
            if not r.get("ok"):
                continue
            a.see(r["ticket"])
            evil = a.resign(r["ticket"], {"budget_key": None})
            ok, why = ep.execute(evil, PAY, params)
            assert not ok and why.startswith(reasons.TICKET_RULE_MISMATCH), why
            moved += 400 if ok else 0
        tick(rack, TICKET_TTL_S + 1)
    assert moved == 0


# 2. One authorization, one effect: approvals are tied to the parameters through the recomputed request hash.
def test_2_two_honest_approvals_cannot_be_rebound_to_other_parameters():
    rack = build_rack(1)
    rack.bring_up()
    node, g = rack.nodes[0], rack.nodes[0].governor
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    params = {"amount": 1001, "currency": "USD", "destination": "acct-1"}
    r = rack.request(node, PAY, params)
    assert r["why"] == reasons.GATE_HELD, r
    tick(rack, 61)                                     # past the approval latency floor
    for approver in rack.approvers["payments.transfer.large"][:2]:
        out = rack.approve(g, r["hold_id"], r["request_hash"], approver)
    assert out["ok"], out
    good = out["ticket"]
    approvals = good["payload"]["approvals"]
    assert len(approvals) >= 2
    big = {"amount": 1_000_000, "currency": "USD", "destination": "acct-x"}
    moved = 0
    for _ in range(10):
        evil = a.ticket(big, {"approvals": approvals, "request_hash": good["payload"]["request_hash"],
                              "request_id": good["payload"]["request_id"]}, rule=good["payload"]["rule"])
        ok, why = ep.execute(evil, PAY, big)
        assert not ok and why.endswith(".request_hash_mismatch"), why
        evil2 = a.ticket(big, {"approvals": approvals}, rule=good["payload"]["rule"])
        ok, why = ep.execute(evil2, PAY, big)
        assert not ok and why.endswith(".approvals_short"), why
        moved += 0
    assert moved == 0
    ok, why = ep.execute(good, PAY, params)          # the honest, approved ticket still goes through once
    assert ok, why
    again = a.resign(good, {})
    ok, why = ep.execute(again, PAY, params)
    assert not ok and why.endswith(".request_spent"), why


# 3. Observer verdicts are checked for expiry and risk at the endpoint.
def test_3_an_expired_or_risky_verdict_does_not_fire_a_strike():
    rack = build_rack(1, "rack")
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["strike-guidance"]
    params = {"target": [10.0, 10.0], "munition": "gbu-39"}
    rid = random_id(8)
    rhash = digest([rid, a.g.fingerprint, "strike", params])
    stale = rack.observer.sign({"type": "observer-verdict", "request_hash": rhash, "risk": 0.1, "expires_at": rack.clock.now() - 1})
    risky = rack.observer.sign({"type": "observer-verdict", "request_hash": rhash, "risk": 0.99, "expires_at": rack.clock.now() + 60})
    rack.clock.advance(3)
    rack.heartbeat()
    for w in (stale, risky):
        t = a.ticket(params, {"witnesses": [w], "valid_from": rack.clock.now() - 1}, rule="strike", action="strike",
                     endpoint="strike-guidance", request_id=rid)
        ok, why = ep.execute(t, "strike", params)
        assert not ok and why.endswith(".no_observer_verdict"), why
    assert ep.executed == []


# 4. A captured commit statement, with its real fleet-commit receipts, cannot be rewrapped for another ticket or device.
def test_4_captured_commit_receipts_do_not_spend_again_here_or_at_a_second_switch():
    racks, _ = build_fleet(2)
    rack = racks[0]
    a = Attacker(rack)
    a.control_host()
    ep1 = rack.endpoints["payment-switch"]
    r, params = honest(rack, 400)
    assert r["ok"]
    a.see(r["ticket"])
    assert ep1.execute(r["ticket"], PAY, params)[0]
    assert a.captured_statements, "the host saw the honest commit statement"
    p = r["ticket"]["payload"]
    # the same reservation and receipts under a fresh ticket at the same device
    again = a.resign(r["ticket"], {})
    ok, why = ep1.execute(again, PAY, params)
    assert not ok and (why.endswith(".request_spent") or why.endswith(".reservation_spent")), why
    # and at a second device with the same role name
    g0 = rack.nodes[0].governor
    ep2 = ActionEndpoint("payment-switch", rack.clock, dict(ep1.keys), safe_transition="decline",
                         governance_hashes=ep1.governance_hashes, governance_floor=ep1.governance_floor,
                         recovery_hashes=ep1.recovery_hashes, recovery_threshold=ep1.recovery_threshold,
                         governor_ids={n.governor.key.key_id: n.governor.chip_id for n in rack.nodes},
                         device_key=ep1.device_key)   # a clone of the listed device: same key, so the edition installs
    ep2.commit = lambda ticket: a.captured_statements[0]
    assert ep2.install_edition(g0.policy) and ep2.set_epoch(g0.signed_epoch())
    ep2.heartbeat(rack.clock.now())
    ok, why = ep2.execute(a.resign(r["ticket"], {}), PAY, params)
    assert not ok, why
    ep2.commit = lambda ticket: a.forged_commit(ticket)
    ok, why = ep2.execute(a.resign(r["ticket"], {}), PAY, params)
    assert not ok, why                                # the receipts name the honest ticket's id, not the re-signed one
    assert ep2.executed == []


# 4b. The residual the panel named: a verbatim copy of an honest ticket, with its real commit statement, presented at
#     a second device that shares the first device's role name. The edition names endpoints by role, not by device,
#     so nothing in the ticket or the receipts tells the two devices apart. Design item: per-device identity in the
#     edition (a key per device), recorded in docs/29.
@pytest.mark.xfail(strict=True, reason="design item: endpoints are named by role; a verbatim ticket and statement act once per device sharing the role")
def test_4b_a_verbatim_ticket_does_not_act_twice_at_two_devices_with_one_role_name():
    racks, _ = build_fleet(2)
    rack = racks[0]
    a = Attacker(rack)
    a.control_host()
    ep1 = rack.endpoints["payment-switch"]
    r, params = honest(rack, 400)
    assert r["ok"]
    assert ep1.execute(r["ticket"], PAY, params)[0]
    g0 = rack.nodes[0].governor
    ep2 = ActionEndpoint("payment-switch", rack.clock, dict(ep1.keys), safe_transition="decline",
                         governance_hashes=ep1.governance_hashes, governance_floor=ep1.governance_floor,
                         recovery_hashes=ep1.recovery_hashes, recovery_threshold=ep1.recovery_threshold,
                         governor_ids={n.governor.key.key_id: n.governor.chip_id for n in rack.nodes},
                         device_key=ep1.device_key)   # a clone of the listed device: same key, so the edition installs
    ep2.commit = lambda ticket: a.captured_statements[0]
    assert ep2.install_edition(g0.policy) and ep2.set_epoch(g0.signed_epoch())
    ep2.heartbeat(rack.clock.now())
    ok, why = ep2.execute(r["ticket"], PAY, params)
    assert not ok, why


# 5. The default rack's money budget is bounded at the endpoint, with no fleet ledger and the host forging commits.
def test_5_the_default_rack_is_bounded_by_the_endpoints_own_count():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    moved = 0
    for _ in range(200):
        params = {"amount": 999, "currency": "USD", "destination": "acct-x"}
        t = a.ticket(params, {"budget_key": KEY, "reservation": "forged-" + random_id(4), "budget_owner": "gov00"})
        ok, why = ep.execute(t, PAY, params)
        moved += 999 if ok else 0
    assert moved <= 2000, moved
    assert any(why.endswith(".endpoint_budget_exceeded") for why, _ in ep.refused)
    tick(rack, 3601)                                  # the window passes and the endpoint's count clears on its own
    params = {"amount": 999, "currency": "USD", "destination": "acct-x"}
    t = a.ticket(params, {"budget_key": KEY, "reservation": "forged-" + random_id(4), "budget_owner": "gov00"})
    ok, why = ep.execute(t, PAY, params)
    assert ok, why                                    # inside the limit again: the bound is a window, not a lock


# 6. Captured receipts do not respend after the used-reservation record is pruned: receipts age.
def test_6_captured_receipts_age_out():
    racks, _ = build_fleet(2)
    rack = racks[0]
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    r, params = honest(rack, 300)
    assert r["ok"]
    a.see(r["ticket"])
    assert ep.execute(r["ticket"], PAY, params)[0]
    tick(rack, 3700)
    ep._prune_used(rack.clock.now())
    assert not ep.used_reservations and not ep.used_requests
    # the same ticket id and request, a new window: nothing in the records refuses it any more; only the receipts' age does
    t = dict(r["ticket"]["payload"]); t.update({"valid_from": rack.clock.now(), "expires_at": rack.clock.now() + 300})
    late = a.g.key.sign(t)
    ok, why = ep.execute(late, PAY, params)
    assert not ok and why.endswith(".fleet_receipts_short"), why


# 7. A string in valid_from is refused, not raised.
def test_7_a_malformed_valid_from_is_refused():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    ep = rack.endpoints["payment-switch"]
    params = {"amount": 100, "currency": "USD", "destination": "acct-1"}
    for bad in ("0", "soon", None, True):
        t = a.ticket(params, {"valid_from": bad})
        ok, why = ep.admit(t, PAY, params, rack.clock.now())
        assert not ok and why.endswith(".validity_malformed"), (bad, why)


# 8. The ticket's budget fields must be the rule's: a budgeted ticket for a rule with no budget is refused.
def test_8_a_reservation_on_a_rule_without_a_budget_is_refused():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["messaging"]
    params = {"recipient": "alice@bank.example", "body": "hello"}
    t = a.ticket(params, {"budget_key": KEY, "reservation": "x", "budget_owner": "gov00"}, rule="message.send.listed",
                 action="message.send", endpoint="messaging")
    ok, why = ep.execute(t, "message.send", params)
    assert not ok and (why.endswith(".unexpected_reservation") or why.startswith(reasons.TICKET_RULE_MISMATCH)), why


# 9. The release path's commit statement is MACed, not signed: no signature per response.
def test_9_a_release_commit_costs_no_signature():
    rack = build_rack(1, "rack", policy_kw={"output_queries": 10 ** 6, "output_bytes": 10 ** 12,
                                             "audit": {"sample_rate": 0.0, "escrow_classes": ["hazard"], "store": "audit-store"}})
    rack.bring_up()
    node = rack.nodes[0]
    before = dict(node.governor.ops)
    res = rack.respond(node, "s", b"a clean response", observer={"hazard_class": "none", "legibility": 0.9})
    assert res["released"] == (True, reasons.OK), res["released"]
    after = node.governor.ops
    assert after.get("commit_mac", 0) == before.get("commit_mac", 0) + 1
    assert after.get("commit", 0) == before.get("commit", 0)
    assert after.get("ticket", 0) == before.get("ticket", 0)


# 10. A pre-tamper ticket under a rule with no budget: bounded by the rule's per-ticket maximum and the ticket's
#     TTL, not refused, because nothing outside the tampered governor counts it. Recorded as a known limit.
@pytest.mark.xfail(strict=True, reason="known limit: a pre-tamper ticket under an unbudgeted rule acts until its TTL; the tamper must reach the endpoints")
def test_10_a_pre_tamper_ticket_under_an_unbudgeted_rule_does_not_act_after_the_tamper():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    ep = rack.endpoints["messaging"]
    params = {"recipient": "alice@bank.example", "body": "hello"}
    r = rack.request(rack.nodes[0], "message.send", params)
    assert r["ok"], r
    rack.nodes[0].governor.tamper_event()
    a.control_host()
    ok, why = ep.execute(r["ticket"], "message.send", params)
    assert not ok, why
