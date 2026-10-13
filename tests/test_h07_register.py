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
