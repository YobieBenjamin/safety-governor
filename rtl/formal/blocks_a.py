# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""WAVE-FORMAL-PROOFS-ON-VERILOG, second set: mailbox, cap_table, ticket_store, epoch_reg, monotonic_counter, lifecycle.

BLOCKS_A has the same shape as BLOCKS in __main__.py: block -> (Amaranth source file, class name, mutants), each
mutant a one-line bug planted on purpose that the block's properties (rtl/formal/<block>.sv) must catch BY ASSERTION.

CHECKS_A are the extra, independent checks python -m rtl.formal runs after the proofs. Each takes the runner's
prove function and the list of blocks asked for, and yields (ok, line):
  - second_solver: the same proofs again (bounded and k-induction) with yices instead of z3.
  - random_sim: thousands of random cycles of the Amaranth Python source in amaranth.sim, compared every cycle
    against a reference model written from the spec (rtl/formal/sim_a.py), on the real block and on every mutant.
  - findings: each finding in FINDINGS-a.md that is still open has a property file under findings_a/ that must
    FAIL by assertion on today's Verilog. If one starts to pass, the finding is stale and the run says so.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(os.path.dirname(HERE), "gen")

# cap_table's bounded check costs about 5 s at depth 4 and 96 s at depth 8 on this machine (8 entries of 94 bits,
# one-cycle CAM), and its k-induction already closes at k = 2 (measured 23 October 2026; k = 1 fails, and I did not dig
# into which assertion needs the second step). So it runs at depth 5: a 5-step bounded check and
# 5-induction, which is a complete proof for every reachable state, not a shallow one. Every planted cap_table bug
# shows within 4 cycles of reset (insert, then look up), so the bounded check still catches them by assertion.
# mailbox: adversarial audit 3 widened its eight sequence registers to 64 bits and added the epoch reset. The bounded
# check to depth 25 then took about 9 minutes with yices and longer with z3 on this machine (26 October 2026), while
# k-induction closes at k = 2 in seconds. So it runs at depth 8: an 8-step bounded check and 8-induction, a complete
# proof for every reachable state. Every planted mailbox bug shows within 4 cycles of reset (doorbell, verify, dispatch,
# or an epoch strobe), so the bounded check still catches each one by assertion.
DEPTH_A = {"cap_table": 5, "mailbox": 8}

# yices could not finish ticket_store on this machine (8 slots of 32-bit ids compared against an arbitrary watched
# id): the bounded check to depth 10 and the 2-induction each ran out a 15-minute cap, where z3 does depth 25 in a
# few minutes (measured 23 October 2026). So ticket_store has one solver, z3, plus the random simulation.
NO_SECOND_SOLVER = {"ticket_store": "yices did not finish in 15 minutes even at 2-induction (23 October 2026); "
                                    "z3 and the random simulation are this block's checks"}

BLOCKS_A = {
    "lifecycle": ("lifecycle.py", "Lifecycle", [
        ("debug granted before the fuses are read (the code before 23 October 2026, RTL-DEBUG-WINDOW-AFTER-RESET)",
         "self.debug_grant.eq(self.debug_req & self.loaded & (self.state < PRODUCTION)),",
         "self.debug_grant.eq(self.debug_req & (self.state < PRODUCTION)),"),
        ("debug granted in PRODUCTION",
         "self.debug_grant.eq(self.debug_req & self.loaded & (self.state < PRODUCTION)),",
         "self.debug_grant.eq(self.debug_req & self.loaded & (self.state <= PRODUCTION)),"),
        ("a fuse load can move the state down",
         "with m.If(self.fuse_state > self.state):", "with m.If(self.fuse_state != self.state):"),
        ("an advance can move the state down (back to TEST)",
         "with m.If(self.advance_to > self.state):", "with m.If(self.advance_to != self.state):"),
        ("a refused debug request is not flagged",
         "self.debug_refused.eq(self.debug_req & ~(self.loaded & (self.state < PRODUCTION))),",
         "self.debug_refused.eq(self.debug_req & (self.state >= PRODUCTION)),"),
    ]),
    "monotonic_counter": ("monotonic.py", "MonotonicCounter", [
        ("the counter wraps to zero at the top (the code before 23 October 2026, RTL-COUNTER-WRAPPED-TO-ZERO)",
         "with m.Elif(self.inc & ~self.value.all()):", "with m.Elif(self.inc):"),
        ("a lower high-water mark pulls the counter down",
         "with m.If(self.hwm > self.value):", "with m.If(self.hwm != self.value):"),
        ("a decrement path exists",
         "m.d.sync += self.value.eq(self.value + 1)", "m.d.sync += self.value.eq(self.value + 1 - (self.dec_req << 1))"),
        ("the fuse high-water mark is not restored at boot",
         "m.d.sync += self.value.eq(self.hwm)", "m.d.sync += self.value.eq(self.value)"),
        ("a decrement attempt is not reported",
         "m.d.comb += self.refused.eq(self.dec_req)", "m.d.comb += self.refused.eq(0)"),
    ]),
    "epoch_reg": ("epoch_reg.py", "EpochReg", [
        ("commit without a quorum",
         "with m.If(self.commit & self.quorum_ok):", "with m.If(self.commit):"),
        ("the host write port reaches the register",
         "with m.If(self.commit & self.quorum_ok):", "with m.If((self.commit & self.quorum_ok) | self.host_wr):"),
        ("commit latches the host's data, not the verified epoch",
         "m.d.sync += self.epoch.eq(self.new_epoch)", "m.d.sync += self.epoch.eq(self.host_data)"),
        ("the epoch tag comes from the wrong bits",
         "self.epoch_tag.eq(self.epoch[:16])", "self.epoch_tag.eq(self.epoch[16:32])"),
        ("a host write is not flagged",
         "self.host_refused.eq(self.host_wr)", "self.host_refused.eq(0)"),
    ]),
    "ticket_store": ("ticket_store.py", "TicketStore", [
        ("a seen id can be burned again (double admit)",
         "with m.If(self.burn & ~match & (free != n)):", "with m.If(self.burn & (free != n)):"),
        ("a full store evicts slot 0 to make room (a burned id comes back)",
         "m.d.comb += free.eq(n)", "m.d.comb += free.eq(0)"),
        ("a burn pulses but does not stick",
         "m.d.sync += [self.valid[free].eq(1), self.ids[free].eq(self.id_in)]",
         "m.d.sync += [self.valid[free].eq(0), self.ids[free].eq(self.id_in)]"),
        ("the last slot is never compared (its id can be replayed)",
         "        for i in range(n):\n            with m.If(self.valid[i] & (self.ids[i] == self.id_in)):",
         "        for i in range(n - 1):\n            with m.If(self.valid[i] & (self.ids[i] == self.id_in)):"),
        ("full is never raised",
         "m.d.comb += self.full.eq(free == n)", "m.d.comb += self.full.eq(0)"),
    ]),
    "cap_table": ("cap_table.py", "CapTable", [
        ("an insert without a MAC is accepted (grant without authorization)",
         "with m.Elif(self.ins & self.mac_ok & found):", "with m.Elif(self.ins & found):"),
        ("a capability is still good at its expiry tick",
         "with m.Elif(self.expiry[hit] <= self.now):", "with m.Elif(self.expiry[hit] < self.now):"),
        ("the epoch tag is not checked",
         "with m.Elif(self.etag[hit] != self.epoch_tag):", "with m.Elif(0):"),
        ("a lookup one byte over the budget is allowed (underflow)",
         "with m.Elif(self.budget[hit] < self.lk_bytes):", "with m.Elif(self.budget[hit] + 1 < self.lk_bytes):"),
        ("an allowed lookup does not spend the budget (unlimited reuse)",
         "m.d.sync += self.budget[hit].eq(self.budget[hit] - self.lk_bytes)", "m.d.sync += self.budget[hit].eq(self.budget[hit])"),
        ("clear_all leaves the ports open",
         "m.d.sync += self.valid[i].eq(0)", "m.d.sync += self.valid[i].eq(self.valid[i])"),
        ("a lookup asking for both directions matches a one-way capability",
         "match_dir = (self.dir[i] == self.lk_dir) | (self.dir[i] == 2)", "match_dir = (self.dir[i] == self.lk_dir) | (self.dir[i] == 2) | (self.lk_dir == 2)"),
        ("the peer is not compared",
         "(self.point[i] == self.lk_point) & (self.peer[i] == self.lk_peer) & match_dir", "(self.point[i] == self.lk_point) & match_dir"),
        ("an expired entry is not dropped",
         "m.d.sync += self.valid[hit].eq(0)", "m.d.sync += self.valid[hit].eq(self.valid[hit])"),
    ]),
    "mailbox": ("mailbox.py", "Mailbox", [
        ("type binding removed: a heartbeat's signature dispatches as CLEAR (the 22 October bug)",
         "with m.If(self.sig_ok & (self.signed_cmd == self.cmd)):", "with m.If(self.sig_ok):"),
        ("a wrong-command frame consumes the sequence number",
         "m.d.sync += self.status.eq(S_WRONG_CMD)",
         "m.d.sync += [self.status.eq(S_WRONG_CMD), self.last_seq[self.key_slot].eq(self.frame_seq)]"),
        ("the same sequence number is accepted twice (replay)",
         "m.d.comb += seq_ok.eq(self.frame_seq > self.last_seq[self.key_slot])",
         "m.d.comb += seq_ok.eq(self.frame_seq >= self.last_seq[self.key_slot])"),
        ("the epoch check is skipped",
         "with m.Elif(~(self.epoch_match | self.epoch_exempt)):", "with m.Elif(0):"),
        ("the epoch failure is reported before the sequence failure (order)",
         "with m.If(~seq_ok):", "with m.If(~seq_ok & (self.epoch_match | self.epoch_exempt)):"),
        ("a run-only command is accepted while halted",
         "with m.Elif(self.needs_run & ~self.running):", "with m.Elif(0):"),
        ("a sig_done strobe with no doorbell starts a dispatch (a second way in)",
         "with m.If(self.doorbell):", "with m.If(self.doorbell | self.sig_done):"),
        ("a forged signature reports ok",
         "m.d.sync += self.status.eq(S_BAD_SIG)", "m.d.sync += self.status.eq(S_OK)"),
        ("the accepted sequence is recorded in the wrong key slot",
         "self.last_seq[self.key_slot].eq(self.frame_seq), self.status.eq(S_OK)",
         "self.last_seq[0].eq(self.frame_seq), self.status.eq(S_OK)"),
        # adversarial audit 3: 64-bit sequence space, every key slot restarts at zero when the epoch advances
        ("the sequence registers shrink back to 32 bits (one frame at 2**32 - 1 ends a key; adversarial audit 3)",
         "def __init__(self, key_slots: int = 8, seq_bits: int = 64):", "def __init__(self, key_slots: int = 8, seq_bits: int = 32):"),
        ("an epoch advance does not restart the key slots (adversarial audit 3)",
         "                m.d.sync += seq.eq(0)", "                m.d.sync += seq.eq(seq)"),
        ("the key slots restart on a doorbell, not only on an epoch advance (a replay inside the epoch; adversarial audit 3)",
         "with m.If(self.epoch_advanced):", "with m.If(self.epoch_advanced | self.doorbell):"),
    ]),
}


def _run_second_solver(prove, only):
    if shutil.which("yices-smt2", path=os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", "")) is None:
        yield False, "MISSING  second solver: yices-smt2 not found (pip install -e '.[dev]' installs yices-solver)"
        return
    for block in BLOCKS_A:
        if only and block not in only:
            continue
        if block in NO_SECOND_SOLVER:
            # not a proof and not counted as one: said out loud on every run
            yield True, f"NOT RUN  {block} (second solver): {NO_SECOND_SOLVER[block]}"
            continue
        with tempfile.TemporaryDirectory() as work:
            ok, why = prove(os.path.join(GEN, block + ".v"), os.path.join(HERE, block + ".sv"), work, solver="yices",
                            depth=DEPTH_A.get(block, 25))
        yield ok, f"{'PROVED' if ok else 'FAILED'}  {block} (second solver): {why}"


def _run_random_sim(prove, only):
    from . import sim_a
    for block in BLOCKS_A:
        if only and block not in only:
            continue
        yield from sim_a.check(block, BLOCKS_A[block])


def _run_findings(prove, only):
    folder = os.path.join(HERE, "findings_a")
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not name.endswith(".sv"):
            continue
        block = open(os.path.join(folder, name), encoding="utf-8").readline().split("block:")[-1].split()[0].rstrip(".,;:")
        if only and block not in only:
            continue
        with tempfile.TemporaryDirectory() as work:
            props = os.path.join(work, block + ".sv")          # prove() names the top after the file
            shutil.copy(os.path.join(folder, name), props)
            ok, why = prove(os.path.join(GEN, block + ".v"), props, work)
        # only a concrete trace counts: a failed bounded check. An induction failure alone can be an unreachable state.
        reproduced = not ok and why.startswith("bounded check failed")
        yield reproduced, (f"reproduced  finding {name[:-3]}: {why}" if reproduced else
                           f"NOT REPRODUCED  finding {name[:-3]} ({why}): fixed? update FINDINGS-a.md and remove the file")


CHECKS_A = [_run_second_solver, _run_random_sim, _run_findings]
