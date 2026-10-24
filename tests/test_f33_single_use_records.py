# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F33: the single-use check reads a second, separate record of burned tickets.

Covers VEC-0082. In-process writes to the governor's and the endpoint's memory can clear a record. The
endpoint now keeps ``burned`` as well as ``consumed``, written in the same save before the action, and
checks both. The first test shows that clearing one endpoint record does not reopen a ticket; it fails on
the code before the fix. The second test documents the open part: when the endpoint's two records and the
governor's record are all cleared in-process, the same ticket runs again. That rests on the trust assumption
that the host cannot write these records. It is not a software fix."""
from govsim import reasons
from govsim.cluster import build_rack

P = {"target": [10.0, 10.0]}


def _strike_ticket():
    r = build_rack(1, "rack")
    r.bring_up()
    node = r.nodes[0]
    g = node.governor
    rule = next(x for x in g.policy["rules"] if x.get("endpoint") == "strike-guidance")
    ticket = g._mint("rh", "strike", P, g.fingerprint, rule, None, r.clock.now())
    r.clock.advance(rule.get("delay_s", 0.0) + 1.0)     # past the rule's delay, inside the ticket window
    r.heartbeat()
    return r, node, ticket


def test_clearing_the_governor_record_and_one_endpoint_record_does_not_reopen_a_ticket():
    r, node, ticket = _strike_ticket()
    ep = r.endpoints["strike-guidance"]
    g = node.governor
    ep.execute(ticket, "strike", P)                     # the first use burns the ticket, whatever the device checks say
    ep.consumed.clear()                                 # corrupt the endpoint's first record
    g.committed_tickets.clear()                         # and the governor's record; the burned record is still there
    before = len(ep.executed)
    ok, why = ep.execute(ticket, "strike", P)
    assert not ok and why == reasons.TICKET_REPLAY
    assert len(ep.executed) == before


def test_clearing_every_record_reopens_the_ticket_documented_open():
    # Documented open part of F33. This is an in-process write to all three records (two endpoint, one governor).
    r, node, ticket = _strike_ticket()
    ep = r.endpoints["strike-guidance"]
    g = node.governor
    ep.execute(ticket, "strike", P)
    ep.consumed.clear()
    ep.burned.clear()
    g.committed_tickets.clear()
    before = len(ep.executed)
    ep.execute(ticket, "strike", P)
    assert len(ep.executed) == before + 1, "expected the trust-root gap to reproduce; if this fails, the gap has changed"
