"""Finding reproducers for the hard-core blocks, and cross-checks of the RTL against the functional model.

A test marked ``finding=`` asserts what the spec requires; on today's RTL it fails by assertion, and the
assertion message says what the RTL did instead. FINDINGS.md has the write-up for each id. The two leads the
brief named are F-05 (CLEAR and tamper in the same cycle) and F-06 (the lifecycle value before the fuse load).
"""
from __future__ import annotations

import os
import random
import re

from govsim import reasons
from govsim.cluster import build_rack
from govsim.endpoints import Switch

from rtl.governor_rtl.cap_table import R_OK
from rtl.governor_rtl.halt import C_LOCAL, C_TAMPER, HALT, HALTED_INITIAL, RUN, SAFE, THROTTLE
from rtl.governor_rtl.lifecycle import PRODUCTION, TEST

from .framework import B, conformance, levers, sim
from .tests_blocks import _cap_insert, _cap_lookup, _to_run, mbox_deliver

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ================================================================ F-05: CLEAR and tamper in the same cycle (lead a)
async def _halted_by_command(ctx, dut):
    await _to_run(ctx, dut)
    ctx.set(dut.cmd_halt, 1)
    await ctx.tick()
    ctx.set(dut.cmd_halt, 0)
    assert ctx.get(dut.state) == HALT


# F-05 closed on fix/halt: tamper now outranks CLEAR. This test passes and guards the fix.
@conformance("R-042", "R-035")
def test_finding_clear_and_tamper_pulse_same_cycle_ends_safe():
    """F-05: the spec says tamper means SAFE. A one-cycle tamper strobe (a glitch detector) in the same cycle as
    an authorized CLEAR: the RTL takes the CLEAR branch first, lands in HALTED_INITIAL with cause none, and the
    tamper is gone. Required: SAFE with cause tamper."""
    dut = B.HaltSeq()

    async def tb(ctx):
        await _halted_by_command(ctx, dut)
        ctx.set(dut.clear, 1)
        ctx.set(dut.tamper, 1)
        await ctx.tick()
        ctx.set(dut.clear, 0)
        ctx.set(dut.tamper, 0)
        for _ in range(3):
            await ctx.tick()
        assert (ctx.get(dut.state), ctx.get(dut.cause)) == (SAFE, C_TAMPER), \
            f"state {ctx.get(dut.state)} cause {ctx.get(dut.cause)}: the tamper was lost to the CLEAR"
    sim(dut, tb)


# F-05 closed on fix/halt: tamper now outranks CLEAR. This test passes and guards the fix.
@conformance("R-042", "R-035")
def test_finding_clear_and_tamper_same_cycle_never_leaves_safe_rung():
    """F-05, the one-cycle view: even with tamper held high (a mesh cut), the cycle after CLEAR plus tamper must
    show SAFE; the RTL shows HALTED_INITIAL for one cycle, then SAFE."""
    dut = B.HaltSeq()

    async def tb(ctx):
        await _halted_by_command(ctx, dut)
        ctx.set(dut.clear, 1)
        ctx.set(dut.tamper, 1)
        await ctx.tick()
        ctx.set(dut.clear, 0)
        assert ctx.get(dut.state) == SAFE, f"state {ctx.get(dut.state)} in the cycle after CLEAR + tamper"
    sim(dut, tb)


@conformance("R-042")
def test_level_tamper_with_clear_settles_in_safe():
    """Not a finding on its own: with tamper held as a level, the sequencer is back in SAFE one cycle later, and
    during that cycle the levers are the boot rung's (brake, reset, power off), so the GPU is never released."""
    dut = B.HaltSeq()

    async def tb(ctx):
        await _halted_by_command(ctx, dut)
        ctx.set(dut.clear, 1)
        ctx.set(dut.tamper, 1)
        await ctx.tick()
        ctx.set(dut.clear, 0)
        assert levers(ctx, dut) == (1, 1, 0)
        await ctx.tick()
        assert ctx.get(dut.state) == SAFE and ctx.get(dut.cause) == C_TAMPER
    sim(dut, tb)


@conformance("R-074", "R-042")
def test_model_tamper_is_safe_and_unclearable():
    """The model: a tamper event zeroizes, goes to SAFE, and every command after it (CLEAR included) is refused."""
    rack = build_rack(1, "rack")
    rack.bring_up()
    g = rack.nodes[0].governor
    g.tamper_event()
    assert g.state == "SAFE" and g.levers == {"pwrbrk": True, "perst": True, "pwr_en": False}
    r = g.command("CLEAR", {}, rack._authority_env({"type": "clear"}, g))
    assert r == {"ok": False, "why": reasons.TAMPER_ZEROIZED}


# ================================================================ F-06: lifecycle before the fuse load (lead b)
# F-06 closed by the L7 group A merge: this test passes and guards the fix.
@conformance("R-010", "R-011")
def test_finding_lifecycle_debug_before_fuse_load():
    """F-06: a part fused PRODUCTION, between reset and the fuse load: the register holds its reset value 0 (TEST)
    and debug_grant follows debug_req. Required: debug is impossible on production silicon, at every cycle."""
    dut = B.Lifecycle()

    async def tb(ctx):
        ctx.set(dut.fuse_state, PRODUCTION)       # the fuses say production; load has not happened yet
        ctx.set(dut.debug_req, 1)
        assert ctx.get(dut.debug_grant) == 0, f"debug granted with state {ctx.get(dut.state)} before the fuse load"
    sim(dut, tb)


# F-06 is only half closed: debug is no longer granted before the fuse load, but the LIFECYCLE register still
# reads TEST in that window, so this reproducer still fails, on the register half.
@conformance("R-012", "R-011", finding="F-06")
def test_finding_core_reports_test_lifecycle_before_fuse_load():
    """F-06 through the core: LIFECYCLE reads 0 (test) and the debug_grant port is high on a production part
    until the firmware strobes life.load. Required: never test, never granted."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.life.fuse_state, PRODUCTION)
        ctx.set(dut.life.debug_req, 1)
        ctx.set(dut.csr_addr, 0x004)
        for _ in range(4):                        # four cycles of firmware boot before it gets to the fuse load
            await ctx.tick()
            assert ctx.get(dut.life.debug_grant) == 0 and ctx.get(dut.csr_rdata) != TEST, \
                f"LIFECYCLE reads {ctx.get(dut.csr_rdata)} and debug_grant is {ctx.get(dut.life.debug_grant)}"
    sim(dut, tb)


@conformance("R-011")
def test_lifecycle_after_load_debug_is_dead():
    """The other half of F-06: once loaded, a production part never grants debug again, whatever arrives."""
    dut = B.Lifecycle()
    rng = random.Random(9)

    async def tb(ctx):
        ctx.set(dut.fuse_state, PRODUCTION)
        ctx.set(dut.load, 1)
        await ctx.tick()
        for _ in range(500):
            ctx.set(dut.load, rng.random() < 0.3)
            ctx.set(dut.fuse_state, rng.randrange(4))
            ctx.set(dut.advance, rng.random() < 0.3)
            ctx.set(dut.advance_to, rng.randrange(4))
            ctx.set(dut.debug_req, 1)
            assert ctx.get(dut.debug_grant) == 0
            await ctx.tick()
    sim(dut, tb)


# ================================================================ F-07: a signed HALT to a governor already in SAFE
async def _safe_by_local_cause(ctx, dut):
    await _to_run(ctx, dut)
    ctx.set(dut.hb_expired, 1)
    await ctx.tick()
    ctx.set(dut.hb_expired, 0)
    ctx.set(dut.tick, 1)
    for _ in range(4):
        await ctx.tick()
    ctx.set(dut.tick, 0)
    assert ctx.get(dut.state) == SAFE and ctx.get(dut.cause) == C_LOCAL and ctx.get(dut.switch_open) == 0


# F-07 closed by Yobie's call 1 (23 October 2026): a HALT opens the loop on every rung. This test passes and guards it.
@conformance("R-038", "R-144")
def test_finding_cmd_halt_in_safe_opens_the_loop():
    """F-07 (RTL): a governor that climbed to SAFE on a local cause keeps its loop switch closed (right: local
    causes do not stop the rack). A signed HALT then arrives. The spec: switch_open sets on cmd_halt, and a
    signed HALT is a loop-opening cause that stops the whole domain. The RTL ignores cmd_halt in SAFE."""
    dut = B.HaltSeq(t_throttle=2, t_halt=2)

    async def tb(ctx):
        await _safe_by_local_cause(ctx, dut)
        ctx.set(dut.cmd_halt, 1)
        await ctx.tick()
        ctx.set(dut.cmd_halt, 0)
        assert ctx.get(dut.switch_open) == 1, "signed HALT in SAFE left the loop switch closed"
    sim(dut, tb)


# F-07 closed (model half): enter_safe_mode never applies a lower rung. This test passes and guards it.
@conformance("R-035", "R-036", "R-145")
def test_model_finding_halt_in_safe_does_not_descend():
    """F-07 (model): the same event in govsim moves the governor DOWN from SAFE to HALT and turns slot power back
    on. The spec: the rung never descends without CLEAR; SAFE has PWR_EN low."""
    rack = build_rack(1, "rack")
    rack.bring_up()
    g = rack.nodes[0].governor
    g.enter_safe_mode(reasons.HEARTBEAT_LOST)
    g._apply_rung("HALT", opens_loop=False)
    g._apply_rung("SAFE", opens_loop=False)
    assert g.state == "SAFE" and g.loop_switch_open is False
    assert rack.halt(g)["ok"]
    assert g.state == "SAFE" and g.levers["pwr_en"] is False, f"model went to {g.state}, levers {g.levers}"


@conformance("R-038")
def test_cmd_halt_in_throttle_from_local_cause_opens_loop():
    """The neighbouring case conforms: a signed HALT to a governor throttled on a local cause halts it and opens the loop."""
    dut = B.HaltSeq()

    async def tb(ctx):
        await _to_run(ctx, dut)
        ctx.set(dut.hb_expired, 1)
        await ctx.tick()
        ctx.set(dut.hb_expired, 0)
        ctx.set(dut.cmd_halt, 1)
        await ctx.tick()
        assert ctx.get(dut.state) == HALT and ctx.get(dut.switch_open) == 1
    sim(dut, tb)


# ================================================================ F-15: loop_lost outside RUN and THROTTLE
@conformance("R-038", finding="F-15")
def test_finding_loop_lost_in_halt_sets_switch_open():
    """F-15 (spec text): 07 section 3 says switch_open sets on loop_lost. A governor in HALT on a local cause
    (switch closed) sees the loop drop: the RTL, like the model, only acts on loop_lost in RUN or THROTTLE."""
    dut = B.HaltSeq(t_throttle=2, t_halt=50)

    async def tb(ctx):
        await _to_run(ctx, dut)
        ctx.set(dut.local_trip, 1)
        await ctx.tick()
        ctx.set(dut.local_trip, 0)
        ctx.set(dut.tick, 1)
        for _ in range(2):
            await ctx.tick()
        ctx.set(dut.tick, 0)
        assert ctx.get(dut.state) == HALT and ctx.get(dut.switch_open) == 0
        ctx.set(dut.loop_lost, 1)
        await ctx.tick()
        assert ctx.get(dut.switch_open) == 1, "loop_lost in HALT did not set switch_open"
    sim(dut, tb)


# ================================================================ F-08: the "millisecond" is 1,024 microseconds
@conformance("R-032", "R-029", "R-031", finding="F-08")
def test_finding_heartbeat_expires_on_time():
    """F-08: a 2 ms heartbeat window must have expired after 2,000 microsecond ticks (plus one cycle for the
    register). The core's millisecond strobe is every 2^10 = 1,024 ticks, so it expires after 2,048: every timer
    the spec states in milliseconds runs 2.4 percent long (a 5 s heartbeat expiry becomes 5.12 s)."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        ctx.set(dut.hb.window, 2)
        ctx.set(dut.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(dut.hb.hb_valid, 0)
        ctx.set(dut.tick, 1)
        for _ in range(2001):
            await ctx.tick()
        assert ctx.get(dut.hb.expired) == 1, f"heartbeat still live after 2,001 us; HB_REMAIN = {ctx.get(dut.hb.remaining)}"
    sim(dut, tb)


@conformance("R-032")
def test_core_ms_strobe_is_derived_from_the_counter():
    """What does conform: the slow strobe is derived from the microsecond counter (it is a function of MONO's low
    bits and the tick), so nothing outside the core can make the timers run faster or slower."""
    dut = B.GovernorCore(cap_entries=1, ticket_entries=1)

    async def tb(ctx):
        strobes = []
        ctx.set(dut.tick, 1)
        for i in range(3 * 1024):
            if ctx.get(dut.tick_ms):
                strobes.append(ctx.get(dut.mono.value))
            await ctx.tick()
        assert len(strobes) == 3 and all((v & 1023) == 1023 for v in strobes), strobes
    sim(dut, tb)


# ================================================================ F-09, F-10: capability table
@conformance("R-016", finding="F-09")
def test_finding_cap_refuses_at_zero_budget():
    """F-09: the spec says a lookup refuses at zero. With the budget spent to exactly zero, a zero-byte lookup is
    still allowed by the RTL (budget < bytes is false for 0 < 0). The model's switch does the same."""
    dut = B.CapTable(entries=2)

    async def tb(ctx):
        ctx.set(dut.epoch_tag, 0x11)
        ctx.set(dut.now, 100)
        _cap_insert(ctx, dut, budget=10)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        _cap_lookup(ctx, dut, nbytes=10)
        await ctx.tick()
        assert ctx.get(dut.budget[0]) == 0
        allow, reason = _cap_lookup(ctx, dut, nbytes=0)
        assert allow == 0, f"zero budget, zero-byte lookup allowed (reason {reason})"
    sim(dut, tb)


@conformance("R-014", "R-015", finding="F-10")
def test_finding_cap_reprogramming_a_key_replaces_it():
    """F-10: the table is keyed on (point, peer, dir), and the model's switch replaces an entry when the same key
    is programmed again. The RTL stores a second entry and the priority encoder keeps answering from the first:
    tightening a 1,000-byte capability to 10 bytes leaves 1,000 bytes usable."""
    dut = B.CapTable(entries=4)

    async def tb(ctx):
        ctx.set(dut.epoch_tag, 0x11)
        ctx.set(dut.now, 100)
        _cap_insert(ctx, dut, budget=1000)
        await ctx.tick()
        _cap_insert(ctx, dut, budget=10)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        allow, _ = _cap_lookup(ctx, dut, nbytes=500)
        assert allow == 0, "a 500-byte lookup passed after the capability was reprogrammed to 10 bytes"
    sim(dut, tb)


def _model_switch():
    sw = Switch("pcie", "chip", b"k" * 32, lambda *a: None)
    sw.set_epoch("t1")
    return sw


def _model_cap(sw, peer, direction, budget, expiry):
    cap = {"point": "pcie", "peer": peer, "direction": direction, "budget": budget, "expiry": expiry, "epoch_tag": "t1"}
    cap["mac"] = sw.mac(cap)
    return cap


@conformance("R-014", "R-015")
def test_model_switch_replaces_on_reprogram():
    """The model's side of F-10: programming the same (peer, direction) again replaces the entry."""
    sw = _model_switch()
    assert sw.program(_model_cap(sw, "p7", "both", 1000, 200))
    assert sw.program(_model_cap(sw, "p7", "both", 10, 200))
    assert sw.pass_traffic("p7", "in", 500, 100)[0] is False


@conformance("R-014", "R-015", "R-016", "R-017", "R-018", "R-020", "R-021")
def test_diff_cap_table_random_against_model_switch():
    """1,500 random inserts and lookups on one point into the RTL table and the model's Switch, with keys that never
    overlap (F-10 covers overlap): allow agrees on every lookup and the remaining budgets agree after each one."""
    rng = random.Random(10)
    dut = B.CapTable(entries=8)
    sw = _model_switch()
    peers = [1, 2, 3]
    dirs = {0: "in", 1: "out", 2: "both"}
    stats = {"lookups": 0, "allowed": 0, "inserts": 0}

    async def tb(ctx):
        ctx.set(dut.epoch_tag, 0x11)
        now = 100
        for _ in range(1500):
            now += rng.randrange(0, 3)
            ctx.set(dut.now, now)
            ctx.set(dut.ins, 0)
            ctx.set(dut.lk, 0)
            if rng.random() < 0.15:
                valid = sum(ctx.get(dut.valid[i]) for i in range(8))
                peer, d = rng.choice(peers), rng.randrange(3)
                overlap = any(ctx.get(dut.valid[i]) and ctx.get(dut.peer[i]) == peer and 2 in (d, ctx.get(dut.dir[i]))
                              or ctx.get(dut.valid[i]) and ctx.get(dut.peer[i]) == peer and ctx.get(dut.dir[i]) == d
                              for i in range(8))
                if valid < 8 and not overlap:
                    stats["inserts"] += 1
                    budget, exp = rng.randrange(0, 300), now + rng.randrange(1, 60)
                    _cap_insert(ctx, dut, point=1, peer=peer, d=d, budget=budget, expiry=exp, etag=0x11)
                    assert sw.program(_model_cap(sw, f"p{peer}", dirs[d], budget, exp))
                    await ctx.tick()
                    ctx.set(dut.ins, 0)
                continue
            peer, d, n = rng.choice(peers), rng.randrange(2), rng.randrange(0, 80)
            allow, _ = _cap_lookup(ctx, dut, point=1, peer=peer, d=d, nbytes=n)
            ok, _ = sw.pass_traffic(f"p{peer}", dirs[d], n, now)
            stats["lookups"] += 1
            stats["allowed"] += bool(ok)
            assert bool(allow) == bool(ok), f"peer {peer} dir {d} bytes {n} at {now}: RTL {allow}, model {ok}"
            await ctx.tick()
            rtl_b = sorted((ctx.get(dut.peer[i]), ctx.get(dut.dir[i]), ctx.get(dut.budget[i])) for i in range(8)
                           if ctx.get(dut.valid[i]))
            mod_b = sorted((int(c["peer"][1:]), {v: k for k, v in dirs.items()}[c["direction"]], c["budget"])
                           for c in sw.table.values())
            assert rtl_b == mod_b, (rtl_b, mod_b)
    sim(dut, tb)
    assert stats["allowed"] > 50 and stats["inserts"] > 50, stats
    return stats


# ================================================================ F-11, F-12: counters that wrap
# F-11 closed by the L7 group B merge (acce09f): the meter saturates. This test now passes and guards the fix.
@conformance("R-052")
def test_finding_meter_counter_wraps_at_48_bits():
    """F-11: meter counters only increment. At the prototype's 48 bits (the spec's register is 64), bytes out
    wraps to a small number after 2^48 bytes, about 281 TB, which a long-lived slot can reach."""
    dut = B.Meter(slots=1)

    async def tb(ctx):
        ctx.set(dut.add_out, (1 << 48) - 1)
        ctx.set(dut.strobe, 1)
        await ctx.tick()
        before = ctx.get(dut.rd_out)
        ctx.set(dut.add_out, 16)
        await ctx.tick()
        assert ctx.get(dut.rd_out) >= before, f"bytes out went from {before} to {ctx.get(dut.rd_out)}"
    sim(dut, tb)


# F-12 closed by the L7 group A merge: this test passes and guards the fix.
@conformance("R-002", "R-003")
def test_finding_mono_wraps_from_an_all_ones_high_water_mark():
    """F-12: the counter never decreases. A high-water mark that reads all ones (an erased or failed fuse array)
    loads 2^64 - 1, and the next tick wraps the governor's clock to 0. Low severity: unreachable by counting."""
    dut = B.MonotonicCounter()

    async def tb(ctx):
        ctx.set(dut.hwm, (1 << 64) - 1)
        ctx.set(dut.load_hwm, 1)
        await ctx.tick()
        ctx.set(dut.load_hwm, 0)
        ctx.set(dut.inc, 1)
        await ctx.tick()
        assert ctx.get(dut.value) == (1 << 64) - 1, f"counter wrapped to {ctx.get(dut.value)}"
    sim(dut, tb)


# ================================================================ F-13: mailbox inputs are not latched
@conformance("R-062", "R-054", finding="F-13")
def test_finding_mailbox_sequence_never_moves_backwards():
    """F-13: the Mailbox checks frame_seq at the doorbell and stores frame_seq at sig_done, reading the port live
    both times. If the value on the port changes in between, the RTL dispatches a frame whose sequence is not
    above the last accepted one and moves last_seq backwards. Required: last_seq never decreases."""
    dut = B.Mailbox()

    async def tb(ctx):
        await mbox_deliver(ctx, dut, seq=10)
        ctx.set(dut.frame_seq, 11)
        ctx.set(dut.doorbell, 1)
        await ctx.tick()
        ctx.set(dut.doorbell, 0)
        ctx.set(dut.frame_seq, 3)                  # the port changes while the crypto core works
        ctx.set(dut.sig_done, 1)
        ctx.set(dut.sig_ok, 1)
        await ctx.tick()
        ctx.set(dut.sig_done, 0)
        assert ctx.get(dut.last_seq[0]) >= 10, f"last accepted sequence moved back to {ctx.get(dut.last_seq[0])}"
    sim(dut, tb)


# ================================================================ F-14: the spec's own status table
@conformance("R-061", "R-063", finding="F-14")
def test_finding_spec_status_table_lists_status_7():
    """F-14 (spec): section 3 and the RTL use MBOX_STATUS 7 (wrong command); the register map's row lists 0 to 6."""
    text = open(os.path.join(ROOT, "docs", "04-specification.md"), encoding="utf-8").read()
    row = next(l for l in text.splitlines() if "`MBOX_STATUS`" in l)
    assert re.search(r"\b7\b", row), f"register map row: {row.strip()}"


# ================================================================ cross-model checks that conform
@conformance("R-036")
def test_diff_levers_per_rung_rtl_equals_model():
    """For every rung, the RTL's levers equal the model's _apply_rung levers."""
    rack = build_rack(1, "rack")
    rack.bring_up()
    g = rack.nodes[0].governor
    model = {}
    for name in ("HALTED_INITIAL", "RUN", "THROTTLE", "HALT", "SAFE"):
        g._apply_rung(name)
        model[name] = (int(g.levers["pwrbrk"]), int(g.levers["perst"]), int(g.levers["pwr_en"]))
    dut = B.HaltSeq(t_throttle=1, t_halt=1)
    rtl = {}
    names = {HALTED_INITIAL: "HALTED_INITIAL", RUN: "RUN", THROTTLE: "THROTTLE", HALT: "HALT", SAFE: "SAFE"}

    async def tb(ctx):
        rtl[names[ctx.get(dut.state)]] = levers(ctx, dut)
        await _to_run(ctx, dut)
        rtl["RUN"] = levers(ctx, dut)
        ctx.set(dut.cmd_throttle, 1)
        await ctx.tick()
        ctx.set(dut.cmd_throttle, 0)
        rtl[names[ctx.get(dut.state)]] = levers(ctx, dut)
        ctx.set(dut.tick, 1)
        await ctx.tick()
        rtl[names[ctx.get(dut.state)]] = levers(ctx, dut)
        await ctx.tick()
        rtl[names[ctx.get(dut.state)]] = levers(ctx, dut)
    sim(dut, tb)
    assert rtl == model, (rtl, model)


@conformance("R-037", "R-073")
def test_diff_boot_rung_rtl_equals_model():
    """Fresh out of boot, RTL and model agree: HALTED_INITIAL, levers safe, loop switch open."""
    from govsim.cluster import build_rack as br
    rack = br(1, "rack")
    g = rack.nodes[0].governor
    assert g.state == "HALTED_INITIAL" and g.loop_switch_open is True
    dut = B.HaltSeq()

    async def tb(ctx):
        assert ctx.get(dut.state) == HALTED_INITIAL and ctx.get(dut.switch_open) == 1
        assert levers(ctx, dut) == (int(g.levers["pwrbrk"]), int(g.levers["perst"]), int(g.levers["pwr_en"]))
    sim(dut, tb)


@conformance("R-024")
def test_cap_expired_entry_closes_the_port_for_good():
    """After an expiry is seen, the entry is gone: moving the clock back (it cannot, but the table must not care) finds nothing."""
    dut = B.CapTable(entries=2)

    async def tb(ctx):
        ctx.set(dut.epoch_tag, 0x11)
        ctx.set(dut.now, 100)
        _cap_insert(ctx, dut, expiry=120)
        await ctx.tick()
        ctx.set(dut.ins, 0)
        ctx.set(dut.now, 120)
        _cap_lookup(ctx, dut, nbytes=1)
        await ctx.tick()
        ctx.set(dut.now, 110)
        assert _cap_lookup(ctx, dut, nbytes=1)[0] == 0
        assert _cap_lookup(ctx, dut, nbytes=1)[1] != R_OK
    sim(dut, tb)


@conformance("R-014", "R-093", finding="F-10")
def test_finding_cap_rederived_after_epoch_switch_is_usable():
    """F-10, the fail-closed face: in RUN the epoch switches, the firmware re-derives the port under the new tag
    (spec: it re-derives the switch configuration after any epoch event). The stale entry still sits in a lower
    slot, the priority encoder hits it first, and the new, valid capability is refused R_STALE_EPOCH."""
    dut = B.CapTable(entries=4)

    async def tb(ctx):
        ctx.set(dut.now, 100)
        ctx.set(dut.epoch_tag, 0x11)
        _cap_insert(ctx, dut, etag=0x11)
        await ctx.tick()
        ctx.set(dut.epoch_tag, 0x22)                 # the epoch moved
        _cap_insert(ctx, dut, etag=0x22)              # the re-derived capability
        await ctx.tick()
        ctx.set(dut.ins, 0)
        allow, reason = _cap_lookup(ctx, dut, nbytes=1)
        assert allow == 1, f"re-derived capability refused (reason {reason}): the stale entry shadows it"
    sim(dut, tb)
