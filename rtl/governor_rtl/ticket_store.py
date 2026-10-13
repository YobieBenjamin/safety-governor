"""Used-ticket store. Invariant: a burned id is never admitted again; when the store is full,
``burn`` is refused and ``full`` is asserted so the endpoint refuses rather than admits.

In silicon this is a cuckoo table in NVM sized for a year of tickets and checkpointed; the
block here is a small CAM with the same interface and the same invariant.
"""
from amaranth import Array, Elaboratable, Module, Signal


class TicketStore(Elaboratable):
    def __init__(self, entries: int = 8, id_bits: int = 32):
        self.n = entries
        self.query = Signal()
        self.burn = Signal()
        self.id_in = Signal(id_bits)
        self.seen = Signal()            # valid in the cycle of query
        self.burned = Signal()          # pulses when burn succeeded
        self.full = Signal()
        self.valid = Array(Signal(name=f"v{i}") for i in range(entries))
        self.ids = Array(Signal(id_bits, name=f"id{i}") for i in range(entries))

    def elaborate(self, platform):
        m = Module()
        n = self.n
        match = Signal()
        for i in range(n):
            with m.If(self.valid[i] & (self.ids[i] == self.id_in)):
                m.d.comb += match.eq(1)
        m.d.comb += self.seen.eq(match)
        free = Signal(range(n + 1))
        m.d.comb += free.eq(n)
        for i in reversed(range(n)):
            with m.If(~self.valid[i]):
                m.d.comb += free.eq(i)
        m.d.comb += self.full.eq(free == n)
        with m.If(self.burn & ~match & (free != n)):
            m.d.sync += [self.valid[free].eq(1), self.ids[free].eq(self.id_in)]
            m.d.comb += self.burned.eq(1)
        return m
