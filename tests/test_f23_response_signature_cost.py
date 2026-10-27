# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F23 and adversarial audit 3 (rows 19, 20, 32, 34): the engine budget is priced on the whole path.

F23 found that the overhead benchmark priced only the batched provenance records and left out the per-response release
ticket, which the governor signed with P-384 for every response. Audit 3 measured the result: 88 percent of one engine
at 500-token responses and over 300 percent at 100-token responses, while the sweep still said "pass". The design now
authenticates each release ticket with a MAC under the key the governor shares with its own egress endpoint (only that
egress ever checks it), on the hash engine; action tickets stay P-384 signatures, and the batched records stay signed.
These tests reconcile the counts, keep the old design's figure for comparison, and pin the new full-path load.
"""
from govsim.bench import measured_fabric_auth, roll_call_load, run_full_path


def test_counts_reconcile_on_the_full_path():
    r = run_full_path("rack", responses=100, tokens_per_response=500, actions=0)
    assert r["signatures"] == 100                                   # one provenance record per response
    assert r["release_tickets"] == 100 and r["action_tickets"] == 0
    assert r["verifications"] == 100 and r["releases"] == 100
    assert r["ops"]["ticket_mac"] == 100 and r["ops"].get("ticket", 0) == 0 and r["ops"]["sign"] == 100


def test_action_tickets_are_separated_from_release_tickets():
    r = run_full_path("rack", responses=50, tokens_per_response=500, actions=7)
    assert r["release_tickets"] == 50 and r["action_tickets"] == 7
    assert r["tickets"] == 57


def test_at_100_tokens_the_full_path_now_fits_and_the_old_design_did_not():
    r = run_full_path("rack", responses=100, tokens_per_response=100, actions=0)
    assert r["engine_utilization_full_path_pct"] < 50.0, r
    assert r["engine_utilization_signed_release_pct"] > 100.0, r        # what audit 3 measured


def test_the_roll_call_at_72_members_fits_with_the_fabric_the_model_uses():
    assert measured_fabric_auth()["fabric_sign"] == 0                   # roster traffic is MACed in the model
    assert roll_call_load(72, fabric_auth="sign")["engine_pct"] > 100.0  # the signed design audit 3 priced
    assert roll_call_load(72, fabric_auth="mac")["engine_pct"] < 50.0
