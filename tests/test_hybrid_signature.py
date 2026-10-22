"""C3: the post-quantum path. A hybrid signature (ECDSA P-384 plus ML-DSA-65) per batch on the one OTBN-class
engine. ML-DSA's cycle count on OTBN is an UNVERIFIED placeholder (see govsim/bench.py), so every result here is
conditional on it, and the tests also hold under a pessimistic multiple of it. Disproof: no window under one
second keeps the engine under 100 percent."""
import pytest

from govsim.bench import (BATCH_WINDOW_S, HYBRID_BATCH_WINDOW_S, HYBRID_SIGN_S, MLDSA65_COST_SOURCED,
                          MLDSA65_SIGN_S, SIGN_S, hybrid_report, run)

# ML-DSA twice as slow on OTBN as the M4 figure, standing in for the long rejection-sampling tail. The factor is
# an assumption, not a measurement: a real tail bound needs a Phase 2 measurement.
HYBRID_PESSIMISM = 2.0


def test_hybrid_costs_both_signatures():
    assert abs(HYBRID_SIGN_S - (SIGN_S + MLDSA65_SIGN_S)) < 1e-12
    r = run("rack", batch_window_s=HYBRID_BATCH_WINDOW_S, hybrid_window_s=HYBRID_BATCH_WINDOW_S)
    assert r["hybrid_engine_utilization_pct"] > r["engine_utilization_pct"]
    assert abs(r["hybrid_engine_utilization_pct"]
               - 100.0 * r["hybrid_signatures_batched"] * HYBRID_SIGN_S / r["gpu_seconds"]) < 1e-9


def test_hybrid_utilisation_matches_sign_time_over_window():
    # window-limited, so utilisation is sign time over window; the bench's printed figures are these values
    r = run("rack")
    assert r["hybrid_engine_utilization_pct"] == pytest.approx(100.0 * HYBRID_SIGN_S / HYBRID_BATCH_WINDOW_S)
    assert r["hybrid_engine_utilization_at_base_window_pct"] == pytest.approx(100.0 * HYBRID_SIGN_S / BATCH_WINDOW_S)
    assert r["hybrid_record_latency_s"] == pytest.approx(HYBRID_BATCH_WINDOW_S + HYBRID_SIGN_S)


def test_hybrid_at_the_classical_window_does_not_keep_up():
    r = run("rack")
    assert r["hybrid_engine_utilization_at_base_window_pct"] > 100.0, r


def test_hybrid_window_keeps_engine_under_100_percent():
    r = run("rack")
    assert HYBRID_BATCH_WINDOW_S < 1.0
    assert r["hybrid_engine_utilization_pct"] < 100.0, r


def test_hybrid_holds_under_pessimistic_ml_dsa_cost():
    sign = SIGN_S + HYBRID_PESSIMISM * MLDSA65_SIGN_S
    r = run("rack", hybrid_sign_s=sign)
    util = r["hybrid_engine_utilization_pct"]
    assert util < 100.0, r
    # computed, not asserted by hand: the slack at the chosen window is 100 - 100*sign/window
    assert 100.0 - util == pytest.approx(100.0 - 100.0 * sign / HYBRID_BATCH_WINDOW_S)
    assert 100.0 - util < 20.0, "the chosen window is tight at 2x; widen it if this stops being so"


def test_a_window_under_one_second_exists_by_search():
    # Search windows below 1 s (10 ms steps) rather than checking one chosen point.
    windows = [w / 100.0 for w in range(1, 100)]
    ok = [w for w in windows if run("rack", gpus=2, requests=20, hybrid_window_s=w)["hybrid_engine_utilization_pct"] < 100.0]
    assert ok, "disproof: no window under one second keeps the engine under 100 percent"
    # the shortest that works is just above the combined sign time, and 250 ms is among them
    assert min(ok) > HYBRID_SIGN_S
    assert min(ok) - HYBRID_SIGN_S < 0.01
    assert HYBRID_BATCH_WINDOW_S in ok


def test_under_one_second_disproof_has_headroom_and_its_latency_cost():
    w, k = 0.999, 8.0
    sign = SIGN_S + k * MLDSA65_SIGN_S
    r = run("rack", hybrid_window_s=w, hybrid_sign_s=sign)
    assert r["hybrid_engine_utilization_pct"] < 100.0, r
    # the price is record latency: a window near 1 s plus the slower signature
    assert r["hybrid_record_latency_s"] == pytest.approx(w + sign)
    assert r["hybrid_record_latency_s"] > 1.0


def test_verdict_text_is_computed_and_carries_the_caveat():
    r = run("rack")
    text = hybrid_report(r)
    assert "did not hold" in text and "cannot keep up" in text and "keeps up" in text
    if not MLDSA65_COST_SOURCED:
        assert "conditional on the unverified" in text
    # and the verdict flips when the numbers do: with a one-second signature no window below 1 s works
    bad = run("rack", hybrid_sign_s=1.5)
    assert bad["hybrid_engine_utilization_pct"] > 100.0
