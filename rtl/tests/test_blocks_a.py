# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Regressions for the two RTL bugs L7 found on 23 October 2026 (rtl/formal/FINDINGS-a.md F1, F2). Each test fails
by assertion on the code before the fix. Amaranth's built-in simulator, no external tools."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from amaranth import ClockDomain, Elaboratable, Module  # noqa: E402
from amaranth.sim import Simulator  # noqa: E402

from rtl.governor_rtl import Lifecycle, MonotonicCounter  # noqa: E402
from rtl.governor_rtl.lifecycle import PRODUCTION  # noqa: E402


class _WithReset(Elaboratable):
    def __init__(self, dut):
        self.dut, self.cd = dut, ClockDomain("sync")

    def elaborate(self, platform):
        m = Module()
        m.domains.sync = self.cd
        m.submodules.dut = self.dut
        return m


def run(top, testbench):
    sim = Simulator(top)
    sim.add_clock(1e-6)
    sim.add_testbench(testbench)
    sim.run()


def test_f1_no_debug_window_after_reset_on_a_production_chip():
    dut = Lifecycle()
    top = _WithReset(dut)

    async def tb(ctx):
        ctx.set(dut.fuse_state, PRODUCTION)
        ctx.set(dut.load, 1)
        await ctx.tick()
        ctx.set(dut.load, 0)
        ctx.set(dut.debug_req, 1)
        assert ctx.get(dut.debug_grant) == 0 and ctx.get(dut.debug_refused) == 1
        ctx.set(top.cd.rst, 1)                     # a warm reset, or a glitch on the reset line
        await ctx.tick()
        ctx.set(top.cd.rst, 0)
        for _ in range(3):                          # the cycles before the boot code strobes load
            assert ctx.get(dut.state) == 0          # the register itself is back at TEST ...
            assert ctx.get(dut.debug_grant) == 0    # ... and debug is still refused
            assert ctx.get(dut.debug_refused) == 1
            await ctx.tick()
        ctx.set(dut.load, 1)
        await ctx.tick()
        assert ctx.get(dut.state) == PRODUCTION and ctx.get(dut.debug_grant) == 0

    run(top, tb)


def test_f2_counter_saturates_instead_of_wrapping():
    dut = MonotonicCounter()

    async def tb(ctx):
        top = (1 << 64) - 1
        ctx.set(dut.hwm, top)
        ctx.set(dut.load_hwm, 1)
        await ctx.tick()
        ctx.set(dut.load_hwm, 0)
        assert ctx.get(dut.value) == top
        ctx.set(dut.inc, 1)
        await ctx.tick()
        assert ctx.get(dut.value) == top            # the old code wrapped to 0 here

    run(dut, tb)
