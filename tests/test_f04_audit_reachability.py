# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F04 (external audit): the A1 reachability audit called any enum a destination boundary.

classify() labelled a rule "confined" if any constraint field had in / in_list / not_in_list, so a
`currency in [USD]` enum or a `munition in [...]` enum made an unbounded payment or strike rule look
confined, and a `not_in_list` denylist complement did the same. Confinement must instead require a signed
allowlist of the parties that may RECEIVE the effect, and an action whose effect creates new authority (a
credential, an account, a forward to another service) is unconfined even behind a destination allowlist.

These checks fail on the pre-fix source and pass after it."""
from govsim import reasons, road_reachability
from govsim.cluster import MODEL_70B, build_rack
from govsim.policy import make_rule


def test_an_unrelated_enum_alone_does_not_confine():
    # currency / product / munition enums name no receiver; they must not confine a world action.
    for field, allowed in (("currency", ["USD"]), ("product", ["widget"]), ("munition", ["gbu-39"])):
        rule = make_rule("enum.only", "payments.transfer", constraints={field: {"in": allowed}}, endpoint="some-switch")
        assert road_reachability.classify(rule) == "open", field


def test_a_denylist_complement_does_not_confine():
    # not_in_list is the complement of a denylist, not an allowlist of receivers.
    rule = make_rule("deny.only", "strike", constraints={"target": {"not_in_list": "protected-sites"}}, endpoint="strike-guidance")
    assert road_reachability.classify(rule) == "open"


def test_a_receiver_allowlist_confines():
    # an in_list / in on a field that names the receiver is what confinement requires.
    recip = make_rule("msg.listed", "message.send", constraints={"recipient": {"in_list": "recipient-registry"}}, endpoint="messaging")
    dest = make_rule("w.own", "weights.write", constraints={"destination": {"in": [MODEL_70B]}})
    assert road_reachability.classify(recip) == "confined"
    assert road_reachability.classify(dest) == "confined"


def test_an_enforced_beneficiary_registry_confines_a_payment_with_only_an_enum():
    # payments.transfer.small carries currency in [USD] (an enum) but also an enforced beneficiary registry (F04).
    # The enum alone would not confine; the registry, now enforced in code, is the receiver allowlist that does.
    rule = make_rule("pay.small", "payments.transfer", constraints={"amount": {"min": 0, "max": 1000}, "currency": {"in": ["USD"]}},
                     endpoint="payment-switch", beneficiary={"registry": "beneficiary-registry", "param": "destination"})
    bare = make_rule("pay.bare", "payments.transfer", constraints={"amount": {"min": 0, "max": 1000}, "currency": {"in": ["USD"]}},
                     endpoint="payment-switch")
    assert road_reachability.classify(rule) == "confined"
    assert road_reachability.classify(bare) == "open"       # same enum, no beneficiary enforcement: unconfined


def test_a_service_that_creates_a_credential_or_forwards_is_new_authority_not_confined():
    # Approving an action that mints a credential or forwards to another service grants reachable authority
    # beyond the named place, so a destination allowlist must NOT fold it into confinement.
    cred = make_rule("cred.issue", "credential.issue", constraints={"destination": {"in": ["holder-a"]}}, endpoint="identity-service")
    fwd = {**make_rule("svc.fwd", "message.send", constraints={"recipient": {"in_list": "recipient-registry"}},
                       endpoint="messaging"), "effect": "create_authority"}   # this message delegates onward to another service
    assert road_reachability.creates_new_authority(cred)
    assert road_reachability.creates_new_authority(fwd)
    assert road_reachability.classify(cred) == "open"
    assert road_reachability.classify(fwd) == "open"


def test_the_payment_confinement_claim_is_backed_by_real_enforcement():
    # The audit may call payments.transfer.small confined only because the external effect is modelled: an
    # unlisted payee is actually held in govsim, not merely declared. Tie the label to the enforcement.
    rack = build_rack(1, "rack")
    rack.bring_up()
    node = rack.nodes[0]
    small = next(r for r in node.governor.policy["rules"] if r["id"] == "payments.transfer.small")
    assert road_reachability.classify(small) == "confined"
    new = rack.request(node, "payments.transfer", {"amount": 100, "currency": "USD", "destination": "attacker-new-account"})
    assert not new["ok"] and new["why"] == reasons.GATE_HELD and new["cause"] == reasons.GATE_BENEFICIARY_UNLISTED


def test_audit_still_pins_exactly_the_one_open_auto_road():
    # The reference rulebook still has exactly one open-auto road, and the full audit still passes.
    failed = [(n, d) for n, ok, d in road_reachability.checks() if not ok]
    assert not failed, failed
    assert road_reachability.checks.ref_open == ["model.export.70b"]
