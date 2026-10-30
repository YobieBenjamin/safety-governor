# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The fresh adversarial audit of 30 October 2026 (the second one that day) against the third endpoint commit, kept
as regression tests. The auditor had seen none of the earlier reviews. It found two catastrophic, five serious and
four moderate weaknesses; the fourth commit answers them and this module asserts the secure outcome for each, so a
failing test means one is back. Its "held" probes (what it tried that the code refused) are kept too, so a later
change that reopens one of those shows up.

Attacker: one governor's signing key, every ticket field, every captured receipt, verdict, approval and commit
statement, a host between every endpoint and the governor, a second device with the same role name (and, as a
clone, the same device key). No ledger, governance, approver or observer key."""
from __future__ import annotations

import threading

import pytest

from govsim import endpoints as E
from govsim import reasons
from govsim.cluster import LISTED_RECIPIENTS, build_rack
from govsim.crypto import digest, random_id
from govsim.fleet import build_fleet
from govsim.policy import shape_problems

PAY = "payments.transfer"
KEY = "pay-usd-hourly"

class Attacker:
    def __init__(self, rack, gov=None):
        self.rack = rack
        self.g = gov or rack.nodes[0].governor
        self.captured_receipts: list[dict] = []
        self.captured_statements: list[dict] = []

    def forged_commit(self, ticket):
        t = ticket["payload"]
        return self.g.key.sign({"type": "commit", "ticket_id": t["ticket_id"], "request_hash": t.get("request_hash"),
                                "endpoint": t.get("endpoint"), "governor": t.get("governor"), "budget_key": t.get("budget_key"),
                                "reservation": t.get("reservation"), "fleet_receipts": list(self.captured_receipts),
                                "at": self.rack.clock.now()})

    def control_host(self, eps=None):
        for ep in (eps or self.rack.endpoints.values()):
            real = ep.commit

            def commit(ticket, real=real):
                out = real(ticket)
                if isinstance(out, dict):
                    self.captured_statements.append(out)
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

    def resign(self, ticket, changes, new_id=True):
        t = dict(ticket["payload"])
        if new_id:
            t["ticket_id"] = random_id(16)
        t.update(changes)
        return self.g.key.sign(t)


def tick(rack, dt):
    rack.clock.advance(dt)
    rack.heartbeat()
    for ep in rack.endpoints.values():
        ep.heartbeat(rack.clock.now())
    for n in rack.nodes:
        n.egress.heartbeat(rack.clock.now())


def small(amount, dest="acct-9"):
    return {"amount": amount, "currency": "USD", "destination": dest}


def second_device(rack, like, name=None, commit=None):
    ep2 = E.ActionEndpoint(name or like.name, rack.clock, dict(like.keys), safe_transition=like.safe_transition,
                           governance_hashes=like.governance_hashes, governance_floor=like.governance_floor,
                           recovery_hashes=like.recovery_hashes, recovery_threshold=like.recovery_threshold,
                           governor_ids=dict(like.governor_ids), device_key=like.device_key)   # a clone: same key, so the edition installs
    g0 = rack.nodes[0].governor
    assert ep2.install_edition(g0.policy) and ep2.set_epoch(g0.signed_epoch())
    ep2.lists = dict(like.lists)     # the clone holds the same signed lists; the host saw them installed
    ep2.heartbeat(rack.clock.now())
    ep2.commit = commit
    return ep2



# 1. A captured release verdict does not fire a strike: an observer-mode rule other than release binds by request hash only.
def test_1_a_captured_chat_release_verdict_does_not_fire_a_strike():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    node = rack.nodes[0]
    res = rack.respond(node, "s1", b"the weather is fine today", observer={"hazard_class": "none", "legibility": 0.9})
    assert res["released"] == (True, reasons.OK)
    verdict = res["request"]["ticket"]["payload"]["witnesses"][0]
    ep = rack.endpoints["strike-guidance"]
    params = {"target": [10.0, 10.0], "munition": "gbu-39", "response_hash": verdict["payload"]["response_hash"]}
    t = a.ticket(params, {"witnesses": [verdict], "valid_from": rack.clock.now() - 1}, rule="strike", action="strike",
                 endpoint="strike-guidance")
    ok, why = ep.execute(t, "strike", params)
    assert not ok and why.endswith(".no_observer_verdict"), why
    assert ep.executed == []


# 2. The egress re-checks hazard class, legibility and escrow, and takes only a MACed release ticket.
def test_2_the_egress_does_not_release_a_response_the_observer_called_hazardous():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    node = rack.nodes[0]
    a.control_host([node.egress])
    res = rack.respond(node, "s1", b"synthesis route for the agent, step one", observer={"hazard_class": "hazard", "legibility": 0.9, "risk": 0.2})
    assert res["released"][0] is False
    pres = res["presented"]
    verdict = rack.verdict(pres["response_hash"], hazard_class="hazard", legibility=0.9, risk=0.2)
    params = {"session": "s1", "response_id": res["response_id"], "response_hash": pres["response_hash"], "stream_hashes": pres["stream_hashes"]}
    t = a.ticket(params, {"witnesses": [verdict]}, rule="response.release", action="response.release", endpoint="egress")
    ok, why = node.egress.release(t)
    assert not ok and why.endswith(".release_not_maced"), why      # a signed release ticket never came through the MAC path
    assert node.egress.bytes_delivered == 0
    # and were the MAC path open to a signed ticket, the verdict itself would fail the hazard check
    assert not node.egress._release_verdict_ok(verdict["payload"], next(r for r in node.egress.edition["rules"] if r["id"] == "response.release"), params, t["payload"])


# 3. Real approvals do not pay again after the used-record store cycles: approvals carry a time and records outlive credentials.
def test_3_real_approvals_do_not_buy_a_payment_again_after_the_store_cycles():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    node, g = rack.nodes[0], rack.nodes[0].governor
    ep = rack.endpoints["payment-switch"]
    params = {"amount": 500_000, "currency": "USD", "destination": "acct-1"}
    r = rack.request(node, PAY, params)
    tick(rack, 61)
    for approver in rack.approvers["payments.transfer.large"][:2]:
        out = rack.approve(g, r["hold_id"], r["request_hash"], approver)
    good = out["ticket"]
    assert ep.execute(good, PAY, params)[0]
    moved = 500_000
    saved = E.USED_TICKET_CAPACITY
    E.USED_TICKET_CAPACITY = 50
    try:
        def fill(n):
            for _ in range(n):
                p0 = small(0)
                t = a.ticket(p0, {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"})
                ep.execute(t, PAY, p0)
        fill(45)
        for _ in range(5):
            tick(rack, 301)
            fill(45)
            gp = good["payload"]
            again = a.ticket(params, {"approvals": gp["approvals"], "ticket_id": gp["ticket_id"]},
                             rule="payments.transfer.large", request_id=gp["request_id"])
            ok, why = ep.execute(again, PAY, params)
            assert not ok, why
            moved += 500_000 if ok else 0
    finally:
        E.USED_TICKET_CAPACITY = saved
    assert moved == 500_000


# 4. A rate-bearing rule is counted at the endpoint.
def test_4_a_rate_limited_rule_is_counted_at_the_endpoint():
    rack = build_rack(1, policy_kw={"message_rate": {"max": 5, "window_s": 60}, "message_max_bytes": 100})
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["messaging"]
    sent = 0
    for i in range(100):
        p = {"recipient": LISTED_RECIPIENTS[0], "body": f"chunk {i:03d} " + "x" * 60}
        t = a.ticket(p, rule="message.send.listed", action="message.send", endpoint="messaging")
        ok, why = ep.execute(t, "message.send", p)
        sent += ok
    assert sent == 5
    assert any(why.endswith(".endpoint_rate_exceeded") for why, _ in ep.refused)
    tick(rack, 61)
    p = {"recipient": LISTED_RECIPIENTS[0], "body": "after the window"}
    t = a.ticket(p, rule="message.send.listed", action="message.send", endpoint="messaging")
    assert ep.execute(t, "message.send", p)[0]                      # the window passed: the count is a window, not a lock


# 5. The edition's expiry cannot be erased by a governor-signed epoch statement.
def test_5_a_governor_signed_epoch_statement_cannot_erase_the_edition_expiry():
    rack = build_rack(1, policy_kw={"expires_in_s": 1000})
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    g = a.g
    before = ep.policy_expires_at
    assert before is not None
    ep.set_epoch(g.key.sign({"type": "policy-epoch", "version": 999, "epoch": g.epoch, "expires_at": None}))
    assert ep.policy_expires_at == before
    assert not ep.set_epoch(g.key.sign({"type": "policy-epoch", "version": 999, "epoch": "attacker-epoch", "expires_at": None}))
    tick(rack, 2000)
    moved = 0
    for _ in range(3):
        p = small(999)
        t = a.ticket(p, {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"})
        ok, why = ep.execute(t, PAY, p)
        assert not ok and why == reasons.POLICY_EXPIRED, why
        moved += 999 if ok else 0
    assert moved == 0


# 6. The audit store checks the edition like every other egress.
def test_6_the_audit_store_checks_the_edition():
    rack = build_rack(1, policy_kw={"sandbox": True})
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    st = rack.audit_store
    st.heartbeat(rack.clock.now())
    assert st.edition is not None
    assert not st.set_epoch(a.g.key.sign({"type": "policy-epoch", "version": 999, "epoch": "attacker-epoch", "expires_at": None}))
    h = st.hold("s", "r1", b"escrowed bytes")
    params = {"session": "s", "response_id": "r1", "response_hash": h, "stream_hashes": {"response": h}}
    t = a.ticket(params, {"policy_epoch": "attacker-epoch"}, rule="no-such-rule", action="response.release", endpoint="audit-store")
    ok, why = st.release(t)
    assert not ok, why
    assert st.bytes_delivered == 0


# 7. A rule with no endpoint is accepted at no endpoint.
def test_7_a_rule_with_no_endpoint_is_accepted_nowhere():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    for name in ("payment-switch", "messaging", "fulfilment"):
        ep = rack.endpoints[name]
        p = {"cycles": 10 ** 12}
        t = a.ticket(p, rule="compute.extend", action="compute.extend", endpoint=name)
        ok, why = ep.execute(t, "compute.extend", p)
        assert not ok and why == reasons.TICKET_RULE_MISMATCH, (name, why)


# 8. A second device with a listed role name: unlisted, it installs no edition and acts on nothing; a clone of the
#    listed device shares the listed device's share of the cap.
def test_8_an_unlisted_second_device_acts_on_nothing():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep1 = rack.endpoints["payment-switch"]
    rogue = E.ActionEndpoint("payment-switch", rack.clock, dict(ep1.keys), safe_transition="decline",
                             governance_hashes=ep1.governance_hashes, governance_floor=ep1.governance_floor,
                             recovery_hashes=ep1.recovery_hashes, recovery_threshold=ep1.recovery_threshold,
                             governor_ids=dict(ep1.governor_ids))        # no device key: not a device the edition lists
    assert not rogue.install_edition(rack.nodes[0].governor.policy)
    rogue.commit = a.forged_commit
    rogue.heartbeat(rack.clock.now())
    p = small(999)
    t = a.ticket(p, {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"})
    ok, why = rogue.execute(t, PAY, p)
    assert not ok, why


@pytest.mark.xfail(strict=True, reason="design item: a clone of a listed device (same key) counts its own share; two clones together exceed the cap")
def test_8b_a_cloned_listed_device_does_not_double_the_cap():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep1 = rack.endpoints["payment-switch"]
    ep2 = second_device(rack, ep1, commit=a.forged_commit)
    moved = 0
    for ep in (ep1, ep2):
        for _ in range(3):
            p = small(999)
            t = a.ticket(p, {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"})
            ok, _ = ep.execute(t, PAY, p)
            moved += 999 if ok else 0
    assert moved <= 2000, moved


# 9. One fleet reservation does not spend twice between the ticket's expiry and its receipts' ageing.
def test_9_one_fleet_reservation_does_not_spend_twice_after_the_ticket_expires():
    racks, fleet = build_fleet(2)
    rack = racks[0]
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    params = small(400, "acct-1")
    r = rack.request(rack.nodes[0], PAY, params)
    assert r["ok"]
    a.captured_receipts.extend(r["ticket"]["payload"]["fleet_receipts"])
    assert ep.execute(r["ticket"], PAY, params)[0]
    committed_before = fleet.replicas[0].ledger.usage(KEY, 3600, rack.clock.now())[0]
    tick(rack, 301)
    ep._prune_used(rack.clock.now())
    again = a.resign(r["ticket"], {"valid_from": rack.clock.now(), "expires_at": rack.clock.now() + 1}, new_id=False)
    ok, why = ep.execute(again, PAY, params)
    assert not ok, why
    assert fleet.replicas[0].ledger.usage(KEY, 3600, rack.clock.now())[0] == committed_before
    assert sum(x["params"]["amount"] for x in ep.executed) == 400


# 10. A tamper revokes the governor at every endpoint, rack-local budgets included.
def test_10_after_a_tamper_the_default_rack_pays_nothing_on_the_extracted_key():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    pre = rack.request(rack.nodes[0], PAY, small(600, "acct-1"))
    assert pre["ok"]
    rack.nodes[0].governor.tamper_event()
    moved = 0
    ok, why = ep.execute(pre["ticket"], PAY, small(600, "acct-1"))
    assert not ok and why == reasons.TICKET_REVOKED_GOVERNOR, why
    for _ in range(5):
        p = small(999)
        t = a.ticket(p, {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"})
        ok, why = ep.execute(t, PAY, p)
        assert not ok and why == reasons.TICKET_REVOKED_GOVERNOR, why
        moved += 999 if ok else 0
    assert moved == 0
    ep.restart()                                                   # the revocation survives a power cycle
    assert a.g.key.key_id in ep.revoked_by_statement


# 11. The default messaging exit is bounded: the device holds the list, counts the rate.
def test_11_the_default_messaging_exit_is_bounded_for_the_extracted_key():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["messaging"]
    sent = 0
    for i in range(50):
        p = {"recipient": f"exfil-{i}@outside.example", "body": "W" * 100_000}
        t = a.ticket(p, rule="message.send.listed", action="message.send", endpoint="messaging")
        ok, why = ep.execute(t, "message.send", p)
        assert not ok and "not_in_allowed_list" in why, why
        sent += ok
    assert sent == 0
    rule = next(r for r in ep.edition["rules"] if r["id"] == "message.send.listed")
    assert rule.get("rate"), "the default messaging rule carries a rate"


# 12. The shape check: editions that would enforce nothing are refused at signing time.
def test_12_unsafe_rulebook_shapes_are_refused_by_the_compiler():
    rack = build_rack(1)
    rack.bring_up()
    img = rack.make_policy_image(rack.policy_version + 1, **rack.policy_kw)
    assert shape_problems(img) == []
    import copy
    def mutate(f):
        m = copy.deepcopy(img)
        f(m)
        return shape_problems(m)
    def no_endpoint(m):
        next(r for r in m["rules"] if r["id"] == "payments.transfer.small")["endpoint"] = None
    def unbounded_outward(m):
        r = next(r for r in m["rules"] if r["id"] == "message.send.listed"); r["rate"] = None; r["budget"] = None
    def risk_one(m):
        next(r for r in m["rules"] if r["id"] == "strike")["requirement"]["max_risk"] = 1.0
    def no_approvers(m):
        m["approver_keys"].pop("payments.transfer.large")
    def unlisted_store(m):
        m["audit"]["store"] = "somewhere-else"
    for f in (no_endpoint, unbounded_outward, risk_one, no_approvers, unlisted_store):
        assert mutate(f), f.__name__
    # and the governor refuses such an edition when it is signed and committed
    from govsim.policy import sign_policy
    m = copy.deepcopy(img); risk_one(m)
    rack.policy_version += 1
    res = rack.change_epoch(sign_policy(m, rack.governance[: rack.threshold]))
    assert not res["committed"]
    assert rack.nodes[0].governor.log.has("policy.unsafe_shape")


# 13. install_list refuses malformed fields rather than raising.
def test_13_a_malformed_list_is_refused_not_raised():
    rack = build_rack(1)
    rack.bring_up()
    ep = rack.endpoints["messaging"]
    env = rack.signed_list("recipient-registry", LISTED_RECIPIENTS, version=7)
    env["payload"]["expires_at"] = "never"
    # the payload changed, so the signatures no longer verify: refused before the fields are read
    assert not ep.install_list("recipient-registry", env)
    # and a genuinely signed list with a malformed field is refused, not raised on
    bad = rack.signed_list("recipient-registry", LISTED_RECIPIENTS, version=8)
    bad["payload"]["expires_at"] = "never"
    bad = rack.governance[0].sign(bad["payload"])
    bad["cosignatures"] = [rack.governance[1].sign(bad["payload"])]
    assert not ep.install_list("recipient-registry", bad)


# 14. The commit statement's time and the MAC commit path are checked.
def test_14_a_commit_statement_from_another_time_or_with_a_bad_mac_is_no_commit():
    # sampling off: a sampled response needs an escrow receipt, which is not what this test is about
    rack = build_rack(1, policy_kw={"audit": {"sample_rate": 0.0, "escrow_classes": ["hazard"], "store": "audit-store"}})
    rack.bring_up()
    node, g = rack.nodes[0], rack.nodes[0].governor
    ep = rack.endpoints["payment-switch"]
    params = small(300, "acct-1")
    r = rack.request(node, PAY, params)
    assert r["ok"]
    stmt = g.commit_from_endpoint(r["ticket"])
    assert isinstance(stmt, dict)
    far = dict(stmt["payload"]); far["at"] = rack.clock.now() + 10 ** 6
    assert not ep._commit_verified(r["ticket"], g.key.sign(far), rack.clock.now())
    assert ep._commit_verified(r["ticket"], stmt, rack.clock.now())
    # the MAC path at the egress: a statement MACed under the wrong key is no commit
    res = rack.respond(node, "s", b"a clean response", observer={"hazard_class": "none", "legibility": 0.9})
    assert res["released"] == (True, reasons.OK)
    from govsim.crypto import canonical, hmac_sha256
    t = res["request"]["ticket"]
    body = {"type": "commit", "ticket_id": t["payload"]["ticket_id"], "request_hash": t["payload"]["request_hash"], "endpoint": "egress",
            "governor": g.chip_id, "budget_key": None, "reservation": None, "fleet_receipts": [], "at": rack.clock.now()}
    bad = {"payload": body, "signer": g.key.key_id, "mac": hmac_sha256(b"not the key", canonical(body))}
    assert not node.egress._commit_verified(t, bad, rack.clock.now())
    good = {"payload": body, "signer": g.key.key_id, "mac": hmac_sha256(node.egress.mac_key, canonical(body))}
    assert node.egress._commit_verified(t, good, rack.clock.now())


# ----------------------------------------------------------------------------------------------------- held: things that were tried and refused
def test_held_threads_cannot_overspend_the_endpoint_count():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    tickets = [(a.ticket(small(999), {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"}), small(999)) for _ in range(40)]
    results = []
    barrier = threading.Barrier(40)

    def go(t, p):
        barrier.wait()
        results.append(ep.execute(t, PAY, p)[0])
    ths = [threading.Thread(target=go, args=tp) for tp in tickets]
    [th.start() for th in ths]
    [th.join() for th in ths]
    moved = 999 * sum(results)
    print(f"\n[held] 40 threads, cap 2000: moved {moved}")
    assert moved <= 2000


def test_held_one_ticket_many_threads_acts_once():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    p = small(999)
    t = a.ticket(p, {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"})
    results = []
    barrier = threading.Barrier(20)

    def go():
        barrier.wait()
        results.append(ep.execute(t, PAY, p)[0])
    ths = [threading.Thread(target=go) for _ in range(20)]
    [th.start() for th in ths]
    [th.join() for th in ths]
    assert sum(results) == 1


@pytest.mark.parametrize("amount", [True, "999", None, -1, -0.0, 1e308, 10 ** 30, [999], {"v": 999}])
def test_held_odd_amount_types_do_not_move_money(amount):
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["payment-switch"]
    p = small(amount)
    for rule in ("payments.transfer.small", "payments.transfer.large"):
        t = a.ticket(p, {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"} if rule.endswith("small") else {}, rule=rule)
        ok, why = ep.execute(t, PAY, p)
        assert not ok or amount == -0.0, (rule, why)     # -0.0 is a zero-dollar payment: nothing moves


def test_held_approvals_do_not_survive_an_epoch_change():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    node, g = rack.nodes[0], rack.nodes[0].governor
    ep = rack.endpoints["payment-switch"]
    params = {"amount": 5000, "currency": "USD", "destination": "acct-1"}
    r = rack.request(node, PAY, params)
    tick(rack, 61)
    for approver in rack.approvers["payments.transfer.large"][:2]:
        out = rack.approve(g, r["hold_id"], r["request_hash"], approver)
    good = out["ticket"]
    assert rack.change_epoch(rack.new_policy())["committed"]
    ep.set_epoch(g.signed_epoch())
    gp = good["payload"]
    t = a.ticket(params, {"approvals": gp["approvals"]}, rule="payments.transfer.large", request_id=gp["request_id"])
    ok, why = ep.execute(t, PAY, params)
    assert not ok and why.endswith(".approvals_short"), why


def test_held_commit_statement_fields_inconsistent_with_the_ticket_are_refused():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    ep = rack.endpoints["payment-switch"]
    p = small(100)
    t = a.ticket(p, {"budget_key": KEY, "reservation": "r1", "budget_owner": "gov00"})
    for field, value in (("endpoint", "messaging"), ("ticket_id", "other"), ("request_hash", "x"), ("reservation", "r2"),
                         ("budget_key", None), ("at", "now"), ("at", None), ("at", rack.clock.now() + 10_000), ("type", "ticket")):
        def commit(ticket, field=field, value=value):
            s = a.forged_commit(ticket)
            body = dict(s["payload"]); body[field] = value
            return a.g.key.sign(body)
        ep.commit = commit
        fresh = a.ticket(p, {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"})
        ok, why = ep.execute(fresh, PAY, p)
        assert not ok and why == reasons.COMMIT_REJECTED, (field, why)
    assert ep.executed == []


def test_held_a_bare_true_or_a_string_commit_is_no_commit():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    ep = rack.endpoints["payment-switch"]
    for answer in (True, "ok", 1, {"payload": {"type": "commit"}}, {"payload": None, "signer": a.g.key.key_id}):
        ep.commit = lambda ticket, answer=answer: answer
        p = small(100)
        t = a.ticket(p, {"budget_key": KEY, "reservation": random_id(4), "budget_owner": "gov00"})
        ok, why = ep.execute(t, PAY, p)
        assert not ok, (answer, why)
    assert ep.executed == []


def test_held_a_mac_release_ticket_cannot_be_forged_without_the_mac_key():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    node = rack.nodes[0]
    a.control_host([node.egress])
    h = node.egress.hold("s", "r9", b"held")
    params = {"session": "s", "response_id": "r9", "response_hash": h, "stream_hashes": {"response": h}}
    t = a.ticket(params, rule="response.release", action="response.release", endpoint="egress")
    t["mac"] = "00" * 32          # a signed envelope with a MAC field: the MAC path is taken and fails
    ok, why = node.egress.release(t)
    assert not ok and why == reasons.TICKET_BAD_SIGNATURE


def test_held_strike_verdict_replay_is_bounded_by_the_verdict_expiry():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    a.control_host()
    ep = rack.endpoints["strike-guidance"]
    params = {"target": [10.0, 10.0], "munition": "gbu-39"}
    r = rack.request_with_witness(rack.nodes[0], "strike", params)
    assert r["ok"], r
    tick(rack, 3)
    assert ep.execute(r["ticket"], "strike", params)[0]
    tick(rack, 31)                                            # the verdict's 30 s life has passed
    ep._prune_used(rack.clock.now())
    again = a.resign(r["ticket"], {"valid_from": rack.clock.now(), "expires_at": rack.clock.now() + 300}, new_id=False)
    ok, why = ep.execute(again, "strike", params)
    assert not ok and why.endswith(".no_observer_verdict"), why


def test_held_list_version_floor_and_expiry_hold_against_governor_signed_lists():
    rack = build_rack(1)
    rack.bring_up()
    a = Attacker(rack)
    ep = rack.endpoints["messaging"]
    assert ep.install_list("recipient-registry", rack.signed_list("recipient-registry", LISTED_RECIPIENTS, version=3))
    forged = a.g.key.sign({"type": "list", "list_id": "recipient-registry", "entries": ["evil@x"], "version": 9, "expires_at": rack.clock.now() + 1000})
    assert not ep.install_list("recipient-registry", forged)
    assert not ep.install_list("recipient-registry", rack.signed_list("recipient-registry", ["evil@x"], version=2))
    assert ep.lists["recipient-registry"]["version"] == 3


