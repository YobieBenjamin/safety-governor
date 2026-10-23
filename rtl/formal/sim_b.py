"""L7 check (c): each block driven with random inputs in amaranth.sim for thousands of cycles and compared, every
cycle, with a small reference model written from the spec (docs/07 section 3, docs/04 sections 2 and 9, docs/02),
not from the RTL. This is independent of the solvers and of yosys: a different simulator, a different description.

    python -m rtl.formal.sim_b            # all six
    python -m rtl.formal.sim_b meter      # one

Seeds are fixed so a failure reproduces; the seed and cycle are printed on the first mismatch.
"""
from __future__ import annotations

import random
import sys

from amaranth.sim import Simulator

M48 = (1 << 48) - 1


def _run(dut, bench) -> tuple[bool, str]:
    out: dict = {}

    async def tb(ctx):
        try:
            out["msg"] = await bench(ctx)
        except AssertionError as e:                          # a mismatch with the reference
            out["fail"] = str(e)

    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(tb)
    sim.run()
    return ("fail" not in out), out.get("fail") or out.get("msg", "")


def _check(ok: bool, seed: int, cyc: int, what: str):
    if not ok:
        raise AssertionError(f"seed {seed} cycle {cyc}: {what}")


# ---------------------------------------------------------------------------------------------------- heartbeat
def sim_heartbeat(cycles: int = 4000, seed: int = 1, cls=None) -> tuple[bool, str]:
    from rtl.governor_rtl import Heartbeat
    dut = (cls or Heartbeat)()
    rng = random.Random(seed)

    async def bench(ctx):
        rem = 0                                              # reference: the time left, in ticks
        for c in range(cycles):
            hv = rng.random() < 0.04
            win = rng.choice([0, 1, 2, rng.randrange(1, 40), rng.randrange(1 << 32)])
            tick = rng.random() < 0.6
            ctx.set(dut.hb_valid, hv); ctx.set(dut.window, win); ctx.set(dut.tick, tick)
            _check(ctx.get(dut.remaining) == rem, seed, c, f"remaining {ctx.get(dut.remaining)} != {rem}")
            _check(ctx.get(dut.expired) == (rem == 0), seed, c, "expired is not 'nothing left'")
            # spec: reloads only on a valid heartbeat, to the window given; otherwise one tick takes one off
            rem = win if hv else (rem - 1 if tick and rem else rem)
            await ctx.tick()
        return f"{cycles} random cycles match the spec model (seed {seed})"
    return _run(dut, bench)


# ---------------------------------------------------------------------------------------------------- meter
def sim_meter(cycles: int = 4000, seed: int = 2, cls=None) -> tuple[bool, str]:
    from rtl.governor_rtl import Meter
    dut = (cls or Meter)()
    rng = random.Random(seed)
    names = ("tokens", "cycles", "in", "out")

    async def bench(ctx):
        ref = [[0] * 4 for _ in range(4)]
        for c in range(cycles):
            st = rng.random() < 0.5
            sl = rng.randrange(4)
            adds = [rng.choice([0, 1, rng.randrange(1000), rng.randrange(1 << 48), M48]) for _ in range(4)]
            hw = rng.random() < 0.2
            rs = rng.randrange(4)
            ctx.set(dut.strobe, st); ctx.set(dut.slot, sl); ctx.set(dut.host_wr, hw); ctx.set(dut.rd_slot, rs)
            for sig, a in zip((dut.add_tokens, dut.add_cycles, dut.add_in, dut.add_out), adds):
                ctx.set(sig, a)
            got = [ctx.get(s) for s in (dut.rd_tokens, dut.rd_cycles, dut.rd_in, dut.rd_out)]
            for i in range(4):
                _check(got[i] == ref[rs][i], seed, c, f"slot {rs} {names[i]} {got[i]} != {ref[rs][i]}")
            _check(ctx.get(dut.host_wr_refused) == hw, seed, c, "host write not flagged")
            if st:                                           # spec: counters only go up; saturate rather than wrap
                ref[sl] = [min(M48, ref[sl][i] + adds[i]) for i in range(4)]
            await ctx.tick()
        return f"{cycles} random cycles match the spec model, saturation exercised (seed {seed})"
    return _run(dut, bench)


# ---------------------------------------------------------------------------------------------------- alarms
def sim_alarms(cycles: int = 4000, seed: int = 3, cls=None) -> tuple[bool, str]:
    from rtl.governor_rtl import Alarms
    dut = (cls or Alarms)()
    rng = random.Random(seed)

    async def bench(ctx):
        ref = 0
        for c in range(cycles):
            sm = rng.choice([0, 0, 1 << rng.randrange(32), rng.getrandbits(32)])
            cm = rng.choice([0, 1 << rng.randrange(32), rng.getrandbits(32), 0xFFFF_FFFF])
            au = rng.random() < 0.3
            ctx.set(dut.set_mask, sm); ctx.set(dut.clear_mask, cm); ctx.set(dut.clear_authorized, au)
            _check(ctx.get(dut.alarms) == ref, seed, c, f"alarms {ctx.get(dut.alarms):08x} != {ref:08x}")
            _check(ctx.get(dut.any) == (ref != 0), seed, c, "any")
            _check(ctx.get(dut.clear_refused) == (cm != 0 and not au), seed, c, "clear_refused")
            # spec: sticky; an authorized clear removes the named bits; any source raises, and a raise wins
            ref = ((ref & ~cm) if au else ref) | sm
            await ctx.tick()
        return f"{cycles} random cycles match the spec model (seed {seed})"
    return _run(dut, bench)


# ---------------------------------------------------------------------------------------------------- measure_reg
def sim_measure_reg(cycles: int = 3000, seed: int = 4, cls=None) -> tuple[bool, str]:
    from rtl.governor_rtl import MeasureReg
    dut = (cls or MeasureReg)()
    rng = random.Random(seed)

    async def bench(ctx):
        val, busy, extends = 0, False, 0
        for c in range(cycles):
            ex = rng.random() < 0.3
            data = rng.getrandbits(256)
            done = rng.random() < 0.3
            hout = rng.getrandbits(256)
            ctx.set(dut.extend, ex); ctx.set(dut.data, data); ctx.set(dut.hash_done, done); ctx.set(dut.hash_out, hout)
            _check(ctx.get(dut.value) == val, seed, c, "value changed outside an answered extend")
            _check(ctx.get(dut.busy) == busy, seed, c, "busy")
            _check(ctx.get(dut.hash_req) == (ex and not busy), seed, c, "hash_req")
            _check(ctx.get(dut.hash_in) == (val << 256) | data, seed, c, "hash_in is not value || data")
            # spec: extend asks the engine for H(value || data); the engine's answer is latched; nothing else writes
            if busy and done:
                val, busy, extends = hout, False, extends + 1
            elif not busy and ex:
                busy = True
            await ctx.tick()
        return f"{cycles} random cycles, {extends} extends, match the spec model (seed {seed})"
    return _run(dut, bench)


# ---------------------------------------------------------------------------------------------------- loop_io
def sim_loop_io(cycles: int = 4000, seed: int = 5, cls=None) -> tuple[bool, str]:
    from rtl.governor_rtl import LoopIO
    dut = (cls or LoopIO)()
    rng = random.Random(seed)

    async def bench(ctx):
        last_two = []                                        # the most recent sense samples, newest last
        losses = 0
        for c in range(cycles):
            so = rng.random() < 0.5
            smp = rng.random() < 0.3
            sense = rng.random() < 0.6
            ctx.set(dut.switch_open, so); ctx.set(dut.sample, smp); ctx.set(dut.loop_sense, sense)
            lost = len(last_two) == 2 and not any(last_two)
            _check(ctx.get(dut.loop_out_open) == so, seed, c, "the pad does not follow the switch")
            _check(ctx.get(dut.loop_lost) == lost, seed, c, f"loop_lost {ctx.get(dut.loop_lost)} != {lost} after {last_two}")
            losses += lost
            # spec: a loss is declared after two sense periods without current (docs/02, docs/04 section 9)
            if smp:
                last_two = (last_two + [sense])[-2:]
            await ctx.tick()
        return f"{cycles} random cycles ({losses} with loss declared) match the spec model (seed {seed})"
    return _run(dut, bench)


# ---------------------------------------------------------------------------------------------------- governor_core
HALTED_INITIAL, RUN, THROTTLE, HALT, SAFE = 0, 1, 2, 3, 4


class SeqRef:
    """The safe-mode sequencer from the spec: docs/01 (ladder; loop-opening vs local causes), docs/07 section 3 (halt
    row), and Yobie's two calls of 23 October 2026 (docs/04 sections 2 and 3, docs/02 section 1): a HALT opens the loop
    on every rung, SAFE included (SAFE stays SAFE, the command is the cause unless it is tamper); a chip never armed
    since reset raises NO_FIRST_HEARTBEAT once it has waited t_boot milliseconds; an authorized EXCLUDE closes the
    switch of a chip in HALTED_INITIAL with no cause and no live heartbeat, and nothing else."""

    def __init__(self, t_throttle, t_halt, t_boot):
        self.tt, self.th, self.tb = t_throttle, t_halt, t_boot
        self.state, self.cause, self.sw_open, self.timer = HALTED_INITIAL, 0, True, 0
        self.hb_seen, self.boot, self.excluded = False, 0, False

    def no_first_hb(self):
        return (not self.hb_seen) and self.boot >= self.tb

    def step(self, i):
        """i: tamper, clear, lost, cmd_halt, hb_expired, local_trip, cmd_throttle, hb_ok, loop_sense, tick, cmd_exclude."""
        s, run_like = self.state, self.state in (RUN, THROTTLE)
        ns, nc, nsw, nt = s, self.cause, self.sw_open, self.timer
        seen, exc = self.hb_seen, self.excluded
        if i["tamper"]:                                       # tamper outranks CLEAR (F-05, fixed 23 October)
            ns, nc, nsw = SAFE, 3, True
        elif i["clear"] and s != HALTED_INITIAL:
            ns, nc, nt = HALTED_INITIAL, 0, 0                # clear does not touch the switch
        elif i["lost"] and run_like:
            ns, nc, nsw, nt = HALT, 1, True, 0
        elif i["cmd_halt"] and s == SAFE:                     # Yobie's call 1: SAFE stays SAFE, the loop opens
            nc, nsw = (3 if self.cause == 3 else 4), True
        elif i["cmd_halt"]:
            ns, nc, nsw, nt = HALT, 4, True, 0
        elif (i["hb_expired"] or i["local_trip"] or i["cmd_throttle"]) and s == RUN:
            ns, nc, nt = THROTTLE, 2, 0
        elif s == HALTED_INITIAL and self.cause == 0 and i["hb_ok"]:
            nsw, seen, exc = False, True, False               # armed: ends any exclusion
            if i["loop_sense"] and not i["lost"]:             # RUN needs a clean loop sample (F1, fixed 23 October)
                ns = RUN
        elif i["cmd_exclude"] and s == HALTED_INITIAL and self.cause == 0:
            nsw, exc = False, True                            # Yobie's call 2: the levers stay, the loop closes
        elif i["tick"] and s == THROTTLE:
            ns, nt = (HALT, 0) if self.timer + 1 >= self.tt else (s, self.timer + 1)
        elif i["tick"] and s == HALT:
            ns, nt = (SAFE, 0) if self.timer + 1 >= self.th else (s, self.timer + 1)
        if i["tamper"] or i["cmd_halt"]:
            exc = False
        waiting = not self.hb_seen and s == HALTED_INITIAL and self.cause == 0 and not i["hb_ok"]
        nb = self.boot + 1 if waiting and i["tick"] and self.boot != 0xFFFF else self.boot
        self.state, self.cause, self.sw_open, self.timer = ns, nc, nsw, nt
        self.hb_seen, self.boot, self.excluded = seen, nb, exc


def sim_halt_seq(cycles: int = 4000, seed: int = 11, cls=None) -> tuple[bool, str]:
    """Several fresh power-ons (a new DUT each), so the boot window and EXCLUDE are visited often."""
    from rtl.governor_rtl import HaltSeq
    rng = random.Random(seed)
    names = ("tamper", "clear", "loop_lost", "cmd_halt", "hb_expired", "local_trip", "cmd_throttle", "hb_ok",
             "loop_sense", "tick", "cmd_exclude")
    stats = {"seen": set(), "excl": 0, "nfh": 0}
    seg = 500

    def segment(base):
        dut = (cls or HaltSeq)(t_throttle=3, t_halt=4, t_boot=5)
        ref = SeqRef(3, 4, 5)
        quiet_hb = rng.random() < 0.5                          # half the power-ons wait a long time for a heartbeat

        async def bench(ctx):
            for c in range(base, base + seg):
                i = {"tamper": rng.random() < 0.004, "clear": rng.random() < 0.02, "loop_lost": rng.random() < 0.05,
                     "cmd_halt": rng.random() < 0.02, "hb_expired": rng.random() < 0.05, "local_trip": rng.random() < 0.01,
                     "cmd_throttle": rng.random() < 0.01, "hb_ok": rng.random() < (0.01 if quiet_hb else 0.08),
                     "loop_sense": rng.random() < 0.9, "tick": rng.random() < 0.7, "cmd_exclude": rng.random() < 0.05}
                for k in names:
                    ctx.set(getattr(dut, k), i[k])
                got = {k: ctx.get(getattr(dut, k)) for k in ("state", "cause", "switch_open", "timer", "hb_seen",
                                                              "boot_timer", "excluded", "no_first_hb", "pwr_en", "perst", "pwrbrk")}
                s = ref.state
                want = {"state": s, "cause": ref.cause, "switch_open": int(ref.sw_open), "timer": ref.timer,
                        "hb_seen": int(ref.hb_seen), "boot_timer": ref.boot, "excluded": int(ref.excluded),
                        "no_first_hb": int(ref.no_first_hb()), "pwr_en": int(s not in (HALTED_INITIAL, SAFE)),
                        "perst": int(s in (HALTED_INITIAL, HALT, SAFE)), "pwrbrk": int(s != RUN)}
                _check(got == want, seed, c, f"{got} != {want}")
                stats["seen"].add(s); stats["excl"] += ref.excluded; stats["nfh"] += ref.no_first_hb()
                ref.step({**i, "lost": i["loop_lost"]})
                await ctx.tick()
            return ""
        return _run(dut, bench)

    for base in range(0, cycles, seg):
        ok, why = segment(base)
        if not ok:
            return ok, why
    return True, (f"{cycles} random cycles over {cycles // seg} power-ons match the spec model; rungs visited "
                  f"{sorted(stats['seen'])}, {stats['excl']} cycles excluded, {stats['nfh']} with the boot alarm up (seed {seed})")


class CoreRef:
    """The sequencer (SeqRef), heartbeat, loop debounce, millisecond prescaler and hardware alarm bits of
    governor_core, from the spec: docs/07 section 3 (halt, heartbeat, halt_loop, top rows), docs/04 section 9 (ms tick
    from the us tick), docs/04 section 2 (ALARMS bits 31 NO_FIRST_HEARTBEAT and 30 EXCLUDED: hardware-owned, sticky).
    Levers per rung from docs/07: brake unless RUN; reset in HALTED_INITIAL, HALT, SAFE; power off in HALTED_INITIAL
    and SAFE."""

    def __init__(self, t_throttle, t_halt, ms_shift, t_boot):
        self.seq = SeqRef(t_throttle, t_halt, t_boot)
        self.ms = 1 << ms_shift
        self.rem, self.div, self.samples, self.alarms = 0, 0, [], 0

    state = property(lambda self: self.seq.state)
    cause = property(lambda self: self.seq.cause)

    def outputs(self):
        s = self.seq.state
        return {"pwrbrk_n": int(s == RUN), "perst_n": int(s not in (HALTED_INITIAL, HALT, SAFE)),
                "pwr_en": int(s not in (HALTED_INITIAL, SAFE)), "loop_out_open": int(self.seq.sw_open)}

    def step(self, i):
        tick_ms = i["tick"] and self.div == self.ms - 1
        expired = self.rem == 0
        lost = len(self.samples) == 2 and not any(self.samples)
        hw = (int(self.seq.no_first_hb()) << 31) | (int(self.seq.excluded) << 30)
        self.alarms |= hw | (i["set_mask"] & ~(3 << 30))     # firmware cannot raise the hardware bits
        self.seq.step({**i, "lost": lost, "hb_expired": expired, "hb_ok": not expired, "tick": tick_ms})
        self.rem = i["window"] if i["hb_valid"] else (self.rem - 1 if tick_ms and self.rem else self.rem)
        if i["tick"]:
            self.div = (self.div + 1) % self.ms
        if i["sample"]:
            self.samples = (self.samples + [i["loop_sense"]])[-2:]
        return tick_ms


def sim_governor_core(cycles: int = 3000, seed: int = 6, cls=None) -> tuple[bool, str]:
    from rtl.governor_rtl import GovernorCore
    kw = dict(cap_entries=2, ticket_entries=2, t_throttle_ms=3, t_halt_ms=4, ms_shift=2, t_boot_ms=3)
    dut = (cls or GovernorCore)(**kw)
    ref = CoreRef(3, 4, 2, 3)
    rng = random.Random(seed)
    pins = {"pwrbrk_n": dut.pwrbrk_n, "perst_n": dut.perst_n, "pwr_en": dut.pwr_en, "loop_out_open": dut.loop_out_open}

    async def bench(ctx):
        seen, excl = set(), 0
        for c in range(cycles):
            # rare causes, so the ladder gets climbed instead of being reset every few cycles
            i = {"tick": rng.random() < 0.8, "sample": rng.random() < 0.3, "loop_sense": rng.random() < 0.85,
                 "hb_valid": rng.random() < 0.03, "window": rng.randrange(0, 12),
                 "tamper": rng.random() < 0.003, "cmd_halt": rng.random() < 0.004, "cmd_throttle": rng.random() < 0.004,
                 "local_trip": rng.random() < 0.004, "clear": rng.random() < 0.01, "cmd_exclude": rng.random() < 0.02,
                 "set_mask": rng.choice([0, 0, 0, 0, 1 << 31, 1 << 30, rng.randrange(1 << 32)])}
            sigs = {"tick": dut.tick, "sample": dut.sample, "loop_sense": dut.loop_sense, "hb_valid": dut.hb.hb_valid,
                    "window": dut.hb.window, "tamper": dut.halt.tamper, "cmd_halt": dut.halt.cmd_halt,
                    "cmd_throttle": dut.halt.cmd_throttle, "local_trip": dut.halt.local_trip, "clear": dut.halt.clear,
                    "cmd_exclude": dut.halt.cmd_exclude, "set_mask": dut.alarms.set_mask}
            for k, s in sigs.items():
                ctx.set(s, i[k])
            # the host side does random things too: reads anywhere, rings the doorbell; none of it may matter
            ctx.set(dut.csr_addr, rng.randrange(4096)); ctx.set(dut.doorbell, rng.random() < 0.1)
            # and the fuse side jumps the monotonic counter upward, often keeping its low bits: that must not move
            # the millisecond (FINDINGS-b.md, F2), so the reference model's prescaler ignores it
            hammer = rng.random() < 0.5
            ctx.set(dut.mono.load_hwm, hammer)
            if hammer:
                ctx.set(dut.mono.hwm, ctx.get(dut.mono.value) + rng.choice([4, 8, 4096, rng.randrange(1, 1 << 20)]))
            exp = ref.outputs()
            for k, s in pins.items():
                _check(ctx.get(s) == exp[k], seed, c, f"pin {k} {ctx.get(s)} != {exp[k]} in state {ref.state}")
            _check(ctx.get(dut.halt.state) == ref.state, seed, c, f"state {ctx.get(dut.halt.state)} != {ref.state}")
            _check(ctx.get(dut.halt.cause) == ref.cause, seed, c, f"cause {ctx.get(dut.halt.cause)} != {ref.cause}")
            _check(ctx.get(dut.hb.remaining) == ref.rem, seed, c, f"heartbeat {ctx.get(dut.hb.remaining)} != {ref.rem}")
            _check(ctx.get(dut.halt.excluded) == int(ref.seq.excluded), seed, c, "excluded")
            _check(ctx.get(dut.halt.no_first_hb) == int(ref.seq.no_first_hb()), seed, c, "no_first_hb")
            _check(ctx.get(dut.alarms.alarms) == ref.alarms, seed, c, f"ALARMS {ctx.get(dut.alarms.alarms):#x} != {ref.alarms:#x}")
            excl += ref.seq.excluded
            tms = ref.step(i)
            _check(ctx.get(dut.tick_ms) == tms, seed, c, "millisecond strobe")
            seen.add(ref.state)
            await ctx.tick()
        return f"{cycles} random cycles match the spec model; rungs visited {sorted(seen)}, {excl} cycles excluded (seed {seed})"
    return _run(dut, bench)


SIMS = {"halt_seq": sim_halt_seq, "heartbeat": sim_heartbeat, "meter": sim_meter, "alarms": sim_alarms, "measure_reg": sim_measure_reg,
        "loop_io": sim_loop_io, "governor_core": sim_governor_core}

if __name__ == "__main__":
    bad = 0
    for name in (sys.argv[1:] or SIMS):
        ok, why = SIMS[name]()
        print(f"  {'SIM-OK' if ok else 'SIM-FAILED'}  {name}: {why}")
        bad += not ok
    sys.exit(1 if bad else 0)
