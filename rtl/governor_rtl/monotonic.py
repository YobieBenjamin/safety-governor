# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Monotonic counter. Invariant: the value never decreases; a decrement request is refused.

The 64-bit value is the governor's notion of time and the policy anti-rollback reference.
``hwm`` is the fuse-backed high-water mark loaded at reset so a power loss cannot move the
counter backwards; the firmware writes the high-water mark to fuses periodically (outside this
block).

The increment saturates at the top value. Before 23 October 2026 it wrapped: a high-water mark of all ones
followed by one tick put the counter at zero, the one move this block exists to forbid (WAVE-FORMAL-PROOFS-ON-VERILOG found it:
rtl/formal/FINDINGS-a.md, RTL-COUNTER-WRAPPED-TO-ZERO). At 1 us a tick the top is 584,000 years away; the reachable path was the load.
"""
from amaranth import Elaboratable, Module, Signal


class MonotonicCounter(Elaboratable):
    def __init__(self, width: int = 64):
        self.width = width
        self.hwm = Signal(width)            # from fuses, sampled at reset release
        self.load_hwm = Signal()            # one-cycle strobe at boot
        self.inc = Signal()                 # increment strobe
        self.dec_req = Signal()             # an attempted decrement (there is no decrement path; this reports the attempt)
        self.value = Signal(width)
        self.refused = Signal()             # pulses when dec_req is seen

    def elaborate(self, platform):
        m = Module()
        with m.If(self.load_hwm):
            with m.If(self.hwm > self.value):
                m.d.sync += self.value.eq(self.hwm)
        with m.Elif(self.inc & ~self.value.all()):
            m.d.sync += self.value.eq(self.value + 1)
        m.d.comb += self.refused.eq(self.dec_req)
        return m
