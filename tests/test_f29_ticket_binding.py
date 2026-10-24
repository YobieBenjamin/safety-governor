# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F29: a ticket must name exactly one endpoint, and only that endpoint may act on it.

Before this fix an endpoint checked the endpoint field only when the ticket carried a truthy value, so a
ticket with no endpoint (a rule that names none, such as model.export) was accepted by any effector. The
covered vectors are VEC-0005, VEC-0006, VEC-0007, VEC-0008 and VEC-0069. These tests fail on the code before
the fix and pass after it."""
from govsim import reasons
from govsim.cluster import build_rack


def _rack_with_export_ticket():
    r = build_rack(1, "rack")
    r.bring_up()
    node = r.nodes[0]
    res = r.request(node, "model.export", {"target": "not-a-payment"})
    assert res["ok"], res
    return r, res["ticket"]


def test_an_unbound_ticket_is_refused_by_every_effector():
    r, ticket = _rack_with_export_ticket()
    assert ticket["payload"]["endpoint"] is None          # the rule names no endpoint
    params = {"target": "not-a-payment"}
    for name, ep in r.endpoints.items():
        ok, why = ep.execute(ticket, "model.export", params)
        assert not ok and why == reasons.TICKET_UNBOUND, name
    assert all(len(ep.executed) == 0 for ep in r.endpoints.values())


def test_a_ticket_bound_to_another_endpoint_is_refused():
    # A genuine ticket, minted by the governor for the payment rule, must not act at the messaging effector.
    r, _ = _rack_with_export_ticket()
    g = r.nodes[0].governor
    rule = next(x for x in g.policy["rules"] if x.get("endpoint") == "payment-switch")
    ticket = g._mint("rh", "payments.transfer", {"amount": 1}, g.fingerprint, rule, None, r.clock.now())
    assert ticket["payload"]["endpoint"] == "payment-switch"
    ok, why = r.endpoints["messaging"].execute(ticket, "payments.transfer", {"amount": 1})
    assert not ok and why == reasons.TICKET_WRONG_ENDPOINT
    assert len(r.endpoints["messaging"].executed) == 0


def test_the_governor_does_not_commit_an_unbound_ticket():
    r, ticket = _rack_with_export_ticket()
    g = r.nodes[0].governor
    assert g.commit_from_endpoint(ticket) is False
    assert ticket["payload"]["ticket_id"] not in g.committed_tickets
