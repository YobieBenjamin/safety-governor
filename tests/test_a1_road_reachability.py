# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""EXPERIMENT-ROAD-REACHABILITY (govsim/road_reachability.py): a rulebook reachability audit. Every road-opening action must be non-auto;
the one open-auto road in the reference rulebook (finding EXPERIMENT-ROAD-REACHABILITY-a, model.export.70b) is pinned so a change is noticed."""
from govsim import road_reachability


def test_audit_works_and_pins_the_one_finding():
    failed = [(n, d) for n, ok, d in road_reachability.checks() if not ok]
    assert not failed, failed
    assert road_reachability.checks.ref_open == ["model.export.70b"]
