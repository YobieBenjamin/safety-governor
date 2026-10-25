# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Yobie's two design calls of 23 October 2026, as simulation tests on the RTL ("silently failing is a bullshit
feature. Operators should have some verbose warning / signal / notice.").

1. A signed HALT to a chip already in SAFE opens its loop switch (state stays SAFE, the command is the cause on
   record). On the old sequencer, which ignored cmd_halt in SAFE, the first two tests fail by assertion.
2. A chip that never gets its first heartbeat keeps holding the rack, but raises the hardware alarm
   NO_FIRST_HEARTBEAT once the boot window passes (ALARMS bit 31, CAUSE bit 3, BOOT_WAIT), and an authorized EXCLUDE
   closes its loop switch while its own levers stay asserted (ALARMS bit 30, CAUSE bit 4).
The formal versions are in rtl/formal/halt_seq.sv (X, N and H rules) and rtl/formal/governor_core.sv (RTL-HALT-REACHES-PINS, RTL-LOOP-STAYS-OPEN, RTL-EXCLUDED-LEVERS-SAFE and RTL-ALARMS-HARDWARE-OWNED).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from amaranth.sim import Simulator  # noqa: E402

from rtl.governor_rtl import GovernorCore, HaltSeq  # noqa: E402
from rtl.governor_rtl.halt import C_COMMAND, C_LOCAL, C_LOOP, C_NONE, C_TAMPER, HALT, HALTED_INITIAL, RUN, SAFE, THROTTLE  # noqa: E402
from rtl.governor_rtl.top import ALARM_EXCLUDED, ALARM_NO_FIRST_HEARTBEAT  # noqa: E402

NFH, EXC = 1 << ALARM_NO_FIRST_HEARTBEAT, 1 << ALARM_EXCLUDED


def run(dut, testbench):
    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(testbench)
    sim.run()


def levers(ctx, dut):
    return ctx.get(dut.pwrbrk), ctx.get(dut.perst), ctx.get(dut.pwr_en)


async def pulse(ctx, sig, cycles=1):
    ctx.set(sig, 1)
    for _ in range(cycles):
        await ctx.tick()
    ctx.set(sig, 0)


async def to_run(ctx, dut):
    ctx.set(dut.hb_ok, 1)
    ctx.set(dut.loop_sense, 1)
    await ctx.tick()
    assert ctx.get(dut.state) == RUN


async def safe_by_lost_heartbeat(ctx, dut):
    await to_run(ctx, dut)
    await pulse(ctx, dut.hb_expired)
    ctx.set(dut.hb_ok, 0)
    ctx.set(dut.tick, 1)
    for _ in range(4):
        await ctx.tick()
    ctx.set(dut.tick, 0)
    assert (ctx.get(dut.state), ctx.get(dut.cause), ctx.get(dut.switch_open)) == (SAFE, C_LOCAL, 0)


# ------------------------------------------------------------------------------------------- call 1: HALT in SAFE
def test_halt_to_a_chip_in_safe_opens_its_loop_and_stays_safe():
    dut = HaltSeq(t_throttle=2, t_halt=2)

    async def tb(ctx):
        await safe_by_lost_heartbeat(ctx, dut)
        await pulse(ctx, dut.cmd_halt)
        assert ctx.get(dut.switch_open) == 1, "a signed HALT in SAFE left the loop closed (the old behaviour)"
        assert ctx.get(dut.state) == SAFE and ctx.get(dut.cause) == C_COMMAND
        assert levers(ctx, dut) == (1, 1, 0)                   # power stays off: no descent to HALT
        for _ in range(5):                                     # and nothing but CLEAR moves it
            await ctx.tick()
        assert (ctx.get(dut.state), ctx.get(dut.switch_open)) == (SAFE, 1)
    run(dut, tb)


def test_halt_in_safe_through_the_core_reaches_the_loop_pad():
    dut = GovernorCore(cap_entries=1, ticket_entries=1, t_throttle_ms=1, t_halt_ms=1, ms_shift=1, t_boot_ms=50)

    async def tb(ctx):
        ctx.set(dut.hb.window, 3)
        await pulse(ctx, dut.hb.hb_valid)
        ctx.set(dut.loop_sense, 1)
        await ctx.tick()
        assert ctx.get(dut.halt.state) == RUN
        ctx.set(dut.tick, 1)                                   # let the heartbeat run out and the rungs climb
        for _ in range(40):
            await ctx.tick()
        ctx.set(dut.tick, 0)
        assert ctx.get(dut.halt.state) == SAFE and ctx.get(dut.loop_out_open) == 0
        await pulse(ctx, dut.halt.cmd_halt)
        assert ctx.get(dut.loop_out_open) == 1 and ctx.get(dut.halt.state) == SAFE and ctx.get(dut.pwr_en) == 0
        ctx.set(dut.csr_addr, 0x00C)
        assert ctx.get(dut.csr_rdata) & 0x7 == C_COMMAND       # CAUSE says who stopped it
        ctx.set(dut.csr_addr, 0x07C)
        assert ctx.get(dut.csr_rdata) >> 1 & 1 == 1            # LOOP bit 1: own switch open
    run(dut, tb)


def test_halt_in_safe_keeps_a_tamper_cause():
    dut = HaltSeq()

    async def tb(ctx):
        await pulse(ctx, dut.tamper)
        await pulse(ctx, dut.cmd_halt)
        assert (ctx.get(dut.state), ctx.get(dut.cause), ctx.get(dut.switch_open)) == (SAFE, C_TAMPER, 1)
    run(dut, tb)


# ------------------------------------------------------------------------------- call 2: the first heartbeat
def core(**kw):
    return GovernorCore(cap_entries=1, ticket_entries=1, ms_shift=1, **{"t_boot_ms": 3, **kw})


async def ms(ctx, dut, n):
    """n milliseconds of the small build (2 microsecond ticks each)."""
    ctx.set(dut.tick, 1)
    for _ in range(2 * n):
        await ctx.tick()
    ctx.set(dut.tick, 0)


def csr(ctx, dut, addr):
    ctx.set(dut.csr_addr, addr)
    return ctx.get(dut.csr_rdata)


def test_no_first_heartbeat_is_loud_and_named_after_the_boot_window():
    dut = core()

    async def tb(ctx):
        await ms(ctx, dut, 2)
        assert csr(ctx, dut, 0x084) & NFH == 0                 # inside the window: quiet
        await ms(ctx, dut, 2)
        await ctx.tick()
        assert ctx.get(dut.halt.no_first_hb) == 1
        assert csr(ctx, dut, 0x084) & NFH, "ALARMS bit 31 NO_FIRST_HEARTBEAT not set past the boot window"
        assert csr(ctx, dut, 0x00C) >> 3 & 1 == 1              # CAUSE bit 3: waiting for the first heartbeat
        assert csr(ctx, dut, 0x00C) & 0x7 == C_NONE            # and no sequencer cause: nobody halted it
        assert csr(ctx, dut, 0x088) >= 3                       # BOOT_WAIT: how long it has waited, ms
        assert csr(ctx, dut, 0x008) == HALTED_INITIAL and ctx.get(dut.loop_out_open) == 1   # still holds the rack
        assert (ctx.get(dut.pwrbrk_n), ctx.get(dut.perst_n), ctx.get(dut.pwr_en)) == (0, 0, 0)
    run(dut, tb)


def test_no_first_heartbeat_alarm_is_hardware_owned_and_sticky():
    dut = core()

    async def tb(ctx):
        ctx.set(dut.alarms.set_mask, NFH | EXC | 1)            # firmware tries to raise the hardware bits
        await ctx.tick()
        ctx.set(dut.alarms.set_mask, 0)
        assert csr(ctx, dut, 0x084) == 1, "firmware raised a hardware-owned alarm bit"
        await ms(ctx, dut, 4)
        await ctx.tick()
        assert csr(ctx, dut, 0x084) & NFH
        ctx.set(dut.hb.window, 5)                              # the first heartbeat arrives at last
        await pulse(ctx, dut.hb.hb_valid)
        await ctx.tick()
        assert ctx.get(dut.halt.no_first_hb) == 0 and csr(ctx, dut, 0x00C) >> 3 & 1 == 0
        assert csr(ctx, dut, 0x084) & NFH                      # the record stays until an authorized clear
        ctx.set(dut.alarms.clear_mask, NFH)
        await ctx.tick()
        assert csr(ctx, dut, 0x084) & NFH                      # an unauthorized clear does nothing
        ctx.set(dut.alarms.clear_authorized, 1)
        await ctx.tick()
        ctx.set(dut.alarms.clear_authorized, 0)
        ctx.set(dut.alarms.clear_mask, 0)
        assert csr(ctx, dut, 0x084) & NFH == 0
        await ms(ctx, dut, 20)                                      # armed once: never raised again, heartbeat or not
        assert csr(ctx, dut, 0x084) & NFH == 0
    run(dut, tb)


def test_heartbeat_inside_the_window_never_raises_the_alarm():
    dut = core()

    async def tb(ctx):
        await ms(ctx, dut, 1)
        ctx.set(dut.hb.window, 2)
        await pulse(ctx, dut.hb.hb_valid)
        ctx.set(dut.loop_sense, 1)
        await ms(ctx, dut, 30)
        assert csr(ctx, dut, 0x084) & NFH == 0 and ctx.get(dut.halt.no_first_hb) == 0
        assert 1 <= csr(ctx, dut, 0x088) <= 2                  # BOOT_WAIT froze when it armed
    run(dut, tb)


def test_exclude_closes_the_loop_and_keeps_the_levers_on():
    dut = core()

    async def tb(ctx):
        await ms(ctx, dut, 4)
        await pulse(ctx, dut.halt.cmd_exclude)
        assert ctx.get(dut.loop_out_open) == 0, "EXCLUDE did not close the loop switch"
        assert csr(ctx, dut, 0x008) == HALTED_INITIAL
        assert (ctx.get(dut.pwrbrk_n), ctx.get(dut.perst_n), ctx.get(dut.pwr_en)) == (0, 0, 0)
        await ctx.tick()
        assert csr(ctx, dut, 0x084) & EXC and csr(ctx, dut, 0x084) & NFH   # excluded, and still waiting: both loud
        assert csr(ctx, dut, 0x00C) >> 4 & 1 == 1                          # CAUSE bit 4: excluded
        ctx.set(dut.loop_sense, 1)                             # the rest of the rack runs; this chip does not
        await ms(ctx, dut, 20)
        assert csr(ctx, dut, 0x008) == HALTED_INITIAL and ctx.get(dut.pwr_en) == 0 and ctx.get(dut.halt.excluded)
        ctx.set(dut.hb.window, 5)                              # a valid heartbeat ends the exclusion the normal way
        await pulse(ctx, dut.hb.hb_valid)
        await ctx.tick()
        assert ctx.get(dut.halt.excluded) == 0 and csr(ctx, dut, 0x008) == RUN
    run(dut, tb)


def _exclude_has_no_effect(prep, want_state, want_cause):
    dut = HaltSeq(t_throttle=2, t_halt=2)

    async def tb(ctx):
        await prep(ctx, dut)
        before = (ctx.get(dut.state), ctx.get(dut.cause), ctx.get(dut.switch_open))
        assert before[:2] == (want_state, want_cause)
        await pulse(ctx, dut.cmd_exclude)
        after = (ctx.get(dut.state), ctx.get(dut.cause), ctx.get(dut.switch_open))
        assert after == before and ctx.get(dut.excluded) == 0, f"EXCLUDE changed {before} to {after}"
    run(dut, tb)


def test_exclude_cannot_close_a_loop_opened_by_loop_loss():
    async def prep(ctx, dut):
        await to_run(ctx, dut)
        await pulse(ctx, dut.loop_lost)
        ctx.set(dut.hb_ok, 0)
    _exclude_has_no_effect(prep, HALT, C_LOOP)


def test_exclude_cannot_close_a_loop_opened_by_a_command():
    async def prep(ctx, dut):
        await pulse(ctx, dut.cmd_halt)
    _exclude_has_no_effect(prep, HALT, C_COMMAND)


def test_exclude_cannot_close_a_loop_opened_by_tamper():
    async def prep(ctx, dut):
        await pulse(ctx, dut.tamper)
    _exclude_has_no_effect(prep, SAFE, C_TAMPER)


def test_exclude_does_nothing_to_a_running_or_throttled_chip():
    async def prep_run(ctx, dut):
        await to_run(ctx, dut)
    _exclude_has_no_effect(prep_run, RUN, C_NONE)

    async def prep_thr(ctx, dut):
        await to_run(ctx, dut)
        await pulse(ctx, dut.local_trip)
    _exclude_has_no_effect(prep_thr, THROTTLE, C_LOCAL)


def test_halt_or_tamper_ends_an_exclusion_with_the_loop_open():
    for strobe, want in (("cmd_halt", (HALT, C_COMMAND)), ("tamper", (SAFE, C_TAMPER))):
        dut = HaltSeq()

        async def tb(ctx, dut=dut, strobe=strobe, want=want):
            await pulse(ctx, dut.cmd_exclude)
            assert ctx.get(dut.excluded) == 1 and ctx.get(dut.switch_open) == 0
            await pulse(ctx, getattr(dut, strobe))
            assert ctx.get(dut.excluded) == 0 and ctx.get(dut.switch_open) == 1
            assert (ctx.get(dut.state), ctx.get(dut.cause)) == want
        run(dut, tb)
