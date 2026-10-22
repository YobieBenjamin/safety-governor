"""N1: the whole-deployment overhead (docs/12). 72 governors, eight slots each, in a
discrete-event simulation. The plan of record must cost under one percent of throughput; the
test prints where each policy axis crosses one percent. The disproof ("above one percent at
every serviceable policy") holds for the slot-held release and does *not* hold for the plan of
record, which is the real finding. Throughput lost is measured as tokens governed below baseline,
not a bookkeeping sum."""
from dataclasses import replace

from govsim.bench import BATCH_WINDOW_S, GPU_SECONDS_PER_TOKEN, SIGN_S, SLOTS_PER_CHIP
from govsim.deploy import (ACTIONS_PER_RESPONSE, HEARTBEAT_FANOUT_S, HEARTBEAT_PERIOD_S, LOG_WRITE_S,
                           MERKLE_S, MEAN_TOKENS, ONE_PERCENT, PLAN_OF_RECORD, Policy,
                           crossing, edition_firmware_s, measure, run_one, sensitivity,
                           sweep_actions, sweep_window_held)


def test_plan_of_record_costs_under_one_percent_and_tail_is_bounded():
    p = PLAN_OF_RECORD
    assert p.governors == 72 and p.serviceable
    r = measure(p)                                   # 30 s, same as main and the docs/12 results table
    print(f"\nplan of record {p.label()}: measured overhead {r['overhead_pct']:.4f} %, "
          f"p99 added {r['p99_added_s']*1e3:.1f} ms, p99 receipt wait {r['p99_receipt_wait_s']*1e3:.1f} ms")
    assert r["overhead_pct"] < ONE_PERCENT, r        # measured throughput loss, not a bookkeeping sum
    assert r["engine_util_pct"] < 50.0, r
    assert r["fw_util_pct"] < ONE_PERCENT, r
    # the 67 ms bound of docs/04 §9 is for an idle firmware core at the window edge; with the mid-run
    # edition change the worst receipt waits behind its firmware, so the realistic bound adds it
    assert r["max_receipt_wait_s"] < p.window_s + SIGN_S + edition_firmware_s(), r
    # and with no edition change the ideal bound holds
    r0 = measure(replace(p, edition_change=False))
    assert r0["max_receipt_wait_s"] < p.window_s + SIGN_S + 0.005, r0
    assert 0 <= r["p99_added_s"] < 0.2, r


def test_throughput_lost_is_measured_against_the_baseline():
    """The headline number is tokens the governed run produces below the no-governor baseline in the
    same simulation, not the stall share alone. The two must agree."""
    r = measure(PLAN_OF_RECORD)
    print(f"\nthroughput measured against the baseline: "
          f"governed {r['tokens_governed']:,} vs baseline {r['tokens_baseline']:,} tokens "
          f"= {r['overhead_pct']:.4f} % lost")
    assert r["tokens_baseline"] > 0 and r["tokens_governed"] > 0, r
    assert r["tokens_governed"] < r["tokens_baseline"], r       # the governor never speeds anything up
    # the measured loss and the bookkeeping stall share agree to within 0.003 percentage points
    # (0.0151 against 0.0168: the stall share also counts slot time inside requests unfinished at the horizon)
    assert abs(r["overhead_pct"] - r["stall_pct"]) < 0.003, r
    assert r["overhead_pct"] < ONE_PERCENT, r


def test_disproof_is_not_met_for_the_plan_of_record():
    """The brief's disproof ("above one percent at every serviceable policy") is about the plan of
    record's family. The plan of record, read as the slot freed while the receipt is pending (docs/12's assumption,
    not stated in docs/04), is *under* one percent; the
    slot-held variant is *above* one percent at every serviceable window. Both sides, shown."""
    plan = measure(PLAN_OF_RECORD)
    assert plan["overhead_pct"] < ONE_PERCENT, plan          # plan of record: NOT above one percent
    held = dict(sweep_window_held())
    for w, o in held.items():
        if replace(PLAN_OF_RECORD, window_s=w).serviceable:
            assert o > ONE_PERCENT, (w, o)                   # slot-held: above one percent, every serviceable window
    print(f"\nplan of record {plan['overhead_pct']:.4f} % (disproof not met); "
          f"slot-held serviceable windows all > 1 %: "
          + ", ".join(f"{w*1e3:g}ms:{o:.1f}%" for w, o in held.items()
                      if replace(PLAN_OF_RECORD, window_s=w).serviceable))


def test_where_the_mailbox_load_crosses_one_percent():
    pts = sweep_actions()                                  # 10 s, same as main and the docs/12 sweep
    by_a = dict(pts)
    expect = {0.05: 0.02, 5: 0.11, 20: 0.38, 40: 0.73, 80: 1.45, 160: 3.01}
    for a, e in expect.items():
        assert abs(by_a[a] - e) <= max(0.02, 0.1 * e), (a, by_a[a], e)
    c = crossing(pts)
    mult = round(c / PLAN_OF_RECORD.actions_per_response / 100) * 100
    print("\noverhead by mailbox calls per response: " + ", ".join(f"{a:g}: {o:.3f}%" for a, o in pts))
    print(f"crosses 1 percent at about {c:.0f} mailbox calls per response, "
          f"about {mult:,}x the reference (the plan of record makes {PLAN_OF_RECORD.actions_per_response:g})")
    assert 40 < c < 70, c                                  # ~55, a thousand-fold the reference
    assert mult == 1100, mult


def test_slot_held_until_receipt_is_above_one_percent_at_every_serviceable_window():
    pts = sweep_window_held()
    print("\nslot held until receipt, overhead by window: " + ", ".join(f"{w*1e3:g} ms: {o:.1f}%" for w, o in pts))
    for w, o in pts:
        if replace(PLAN_OF_RECORD, window_s=w).serviceable:
            assert o > ONE_PERCENT, (w, o)


def test_named_assumptions_do_not_move_the_conclusion():
    """docs/12 names three costs (log write, Merkle root, heartbeat fan-out) that are not in
    bench.py. Ten times any one still leaves the plan of record under one percent."""
    rows = dict(sensitivity())
    print("\nsensitivity, each named assumption 10x: " + ", ".join(f"{n}={o:.3f}%" for n, o in rows.items()))
    assert all(o < ONE_PERCENT for o in rows.values()), rows
    assert set(rows) == {"log write 10x", "merkle root 10x", "heartbeat 10x"}, rows


def test_governor_adds_nothing_when_it_is_absent():
    base = run_one(replace(PLAN_OF_RECORD, governors=4), "saturated", False, 5.0)
    assert base["stall_pct"] == 0.0 and base["tokens"] > 0


def test_numbers_used_in_docs_12_are_computed():
    """Every number docs/12 prints is pinned here, not typed: the "no number without an artifact"
    rule. The runs are deterministic (fixed seeds), so the tolerances are for the Python version
    and for the rounding in the doc."""
    assert PLAN_OF_RECORD.governors * SLOTS_PER_CHIP == 576           # 72 governors x 8 slots
    assert abs(SIGN_S * 1e3 - 17) < 0.5                               # the 17 ms signature
    assert BATCH_WINDOW_S * 1e3 == 50.0                               # the 50 ms batch window
    assert abs(MEAN_TOKENS * GPU_SECONDS_PER_TOKEN * 1e3 - 250) < 1e-9  # 500 tokens at 2000/s = 250 ms service
    assert ACTIONS_PER_RESPONSE == 0.05                               # the reference workload
    assert abs(LOG_WRITE_S * 1e6 - 30) < 1e-9                        # the 30 us log append
    assert abs(MERKLE_S * 1e6 - 20) < 1e-9                           # the 20 us Merkle root
    assert HEARTBEAT_FANOUT_S / 5e-6 == 1 + SLOTS_PER_CHIP           # 5 us x 9
    ed = edition_firmware_s()
    assert abs(ed * 1e3 - 18) < 1.0                                   # one edition change, 18 ms of firmware
    assert ed / HEARTBEAT_PERIOD_S * 100 < 2.0                        # one a second is under two percent of the core
    # the results table (30 s), the same measure() main prints
    r = measure(PLAN_OF_RECORD)
    assert abs(r["overhead_pct"] - 0.0151) < 0.002                   # throughput lost, measured
    assert abs(r["tokens_governed"] / 34_273_417 - 1) < 1e-3         # the token counts in the table
    assert abs(r["tokens_baseline"] / 34_278_595 - 1) < 1e-3
    assert abs(r["stall_pct"] - 0.0168) < 0.002                      # the cross-check stall share
    assert abs(r["p99_latency_s"] * 1e3 - 3337) < 20                 # p99, queueing included
    assert abs(r["p99_latency_base_s"] * 1e3 - 3291) < 20            # without the governor
    assert abs(r["p99_added_s"] * 1e3 - 45.6) < 5                    # the p99 added latency
    assert abs(r["p99_receipt_wait_s"] * 1e3 - 66.5) < 3             # the p99 receipt wait
    assert abs(r["max_receipt_wait_s"] * 1e3 - 68.4) < 1             # the max, with the edition change
    assert abs(r["engine_util_pct"] - 28.5) < 1.5                    # busiest engine
    assert abs(r["fw_util_pct"] - 0.209) < 0.02                      # busiest firmware core
    r0 = measure(replace(PLAN_OF_RECORD, edition_change=False))
    assert abs(r0["max_receipt_wait_s"] * 1e3 - 67.0) < 0.5          # without it: window plus signature
    assert 0 < r["max_receipt_wait_s"] - r0["max_receipt_wait_s"] < 0.005   # the edition change adds ~1.4 ms, one firmware op, not 18 ms


def test_open_loop_latency_includes_queueing():
    """A request that arrives while the slot is busy waits, and the wait counts. At 70 percent load
    the p99 without any governor is far above the ~1.1 s of service time alone."""
    r = measure(PLAN_OF_RECORD)
    assert r["p99_latency_base_s"] > 2.0, r                          # queueing, not just the service-time tail
    assert 0 <= r["p99_added_s"] < 0.1, r                            # the governor adds little on top of it


def test_slot_held_table_in_docs_12():
    expect = {0.020: 9.9, 0.030: 11.4, 0.050: 14.3, 0.100: 21.2, 0.200: 32.9}
    got = dict(sweep_window_held())
    for w, e in expect.items():
        assert abs(got[w] - e) <= 0.3, (w, got[w], e)


def test_sensitivity_figures_in_docs_12():
    rows = dict(sensitivity())
    for name, e in {"log write 10x": 0.134, "merkle root 10x": 0.025, "heartbeat 10x": 0.025}.items():
        assert abs(rows[name] - e) <= 0.01, (name, rows[name], e)


def test_mailbox_sweep_stall_share_matches_measured_token_loss():
    """The sweep tables report the stall share of slot time. At 80 calls per response (past the
    crossing) the measured token loss against the baseline is within 0.35 points of it (1.71 against 1.45), so the crossing is not an
    artefact of the bookkeeping."""
    r = measure(replace(PLAN_OF_RECORD, actions_per_response=80), 10.0, 2.0)
    print(f"\n80 calls/response: token loss {r['overhead_pct']:.3f} %, stall share {r['stall_pct']:.3f} %")
    assert abs(r["overhead_pct"] - r["stall_pct"]) < 0.35, r      # 1.71 against 1.45 at 10 s
    assert r["overhead_pct"] > ONE_PERCENT, r
