"""C3: the post-quantum path. A hybrid signature (ECDSA P-384 plus ML-DSA-65) per batch on the one OTBN-class
engine. ML-DSA's cycle count on OTBN is an assumption (see govsim/bench.py), so the test also holds under a
pessimistic multiple of it. Disproof: no window under one second keeps the engine under 100 percent."""
from govsim.bench import (BATCH_WINDOW_S, HYBRID_BATCH_WINDOW_S, HYBRID_SIGN_S, MLDSA65_SIGN_S, SIGN_S, run)

HYBRID_PESSIMISM = 2.0   # ML-DSA twice as slow on OTBN as the M4 figure, or a long rejection-sampling tail


def test_hybrid_costs_both_signatures():
    assert abs(HYBRID_SIGN_S - (SIGN_S + MLDSA65_SIGN_S)) < 1e-12


def test_hybrid_at_the_classical_window_does_not_keep_up():
    r = run("rack")
    assert r["hybrid_engine_utilization_at_base_window_pct"] > 100.0, r


def test_hybrid_window_keeps_engine_under_100_percent():
    r = run("rack")
    assert HYBRID_BATCH_WINDOW_S < 1.0
    assert r["hybrid_engine_utilization_pct"] < 100.0, r


def test_hybrid_holds_under_pessimistic_ml_dsa_cost():
    r = run("rack", hybrid_sign_s=SIGN_S + HYBRID_PESSIMISM * MLDSA65_SIGN_S)
    assert r["hybrid_engine_utilization_pct"] < 100.0, r


def test_a_window_under_one_second_exists():
    # utilisation is hybrid_sign_s / window when saturated, so any window above the sign time works
    w = 1.0
    assert HYBRID_SIGN_S < w
    assert run("rack", hybrid_window_s=w)["hybrid_engine_utilization_pct"] < 100.0
