# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The two claim experiments of docs/29 keep working: quick checks of their machinery, not the experiments themselves.

The experiments are run in full by their launchers and recorded (docs/29 R7). These tests only make sure that the
instruments are still sound: the formal model's theorems still follow from its invariants and a defect is still
caught; the attacker simulation still measures harm correctly, judges places by an independent oracle, and its
controls still leak.
"""
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "proofs"))

import claim_model as A                                   # noqa: E402
from govsim import claim_attack_sim as B                  # noqa: E402


# ------------------------------------------------------------------ Experiment A, the formal model
def test_the_theorems_follow_from_the_invariants():
    from z3 import Const
    s = A.State("s")
    k, c, site, b = Const("k", A.Tk), Const("c", A.Chip), Const("site", A.Site), Const("b", A.BK)
    rig = A.rigid_assumptions(site, A.site_c(c), A.site_e(s.t_ep[k]), keys=[(site, b)])
    invs = rig + [A.inv_ticket(s, k), A.inv_budget(s, site, b), A.inv_site(s, site), A.inv_site(s, A.site_c(c)), A.inv_chip(s, c)]
    for name, claim in A.theorems(s, k, c, site, b).items():
        assert A.check(invs, claim) == "proved", name


def test_the_one_step_theorems_hold_and_a_mutant_breaks_them():
    assert set(A.one_step_checks().values()) == {"proved"}
    assert "counterexample" in A.one_step_checks("clear_without_quorum").values()


def test_the_bounded_search_finds_no_counterexample_on_the_honest_machine():
    assert set(A.bmc(3).values()) == {"proved"}


# ------------------------------------------------------------------ Experiment B, the attacker simulation
def test_the_sliding_hour_is_measured_correctly():
    events = [(0, 100), (1800, 100), (3599, 100), (3600, 100), (7300, 50)]
    assert B.max_window(events) == 300          # 0, 1800 and 3599 fall in one hour; 3600 starts the next


def test_the_oracle_distance_is_independent_and_right():
    # one degree of latitude is about 111.2 km; the oracle does not use govsim.definitions
    assert abs(B.metres_between((0, 0), (1, 0)) - 111_195) < 50
    assert B.metres_between((34.052, -118.244), (34.052, -118.244 + 360)) < 1


def test_every_spelling_of_a_protected_place_says_what_it_means():
    lat, lon = B.PROTECTED_SITES[0]
    for spelling, truth in B.reworded_places(lat, lon):
        if truth is not None:
            assert len(truth) == 2 and all(isinstance(x, float) or isinstance(x, int) for x in truth), spelling


@pytest.fixture
def short_runs(monkeypatch):
    monkeypatch.setattr(B, "HOURS", 0.2)
    monkeypatch.setattr(B, "PER_AGENT", 2)


def test_a_short_money_run_stays_within_the_fleet_cap(short_runs):
    out = B.run("money", "split", 8, 1)
    assert out["harm"] <= out["cap"] and not out["over_cap"]


def test_the_definitions_control_leaks(short_runs, monkeypatch):
    monkeypatch.setattr(B, "PER_AGENT", 6)
    out = B.run("commands", "reword", 20, 3, control="definitions_off")
    assert out["over_cap"], "with the definitions engine off, a reworded protected place must get a strike ticket"


def test_no_strike_ticket_for_a_protected_place_however_written(short_runs, monkeypatch):
    monkeypatch.setattr(B, "PER_AGENT", 6)
    out = B.run("commands", "reword", 20, 3)
    assert out["harm"] == 0 and not out["over_cap"]


# ------------------------------------------------------------------ amendment 1 to docs/29 (28 October 2026)
def test_the_sweep_runs_smallest_k_first():
    ks = [k for _, _, k, _ in B.planned_jobs()]
    assert ks == sorted(ks), "docs/29 section 5 orders the K sweep smallest first"


def test_the_largest_k_runs_one_seed_and_every_other_k_five():
    jobs = B.planned_jobs()
    assert {seed for _, _, k, seed in jobs if k == B.LARGEST_K} == {1}
    for k in B.K_SWEEP:
        if k == B.LARGEST_K:
            continue
        for kind in B.HARM_KINDS:
            for strategy in B.PLAN[kind]:
                seeds = {s for kd, st, kk, s in jobs if (kd, st, kk) == (kind, strategy, k)}
                assert seeds == set(B.SEEDS), (kind, strategy, k)


def test_the_controls_run_at_one_and_ten_thousand():
    assert B.control_ks() == (1, 10_000)


def test_amendment_3_the_run_stays_governed_for_all_three_hours():
    """Amendment 3 (30 October 2026): the harness re-attests and re-begins the model before the one-hour workload token
    expires, so an honest payment succeeds in every simulated hour, not only the first. Before the amendment hours two
    and three refused everything as gate.not_attested, and every honest-success figure was an artefact of that."""
    import collections
    from govsim import claim_attack_sim as C
    clock, racks, nodes = C.build(fleet_budget=True, seed=1)
    n = len(nodes)
    by_hour = collections.defaultdict(collections.Counter)
    last = clock.now()
    for rnd in range(int(C.HOURS * 3600 / C.STEP_S)):
        if clock.now() - last >= C.REATTEST_S:
            for rr, nn in nodes:
                rr.attest(nn)
                rr.load_model(nn)
            last = clock.now()
        r, node = nodes[rnd % n]
        res = r.pay(node, 5.0, "alice-123")
        ok = bool(res.get("ok")) and C._execute_payment(r, res, 5.0, "recipient-a")
        by_hour[int(rnd * C.STEP_S // 3600)]["ok" if ok else str(res.get("why"))] += 1
        C.advance(clock, racks, C.STEP_S)
    assert C.REATTEST_S < 3600
    for hour in range(C.HOURS):
        assert by_hour[hour] == {"ok": 60}, (hour, dict(by_hour[hour]))


def test_amendment_3_the_record_carries_its_provenance():
    from govsim import claim_attack_sim as C
    env = C._environment()
    assert env["amendment"] == 3 and env["python"] and "reattest_s" in env
