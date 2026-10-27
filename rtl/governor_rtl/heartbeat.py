# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Heartbeat timer. Invariant: ``expired`` asserts within one tick of the window running out
and the timer reloads only on ``hb_valid`` (the crypto core's verdict on the authority's
token), never on anything the host writes. ``tick`` is one millisecond; ``window`` is in ms.

The window is clamped in hardware (adversarial audit 3). docs/04 section 9 sets the policy's heartbeat expiry
at 5 s and says the governor clamps any signed window to it; the model does (govsim/governor.py ``_heartbeat``:
``min(window_end, now + heartbeat_expiry_s)``). Before this fix the hard core loaded whatever 32-bit window the
firmware handed it, so one firmware fault or one mis-signed window kept the core alive for about 49 days with no
further heartbeat. Now a valid heartbeat loads ``min(window, max_window)``: ``max_window`` defaults to 5000 ms and
is never above what the register can hold (``2**width - 1``), so the narrow test builds still elaborate.
"""
from amaranth import Elaboratable, Module, Mux, Signal

MAX_WINDOW_MS = 5_000    # docs/04 section 9: the policy's heartbeat expiry, 5 s of 1 ms ticks


class Heartbeat(Elaboratable):
    def __init__(self, width: int = 32, max_window: int = MAX_WINDOW_MS):
        assert max_window >= 1
        # the longest time one valid heartbeat can keep the chip armed, in ticks (adversarial audit 3)
        self.max_window = min(max_window, (1 << width) - 1)
        self.hb_valid = Signal()         # strobe from the verifier
        self.window = Signal(width)      # ticks of validity carried by the token
        self.tick = Signal()             # one per time unit
        self.remaining = Signal(width)
        self.expired = Signal()

    def elaborate(self, platform):
        m = Module()
        # the window actually loaded: what the token says, but never more than the policy maximum (adversarial audit 3)
        clamped = Signal(len(self.window))
        m.d.comb += clamped.eq(Mux(self.window > self.max_window, self.max_window, self.window))
        with m.If(self.hb_valid):
            m.d.sync += self.remaining.eq(clamped)
        with m.Elif(self.tick & (self.remaining != 0)):
            m.d.sync += self.remaining.eq(self.remaining - 1)
        m.d.comb += self.expired.eq(self.remaining == 0)
        return m
