# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""PCIe CEM sideband timing against the RTL (docs/interfaces/02-pcie-cem-sideband.md).

The CEM numbers come from public secondary sources (the CEM itself is members-only); see
govsim/hardware_ref/cem.py. Each rule fails by assertion on a simulated trace. The findings on
the existing sequencer are pinned as tests that expect the violation, so a future fix flips them
on purpose and not by accident. Every mutant of the shaper must be caught by the rule it breaks.
"""
import pytest
from amaranth import Module

from govsim.hardware_ref import cem
from rtl.governor_rtl.cem_sideband import CemSideband


def rules(trace, **kw):
    return {r.rule: r for r in cem.check_trace(trace, **kw)}


@pytest.fixture(scope="module")
def alone():
    return cem.simulate(with_shaper=False)


@pytest.fixture(scope="module")
def shaped():
    return cem.simulate(with_shaper=True)


# ------------------------------------------------------------------ the rule checker itself
def test_checker_rejects_hand_made_violations():
    ok = [(0.0, {"perst": 1, "pwr_en": 0, "pwr_good": 0, "pwrbrk": 1}),
          (10.0, {"perst": 1, "pwr_en": 1, "pwr_good": 0, "pwrbrk": 1}),
          (5_010.0, {"perst": 1, "pwr_en": 1, "pwr_good": 1, "pwrbrk": 1}),
          (105_010.0, {"perst": 0, "pwr_en": 1, "pwr_good": 1, "pwrbrk": 0}),
          (200_000.0, {"perst": 1, "pwr_en": 1, "pwr_good": 1, "pwrbrk": 1}),
          (200_200.0, {"perst": 1, "pwr_en": 0, "pwr_good": 0, "pwrbrk": 1})]
    assert all(r.ok for r in cem.check_trace(ok))
    early = [x if x[0] != 105_010.0 else (105_009.0, x[1]) for x in ok]          # 1 us too early
    assert not rules(early)["T_PVPERL"].ok
    late_reset = ok[:4] + [(200_200.0, {"perst": 0, "pwr_en": 0, "pwr_good": 0, "pwrbrk": 1}),   # power drops, PERST# 100 us late
                           (200_300.0, {"perst": 1, "pwr_en": 0, "pwr_good": 0, "pwrbrk": 1})]
    assert not rules(late_reset)["T_FAIL"].ok


# ------------------------------------------------------------------ findings on the existing RTL
def test_finding_sequencer_releases_perst_with_power_not_valid(alone):
    trace, info = alone
    assert info["state_before_halt"] == 1                      # RUN
    assert rules(trace)["T_PVPERL"].ok is False                # HaltSeq raises PWR_EN and drops PERST# on one edge


def test_finding_sequencer_perst_pulse_shorter_than_t_perst(alone):
    trace, _ = alone
    r = rules(trace)["T_PERST"]
    assert r.ok is False and r.measured.startswith("3.000")    # HALT, CLEAR, RUN: three cycles of reset


def test_finding_sequencer_cannot_see_a_slot_brownout(alone):
    trace, _ = alone
    assert rules(trace)["T_FAIL"].ok is False                  # no power-good input on the governor pinout


# ------------------------------------------------------------------ the shaper fixes them
def test_shaper_meets_every_cem_rule(shaped):
    trace, info = shaped
    assert info["state_before_halt"] == 1 and info["state_before_tamper"] == 1
    assert all(r.ok for r in cem.check_trace(trace)), [r.line() for r in cem.check_trace(trace)]


def test_shaper_stretches_a_short_reset_request():
    assert rules(cem.simulate_short_reset())["T_PERST"].ok


def test_shaper_never_delays_the_brake(alone, shaped):
    # the same scenario with and without the shaper: the brake changes at exactly the same times
    brake = lambda tr: [(t, s["pwrbrk"]) for t, s in tr if True]
    edges = lambda tr: [(t, v) for i, (t, v) in enumerate(brake(tr)) if i == 0 or v != brake(tr)[i - 1][1]]
    assert edges(alone[0]) == edges(shaped[0])
    assert cem.halt_budget(ltpi=False).ok and cem.halt_budget(ltpi=True).ok
    assert cem.brake_latency_cycles() == 1


def test_finding_t_fail_cannot_be_met_through_an_ltpi_hop():
    trace, _ = cem.simulate(with_shaper=True, pg_delay_us=20)
    r = rules(trace)
    assert r["T_PVPERL"].ok and r["T_FAIL"].ok is False


# ------------------------------------------------------------------ mutants of the shaper
class Mutant(CemSideband):
    def __init__(self, kind, **kw):
        super().__init__(**kw)
        self.kind = kind

    def elaborate(self, platform):
        m = Module()
        power_ok = self.pwr_en_req & self.pwr_good
        pg_settled = self.pg_timer >= self.t_pvperl_us
        if self.kind == "no_pg_timer":
            base = self.perst_req | ~power_ok
        elif self.kind == "registered_fail":
            late = type(self.perst)(name="late_power_ok", init=0)
            m.d.sync += late.eq(power_ok)
            base = self.perst_req | ~late | ~pg_settled
        else:
            base = self.perst_req | ~power_ok | ~pg_settled
        held = self.perst_q & (self.hold_timer < self.t_perst_us)
        if self.kind == "no_hold":
            held = 0
        m.d.comb += [self.perst.eq(base | held), self.pwr_en.eq(self.pwr_en_req), self.pwrbrk.eq(self.pwrbrk_req)]
        m.d.sync += self.perst_q.eq(self.perst)
        with m.If(~power_ok):
            m.d.sync += self.pg_timer.eq(0)
        with m.Elif(self.tick_us & ~pg_settled):
            m.d.sync += self.pg_timer.eq(self.pg_timer + 1)
        with m.If(~self.perst):
            m.d.sync += self.hold_timer.eq(0)
        with m.Elif(~self.perst_q):
            m.d.sync += self.hold_timer.eq(0)
        with m.Elif(self.tick_us & (self.hold_timer < self.t_perst_us)):
            m.d.sync += self.hold_timer.eq(self.hold_timer + 1)
        return m


def test_mutant_unmodified_copy_passes():
    """The mutant harness itself is faithful: with no mutation it passes like the real block."""
    trace, _ = cem.simulate(with_shaper=True, shaper=Mutant("none"))
    assert all(r.ok for r in cem.check_trace(trace))


@pytest.mark.parametrize("shaper,rule,where", [
    (lambda: CemSideband(t_pvperl_us=50_000), "T_PVPERL", "seq"),
    (lambda: Mutant("no_pg_timer"), "T_PVPERL", "seq"),
    (lambda: Mutant("registered_fail"), "T_FAIL", "seq"),
    (lambda: CemSideband(t_perst_us=10), "T_PERST", "short"),
    (lambda: Mutant("no_hold"), "T_PERST", "short"),
])
def test_mutant_caught(shaper, rule, where):
    if where == "seq":
        trace, _ = cem.simulate(with_shaper=True, shaper=shaper())
    else:
        trace = cem.simulate_short_reset(shaper())
    assert rules(trace)[rule].ok is False
