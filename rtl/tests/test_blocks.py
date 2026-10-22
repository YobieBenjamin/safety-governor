"""Simulation of every block's invariant (docs/07-verification-plan.md §3), with Amaranth's
built-in simulator. No external tools."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from amaranth.sim import Simulator  # noqa: E402

from rtl.governor_rtl import (Alarms, CapTable, EpochReg, GovernorCore, HaltSeq, Heartbeat, Lifecycle, LoopIO,  # noqa: E402
                              Mailbox, MeasureReg, Meter, MonotonicCounter, TicketStore)
from rtl.governor_rtl.cap_table import R_BUDGET, R_EXPIRED, R_NO_CAP, R_OK, R_STALE_EPOCH  # noqa: E402
from rtl.governor_rtl.halt import C_COMMAND, C_LOCAL, C_LOOP, C_TAMPER, HALT, HALTED_INITIAL, RUN, SAFE, THROTTLE  # noqa: E402
from rtl.governor_rtl.lifecycle import PRODUCTION, TEST  # noqa: E402
from rtl.governor_rtl.mailbox import S_BAD_EPOCH, S_BAD_SEQ, S_BAD_SIG, S_OK, S_REFUSED, S_WRONG_CMD  # noqa: E402


def run(dut, testbench):
    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(testbench)
    sim.run()


def test_monotonic_never_decreases():
    dut = MonotonicCounter(width=16)

    async def tb(ctx):
        ctx.set(dut.hwm, 100)
        ctx.set(dut.load_hwm, 1)
        await ctx.tick()
        ctx.set(dut.load_hwm, 0)
        assert ctx.get(dut.value) == 100
        last = 100
        for _ in range(20):
            ctx.set(dut.inc, 1)
            await ctx.tick()
            v = ctx.get(dut.value)
            assert v >= last
            last = v
        ctx.set(dut.inc, 0)
        ctx.set(dut.dec_req, 1)
        await ctx.tick()
        assert ctx.get(dut.refused) == 1 and ctx.get(dut.value) == last
        ctx.set(dut.dec_req, 0)
        ctx.set(dut.hwm, 5)                       # a lower high-water mark cannot pull the counter down
        ctx.set(dut.load_hwm, 1)
        await ctx.tick()
        assert ctx.get(dut.value) == last

    run(dut, tb)


def test_measure_reg_changes_only_through_extend():
    dut = MeasureReg(width=32)

    async def tb(ctx):
        assert ctx.get(dut.value) == 0
        ctx.set(dut.hash_done, 1)
        ctx.set(dut.hash_out, 0xDEADBEEF)          # the engine output with no request pending
        await ctx.tick()
        await ctx.tick()
        assert ctx.get(dut.value) == 0             # ignored: no extend was issued
        ctx.set(dut.hash_done, 0)
        ctx.set(dut.data, 0x1234)
        ctx.set(dut.extend, 1)
        assert ctx.get(dut.hash_req) == 1
        await ctx.tick()
        ctx.set(dut.extend, 0)
        assert ctx.get(dut.busy) == 1
        ctx.set(dut.hash_done, 1)
        ctx.set(dut.hash_out, 0xCAFEF00D)
        await ctx.tick()
        ctx.set(dut.hash_done, 0)
        assert ctx.get(dut.value) == 0xCAFEF00D

    run(dut, tb)


def test_epoch_reg_ignores_host_and_needs_quorum():
    dut = EpochReg(width=32)

    async def tb(ctx):
        ctx.set(dut.host_wr, 1)
        ctx.set(dut.host_data, 0xBAD)
        await ctx.tick()
        assert ctx.get(dut.epoch) == 0 and ctx.get(dut.host_refused) == 1
        ctx.set(dut.host_wr, 0)
        ctx.set(dut.new_epoch, 0xABCD1234)
        ctx.set(dut.commit, 1)
        ctx.set(dut.quorum_ok, 0)
        await ctx.tick()
        assert ctx.get(dut.epoch) == 0
        ctx.set(dut.quorum_ok, 1)
        await ctx.tick()
        assert ctx.get(dut.epoch) == 0xABCD1234 and ctx.get(dut.epoch_tag) == 0x1234

    run(dut, tb)


def test_lifecycle_monotone_and_debug_dead_in_production():
    dut = Lifecycle()

    async def tb(ctx):
        ctx.set(dut.debug_req, 1)
        await ctx.tick()
        assert ctx.get(dut.debug_grant) == 1
        ctx.set(dut.advance, 1)
        ctx.set(dut.advance_to, PRODUCTION)
        await ctx.tick()
        ctx.set(dut.advance, 0)
        assert ctx.get(dut.state) == PRODUCTION
        assert ctx.get(dut.debug_grant) == 0 and ctx.get(dut.debug_refused) == 1
        ctx.set(dut.advance, 1)
        ctx.set(dut.advance_to, TEST)
        await ctx.tick()
        assert ctx.get(dut.state) == PRODUCTION and ctx.get(dut.advance_refused) == 1

    run(dut, tb)


def test_cap_table_lookup_rules_and_no_underflow():
    dut = CapTable(entries=4)

    async def tb(ctx):
        ctx.set(dut.epoch_tag, 0x11)
        ctx.set(dut.now, 100)
        # insert without a MAC: refused
        ctx.set(dut.ins, 1)
        ctx.set(dut.ins_point, 1)
        ctx.set(dut.ins_peer, 7)
        ctx.set(dut.ins_dir, 2)
        ctx.set(dut.ins_budget, 1000)
        ctx.set(dut.ins_expiry, 200)
        ctx.set(dut.ins_epoch_tag, 0x11)
        ctx.set(dut.mac_ok, 0)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        ctx.set(dut.lk, 1)
        ctx.set(dut.lk_point, 1)
        ctx.set(dut.lk_peer, 7)
        ctx.set(dut.lk_dir, 0)
        ctx.set(dut.lk_bytes, 10)
        assert ctx.get(dut.allow) == 0 and ctx.get(dut.reason) == R_NO_CAP
        ctx.set(dut.lk, 0)
        # insert with a MAC
        ctx.set(dut.ins, 1)
        ctx.set(dut.mac_ok, 1)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        ctx.set(dut.lk, 1)
        ctx.set(dut.lk_bytes, 600)
        assert ctx.get(dut.allow) == 1 and ctx.get(dut.reason) == R_OK
        await ctx.tick()                             # budget now 400
        assert ctx.get(dut.allow) == 0 and ctx.get(dut.reason) == R_BUDGET   # 600 > 400: refused, no underflow
        ctx.set(dut.lk_bytes, 400)
        assert ctx.get(dut.allow) == 1
        await ctx.tick()                             # budget 0
        ctx.set(dut.lk_bytes, 1)
        assert ctx.get(dut.allow) == 0 and ctx.get(dut.reason) == R_BUDGET
        # stale epoch
        ctx.set(dut.epoch_tag, 0x22)
        ctx.set(dut.lk_bytes, 0)
        assert ctx.get(dut.reason) == R_STALE_EPOCH
        ctx.set(dut.epoch_tag, 0x11)
        # expiry
        ctx.set(dut.now, 200)
        assert ctx.get(dut.reason) == R_EXPIRED
        await ctx.tick()
        assert ctx.get(dut.reason) == R_NO_CAP       # the expired entry was dropped
        ctx.set(dut.lk, 0)
        # a stranger never matches
        ctx.set(dut.lk, 1)
        ctx.set(dut.lk_peer, 99)
        ctx.set(dut.now, 100)
        assert ctx.get(dut.allow) == 0

    run(dut, tb)


def test_cap_table_clear_all_closes_every_port():
    dut = CapTable(entries=4)

    async def tb(ctx):
        ctx.set(dut.epoch_tag, 1)
        ctx.set(dut.ins_epoch_tag, 1)
        ctx.set(dut.ins_expiry, 1000)
        ctx.set(dut.ins_budget, 100)
        ctx.set(dut.mac_ok, 1)
        for peer in (1, 2, 3):
            ctx.set(dut.ins, 1)
            ctx.set(dut.ins_peer, peer)
            await ctx.tick()
        ctx.set(dut.ins, 0)
        ctx.set(dut.lk, 1)
        ctx.set(dut.lk_peer, 2)
        ctx.set(dut.lk_bytes, 1)
        assert ctx.get(dut.allow) == 1
        ctx.set(dut.clear_all, 1)
        await ctx.tick()
        ctx.set(dut.clear_all, 0)
        for peer in (1, 2, 3):
            ctx.set(dut.lk_peer, peer)
            assert ctx.get(dut.allow) == 0

    run(dut, tb)


def test_ticket_store_never_admits_twice_and_refuses_when_full():
    dut = TicketStore(entries=2)

    async def tb(ctx):
        ctx.set(dut.id_in, 0xA1)
        ctx.set(dut.query, 1)
        assert ctx.get(dut.seen) == 0
        ctx.set(dut.burn, 1)
        await ctx.tick()
        ctx.set(dut.burn, 0)
        assert ctx.get(dut.seen) == 1
        ctx.set(dut.id_in, 0xA2)
        ctx.set(dut.burn, 1)
        await ctx.tick()
        ctx.set(dut.burn, 0)
        assert ctx.get(dut.full) == 1
        ctx.set(dut.id_in, 0xA3)
        ctx.set(dut.burn, 1)
        await ctx.tick()
        assert ctx.get(dut.burned) == 0 and ctx.get(dut.seen) == 0    # cannot burn: the endpoint must refuse
        ctx.set(dut.id_in, 0xA1)
        assert ctx.get(dut.seen) == 1

    run(dut, tb)


def test_heartbeat_expires_and_reloads_only_on_valid():
    dut = Heartbeat(width=8)

    async def tb(ctx):
        assert ctx.get(dut.expired) == 1
        ctx.set(dut.window, 3)
        ctx.set(dut.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb_valid, 0)
        assert ctx.get(dut.expired) == 0
        ctx.set(dut.tick, 1)
        for _ in range(3):
            await ctx.tick()
        assert ctx.get(dut.expired) == 1
        ctx.set(dut.tick, 0)
        ctx.set(dut.window, 5)                     # a new window alone does nothing
        await ctx.tick()
        assert ctx.get(dut.expired) == 1

    run(dut, tb)


def levers(ctx, dut):
    return (ctx.get(dut.pwrbrk), ctx.get(dut.perst), ctx.get(dut.pwr_en))


def test_halt_sequencer_rungs_and_clear():
    dut = HaltSeq(t_throttle=3, t_halt=4)

    async def tb(ctx):
        # boot: brake and reset asserted, power off, loop switch open
        assert ctx.get(dut.state) == HALTED_INITIAL and levers(ctx, dut) == (1, 1, 0) and ctx.get(dut.switch_open) == 1
        ctx.set(dut.hb_ok, 1)
        ctx.set(dut.loop_sense, 1)
        await ctx.tick()
        assert ctx.get(dut.state) == RUN and levers(ctx, dut) == (0, 0, 1) and ctx.get(dut.ports_closed) == 0
        assert ctx.get(dut.switch_open) == 0
        ctx.set(dut.hb_expired, 1)
        await ctx.tick()
        ctx.set(dut.hb_expired, 0)
        assert ctx.get(dut.state) == THROTTLE and levers(ctx, dut) == (1, 0, 1) and ctx.get(dut.switch_open) == 0
        assert ctx.get(dut.cause) == C_LOCAL
        ctx.set(dut.tick, 1)
        for _ in range(3):
            await ctx.tick()
        assert ctx.get(dut.state) == HALT and levers(ctx, dut) == (1, 1, 1) and ctx.get(dut.switch_open) == 0   # local: loop stays closed
        for _ in range(4):
            await ctx.tick()
        assert ctx.get(dut.state) == SAFE and levers(ctx, dut) == (1, 1, 0)
        ctx.set(dut.tick, 0)
        await ctx.tick()
        assert ctx.get(dut.state) == SAFE                     # no way up without clear
        ctx.set(dut.clear, 1)
        await ctx.tick()
        ctx.set(dut.clear, 0)
        assert ctx.get(dut.state) == HALTED_INITIAL and ctx.get(dut.cause) == 0 and levers(ctx, dut) == (1, 1, 0)
        await ctx.tick()
        assert ctx.get(dut.state) == RUN

    run(dut, tb)


def test_halt_loop_lost_opens_switch_and_tamper_is_safe():
    dut = HaltSeq()

    async def tb(ctx):
        ctx.set(dut.hb_ok, 1)
        ctx.set(dut.loop_sense, 1)
        await ctx.tick()
        assert ctx.get(dut.state) == RUN and ctx.get(dut.switch_open) == 0
        ctx.set(dut.loop_lost, 1)
        await ctx.tick()
        ctx.set(dut.loop_lost, 0)
        assert ctx.get(dut.state) == HALT and ctx.get(dut.switch_open) == 1 and ctx.get(dut.cause) == C_LOOP
        ctx.set(dut.hb_ok, 1)                                  # a live heartbeat alone never closes it again
        await ctx.tick()
        assert ctx.get(dut.switch_open) == 1 and ctx.get(dut.state) == HALT
        ctx.set(dut.tamper, 1)
        await ctx.tick()
        assert ctx.get(dut.state) == SAFE and ctx.get(dut.pwr_en) == 0 and ctx.get(dut.cause) == C_TAMPER

    run(dut, tb)


def test_halt_commanded_opens_the_switch_and_local_causes_write_local():
    dut = HaltSeq()

    async def tb(ctx):
        ctx.set(dut.hb_ok, 1)
        ctx.set(dut.loop_sense, 1)
        await ctx.tick()
        ctx.set(dut.local_trip, 1)
        await ctx.tick()
        ctx.set(dut.local_trip, 0)
        assert ctx.get(dut.state) == THROTTLE and ctx.get(dut.cause) == C_LOCAL and ctx.get(dut.switch_open) == 0
        ctx.set(dut.cmd_halt, 1)
        await ctx.tick()
        ctx.set(dut.cmd_halt, 0)
        assert ctx.get(dut.state) == HALT and ctx.get(dut.cause) == C_COMMAND and ctx.get(dut.switch_open) == 1

    run(dut, tb)


def test_halt_loop_loss_while_throttled_halts():
    dut = HaltSeq()

    async def tb(ctx):
        ctx.set(dut.hb_ok, 1)
        ctx.set(dut.loop_sense, 1)
        await ctx.tick()
        ctx.set(dut.cmd_throttle, 1)
        await ctx.tick()
        ctx.set(dut.cmd_throttle, 0)
        assert ctx.get(dut.state) == THROTTLE and ctx.get(dut.cause) == C_LOCAL
        ctx.set(dut.loop_lost, 1)
        await ctx.tick()
        ctx.set(dut.loop_lost, 0)
        assert ctx.get(dut.state) == HALT and ctx.get(dut.switch_open) == 1 and ctx.get(dut.cause) == C_LOOP

    run(dut, tb)


def test_loop_io_debounce():
    dut = LoopIO(debounce=2)

    async def tb(ctx):
        ctx.set(dut.loop_sense, 1)
        ctx.set(dut.sample, 1)
        await ctx.tick()
        assert ctx.get(dut.loop_lost) == 0
        ctx.set(dut.loop_sense, 0)
        await ctx.tick()
        assert ctx.get(dut.loop_lost) == 0            # one noisy sample is not a loss
        await ctx.tick()
        assert ctx.get(dut.loop_lost) == 1            # two is
        ctx.set(dut.switch_open, 1)
        assert ctx.get(dut.loop_out_open) == 1

    run(dut, tb)


def test_meter_only_increments_and_host_cannot_write():
    dut = Meter(slots=2, width=16)

    async def tb(ctx):
        ctx.set(dut.slot, 1)
        ctx.set(dut.add_tokens, 10)
        ctx.set(dut.strobe, 1)
        await ctx.tick()
        await ctx.tick()
        ctx.set(dut.strobe, 0)
        ctx.set(dut.rd_slot, 1)
        assert ctx.get(dut.rd_tokens) == 20
        ctx.set(dut.host_wr, 1)
        await ctx.tick()
        assert ctx.get(dut.rd_tokens) == 20 and ctx.get(dut.host_wr_refused) == 1

    run(dut, tb)


def test_mailbox_sequence_epoch_signature():
    dut = Mailbox()

    async def deliver(ctx, seq, epoch_match=1, exempt=0, needs_run=0, running=1, sig_ok=1):
        ctx.set(dut.frame_seq, seq)
        ctx.set(dut.epoch_match, epoch_match)
        ctx.set(dut.epoch_exempt, exempt)
        ctx.set(dut.needs_run, needs_run)
        ctx.set(dut.running, running)
        ctx.set(dut.doorbell, 1)
        await ctx.tick()
        ctx.set(dut.doorbell, 0)
        if ctx.get(dut.verify_req):
            ctx.set(dut.sig_done, 1)
            ctx.set(dut.sig_ok, sig_ok)
            dispatched = ctx.get(dut.dispatch)
            await ctx.tick()
            ctx.set(dut.sig_done, 0)
            return dispatched, ctx.get(dut.status)
        return 0, ctx.get(dut.status)

    async def tb(ctx):
        ctx.set(dut.key_slot, 2)
        d, s = await deliver(ctx, seq=1)
        assert d == 1 and s == S_OK
        d, s = await deliver(ctx, seq=1)                     # replay
        assert d == 0 and s == S_BAD_SEQ
        d, s = await deliver(ctx, seq=2, sig_ok=0)           # forged
        assert d == 0 and s == S_BAD_SIG
        d, s = await deliver(ctx, seq=3, epoch_match=0)      # stale epoch
        assert d == 0 and s == S_BAD_EPOCH
        d, s = await deliver(ctx, seq=3, epoch_match=0, exempt=1)
        assert d == 1 and s == S_OK
        d, s = await deliver(ctx, seq=4, needs_run=1, running=0)
        assert d == 0 and s == S_REFUSED
        ctx.set(dut.key_slot, 5)                              # another key has its own sequence
        d, s = await deliver(ctx, seq=1)
        assert d == 1 and s == S_OK

    run(dut, tb)


def test_mailbox_refuses_a_good_signature_over_another_command():
    """A frame signed for one command (the crypto core reads the command byte out of the verified
    payload) is not dispatched as another, and its sequence number is not consumed."""
    dut = Mailbox()
    HEARTBEAT, CLEAR = 0x0E, 0x10                                    # the opcodes in docs/04 §3

    async def deliver(ctx, seq, cmd, signed_cmd):
        ctx.set(dut.frame_seq, seq)
        ctx.set(dut.cmd, cmd)
        ctx.set(dut.signed_cmd, signed_cmd)
        ctx.set(dut.epoch_match, 1)
        ctx.set(dut.running, 1)
        ctx.set(dut.doorbell, 1)
        await ctx.tick()
        ctx.set(dut.doorbell, 0)
        ctx.set(dut.sig_done, 1)
        ctx.set(dut.sig_ok, 1)                                        # the signature itself is good
        dispatched = ctx.get(dut.dispatch)
        await ctx.tick()
        ctx.set(dut.sig_done, 0)
        return dispatched, ctx.get(dut.status)

    async def tb(ctx):
        d, s = await deliver(ctx, seq=1, cmd=CLEAR, signed_cmd=HEARTBEAT)     # a heartbeat presented as CLEAR
        assert d == 0 and s == S_WRONG_CMD
        assert ctx.get(dut.last_seq[0]) == 0                                 # nothing consumed
        d, s = await deliver(ctx, seq=1, cmd=CLEAR, signed_cmd=CLEAR)         # the real CLEAR still goes through
        assert d == 1 and s == S_OK

    run(dut, tb)


def test_mailbox_reports_the_first_failing_check():
    """A frame with two defects reports the first check in the order sequence, epoch, signature."""
    dut = Mailbox()

    async def deliver(ctx, seq, epoch_match=1, sig_ok=1):
        ctx.set(dut.frame_seq, seq)
        ctx.set(dut.epoch_match, epoch_match)
        ctx.set(dut.running, 1)
        ctx.set(dut.doorbell, 1)
        await ctx.tick()
        ctx.set(dut.doorbell, 0)
        verifying = ctx.get(dut.verify_req)
        if verifying:
            ctx.set(dut.sig_done, 1)
            ctx.set(dut.sig_ok, sig_ok)
            dispatched = ctx.get(dut.dispatch)
            await ctx.tick()
            ctx.set(dut.sig_done, 0)
            return dispatched, ctx.get(dut.status), verifying
        return 0, ctx.get(dut.status), verifying

    async def tb(ctx):
        d, s, v = await deliver(ctx, seq=1)
        assert d == 1 and s == S_OK
        d, s, v = await deliver(ctx, seq=1, sig_ok=0)                    # replayed and forged: sequence first
        assert d == 0 and s == S_BAD_SEQ and v == 0                      # the crypto core was never asked
        d, s, v = await deliver(ctx, seq=2, epoch_match=0, sig_ok=0)     # stale and forged: epoch before signature
        assert d == 0 and s == S_BAD_EPOCH and v == 0
        d, s, v = await deliver(ctx, seq=2, sig_ok=0)                    # only the signature is bad
        assert d == 0 and s == S_BAD_SIG and v == 1

    run(dut, tb)


def test_alarms_sticky_and_clear_gated():
    dut = Alarms(width=8)

    async def tb(ctx):
        ctx.set(dut.set_mask, 0b0101)
        await ctx.tick()
        ctx.set(dut.set_mask, 0)
        assert ctx.get(dut.alarms) == 0b0101 and ctx.get(dut.any) == 1
        ctx.set(dut.clear_mask, 0b0001)
        ctx.set(dut.clear_authorized, 0)
        await ctx.tick()
        assert ctx.get(dut.alarms) == 0b0101 and ctx.get(dut.clear_refused) == 1
        ctx.set(dut.clear_authorized, 1)
        await ctx.tick()
        assert ctx.get(dut.alarms) == 0b0100

    run(dut, tb)


def test_governor_core_boots_halted_and_runs_on_heartbeat_with_loop_current():
    dut = GovernorCore(cap_entries=2, ticket_entries=2)

    async def tb(ctx):
        ctx.set(dut.csr_addr, 0x008)
        assert ctx.get(dut.csr_rdata) == HALTED_INITIAL
        # boot: brake and reset asserted (active low pads), slot power off, loop switch open
        assert (ctx.get(dut.pwrbrk_n), ctx.get(dut.perst_n), ctx.get(dut.pwr_en), ctx.get(dut.loop_out_open)) == (0, 0, 0, 1)
        ctx.set(dut.csr_addr, 0x080)
        assert ctx.get(dut.csr_rdata) == 0b111                   # LEVERS: brake, PERST#, PWR_EN low
        ctx.set(dut.csr_addr, 0x008)
        ctx.set(dut.loop_sense, 1)
        ctx.set(dut.hb.window, 10)
        ctx.set(dut.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb.hb_valid, 0)
        await ctx.tick()
        assert ctx.get(dut.csr_rdata) == RUN
        assert (ctx.get(dut.pwrbrk_n), ctx.get(dut.perst_n), ctx.get(dut.pwr_en), ctx.get(dut.loop_out_open)) == (1, 1, 1, 0)
        # the loop drops: two samples later the core halts and opens its switch
        ctx.set(dut.loop_sense, 0)
        ctx.set(dut.sample, 1)
        for _ in range(4):
            await ctx.tick()
        assert ctx.get(dut.csr_rdata) == HALT and ctx.get(dut.loop_out_open) == 1 and ctx.get(dut.perst_n) == 0
        ctx.set(dut.csr_addr, 0x00C)                              # CAUSE: [2:0] from the sequencer, [15:8] from firmware
        ctx.set(dut.cause_fw, 0x2A)
        assert ctx.get(dut.csr_rdata) == (0x2A << 8) | C_LOOP
        # the CSR window has no write port at all
        assert not hasattr(dut, "csr_wdata")

    run(dut, tb)


def test_governor_core_timers_run_on_the_millisecond_tick():
    """Heartbeat and sequencer timers count ms strobes derived from the 1 us monotonic tick."""
    dut = GovernorCore(cap_entries=2, ticket_entries=2, t_throttle_ms=2, t_halt_ms=3)

    async def tb(ctx):
        ctx.set(dut.loop_sense, 1)
        ctx.set(dut.hb.window, 2)                                 # two milliseconds of validity
        ctx.set(dut.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb.hb_valid, 0)
        await ctx.tick()
        assert ctx.get(dut.halt.state) == RUN
        ctx.set(dut.tick, 1)
        for _ in range(1024):                                     # one millisecond of microsecond ticks
            await ctx.tick()
        assert ctx.get(dut.hb.remaining) == 1 and ctx.get(dut.halt.state) == RUN
        for _ in range(1024):
            await ctx.tick()
        await ctx.tick()
        assert ctx.get(dut.hb.expired) == 1 and ctx.get(dut.halt.state) == THROTTLE
        for _ in range(2 * 1024):                                 # T_throttle = 2 ms
            await ctx.tick()
        await ctx.tick()
        assert ctx.get(dut.halt.state) == HALT
        for _ in range(3 * 1024):                                 # T_halt = 3 ms
            await ctx.tick()
        await ctx.tick()
        assert ctx.get(dut.halt.state) == SAFE
        ctx.set(dut.tick, 0)
        ctx.set(dut.csr_addr, 0x070)
        assert ctx.get(dut.csr_rdata) == 7 * 1024 + 3             # MONO_LO counts every microsecond tick

    run(dut, tb)


def test_governor_core_csr_decodes_mbox_seq_and_meter():
    dut = GovernorCore(cap_entries=2, ticket_entries=2)

    async def tb(ctx):
        ctx.set(dut.mbox.key_slot, 0)
        ctx.set(dut.mbox.frame_seq, 7)
        ctx.set(dut.mbox.epoch_match, 1)
        ctx.set(dut.doorbell, 1)
        await ctx.tick()
        ctx.set(dut.doorbell, 0)
        ctx.set(dut.mbox.sig_done, 1)
        ctx.set(dut.mbox.sig_ok, 1)
        await ctx.tick()
        ctx.set(dut.mbox.sig_done, 0)
        ctx.set(dut.csr_addr, 0x108)
        assert ctx.get(dut.csr_rdata) == 7                        # MBOX_SEQ
        ctx.set(dut.meter.slot, 1)
        ctx.set(dut.meter.add_tokens, 5)
        ctx.set(dut.meter.add_out, 0x1_0000_0003)
        ctx.set(dut.meter.strobe, 1)
        await ctx.tick()
        ctx.set(dut.meter.strobe, 0)
        ctx.set(dut.csr_addr, 0x200 + 32 * 1)                     # slot 1, tokens, low word
        assert ctx.get(dut.csr_rdata) == 5
        ctx.set(dut.csr_addr, 0x200 + 32 * 1 + 24)                # slot 1, bytes out, low word
        assert ctx.get(dut.csr_rdata) == 3
        ctx.set(dut.csr_addr, 0x200 + 32 * 1 + 28)                # slot 1, bytes out, high word
        assert ctx.get(dut.csr_rdata) == 1
        ctx.set(dut.csr_addr, 0x200)                              # slot 0 untouched
        assert ctx.get(dut.csr_rdata) == 0

    run(dut, tb)
