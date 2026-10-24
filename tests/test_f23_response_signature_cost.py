# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F23: the engine budget must include the per-response release-ticket signature.

The external audit found that the H9 benchmark calls ``sign_output()`` and prices the batched provenance-record
signatures, but never follows the real response-release path. On that path the verified runtime requests a release
ticket for every response and the governor SIGNS every ticket (counted in ``ops["ticket"]``, not ``ops["sign"]``).
Those per-response release tickets are per-item capabilities and cannot be batched under one Merkle root the way the
records are. Including them, the modeled engine load is well over the advertised ~34 percent at 100 tokens/response.

These tests drive the full path at two response sizes, reconcile the operation counts, and pin that the reported
utilization includes the release-ticket signatures, so it is strictly higher than the batched-record-only figure.
"""
from govsim.bench import run_full_path


def test_counts_reconcile_on_the_full_path():
    r = run_full_path("rack", responses=100, tokens_per_response=500, actions=0)
    # one provenance record signed per response; one release ticket minted (signed) per response; one release each
    assert r["signatures"] == 100
    assert r["release_tickets"] == 100
    assert r["tickets"] == r["release_tickets"] + r["action_tickets"] == 100
    assert r["verifications"] == 100 and r["releases"] == 100
    # the governor's ticket op count is exactly the release tickets (no actions here)
    assert r["ops"]["ticket"] == 100 and r["ops"]["sign"] == 100


def test_action_tickets_are_separated_from_release_tickets():
    r = run_full_path("rack", responses=50, tokens_per_response=500, actions=7)
    assert r["release_tickets"] == 50 and r["action_tickets"] == 7
    assert r["tickets"] == 57


def test_utilization_includes_release_tickets_and_is_strictly_higher():
    for toks in (100, 500):
        r = run_full_path("rack", responses=100, tokens_per_response=toks, actions=0)
        # the full-path figure must exceed the records-only figure by the release-ticket signatures it adds
        assert r["engine_utilization_full_path_pct"] > r["engine_utilization_records_only_pct"], (toks, r)
        assert r["release_ticket_signatures"] > 0


def test_at_100_tokens_the_full_path_exceeds_one_engine():
    r = run_full_path("rack", responses=100, tokens_per_response=100, actions=0)
    # the honest load at short responses is well over one engine, not the advertised ~34 percent
    assert r["engine_utilization_full_path_pct"] > 100.0, r
    # and the old records-only figure is the ~34 percent that hid the release tickets
    assert 25.0 < r["engine_utilization_records_only_pct"] < 50.0, r
