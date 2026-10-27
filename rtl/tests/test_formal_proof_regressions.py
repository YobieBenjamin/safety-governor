# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Regressions for the two RTL bugs WAVE-FORMAL-PROOFS-ON-VERILOG (work stream b) found; each test fails by assertion on the old code.

RTL-METER-COULD-GO-DOWN meter: the counters wrapped, so one large add moved a counter down (rtl/formal/meter.sv, RTL-METER-NEVER-DECREASES).
RTL-HEARTBEAT-KEPT-ALIVE-WITHOUT-HEARTBEAT governor_core: the millisecond strobe tapped the monotonic counter, which load_hwm can move, so the heartbeat
   could be kept from ever expiring without a valid heartbeat (rtl/formal/governor_core.sv, RTL-EXPIRY-NOT-POSTPONED).
Details and reproducers: rtl/formal/FINDINGS-b.md.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from amaranth.sim import Simulator  # noqa: E402

from rtl.governor_rtl import GovernorCore, Meter  # noqa: E402
from rtl.governor_rtl.halt import RUN  # noqa: E402


def run(dut, testbench):
    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(testbench)
    sim.run()


def test_meter_counter_cannot_be_moved_down_by_a_large_add():
    dut = Meter(slots=2, width=16)

    async def tb(ctx):
        ctx.set(dut.slot, 1)
        ctx.set(dut.rd_slot, 1)
        ctx.set(dut.add_cycles, 5)
        ctx.set(dut.strobe, 1)
        await ctx.tick()
        assert ctx.get(dut.rd_cycles) == 5
        ctx.set(dut.add_cycles, 0xFFFF)                       # the old adder wrapped this to 4
        await ctx.tick()
        assert ctx.get(dut.rd_cycles) == 0xFFFF               # stuck at the top: over every budget
        ctx.set(dut.add_cycles, 1)
        await ctx.tick()
        ctx.set(dut.strobe, 0)
        assert ctx.get(dut.rd_cycles) == 0xFFFF

    run(dut, tb)


def test_heartbeat_expires_even_while_load_hwm_is_hammered():
    dut = GovernorCore(cap_entries=2, ticket_entries=2)

    async def tb(ctx):
        ctx.set(dut.loop_sense, 1)
        ctx.set(dut.hb.window, 2)                             # two milliseconds of validity
        ctx.set(dut.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb.hb_valid, 0)
        await ctx.tick()
        assert ctx.get(dut.halt.state) == RUN
        ctx.set(dut.tick, 1)
        ctx.set(dut.mono.load_hwm, 1)
        for _ in range(3 * 1024):                             # three milliseconds of microsecond ticks
            # each cycle the counter jumps up by exactly 2^10: allowed (it only goes up), low bits never reach 1023
            ctx.set(dut.mono.hwm, ctx.get(dut.mono.value) + 1024)
            await ctx.tick()
        assert ctx.get(dut.hb.expired) == 1, "the heartbeat was held alive by load_hwm alone"
        assert ctx.get(dut.halt.state) != RUN

    run(dut, tb)
