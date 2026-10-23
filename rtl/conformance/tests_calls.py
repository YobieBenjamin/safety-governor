# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Conformance tests for Yobie's two design calls of 23 October 2026 (requirements R-144 to R-152, quoting the
sentences added to docs/04 sections 2 and 3 that day). The halt-in-SAFE reproducers of F-07 live on in
tests_findings.py as ordinary guards; these cover the rest, on the RTL blocks and on the model beside them.
"""
from __future__ import annotations

from govsim import reasons
from govsim.cluster import build_rack

from rtl.governor_rtl.halt import C_COMMAND, C_LOCAL, C_LOOP, C_TAMPER, HALT, HALTED_INITIAL, RUN, SAFE

from .framework import B, conformance, levers, sim
from .tests_blocks import _to_run


async def _pulse(ctx, sig):
    ctx.set(sig, 1)
    await ctx.tick()
    ctx.set(sig, 0)


@conformance("R-144", "R-145")
def test_calls_halt_in_safe_from_local_cause_opens_loop_keeps_safe():
    """A chip in SAFE on a local cause: a HALT opens the switch, the rung stays SAFE, power stays off, cause command."""
    dut = B.HaltSeq(t_throttle=1, t_halt=1)

    async def tb(ctx):
        await _to_run(ctx, dut)
        await _pulse(ctx, dut.local_trip)
        ctx.set(dut.hb_ok, 0)
        ctx.set(dut.tick, 1)
        for _ in range(3):
            await ctx.tick()
        ctx.set(dut.tick, 0)
        assert (ctx.get(dut.state), ctx.get(dut.cause), ctx.get(dut.switch_open)) == (SAFE, C_LOCAL, 0)
        await _pulse(ctx, dut.cmd_halt)
        assert (ctx.get(dut.state), ctx.get(dut.cause), ctx.get(dut.switch_open)) == (SAFE, C_COMMAND, 1)
        assert levers(ctx, dut) == (1, 1, 0)
    sim(dut, tb)


@conformance("R-144")
def test_calls_halt_opens_loop_from_every_rung():
    """cmd_halt from HALTED_INITIAL, RUN, THROTTLE, HALT and SAFE: the switch is open afterwards, every time."""
    for prep in ("boot", "run", "throttle", "halt", "safe"):
        dut = B.HaltSeq(t_throttle=1, t_halt=1)

        async def tb(ctx, dut=dut, prep=prep):
            if prep != "boot":
                await _to_run(ctx, dut)
            if prep in ("throttle", "halt", "safe"):
                await _pulse(ctx, dut.local_trip)
                ctx.set(dut.hb_ok, 0)
                ctx.set(dut.tick, 1)
                for _ in range({"throttle": 0, "halt": 1, "safe": 2}[prep]):
                    await ctx.tick()
                ctx.set(dut.tick, 0)
            await _pulse(ctx, dut.cmd_halt)
            assert ctx.get(dut.switch_open) == 1, f"HALT from {prep} left the switch closed"
        sim(dut, tb)


@conformance("R-145", "R-035")
def test_calls_model_halt_in_safe_stays_safe_and_opens_loop():
    """The model: a HALT to a governor in SAFE on a local cause leaves it in SAFE, power off, switch open."""
    rack = build_rack(1, "rack")
    rack.bring_up()
    g = rack.nodes[0].governor
    g.enter_safe_mode(reasons.HEARTBEAT_LOST)
    g._apply_rung("HALT", opens_loop=False)
    g._apply_rung("SAFE", opens_loop=False)
    assert rack.halt(g)["ok"]
    assert g.state == "SAFE" and g.levers["pwr_en"] is False and g.loop_switch_open is True


def _core():
    return B.GovernorCore(cap_entries=1, ticket_entries=1, ms_shift=1, t_boot_ms=3)


async def _ms(ctx, dut, n):
    ctx.set(dut.tick, 1)
    for _ in range(2 * n):
        await ctx.tick()
    ctx.set(dut.tick, 0)


def _csr(ctx, dut, a):
    ctx.set(dut.csr_addr, a)
    return ctx.get(dut.csr_rdata)


@conformance("R-146")
def test_calls_core_names_the_chip_waiting_for_its_first_heartbeat():
    """Past the boot window with no heartbeat: ALARMS bit 31, CAUSE bit 3, BOOT_WAIT, and the rack is still held."""
    dut = _core()

    async def tb(ctx):
        await _ms(ctx, dut, 2)
        assert _csr(ctx, dut, 0x084) >> 31 == 0
        await _ms(ctx, dut, 2)
        await ctx.tick()
        assert _csr(ctx, dut, 0x084) >> 31 == 1 and _csr(ctx, dut, 0x00C) >> 3 & 1 == 1 and _csr(ctx, dut, 0x088) >= 3
        assert _csr(ctx, dut, 0x008) == HALTED_INITIAL and ctx.get(dut.loop_out_open) == 1 and ctx.get(dut.pwr_en) == 0
    sim(dut, tb)


@conformance("R-147")
def test_calls_core_never_raises_no_first_heartbeat_once_armed():
    """A heartbeat inside the window, then a long silence (with clears and halts): bit 31 never rises."""
    dut = _core()

    async def tb(ctx):
        ctx.set(dut.hb.window, 1)
        await _pulse(ctx, dut.hb.hb_valid)
        await ctx.tick()
        await _ms(ctx, dut, 5)
        await _pulse(ctx, dut.halt.cmd_halt)
        await _ms(ctx, dut, 5)
        await _pulse(ctx, dut.halt.clear)
        await _ms(ctx, dut, 10)
        assert _csr(ctx, dut, 0x084) >> 31 == 0 and ctx.get(dut.halt.no_first_hb) == 0
    sim(dut, tb)


@conformance("R-148")
def test_calls_firmware_cannot_raise_the_hardware_alarm_bits():
    """set_mask with every bit: bits 31 and 30 stay clear, the firmware bits are set."""
    dut = _core()

    async def tb(ctx):
        ctx.set(dut.alarms.set_mask, 0xFFFF_FFFF)
        await ctx.tick()
        ctx.set(dut.alarms.set_mask, 0)
        assert _csr(ctx, dut, 0x084) == 0x3FFF_FFFF
    sim(dut, tb)


@conformance("R-149")
def test_calls_exclude_does_nothing_outside_waiting_for_first_heartbeat():
    """EXCLUDE in RUN, in HALT (loop loss, command), in SAFE (tamper): every register unchanged."""
    def preps():
        async def run(ctx, dut):
            await _to_run(ctx, dut)
        async def loop(ctx, dut):
            await _to_run(ctx, dut)
            await _pulse(ctx, dut.loop_lost)
            ctx.set(dut.hb_ok, 0)
        async def cmd(ctx, dut):
            await _pulse(ctx, dut.cmd_halt)
        async def tamper(ctx, dut):
            await _pulse(ctx, dut.tamper)
        return ((run, RUN, 0), (loop, HALT, C_LOOP), (cmd, HALT, C_COMMAND), (tamper, SAFE, C_TAMPER))
    for prep, st, cause in preps():
        dut = B.HaltSeq()

        async def tb(ctx, dut=dut, prep=prep, st=st, cause=cause):
            await prep(ctx, dut)
            regs = lambda: tuple(ctx.get(getattr(dut, k)) for k in ("state", "cause", "switch_open", "timer", "excluded"))
            before = regs()
            assert before[:2] == (st, cause)
            await _pulse(ctx, dut.cmd_exclude)
            assert regs() == before, f"EXCLUDE in state {st} changed {before} to {regs()}"
        sim(dut, tb)


@conformance("R-150")
def test_calls_exclude_closes_the_pad_and_keeps_every_lever():
    """Through the core: the loop pad closes, the three pins stay safe, ALARMS bit 30 and CAUSE bit 4 show it."""
    dut = _core()

    async def tb(ctx):
        await _ms(ctx, dut, 4)
        await _pulse(ctx, dut.halt.cmd_exclude)
        ctx.set(dut.loop_sense, 1)
        await _ms(ctx, dut, 5)
        assert ctx.get(dut.loop_out_open) == 0
        assert (ctx.get(dut.pwrbrk_n), ctx.get(dut.perst_n), ctx.get(dut.pwr_en)) == (0, 0, 0)
        assert _csr(ctx, dut, 0x084) >> 30 & 1 == 1 and _csr(ctx, dut, 0x00C) >> 4 & 1 == 1
    sim(dut, tb)


@conformance("R-151")
def test_calls_exclusion_ends_by_heartbeat_halt_or_tamper_only():
    """Ends on a heartbeat (arms, runs), on a HALT and on a tamper (loop open); a CLEAR or time does not end it."""
    for end, want in (("hb_ok", RUN), ("cmd_halt", HALT), ("tamper", SAFE)):
        dut = B.HaltSeq()

        async def tb(ctx, dut=dut, end=end, want=want):
            await _pulse(ctx, dut.cmd_exclude)
            await _pulse(ctx, dut.clear)
            ctx.set(dut.tick, 1)
            for _ in range(20):
                await ctx.tick()
            ctx.set(dut.tick, 0)
            assert ctx.get(dut.excluded) == 1
            ctx.set(dut.loop_sense, 1)
            await _pulse(ctx, getattr(dut, end))
            assert ctx.get(dut.excluded) == 0 and ctx.get(dut.state) == want
            assert ctx.get(dut.switch_open) == (0 if end == "hb_ok" else 1)
        sim(dut, tb)


@conformance("R-152")
def test_calls_model_logs_every_exclude_with_its_signer():
    """The model: an accepted EXCLUDE and a refused one are both in the log, the accepted one with its signer."""
    rack = build_rack(2, "rack")
    stuck = rack.nodes[1].governor
    rack.fabric.down.add(stuck.chip_id)
    rack.heartbeat()
    assert rack.exclude(stuck)["ok"]
    assert stuck.log.has("exclude", by=rack.authority_key.public.key_id, chip_id=stuck.chip_id)
    g = rack.nodes[0].governor                                  # armed: refused, and the refusal is logged too
    r = rack.exclude(g)
    assert not r["ok"] and g.log.has("deny.exclude", why=reasons.EXCLUDE_NOT_WAITING)
