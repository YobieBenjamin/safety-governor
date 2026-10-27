# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F26 (external audit): governance independence and recourse as explicit obligations.

Before the fix, one organization holding three of five keys could sign a policy that loosens a protected
rule and the chip accepted three valid signatures, because the quorum counts keys, not independent parties.
The fix adds an OPTIONAL quorum across enrolled principal classes: when on, a change signed by several keys
of ONE class is rejected and a change spanning distinct classes is accepted; default behaviour is unchanged.
The docs now carry the independence and recourse obligations that constrain the public claim.

These checks fail on the pre-fix source (no across-class quorum, obligations absent) and pass after."""
from pathlib import Path

from govsim import reasons
from govsim.crypto import SigningKey, digest
from govsim.policy import make_policy, sign_policy, verify_policy

ROOT = Path(__file__).resolve().parents[1]


def _five_keys():
    return [SigningKey.generate() for _ in range(5)]


def _image(keys, *, class_quorum, classes, version=1):
    now = 1000.0
    return make_policy(
        version=version, issued_at=now, expires_at=now + 86400,
        governance_keys=[k.public for k in keys], threshold=3,
        approver_keys={}, heartbeat_key=keys[0].public, publisher_keys=[keys[0].public],
        reference_values=[], endpoints=[], budget_owners={}, rules=[], assumptions=[],
        governance_classes=classes, governance_class_quorum=class_quorum,
    )


def _classes(keys):
    # Three keys held by org-A, two by org-B: a realistic "one org holds the quorum" enrolment.
    return {keys[0].public.hex: "org-A", keys[1].public.hex: "org-A", keys[2].public.hex: "org-A",
            keys[3].public.hex: "org-B", keys[4].public.hex: "org-B"}


def _trusted(keys, *, class_quorum, classes):
    return {"keys": [k.public.hex for k in keys], "threshold": 3,
            "governance_classes": classes, "governance_class_quorum": class_quorum}


def test_default_off_three_keys_of_one_org_still_commit():
    # Default behaviour (class quorum 0) is unchanged: three valid signatures pass, as before.
    keys = _five_keys()
    img = _image(keys, class_quorum=0, classes={})
    signed = sign_policy(img, keys[:3])        # three org-A keys
    ok, why = verify_policy(signed, trusted=_trusted(keys, class_quorum=0, classes={}))
    assert ok and why == reasons.OK


def test_across_class_quorum_rejects_a_single_org_quorum():
    keys = _five_keys()
    classes = _classes(keys)
    img = _image(keys, class_quorum=2, classes=classes)
    signed = sign_policy(img, keys[:3])        # three keys, all org-A: a valid 3-of-5 by count, one class
    ok, why = verify_policy(signed, trusted=_trusted(keys, class_quorum=2, classes=classes))
    assert not ok and why == reasons.POLICY_CLASS_QUORUM


def test_across_class_quorum_accepts_a_cross_class_quorum():
    keys = _five_keys()
    classes = _classes(keys)
    img = _image(keys, class_quorum=2, classes=classes)
    signed = sign_policy(img, [keys[0], keys[1], keys[3]])    # two org-A, one org-B: spans two classes
    ok, why = verify_policy(signed, trusted=_trusted(keys, class_quorum=2, classes=classes))
    assert ok and why == reasons.OK


def test_across_class_quorum_enforced_end_to_end_through_the_governor():
    # Through a real rack: with the class quorum in force, a single-org quorum change is refused and a
    # cross-class one commits.
    from govsim.cluster import build_rack
    keys_by_hex = None
    rack = build_rack(1, "rack")
    rack.bring_up()
    classes = {rack.governance[0].public.hex: "org-A", rack.governance[1].public.hex: "org-A",
               rack.governance[2].public.hex: "org-A", rack.governance[3].public.hex: "org-B",
               rack.governance[4].public.hex: "org-B"}
    # First, commit an edition that turns the across-class quorum on (signed by the bootstrap quorum, which
    # here spans both orgs so it satisfies the rule it installs).
    img = rack.make_policy_image(rack.policy_version + 1, governance_classes=classes, governance_class_quorum=2)
    rack.policy_version += 1
    signed = sign_policy(img, [rack.governance[0], rack.governance[1], rack.governance[3]])
    res = rack.change_epoch(signed)
    assert res["committed"], res

    # Now a change signed by three org-A keys only: rejected, the old edition stands.
    before = rack.nodes[0].governor.epoch
    bad = rack.make_policy_image(rack.policy_version + 1, governance_classes=classes, governance_class_quorum=2)
    rack.policy_version += 1
    bad_signed = sign_policy(bad, [rack.governance[0], rack.governance[1], rack.governance[2]])
    res_bad = rack.change_epoch(bad_signed)
    assert not res_bad["committed"]
    assert rack.nodes[0].governor.epoch == before    # nothing loosened

    # A cross-class change commits.
    good = rack.make_policy_image(rack.policy_version, governance_classes=classes, governance_class_quorum=2)
    good_signed = sign_policy(good, [rack.governance[0], rack.governance[3], rack.governance[4]])
    res_good = rack.change_epoch(good_signed)
    assert res_good["committed"], res_good


# ---- docs obligations ----

def test_docs_carry_the_independence_and_recourse_obligations():
    d18 = (ROOT / "docs/18-viability-and-open-questions.md").read_text(encoding="utf-8").lower()
    assert "counting keys is not independence" in d18
    for obligation in ("principal class", "custody", "emergency authority", "rotation",
                       "compromise recovery", "challengeable", "security-weakening",
                       "authenticated", "checkpoint retention", "contest"):
        assert obligation in d18, obligation
    d05 = (ROOT / "docs/05-threat-model.md").read_text(encoding="utf-8").lower()
    assert "counting keys is not independence" in d05
