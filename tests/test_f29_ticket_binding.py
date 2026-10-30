# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F29: a ticket must name exactly one endpoint, and only that endpoint may act on it.

Before this fix an endpoint checked the endpoint field only when the ticket carried a truthy value, so a
ticket with no endpoint (a rule that names none, such as model.export) was accepted by any effector. The
covered vectors are VEC-0005, VEC-0006, VEC-0007, VEC-0008 and VEC-0069. These tests fail on the code before
the fix and pass after it."""
from govsim import reasons
from govsim.cluster import build_rack
from govsim.crypto import digest


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
    ticket = g._mint(digest(["rid", g.fingerprint, "payments.transfer", {"amount": 1}]), "payments.transfer", {"amount": 1}, g.fingerprint, rule, None, r.clock.now(), request_id="rid")
    assert ticket["payload"]["endpoint"] == "payment-switch"
    ok, why = r.endpoints["messaging"].execute(ticket, "payments.transfer", {"amount": 1})
    assert not ok and why == reasons.TICKET_WRONG_ENDPOINT
    assert len(r.endpoints["messaging"].executed) == 0


def test_the_governor_does_not_commit_an_unbound_ticket():
    r, ticket = _rack_with_export_ticket()
    g = r.nodes[0].governor
    assert g.commit_from_endpoint(ticket) is False
    assert ticket["payload"]["ticket_id"] not in g.committed_tickets


# F29, storage path. The two weights rules are bound to the storage path, so the storage grant accepts only a
# weights.write ticket that names the storage endpoint. The grant refuses an unbound ticket and a ticket bound to
# another name. The data-only rules (model.export and compute.extend) never authorise an effect.

def _storage_rack():
    r = build_rack(1, "rack")
    r.bring_up()
    node = r.nodes[0]
    return r, node, node.governor


def _unbound_copy(rule):
    """The same rule with the endpoint field cleared, as it was before the F29 storage fix."""
    return dict(rule, endpoint=None)


def test_the_storage_grant_refuses_a_weights_ticket_with_no_endpoint():
    r, node, g = _storage_rack()
    n = 4096
    params = {"destination": node.model_digest, "model_digest": node.model_digest, "bytes": n}
    rule = _unbound_copy(next(x for x in g.policy["rules"] if x["id"] == "weights.write.own"))
    ticket = g._mint(digest(["rid", g.fingerprint, "weights.write", params]), "weights.write", params, g.fingerprint, rule, None, r.clock.now(), request_id="rid")
    assert ticket["payload"]["endpoint"] is None
    ok, why = g.grant_storage_export(ticket, n)
    assert not ok and why == reasons.TICKET_UNBOUND, why
    ok, _ = node.gpu.transfer("storage", node.model_digest, "out", n)
    assert not ok


def test_the_storage_grant_refuses_a_weights_ticket_bound_to_another_endpoint():
    r, node, g = _storage_rack()
    n = 4096
    params = {"destination": node.model_digest, "model_digest": node.model_digest, "bytes": n}
    rule = dict(next(x for x in g.policy["rules"] if x["id"] == "weights.write.own"), endpoint="payment-switch")
    ticket = g._mint(digest(["rid", g.fingerprint, "weights.write", params]), "weights.write", params, g.fingerprint, rule, None, r.clock.now(), request_id="rid")
    ok, why = g.grant_storage_export(ticket, n)
    assert not ok and why == reasons.TICKET_WRONG_ENDPOINT, why


def test_the_weights_rules_are_bound_to_the_storage_path():
    _, node, g = _storage_rack()
    for rule_id in ("weights.write.own", "weights.write.any"):
        rule = next(x for x in g.policy["rules"] if x["id"] == rule_id)
        assert rule.get("endpoint") == "storage", rule_id


def test_data_only_rules_never_authorise_an_effect():
    r, node, g = _storage_rack()
    params = {"target": "not-a-payment"}
    n = 4096
    for rule_id, action in (("model.export.70b", "model.export"), ("model.export.any", "model.export"),
                            ("compute.extend", "compute.extend")):
        rule = next(x for x in g.policy["rules"] if x["id"] == rule_id)
        assert rule.get("endpoint") is None, rule_id
        ticket = g._mint(digest(["rid", g.fingerprint, action, params]), action, params, g.fingerprint, rule, None, r.clock.now(), request_id="rid")
        for name, ep in r.endpoints.items():
            ok, why = ep.execute(ticket, action, params)
            assert not ok and why == reasons.TICKET_UNBOUND, (rule_id, name)
        ok, why = g.grant_storage_export(ticket, n)
        assert not ok and why == reasons.TICKET_ACTION_MISMATCH, (rule_id, why)
    assert all(len(ep.executed) == 0 for ep in r.endpoints.values())
    ok, _ = node.gpu.transfer("storage", node.model_digest, "out", n)
    assert not ok
