# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F04 (external audit): the beneficiary registry was declared on the small-payment path but never enforced.

``payments.transfer.small`` checked the amount and the currency, not the payee. Its ``inputs=["beneficiary-registry"]``
performed no lookup and the payment endpoint's device-check list was empty, so a 100 USD transfer to an unlisted
"attacker-new-account" was ticketed and executed on the auto path. The register row says a new beneficiary is a hold;
nothing implemented it. These checks fail on the pre-fix source and pass after it."""
from govsim import reasons
from govsim.cluster import build_rack


def _pay(rack, node, amount, destination):
    return rack.request(node, "payments.transfer", {"amount": amount, "currency": "USD", "destination": destination})


def test_a_new_beneficiary_is_held_while_a_listed_one_still_works(rack1):
    node = rack1.nodes[0]
    listed = _pay(rack1, node, 100, "acct-1")
    assert listed["ok"] and listed["ticket"]["payload"]["rule"] == "payments.transfer.small"   # listed payee: the auto lane
    new = _pay(rack1, node, 100, "attacker-new-account")
    assert not new["ok"] and new["why"] == reasons.GATE_HELD and new["cause"] == reasons.GATE_BENEFICIARY_UNLISTED
    assert "ticket" not in new                                   # never the auto path for an unknown payee


def test_the_unlisted_payee_never_reaches_an_endpoint_as_an_auto_ticket(rack1):
    node = rack1.nodes[0]
    new = _pay(rack1, node, 100, "attacker-new-account")
    assert not new["ok"]
    g = node.governor
    # no auto ticket was minted for this request; only the hold was logged
    assert not any(e["data"].get("request_hash") == new["request_hash"] for e in g.log.entries("gate.ticket"))
    assert g.log.has("gate.hold", request_hash=new["request_hash"])


def test_a_stale_beneficiary_registry_fails_closed(rack1):
    node = rack1.nodes[0]
    g = node.governor
    # reinstall the beneficiary registry already expired; a listed payee can no longer be admitted from it
    assert g.install_list("beneficiary-registry", rack1.signed_list("beneficiary-registry", ["acct-1"], expires_in_s=-1))
    r = _pay(rack1, node, 100, "acct-1")
    assert not r["ok"] and r["why"] == reasons.GATE_BENEFICIARY_NO_REGISTRY
