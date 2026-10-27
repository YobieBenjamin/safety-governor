# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Lifecycle controller. Invariant: the state is monotone (TEST < PROVISIONED < PRODUCTION <
DECOMMISSIONED) and in PRODUCTION or later ``debug_grant`` is never asserted.

The state is mirrored from fuses at reset; ``advance`` burns the next fuse (modelled as the
register moving up) and never moves down.

Debug is also refused until ``load`` has mirrored the fuses since the last reset. Before 23 October 2026 the
register came out of reset as TEST and granted debug to anyone who asked in the cycles before the boot code
strobed ``load``, on a chip whose fuses said PRODUCTION (WAVE-FORMAL-PROOFS-ON-VERILOG found it: rtl/formal/FINDINGS-a.md, RTL-DEBUG-WINDOW-AFTER-RESET).
"""
from amaranth import Elaboratable, Module, Signal

TEST, PROVISIONED, PRODUCTION, DECOMMISSIONED = 0, 1, 2, 3


class Lifecycle(Elaboratable):
    def __init__(self):
        self.fuse_state = Signal(2)        # sampled at reset
        self.load = Signal()
        self.advance = Signal()            # strobe
        self.advance_to = Signal(2)
        self.debug_req = Signal()
        self.state = Signal(2)
        self.debug_grant = Signal()
        self.debug_refused = Signal()
        self.advance_refused = Signal()
        self.loaded = Signal()             # the fuses have been mirrored since the last reset

    def elaborate(self, platform):
        m = Module()
        with m.If(self.load):
            m.d.sync += self.loaded.eq(1)
            with m.If(self.fuse_state > self.state):
                m.d.sync += self.state.eq(self.fuse_state)
        with m.Elif(self.advance):
            with m.If(self.advance_to > self.state):
                m.d.sync += self.state.eq(self.advance_to)
        m.d.comb += [
            self.advance_refused.eq(self.advance & (self.advance_to <= self.state)),
            self.debug_grant.eq(self.debug_req & self.loaded & (self.state < PRODUCTION)),
            self.debug_refused.eq(self.debug_req & ~(self.loaded & (self.state < PRODUCTION))),
        ]
        return m
