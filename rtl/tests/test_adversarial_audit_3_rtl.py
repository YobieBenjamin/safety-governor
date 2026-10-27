# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Adversarial audit 3, the hard core: regression tests for the five RTL findings.

1. The heartbeat window was not clamped (rtl/governor_rtl/heartbeat.py).
2. A halt was forgotten across a power cycle (rtl/governor_rtl/halt.py: the non-volatile rung record).
3. CLEAR was a bare firmware strobe (halt.py ``clear_authorized``, wired in top.py from the mailbox).
4. One frame at the top of the 32-bit sequence space ended a key (rtl/governor_rtl/mailbox.py: 64 bits, epoch reset).
5. The model now sends a lost heartbeat to HALT, not THROTTLE; the RTL does the same.

The auditor's tests for findings 1 and 3 are kept here as written (only the import path changed). For findings 2 and 4
the auditor's literal tests assert the wrong property; each faithful test below says why in its docstring.
The formal side of the same fixes is in rtl/formal (heartbeat.sv, halt_seq.sv, halt_seq_persist.sv, mailbox.sv,
governor_core.sv) with a mutant for each line.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from amaranth import Signal  # noqa: E402
from amaranth.hdl import ResetInserter  # noqa: E402
from amaranth.sim import Simulator  # noqa: E402

from rtl.governor_rtl import GovernorCore, HaltSeq, Heartbeat, Mailbox  # noqa: E402
from rtl.governor_rtl.halt import (C_LOCAL, C_PERSIST, C_TAMPER, HALT, HALTED_INITIAL, RUN, SAFE,  # noqa: E402
                                   THROTTLE)
from rtl.governor_rtl.mailbox import S_BAD_SEQ, S_OK  # noqa: E402
from rtl.governor_rtl.top import MBOX_CLEAR  # noqa: E402

MAX_HB_MS = 5_000      # docs/04 section 9: heartbeat expiry 5 s, "the governor clamps any signed window to it"
HEARTBEAT_CMD = 0x0E   # docs/04 section 3, govsim/governor.py MAILBOX_CODES


def run(dut, tb):
    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(tb)
    sim.run()


async def pulse(ctx, *sigs):
    for s in sigs:
        ctx.set(s, 1)
    await ctx.tick()
    for s in sigs:
        ctx.set(s, 0)


# ------------------------------------------------------------------------------------------------ finding 1
def test_hard_core_heartbeat_never_outlives_the_policy_expiry():
    """Finding 1 (the auditor's own test, unchanged). The model clamps the window (govsim/governor.py _heartbeat); the
    hard core loaded whatever 32-bit window firmware handed it. A firmware fault or a mis-signed window kept the core
    alive about 49 days. Now the core loads min(window, 5000)."""
    dut = Heartbeat()

    async def tb(ctx):
        ctx.set(dut.window, (1 << 32) - 1)
        ctx.set(dut.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb_valid, 0)
        ctx.set(dut.tick, 1)
        for _ in range(MAX_HB_MS + 10):
            await ctx.tick()
        assert ctx.get(dut.expired) == 1, "hard-core heartbeat still live long after the 5 s policy maximum"

    run(dut, tb)


def test_heartbeat_clamp_is_exact_and_reaches_the_core_csr():
    """Finding 1: the clamp loads exactly 5000 for any larger window, a smaller window unchanged, and the core's
    HB_REMAIN (0x078) shows the clamped value. Narrow test builds clamp to what the register holds."""
    assert Heartbeat().max_window == MAX_HB_MS and Heartbeat(width=8).max_window == 255
    dut = GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        for window, want in (((1 << 32) - 1, MAX_HB_MS), (MAX_HB_MS + 1, MAX_HB_MS), (MAX_HB_MS, MAX_HB_MS), (1234, 1234)):
            ctx.set(dut.hb.window, window)
            await pulse(ctx, dut.hb.hb_valid)
            ctx.set(dut.csr_addr, 0x078)
            assert ctx.get(dut.csr_rdata) == want, (window, ctx.get(dut.csr_rdata))

    run(dut, tb)


# ------------------------------------------------------------------------------------------------ finding 2
def _seq_with_reset():
    """HaltSeq with its sync domain reset driven by a testbench signal, as a power cycle drives it. ResetInserter resets
    every register except the reset_less ones, which stand for the NVM or fuse-backed rung record."""
    rst = Signal()
    seq = HaltSeq(t_throttle=5, t_halt=50, t_boot=3)
    return rst, seq, ResetInserter(rst)(seq)


async def _run_then(ctx, seq, strobe):
    ctx.set(seq.hb_ok, 1)
    ctx.set(seq.loop_sense, 1)
    await ctx.tick()
    assert ctx.get(seq.state) == RUN
    await pulse(ctx, strobe)


async def _power_cycle(ctx, rst):
    await pulse(ctx, rst)


def test_a_halt_survives_a_power_cycle_in_the_hard_core():
    """Finding 2, the faithful version. The chip reaches RUN, is HALTed, and is power cycled (the sync domain is reset
    while the valid heartbeat and the loop current stay present). It must come back halted, not armed: HALTED_INITIAL
    with every lever on and the loop open for one cycle, then HALT with cause C_PERSIST and the loop open, and it must
    not reach RUN however long the heartbeat and the loop stay good. A firmware clear alone does not release it; an
    authorized clear does, and then the chip arms and runs as usual.

    Why not the auditor's literal test: it builds a second, brand new HaltSeq object in a second Simulator and expects
    it to remember the first one's halt. A fresh object is a different chip with fresh storage; no register of any kind,
    volatile or not, survives into it, so that test cannot express non-volatile state and cannot pass for any design.
    The property it is after (a reset of THIS chip does not forget a halt) is what this test checks."""
    rst, seq, dut = _seq_with_reset()

    async def tb(ctx):
        await _run_then(ctx, seq, seq.cmd_halt)
        assert ctx.get(seq.state) == HALT and ctx.get(seq.rung_nv) == 1
        await _power_cycle(ctx, rst)
        # out of reset: the boot rung, every lever asserted, loop switch open; the record survived
        assert ctx.get(seq.state) == HALTED_INITIAL and ctx.get(seq.switch_open) == 1 and ctx.get(seq.rung_nv) == 1
        assert (ctx.get(seq.pwrbrk), ctx.get(seq.perst), ctx.get(seq.pwr_en)) == (1, 1, 0)
        await ctx.tick()
        assert (ctx.get(seq.state), ctx.get(seq.cause), ctx.get(seq.switch_open)) == (HALT, C_PERSIST, 1)
        for _ in range(30):                                      # a valid heartbeat and loop current, held: no RUN
            await ctx.tick()
            assert ctx.get(seq.state) == HALT and ctx.get(seq.switch_open) == 1 and ctx.get(seq.hb_seen) == 0
        await pulse(ctx, seq.clear)                              # the firmware's clear alone: refused in hardware
        assert ctx.get(seq.state) == HALT and ctx.get(seq.rung_nv) == 1
        await pulse(ctx, seq.clear, seq.clear_authorized)        # an authorized clear erases the record
        assert ctx.get(seq.state) == HALTED_INITIAL and ctx.get(seq.rung_nv) == 0
        await ctx.tick()
        assert ctx.get(seq.state) == RUN, "after an authorized clear the chip arms and runs as usual"
        await _power_cycle(ctx, rst)                             # and a power cycle of a cleared chip is a normal boot
        await ctx.tick()
        assert ctx.get(seq.state) == RUN

    run(dut, tb)


def test_safe_and_local_halts_also_survive_a_power_cycle():
    """Finding 2: a chip in SAFE comes back in SAFE (slot power stays off; a power cycle never lowers the rung), and a
    halt on a local cause (a lost heartbeat, loop switch closed) comes back as HALT with the loop open. A reset in the
    middle of the restore is harmless: the record is still there."""
    for strobe, want in (("tamper", SAFE), ("hb_expired", HALT)):
        rst, seq, dut = _seq_with_reset()

        async def tb(ctx, seq=seq, rst=rst, strobe=strobe, want=want):
            await _run_then(ctx, seq, getattr(seq, strobe))
            assert ctx.get(seq.state) == want
            await _power_cycle(ctx, rst)
            await _power_cycle(ctx, rst)                         # twice in a row: still remembered
            await ctx.tick()
            assert (ctx.get(seq.state), ctx.get(seq.cause), ctx.get(seq.switch_open)) == (want, C_PERSIST, 1), strobe
            if want == SAFE:
                assert ctx.get(seq.pwr_en) == 0
            await pulse(ctx, seq.cmd_exclude)                    # an EXCLUDE cannot close the switch of a halted chip
            assert ctx.get(seq.switch_open) == 1 and ctx.get(seq.excluded) == 0

        run(dut, tb)


# ------------------------------------------------------------------------------------------------ finding 3
def test_clear_requires_an_authorized_mailbox_clear_in_the_hard_core():
    """Finding 3 (the auditor's own test, unchanged). docs/04: CLEAR needs the authority quorum, the cause logged and a
    neighbour ack. In the hard core ``clear`` was a bare input strobe from firmware. Now a clear takes effect only
    together with ``clear_authorized``, which the core drives from a dispatched, verified CLEAR frame."""
    dut = HaltSeq(t_throttle=5, t_halt=5, t_boot=3)

    async def tb(ctx):
        ctx.set(dut.hb_ok, 1); ctx.set(dut.loop_sense, 1)
        await ctx.tick(); await ctx.tick()
        ctx.set(dut.cmd_halt, 1); await ctx.tick(); ctx.set(dut.cmd_halt, 0)
        assert ctx.get(dut.state) == HALT
        ctx.set(dut.clear, 1); await ctx.tick(); ctx.set(dut.clear, 0)
        await ctx.tick(); await ctx.tick()
        assert ctx.get(dut.state) == HALT, "a firmware strobe on 'clear', with no verified CLEAR frame, released the halt"

    run(dut, tb)


def test_core_clear_lands_only_on_a_dispatched_clear_frame():
    """Finding 3 through the core: the firmware's clear held high does nothing on its own, nor with a verified
    HEARTBEAT frame dispatching, nor with a CLEAR frame whose signature fails; it lands in the cycle a verified CLEAR
    (0x10) frame dispatches."""
    dut = GovernorCore(cap_entries=1, ticket_entries=1)
    m = dut.mbox

    async def frame(ctx, seq_no, cmd, sig_ok):
        ctx.set(m.frame_seq, seq_no); ctx.set(m.cmd, cmd); ctx.set(m.signed_cmd, cmd); ctx.set(m.epoch_exempt, 1)
        await pulse(ctx, dut.doorbell)
        ctx.set(m.sig_done, 1); ctx.set(m.sig_ok, sig_ok)
        dispatched = ctx.get(m.dispatch)
        await ctx.tick()
        ctx.set(m.sig_done, 0)
        return dispatched

    async def tb(ctx):
        assert MBOX_CLEAR == 0x10
        await pulse(ctx, dut.halt.cmd_halt)
        assert ctx.get(dut.halt.state) == HALT
        ctx.set(dut.halt.clear, 1)                                # the firmware's approval, held as a level
        for _ in range(5):
            await ctx.tick()
        assert ctx.get(dut.halt.state) == HALT
        assert await frame(ctx, 1, HEARTBEAT_CMD, 1) == 1        # a verified frame, but not a CLEAR
        assert ctx.get(dut.halt.state) == HALT
        assert await frame(ctx, 2, MBOX_CLEAR, 0) == 0           # a CLEAR whose signature fails
        assert ctx.get(dut.halt.state) == HALT
        assert await frame(ctx, 3, MBOX_CLEAR, 1) == 1           # a verified CLEAR: the halt is released
        assert ctx.get(dut.halt.state) == HALTED_INITIAL
        ctx.set(dut.halt.clear, 0)
        await pulse(ctx, dut.halt.cmd_halt)                       # and without the firmware's approval a CLEAR does nothing
        assert await frame(ctx, 4, MBOX_CLEAR, 1) == 1
        assert ctx.get(dut.halt.state) == HALT

    run(dut, tb)


# ------------------------------------------------------------------------------------------------ finding 4
async def _mbox_frame(ctx, dut, seq_no):
    ctx.set(dut.frame_seq, seq_no); ctx.set(dut.key_slot, 0); ctx.set(dut.cmd, 6); ctx.set(dut.signed_cmd, 6)
    ctx.set(dut.epoch_match, 1); ctx.set(dut.doorbell, 1)
    await ctx.tick(); ctx.set(dut.doorbell, 0)
    ctx.set(dut.sig_done, 1); ctx.set(dut.sig_ok, 1)
    await ctx.tick(); ctx.set(dut.sig_done, 0)
    await ctx.tick()
    return ctx.get(dut.status)


def test_mailbox_sequence_space_outlives_the_chip():
    """Finding 4, the faithful version. After an accepted frame at the top of the old 32-bit space, the key is not
    ended: higher numbers are still there (the register is 64 bits), a lower number in the same epoch is still refused
    (no replay), and once the epoch advances the slot restarts at zero, so a frame numbered 1 in the new epoch is
    accepted, once.

    Why not the auditor's literal test: it asserts that frame 1 is accepted right after frame 2**32 - 1 with no epoch
    change. That is a replay: in one epoch, under one key, a sequence number lower than one already accepted is exactly
    what the mailbox must refuse (docs/04 section 3, govsim _check_signed). Making it pass would reopen every old frame."""
    dut = Mailbox()

    async def tb(ctx):
        assert await _mbox_frame(ctx, dut, (1 << 32) - 1) == S_OK
        assert await _mbox_frame(ctx, dut, 1) == S_BAD_SEQ, "a lower sequence in the same epoch is a replay"
        assert await _mbox_frame(ctx, dut, 1 << 32) == S_OK, "the space goes on past 32 bits"
        assert await _mbox_frame(ctx, dut, (1 << 64) - 2) == S_OK
        await pulse(ctx, dut.epoch_advanced)                     # a new epoch: every key slot restarts at zero
        assert all(ctx.get(s) == 0 for s in dut.last_seq)
        assert await _mbox_frame(ctx, dut, 1) == S_OK
        assert await _mbox_frame(ctx, dut, 1) == S_BAD_SEQ, "replay inside the new epoch is still refused"

    run(dut, tb)


def test_64_bit_sequence_space_cannot_be_exhausted_in_the_product_life():
    """Finding 4, the arithmetic. At 1,000 commands a second (the auditor's rate) a 32-bit slot runs out in 49.7 days;
    a 64-bit slot, even at a million commands a second, lasts about 584,000 years, against a 10-year product life
    (docs/04 section 11). Every register really is 64 bits."""
    dut = Mailbox()
    assert len(dut.frame_seq) == 64 and all(len(s) == 64 for s in dut.last_seq)
    year_s = 365.25 * 24 * 3600
    assert (1 << 32) / 1_000 / 86_400 < 50                       # the old space: under 50 days
    years_64 = (1 << 64) / 1_000_000 / year_s
    assert years_64 > 500_000 and years_64 > 10 * 10_000


def test_core_epoch_advance_restarts_the_slots_and_mbox_seq_has_a_high_word():
    """Finding 4 through the core: an epoch commit with quorum of a DIFFERENT epoch restarts the key slots; a commit
    without quorum, or a re-commit of the epoch in force, does not (it would reopen this epoch's frames). MBOX_SEQ
    (0x108) reads the low word of key slot 0 and MBOX_SEQ_HI (0x10C) the high word."""
    dut = GovernorCore(cap_entries=1, ticket_entries=1)
    m, e = dut.mbox, dut.epoch

    async def frame(ctx, seq_no):
        ctx.set(m.frame_seq, seq_no); ctx.set(m.key_slot, 0); ctx.set(m.cmd, 6); ctx.set(m.signed_cmd, 6)
        ctx.set(m.epoch_match, 1)
        await pulse(ctx, dut.doorbell)
        ctx.set(m.sig_done, 1); ctx.set(m.sig_ok, 1)
        await ctx.tick()
        ctx.set(m.sig_done, 0)

    def mbox_seq(ctx):
        ctx.set(dut.csr_addr, 0x108)
        lo = ctx.get(dut.csr_rdata)
        ctx.set(dut.csr_addr, 0x10C)
        return (ctx.get(dut.csr_rdata) << 32) | lo

    async def tb(ctx):
        await frame(ctx, (5 << 32) | 7)
        assert mbox_seq(ctx) == (5 << 32) | 7
        ctx.set(e.new_epoch, 0xABC)
        await pulse(ctx, e.commit)                                # no quorum: nothing moves
        assert mbox_seq(ctx) == (5 << 32) | 7
        ctx.set(e.quorum_ok, 1)
        await pulse(ctx, e.commit)                                # a new epoch: the slots restart
        assert ctx.get(e.epoch) == 0xABC and mbox_seq(ctx) == 0
        await frame(ctx, 3)
        await pulse(ctx, e.commit)                                # the same epoch again: not an advance
        assert mbox_seq(ctx) == 3

    run(dut, tb)


# ------------------------------------------------------------------------------------------------ finding 5
def test_lost_heartbeat_halts_from_run_and_throttle_with_the_loop_closed():
    """Finding 5 (model alignment): a lost heartbeat in RUN or THROTTLE goes to HALT (brake AND reset; a braked GPU
    still computes at half clock) with the local cause, so the loop switch stays closed and the neighbours keep
    running. local_trip and cmd_throttle still throttle. Matches govsim: the default policy maps HEARTBEAT_LOST to HALT
    and LOOP_OPENING_CAUSES does not list it."""
    from govsim import reasons
    from govsim.cluster import build_rack
    from govsim.governor import LOOP_OPENING_CAUSES
    rack = build_rack(1, "rack")
    rack.bring_up()
    assert rack.nodes[0].governor.policy["safe_mode"]["causes"][reasons.HEARTBEAT_LOST] == "HALT"
    assert reasons.HEARTBEAT_LOST not in LOOP_OPENING_CAUSES

    for start in (RUN, THROTTLE):
        dut = HaltSeq(t_throttle=5, t_halt=5)

        async def tb(ctx, dut=dut, start=start):
            ctx.set(dut.hb_ok, 1); ctx.set(dut.loop_sense, 1)
            await ctx.tick()
            if start == THROTTLE:
                await pulse(ctx, dut.local_trip)
                assert ctx.get(dut.state) == THROTTLE
            await pulse(ctx, dut.hb_expired)
            assert (ctx.get(dut.state), ctx.get(dut.cause), ctx.get(dut.switch_open)) == (HALT, C_LOCAL, 0), start
            assert (ctx.get(dut.pwrbrk), ctx.get(dut.perst), ctx.get(dut.pwr_en)) == (1, 1, 1)

        run(dut, tb)
    assert C_TAMPER != C_PERSIST and C_PERSIST < 8                 # the cause register is still 3 bits
