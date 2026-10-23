"""Conformance tests, block by block: each one checks a sentence of the spec against the Amaranth RTL.

These are the inspector's checks with the code book open: one rule, one room, one observation. Every test
names the requirement ids it covers (rtl/conformance/requirements.py). None of them is an attack: each drives
the block's ports the way its own interface describes and compares what comes out with what the spec says.
"""
from __future__ import annotations

import random

from amaranth import Signal
from amaranth.hdl import ResetInserter

from rtl.governor_rtl.cap_table import R_BUDGET, R_EXPIRED, R_NO_CAP, R_OK, R_STALE_EPOCH
from rtl.governor_rtl.halt import (C_COMMAND, C_LOCAL, C_LOOP, C_NONE, C_TAMPER, HALT, HALTED_INITIAL, RUN, SAFE,
                                   THROTTLE)
from rtl.governor_rtl.lifecycle import DECOMMISSIONED, PRODUCTION, PROVISIONED, TEST
from rtl.governor_rtl.mailbox import S_BAD_EPOCH, S_BAD_SEQ, S_BAD_SIG, S_BUSY, S_IDLE, S_OK, S_REFUSED, S_WRONG_CMD

from .framework import B, conformance, levers, sim

RUNG = {RUN: 0, THROTTLE: 1, HALT: 2, SAFE: 3}       # severity order; HALTED_INITIAL is the boot rung


# ================================================================ monotonic counter
@conformance("R-001")
def test_mono_counter_is_64_bits():
    """The counter is 64 bits wide."""
    assert len(B.MonotonicCounter().value) == 64


@conformance("R-001")
def test_mono_advances_once_per_tick():
    """Each inc strobe advances the counter by exactly one; no strobe, no change."""
    dut = B.MonotonicCounter(width=16)

    async def tb(ctx):
        for i in range(1, 11):
            ctx.set(dut.inc, 1)
            await ctx.tick()
            assert ctx.get(dut.value) == i
        ctx.set(dut.inc, 0)
        for _ in range(5):
            await ctx.tick()
        assert ctx.get(dut.value) == 10
    sim(dut, tb)


@conformance("R-002")
def test_mono_decrement_request_refused_and_value_kept():
    """A decrement request is flagged as refused and the value does not move."""
    dut = B.MonotonicCounter(width=16)

    async def tb(ctx):
        ctx.set(dut.inc, 1)
        for _ in range(7):
            await ctx.tick()
        ctx.set(dut.inc, 0)
        ctx.set(dut.dec_req, 1)
        assert ctx.get(dut.refused) == 1
        await ctx.tick()
        assert ctx.get(dut.value) == 7
        ctx.set(dut.dec_req, 0)
        assert ctx.get(dut.refused) == 0
    sim(dut, tb)


@conformance("R-002")
def test_mono_never_decreases_under_random_inputs():
    """2,000 cycles of random inc, dec_req, load_hwm and hwm: the value never goes down."""
    dut = B.MonotonicCounter(width=16)
    rng = random.Random(1)

    async def tb(ctx):
        last = 0
        for _ in range(2000):
            ctx.set(dut.inc, rng.random() < 0.5)
            ctx.set(dut.dec_req, rng.random() < 0.3)
            ctx.set(dut.load_hwm, rng.random() < 0.1)
            ctx.set(dut.hwm, rng.randrange(0, 3000))
            await ctx.tick()
            v = ctx.get(dut.value)
            assert v >= last, f"counter went from {last} to {v}"
            last = v
    sim(dut, tb)


@conformance("R-003")
def test_mono_high_water_mark_raises_the_counter():
    """At boot the fuse-backed high-water mark is loaded: the counter starts no lower than it."""
    dut = B.MonotonicCounter(width=16)

    async def tb(ctx):
        ctx.set(dut.hwm, 1234)
        ctx.set(dut.load_hwm, 1)
        await ctx.tick()
        assert ctx.get(dut.value) == 1234
    sim(dut, tb)


@conformance("R-003")
def test_mono_lower_high_water_mark_cannot_pull_back():
    """A stale (lower) high-water mark never moves the counter backwards."""
    dut = B.MonotonicCounter(width=16)

    async def tb(ctx):
        ctx.set(dut.hwm, 500)
        ctx.set(dut.load_hwm, 1)
        await ctx.tick()
        ctx.set(dut.hwm, 10)
        await ctx.tick()
        assert ctx.get(dut.value) == 500
    sim(dut, tb)


# ================================================================ measurement registers
@conformance("R-004")
def test_meas_engine_output_without_request_ignored():
    """A hash result that this block did not ask for never lands in the register."""
    dut = B.MeasureReg(width=32)

    async def tb(ctx):
        ctx.set(dut.hash_done, 1)
        ctx.set(dut.hash_out, 0xDEADBEEF)
        for _ in range(3):
            await ctx.tick()
        assert ctx.get(dut.value) == 0
    sim(dut, tb)


@conformance("R-004")
def test_meas_extend_latches_engine_result():
    """extend asks the engine for H(value || data) and latches exactly what the engine returns."""
    dut = B.MeasureReg(width=32)

    async def tb(ctx):
        ctx.set(dut.data, 0x1234)
        ctx.set(dut.extend, 1)
        assert ctx.get(dut.hash_req) == 1
        assert ctx.get(dut.hash_in) == 0x1234             # data in the low half, the old value (0) above it
        await ctx.tick()
        ctx.set(dut.extend, 0)
        ctx.set(dut.hash_done, 1)
        ctx.set(dut.hash_out, 0xCAFEF00D)
        await ctx.tick()
        assert ctx.get(dut.value) == 0xCAFEF00D
    sim(dut, tb)


@conformance("R-004")
def test_meas_has_no_write_port():
    """The block exposes no write-data or write-enable port: only extend, data and the engine interface."""
    dut = B.MeasureReg(width=32)
    ports = {k for k, v in vars(dut).items() if isinstance(v, Signal)}
    assert ports == {"extend", "data", "hash_req", "hash_in", "hash_done", "hash_out", "value", "busy"}, ports


@conformance("R-005", "R-006")
def test_core_meas_csr_windows_read_both_registers():
    """MEAS0 at 0x030.. and MEAS1 at 0x050.. read the two measurement registers, eight words each."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        for blk, val in ((dut.meas0, 0x0102030405060708_1112131415161718_2122232425262728_3132333435363738),
                         (dut.meas1, 0x4142434445464748_5152535455565758_6162636465666768_7172737475767778)):
            ctx.set(blk.extend, 1)
            await ctx.tick()
            ctx.set(blk.extend, 0)
            ctx.set(blk.hash_done, 1)
            ctx.set(blk.hash_out, val)
            await ctx.tick()
            ctx.set(blk.hash_done, 0)
        for base, val in ((0x030, ctx.get(dut.meas0.value)), (0x050, ctx.get(dut.meas1.value))):
            assert val != 0
            for i in range(8):
                ctx.set(dut.csr_addr, base + 4 * i)
                assert ctx.get(dut.csr_rdata) == (val >> (32 * i)) & 0xFFFF_FFFF
    sim(dut, tb)


# ================================================================ epoch register
@conformance("R-007")
def test_epoch_commit_without_quorum_ignored():
    """A commit strobe without quorum_ok leaves the epoch unchanged."""
    dut = B.EpochReg(width=32)

    async def tb(ctx):
        ctx.set(dut.new_epoch, 0xAAAA5555)
        ctx.set(dut.commit, 1)
        await ctx.tick()
        assert ctx.get(dut.epoch) == 0
    sim(dut, tb)


@conformance("R-007")
def test_epoch_quorum_without_commit_ignored():
    """quorum_ok alone, without the policy FSM's commit, changes nothing."""
    dut = B.EpochReg(width=32)

    async def tb(ctx):
        ctx.set(dut.new_epoch, 0xAAAA5555)
        ctx.set(dut.quorum_ok, 1)
        await ctx.tick()
        assert ctx.get(dut.epoch) == 0
    sim(dut, tb)


@conformance("R-007")
def test_epoch_host_write_has_no_effect():
    """The host write port is refused and flagged, and the value never moves."""
    dut = B.EpochReg(width=32)

    async def tb(ctx):
        ctx.set(dut.host_wr, 1)
        ctx.set(dut.host_data, 0xBAD)
        await ctx.tick()
        assert ctx.get(dut.host_refused) == 1 and ctx.get(dut.epoch) == 0
    sim(dut, tb)


@conformance("R-007")
def test_epoch_commit_with_quorum_switches():
    """commit with quorum_ok switches the epoch to the new value."""
    dut = B.EpochReg(width=32)

    async def tb(ctx):
        ctx.set(dut.new_epoch, 0x12345678)
        ctx.set(dut.commit, 1)
        ctx.set(dut.quorum_ok, 1)
        await ctx.tick()
        assert ctx.get(dut.epoch) == 0x12345678
    sim(dut, tb)


@conformance("R-009")
def test_epoch_tag_is_low_16_bits():
    """The capability epoch tag is the low 16 bits of the epoch."""
    dut = B.EpochReg(width=64)

    async def tb(ctx):
        ctx.set(dut.new_epoch, 0x1111_2222_3333_ABCD)
        ctx.set(dut.commit, 1)
        ctx.set(dut.quorum_ok, 1)
        await ctx.tick()
        assert ctx.get(dut.epoch_tag) == 0xABCD
    sim(dut, tb)


@conformance("R-008")
def test_core_epoch_csr_reads_256_bits():
    """EPOCH[0..7] at 0x010.. reads the 256-bit epoch, low word first."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)
    val = int.from_bytes(bytes(range(32)), "little")

    async def tb(ctx):
        ctx.set(dut.epoch.new_epoch, val)
        ctx.set(dut.epoch.commit, 1)
        ctx.set(dut.epoch.quorum_ok, 1)
        await ctx.tick()
        ctx.set(dut.epoch.commit, 0)
        for i in range(8):
            ctx.set(dut.csr_addr, 0x010 + 4 * i)
            assert ctx.get(dut.csr_rdata) == (val >> (32 * i)) & 0xFFFF_FFFF
    sim(dut, tb)


# ================================================================ lifecycle
@conformance("R-010")
def test_lifecycle_never_moves_down_by_advance():
    """advance to a lower or equal state is refused and flagged."""
    dut = B.Lifecycle()

    async def tb(ctx):
        ctx.set(dut.advance, 1)
        ctx.set(dut.advance_to, PRODUCTION)
        await ctx.tick()
        for to in (TEST, PROVISIONED, PRODUCTION):
            ctx.set(dut.advance_to, to)
            assert ctx.get(dut.advance_refused) == 1
            await ctx.tick()
            assert ctx.get(dut.state) == PRODUCTION
    sim(dut, tb)


@conformance("R-010")
def test_lifecycle_lower_fuse_load_cannot_move_down():
    """A fuse load that reads a lower state does not move the register down."""
    dut = B.Lifecycle()

    async def tb(ctx):
        ctx.set(dut.fuse_state, DECOMMISSIONED)
        ctx.set(dut.load, 1)
        await ctx.tick()
        ctx.set(dut.fuse_state, TEST)
        await ctx.tick()
        assert ctx.get(dut.state) == DECOMMISSIONED
    sim(dut, tb)


@conformance("R-010")
def test_lifecycle_monotone_under_random_inputs():
    """2,000 random cycles of load, advance and their values: the state never decreases."""
    dut = B.Lifecycle()
    rng = random.Random(2)

    async def tb(ctx):
        last = 0
        for _ in range(2000):
            ctx.set(dut.load, rng.random() < 0.2)
            ctx.set(dut.fuse_state, rng.randrange(4))
            ctx.set(dut.advance, rng.random() < 0.2)
            ctx.set(dut.advance_to, rng.randrange(4))
            await ctx.tick()
            s = ctx.get(dut.state)
            assert s >= last
            last = s
    sim(dut, tb)


@conformance("R-011", "R-013")
def test_lifecycle_debug_refused_in_production_and_later():
    """Once the register holds PRODUCTION or DECOMMISSIONED, debug_grant is 0 and debug_refused is 1."""
    for target in (PRODUCTION, DECOMMISSIONED):
        dut = B.Lifecycle()

        async def tb(ctx, dut=dut, target=target):
            ctx.set(dut.fuse_state, target)
            ctx.set(dut.load, 1)
            await ctx.tick()
            ctx.set(dut.load, 0)
            ctx.set(dut.debug_req, 1)
            assert ctx.get(dut.debug_grant) == 0 and ctx.get(dut.debug_refused) == 1
        sim(dut, tb)


@conformance("R-011")
def test_lifecycle_debug_granted_before_production():
    """In TEST and PROVISIONED a debug request is granted (the bring-up plan needs JTAG in TEST)."""
    for target in (TEST, PROVISIONED):
        dut = B.Lifecycle()

        async def tb(ctx, dut=dut, target=target):
            ctx.set(dut.fuse_state, target)
            ctx.set(dut.load, 1)
            await ctx.tick()
            ctx.set(dut.debug_req, 1)
            assert ctx.get(dut.debug_grant) == 1 and ctx.get(dut.debug_refused) == 0
        sim(dut, tb)


@conformance("R-012")
def test_core_lifecycle_csr_encoding():
    """LIFECYCLE at 0x004 reads 0 test, 1 provisioned, 2 production, 3 decommissioned after the fuse load."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.csr_addr, 0x004)
        for s in (PROVISIONED, PRODUCTION, DECOMMISSIONED):
            ctx.set(dut.life.fuse_state, s)
            ctx.set(dut.life.load, 1)
            await ctx.tick()
            assert ctx.get(dut.csr_rdata) == s
    sim(dut, tb)


# ================================================================ capability table
def _cap_insert(ctx, dut, point=1, peer=7, d=2, budget=1000, expiry=200, etag=0x11, mac=1):
    ctx.set(dut.ins, 1)
    ctx.set(dut.ins_point, point)
    ctx.set(dut.ins_peer, peer)
    ctx.set(dut.ins_dir, d)
    ctx.set(dut.ins_budget, budget)
    ctx.set(dut.ins_expiry, expiry)
    ctx.set(dut.ins_epoch_tag, etag)
    ctx.set(dut.mac_ok, mac)


def _cap_lookup(ctx, dut, point=1, peer=7, d=0, nbytes=10):
    ctx.set(dut.lk, 1)
    ctx.set(dut.lk_point, point)
    ctx.set(dut.lk_peer, peer)
    ctx.set(dut.lk_dir, d)
    ctx.set(dut.lk_bytes, nbytes)
    return ctx.get(dut.allow), ctx.get(dut.reason)


def _cap_tb(body):
    dut = B.CapTable(entries=4)

    async def tb(ctx):
        ctx.set(dut.epoch_tag, 0x11)
        ctx.set(dut.now, 100)
        await body(ctx, dut)
    sim(dut, tb)


@conformance("R-014")
def test_cap_match_requires_point():
    """An entry for one enforcement point never matches a lookup at another."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut, point=1)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        assert _cap_lookup(ctx, dut, point=0) == (0, R_NO_CAP)
        assert _cap_lookup(ctx, dut, point=1)[0] == 1
    _cap_tb(body)


@conformance("R-014")
def test_cap_match_requires_peer():
    """An entry for one peer never matches a lookup for another."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut, peer=7)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        assert _cap_lookup(ctx, dut, peer=8) == (0, R_NO_CAP)
    _cap_tb(body)


@conformance("R-014", "R-021")
def test_cap_match_requires_direction():
    """An 'out' entry does not admit 'in' traffic; an 'in' entry does not admit 'out'."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut, peer=7, d=1)          # out
        await ctx.tick()
        _cap_insert(ctx, dut, peer=9, d=0)          # in
        await ctx.tick()
        ctx.set(dut.ins, 0)
        assert _cap_lookup(ctx, dut, peer=7, d=0) == (0, R_NO_CAP)
        assert _cap_lookup(ctx, dut, peer=7, d=1)[0] == 1
        assert _cap_lookup(ctx, dut, peer=9, d=1) == (0, R_NO_CAP)
        assert _cap_lookup(ctx, dut, peer=9, d=0)[0] == 1
    _cap_tb(body)


@conformance("R-021")
def test_cap_both_admits_in_and_out():
    """A 'both' entry admits traffic in either direction."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut, d=2)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        assert _cap_lookup(ctx, dut, d=0)[0] == 1
        assert _cap_lookup(ctx, dut, d=1)[0] == 1
    _cap_tb(body)


@conformance("R-015")
def test_cap_lookup_decrements_by_bytes():
    """An allowed lookup takes exactly lk_bytes off the entry's budget."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut, budget=100)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        assert _cap_lookup(ctx, dut, nbytes=30)[0] == 1
        await ctx.tick()
        assert ctx.get(dut.budget[0]) == 70
        ctx.set(dut.lk, 0)
        await ctx.tick()
        assert ctx.get(dut.budget[0]) == 70          # no lookup, no decrement
    _cap_tb(body)


@conformance("R-016", "R-020")
def test_cap_refuses_more_than_remaining_budget():
    """A lookup larger than what is left is refused with R_BUDGET and takes nothing."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut, budget=50)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        assert _cap_lookup(ctx, dut, nbytes=51) == (0, R_BUDGET)
        await ctx.tick()
        assert ctx.get(dut.budget[0]) == 50
    _cap_tb(body)


@conformance("R-020")
def test_cap_budget_never_underflows_random():
    """1,000 random lookups against one entry: the budget only falls, never wraps, and allows sum to the start."""
    rng = random.Random(3)

    async def body(ctx, dut):
        _cap_insert(ctx, dut, budget=5000, expiry=1 << 30)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        spent, last = 0, 5000
        for _ in range(1000):
            n = rng.randrange(0, 200)
            allow, _ = _cap_lookup(ctx, dut, nbytes=n)
            await ctx.tick()
            b = ctx.get(dut.budget[0])
            assert b <= last and b == 5000 - spent - (n if allow else 0)
            spent += n if allow else 0
            last = b
        assert spent <= 5000
    _cap_tb(body)


@conformance("R-017")
def test_cap_refuses_at_expiry_and_drops_entry():
    """At now == expiry the lookup is refused R_EXPIRED and the entry is dropped."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut, expiry=150)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        ctx.set(dut.now, 149)
        assert _cap_lookup(ctx, dut)[0] == 1
        ctx.set(dut.now, 150)
        assert _cap_lookup(ctx, dut, nbytes=0) == (0, R_EXPIRED)
        await ctx.tick()
        ctx.set(dut.now, 100)
        assert _cap_lookup(ctx, dut) == (0, R_NO_CAP)
    _cap_tb(body)


@conformance("R-018", "R-093")
def test_cap_refuses_on_epoch_tag_mismatch():
    """An entry minted under another epoch tag is refused R_STALE_EPOCH."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut, etag=0x11)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        ctx.set(dut.epoch_tag, 0x12)
        assert _cap_lookup(ctx, dut) == (0, R_STALE_EPOCH)
    _cap_tb(body)


@conformance("R-019")
def test_cap_insert_needs_mac():
    """An insert without mac_ok is not stored."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut, mac=0)
        assert ctx.get(dut.ins_ok) == 0
        await ctx.tick()
        ctx.set(dut.ins, 0)
        assert _cap_lookup(ctx, dut) == (0, R_NO_CAP)
    _cap_tb(body)


@conformance("R-019")
def test_cap_lookup_does_not_consult_mac():
    """Once stored, lookups succeed whatever mac_ok says: the MAC is checked at insertion only."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut, mac=1)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        ctx.set(dut.mac_ok, 0)
        assert _cap_lookup(ctx, dut)[0] == 1
    _cap_tb(body)


@conformance("R-014")
def test_cap_full_table_refuses_insert():
    """With every slot valid, a further insert is flagged ins_full and not stored."""
    async def body(ctx, dut):
        for peer in range(4):
            _cap_insert(ctx, dut, peer=peer)
            await ctx.tick()
        _cap_insert(ctx, dut, peer=99)
        assert ctx.get(dut.ins_full) == 1 and ctx.get(dut.ins_ok) == 0
        await ctx.tick()
        ctx.set(dut.ins, 0)
        assert _cap_lookup(ctx, dut, peer=99) == (0, R_NO_CAP)
    _cap_tb(body)


@conformance("R-025")
def test_cap_lookup_answers_in_the_same_cycle():
    """allow and reason are combinational: the answer is there in the cycle the lookup is presented."""
    async def body(ctx, dut):
        _cap_insert(ctx, dut)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        allow, reason = _cap_lookup(ctx, dut)           # no tick between presenting and reading
        assert (allow, reason) == (1, R_OK)
    _cap_tb(body)


@conformance("R-022", "R-026")
def test_core_has_one_table_per_point_sized_by_parameter():
    """GovernorCore has four capability tables (NVSwitch, PCIe, DPU, storage), each of cap_entries entries."""
    for n in (1, 3):
        dut = B.GovernorCore(cap_entries=n, ticket_entries=2)
        assert list(dut.caps) == ["nvswitch", "pcie", "dpu", "storage"]
        assert all(c.n == n for c in dut.caps.values())
        assert dut.tickets.n == 2


@conformance("R-023")
def test_core_default_sizes_are_the_spec_prototype():
    """Defaults: 8 entries per point, 16-bit peer, 24-bit budget, 32-bit ticket id, 8-bit command, 4 meter slots of 48 bits."""
    dut = B.GovernorCore()
    c = dut.caps["nvswitch"]
    assert c.n == 8 and len(c.ins_peer) == 16 and len(c.ins_budget) == 24
    assert len(dut.tickets.id_in) == 32 and dut.tickets.n == 8
    assert len(dut.mbox.cmd) == 8
    assert dut.meter.slots == 4 and len(dut.meter.add_tokens) == 48


@conformance("R-024")
def test_core_tables_empty_whenever_not_running():
    """Out of RUN every table is cleared and an insert does not stick: no port can be open."""
    dut = B.GovernorCore(cap_entries=2, ticket_entries=1)

    async def tb(ctx):
        c = dut.caps["pcie"]
        _cap_insert(ctx, c, budget=100, expiry=1 << 30, etag=0)
        await ctx.tick()
        ctx.set(c.ins, 0)
        assert _cap_lookup(ctx, c, nbytes=1)[0] == 0           # HALTED_INITIAL: nothing open
        ctx.set(c.lk, 0)
        ctx.set(dut.loop_sense, 1)
        ctx.set(dut.hb.window, 50)
        ctx.set(dut.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb.hb_valid, 0)
        await ctx.tick()
        assert ctx.get(dut.halt.state) == RUN
        _cap_insert(ctx, c, budget=100, expiry=1 << 30, etag=0)
        await ctx.tick()
        ctx.set(c.ins, 0)
        assert _cap_lookup(ctx, c, nbytes=1)[0] == 1           # RUN: the port is open
        ctx.set(c.lk, 0)
        ctx.set(dut.halt.cmd_halt, 1)
        await ctx.tick()
        ctx.set(dut.halt.cmd_halt, 0)
        await ctx.tick()
        assert ctx.get(dut.halt.state) == HALT
        assert _cap_lookup(ctx, c, nbytes=1)[0] == 0           # halted: closed and gone
    sim(dut, tb)


# ================================================================ used-ticket store
@conformance("R-027", "R-028")
def test_ticket_seen_after_burn():
    """After a burn, a query for the same id reports seen, every time."""
    dut = B.TicketStore(entries=4)

    async def tb(ctx):
        ctx.set(dut.id_in, 0x55)
        ctx.set(dut.query, 1)
        assert ctx.get(dut.seen) == 0
        ctx.set(dut.burn, 1)
        assert ctx.get(dut.burned) == 1
        await ctx.tick()
        ctx.set(dut.burn, 0)
        for _ in range(5):
            assert ctx.get(dut.seen) == 1
            await ctx.tick()
    sim(dut, tb)


@conformance("R-027")
def test_ticket_second_burn_of_same_id_refused():
    """Burning an id that is already in the store does not succeed again."""
    dut = B.TicketStore(entries=4)

    async def tb(ctx):
        ctx.set(dut.id_in, 0x77)
        ctx.set(dut.burn, 1)
        await ctx.tick()
        assert ctx.get(dut.burned) == 0
    sim(dut, tb)


@conformance("R-027")
def test_ticket_full_store_refuses_burn_and_flags():
    """When the store is full a new id cannot be burned and full is asserted, so the endpoint must refuse."""
    dut = B.TicketStore(entries=2)

    async def tb(ctx):
        for i in (1, 2):
            ctx.set(dut.id_in, i)
            ctx.set(dut.burn, 1)
            await ctx.tick()
        ctx.set(dut.id_in, 3)
        assert ctx.get(dut.full) == 1 and ctx.get(dut.burned) == 0
        await ctx.tick()
        ctx.set(dut.burn, 0)
        for i in (1, 2):
            ctx.set(dut.id_in, i)
            assert ctx.get(dut.seen) == 1
    sim(dut, tb)


@conformance("R-027")
def test_ticket_never_admitted_twice_random():
    """500 random burns over a small id space: an id whose burn succeeded never has a second successful burn."""
    dut = B.TicketStore(entries=16)
    rng = random.Random(4)

    async def tb(ctx):
        burned = set()
        for _ in range(500):
            i = rng.randrange(24)
            ctx.set(dut.id_in, i)
            ctx.set(dut.burn, 1)
            ok = ctx.get(dut.burned)
            if ok:
                assert i not in burned, f"id {i} admitted twice"
                burned.add(i)
            await ctx.tick()
    sim(dut, tb)


# ================================================================ heartbeat
@conformance("R-029")
def test_hb_expired_at_reset():
    """Before any valid heartbeat the timer is expired (nothing to arm on)."""
    dut = B.Heartbeat(width=8)

    async def tb(ctx):
        assert ctx.get(dut.expired) == 1
    sim(dut, tb)


@conformance("R-029")
def test_hb_expires_on_the_window_th_tick():
    """With a window of N ticks, expired is 0 after N-1 ticks and 1 after the Nth."""
    dut = B.Heartbeat(width=8)

    async def tb(ctx):
        ctx.set(dut.window, 5)
        ctx.set(dut.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb_valid, 0)
        ctx.set(dut.tick, 1)
        for _ in range(4):
            await ctx.tick()
            assert ctx.get(dut.expired) == 0
        await ctx.tick()
        assert ctx.get(dut.expired) == 1
    sim(dut, tb)


@conformance("R-030")
def test_hb_reload_only_on_valid():
    """Changing the window input or ticking never reloads; only hb_valid does, and to the window given."""
    dut = B.Heartbeat(width=8)

    async def tb(ctx):
        ctx.set(dut.window, 9)
        for _ in range(3):
            await ctx.tick()
        assert ctx.get(dut.remaining) == 0
        ctx.set(dut.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb_valid, 0)
        assert ctx.get(dut.remaining) == 9
        ctx.set(dut.window, 200)
        await ctx.tick()
        assert ctx.get(dut.remaining) == 9
    sim(dut, tb)


@conformance("R-030")
def test_hb_valid_wins_over_tick():
    """A valid heartbeat in a tick cycle reloads to the full window (it is not decremented in the same cycle)."""
    dut = B.Heartbeat(width=8)

    async def tb(ctx):
        ctx.set(dut.window, 4)
        ctx.set(dut.hb_valid, 1)
        ctx.set(dut.tick, 1)
        await ctx.tick()
        assert ctx.get(dut.remaining) == 4
    sim(dut, tb)


@conformance("R-031")
def test_core_hb_remain_csr():
    """HB_REMAIN at 0x078 reads the heartbeat's remaining count."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.hb.window, 4321)
        ctx.set(dut.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.csr_addr, 0x078)
        assert ctx.get(dut.csr_rdata) == 4321
    sim(dut, tb)


@conformance("R-032")
def test_core_timers_ignore_the_raw_microsecond_tick():
    """The heartbeat counts on the derived slow strobe, not on every microsecond tick."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.hb.window, 3)
        ctx.set(dut.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb.hb_valid, 0)
        ctx.set(dut.tick, 1)
        for _ in range(500):
            await ctx.tick()
        assert ctx.get(dut.hb.remaining) == 3
    sim(dut, tb)


# ================================================================ safe-mode sequencer
async def _to_run(ctx, dut):
    ctx.set(dut.hb_ok, 1)
    ctx.set(dut.loop_sense, 1)
    await ctx.tick()
    assert ctx.get(dut.state) == RUN


def _halt(body, **kw):
    dut = B.HaltSeq(**kw)

    async def tb(ctx):
        await body(ctx, dut)
    sim(dut, tb)


def _cause_test(cause_sig, start, expect_state, expect_cause, opens):
    async def body(ctx, dut):
        await _to_run(ctx, dut)
        if start == THROTTLE:
            ctx.set(dut.cmd_throttle, 1)
            await ctx.tick()
            ctx.set(dut.cmd_throttle, 0)
            assert ctx.get(dut.state) == THROTTLE
        ctx.set(getattr(dut, cause_sig), 1)
        await ctx.tick()
        ctx.set(getattr(dut, cause_sig), 0)
        assert ctx.get(dut.state) == expect_state, (cause_sig, ctx.get(dut.state))
        assert ctx.get(dut.cause) == expect_cause
        assert ctx.get(dut.switch_open) == opens
    _halt(body)


@conformance("R-034", "R-038")
def test_halt_loop_lost_from_run():
    """loop_lost in RUN: HALT, cause loop, switch open."""
    _cause_test("loop_lost", RUN, HALT, C_LOOP, 1)


@conformance("R-034", "R-038")
def test_halt_loop_lost_from_throttle():
    """loop_lost in THROTTLE: HALT, cause loop, switch open."""
    _cause_test("loop_lost", THROTTLE, HALT, C_LOOP, 1)


@conformance("R-034")
def test_halt_hb_expired_throttles():
    """hb_expired in RUN: THROTTLE, cause local, loop stays closed."""
    _cause_test("hb_expired", RUN, THROTTLE, C_LOCAL, 0)


@conformance("R-034")
def test_halt_local_trip_throttles():
    """local_trip in RUN: THROTTLE, cause local, loop stays closed."""
    _cause_test("local_trip", RUN, THROTTLE, C_LOCAL, 0)


@conformance("R-034")
def test_halt_cmd_throttle_throttles():
    """cmd_throttle in RUN: THROTTLE, cause local, loop stays closed."""
    _cause_test("cmd_throttle", RUN, THROTTLE, C_LOCAL, 0)


@conformance("R-034", "R-038")
def test_halt_cmd_halt_from_run():
    """cmd_halt in RUN: HALT, cause command, switch open."""
    _cause_test("cmd_halt", RUN, HALT, C_COMMAND, 1)


@conformance("R-034", "R-038")
def test_halt_cmd_halt_from_throttle():
    """cmd_halt in THROTTLE: HALT, cause command, switch open."""
    _cause_test("cmd_halt", THROTTLE, HALT, C_COMMAND, 1)


@conformance("R-034", "R-038", "R-042")
def test_halt_tamper_from_run():
    """tamper in RUN: SAFE, cause tamper, switch open."""
    _cause_test("tamper", RUN, SAFE, C_TAMPER, 1)


@conformance("R-034", "R-038", "R-042")
def test_halt_tamper_from_every_rung():
    """tamper from HALTED_INITIAL, THROTTLE, HALT and SAFE all land in SAFE with cause tamper and the switch open."""
    for prep in ("boot", "throttle", "halt", "safe"):
        async def body(ctx, dut, prep=prep):
            if prep != "boot":
                await _to_run(ctx, dut)
                ctx.set(dut.cmd_throttle if prep == "throttle" else dut.cmd_halt, 1)
                await ctx.tick()
                ctx.set(dut.cmd_throttle, 0)
                ctx.set(dut.cmd_halt, 0)
                if prep == "safe":
                    ctx.set(dut.tick, 1)
                    for _ in range(5):
                        await ctx.tick()
                    ctx.set(dut.tick, 0)
                    assert ctx.get(dut.state) == SAFE
            ctx.set(dut.tamper, 1)
            await ctx.tick()
            assert (ctx.get(dut.state), ctx.get(dut.cause), ctx.get(dut.switch_open)) == (SAFE, C_TAMPER, 1), prep
        _halt(body, t_throttle=3, t_halt=4)


@conformance("R-034", "R-041")
def test_halt_throttle_escalates_after_t_throttle_ticks():
    """THROTTLE moves to HALT on exactly the t_throttle-th millisecond tick, not before."""
    async def body(ctx, dut):
        await _to_run(ctx, dut)
        ctx.set(dut.local_trip, 1)
        await ctx.tick()
        ctx.set(dut.local_trip, 0)
        ctx.set(dut.tick, 1)
        for _ in range(6):
            await ctx.tick()
            assert ctx.get(dut.state) == THROTTLE
        await ctx.tick()
        assert ctx.get(dut.state) == HALT
    _halt(body, t_throttle=7, t_halt=9)


@conformance("R-034", "R-041")
def test_halt_halt_escalates_after_t_halt_ticks():
    """HALT moves to SAFE on exactly the t_halt-th millisecond tick, not before."""
    async def body(ctx, dut):
        await _to_run(ctx, dut)
        ctx.set(dut.cmd_halt, 1)
        await ctx.tick()
        ctx.set(dut.cmd_halt, 0)
        ctx.set(dut.tick, 1)
        for _ in range(8):
            await ctx.tick()
            assert ctx.get(dut.state) == HALT
        await ctx.tick()
        assert ctx.get(dut.state) == SAFE
    _halt(body, t_throttle=7, t_halt=9)


@conformance("R-041")
def test_core_default_timers_are_30s_and_300s():
    """The core's defaults are T_throttle 30,000 ms and T_halt 300,000 ms."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)
    assert dut.halt.t_throttle == 30_000 and dut.halt.t_halt == 300_000
    assert 300_000 < (1 << len(dut.halt.timer))      # the timer can count that far


@conformance("R-035")
def test_halt_never_descends_without_clear_random():
    """5,000 random cycles of every cause, tick, hb_ok and loop_sense, clear held low: the rung only climbs.
    The one move off HALTED_INITIAL that is not a climb is arming into RUN, allowed only with no cause."""
    rng = random.Random(5)

    async def body(ctx, dut):
        prev = ctx.get(dut.state)
        for _ in range(5000):
            for s in ("loop_lost", "hb_expired", "tamper", "cmd_halt", "cmd_throttle", "local_trip"):
                ctx.set(getattr(dut, s), rng.random() < 0.02)
            ctx.set(dut.tick, rng.random() < 0.5)
            ctx.set(dut.hb_ok, rng.random() < 0.7)
            ctx.set(dut.loop_sense, rng.random() < 0.7)
            await ctx.tick()
            cur = ctx.get(dut.state)
            if prev != cur:
                assert cur != HALTED_INITIAL, f"{prev} -> HALTED_INITIAL without clear"
                if prev != HALTED_INITIAL:
                    assert RUNG[cur] > RUNG[prev], f"descended {prev} -> {cur} without clear"
            prev = cur
    _halt(body, t_throttle=4, t_halt=6)


@conformance("R-035")
def test_halt_safe_is_absorbing_without_clear():
    """In SAFE every input but clear (and tamper, which stays in SAFE) leaves the state in SAFE."""
    async def body(ctx, dut):
        ctx.set(dut.tamper, 1)
        await ctx.tick()
        ctx.set(dut.tamper, 0)
        for s in ("loop_lost", "hb_expired", "cmd_halt", "cmd_throttle", "local_trip", "hb_ok", "loop_sense", "tick"):
            ctx.set(getattr(dut, s), 1)
        for _ in range(20):
            await ctx.tick()
            assert ctx.get(dut.state) == SAFE
    _halt(body, t_throttle=2, t_halt=2)


@conformance("R-036")
def test_halt_levers_follow_every_rung():
    """Levers per rung: HALTED_INITIAL brake+reset+power off; RUN released; THROTTLE brake; HALT brake+reset; SAFE all."""
    expect = {HALTED_INITIAL: (1, 1, 0), RUN: (0, 0, 1), THROTTLE: (1, 0, 1), HALT: (1, 1, 1), SAFE: (1, 1, 0)}

    async def body(ctx, dut):
        seen = {ctx.get(dut.state): levers(ctx, dut)}
        await _to_run(ctx, dut)
        seen[RUN] = levers(ctx, dut)
        ctx.set(dut.cmd_throttle, 1)
        await ctx.tick()
        ctx.set(dut.cmd_throttle, 0)
        seen[ctx.get(dut.state)] = levers(ctx, dut)
        ctx.set(dut.tick, 1)
        for _ in range(2):
            await ctx.tick()
        seen[ctx.get(dut.state)] = levers(ctx, dut)
        for _ in range(2):
            await ctx.tick()
        seen[ctx.get(dut.state)] = levers(ctx, dut)
        assert seen == expect, seen
    _halt(body, t_throttle=2, t_halt=2)


@conformance("R-036")
def test_halt_ports_closed_outside_run():
    """ports_closed is 0 only in RUN."""
    async def body(ctx, dut):
        assert ctx.get(dut.ports_closed) == 1
        await _to_run(ctx, dut)
        assert ctx.get(dut.ports_closed) == 0
        ctx.set(dut.local_trip, 1)
        await ctx.tick()
        assert ctx.get(dut.ports_closed) == 1
    _halt(body)


@conformance("R-037")
def test_halt_switch_open_at_reset():
    """The loop switch starts open."""
    async def body(ctx, dut):
        assert ctx.get(dut.switch_open) == 1
    _halt(body)


@conformance("R-037", "R-073")
def test_halt_no_arming_without_heartbeat():
    """Without hb_ok the switch never closes and the sequencer never leaves HALTED_INITIAL, loop current or not."""
    async def body(ctx, dut):
        ctx.set(dut.loop_sense, 1)
        ctx.set(dut.tick, 1)
        for _ in range(50):
            await ctx.tick()
            assert ctx.get(dut.switch_open) == 1 and ctx.get(dut.state) == HALTED_INITIAL
    _halt(body)


@conformance("R-037")
def test_halt_arms_before_loop_current():
    """With hb_ok and no loop current the switch closes (armed) but the state waits in HALTED_INITIAL."""
    async def body(ctx, dut):
        ctx.set(dut.hb_ok, 1)
        await ctx.tick()
        assert ctx.get(dut.switch_open) == 0 and ctx.get(dut.state) == HALTED_INITIAL
        ctx.set(dut.loop_sense, 1)
        await ctx.tick()
        assert ctx.get(dut.state) == RUN
    _halt(body)


@conformance("R-037", "R-039")
def test_halt_heartbeat_alone_never_recloses_after_a_loop_cause():
    """Once a loop-opening cause opened the switch, a live heartbeat alone never closes it."""
    async def body(ctx, dut):
        await _to_run(ctx, dut)
        ctx.set(dut.cmd_halt, 1)
        await ctx.tick()
        ctx.set(dut.cmd_halt, 0)
        for _ in range(20):
            await ctx.tick()
            assert ctx.get(dut.switch_open) == 1
    _halt(body)


@conformance("R-039", "R-047")
def test_halt_clear_does_not_close_the_switch_until_armed():
    """After clear the state is HALTED_INITIAL with no cause and the switch still open; it closes only when armed."""
    async def body(ctx, dut):
        await _to_run(ctx, dut)
        ctx.set(dut.loop_lost, 1)
        await ctx.tick()
        ctx.set(dut.loop_lost, 0)
        ctx.set(dut.hb_ok, 0)
        ctx.set(dut.clear, 1)
        await ctx.tick()
        ctx.set(dut.clear, 0)
        assert (ctx.get(dut.state), ctx.get(dut.cause), ctx.get(dut.switch_open)) == (HALTED_INITIAL, C_NONE, 1)
        await ctx.tick()
        assert ctx.get(dut.switch_open) == 1
        ctx.set(dut.hb_ok, 1)
        await ctx.tick()
        assert ctx.get(dut.switch_open) == 0
    _halt(body)


@conformance("R-047")
def test_halt_clear_in_boot_rung_is_a_no_op():
    """A clear while already in HALTED_INITIAL changes nothing."""
    async def body(ctx, dut):
        ctx.set(dut.clear, 1)
        await ctx.tick()
        assert (ctx.get(dut.state), ctx.get(dut.cause), ctx.get(dut.switch_open)) == (HALTED_INITIAL, C_NONE, 1)
    _halt(body)


@conformance("R-040")
def test_halt_cause_codes_match_the_spec():
    """The cause encoding is 0 none, 1 loop, 2 local, 3 tamper, 4 command."""
    assert (C_NONE, C_LOOP, C_LOCAL, C_TAMPER, C_COMMAND) == (0, 1, 2, 3, 4)
    assert len(B.HaltSeq().cause) == 3


@conformance("R-040")
def test_halt_escalation_keeps_the_cause():
    """A timer escalation keeps the cause that started the climb."""
    async def body(ctx, dut):
        await _to_run(ctx, dut)
        ctx.set(dut.hb_expired, 1)
        await ctx.tick()
        ctx.set(dut.hb_expired, 0)
        ctx.set(dut.tick, 1)
        for _ in range(5):
            await ctx.tick()
        assert ctx.get(dut.state) == SAFE and ctx.get(dut.cause) == C_LOCAL
    _halt(body, t_throttle=2, t_halt=2)


@conformance("R-043")
def test_halt_state_codes_match_the_spec():
    """The rung encoding is 0 HALTED_INITIAL, 1 RUN, 2 THROTTLE, 3 HALT, 4 SAFE."""
    assert (HALTED_INITIAL, RUN, THROTTLE, HALT, SAFE) == (0, 1, 2, 3, 4)


@conformance("R-043", "R-067")
def test_core_state_and_cause_csrs():
    """STATE at 0x008 and CAUSE at 0x00C follow the sequencer, with the firmware's code in CAUSE[15:8]."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.halt.tamper, 1)
        await ctx.tick()
        ctx.set(dut.cause_fw, 0x5A)
        ctx.set(dut.csr_addr, 0x008)
        assert ctx.get(dut.csr_rdata) == SAFE
        ctx.set(dut.csr_addr, 0x00C)
        assert ctx.get(dut.csr_rdata) == (0x5A << 8) | C_TAMPER
    sim(dut, tb)


@conformance("R-044")
def test_core_levers_csr_bits():
    """LEVERS at 0x080: bit 0 brake, bit 1 PERST#, bit 2 PWR_EN low, for each rung the core can reach quickly."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.csr_addr, 0x080)
        assert ctx.get(dut.csr_rdata) == 0b111                   # boot: brake, reset, power off
        ctx.set(dut.loop_sense, 1)
        ctx.set(dut.hb.window, 50)
        ctx.set(dut.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb.hb_valid, 0)
        await ctx.tick()
        assert ctx.get(dut.csr_rdata) == 0b000                   # RUN
        ctx.set(dut.halt.cmd_throttle, 1)
        await ctx.tick()
        ctx.set(dut.halt.cmd_throttle, 0)
        assert ctx.get(dut.csr_rdata) == 0b001                   # THROTTLE: brake only
        ctx.set(dut.halt.cmd_halt, 1)
        await ctx.tick()
        ctx.set(dut.halt.cmd_halt, 0)
        assert ctx.get(dut.csr_rdata) == 0b011                   # HALT: brake and reset, power on
    sim(dut, tb)


@conformance("R-045")
def test_core_boot_state_levers_and_switch():
    """Out of reset: HALTED_INITIAL, brake and reset asserted at the pads (active low), PWR_EN low, switch open."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        assert ctx.get(dut.halt.state) == HALTED_INITIAL
        assert (ctx.get(dut.pwrbrk_n), ctx.get(dut.perst_n), ctx.get(dut.pwr_en), ctx.get(dut.loop_out_open)) == (0, 0, 0, 1)
    sim(dut, tb)


@conformance("R-046")
def test_core_reset_from_run_returns_to_boot_rung():
    """A reset (the watchdog's) in RUN puts the core back in HALTED_INITIAL with the loop switch open."""
    rst = Signal()
    core = B.GovernorCore(cap_entries=1, ticket_entries=1)
    dut = ResetInserter(rst)(core)

    async def tb(ctx):
        ctx.set(core.loop_sense, 1)
        ctx.set(core.hb.window, 50)
        ctx.set(core.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(core.hb.hb_valid, 0)
        await ctx.tick()
        assert ctx.get(core.halt.state) == RUN and ctx.get(core.loop_out_open) == 0
        ctx.set(rst, 1)
        await ctx.tick()
        ctx.set(rst, 0)
        assert ctx.get(core.halt.state) == HALTED_INITIAL and ctx.get(core.loop_out_open) == 1
        assert ctx.get(core.pwr_en) == 0
    sim(dut, tb)


# ================================================================ loop
@conformance("R-048")
def test_loop_pad_follows_switch_request():
    """loop_out_open is the sequencer's switch_open, both ways, in the same cycle."""
    dut = B.LoopIO()

    async def tb(ctx):
        for v in (1, 0, 1, 0):
            ctx.set(dut.switch_open, v)
            assert ctx.get(dut.loop_out_open) == v
    sim(dut, tb)


@conformance("R-049", "R-143")
def test_loop_one_noisy_sample_is_not_a_loss():
    """A single low sample between good ones never declares a loss."""
    dut = B.LoopIO()

    async def tb(ctx):
        ctx.set(dut.sample, 1)
        for v in (1, 0, 1, 0, 1, 0, 1):
            ctx.set(dut.loop_sense, v)
            await ctx.tick()
            assert ctx.get(dut.loop_lost) == 0
    sim(dut, tb)


@conformance("R-049", "R-143")
def test_loop_two_low_samples_declare_loss():
    """Two consecutive low samples declare the loss; it stays declared while current is absent."""
    dut = B.LoopIO()

    async def tb(ctx):
        ctx.set(dut.sample, 1)
        ctx.set(dut.loop_sense, 0)
        await ctx.tick()
        assert ctx.get(dut.loop_lost) == 0
        await ctx.tick()
        assert ctx.get(dut.loop_lost) == 1
        for _ in range(5):
            await ctx.tick()
            assert ctx.get(dut.loop_lost) == 1
    sim(dut, tb)


@conformance("R-049")
def test_loop_counts_only_on_sample_strobes():
    """Cycles without a sample strobe do not count toward the debounce."""
    dut = B.LoopIO()

    async def tb(ctx):
        ctx.set(dut.loop_sense, 0)
        ctx.set(dut.sample, 1)
        await ctx.tick()
        ctx.set(dut.sample, 0)
        for _ in range(10):
            await ctx.tick()
            assert ctx.get(dut.loop_lost) == 0
    sim(dut, tb)


@conformance("R-050")
def test_core_loop_csr_bits():
    """LOOP at 0x07C: bit 0 current sensed, bit 1 own switch open."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.csr_addr, 0x07C)
        assert ctx.get(dut.csr_rdata) == 0b10
        ctx.set(dut.loop_sense, 1)
        assert ctx.get(dut.csr_rdata) == 0b11
        ctx.set(dut.hb.window, 50)
        ctx.set(dut.hb.hb_valid, 1)
        await ctx.tick()                                         # the heartbeat loads
        ctx.set(dut.hb.hb_valid, 0)
        await ctx.tick()                                         # armed: the switch closes, RUN
        assert ctx.get(dut.csr_rdata) == 0b01
    sim(dut, tb)


# ================================================================ meter
@conformance("R-051")
def test_meter_host_write_refused_and_flagged():
    """A host write is flagged and leaves every counter as it was."""
    dut = B.Meter(slots=2, width=16)

    async def tb(ctx):
        ctx.set(dut.add_tokens, 5)
        ctx.set(dut.strobe, 1)
        await ctx.tick()
        ctx.set(dut.strobe, 0)
        ctx.set(dut.host_wr, 1)
        assert ctx.get(dut.host_wr_refused) == 1
        await ctx.tick()
        assert ctx.get(dut.rd_tokens) == 5
    sim(dut, tb)


@conformance("R-052")
def test_meter_counters_only_increase_random():
    """500 random strobes with small adds across slots: no counter ever goes down (while it does not wrap)."""
    dut = B.Meter(slots=4, width=32)
    rng = random.Random(6)

    async def tb(ctx):
        last = {(s, k): 0 for s in range(4) for k in range(4)}
        for _ in range(500):
            ctx.set(dut.slot, rng.randrange(4))
            for sig in (dut.add_tokens, dut.add_cycles, dut.add_in, dut.add_out):
                ctx.set(sig, rng.randrange(1000))
            ctx.set(dut.strobe, rng.random() < 0.7)
            await ctx.tick()
            for s in range(4):
                ctx.set(dut.rd_slot, s)
                for k, sig in enumerate((dut.rd_tokens, dut.rd_cycles, dut.rd_in, dut.rd_out)):
                    v = ctx.get(sig)
                    assert v >= last[(s, k)]
                    last[(s, k)] = v
    sim(dut, tb)


@conformance("R-052")
def test_meter_slots_are_independent():
    """A strobe on one slot changes only that slot."""
    dut = B.Meter(slots=2, width=16)

    async def tb(ctx):
        ctx.set(dut.slot, 1)
        ctx.set(dut.add_cycles, 9)
        ctx.set(dut.strobe, 1)
        await ctx.tick()
        ctx.set(dut.strobe, 0)
        ctx.set(dut.rd_slot, 0)
        assert ctx.get(dut.rd_cycles) == 0
        ctx.set(dut.rd_slot, 1)
        assert ctx.get(dut.rd_cycles) == 9
    sim(dut, tb)


@conformance("R-053")
def test_core_meter_csr_layout():
    """METER_SLOT[n] at 0x200 + 32n: tokens, cycles, bytes in, bytes out, each a low and a high word."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.meter.slot, 2)
        vals = (0x1_0000_0001, 0x2_0000_0002, 0x3_0000_0003, 0x4_0000_0004)
        for sig, v in zip((dut.meter.add_tokens, dut.meter.add_cycles, dut.meter.add_in, dut.meter.add_out), vals):
            ctx.set(sig, v)
        ctx.set(dut.meter.strobe, 1)
        await ctx.tick()
        ctx.set(dut.meter.strobe, 0)
        for k, v in enumerate(vals):
            ctx.set(dut.csr_addr, 0x200 + 32 * 2 + 8 * k)
            assert ctx.get(dut.csr_rdata) == v & 0xFFFF_FFFF
            ctx.set(dut.csr_addr, 0x200 + 32 * 2 + 8 * k + 4)
            assert ctx.get(dut.csr_rdata) == v >> 32
    sim(dut, tb)


# ================================================================ mailbox (block level; the differential is separate)
async def mbox_deliver(ctx, dut, seq, slot=0, cmd=0x10, signed_cmd=None, epoch_match=1, exempt=0, needs_run=0,
                       running=1, sig_ok=1):
    ctx.set(dut.frame_seq, seq)
    ctx.set(dut.key_slot, slot)
    ctx.set(dut.cmd, cmd)
    ctx.set(dut.signed_cmd, cmd if signed_cmd is None else signed_cmd)
    ctx.set(dut.epoch_match, epoch_match)
    ctx.set(dut.epoch_exempt, exempt)
    ctx.set(dut.needs_run, needs_run)
    ctx.set(dut.running, running)
    ctx.set(dut.doorbell, 1)
    await ctx.tick()
    ctx.set(dut.doorbell, 0)
    asked = ctx.get(dut.verify_req)
    dispatched = 0
    if asked:
        ctx.set(dut.sig_done, 1)
        ctx.set(dut.sig_ok, sig_ok)
        dispatched = ctx.get(dut.dispatch)
        await ctx.tick()
        ctx.set(dut.sig_done, 0)
    return dispatched, ctx.get(dut.status), asked


def _mbox(body):
    dut = B.Mailbox()

    async def tb(ctx):
        await body(ctx, dut)
    sim(dut, tb)


@conformance("R-054", "R-059")
def test_mbox_good_frame_dispatches_once():
    """A good frame dispatches with the command on cmd_out; the same frame again is a replay."""
    async def body(ctx, dut):
        d, s, _ = await mbox_deliver(ctx, dut, seq=5, cmd=0x0F)
        assert (d, s, ctx.get(dut.cmd_out)) == (1, S_OK, 0x0F)
        d, s, _ = await mbox_deliver(ctx, dut, seq=5, cmd=0x0F)
        assert (d, s) == (0, S_BAD_SEQ)
    _mbox(body)


@conformance("R-054")
def test_mbox_sequence_must_strictly_increase():
    """A lower sequence number than the last accepted is refused; a higher one (gaps allowed) is accepted."""
    async def body(ctx, dut):
        await mbox_deliver(ctx, dut, seq=10)
        assert (await mbox_deliver(ctx, dut, seq=9))[1] == S_BAD_SEQ
        assert (await mbox_deliver(ctx, dut, seq=100))[1] == S_OK
    _mbox(body)


@conformance("R-054", "R-060")
def test_mbox_sequence_is_per_key_slot():
    """Each signer key slot keeps its own last accepted sequence."""
    async def body(ctx, dut):
        await mbox_deliver(ctx, dut, seq=50, slot=1)
        assert (await mbox_deliver(ctx, dut, seq=1, slot=2))[1] == S_OK
        assert (await mbox_deliver(ctx, dut, seq=49, slot=1))[1] == S_BAD_SEQ
        assert ctx.get(dut.last_seq[1]) == 50 and ctx.get(dut.last_seq[2]) == 1
    _mbox(body)


@conformance("R-055")
def test_mbox_stale_epoch_refused_unless_exempt():
    """A stale epoch is refused with status 5; the same frame marked epoch-exempt goes through."""
    async def body(ctx, dut):
        assert (await mbox_deliver(ctx, dut, seq=1, epoch_match=0))[1] == S_BAD_EPOCH
        assert (await mbox_deliver(ctx, dut, seq=1, epoch_match=0, exempt=1))[1] == S_OK
    _mbox(body)


@conformance("R-056")
def test_mbox_bad_signature_refused():
    """A frame whose signature does not verify is refused with status 3 and not dispatched."""
    async def body(ctx, dut):
        d, s, asked = await mbox_deliver(ctx, dut, seq=1, sig_ok=0)
        assert (d, s, asked) == (0, S_BAD_SIG, 1)
    _mbox(body)


@conformance("R-056", "R-059")
def test_mbox_no_dispatch_before_signature():
    """While the crypto core has not answered, nothing is dispatched and the status is busy."""
    async def body(ctx, dut):
        ctx.set(dut.frame_seq, 1)
        ctx.set(dut.epoch_match, 1)
        ctx.set(dut.running, 1)
        ctx.set(dut.doorbell, 1)
        await ctx.tick()
        ctx.set(dut.doorbell, 0)
        for _ in range(10):
            assert ctx.get(dut.dispatch) == 0 and ctx.get(dut.status) == S_BUSY and ctx.get(dut.verify_req) == 1
            await ctx.tick()
    _mbox(body)


@conformance("R-057", "R-063")
def test_mbox_signed_for_another_command_is_status_7():
    """A good signature over a different command is status 7, not dispatched, and the sequence is not consumed."""
    async def body(ctx, dut):
        d, s, _ = await mbox_deliver(ctx, dut, seq=3, cmd=0x10, signed_cmd=0x0E)
        assert (d, s, ctx.get(dut.last_seq[0])) == (0, S_WRONG_CMD, 0)
        assert (await mbox_deliver(ctx, dut, seq=3, cmd=0x10))[1] == S_OK
    _mbox(body)


@conformance("R-061")
def test_mbox_refused_when_not_running():
    """A command class that needs RUN is refused with status 6 while not running, and is not sent for verification."""
    async def body(ctx, dut):
        d, s, asked = await mbox_deliver(ctx, dut, seq=1, needs_run=1, running=0)
        assert (d, s, asked) == (0, S_REFUSED, 0)
        assert (await mbox_deliver(ctx, dut, seq=1, needs_run=1, running=1))[1] == S_OK
    _mbox(body)


@conformance("R-061")
def test_mbox_status_codes_match_the_register_map():
    """MBOX_STATUS codes: 0 idle, 1 busy, 2 ok, 3 bad signature, 4 bad sequence, 5 bad epoch, 6 refused (7 wrong command, from section 3)."""
    assert (S_IDLE, S_BUSY, S_OK, S_BAD_SIG, S_BAD_SEQ, S_BAD_EPOCH, S_REFUSED, S_WRONG_CMD) == (0, 1, 2, 3, 4, 5, 6, 7)
    assert B.Mailbox().status.shape().width <= 8


@conformance("R-062", "R-054")
def test_mbox_failed_frames_do_not_consume_sequence():
    """Bad signature, bad epoch, refused and wrong-command frames leave the sequence where it was."""
    async def body(ctx, dut):
        await mbox_deliver(ctx, dut, seq=4)
        for kw in ({"sig_ok": 0}, {"epoch_match": 0}, {"needs_run": 1, "running": 0}, {"signed_cmd": 0x01}):
            await mbox_deliver(ctx, dut, seq=9, **kw)
            assert ctx.get(dut.last_seq[0]) == 4, kw
    _mbox(body)


@conformance("R-062")
def test_mbox_no_dispatch_without_all_checks_random():
    """3,000 random frames with inputs held stable: dispatch happens exactly when seq > last, epoch ok or exempt,
    running or not needed, signature good and command matching; and then the sequence moves to frame_seq."""
    rng = random.Random(7)

    async def body(ctx, dut):
        last = [0] * 8
        for _ in range(3000):
            slot = rng.randrange(8)
            seq = max(0, last[slot] + rng.randrange(-2, 3))
            f = dict(slot=slot, seq=seq, cmd=0x10, signed_cmd=0x10 if rng.random() < 0.8 else 0x0E,
                     epoch_match=rng.random() < 0.8, exempt=rng.random() < 0.3, needs_run=rng.random() < 0.4,
                     running=rng.random() < 0.7, sig_ok=rng.random() < 0.8)
            d, s, _ = await mbox_deliver(ctx, dut, **f)
            should = (seq > last[slot] and (f["epoch_match"] or f["exempt"]) and (f["running"] or not f["needs_run"])
                      and f["sig_ok"] and f["signed_cmd"] == f["cmd"])
            assert d == should, (f, s)
            if should:
                last[slot] = seq
            assert ctx.get(dut.last_seq[slot]) == last[slot]
    _mbox(body)


@conformance("R-060", "R-061")
def test_core_mbox_status_and_seq_csrs():
    """Through the core: MBOX_STATUS at 0x104 reports refused while not RUN for a run-needing class; MBOX_SEQ at 0x108 tracks slot 0."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        m = dut.mbox
        ctx.set(m.frame_seq, 3)
        ctx.set(m.epoch_match, 1)
        ctx.set(m.needs_run, 1)
        ctx.set(dut.doorbell, 1)
        await ctx.tick()
        ctx.set(dut.doorbell, 0)
        ctx.set(dut.csr_addr, 0x104)
        assert ctx.get(dut.csr_rdata) == S_REFUSED              # boot rung is not RUN
        ctx.set(m.needs_run, 0)
        ctx.set(dut.doorbell, 1)
        await ctx.tick()
        ctx.set(dut.doorbell, 0)
        ctx.set(m.sig_done, 1)
        ctx.set(m.sig_ok, 1)
        await ctx.tick()
        ctx.set(m.sig_done, 0)
        assert ctx.get(dut.csr_rdata) == S_OK
        ctx.set(dut.csr_addr, 0x108)
        assert ctx.get(dut.csr_rdata) == 3
    sim(dut, tb)


# ================================================================ top: the CSR window
@conformance("R-064", "R-065")
def test_core_has_no_csr_write_port():
    """GovernorCore exposes no CSR write data or write enable; the doorbell is the only host-driven CSR input."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)
    names = {s.name for s in dut.ports()}
    assert not any(("wdata" in n) or n.endswith("_we") or ("csr_w" in n) for n in names), names
    host_side = {n for n in names if n.startswith("csr_")}
    assert host_side == {"csr_addr", "csr_rdata"}, host_side


@conformance("R-064", "R-065")
def test_core_csr_reads_have_no_side_effects():
    """Sweeping every CSR address for many cycles changes no state the CSR window shows."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        def snap():
            return (ctx.get(dut.halt.state), ctx.get(dut.life.state), ctx.get(dut.epoch.epoch), ctx.get(dut.alarms.alarms),
                    ctx.get(dut.mbox.status), ctx.get(dut.meas0.value), ctx.get(dut.hb.remaining))
        before = snap()
        for a in range(0, 0x500, 4):
            ctx.set(dut.csr_addr, a)
            await ctx.tick()
        assert snap() == before
    sim(dut, tb)


@conformance("R-066")
def test_core_id_register():
    """ID at 0x000 reads a fixed, non-zero silicon id and revision."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.csr_addr, 0x000)
        v = ctx.get(dut.csr_rdata)
        assert v == 0x5347_0001 and (v >> 16) == 0x5347
    sim(dut, tb)


@conformance("R-068")
def test_core_log_window_is_not_decoded():
    """LOG_HEAD and LOG_SIZE are firmware-mapped: the RTL core returns 0 there."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        for a in list(range(0x400, 0x420, 4)) + [0x420, 0x424]:
            ctx.set(dut.csr_addr, a)
            assert ctx.get(dut.csr_rdata) == 0
    sim(dut, tb)


@conformance("R-001")
def test_core_mono_csr_low_and_high_words():
    """MONO_LO and MONO_HI at 0x070 and 0x074 read the 64-bit counter."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.mono.hwm, 0x0000_0002_FFFF_FFFE)
        ctx.set(dut.mono.load_hwm, 1)
        await ctx.tick()
        ctx.set(dut.mono.load_hwm, 0)
        ctx.set(dut.tick, 1)
        for _ in range(3):
            await ctx.tick()
        ctx.set(dut.csr_addr, 0x070)
        lo = ctx.get(dut.csr_rdata)
        ctx.set(dut.csr_addr, 0x074)
        hi = ctx.get(dut.csr_rdata)
        assert (hi << 32) | lo == 0x0000_0003_0000_0001
    sim(dut, tb)


# ================================================================ alarms
@conformance("R-069", "R-072", "R-088")
def test_alarm_any_source_sets():
    """Any bit presented on set_mask becomes and stays set."""
    dut = B.Alarms(width=8)

    async def tb(ctx):
        for bit in range(8):
            ctx.set(dut.set_mask, 1 << bit)
            await ctx.tick()
        ctx.set(dut.set_mask, 0)
        for _ in range(5):
            await ctx.tick()
        assert ctx.get(dut.alarms) == 0xFF and ctx.get(dut.any) == 1
    sim(dut, tb)


@conformance("R-070", "R-089")
def test_alarm_clear_needs_authorization():
    """clear_mask without clear_authorized is refused and flagged; with it, only the named bits clear."""
    dut = B.Alarms(width=8)

    async def tb(ctx):
        ctx.set(dut.set_mask, 0b1011)
        await ctx.tick()
        ctx.set(dut.set_mask, 0)
        ctx.set(dut.clear_mask, 0b0011)
        assert ctx.get(dut.clear_refused) == 1
        await ctx.tick()
        assert ctx.get(dut.alarms) == 0b1011
        ctx.set(dut.clear_authorized, 1)
        await ctx.tick()
        assert ctx.get(dut.alarms) == 0b1000
    sim(dut, tb)


@conformance("R-070", "R-072")
def test_alarm_set_beats_clear_in_the_same_cycle():
    """A bit set and cleared (authorized) in the same cycle stays set: a fresh alarm is never lost."""
    dut = B.Alarms(width=8)

    async def tb(ctx):
        ctx.set(dut.set_mask, 0b1)
        ctx.set(dut.clear_mask, 0b1)
        ctx.set(dut.clear_authorized, 1)
        await ctx.tick()
        assert ctx.get(dut.alarms) == 0b1
    sim(dut, tb)


@conformance("R-072")
def test_alarm_monotone_without_authorization_random():
    """1,000 random cycles with clear_authorized low: the alarm word only gains bits."""
    dut = B.Alarms(width=16)
    rng = random.Random(8)

    async def tb(ctx):
        last = 0
        for _ in range(1000):
            ctx.set(dut.set_mask, rng.getrandbits(16) if rng.random() < 0.1 else 0)
            ctx.set(dut.clear_mask, rng.getrandbits(16))
            await ctx.tick()
            a = ctx.get(dut.alarms)
            assert a & last == last
            last = a
    sim(dut, tb)


@conformance("R-071")
def test_core_alarms_csr():
    """ALARMS at 0x084 reads the sticky alarm word. (Bits 31 and 30 became hardware-owned on 23 October 2026, so the
    firmware-raised word here uses bit 29; R-148 checks that firmware cannot raise 31 and 30.)"""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.alarms.set_mask, 0x2000_0001)
        await ctx.tick()
        ctx.set(dut.alarms.set_mask, 0)
        ctx.set(dut.csr_addr, 0x084)
        assert ctx.get(dut.csr_rdata) == 0x2000_0001
    sim(dut, tb)


@conformance("R-091", "R-052")
def test_meter_frozen_slot_stays_put_without_strobes():
    """END_MODEL freezes a slot by the firmware no longer strobing it: with no strobe, no counter moves, whatever the add inputs say."""
    dut = B.Meter(slots=2, width=16)

    async def tb(ctx):
        ctx.set(dut.slot, 0)
        ctx.set(dut.add_tokens, 3)
        ctx.set(dut.strobe, 1)
        await ctx.tick()
        ctx.set(dut.strobe, 0)
        for sig in (dut.add_tokens, dut.add_cycles, dut.add_in, dut.add_out):
            ctx.set(sig, 999)
        for _ in range(10):
            await ctx.tick()
        assert (ctx.get(dut.rd_tokens), ctx.get(dut.rd_cycles), ctx.get(dut.rd_in), ctx.get(dut.rd_out)) == (3, 0, 0, 0)
    sim(dut, tb)


@conformance("R-093", "R-009", "R-087")
def test_core_epoch_switch_kills_every_old_capability():
    """After a quorum-backed epoch switch, every capability minted under the old epoch tag is refused at once, on every point."""
    dut = B.GovernorCore(cap_entries=2, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.loop_sense, 1)
        ctx.set(dut.hb.window, 50)
        ctx.set(dut.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb.hb_valid, 0)
        await ctx.tick()
        assert ctx.get(dut.halt.state) == RUN
        for c in dut.caps.values():
            _cap_insert(ctx, c, budget=100, expiry=1 << 30, etag=0)
        await ctx.tick()
        for c in dut.caps.values():
            ctx.set(c.ins, 0)
            assert _cap_lookup(ctx, c, nbytes=1)[0] == 1
            ctx.set(c.lk, 0)
        ctx.set(dut.epoch.new_epoch, 0xBEEF)
        ctx.set(dut.epoch.commit, 1)
        ctx.set(dut.epoch.quorum_ok, 1)
        await ctx.tick()
        ctx.set(dut.epoch.commit, 0)
        for c in dut.caps.values():
            assert _cap_lookup(ctx, c, nbytes=1) == (0, R_STALE_EPOCH)
    sim(dut, tb)


@conformance("R-082", "R-055")
def test_mbox_self_authenticating_command_rides_on_the_firmware_verdict():
    """A command that authenticates itself in the body (a k-of-n policy image) has no frame signature; the RTL has
    no bypass for it, so it is dispatched only when the firmware reports the body's own verification on sig_ok."""
    async def body(ctx, dut):
        d, s, _ = await mbox_deliver(ctx, dut, seq=1, cmd=0x0C, epoch_match=0, exempt=1, sig_ok=0)
        assert (d, s) == (0, S_BAD_SIG)
        d, s, _ = await mbox_deliver(ctx, dut, seq=1, cmd=0x0C, epoch_match=0, exempt=1, sig_ok=1)
        assert (d, s) == (1, S_OK)
    _mbox(body)
