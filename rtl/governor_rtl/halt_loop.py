# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Loop driver and sense. Invariant: the switch opens when the sequencer says so; a loss of
loop current for longer than the debounce drives ``loop_lost`` within one sense period.

``loop_sense`` is the comparator output (1 = current flowing). ``switch_open`` is the
sequencer's request; ``loop_out_open`` is the pad. Debounce rejects a single noisy sample.
"""
from amaranth import Elaboratable, Module, Signal


class LoopIO(Elaboratable):
    def __init__(self, debounce: int = 2):
        self.debounce = debounce
        self.loop_sense = Signal()
        self.switch_open = Signal()
        self.sample = Signal()            # one per sense period
        self.loop_out_open = Signal()
        self.loop_lost = Signal()
        self.count = Signal(range(debounce + 1))

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.loop_out_open.eq(self.switch_open)
        with m.If(self.sample):
            with m.If(~self.loop_sense):
                with m.If(self.count < self.debounce):
                    m.d.sync += self.count.eq(self.count + 1)
            with m.Else():
                m.d.sync += self.count.eq(0)
        m.d.comb += self.loop_lost.eq(self.count >= self.debounce)
        return m
