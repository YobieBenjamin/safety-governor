# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The independent second look for the WAVE-FORMAL-PROOFS-ON-VERILOG second set: random cycles of the Amaranth Python source in amaranth.sim,
compared every cycle against a small reference model written from the spec (not from the RTL), outputs before the
clock edge and state after it. Run on the real block (must agree on every cycle) and on every mutant in BLOCKS_A
(a mutant that the random run never tells apart from the model is reported as such; the formal proof is what
must catch it, this is the cross-check).

The reference models are what docs/04-specification.md, docs/07-verification-plan.md section 3 and govsim say each
block does. Where the spec and the RTL disagree (FINDINGS-a.md), the model follows the RTL's documented behaviour and
the finding is pinned separately, so this check stays green while the finding is open.

The random driver keeps the mailbox's RTL-MAILBOX-FRAME-HELD-STILL obligation (frame fields stable while verifying), as the proof assumes.
"""
from __future__ import annotations

import os
import random

from amaranth import ClockDomain, Elaboratable, Module, Signal
from amaranth.sim import Simulator

RTL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CYCLES = int(os.environ.get("FORMAL_SIM_CYCLES", "20000"))          # on the real block
MUTANT_CYCLES = int(os.environ.get("FORMAL_SIM_MUTANT_CYCLES", "4000"))
M64 = (1 << 64) - 1


class Mismatch(Exception):
    pass


def load_class(src_file: str, cls: str, old: str | None = None, new: str | None = None):
    src = open(os.path.join(RTL, "governor_rtl", src_file), encoding="utf-8").read()
    if old is not None:
        if src.count(old) != 1:
            raise SystemExit(f"mutant text not found exactly once in {src_file}: {old!r}")
        src = src.replace(old, new)
    ns: dict = {"__name__": "sim_a_" + cls}
    exec(compile(src, src_file, "exec"), ns)
    return ns[cls]


class _Harness(Elaboratable):
    """The block under an explicit sync domain, so the testbench can drive reset in any cycle."""
    def __init__(self, dut):
        self.dut, self.cd = dut, ClockDomain("sync")

    def elaborate(self, platform):
        m = Module()
        m.domains.sync = self.cd
        m.submodules.dut = self.dut
        return m


# ---------------------------------------------------------------- reference models
class LifecycleRef:
    def __init__(self): self.reset()
    def reset(self): self.state, self.loaded = 0, 0
    def comb(self, i):
        g = i["debug_req"] and self.loaded and self.state < 2
        return {"debug_grant": int(g), "debug_refused": int(i["debug_req"] and not g),
                "advance_refused": int(i["advance"] and i["advance_to"] <= self.state)}
    def tick(self, i):
        if i["load"]:
            self.loaded = 1
            self.state = max(self.state, i["fuse_state"])
        elif i["advance"]:
            self.state = max(self.state, i["advance_to"])
    def regs(self): return {"state": self.state, "loaded": self.loaded}
    @staticmethod
    def stim(r, prev):
        return {"rst": r.random() < .03, "load": r.random() < .1, "fuse_state": r.randrange(4), "advance": r.random() < .2,
                "advance_to": r.randrange(4), "debug_req": r.random() < .5}


class MonotonicRef:
    def __init__(self): self.reset()
    def reset(self): self.value = 0
    def comb(self, i): return {"refused": int(i["dec_req"])}
    def tick(self, i):
        if i["load_hwm"]:
            self.value = max(self.value, i["hwm"])
        elif i["inc"]:
            self.value = min(self.value + 1, M64)        # never wraps
    def regs(self): return {"value": self.value}
    @staticmethod
    def stim(r, prev):
        hwm = r.choice([r.randrange(64), r.getrandbits(64), M64, M64 - 1, M64 - 3])
        return {"rst": r.random() < .02, "load_hwm": r.random() < .1, "hwm": hwm, "inc": r.random() < .6, "dec_req": r.random() < .2}


class EpochRef:
    def __init__(self): self.reset()
    def reset(self): self.epoch = 0
    def comb(self, i): return {"host_refused": int(i["host_wr"]), "epoch_tag": self.epoch & 0xFFFF}
    def tick(self, i):
        if i["commit"] and i["quorum_ok"]:
            self.epoch = i["new_epoch"]
    def regs(self): return {"epoch": self.epoch}
    @staticmethod
    def stim(r, prev):
        return {"rst": r.random() < .02, "commit": r.random() < .3, "quorum_ok": r.random() < .5, "new_epoch": r.getrandbits(256),
                "host_wr": r.random() < .3, "host_data": r.getrandbits(256)}


class TicketRef:
    N = 8
    def __init__(self): self.reset()
    def reset(self): self.used: list[int] = []
    def comb(self, i):
        seen = i["id_in"] in self.used
        full = len(self.used) == self.N
        return {"seen": int(seen), "full": int(full), "burned": int(i["burn"] and not seen and not full)}
    def tick(self, i):
        if self.comb(i)["burned"]:
            self.used.append(i["id_in"])
    def regs(self): return {}
    @staticmethod
    def stim(r, prev):
        return {"rst": r.random() < .01, "query": r.random() < .5, "burn": r.random() < .5, "id_in": r.randrange(12)}


class CapRef:
    N = 8
    def __init__(self): self.reset()
    def reset(self): self.e: list[dict | None] = [None] * self.N
    def _hit(self, i):
        for k, c in enumerate(self.e):
            if c and c["point"] == i["lk_point"] and c["peer"] == i["lk_peer"] and (c["dir"] == i["lk_dir"] or c["dir"] == 2):
                return k
        return None
    def _look(self, i):
        k = self._hit(i)
        if k is None:
            return k, 0, 1
        c = self.e[k]
        if c["expiry"] <= i["now"]:
            return k, 0, 2
        if c["etag"] != i["epoch_tag"]:
            return k, 0, 3
        if c["budget"] < i["lk_bytes"]:
            return k, 0, 4
        return k, 1, 0
    def comb(self, i):
        free = next((k for k, c in enumerate(self.e) if c is None), None)
        out = {"ins_ok": int(bool(i["ins"] and i["mac_ok"] and free is not None and not i["clear_all"])),
               "ins_full": int(bool(i["ins"] and free is None)), "allow": 0}
        if i["lk"]:
            _, allow, reason = self._look(i)
            out.update(allow=allow, reason=reason)
        return out
    def tick(self, i):
        free = next((k for k, c in enumerate(self.e) if c is None), None)
        k, allow, reason = self._look(i) if i["lk"] else (None, 0, None)
        if i["lk"] and allow:
            self.e[k]["budget"] -= i["lk_bytes"]
        if i["lk"] and reason == 2:
            self.e[k] = None
        if i["clear_all"]:
            self.e = [None] * self.N
        elif i["ins"] and i["mac_ok"] and free is not None:
            self.e[free] = {"point": i["ins_point"], "peer": i["ins_peer"], "dir": i["ins_dir"], "budget": i["ins_budget"],
                            "expiry": i["ins_expiry"], "etag": i["ins_epoch_tag"]}
    def regs(self):
        out = {}
        for k, c in enumerate(self.e):
            out[f"valid[{k}]"] = int(c is not None)
            if c:
                out[f"budget[{k}]"] = c["budget"]
        return out
    @staticmethod
    def stim(r, prev):
        now = (prev.get("now", 0) + r.choice([0, 0, 1, 2])) if r.random() > .01 else r.getrandbits(32)
        return {"rst": r.random() < .01, "ins": r.random() < .3, "ins_point": r.randrange(2), "ins_peer": r.randrange(3),
                "ins_dir": r.randrange(4), "ins_budget": r.randrange(20), "ins_expiry": (now + r.randrange(-3, 40)) & 0xFFFF_FFFF,
                "ins_epoch_tag": r.randrange(2), "mac_ok": r.random() < .75, "clear_all": r.random() < .02,
                "lk": r.random() < .7, "lk_point": r.randrange(2), "lk_peer": r.randrange(3), "lk_dir": r.randrange(4),
                "lk_bytes": r.randrange(9), "now": now & 0xFFFF_FFFF, "epoch_tag": r.randrange(2) if r.random() < .3 else 0}


class MailboxRef:
    FIELDS = ("frame_seq", "key_slot", "cmd", "epoch_match", "epoch_exempt", "needs_run")
    def __init__(self): self.reset()
    def reset(self): self.verify, self.status, self.cmd_out, self.seq = 0, 0, 0, [0] * 8
    def comb(self, i):
        d = self.verify and i["sig_done"] and i["sig_ok"] and i["signed_cmd"] == i["cmd"]
        return {"verify_req": self.verify, "dispatch": int(bool(d))}
    def tick(self, i):
        if not self.verify:
            if i["doorbell"]:
                if not i["frame_seq"] > self.seq[i["key_slot"]]:
                    self.status = 4
                elif not (i["epoch_match"] or i["epoch_exempt"]):
                    self.status = 5
                elif i["needs_run"] and not i["running"]:
                    self.status = 6
                else:
                    self.status, self.verify = 1, 1
        elif i["sig_done"]:
            if i["sig_ok"] and i["signed_cmd"] == i["cmd"]:
                self.seq[i["key_slot"]] = i["frame_seq"]
                self.status, self.cmd_out = 2, i["cmd"]
            elif i["sig_ok"]:
                self.status = 7
            else:
                self.status = 3
            self.verify = 0
        if i["epoch_advanced"]:                           # adversarial audit 3: a new epoch restarts every key slot
            self.seq = [0] * 8
    def regs(self):
        return {"status": self.status, "cmd_out": self.cmd_out, **{f"last_seq[{k}]": v for k, v in enumerate(self.seq)}}
    @staticmethod
    def stim(r, prev):
        i = {"rst": False, "doorbell": r.random() < .4, "frame_seq": r.randrange(16), "key_slot": r.randrange(3),
             "cmd": r.randrange(4), "epoch_match": r.random() < .8, "epoch_exempt": r.random() < .3,
             "needs_run": r.random() < .5, "running": r.random() < .7, "sig_done": r.random() < .4, "sig_ok": r.random() < .8,
             "epoch_advanced": r.random() < .05}
        i["signed_cmd"] = i["cmd"] if r.random() < .7 else r.randrange(4)
        if prev.get("_verifying"):                        # RTL-MAILBOX-FRAME-HELD-STILL: the frame holds still while it is being verified
            for f in MailboxRef.FIELDS:
                i[f] = prev[f]
        return i


REFS = {"lifecycle": LifecycleRef, "monotonic_counter": MonotonicRef, "epoch_reg": EpochRef, "ticket_store": TicketRef,
        "cap_table": CapRef, "mailbox": MailboxRef}


def _sig(dut, name):
    if "[" in name:
        base, k = name[:-1].split("[")
        return getattr(dut, base)[int(k)]
    return getattr(dut, name)


def run(block: str, cls, cycles: int, seed: int) -> str | None:
    """None if the block agreed with the model on every cycle, else the first disagreement."""
    dut = cls()
    ref = REFS[block]()
    h = _Harness(dut)
    sim = Simulator(h)
    sim.add_clock(1e-6)
    r = random.Random(seed)
    result: list = [None]

    async def tb(ctx):
        prev: dict = {}
        for n in range(cycles):
            i = ref.stim(r, prev)
            for k, v in i.items():
                if k != "rst":
                    ctx.set(getattr(dut, k), int(v))
            ctx.set(h.cd.rst, int(i["rst"]))
            if not i["rst"]:
                for k, v in ref.comb(i).items():
                    got = ctx.get(_sig(dut, k))
                    if got != v:
                        result[0] = f"cycle {n}: {k} = {got}, the spec says {v} (inputs {i})"
                        return
            await ctx.tick()
            ref.reset() if i["rst"] else ref.tick(i)
            for k, v in ref.regs().items():
                got = ctx.get(_sig(dut, k))
                if got != v:
                    result[0] = f"cycle {n}: {k} = {got} after the edge, the spec says {v} (inputs {i})"
                    return
            prev = dict(i, _verifying=getattr(ref, "verify", 0))

    sim.add_testbench(tb)
    sim.run()
    return result[0]


def check(block: str, entry):
    src_file, cls_name, mutants = entry
    bad = run(block, load_class(src_file, cls_name), CYCLES, seed=1)
    yield (bad is None), (f"AGREES  {block} random sim: {CYCLES} random cycles of the Python source match the spec model"
                          if bad is None else f"DISAGREES  {block} random sim: {bad}")
    caught = []
    for k, (desc, old, new) in enumerate(mutants):
        if run(block, load_class(src_file, cls_name, old, new), MUTANT_CYCLES, seed=100 + k) is not None:
            caught.append(desc)
    missed = [d for d, _, _ in mutants if d not in caught]
    # informational: the formal proof is what must catch every mutant; this says how sharp the second look is
    yield True, (f"         {block} random sim also tells apart {len(caught)} of {len(mutants)} mutants"
                 + (f" (not: {'; '.join(missed)})" if missed else ""))
