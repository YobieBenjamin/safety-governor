"""H9: zero governor work per token, one lookup per transfer, one signature per response,
modelled overhead under one percent for the reference workload. The silicon measurement
replaces the model; this test pins the model's shape so a change in the design that adds
per-token work is caught. The costs are the budgets in docs/04-specification.md §9, with the
signature charged at its 1 ms budget rather than at a figure nobody has measured."""
from govsim.bench import run


def test_no_per_token_work_and_overhead_under_one_percent():
    r = run("rack", gpus=2, requests=200, tokens_per_request=500, actions=20)
    assert r["ops"].get("output_bytes", 0) == 0 or r["tier"] == "integrated"
    assert "per_token" not in r["ops"]
    assert r["ops"]["sign"] == 200
    assert r["ops"]["ticket"] == 20
    assert r["overhead_pct"] < 1.0, r


def test_work_scales_with_responses_and_actions_not_tokens():
    a = run("rack", gpus=2, requests=100, tokens_per_request=100, actions=10)
    b = run("rack", gpus=2, requests=100, tokens_per_request=10_000, actions=10)
    assert a["ops"]["sign"] == b["ops"]["sign"]
    assert a["ops"]["ticket"] == b["ops"]["ticket"]
    assert a["governor_seconds"] == b["governor_seconds"]


def test_integrated_tier_hashes_at_line_rate_with_no_firmware_time():
    r = run("integrated", gpus=2, requests=100, tokens_per_request=500, actions=5)
    assert r["ops"]["output_bytes"] > 0
    assert r["overhead_pct"] < 1.0, r


def test_short_responses_cost_more_per_response_which_is_why_the_spec_batches():
    """The signature is per response, so the overhead is inversely proportional to response
    length. At 100 tokens per response (50 ms of GPU time) a 1 ms signature is 2 percent, over
    the budget. docs/04-specification.md §9 batches records: an inference server that
    completes N responses inside one window gets one signature for all of them, which is
    the figure that has to hold on real hardware. The model makes the shortfall visible
    rather than hiding it."""
    unbatched = run("rack", gpus=2, requests=100, tokens_per_request=100, actions=0)
    assert unbatched["overhead_pct"] > 1.0, unbatched
    batched = run("rack", gpus=2, requests=100, tokens_per_request=100, actions=0, concurrent_sequences=16)
    assert batched["signatures"] == 7            # ceil(100 / 16)
    assert batched["overhead_pct"] < 1.0, batched
    assert batched["ops"]["sign"] == unbatched["ops"]["sign"]   # the model still signs every response; only the pricing batches
