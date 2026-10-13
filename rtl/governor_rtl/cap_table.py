"""Capability table and checker. One instance per enforcement point.

Invariant: a lookup allows only an entry with a matching (point, peer, dir), budget >= bytes,
not expired, matching epoch tag; the budget never underflows; an insert is accepted only with
``mac_ok`` from the HMAC engine. At the rack tier this table is the source of truth for the
switch ports the governor has opened; at the integrated tier it sits in the descriptor path.

Sizes are parameters; the simulation uses small ones. Lookup is one cycle: every entry is
compared in parallel (a CAM), the match is priority-encoded, the budget is decremented in
the same cycle.
"""
from amaranth import Array, Elaboratable, Module, Signal

R_OK, R_NO_CAP, R_EXPIRED, R_STALE_EPOCH, R_BUDGET = 0, 1, 2, 3, 4


class CapTable(Elaboratable):
    def __init__(self, entries: int = 8, peer_bits: int = 16, budget_bits: int = 24, time_bits: int = 32):
        self.n = entries
        # insert port
        self.ins = Signal()
        self.ins_point = Signal(3)
        self.ins_peer = Signal(peer_bits)
        self.ins_dir = Signal(2)
        self.ins_budget = Signal(budget_bits)
        self.ins_expiry = Signal(time_bits)
        self.ins_epoch_tag = Signal(16)
        self.mac_ok = Signal()
        self.ins_ok = Signal()
        self.ins_full = Signal()
        self.clear_all = Signal()
        # lookup port
        self.lk = Signal()
        self.lk_point = Signal(3)
        self.lk_peer = Signal(peer_bits)
        self.lk_dir = Signal(2)
        self.lk_bytes = Signal(budget_bits)
        self.now = Signal(time_bits)
        self.epoch_tag = Signal(16)
        self.allow = Signal()
        self.reason = Signal(3)
        # storage
        self.valid = Array(Signal(name=f"valid{i}") for i in range(entries))
        self.point = Array(Signal(3, name=f"point{i}") for i in range(entries))
        self.peer = Array(Signal(peer_bits, name=f"peer{i}") for i in range(entries))
        self.dir = Array(Signal(2, name=f"dir{i}") for i in range(entries))
        self.budget = Array(Signal(budget_bits, name=f"budget{i}") for i in range(entries))
        self.expiry = Array(Signal(time_bits, name=f"expiry{i}") for i in range(entries))
        self.etag = Array(Signal(16, name=f"etag{i}") for i in range(entries))

    def elaborate(self, platform):
        m = Module()
        n = self.n
        # ---- insert: first free slot, only with a valid MAC
        free = Signal(range(n + 1))
        found = Signal()
        m.d.comb += free.eq(n)
        for i in reversed(range(n)):
            with m.If(~self.valid[i]):
                m.d.comb += free.eq(i)
        m.d.comb += found.eq(free != n)
        m.d.comb += self.ins_full.eq(self.ins & ~found)
        with m.If(self.clear_all):
            for i in range(n):
                m.d.sync += self.valid[i].eq(0)
        with m.Elif(self.ins & self.mac_ok & found):
            m.d.comb += self.ins_ok.eq(1)
            m.d.sync += [self.valid[free].eq(1), self.point[free].eq(self.ins_point), self.peer[free].eq(self.ins_peer),
                         self.dir[free].eq(self.ins_dir), self.budget[free].eq(self.ins_budget),
                         self.expiry[free].eq(self.ins_expiry), self.etag[free].eq(self.ins_epoch_tag)]
        # ---- lookup: parallel compare, priority encode
        hit = Signal(range(n + 1))
        m.d.comb += hit.eq(n)
        for i in reversed(range(n)):
            match_dir = (self.dir[i] == self.lk_dir) | (self.dir[i] == 2)   # 2 = both
            with m.If(self.valid[i] & (self.point[i] == self.lk_point) & (self.peer[i] == self.lk_peer) & match_dir):
                m.d.comb += hit.eq(i)
        with m.If(self.lk):
            with m.If(hit == n):
                m.d.comb += [self.allow.eq(0), self.reason.eq(R_NO_CAP)]
            with m.Elif(self.expiry[hit] <= self.now):
                m.d.comb += [self.allow.eq(0), self.reason.eq(R_EXPIRED)]
                m.d.sync += self.valid[hit].eq(0)
            with m.Elif(self.etag[hit] != self.epoch_tag):
                m.d.comb += [self.allow.eq(0), self.reason.eq(R_STALE_EPOCH)]
            with m.Elif(self.budget[hit] < self.lk_bytes):
                m.d.comb += [self.allow.eq(0), self.reason.eq(R_BUDGET)]
            with m.Else():
                m.d.comb += [self.allow.eq(1), self.reason.eq(R_OK)]
                m.d.sync += self.budget[hit].eq(self.budget[hit] - self.lk_bytes)
        return m
