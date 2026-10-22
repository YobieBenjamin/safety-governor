"""N1: the whole-deployment overhead (docs/12). 72 governors, eight slots each, in a
discrete-event simulation. The plan of record must cost under one percent of throughput; the
test prints where each policy axis crosses one percent. The disproof (above one percent at
every serviceable policy) is asserted for the slot-held release, which is the real finding."""
from dataclasses import replace

from govsim.bench import SIGN_S
from govsim.deploy import (ONE_PERCENT, PLAN_OF_RECORD, Policy, crossing, measure, run_one,
                           sweep_actions, sweep_window_held)


def test_plan_of_record_costs_under_one_percent_and_tail_is_bounded():
    p = PLAN_OF_RECORD
    assert p.governors == 72 and p.serviceable
    r = measure(p, horizon=20.0, open_horizon=20.0)
    print(f"\nplan of record {p.label()}: overhead {r['overhead_pct']:.4f} %, "
          f"p99 added {r['p99_added_s']*1e3:.1f} ms, p99 receipt wait {r['p99_receipt_wait_s']*1e3:.1f} ms")
    assert r["overhead_pct"] < ONE_PERCENT, r
    assert r["engine_util_pct"] < 50.0, r
    assert r["max_receipt_wait_s"] < p.window_s + SIGN_S + 0.005, r      # docs/04 §9: window plus signature
    assert 0 <= r["p99_added_s"] < 0.2, r


def test_where_the_mailbox_load_crosses_one_percent():
    pts = sweep_actions(horizon=8.0)
    c = crossing(pts)
    print("\noverhead by mailbox calls per response: " + ", ".join(f"{a:g}: {o:.3f}%" for a, o in pts))
    print(f"policy at which overhead crosses 1 percent: about {c} mailbox calls per response "
          f"(the plan of record makes {PLAN_OF_RECORD.actions_per_response:g})")
    assert c is not None and c > 100 * PLAN_OF_RECORD.actions_per_response


def test_slot_held_until_receipt_is_above_one_percent_at_every_serviceable_window():
    pts = sweep_window_held(horizon=8.0)
    print("\nslot held until receipt, overhead by window: " + ", ".join(f"{w*1e3:g} ms: {o:.1f}%" for w, o in pts))
    for w, o in pts:
        if replace(Policy(), window_s=w).serviceable:
            assert o > ONE_PERCENT, (w, o)


def test_governor_adds_nothing_when_it_is_absent():
    base = run_one(replace(PLAN_OF_RECORD, governors=4), "saturated", False, 5.0)
    assert base["stall_pct"] == 0.0 and base["tokens"] > 0
