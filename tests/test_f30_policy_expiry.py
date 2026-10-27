# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F30: policy expiry is checked per request, not only at load and at tick.

Covers VEC-0024. The documented contract (docs/18 and the 2026-10-22 fact-check) says expiry is checked at
commit and boot only. This test pins the gap between that contract and the code, and the fix closes it.
Before the fix a request after the edition's expiry was admitted when no tick had run, and a payment executed.
These tests fail on the code before the fix and pass after it."""
from govsim import reasons
from govsim.cluster import build_rack

PAY = {"amount": 100, "currency": "USD", "from_account": "alice-123", "destination": "recipient-a"}


def _expired_rack():
    r = build_rack(1, "rack")
    r.bring_up()
    node = r.nodes[0]
    g = node.governor
    r.clock.set(g.policy["expires_at"] + 10)     # the edition has expired; no tick runs
    r.heartbeat()
    r.install_lists(node)
    r.attest(node)
    r.load_model(node)
    r.heartbeat()
    return r, node, g


def test_a_request_after_policy_expiry_is_refused_without_a_tick():
    r, node, g = _expired_rack()
    res = r.request(node, "payments.transfer", PAY)
    assert res["ok"] is False and res["why"] == reasons.POLICY_EXPIRED
    assert len(r.endpoints["payment-switch"].executed) == 0


def test_an_endpoint_refuses_an_expired_edition_on_its_own_clock():
    # Mint a ticket while the edition is live. Then let the edition expire. The endpoint must refuse it,
    # even though the ticket itself is still inside its own window.
    r = build_rack(1, "rack")
    r.bring_up()
    node = r.nodes[0]
    g = node.governor
    r.install_lists(node)
    r.attest(node)
    r.load_model(node)
    r.heartbeat()
    res = r.request(node, "payments.transfer", PAY)
    assert res["ok"], res
    ep = r.endpoints["payment-switch"]
    r.clock.set(g.policy["expires_at"] + 1)
    ok, why = ep.admit(res["ticket"], "payments.transfer", PAY, r.clock.now())   # the admit check, on its own
    assert not ok and why == reasons.POLICY_EXPIRED
    ok, why = ep.execute(res["ticket"], "payments.transfer", PAY)                  # the full path refuses too
    assert not ok
    assert len(ep.executed) == 0
