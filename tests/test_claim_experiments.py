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


# ------------------------------------------------------------------ amendment 2 to docs/29 (approved 30 October 2026)
def _point(kind, strategy, k, seed, harm, cap, error=None, baseline=False):
    """One hand-built run row, shaped as the record holds it."""
    row = {"kind": kind, "strategy": strategy, "K": k, "seed": seed, "control": None, "harm": harm, "cap": cap,
           "over_cap": (harm is not None and cap is not None and harm > cap + 1e-9), "baseline": baseline}
    if error:
        row.update({"error": error, "harm": None, "cap": None, "over_cap": None})
    return row


def _money_sweep(harms_by_k, cap=2000.0, strategy="split", seeds=(1, 2)):
    """A money strategy line at K = 10, 100 and 1,000 with the given harm at each (same on every seed)."""
    return [_point("money", strategy, k, s, h, cap) for k, h in harms_by_k.items() for s in seeds]


def _baselines_for(runs, harm=None):
    """A baseline row for every run, with the run's own harm unless one is given (so the sweep never exceeds it)."""
    return [_point(r["kind"], r["strategy"], r["K"], r["seed"], r["harm"] if harm is None else harm, r["cap"], baseline=True)
            for r in runs]


def test_amendment_2_the_verdict_function_gives_each_outcome():
    """Clauses 1 to 3 of amendment 2 on hand-built points: FAIL on cap, FAIL on the baseline, PASS, INCONCLUSIVE when the
    baselines are missing, INCOMPLETE on a crashed run; and the seed-for-seed comparison with no tolerance."""
    plan = {"money": ("split",)}
    runs = _money_sweep({10: 1500.0, 100: 1900.0, 1000: 1995.0})

    # PASS: every run under the cap and at or below its own baseline, every baseline present
    line, report = B.verdict_for_kind("money", runs, _baselines_for(runs), plan)
    assert line.startswith("PASS"), line
    assert report["split"]["maxima_by_k"] == {"10": 1500.0, "100": 1900.0, "1000": 1995.0}
    assert report["split"]["baseline_by_k"]["1000"] == 1995.0 and report["split"]["baselines_missing"] == []

    # FAIL on cap: one run at one seed over the cap, whatever the baselines say
    over = _money_sweep({10: 1500.0, 100: 1900.0, 1000: 1995.0}) + [_point("money", "split", 1000, 3, 2000.5, 2000.0)]
    line, _ = B.verdict_for_kind("money", over, _baselines_for(over), plan)
    assert line.startswith("FAIL: over cap: split K = 1,000 seed 3"), line

    # FAIL on the baseline: the sweep exceeds the one-requester baseline at K = 100 on seed 2 only, by one cent, no tolerance
    base = _baselines_for(runs)
    for b in base:
        if (b["K"], b["seed"]) == (100, 2):
            b["harm"] = 1899.99
    line, _ = B.verdict_for_kind("money", runs, base, plan)
    assert line.startswith("FAIL: 100 cooperating attackers got 0.01 more than one requester with the same volume (split, seed 2"), line
    # the same baseline on seed 1 keeps seed 1 passing: the comparison is seed for seed, not against the best baseline
    assert "seed 1" not in line.split(". Reported")[0]

    # INCONCLUSIVE: the baselines did not finish (none at K = 1,000)
    partial = [b for b in _baselines_for(runs) if b["K"] != 1000]
    line, report = B.verdict_for_kind("money", runs, partial, plan)
    assert line.startswith("INCONCLUSIVE: the one-requester baselines did not finish (2 of 6 missing)"), line
    assert report["split"]["baselines_missing"] == ["K = 1,000 seed 1", "K = 1,000 seed 2"]
    # a crashed baseline counts as not finished too
    crashed_base = _baselines_for(runs)
    crashed_base[0]["error"] = "RuntimeError('x')"
    line, _ = B.verdict_for_kind("money", runs, crashed_base, plan)
    assert line.startswith("INCONCLUSIVE"), line

    # INCOMPLETE: a crashed run, with everything else passing
    crashed = runs + [_point("money", "split", 1000, 3, None, None, error="ZeroDivisionError('division by zero')")]
    line, _ = B.verdict_for_kind("money", crashed, _baselines_for(runs), plan)
    assert line.startswith("INCOMPLETE: a run crashed (split K = 1,000 seed 3: ZeroDivisionError"), line
    # but a FAIL stands over a crash
    line, _ = B.verdict_for_kind("money", crashed + [_point("money", "split", 10, 4, 2500.0, 2000.0)], _baselines_for(runs), plan)
    assert line.startswith("FAIL: over cap"), line


def test_amendment_2_the_rise_sentence_is_reported_in_every_verdict_line():
    """The change in L between the two largest K on seed 1, in units of the cap, the one-seed point labelled."""
    plan = {"money": ("split",)}
    # seed 1 rises 1,950 to 1,994 between K = 100 and K = 1,000 (2.20 percent of a 2,000 cap); K = 1,000 has one seed
    runs = [_point("money", "split", 10, 1, 1500.0, 2000.0), _point("money", "split", 10, 2, 1510.0, 2000.0),
            _point("money", "split", 100, 1, 1950.0, 2000.0), _point("money", "split", 100, 2, 1999.0, 2000.0),
            _point("money", "split", 1000, 1, 1994.0, 2000.0)]
    sentence = B.rise_sentence("split", runs)
    assert sentence == "split: still rising by 2.20 percent of the cap between K = 100 and K = 1,000 on seed 1 (K = 1,000, one seed)", sentence
    # seed 2's higher value at K = 100 is not used: seed 1 against seed 1
    for base_harm, head in ((None, "PASS"), (1.0, "FAIL")):
        line, report = B.verdict_for_kind("money", runs, _baselines_for(runs, base_harm), plan)
        assert line.startswith(head) and sentence in line, line
        assert report["split"]["rise"] == sentence
        assert report["split"]["spread_by_k"] == {"10": 10.0, "100": 49.0, "1000": 0.0}
    # flat, and a zero cap
    flat = [_point("money", "split", 100, 1, 1995.0, 2000.0), _point("money", "split", 1000, 1, 1995.0, 2000.0)]
    assert B.rise_sentence("split", flat).startswith("split: flat between K = 100 and K = 1,000 on seed 1")
    zero = [_point("commands", "reword", 100, 1, 0.0, 0.0), _point("commands", "reword", 1000, 1, 0.0, 0.0)]
    assert B.rise_sentence("reword", zero).startswith("reword: the cap is zero, so no units of it: L 0 then 0")
    line, _ = B.verdict_for_kind("commands", zero, _baselines_for(zero), {"commands": ("reword",)})
    assert line.startswith("PASS. Reported, not judged: reword: the cap is zero"), line


def test_amendment_2_the_overall_verdict_and_the_dead_clause():
    """FAIL in any kind fails the record; INCOMPLETE and INCONCLUSIVE rank below it; grows_with_k is gone."""
    runs = _money_sweep({10: 1500.0, 100: 1900.0}) + [_point("data_out", "split", 10, 1, 4e6, 1e7), _point("data_out", "split", 100, 1, 5e6, 1e7)]
    verdicts, report = B.approved_verdicts({"runs": runs, "baseline": _baselines_for(runs)})
    assert verdicts["overall"] == "PASS" and set(report) == {"money", "data_out"}
    verdicts, _ = B.approved_verdicts({"runs": runs, "baseline": [b for b in _baselines_for(runs) if b["kind"] == "money"]})
    assert verdicts["overall"] == "INCONCLUSIVE (data_out)"
    verdicts, _ = B.approved_verdicts({"runs": runs + [_point("money", "split", 100, 3, 2001.0, 2000.0)], "baseline": []})
    assert verdicts["overall"] == "FAIL (money)" and verdicts["data_out"].startswith("INCONCLUSIVE")
    assert not hasattr(B, "grows_with_k"), "the unreachable growth clause was removed (review panel condition B1)"


def test_amendment_2_the_pinned_baseline_touches_exactly_one_gpu(short_runs):
    """The one-requester baseline sends every attacker request through one GPU; the sweep's rotation reaches several.
    The data cap is read from the edition in force and equals the output budget plus the host slack (B7)."""
    pinned = B.run("data_out", "exits", 4, 1, pin_gpu=B.BASELINE_GPU)
    assert pinned["attacker_gpus"] == [B.BASELINE_GPU] and pinned["baseline"] is True and pinned["pinned_gpu"] == B.BASELINE_GPU
    assert pinned["attack_requests"] == 4 * B.PER_AGENT
    assert pinned["data_cap_per_gpu"] == 200_000 + (1 << 20) and pinned["data_cap"] == pinned["data_cap_per_gpu"] * pinned["gpus"]
    # one GPU's allowance bounds the pinned attacker's bytes in any hour
    assert pinned["harm"] <= pinned["data_cap_per_gpu"]
    rotating = B.run("data_out", "exits", 4, 1)
    assert len(rotating["attacker_gpus"]) > 1 and rotating["baseline"] is False
    with pytest.raises(ValueError):
        B.run("data_out", "exits", 1, 1, pin_gpu=99)


def test_amendment_2_the_baselines_are_planned_one_per_sweep_run():
    jobs, bases = B.planned_jobs(), B.planned_baselines()
    assert [b[:4] for b in bases] == jobs and {b[4] for b in bases} == {B.BASELINE_GPU}
    assert [k for *_, k, _, _ in bases] == sorted(k for *_, k, _, _ in bases)


def _small_record(tmp_path, name, runs, baselines=(), env=None, controls=()):
    """A record file shaped as the harness writes one, from hand-built rows."""
    rec = {"protocol": "safety-governor/docs/29-claim-experiments-protocol.md", "protocol_sha256": "abc", "started": "2026-10-30T00:00:00Z",
           "fleet": {"sites": 2, "racks_per_site": 2, "gpus_per_rack": 2}, "hours": 3, "per_agent": 3,
           "ks": sorted({r["K"] for r in runs}), "seeds": sorted({r["seed"] for r in runs}), "environment": env or {"commit": name},
           "runs": list(runs), "controls": list(controls), "baseline": list(baselines), "verdicts": {}, "finished": True,
           "planned_runs": len(runs), "seconds": 1.0}
    import json
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps(rec, indent=1))
    return p


def test_amendment_2_the_reader_computes_the_three_readings(tmp_path, capsys):
    """A rising-under-cap line with no baselines: FAIL under the text, PASS under the pre-amendment code, INCONCLUSIVE
    under the approved rule; with baselines the approved rule decides PASS or FAIL. The record is not altered."""
    import json
    from govsim import claim_readings as R
    runs = _money_sweep({10: 1500.0, 100: 1900.0, 1000: 1995.0}, seeds=(1,))
    p = _small_record(tmp_path, "rec", runs)
    before = p.read_bytes()
    out = R.readings(json.loads(before))
    assert out["original_text"]["money"].startswith("FAIL: L grows with K: split 1,500.00 at K = 10 to 1,995.00 at K = 1,000")
    assert out["pre_amendment_code"]["money"] == "PASS"
    assert out["approved_rule"]["money"].startswith("INCONCLUSIVE: the one-requester baselines did not finish (3 of 3 missing)")
    assert out["approved_rule"]["overall"] == "INCONCLUSIVE (money)" and out["original_text"]["overall"] == "FAIL (money)"
    assert out["two_largest_k_seed_1"][0]["K_upper"] == 1000 and out["two_largest_k_seed_1"][0]["seeds_at_K_upper"] == 1
    assert abs(out["two_largest_k_seed_1"][0]["change_in_units_of_cap"] - 0.0475) < 1e-9
    # with baselines: the approved rule passes when the sweep never exceeds them, fails when it does
    assert R.readings({**json.loads(before), "baseline": _baselines_for(runs)})["approved_rule"]["money"].startswith("PASS")
    assert R.readings({**json.loads(before), "baseline": _baselines_for(runs, 1000.0)})["approved_rule"]["money"].startswith("FAIL: 10 cooperating attackers got 500")
    # an over-cap run fails under all three readings
    over = json.loads(before)
    over["runs"].append(_point("money", "split", 1000, 2, 2100.0, 2000.0))
    for reading in ("original_text", "pre_amendment_code", "approved_rule"):
        assert R.readings(over)[reading]["money"].startswith("FAIL"), reading
    # the command line prints the readings, writes them beside the record and leaves the record alone
    out_file = tmp_path / "rec-readings.json"
    assert R.main([str(p), "--out", str(out_file)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["approved_rule"]["money"].startswith("INCONCLUSIVE") and json.loads(out_file.read_text()) == printed
    assert p.read_bytes() == before
    with pytest.raises(SystemExit):
        R.main([str(p), "--out", str(p)])


def test_amendment_2_merge_combines_two_records_and_alters_neither(tmp_path):
    """Two records of one protocol (a sweep at small K and one at a larger K) merge into one record with the runs,
    controls, baselines and environments of both, the verdicts recomputed by the approved rule."""
    import json
    a_runs = _money_sweep({10: 1500.0, 100: 1900.0}, seeds=(1, 2))
    b_runs = _money_sweep({1000: 1995.0}, seeds=(1,))
    control = {**_point("money", "split", 1, 1, 7995.0, 2000.0), "control": "fleet_budget_off"}
    control2 = {**_point("commands", "reword", 1, 1, 3.0, 0.0), "control": "definitions_off"}
    pa = _small_record(tmp_path, "A", a_runs, _baselines_for(a_runs), env={"commit": "aaa"}, controls=[control, control2])
    pb = _small_record(tmp_path, "B", b_runs, [], env={"commit": "bbb"})
    a_bytes, b_bytes = pa.read_bytes(), pb.read_bytes()
    out = tmp_path / "AB.json"
    rec = B.merge(str(pa), str(pb), str(out))
    assert pa.read_bytes() == a_bytes and pb.read_bytes() == b_bytes
    assert json.loads(out.read_text()) == rec
    assert len(rec["runs"]) == 5 and len(rec["baseline"]) == 4 and len(rec["controls"]) == 2 and rec["duplicate_runs"] == []
    assert [e["commit"] for e in rec["environments"]] == ["aaa", "bbb"] and [e["source"] for e in rec["environments"]] == [str(pa), str(pb)]
    assert {r["source"] for r in rec["runs"]} == {str(pa), str(pb)} and rec["ks"] == [10, 100, 1000]
    assert rec["verdicts"]["control:fleet_budget_off"].startswith("LEAK SEEN") and rec["verdicts"]["control:definitions_off"].startswith("LEAK SEEN")
    # B brought no baselines, so the merged record is INCONCLUSIVE at K = 1,000 until --baselines adds them
    assert rec["verdicts"]["money"].startswith("INCONCLUSIVE: the one-requester baselines did not finish (1 of 5 missing)")
    assert rec["report"]["money"]["split"]["baselines_missing"] == ["K = 1,000 seed 1"]
    # with B's baseline present the merged record passes, and a merged record never claims to be pre-registered
    pb2 = _small_record(tmp_path, "B2", b_runs, _baselines_for(b_runs), env={"commit": "bbb"})
    rec2 = B.merge(str(pa), str(pb2), str(tmp_path / "AB2.json"))
    assert rec2["verdicts"]["money"].startswith("PASS") and rec2["verdicts"]["overall"] == "PASS" and rec2["pre_registered"] is False
    # the command line form, and the refusals: overwriting an input, or merging records of different protocols
    assert B.main(["--merge", str(pa), str(pb2), str(tmp_path / "AB3.json")]) == 0
    with pytest.raises(SystemExit):
        B.merge(str(pa), str(pb), str(pa))
    other = json.loads(b_bytes)
    other["per_agent"] = 4
    po = tmp_path / "other.json"
    po.write_text(json.dumps(other))
    with pytest.raises(SystemExit):
        B.merge(str(pa), str(po), str(tmp_path / "x.json"))


def test_amendment_2_the_record_carries_the_protocol_hash_and_provenance_first(tmp_path, monkeypatch):
    """B8: the record names docs/29 by SHA-256, not only by path, and the environment is on disk before the first
    control runs, so a record that stops at the controls still says what code and protocol it ran under."""
    import hashlib, json
    digest = hashlib.sha256(open(B.PROTOCOL_PATH, "rb").read()).hexdigest()
    assert B.protocol_sha256() == digest and len(digest) == 64

    def no_run(*args, **kwargs):
        raise RuntimeError("the first control was never reached")
    monkeypatch.setattr(B, "run", no_run)
    out = tmp_path / "stopped.json"
    with pytest.raises(RuntimeError):
        B.sweep(str(out), workers=1)
    rec = json.loads(out.read_text())
    assert rec["protocol_sha256"] == digest and rec["environment"]["amendment"] == 3 and rec["environment"]["python"]
    assert rec["pass_rule"] == B.PASS_RULE and rec["controls"] == [] and rec["runs"] == [] and rec["finished"] is False
