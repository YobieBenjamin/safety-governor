# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F05 (external audit): turning on human approval silently turned off payer consent.

With both ``payer_confirm_payments`` and ``sandbox`` on, the small-payment rule kept its payer-confirmation
requirement but became a human-mode rule, and the request handler skipped ``_payer_confirmed`` in human mode. A hold
was created with no payer signature, the operator quorum approved, and ``_cmd_approve`` minted the ticket without ever
checking payer consent. The fix makes payer consent and operator approval SEPARATE conjunctive predicates: the payer's
request-bound confirmation is required even for a human-mode rule, kept with the hold, and revalidated before the
ticket is minted. These checks fail on the pre-fix source and pass after it."""
from govsim import reasons
from govsim.cluster import build_rack


def _rack(sandbox, payer):
    r = build_rack(1, "rack", policy_kw={"sandbox": sandbox, "payer_confirm_payments": payer})
    r.bring_up()
    r.nodes[0].governor.install_list("customer-registry", r.customer_registry_list())
    return r, r.nodes[0]


def test_reference_small_payment_needs_no_payer_key():
    """sandbox off, payer-confirm off: the reference behaviour is unchanged."""
    r, node = _rack(sandbox=False, payer=False)
    assert r.pay(node, 100, "alice-123", confirm_as=None)["ok"]


def test_auto_rule_with_payer_confirm_requires_the_payer_key():
    """sandbox off, payer-confirm on: the auto lane needs the payer's own key (the EXPERIMENT-CUSTOMER-CONFIRMATION behaviour)."""
    r, node = _rack(sandbox=False, payer=True)
    assert not r.pay(node, 100, "alice-123", confirm_as=None)["ok"]
    assert r.pay(node, 100, "alice-123", confirm_as="alice-123")["ok"]


def test_human_rule_without_payer_confirm_mints_on_quorum():
    """sandbox on, payer-confirm off: the ordinary human lane still releases on an operator quorum."""
    r, node = _rack(sandbox=True, payer=False)
    g = node.governor
    held = r.pay(node, 100, "alice-123", confirm_as=None)
    assert held["why"] == reasons.GATE_HELD
    r.clock.advance(61.0)                                   # past the override latency floor
    for k in r.approvers["sandbox"][:2]:
        res = r.approve(g, held["hold_id"], held["request_hash"], k)
    assert res["ok"] and "ticket" in res


def test_sandbox_plus_payer_confirm_does_not_let_operator_quorum_alone_mint():
    """sandbox on, payer-confirm on, NO payer signature: there must be no mintable path. The pre-fix code created a
    hold the operator quorum could then approve into a ticket; the fix denies the request outright, so the operator
    quorum has nothing to act on."""
    r, node = _rack(sandbox=True, payer=True)
    g = node.governor
    res = r.pay(node, 100, "alice-123", confirm_as=None)
    assert not res["ok"] and res["why"].startswith(reasons.GATE_PAYER_UNCONFIRMED)
    assert "hold_id" not in res and not g.holds                 # operator quorum alone cannot conjure a ticket


def test_sandbox_plus_payer_confirm_permits_the_path_with_a_current_payer_confirmation():
    """Both on, payer confirmation present: the request holds for a human, and the operator quorum releases it only
    after the kept payer consent is revalidated."""
    r, node = _rack(sandbox=True, payer=True)
    g = node.governor
    held = r.pay(node, 100, "alice-123", confirm_as="alice-123", confirm_ttl_s=10_000.0)
    assert held["why"] == reasons.GATE_HELD and held["hold_id"] in g.holds
    assert g.holds[held["hold_id"]]["payer_confirm"]["account"] == "alice-123"
    r.clock.advance(61.0)                                       # past the latency floor; the confirmation is still live
    for k in r.approvers["sandbox"][:2]:
        res = r.approve(g, held["hold_id"], held["request_hash"], k)
    assert res["ok"] and "ticket" in res


def test_sandbox_plus_payer_confirm_forces_reauthorization_when_the_confirmation_expires_in_the_hold():
    """Both on, but the payer confirmation expires while the hold waits: the operator quorum cannot release it; the
    specified reauthorization is forced."""
    r, node = _rack(sandbox=True, payer=True)
    g = node.governor
    held = r.pay(node, 100, "alice-123", confirm_as="alice-123", confirm_ttl_s=30.0)
    assert held["why"] == reasons.GATE_HELD
    r.clock.advance(61.0)                                       # past the floor AND past the confirmation's 30s expiry
    for k in r.approvers["sandbox"][:2]:
        res = r.approve(g, held["hold_id"], held["request_hash"], k)
    assert not res["ok"] and res["why"].endswith(".expired_reauthorize")
    assert held["hold_id"] in g.holds                          # not released: it awaits a fresh payer confirmation
