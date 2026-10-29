# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The endpoint checks the fleet ledger's receipts and the signed lists itself (29 October 2026).

The threat: a governor whose signing key was extracted without tripping the tamper mesh. Before this change the
endpoint accepted a budgeted ticket that merely named a reservation, and its only defence was the commit message
going back to the honest governor; an attacker who also answers commits (the host is untrusted) could spend past the
fleet cap at that endpoint, and could mint for a recipient outside the registry because list checks stayed at the
governor. Now the ticket carries the replicas' signed receipts, the endpoint verifies them against the replica keys the
edition names, one reservation buys one ticket, and an endpoint that holds a signed list re-checks it.

Every test here answers the commit with True, modelling an attacker-controlled host, so nothing below passes because
the honest governor refused a commit."""
from __future__ import annotations

from govsim import reasons
from govsim.cluster import LISTED_RECIPIENTS
from govsim.crypto import digest, random_id
from govsim.fleet import build_fleet

PAY = "payments.transfer"


def _attacker_answers_commits(rack):
    for ep in rack.endpoints.values():
        ep.commit = lambda ticket: True


def _honest_ticket(rack, amount=300):
    params = {"amount": amount, "currency": "USD", "destination": "acct-1"}
    r = rack.request(rack.nodes[0], PAY, params)
    assert r["ok"], r
    return r["ticket"], params


def _forged(rack, payload_changes: dict, params: dict):
    """A ticket signed with the governor's own key (extracted), with whatever payload the attacker likes."""
    g = rack.nodes[0].governor
    now = rack.clock.now()
    t = {"type": "ticket", "ticket_id": random_id(16), "request_hash": digest(random_id(8)), "action": PAY,
         "params_digest": digest(params), "measurement": g.fingerprint, "rule": "payments.transfer.listed",
         "policy_epoch": g.epoch, "endpoint": "payment-switch", "budget_key": "pay-usd-hourly",
         "reservation": {"forged-replica": "rid-forged"}, "budget_owner": "fleet", "governor": g.chip_id,
         "issued_at": g.mono(), "valid_from": now, "expires_at": now + 300}
    t.update(payload_changes)
    return g.key.sign(t)


def _rule_id(rack):
    return next(r["id"] for r in rack.nodes[0].governor.policy["rules"] if r["action"] == PAY)


def test_an_honest_fleet_ticket_carries_the_replicas_receipts_and_is_accepted():
    racks, fleet = build_fleet(2)
    rack = racks[0]
    _attacker_answers_commits(rack)
    ticket, params = _honest_ticket(rack)
    receipts = ticket["payload"]["fleet_receipts"]
    assert len(receipts) >= fleet.edition_entry()["threshold"]
    assert {env["signer"] for env in receipts} == set(ticket["payload"]["reservation"])
    ok, why = rack.endpoints["payment-switch"].execute(ticket, PAY, params)
    assert ok, why


def test_a_forged_reservation_without_receipts_is_refused_at_the_endpoint():
    racks, _ = build_fleet(2)
    rack = racks[0]
    _attacker_answers_commits(rack)
    params = {"amount": 900, "currency": "USD", "destination": "acct-1"}
    ticket = _forged(rack, {"rule": _rule_id(rack)}, params)
    ok, why = rack.endpoints["payment-switch"].execute(ticket, PAY, params)
    assert not ok
    assert why.endswith(".fleet_receipts_missing"), why


def test_receipts_for_another_amount_do_not_authorize_this_one():
    """The attacker reserves $300 honestly, then signs a ticket for $900 that carries the $300 receipts."""
    racks, _ = build_fleet(2)
    rack = racks[0]
    _attacker_answers_commits(rack)
    honest, _ = _honest_ticket(rack, amount=300)
    params = {"amount": 900, "currency": "USD", "destination": "acct-1"}
    ticket = _forged(rack, {"rule": honest["payload"]["rule"], "reservation": honest["payload"]["reservation"],
                            "fleet_receipts": honest["payload"]["fleet_receipts"]}, params)
    ok, why = rack.endpoints["payment-switch"].execute(ticket, PAY, params)
    assert not ok
    assert why.endswith(".fleet_receipts_short"), why


def test_one_reservation_buys_one_ticket():
    """Real receipts, reused: the second ticket carrying the same reservation is refused before it acts."""
    racks, _ = build_fleet(2)
    rack = racks[0]
    _attacker_answers_commits(rack)
    honest, params = _honest_ticket(rack, amount=300)
    ep = rack.endpoints["payment-switch"]
    ok, why = ep.execute(honest, PAY, params)
    assert ok, why
    again = _forged(rack, {"rule": honest["payload"]["rule"], "reservation": honest["payload"]["reservation"],
                           "fleet_receipts": honest["payload"]["fleet_receipts"]}, params)
    ok, why = ep.execute(again, PAY, params)
    assert not ok
    assert why.endswith(".reservation_spent"), why
    assert len(ep.executed) == 1


def test_an_extracted_key_cannot_spend_past_the_fleet_cap_with_the_host_answering_commits():
    """The whole point: $2,000 an hour is the fleet cap. The attacker holds one governor's key and the host, signs
    payment tickets at will, and reuses every receipt it ever saw. The endpoint lets through at most the cap."""
    racks, _ = build_fleet(2)
    rack = racks[0]
    _attacker_answers_commits(rack)
    ep = rack.endpoints["payment-switch"]
    moved = 0
    seen = []
    for _ in range(12):
        params = {"amount": 400, "currency": "USD", "destination": "acct-1"}
        r = rack.request(rack.nodes[0], PAY, params)
        if r.get("ok"):
            seen.append(r["ticket"])
            ok, _ = ep.execute(r["ticket"], PAY, params)
            moved += 400 if ok else 0
        for old in seen:                                   # replay every receipt set under a fresh ticket id
            forged = _forged(rack, {"rule": old["payload"]["rule"], "reservation": old["payload"]["reservation"],
                                    "fleet_receipts": old["payload"]["fleet_receipts"]}, params)
            ok, _ = ep.execute(forged, PAY, params)
            moved += 400 if ok else 0
    assert 0 < moved <= 2000, moved


def test_an_endpoint_holding_the_recipient_list_refuses_an_unlisted_recipient_whoever_signed():
    racks, _ = build_fleet(1)
    rack = racks[0]
    _attacker_answers_commits(rack)
    g = rack.nodes[0].governor
    ep = rack.endpoints["messaging"]
    assert ep.install_list("recipient-registry", rack.signed_list("recipient-registry", LISTED_RECIPIENTS))
    params = {"recipient": "anyone@outside.example", "body": "weights part 1"}
    now = rack.clock.now()
    t = {"type": "ticket", "ticket_id": random_id(16), "request_hash": digest("forged"), "action": "message.send",
         "params_digest": digest(params), "measurement": g.fingerprint, "rule": "message.send.listed", "policy_epoch": g.epoch,
         "endpoint": "messaging", "budget_key": None, "reservation": None, "budget_owner": None, "governor": g.chip_id,
         "issued_at": g.mono(), "valid_from": now, "expires_at": now + 300}
    ok, why = ep.execute(g.key.sign(t), "message.send", params)
    assert not ok
    assert "not_in_allowed_list" in why, why
    # and a listed recipient, minted honestly, still goes through
    good = {"recipient": LISTED_RECIPIENTS[0], "body": "hello"}
    r = rack.request(rack.nodes[0], "message.send", good)
    assert r["ok"], r
    ok, why = ep.execute(r["ticket"], "message.send", good)
    assert ok, why


def test_an_endpoint_without_the_list_counts_what_it_could_not_check():
    racks, _ = build_fleet(1)
    rack = racks[0]
    ep = rack.endpoints["messaging"]
    before = ep.unchecked_list_constraints
    good = {"recipient": LISTED_RECIPIENTS[0], "body": "hello"}
    r = rack.request(rack.nodes[0], "message.send", good)
    assert r["ok"], r
    ok, _ = ep.execute(r["ticket"], "message.send", good)
    assert ok
    assert ep.unchecked_list_constraints == before + 1


def test_a_list_signed_below_the_quorum_is_not_installed_at_the_endpoint():
    racks, _ = build_fleet(1)
    rack = racks[0]
    ep = rack.endpoints["messaging"]
    env = rack.signed_list("recipient-registry", LISTED_RECIPIENTS)
    env.pop("cosignatures", None)
    assert not ep.install_list("recipient-registry", env)
    assert "recipient-registry" not in ep.lists


def test_used_reservations_survive_a_restart():
    racks, _ = build_fleet(2)
    rack = racks[0]
    _attacker_answers_commits(rack)
    honest, params = _honest_ticket(rack, amount=300)
    ep = rack.endpoints["payment-switch"]
    assert ep.execute(honest, PAY, params)[0]
    ep.restart()
    again = _forged(rack, {"rule": honest["payload"]["rule"], "reservation": honest["payload"]["reservation"],
                           "fleet_receipts": honest["payload"]["fleet_receipts"]}, params)
    ok, why = ep.execute(again, PAY, params)
    assert not ok and why.endswith(".reservation_spent"), why
