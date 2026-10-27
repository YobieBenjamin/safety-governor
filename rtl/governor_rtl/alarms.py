# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Sticky alarm register. Invariant: bits are set by any source and cleared only through
``clear_mask`` while ``clear_authorized`` is asserted (an approver signature verified by the
crypto core, or a rule the firmware evaluated).

``hw_mask`` (a constructor parameter, 0 by default, so the stand-alone block is unchanged) names hardware-owned bits.
The core gives two of them to the halt sequencer (NO_FIRST_HEARTBEAT, EXCLUDED; docs/04 section 2): for those bits
only ``hw_set`` raises them and ``set_mask`` is ignored, so firmware can neither forge nor fake-raise them. They are
still cleared only through ``clear_mask`` with ``clear_authorized``, and a hardware raise beats a clear in the same
cycle, like any other bit (23 October 2026).
"""
from amaranth import Elaboratable, Module, Signal


class Alarms(Elaboratable):
    def __init__(self, width: int = 32, hw_mask: int = 0):
        self.hw_mask = hw_mask
        self.set_mask = Signal(width)
        if hw_mask:
            self.hw_set = Signal(width)     # raised by the hard core itself, never by firmware
        self.clear_mask = Signal(width)
        self.clear_authorized = Signal()
        self.alarms = Signal(width)
        self.any = Signal()
        self.clear_refused = Signal()

    def elaborate(self, platform):
        m = Module()
        cleared = Signal(self.alarms.shape())
        m.d.comb += cleared.eq(self.alarms & ~(self.clear_mask & self.clear_authorized.replicate(len(self.alarms))))
        if self.hw_mask:
            raise_ = (self.set_mask & ~self.hw_mask) | (self.hw_set & self.hw_mask)
        else:
            raise_ = self.set_mask
        m.d.sync += self.alarms.eq(cleared | raise_)
        m.d.comb += [self.any.eq(self.alarms != 0), self.clear_refused.eq((self.clear_mask != 0) & ~self.clear_authorized)]
        return m
