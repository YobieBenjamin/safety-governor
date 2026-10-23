# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""PCIe CEM sideband timing, checked against the RTL halt sequencer.

The numbers. The PCI Express CEM specification is members-only; we have not read it. Every
number below comes from a public secondary source named next to it (ids in
docs/interfaces/sources.csv):

    T_PVPERL     100 ms   power stable to PERST# inactive     LINUXPCI (cites CEM r5.1 2.9.2), LKMLCEM (quotes CEM 2.0)
    T_PERST-CLK  100 us   REFCLK stable before PERST# inactive LINUXPCI, LKMLCEM
    T_PERST      100 us   PERST# active time                  LKMLCEM (quotes CEM 2.0)
    T_FAIL       500 ns   power level invalid to PERST# active LKMLCEM (quotes CEM 2.0)
    PWRBRK#      no public response-time number. INSPUR (a patent, not NVIDIA) says a GPU's
                 frequency reduction "may be completed within 5 ms"; CTYUN shows the table is an
                 image we cannot read. The governor's 1 ms bound is therefore a bound on the pin,
                 not on the GPU's slowdown.

The method. The halt sequencer (``rtl.governor_rtl.halt.HaltSeq``) and, optionally, the CEM
shaper (``rtl.governor_rtl.cem_sideband.CemSideband``) are simulated with Amaranth's simulator.
A slot model turns PWR_EN into a power-good that rises after a ramp and falls at once. Every
change of the pad-level signals is recorded with its time, and ``check_trace`` applies the CEM
rules to the recorded trace. A rule fails by assertion on the trace, never on a tool error.

    python -m govsim.hardware_ref.cem
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

from amaranth import Elaboratable, Module, Signal
from amaranth.sim import Simulator

from rtl.governor_rtl.cem_sideband import CemSideband
from rtl.governor_rtl.halt import HaltSeq, RUN

US = 1.0
T_PVPERL_US = 100_000.0     # LINUXPCI, LKMLCEM
T_PERST_US = 100.0          # LKMLCEM
T_FAIL_US = 0.5             # LKMLCEM
T_PERST_CLK_US = 100.0      # LINUXPCI, LKMLCEM: a board requirement; the governor does not own REFCLK
CORE_CLOCK_HZ = 50e6        # docs/08-silicon-plan.md: 50 MHz target
HALT_BOUND_US = 1000.0      # docs/02-safety-fabric.md section 1
LOOP_DIGITAL_US = 311.0     # hw/loop/run_loop.py digital path (includes the 10 us lever assumption)
LOOP_ELECTRICAL_WORST_US = 6.15   # hw/loop/results.md, N=72, 3 m hops, 85 C
LTPI_LL_WORST_US = 19.20    # LTPI12 Table 15, 25 MHz SDR random latency


@dataclass
class RuleResult:
    rule: str
    ok: bool
    measured: str
    required: str
    source: str

    def line(self) -> str:
        return f"{'PASS' if self.ok else 'FAIL'}  {self.rule:<14} measured {self.measured:<34} required {self.required:<28} [{self.source}]"


def _edges(trace, name):
    """(time, new_value) for every change of ``name``; the first sample counts as an edge."""
    out, last = [], None
    for t, s in trace:
        v = s[name]
        if v != last:
            out.append((t, v))
            last = v
    return out


def _value_at(trace, name, t):
    v = None
    for tt, s in trace:
        if tt > t:
            break
        v = s[name]
    return v


def check_trace(trace: list[tuple[float, dict]], *, has_pg: bool = True) -> list[RuleResult]:
    """CEM rules on a trace of {perst, pwr_en, pwr_good, pwrbrk} samples (1 = asserted / on),
    taken at every change. Times in microseconds."""
    res: list[RuleResult] = []
    perst = _edges(trace, "perst")
    power = [(t, s["pwr_en"] and (s["pwr_good"] if has_pg else 1)) for t, s in trace]
    p_edges, last = [], None
    for t, v in power:
        if v != last:
            p_edges.append((t, v))
            last = v
    # T_PVPERL: every PERST# release happens with power valid for at least 100 ms
    releases = [t for t, v in perst if v == 0]
    worst = None
    for t in releases:
        valid_since = None
        for tt, v in p_edges:
            if tt > t:
                break
            valid_since = tt if v else None
        gap = -1.0 if valid_since is None else t - valid_since
        worst = gap if worst is None else min(worst, gap)
    ok = worst is not None and worst >= T_PVPERL_US
    res.append(RuleResult("T_PVPERL", ok, "no release seen" if worst is None else ("released with power not valid" if worst < 0 else f"{worst / 1000:.3f} ms min"),
                          f">= {T_PVPERL_US / 1000:.0f} ms", "LINUXPCI; LKMLCEM"))
    # T_PERST: every assertion lasts at least 100 us
    widths = []
    for i, (t, v) in enumerate(perst):
        if v == 1:
            end = next((tt for tt, vv in perst[i + 1:] if vv == 0), None)
            if end is not None:
                widths.append(end - t)
    w = min(widths) if widths else None
    res.append(RuleResult("T_PERST", w is not None and w >= T_PERST_US, "no complete pulse" if w is None else f"{w:.3f} us min",
                          f">= {T_PERST_US:.0f} us", "LKMLCEM"))
    # T_FAIL: when power goes invalid, PERST# is already asserted or asserts within 500 ns
    lag = None
    for t, v in p_edges:
        if v == 0 and t > trace[0][0]:
            if _value_at(trace, "perst", t) == 1:
                d = 0.0
            else:
                d = next((tt - t for tt, vv in perst if tt >= t and vv == 1), float("inf"))
            lag = d if lag is None else max(lag, d)
    res.append(RuleResult("T_FAIL", lag is not None and lag <= T_FAIL_US, "no power loss seen" if lag is None else f"{lag:.3f} us max",
                          f"<= {T_FAIL_US} us", "LKMLCEM"))
    return res


class SlotUnderTest(Elaboratable):
    """HaltSeq, optionally followed by CemSideband, driving one slot, plus a slot power model in
    hardware so the simulation needs no per-cycle testbench work: power-good rises ``ramp``
    cycles after PWR_EN, falls at once with PWR_EN or during a ``brownout``, and reaches the
    governor ``pg_delay`` cycles late (an LTPI hop)."""

    def __init__(self, with_shaper: bool, shaper: Elaboratable | None = None, ramp: int = 5_000, pg_delay: int = 0):
        self.seq = HaltSeq(t_throttle=3, t_halt=4)
        self.shaper = (shaper or CemSideband()) if with_shaper else None
        self.ramp, self.pg_delay = ramp, pg_delay
        self.brownout = Signal()
        self.pg_real = Signal()
        self.cycles = Signal(32)
        self.perst = Signal()
        self.pwr_en = Signal()
        self.pwrbrk = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules.seq = self.seq
        m.d.sync += self.cycles.eq(self.cycles + 1)
        ramp_ctr = Signal(range(self.ramp + 1))
        with m.If(~self.pwr_en):
            m.d.sync += ramp_ctr.eq(0)
        with m.Elif(ramp_ctr < self.ramp):
            m.d.sync += ramp_ctr.eq(ramp_ctr + 1)
        m.d.comb += self.pg_real.eq(self.pwr_en & (ramp_ctr >= self.ramp) & ~self.brownout)
        pg_seen = self.pg_real
        for i in range(self.pg_delay):
            nxt = Signal(name=f"pg_d{i}")
            m.d.sync += nxt.eq(pg_seen)
            pg_seen = nxt
        if self.shaper is None:
            m.d.comb += [self.perst.eq(self.seq.perst), self.pwr_en.eq(self.seq.pwr_en), self.pwrbrk.eq(self.seq.pwrbrk)]
        else:
            sh = self.shaper
            m.submodules.shaper = sh
            m.d.comb += [sh.perst_req.eq(self.seq.perst), sh.pwr_en_req.eq(self.seq.pwr_en), sh.pwrbrk_req.eq(self.seq.pwrbrk),
                         sh.pwr_good.eq(pg_seen), sh.tick_us.eq(1),
                         self.perst.eq(sh.perst), self.pwr_en.eq(sh.pwr_en), self.pwrbrk.eq(sh.pwrbrk)]
        return m


def simulate(with_shaper: bool, shaper=None, ramp_us: int = 5_000, pg_delay_us: int = 0, run_us: int = 110_000):
    """One scenario, one clock cycle per microsecond:

    boot, arm and run; hold RUN past T_PVPERL; a loop loss (HALT) at once followed by an
    authorized CLEAR with the loop still live, so the sequencer goes straight back to RUN; run
    past T_PVPERL again; a 2 ms brown-out of the slot rail that nobody commanded; run past
    T_PVPERL again; then a tamper (SAFE: power cut).

    ``ramp_us`` is the slot's power-good delay after PWR_EN; ``pg_delay_us`` adds a transport
    delay on the power-good the governor sees (an LTPI hop). Returns (trace, info)."""
    dut = SlotUnderTest(with_shaper, shaper, ramp=ramp_us, pg_delay=pg_delay_us)
    seq = dut.seq
    trace: list[tuple[float, dict]] = []
    info: dict = {}

    def record(t, perst, pwr_en, pg, brk):
        # several delta cycles can fire inside one clock step while combinational logic settles;
        # only the settled value at each time counts
        st = {"perst": int(perst), "pwr_en": int(pwr_en), "pwr_good": int(pg), "pwrbrk": int(brk)}
        if trace and trace[-1][0] == float(t):
            trace.pop()
        if not trace or trace[-1][1] != st:
            trace.append((float(t), st))

    async def recorder(ctx):
        # the reset values: HaltSeq starts in HALTED_INITIAL (brake and reset asserted, power off)
        record(0, 1, 0, 0, 1)
        async for perst, pwr_en, pg, brk, t in ctx.changed(dut.perst, dut.pwr_en, dut.pg_real, dut.pwrbrk).sample(dut.cycles):
            record(t, perst, pwr_en, pg, brk)

    async def tb(ctx):
        await ctx.tick().repeat(10)
        ctx.set(seq.hb_ok, 1)
        ctx.set(seq.loop_sense, 1)
        await ctx.tick().repeat(run_us)
        info["state_before_halt"] = ctx.get(seq.state)
        ctx.set(seq.loop_lost, 1)
        await ctx.tick()
        ctx.set(seq.loop_lost, 0)
        await ctx.tick()
        ctx.set(seq.clear, 1)
        await ctx.tick()
        ctx.set(seq.clear, 0)
        await ctx.tick().repeat(run_us)
        ctx.set(dut.brownout, 1)
        await ctx.tick().repeat(2_000)
        ctx.set(dut.brownout, 0)
        await ctx.tick().repeat(run_us)
        info["state_before_tamper"] = ctx.get(seq.state)
        ctx.set(seq.tamper, 1)
        await ctx.tick().repeat(50)

    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(tb)
    sim.add_process(recorder)
    sim.run()
    return trace, info



def simulate_short_reset(shaper=None, settle_us: int = 101_000, pulse_us: int = 3) -> list[tuple[float, dict]]:
    """CemSideband alone with power held valid: wait past T_PVPERL, then ask for PERST# for only
    ``pulse_us``. The sequencer can do this (HALT, then CLEAR and RUN within a few cycles), so the
    shaper must stretch it to T_PERST."""
    sh = shaper or CemSideband()
    trace: list[tuple[float, dict]] = []

    class Harness(Elaboratable):
        def __init__(self):
            self.cycles = Signal(32)

        def elaborate(self, platform):
            m = Module()
            m.submodules.sh = sh
            m.d.sync += self.cycles.eq(self.cycles + 1)
            m.d.comb += sh.tick_us.eq(1)
            return m

    h = Harness()

    def record(t, perst, pwr_en, pg, brk):
        st = {"perst": int(perst), "pwr_en": int(pwr_en), "pwr_good": int(pg), "pwrbrk": int(brk)}
        if trace and trace[-1][0] == float(t):
            trace.pop()
        if not trace or trace[-1][1] != st:
            trace.append((float(t), st))

    async def recorder(ctx):
        record(0, 1, 0, 0, 0)
        async for perst, pwr_en, pg, brk, t in ctx.changed(sh.perst, sh.pwr_en, sh.pwr_good, sh.pwrbrk).sample(h.cycles):
            record(t, perst, pwr_en, pg, brk)

    async def tb(ctx):
        ctx.set(sh.pwr_en_req, 1)
        ctx.set(sh.pwr_good, 1)
        await ctx.tick().repeat(settle_us)
        ctx.set(sh.perst_req, 1)
        await ctx.tick().repeat(pulse_us)
        ctx.set(sh.perst_req, 0)
        await ctx.tick().repeat(1_000)

    sim = Simulator(h)
    sim.add_clock(1e-6)
    sim.add_testbench(tb)
    sim.add_process(recorder)
    sim.run()
    return trace

def brake_latency_cycles() -> int:
    """Clock cycles from a loss of loop current at the sequencer's input to the brake asserting.
    Simulated on HaltSeq alone, from RUN."""
    dut = HaltSeq(t_throttle=3, t_halt=4)
    out = {}

    async def tb(ctx):
        ctx.set(dut.hb_ok, 1)
        ctx.set(dut.loop_sense, 1)
        await ctx.tick()
        assert ctx.get(dut.state) == RUN and ctx.get(dut.pwrbrk) == 0
        ctx.set(dut.loop_lost, 1)
        n = 0
        while not ctx.get(dut.pwrbrk):
            await ctx.tick()
            n += 1
            if n > 100:
                break
        out["cycles"] = n

    sim = Simulator(dut)
    sim.add_clock(1 / CORE_CLOCK_HZ)
    sim.add_testbench(tb)
    sim.run()
    return out["cycles"]


def halt_budget(ltpi: bool) -> RuleResult:
    """The 1 ms halt bound with the governor's own brake latency and, when the lever rides LTPI,
    the LTPI low-latency GPIO hop added. The loop's 311 us digital path already assumes 10 us
    for the lever driver; the measured sequencer latency must fit inside that assumption."""
    seq_us = brake_latency_cycles() / CORE_CLOCK_HZ * 1e6
    total = LOOP_ELECTRICAL_WORST_US + LOOP_DIGITAL_US + (LTPI_LL_WORST_US if ltpi else 0.0)
    ok = seq_us <= 10.0 and total <= HALT_BOUND_US
    name = "HALT_PIN_LTPI" if ltpi else "HALT_PIN"
    return RuleResult(name, ok, f"{total:.2f} us (sequencer {seq_us * 1000:.0f} ns)", f"<= {HALT_BOUND_US:.0f} us at the pin",
                      "REPO_LOOP; LTPI12 Table 15" if ltpi else "REPO_LOOP")


def report() -> tuple[list[RuleResult], list[RuleResult], list[RuleResult], list[RuleResult]]:
    alone, _ = simulate(with_shaper=False)
    shaped, _ = simulate(with_shaper=True)
    ltpi_pg, _ = simulate(with_shaper=True, pg_delay_us=20)
    short = [r for r in check_trace(simulate_short_reset()) if r.rule == "T_PERST"]
    return check_trace(alone), check_trace(shaped) + short + [halt_budget(False), halt_budget(True)], check_trace(ltpi_pg), short


def main(argv: list[str] | None = None) -> int:
    alone, shaped, ltpi_pg, _short = report()
    print("CEM sideband timing (one clock = 1 us; slot power-good ramps 5 ms after PWR_EN)")
    print(" HaltSeq alone, pads driven straight from the sequencer:")
    for r in alone:
        print("   ", r.line())
    print(" HaltSeq + CemSideband (T_PERST also from a 3 us reset request with power held valid, CemSideband alone):")
    for r in shaped:
        print("   ", r.line())
    print(" HaltSeq + CemSideband, power-good seen through a 20 us LTPI hop:")
    for r in ltpi_pg:
        print("   ", r.line())
    expected_alone = {"T_PVPERL": False, "T_PERST": False, "T_FAIL": False}
    got_alone = {r.rule: r.ok for r in alone}
    ok = got_alone == expected_alone and all(r.ok for r in shaped)
    ok = ok and {r.rule: r.ok for r in ltpi_pg} == {"T_PVPERL": True, "T_PERST": True, "T_FAIL": False}
    print(" findings reproduced (sequencer alone misses T_PVPERL, T_PERST and T_FAIL; the shaper meets all three;"
          " T_FAIL on a brown-out cannot be met through an LTPI hop):", "YES" if ok else "NO")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
