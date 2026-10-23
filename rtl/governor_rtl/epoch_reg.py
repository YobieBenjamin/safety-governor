# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Epoch register. Invariant: the register changes only on ``commit`` with ``quorum_ok``
asserted by the policy verifier; the host write port exists on the bus and has no effect.
"""
from amaranth import Elaboratable, Module, Signal


class EpochReg(Elaboratable):
    def __init__(self, width: int = 256):
        self.width = width
        self.commit = Signal()          # from the policy FSM after k-of-n verification
        self.quorum_ok = Signal()       # from the signature verifier
        self.new_epoch = Signal(width)
        self.host_wr = Signal()         # the host's attempt; wired to nothing on purpose
        self.host_data = Signal(width)
        self.epoch = Signal(width)
        self.epoch_tag = Signal(16)
        self.host_refused = Signal()

    def elaborate(self, platform):
        m = Module()
        with m.If(self.commit & self.quorum_ok):
            m.d.sync += self.epoch.eq(self.new_epoch)
        m.d.comb += [self.epoch_tag.eq(self.epoch[:16]), self.host_refused.eq(self.host_wr)]
        return m
