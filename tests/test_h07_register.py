# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""H7: the assumptions register is complete for the deployment. Falsified if a policy whose
rules rely on an input with no register row loads."""
from govsim import reasons
from govsim.policy import check_register, sign_policy


def test_policy_missing_a_register_row_does_not_load(rack1):
    g = rack1.nodes[0].governor
    image = sign_policy(rack1.make_policy_image(rack1.policy_version + 1, drop_register_row="protected-sites"), rack1.governance[:3])
    assert check_register(image) == ["protected-sites"]
    r = g.command("POLICY_PROPOSE", {"image": image})
    assert not r["ok"] and r["why"] == reasons.POLICY_REGISTER_INCOMPLETE


def test_shipped_policy_is_complete(rack1):
    assert check_register(rack1.policy) == []


def test_every_row_has_every_column(rack1):
    for row in rack1.policy["assumptions"]:
        for col in ("input", "authority", "freshness", "on_conflict", "independence", "unchecked"):
            assert row.get(col), (row.get("input"), col)


def test_a_stale_list_is_a_denial_not_a_pass(rack1):
    node = rack1.nodes[0]
    g = node.governor
    g.install_list("protected-sites", rack1.signed_list("protected-sites", [], expires_in_s=-1))
    r = rack1.request_with_witness(node, "strike", {"target": [37.0, -122.0], "munition": "gbu-39"})
    assert not r["ok"] and r["why"].endswith("list_unavailable")


def test_an_input_named_only_by_a_constraint_still_needs_a_row(rack1):
    """The register check derives inputs from what a rule does, not from what its author declares."""
    g = rack1.nodes[0].governor
    image = rack1.make_policy_image(rack1.policy_version + 1, drop_register_row="protected-sites")
    for rule in image["rules"]:
        rule["inputs"] = [i for i in rule["inputs"] if i != "protected-sites"]
    for ep in image["endpoints"]:
        ep["inputs"] = [i for i in ep["inputs"] if i != "protected-sites"]
    image = sign_policy(image, rack1.governance[:3])
    assert check_register(image) == ["protected-sites"]
    r = g.command("POLICY_PROPOSE", {"image": image})
    assert not r["ok"] and r["why"] == reasons.POLICY_REGISTER_INCOMPLETE


def test_observer_lane_and_budget_key_are_inputs_too(rack1):
    from govsim.policy import rule_inputs
    strike = next(r for r in rack1.policy["rules"] if r["id"] == "strike")
    small = next(r for r in rack1.policy["rules"] if r["id"] == "payments.transfer.small")
    assert "observer-verdict" in rule_inputs(strike) and "protected-sites" in rule_inputs(strike)
    assert "pay-usd-hourly" in rule_inputs(small)
