# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""CONTRACT-ZERO-PER-TOKEN-OVERHEAD: zero governor work per token, one lookup per transfer, one signature per response.
The firmware's share of GPU time is the overhead that matters for an action path; the
signing engine runs beside the GPU and only has to keep up. The silicon measurement
replaces the model; these tests pin the model's shape and its honest arithmetic, with the
signature priced at OpenTitan's published OTBN cycle count rather than at a wish."""
from govsim.bench import BATCH_WINDOW_S, OTBN_CLOCK_HZ, OTBN_P384_SIGN_CYCLES, SIGN_S, run


def test_no_per_token_work_and_firmware_overhead_is_negligible():
    r = run("rack", gpus=2, requests=200, tokens_per_request=500, actions=20)
    assert r["ops"].get("output_bytes", 0) == 0 or r["tier"] == "integrated"
    assert r["ops"]["sign"] == 200
    assert r["ops"]["ticket"] == 20
    assert r["firmware_overhead_pct"] < 0.1, r


def test_work_scales_with_responses_and_actions_not_tokens():
    a = run("rack", gpus=2, requests=100, tokens_per_request=100, actions=10)
    b = run("rack", gpus=2, requests=100, tokens_per_request=10_000, actions=10)
    assert a["ops"]["sign"] == b["ops"]["sign"]
    assert a["ops"]["ticket"] == b["ops"]["ticket"]
    assert a["firmware_seconds"] == b["firmware_seconds"]


def test_integrated_tier_hashes_at_line_rate_with_no_firmware_time():
    r = run("integrated", gpus=2, requests=100, tokens_per_request=500, actions=5)
    assert r["ops"]["output_bytes"] > 0
    assert r["firmware_overhead_pct"] < 0.1, r


def test_signature_cost_is_the_published_otbn_figure_not_a_wish():
    assert OTBN_P384_SIGN_CYCLES == 1_697_985 and OTBN_CLOCK_HZ == 100e6
    assert abs(SIGN_S - 0.017) < 0.0005
    assert BATCH_WINDOW_S > SIGN_S       # a window shorter than the signature cannot be honoured


def test_per_response_signing_cannot_keep_up_on_an_otbn_without_batching():
    """Eight slots on one chip at 100-token responses: one signature per response would need
    the engine 272 percent of the time. One signature per 50 ms window caps it at 34 percent
    whatever the load, which is why docs/04 §9 batches. The model shows the shortfall rather
    than hiding it."""
    r = run("rack", gpus=2, requests=100, tokens_per_request=100, actions=0)
    assert r["engine_utilization_unbatched_pct"] > 100.0, r
    assert r["engine_utilization_pct"] < 50.0, r
    assert r["signatures_batched"] <= r["gpu_seconds"] / BATCH_WINDOW_S + 1e-9
    assert r["record_latency_s"] < 0.1
