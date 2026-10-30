# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The endpoint checks the fleet ledger's receipts, the governor's signed commit and the signed lists itself
(29 and 30 October 2026).

The threat: a governor whose signing key was extracted without tripping the tamper mesh, on a host the attacker
controls. Before this change the endpoint accepted a budgeted ticket that merely named a reservation, took the host's
word for the commit, and left list checks to the governor; an attacker could spend past the fleet cap at that endpoint,
and the audit of 30 October showed that a host which simply swallows commits lets the hourly cap refill every five
minutes, because an uncommitted reservation lapses. Now the ticket carries the replicas' signed receipts bound to this
request and this endpoint, the endpoint verifies them against the replica keys the edition names, one reservation buys
one ticket, the commit is a statement signed by the minting governor that carries the replicas' fleet-commit receipts,
and an endpoint that holds a signed list re-checks it.

Every test here runs on a lying host: it forwards the commit to the governor, and answers True itself for anything the
governor refused. So nothing below passes because the honest governor refused a commit; it passes only because the
endpoint checked for itself."""
from __future__ import annotations

from govsim import reasons
from govsim.cluster import LISTED_RECIPIENTS
from govsim.crypto import digest, random_id
from govsim.fleet import build_fleet

PAY = "payments.transfer"
KEY = "pay-usd-hourly"


def _attacker_answers_commits(rack):
    """The host forwards the commit, and answers True on the governor's behalf whenever the governor refused."""
    for ep in rack.endpoints.values():
        real = ep.commit
        ep.commit = (lambda r: (lambda ticket: r(ticket) or True))(real)


def _host_swallows_commits(rack):
    """The host never forwards a commit and always answers True (the audit's cap-refill attack)."""
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
    rid = random_id(8)
    # The attacker builds the ticket the way the governor does, request id and hash included, so the endpoint's
    # recomputation of the hash passes and the checks under test are the ones that refuse.
    t = {"type": "ticket", "ticket_id": random_id(16), "request_id": rid, "request_hash": digest([rid, g.fingerprint, PAY, params]),
         "action": PAY, "params_digest": digest(params), "measurement": g.fingerprint, "rule": "payments.transfer.listed",
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
    """The attacker reserves $300 honestly, then signs a ticket for $900 that carries the $300 receipts. The request
    hash refuses it first; the amount check is exercised on its own with receipts the replicas sign for this very
    request at the smaller amount (a governor that reserved less than it minted for)."""
    racks, fleet = build_fleet(2)
    rack = racks[0]
    _attacker_answers_commits(rack)
    honest, _ = _honest_ticket(rack, amount=300)
    params = {"amount": 900, "currency": "USD", "destination": "acct-1"}
    ticket = _forged(rack, {"rule": honest["payload"]["rule"], "reservation": honest["payload"]["reservation"],
                            "fleet_receipts": honest["payload"]["fleet_receipts"]}, params)
    ep = rack.endpoints["payment-switch"]
    ok, why = ep.execute(ticket, PAY, params)
    assert not ok
    assert why.endswith(".fleet_receipts_short"), why
    # receipts genuinely signed by the replicas, bound to this request and ticket, but for $300 against a $900 ticket
    t = ticket["payload"]
    rule = next(r for r in ep.edition["rules"] if r["id"] == t["rule"])
    receipts, rids = [], {}
    for rep in fleet.replicas:
        rid = "rid-" + random_id(4)
        rids[rep.key.public.key_id] = rid
        receipts.append(rep.key.sign({"type": "fleet-reserve", "key": KEY, "amount": 300, "reserver": t["governor"], "nonce": "n", "rid": rid,
                                      "binding": {"request_hash": t["request_hash"], "endpoint": "payment-switch", "ticket_id": t["ticket_id"]},
                                      "at": rack.clock.now()}))
    ok, why = ep._fleet_receipts_ok({**t, "reservation": rids, "fleet_receipts": receipts}, rule, params, rack.clock.now())
    assert not ok and why.endswith(".fleet_receipts_short"), why


def test_receipts_are_bound_to_the_request_they_were_minted_for():
    """Real receipts under a ticket for a different request hash: the binding in each receipt names the original
    request and this endpoint, so the replicas' signatures authorize nothing else (audit 30 October 2026)."""
    racks, _ = build_fleet(2)
    rack = racks[0]
    _attacker_answers_commits(rack)
    honest, params = _honest_ticket(rack, amount=300)
    moved = _forged(rack, {"rule": honest["payload"]["rule"], "reservation": honest["payload"]["reservation"],
                           "fleet_receipts": honest["payload"]["fleet_receipts"]}, params)
    ok, why = rack.endpoints["payment-switch"].execute(moved, PAY, params)
    assert not ok and why.endswith(".fleet_receipts_short"), why


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
                           "request_hash": honest["payload"]["request_hash"], "request_id": honest["payload"]["request_id"],
                           "fleet_receipts": honest["payload"]["fleet_receipts"]}, params)
    ok, why = ep.execute(again, PAY, params)
    assert not ok
    assert why.endswith(".request_spent") or why.endswith(".reservation_spent"), why
    assert len(ep.executed) == 1
    # the reservation record refuses on its own: with every other record cleared in process, the honest ticket
    # presented again is stopped by the spent reservation alone
    ep.used_requests.clear(); ep.consumed.clear(); ep.burned.clear()
    ok, why = ep.execute(honest, PAY, params)
    assert not ok and why.endswith(".reservation_spent"), why


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


def test_a_host_that_swallows_commits_cannot_refill_the_cap():
    """The audit's finding: with commits swallowed, the governor's reservations lapse after 300 s and the hourly cap
    refills, so a bare 'committed' from the host let $24,000 through an hour capped at $2,000. Now a bare True is no
    commit: the endpoint moves nothing it cannot verify, and the ledger, not the host, decides what was spent."""
    racks, _ = build_fleet(2)
    rack = racks[0]
    _host_swallows_commits(rack)
    ep = rack.endpoints["payment-switch"]
    moved = 0
    for _ in range(12 * 6):                                  # an hour, a request every 50 s, across many lapse windows
        params = {"amount": 400, "currency": "USD", "destination": "acct-1"}
        r = rack.request(rack.nodes[0], PAY, params)
        if r.get("ok"):
            ok, why = ep.execute(r["ticket"], PAY, params)
            assert not ok and why == reasons.COMMIT_REJECTED, why
            moved += 400 if ok else 0
        rack.tick(50)
        rack.heartbeat()
    assert moved == 0


def test_a_commit_statement_for_another_ticket_or_from_another_signer_is_no_commit():
    """The commit the endpoint acts on must be signed by the governor that minted this ticket and must name it."""
    racks, _ = build_fleet(2)
    rack = racks[0]
    ep = rack.endpoints["payment-switch"]
    first, params = _honest_ticket(rack, amount=300)
    statement = rack.nodes[0].governor.commit_from_endpoint(first)
    assert isinstance(statement, dict) and statement["payload"]["ticket_id"] == first["payload"]["ticket_id"]
    second, params2 = _honest_ticket(rack, amount=300)
    ep.commit = lambda ticket: statement                     # the host replays the first ticket's commit for the second
    ok, why = ep.execute(second, PAY, params2)
    assert not ok and why == reasons.COMMIT_REJECTED, why
    # the statement's own fields are what refuse for a rack-local budget: the same check, without fleet receipts
    assert not ep._commit_verified(second, {**statement, "payload": {**statement["payload"], "ticket_id": second["payload"]["ticket_id"]}}, rack.clock.now())
    third, params3 = _honest_ticket(rack, amount=300)
    other = racks[1].nodes[0].governor                       # another governor's key signs a commit naming this ticket
    ep.commit = lambda ticket: other.key.sign({**statement["payload"], "ticket_id": ticket["payload"]["ticket_id"], "governor": other.chip_id})
    ok, why = ep.execute(third, PAY, params3)
    assert not ok and why == reasons.COMMIT_REJECTED, why
    assert len(ep.executed) == 0


def test_an_endpoint_holding_the_recipient_list_refuses_an_unlisted_recipient_whoever_signed():
    racks, _ = build_fleet(1)
    rack = racks[0]
    _attacker_answers_commits(rack)
    g = rack.nodes[0].governor
    ep = rack.endpoints["messaging"]
    assert ep.install_list("recipient-registry", rack.signed_list("recipient-registry", LISTED_RECIPIENTS))
    params = {"recipient": "anyone@outside.example", "body": "weights part 1"}
    now = rack.clock.now()
    t = {"type": "ticket", "ticket_id": random_id(16), "request_id": "forged", "request_hash": digest(["forged", g.fingerprint, "message.send", params]),
         "action": "message.send",
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
    ep.lists.pop("recipient-registry", None)            # a device that was never given the list (the default now holds it)
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
    env = rack.signed_list("recipient-registry", LISTED_RECIPIENTS + ["attacker"], version=9)
    env.pop("cosignatures", None)
    assert not ep.install_list("recipient-registry", env)
    assert "attacker" not in ep.lists["recipient-registry"]["entries"]   # the list the device holds is the one it was given at bring-up


def test_used_reservations_survive_a_restart():
    racks, _ = build_fleet(2)
    rack = racks[0]
    _attacker_answers_commits(rack)
    honest, params = _honest_ticket(rack, amount=300)
    ep = rack.endpoints["payment-switch"]
    assert ep.execute(honest, PAY, params)[0]
    ep.restart()
    again = _forged(rack, {"rule": honest["payload"]["rule"], "reservation": honest["payload"]["reservation"],
                           "request_hash": honest["payload"]["request_hash"], "request_id": honest["payload"]["request_id"],
                           "fleet_receipts": honest["payload"]["fleet_receipts"]}, params)
    ok, why = ep.execute(again, PAY, params)
    assert not ok and (why.endswith(".request_spent") or why.endswith(".reservation_spent")), why
