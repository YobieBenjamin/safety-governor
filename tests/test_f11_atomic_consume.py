# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F11: at-most-once endpoint execution must not rest on an unstated single-thread assumption.

The external audit found that for one valid unbudgeted ticket, two callers could both complete
admit() before either wrote the consumed set; both then burned the same entry and both appended an
effect, because an unbudgeted ticket has no reservation to spend and there was no central single-use
record. The fix states the concurrency contract and makes admission plus durable consumption an
atomic compare-and-set at the endpoint, backed by a central single-use record at the governor so the
at-most-once guarantee survives an endpoint that loses its burn before it learns the commit outcome.
"""
import threading

from govsim import reasons
from govsim.cluster import build_rack
from govsim.crypto import digest

BIG = {"output_queries": 10 ** 6, "output_bytes": 10 ** 12}
TID = "unbudgeted-msg-1"
PARAMS = {"recipient": "recipient-a", "body": "status update"}   # a listed recipient: the messaging endpoint holds the registry


def setup():
    """A rack, its messaging endpoint, and a valid unbudgeted ``message.send`` ticket (no reservation)."""
    r = build_rack(1, "rack", rng_seed=7, policy_kw={**BIG})
    r.bring_up()
    r.heartbeat()
    node = r.nodes[0]
    g = node.governor
    ep = r.endpoints["messaging"]
    now = r.clock.now()
    payload = {"type": "ticket", "ticket_id": TID, "request_hash": digest(["rid", g.fingerprint, "message.send", PARAMS]),
               "request_id": "rid", "action": "message.send", "params_digest": digest(PARAMS), "measurement": g.fingerprint,
               "rule": "message.send.listed", "policy_epoch": g.epoch, "endpoint": "messaging",
               "budget_key": None, "reservation": None, "budget_owner": None, "governor": g.chip_id,
               "issued_at": g.mono(), "valid_from": now, "expires_at": now + 300}
    ticket = g.key.sign(payload)
    # Built here rather than through a request, so record it the way the governor's mint does: a commit is accepted
    # only for a ticket in the governor's minted record (adversarial audit 3).
    g.minted_tickets[TID] = {"digest": digest(payload), "expires_at": payload["expires_at"]}
    assert payload["reservation"] is None          # this ticket has no budget reservation to make it single-use
    return r, node, g, ep, ticket


def test_concurrent_dispatch_lets_exactly_one_caller_cross_the_effect_boundary():
    r, node, g, ep, ticket = setup()

    # A seam that forces the dangerous interleaving deterministically: both callers finish admit() before
    # either burns the ticket, exactly the window the audit flagged.
    barrier = threading.Barrier(2)
    real_admit = ep.admit

    def admit_then_wait(tkt, action, params, now):
        out = real_admit(tkt, action, params, now)
        barrier.wait()
        return out

    ep.admit = admit_then_wait
    results: dict[str, tuple] = {}

    def run(name):
        results[name] = ep.execute(ticket, "message.send", PARAMS)

    threads = [threading.Thread(target=run, args=(n,)) for n in ("A", "B")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ep.admit = real_admit

    oks = sorted(v[0] for v in results.values())
    assert oks == [False, True]                                     # exactly one owner, one loser
    loser = [v[1] for v in results.values() if not v[0]][0]
    assert loser == reasons.TICKET_REPLAY
    assert len([e for e in ep.executed if e["ticket"] == TID]) == 1  # exactly one effect crossed
    assert g.committed_tickets.get(TID) is not None                  # the central single-use record exists


def test_central_single_use_blocks_a_second_commit_after_a_lost_burn():
    r, node, g, ep, ticket = setup()
    ok, why = ep.execute(ticket, "message.send", PARAMS)
    assert ok and why == reasons.OK
    assert len([e for e in ep.executed if e["ticket"] == TID]) == 1
    assert g.committed_tickets.get(TID) is not None

    # Recovery after consumption but before the outcome is known: the endpoint comes back having lost the
    # burn (the consumed write had not reached NVM), and re-presents the ticket. A local consumed flag can
    # no longer be the only guard; the governor's central single-use record refuses the second commit.
    ep.consumed.clear()
    ep.burned.clear()        # F33: the endpoint's second record is lost as well, so only the central record is left
    ep.used_requests.clear() # and the request record, written in the same save (30 October 2026), is lost with them
    ok2, why2 = ep.execute(ticket, "message.send", PARAMS)
    assert not ok2 and why2 == reasons.COMMIT_REJECTED
    assert len([e for e in ep.executed if e["ticket"] == TID]) == 1   # still exactly one effect
    assert g.log.has("gate.commit_rejected", ticket_id=TID, why=reasons.TICKET_REPLAY)
