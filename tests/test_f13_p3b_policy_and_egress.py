# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F13: EXPERIMENT-CONTAINMENT must measure the policy it installed, at the egress boundary, not signing calls.

The external audit found that ``egress_ceiling`` built the rack (whose constructor already signed and loaded a
policy), then changed ``r.policy_kw`` and called ``bring_up()``, which does not reload the policy. Both the named
"sandbox" and "busy-service" cases therefore ran the reference rulebook, and the recorded 6,135 and 26,200 B/h were
the loop and default-policy values, not the named policies. Worse, the figure counted successful ``sign_output``
calls, which record a provenance signature and release nothing.

These tests pin the honest behaviour: three deliberately distinct policies, each read back from the live governor
and asserted before measuring; the tightest case never delivers more than its signed byte allowance; and a signature
with no egress release moves zero bytes.
"""
from govsim import containment
from govsim.cluster import build_rack


def test_three_distinct_policies_are_actually_installed_and_read_back():
    a = containment.egress_ceiling(4_096, 10, 4_096, sandbox=True)
    b = containment.egress_ceiling(200_000, 50, 1 << 20, sandbox=False, **containment.BOUNDED_MSG)
    c = containment.egress_ceiling(50 << 20, 100_000, 16 << 20, sandbox=False, **containment.BOUNDED_MSG)

    # the live limits are the ones each case asked for, read back from the governor's loaded policy
    assert a["installed"]["output_bytes"] == 4_096 and a["installed"]["output_queries"] == 10
    assert b["installed"]["output_bytes"] == 200_000 and b["installed"]["output_queries"] == 50
    assert c["installed"]["output_bytes"] == 50 << 20 and c["installed"]["output_queries"] == 100_000
    assert a["installed"]["sandbox"] is True and b["installed"]["sandbox"] is False

    # three distinct policies give three distinct measured ceilings (the old bug returned the reference value thrice)
    ceilings = {a["sustained_bytes_per_hour"], b["sustained_bytes_per_hour"], c["sustained_bytes_per_hour"]}
    assert len(ceilings) == 3, ceilings


def test_the_4096_byte_case_never_exceeds_its_signed_allowance():
    a = containment.egress_ceiling(4_096, 10, 4_096, sandbox=True)
    # measured at the boundary (delivered), never above the signed byte budget the policy set
    assert a["sustained_bytes_per_hour"] <= 4_096, a["sustained_bytes_per_hour"]
    assert a["installed"]["output_bytes"] == 4_096
    # the one-time burst is reported separately and is NOT folded into the per-hour figure
    assert a["burst_bytes"] == 4_096
    assert a["ceiling_bytes_per_hour"] == a["sustained_bytes_per_hour"]


def test_a_signature_with_no_release_contributes_zero_delivered_bytes():
    r = build_rack(1, "rack", policy_kw={"output_bytes": 200_000, "output_queries": 50, "unpresented_bytes": 1 << 20})
    r.bring_up()
    node = r.nodes[0]
    # record a provenance signature over some bytes, but never request a release
    rec = r.sign_output(node, "response", b"z" * 8_000)
    assert rec["ok"], rec
    # nothing left the egress boundary: signing is not delivery
    assert node.egress.bytes_delivered == 0


def test_measured_ceiling_matches_the_installed_byte_budget_not_the_reference():
    # the sandbox budget (4,096) and the busy budget (50 MiB) must produce ceilings an order of magnitude apart;
    # the old code ran the reference policy for both, so both came back near the reference loop value
    tight = containment.egress_ceiling(4_096, 10, 4_096, sandbox=True)
    loose = containment.egress_ceiling(50 << 20, 100_000, 16 << 20, sandbox=False, **containment.BOUNDED_MSG)
    assert loose["sustained_bytes_per_hour"] > 1000 * tight["sustained_bytes_per_hour"]
