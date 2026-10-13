"""Sticky alarm register. Invariant: bits are set by any source and cleared only through
``clear_mask`` while ``clear_authorized`` is asserted (an approver signature verified by the
crypto core, or a rule the firmware evaluated).
"""
from amaranth import Elaboratable, Module, Signal


class Alarms(Elaboratable):
    def __init__(self, width: int = 32):
        self.set_mask = Signal(width)
        self.clear_mask = Signal(width)
        self.clear_authorized = Signal()
        self.alarms = Signal(width)
        self.any = Signal()
        self.clear_refused = Signal()

    def elaborate(self, platform):
        m = Module()
        cleared = Signal(self.alarms.shape())
        m.d.comb += cleared.eq(self.alarms & ~(self.clear_mask & self.clear_authorized.replicate(len(self.alarms))))
        m.d.sync += self.alarms.eq(cleared | self.set_mask)
        m.d.comb += [self.any.eq(self.alarms != 0), self.clear_refused.eq((self.clear_mask != 0) & ~self.clear_authorized)]
        return m
