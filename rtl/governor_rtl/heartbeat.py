"""Heartbeat timer. Invariant: ``expired`` asserts within one tick of the window running out
and the timer reloads only on ``hb_valid`` (the crypto core's verdict on the authority's
token), never on anything the host writes. ``tick`` is one millisecond; ``window`` is in ms.
"""
from amaranth import Elaboratable, Module, Signal


class Heartbeat(Elaboratable):
    def __init__(self, width: int = 32):
        self.hb_valid = Signal()         # strobe from the verifier
        self.window = Signal(width)      # ticks of validity carried by the token
        self.tick = Signal()             # one per time unit
        self.remaining = Signal(width)
        self.expired = Signal()

    def elaborate(self, platform):
        m = Module()
        with m.If(self.hb_valid):
            m.d.sync += self.remaining.eq(self.window)
        with m.Elif(self.tick & (self.remaining != 0)):
            m.d.sync += self.remaining.eq(self.remaining - 1)
        m.d.comb += self.expired.eq(self.remaining == 0)
        return m
