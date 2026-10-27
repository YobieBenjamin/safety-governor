# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Measurement register. Invariant: the register changes only through ``extend``; there is no
write port. ``extend`` asks the SHA-256 engine for H(value || data) and latches the result.

The hash engine is external (OpenTitan HMAC/SHA-256 class). This block owns the request
and the latch, so the only data path into ``value`` is the engine's output after a request
this block made.
"""
from amaranth import Elaboratable, Module, Signal, Cat


class MeasureReg(Elaboratable):
    def __init__(self, width: int = 256):
        self.width = width
        self.extend = Signal()                 # strobe
        self.data = Signal(width)              # the digest to fold in
        self.hash_req = Signal()               # to the engine: hash (value || data)
        self.hash_in = Signal(2 * width)       # the block of bytes the engine hashes
        self.hash_done = Signal()              # from the engine
        self.hash_out = Signal(width)
        self.value = Signal(width)
        self.busy = Signal()

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.hash_in.eq(Cat(self.data, self.value))
        with m.FSM() as fsm:
            with m.State("IDLE"):
                with m.If(self.extend):
                    m.d.comb += self.hash_req.eq(1)
                    m.next = "WAIT"
            with m.State("WAIT"):
                m.d.comb += self.busy.eq(1)
                with m.If(self.hash_done):
                    m.d.sync += self.value.eq(self.hash_out)
                    m.next = "IDLE"
        return m
