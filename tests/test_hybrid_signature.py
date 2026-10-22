"""C3: the post-quantum path. A hybrid signature (ECDSA P-384 plus ML-DSA-65) per batch on the one OTBN-class
engine. ML-DSA's cycle count on OTBN is an UNVERIFIED placeholder (see govsim/bench.py), so every result here is
conditional on it, and the tests also hold under a pessimistic multiple of it. Disproof: no window under one
second keeps the engine under 100 percent."""
from govsim.bench import (BATCH_WINDOW_S, HYBRID_BATCH_WINDOW_S, HYBRID_SIGN_S, MLDSA65_COST_SOURCED, MLDSA65_SIGN_S,
                          SIGN_S, run)

# ML-DSA twice as slow on OTBN as the M4 figure, standing in for the long rejection-sampling tail. The factor is
# an assumption, not a measurement: a real tail bound needs a Phase 2 measurement (recorded in docs/04 §9).
HYBRID_PESSIMISM = 2.0


def test_hybrid_costs_both_signatures():
    # The hybrid cost is both signatures per batch, and run() must charge both, not one.
    assert abs(HYBRID_SIGN_S - (SIGN_S + MLDSA65_SIGN_S)) < 1e-12
    r = run("rack", batch_window_s=HYBRID_BATCH_WINDOW_S, hybrid_window_s=HYBRID_BATCH_WINDOW_S)
    # At the same window the engine counts ML-DSA on top of P-384, so hybrid utilisation exceeds P-384 alone.
    assert r["hybrid_engine_utilization_pct"] > r["engine_utilization_pct"]
    # and it is the utilisation computed from the combined sign time of both signatures.
    assert abs(r["hybrid_engine_utilization_pct"]
               - 100.0 * r["hybrid_signatures_batched"] * HYBRID_SIGN_S / r["gpu_seconds"]) < 1e-9


def test_hybrid_at_the_classical_window_does_not_keep_up():
    r = run("rack")
    assert r["hybrid_engine_utilization_at_base_window_pct"] > 100.0, r


def test_hybrid_window_keeps_engine_under_100_percent():
    r = run("rack")
    assert HYBRID_BATCH_WINDOW_S < 1.0
    assert r["hybrid_engine_utilization_pct"] < 100.0, r


def test_hybrid_holds_under_pessimistic_ml_dsa_cost():
    # 2x stands in for the rejection-sampling tail. The margin to 100 percent is tight at the 250 ms window, so
    # the result is sensitive: a real tail bound needs a measurement (recorded in docs/04 §9).
    r = run("rack", hybrid_sign_s=SIGN_S + HYBRID_PESSIMISM * MLDSA65_SIGN_S)
    assert r["hybrid_engine_utilization_pct"] < 100.0, r
    # at the 250 ms window the 2x cost leaves only ~13 percent slack, not headroom
    assert r["hybrid_engine_utilization_pct"] > 50.0, r


def test_a_window_under_one_second_exists():
    # The disproof asks whether any window UNDER one second keeps the engine under 100 percent. The modelled window
    # is under a second and keeps the engine up; that is the window that makes the disproof hold.
    w = HYBRID_BATCH_WINDOW_S
    assert w < 1.0
    r = run("rack", hybrid_window_s=w)
    assert r["hybrid_engine_utilization_pct"] < 100.0, r


def test_under_one_second_disproof_has_headroom():
    # Within the under-one-second budget the ML-DSA cost could grow several-fold before a window stops keeping the
    # engine up; only a 2x tail is assumed, so the disproof has headroom on the 1 s boundary even at 8x (recorded
    # in docs/04 §9), unlike the tight 250 ms window.
    w = 0.999
    r = run("rack", hybrid_window_s=w, hybrid_sign_s=SIGN_S + 8.0 * MLDSA65_SIGN_S)
    assert r["hybrid_engine_utilization_pct"] < 100.0, r


def test_result_is_conditional_on_unverified_cost():
    # The hybrid verdict rests on the unverified ML-DSA figure; the model records that it is unsourced, so the
    # "disproof did not hold" conclusion is not relied on until the figure is checked (see govsim/bench.py).
    assert MLDSA65_COST_SOURCED is False
