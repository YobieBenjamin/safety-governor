# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""W1, the origin gate: weights sealed to governed hardware, the key released by the governor (docs/18 question 20).
The experiment's checks, run small. ``python -m govsim.origin_gate --write`` runs them with the cost measurement."""
import pytest

from govsim import origin_gate


@pytest.fixture(scope="module")
def results():
    return origin_gate.checks(mib=1)


def test_every_origin_gate_check_holds(results):
    failed = [(n, d) for n, ok, d in results if not ok]
    assert not failed, failed


def test_the_run_covers_every_route_to_revocation(results):
    assert set(origin_gate.checks.stops) >= {"edition drops the model", "GPU revoked", "governor halts",
                                              "governor silent, no renewal", "edition drops the model, push switched off"}
