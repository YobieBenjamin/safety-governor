# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The sixteen probes of the adversarial logic audit of 30 October 2026, kept as regression tests.

The audit ran against the first endpoint-receipts change (commit 23a6b5a) and every probe below reproduced. Each test
here asserts the secure outcome, so a test that fails means the weakness is back. Six of the sixteen are design items
rather than defects in this change (reservation starvation, k = n liveness, n/k overspend under a lowered threshold,
the beneficiary registry not being an endpoint constraint, and the fail-closed burn of a ticket whose commit was
refused); those are marked xfail(strict=True) or documented as intended. The rack-local budget (C) was closed on the
review panel's finding of 30 October 2026 by the endpoint's own count, and the record of each is in docs/29 and the case-against paper, so they are tracked and not hidden.

The attacker model is the audit's: one governor's signing key extracted without tripping the tamper mesh, on a host the
attacker controls. The host forwards every commit to the governor and, when the governor refuses, answers with a commit
statement it signs itself with the extracted key (the strongest host the audit described)."""
from __future__ import annotations

import pytest

from govsim import reasons
from govsim.cluster import LISTED_RECIPIENTS, build_rack
from govsim.crypto import digest, random_id
from govsim.endpoints import MAX_TICKET_LIFE_S, ActionEndpoint
from govsim.fleet import build_fleet
from govsim.governor import TICKET_TTL_S

PAY = "payments.transfer"
KEY = "pay-usd-hourly"


CAPTURED: list[dict] = []   # every fleet receipt the host has seen, reused in every forged commit statement


def attacker_host(rack, gov=None):
    """Forward the commit; record every receipt that comes back; when the governor refuses, sign a commit statement
    with the extracted key that names every field the endpoint checks and carries every captured receipt
    (review panel 30 October 2026: the earlier helper left the statement half empty, which is why some probes
    passed for incidental reasons)."""
    g = gov or rack.nodes[0].governor

    def forged_commit(ticket):
        t = ticket["payload"]
        return g.key.sign({"type": "commit", "ticket_id": t["ticket_id"], "request_hash": t.get("request_hash"),
                           "endpoint": t.get("endpoint"), "governor": t.get("governor"), "budget_key": t.get("budget_key"),
                           "reservation": t.get("reservation"), "fleet_receipts": list(CAPTURED), "at": rack.clock.now()})

    def wrap(real):
        def commit(ticket):
            CAPTURED.extend(ticket["payload"].get("fleet_receipts") or [])
            out = real(ticket)
            if isinstance(out, dict):
                CAPTURED.extend((out.get("payload") or {}).get("fleet_receipts") or [])
                return out
            return forged_commit(ticket)
        return commit

    for ep in rack.endpoints.values():
        ep.commit = wrap(ep.commit)


def host_swallows_commits(rack):
    for ep in rack.endpoints.values():
        ep.commit = lambda ticket: True


def honest(rack, amount=300, node=0, dest="acct-1"):
    params = {"amount": amount, "currency": "USD", "destination": dest}
    r = rack.request(rack.nodes[node], PAY, params)
    return r, params


def signed_with_governor_key(rack, changes: dict, params: dict, rule="payments.transfer.small", gov=None):
    """A ticket signed with the governor's key but not produced by its rule engine (the extracted-key threat)."""
    g = gov or rack.nodes[0].governor
    now = rack.clock.now()
    rid = changes.get("request_id") or random_id(8)
    t = {"type": "ticket", "ticket_id": random_id(16), "request_id": rid, "request_hash": digest([rid, g.fingerprint, PAY, params]),
         "action": PAY, "params_digest": digest(params), "measurement": g.fingerprint, "rule": rule,
         "policy_epoch": g.epoch, "endpoint": "payment-switch", "budget_key": None,
         "reservation": None, "budget_owner": None, "governor": g.chip_id,
         "issued_at": g.mono(), "valid_from": now, "expires_at": now + 300}
    t.update(changes)
    return g.key.sign(t)


def tick(rack, dt):
    rack.clock.advance(dt)
    rack.heartbeat()
    for ep in rack.endpoints.values():
        ep.heartbeat(rack.clock.now())


# A. The approval lane was invisible at the endpoint: a human-mode rule was accepted on the governor signature alone.
#    Now the endpoint wants the edition's quorum of approver signatures over this request hash.
def test_A_a_human_mode_rule_needs_the_approvers_signatures_at_the_endpoint():
    racks, _ = build_fleet(2)
    rack = racks[0]
    attacker_host(rack)
    ep = rack.endpoints["payment-switch"]
    for _ in range(3):
        params = {"amount": 1_000_000, "currency": "USD", "destination": "acct-x"}
        t = signed_with_governor_key(rack, {}, params, rule="payments.transfer.large")
        ok, why = ep.execute(t, PAY, params)
        assert not ok and why.startswith(reasons.TICKET_RULE_MISMATCH), why
    assert ep.executed == []


# B. Receipts proved a reservation, and the ledger dropped it after TICKET_TTL_S without a commit, so a host that
#    swallowed commits refilled the hourly cap every 300 s. Now a bare 'committed' is no commit and nothing moves.
def test_B_swallowed_commits_no_longer_refill_the_cap():
    racks, fleet = build_fleet(2)
    rack = racks[0]
    host_swallows_commits(rack)
    ep = rack.endpoints["payment-switch"]
    moved = 0
    for _ in range(12):
        for _ in range(5):
            r, params = honest(rack, 400)
            if r.get("ok"):
                ok, why = ep.execute(r["ticket"], PAY, params)
                assert not ok and why in (reasons.COMMIT_REJECTED, reasons.TICKET_RULE_MISMATCH + ".endpoint_budget_exceeded"), why
                moved += 400 if ok else 0
        tick(rack, TICKET_TTL_S + 1)
    assert moved == 0


# C. A rack-local budget had no ledger outside the governor, so an extracted key that also signed its own commit
#    statements was bounded only by the rule's per-ticket maximum. Now the endpoint counts what it lets through under
#    each budget key against the rule's limit and window (review panel 30 October 2026).
def test_C_a_rack_local_budget_is_bounded_without_the_governor():
    rack = build_rack(1)
    rack.bring_up()
    attacker_host(rack)
    ep = rack.endpoints["payment-switch"]
    moved = 0
    for _ in range(20):
        params = {"amount": 999, "currency": "USD", "destination": "acct-x"}
        t = signed_with_governor_key(rack, {"budget_key": KEY, "reservation": "any", "budget_owner": "gov00"}, params)
        ok, _ = ep.execute(t, PAY, params)
        moved += 999 if ok else 0
    assert moved <= 2000, moved


# D. Receipts were not bound to the request: an honest reservation was redirected to another destination.
def test_D_receipts_cannot_be_redirected_to_another_destination():
    racks, _ = build_fleet(2)
    rack = racks[0]
    attacker_host(rack)
    ep = rack.endpoints["payment-switch"]
    r, params = honest(rack, 300, dest="acct-1")
    assert r["ok"]
    p = r["ticket"]["payload"]
    bad = {"amount": 300, "currency": "USD", "destination": "acct-x"}
    t = signed_with_governor_key(rack, {"budget_key": KEY, "reservation": p["reservation"], "budget_owner": "fleet",
                                        "fleet_receipts": p["fleet_receipts"]}, bad)
    ok, why = ep.execute(t, PAY, bad)
    assert not ok and why.endswith(".fleet_receipts_short"), why
    t = signed_with_governor_key(rack, {"budget_key": KEY, "reservation": p["reservation"], "budget_owner": "fleet",
                                        "request_hash": p["request_hash"], "request_id": p["request_id"],
                                        "fleet_receipts": p["fleet_receipts"]}, bad)
    ok, why = ep.execute(t, PAY, bad)                        # the hash copied too: it no longer matches the parameters
    assert not ok and why.endswith(".request_hash_mismatch"), why
    ok2, why2 = ep.execute(r["ticket"], PAY, params)       # and the honest ticket still goes through
    assert ok2, why2


# E. The used-reservation record is per device, so a second device with the same role name accepted the same
#    receipts. Now the receipts name the endpoint, and the commit needs the replicas' commit receipts, which the
#    ledger issues once per reservation.
def test_E_the_same_receipts_do_not_spend_at_a_second_payment_switch():
    racks, _ = build_fleet(2)
    rack = racks[0]
    attacker_host(rack)
    ep1 = rack.endpoints["payment-switch"]
    g0 = rack.nodes[0].governor
    ep2 = ActionEndpoint("payment-switch", rack.clock, dict(ep1.keys), safe_transition="decline",
                         governance_hashes=ep1.governance_hashes, governance_floor=ep1.governance_floor,
                         recovery_hashes=ep1.recovery_hashes, recovery_threshold=ep1.recovery_threshold,
                         governor_ids={k: g.chip_id for k, g in ((n.governor.key.key_id, n.governor) for n in rack.nodes)},
                         device_key=ep1.device_key)   # a clone of the listed device: same key, so the edition installs
    ep2.commit = ep1.commit
    assert ep2.install_edition(g0.policy) and ep2.set_epoch(g0.signed_epoch())
    ep2.heartbeat(rack.clock.now())
    r, params = honest(rack, 400)
    assert r["ok"]
    assert ep1.execute(r["ticket"], PAY, params)[0]
    p = r["ticket"]["payload"]
    again = signed_with_governor_key(rack, {"budget_key": KEY, "reservation": p["reservation"], "budget_owner": "fleet",
                                            "request_hash": p["request_hash"], "request_id": p["request_id"],
                                            "fleet_receipts": p["fleet_receipts"]}, params)
    ok, why = ep2.execute(again, PAY, params)
    assert not ok, why


# F. Free starvation: a host with no key reserves the whole fleet cap and never executes; other racks are refused
#    until the reservations lapse. Design item: reservation rate limits per requester (docs/29, case-against).
@pytest.mark.xfail(strict=True, reason="design item: reservation starvation by a keyless host; rate limits per requester are not yet designed")
def test_F_a_keyless_host_cannot_starve_the_fleet():
    racks, fleet = build_fleet(2)
    a, b = racks
    for _ in range(5):
        r, _ = honest(a, 400)
        assert r["ok"]
    r, _ = honest(b, 100)
    assert r["ok"], r


# G. Partial reservations were never released: one unreachable replica left orphans on the others.
def test_G_partial_reservations_are_released():
    racks, fleet = build_fleet(2)
    a, b = racks
    fleet.replicas[2].reachable = False
    for _ in range(5):
        r, _ = honest(a, 400)
        assert not r["ok"]
    fleet.replicas[2].reachable = True
    r, _ = honest(b, 100)
    assert r["ok"], r
    _, reserved = fleet.replicas[0].ledger.usage(KEY, 3600, a.clock.now())
    assert reserved == 100


# H. One unreachable replica stops every fleet-budgeted payment (k = n). Intended: the fleet count fails closed; the
#    liveness cost is recorded as a design item (threshold replicas with a bounded n/k overspend, see I).
def test_H_one_replica_down_fails_closed():
    racks, fleet = build_fleet(2)
    fleet.replicas[1].reachable = False
    r, _ = honest(racks[0], 100)
    assert not r["ok"] and r["why"] == reasons.GATE_BUDGET_OWNER_UNREACHABLE


# I. With k = 2 of 3 and a flapping replica, reservations reach n/k times the cap. Design item: the bound is known
#    and documented (the cap times n/k), not yet tightened.
@pytest.mark.xfail(strict=True, reason="design item: under a lowered threshold a flapping replica allows n/k times the cap")
def test_I_a_lowered_threshold_does_not_overspend():
    racks, fleet = build_fleet(2)
    fleet.threshold = 2
    for rack in racks:
        for node in rack.nodes:
            node.governor.policy["fleet_ledger"]["threshold"] = 2
    a = racks[0]
    total = 0
    for down in (0, 1, 2):
        for rep in fleet.replicas:
            rep.reachable = True
        fleet.replicas[down].reachable = False
        for _ in range(5):
            r, _ = honest(a, 200)
            total += 200 if r.get("ok") else 0
    assert total <= 2000, total


# J. No upper bound on ticket validity: used-record entries that never pruned. Now the endpoint refuses a ticket
#    valid for longer than MAX_TICKET_LIFE_S.
def test_J_ticket_validity_has_a_ceiling():
    racks, _ = build_fleet(1)
    rack = racks[0]
    ep = rack.endpoints["payment-switch"]
    params = {"amount": 1000, "currency": "USD", "destination": "acct-x"}
    t = signed_with_governor_key(rack, {"expires_at": rack.clock.now() + MAX_TICKET_LIFE_S + 1}, params, rule="payments.transfer.large")
    ok, why = ep.admit(t, PAY, params, rack.clock.now())
    assert not ok and why.endswith(".validity_too_long"), why
    t = signed_with_governor_key(rack, {"expires_at": "never"}, params, rule="payments.transfer.large")
    ok, why = ep.admit(t, PAY, params, rack.clock.now())
    assert not ok and why.endswith(".validity_malformed"), why


# K. An expired but quorum-signed list was installed and made every honest ticket fail closed.
def test_K_an_expired_signed_list_is_not_installed():
    racks, _ = build_fleet(1)
    rack = racks[0]
    ep = rack.endpoints["messaging"]
    old = rack.signed_list("recipient-registry", LISTED_RECIPIENTS, expires_in_s=10)
    tick(rack, 20)
    assert not ep.install_list("recipient-registry", old)
    good = {"recipient": LISTED_RECIPIENTS[0], "body": "hello"}
    r = rack.request(rack.nodes[0], "message.send", good)
    assert r["ok"], r
    ok, why = ep.execute(r["ticket"], "message.send", good)
    assert ok, why


# L. The list version floor was in memory only: after a restart an older list replaced a newer one.
def test_L_the_list_version_floor_survives_a_restart():
    racks, _ = build_fleet(1)
    rack = racks[0]
    ep = rack.endpoints["messaging"]
    assert ep.install_list("recipient-registry", rack.signed_list("recipient-registry", LISTED_RECIPIENTS + ["c"], version=5))
    assert not ep.install_list("recipient-registry", rack.signed_list("recipient-registry", LISTED_RECIPIENTS, version=1))
    g0 = rack.nodes[0].governor
    cold = ActionEndpoint("messaging", rack.clock, dict(ep.keys), store=ep.store, safe_transition="hold",
                          governance_hashes=ep.governance_hashes, governance_floor=ep.governance_floor,
                          recovery_hashes=ep.recovery_hashes, recovery_threshold=ep.recovery_threshold, device_key=ep.device_key)
    assert cold.install_edition(g0.policy)
    assert not cold.install_list("recipient-registry", rack.signed_list("recipient-registry", LISTED_RECIPIENTS, version=1))
    assert cold.install_list("recipient-registry", rack.signed_list("recipient-registry", LISTED_RECIPIENTS, version=6))


# M. The beneficiary registry (F04) is not a rule constraint, so the endpoint neither checks nor counts it.
#    Design item: the registry becomes an allowed-list constraint on the destination, so the endpoint can hold it.
@pytest.mark.xfail(strict=True, reason="design item: the beneficiary registry is not yet an endpoint-checkable list constraint")
def test_M_the_beneficiary_registry_is_an_endpoint_constraint():
    racks, _ = build_fleet(1)
    rack = racks[0]
    ep = rack.endpoints["payment-switch"]
    rule = next(x for x in ep.edition["rules"] if x["id"] == "payments.transfer.small")
    assert "destination" in rule["constraints"]


# N. Tickets minted before a tamper event stayed valid at the endpoint until expiry. The governor is zeroized by the
#    tamper, so it signs no commit; a commit statement the attacker signs with the extracted key carries no fleet
#    commit receipts, and the endpoint acts on neither.
def test_N_pre_tamper_tickets_do_not_act_after_the_tamper():
    racks, _ = build_fleet(1)
    rack = racks[0]
    attacker_host(rack)
    ep = rack.endpoints["payment-switch"]
    r, params = honest(rack, 300)
    assert r["ok"]
    rack.nodes[0].governor.tamper_event()
    ok, why = ep.execute(r["ticket"], PAY, params)
    # the tampered governor's last act revoked its key at every endpoint, so the ticket is refused before any commit
    assert not ok and why in (reasons.TICKET_REVOKED_GOVERNOR, reasons.COMMIT_REJECTED), why


# O. The signer and the governor field were not tied: receipts for gov00 rode in a ticket signed by gov01.
def test_O_the_signer_must_be_the_governor_the_ticket_names():
    racks, _ = build_fleet(2, gpus_per_rack=2)
    rack = racks[0]
    attacker_host(rack, gov=rack.nodes[1].governor)
    ep = rack.endpoints["payment-switch"]
    r, params = honest(rack, 300, node=0)
    assert r["ok"]
    p = r["ticket"]["payload"]
    g1 = rack.nodes[1].governor
    t = signed_with_governor_key(rack, {"budget_key": KEY, "reservation": p["reservation"], "budget_owner": "fleet",
                                        "request_hash": p["request_hash"], "request_id": p["request_id"],
                                        "fleet_receipts": p["fleet_receipts"], "governor": "gov00"}, params, gov=g1)
    assert t["signer"] == g1.key.key_id and t["payload"]["governor"] == "gov00"
    ok, why = ep.execute(t, PAY, params)
    assert not ok and why.endswith(".governor_mismatch"), why


# P. A commit answered False after the burn: the honest ticket is spent, nothing happens, the reservation is held
#    until it lapses. This is the intended fail-closed order (burn before act); recorded here as behaviour, not defect.
def test_P_a_refused_commit_burns_the_ticket_and_nothing_happens():
    racks, fleet = build_fleet(1)
    rack = racks[0]
    for ep_ in rack.endpoints.values():
        ep_.commit = lambda ticket: False
    ep = rack.endpoints["payment-switch"]
    r, params = honest(rack, 300)
    ok, why = ep.execute(r["ticket"], PAY, params)
    assert not ok and why == reasons.COMMIT_REJECTED
    ep.commit = rack._commit_route
    ok, why = ep.execute(r["ticket"], PAY, params)
    assert not ok and why == reasons.TICKET_REPLAY
    assert ep.executed == []
