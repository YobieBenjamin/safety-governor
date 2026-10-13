"""Meter. Invariant: counters only increment, and the host port can read but not write.

Four counters per slot (tokens, cycles, bytes in, bytes out); a slot is one model digest.
"""
from amaranth import Array, Elaboratable, Module, Signal


class Meter(Elaboratable):
    def __init__(self, slots: int = 4, width: int = 48):
        self.slots = slots
        self.slot = Signal(range(max(2, slots)))
        self.add_tokens = Signal(width)
        self.add_cycles = Signal(width)
        self.add_in = Signal(width)
        self.add_out = Signal(width)
        self.strobe = Signal()
        self.host_wr = Signal()
        self.host_wr_refused = Signal()
        self.rd_slot = Signal(range(max(2, slots)))
        self.rd_tokens = Signal(width)
        self.rd_cycles = Signal(width)
        self.rd_in = Signal(width)
        self.rd_out = Signal(width)
        self.tokens = Array(Signal(width, name=f"tok{i}") for i in range(slots))
        self.cycles = Array(Signal(width, name=f"cyc{i}") for i in range(slots))
        self.bin = Array(Signal(width, name=f"bin{i}") for i in range(slots))
        self.bout = Array(Signal(width, name=f"bout{i}") for i in range(slots))

    def elaborate(self, platform):
        m = Module()
        with m.If(self.strobe):
            m.d.sync += [self.tokens[self.slot].eq(self.tokens[self.slot] + self.add_tokens),
                         self.cycles[self.slot].eq(self.cycles[self.slot] + self.add_cycles),
                         self.bin[self.slot].eq(self.bin[self.slot] + self.add_in),
                         self.bout[self.slot].eq(self.bout[self.slot] + self.add_out)]
        m.d.comb += [self.rd_tokens.eq(self.tokens[self.rd_slot]), self.rd_cycles.eq(self.cycles[self.rd_slot]),
                     self.rd_in.eq(self.bin[self.rd_slot]), self.rd_out.eq(self.bout[self.rd_slot]),
                     self.host_wr_refused.eq(self.host_wr)]
        return m
