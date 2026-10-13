"""H9: zero governor work per token, one lookup per transfer, one signature per response,
modelled overhead under one percent for the reference workload. The silicon measurement
replaces the model; this test pins the model's shape so a change in the design that adds
per-token work is caught."""
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
    assert abs(a["governor_seconds"] - b["governor_seconds"]) < 1e-3


def test_integrated_tier_hashes_at_line_rate_with_no_firmware_time():
    r = run("integrated", gpus=2, requests=100, tokens_per_request=100, actions=5)
    assert r["ops"]["output_bytes"] > 0
    assert r["overhead_pct"] < 1.0
