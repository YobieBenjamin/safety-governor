"""P3b, the containment rate (govsim/containment.py): how little can leave a governed rack under a tight policy.
The defensive side of the replication question; companion to test_h10_leakage.py (P3)."""
from govsim import containment


def test_every_containment_check_holds():
    failed = [(n, d) for n, ok, d in containment.checks() if not ok]
    assert not failed, failed


def test_a_tighter_budget_is_a_lower_ceiling():
    tight = containment.egress_ceiling(4_096, 10, 4_096, sandbox=True)
    loose = containment.egress_ceiling(50 << 20, 100_000, 16 << 20, sandbox=False)
    assert tight["ceiling_bytes_per_hour"] < loose["ceiling_bytes_per_hour"]
    assert not tight["off_roster_flow_opened"] and not loose["off_roster_flow_opened"]
