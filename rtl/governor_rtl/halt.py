# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Safe-mode sequencer and the levers. Invariants: the levers assert on any cause and never
release without an authorized ``clear``; tamper outranks clear; causes that open the loop open it; rungs escalate on
the policy timers and never descend on their own; the loop switch is open at reset, closes only
when armed (no cause, a valid heartbeat) or excluded, and once opened by a cause never closes without clear.

Two design calls by Yobie, 23 October 2026 ("silently failing is a bullshit feature"):

1. A HALT opens the loop on every rung, SAFE included. A chip that reached SAFE on a local cause (a lost
   heartbeat) keeps its loop switch closed; a signed HALT to it now opens the switch and records the command as the
   cause (CAUSE reads 4), so the neighbours stop too. The state stays SAFE, which outranks HALT. Tamper keeps its
   cause. Before this the sequencer ignored ``cmd_halt`` in SAFE (FINDINGS-b.md).
2. A chip that never gets its first heartbeat still holds the rack (fail closed), but loudly. ``boot_timer`` counts
   milliseconds in HALTED_INITIAL with no cause while the chip has never been armed since reset (``hb_seen`` low);
   past ``t_boot`` the level ``no_first_hb`` rises (the core makes it the sticky ALARMS bit NO_FIRST_HEARTBEAT and
   CAUSE bit 3). It can never rise once the chip has been armed. The deliberate way out is ``cmd_exclude``, the
   strobe of a signed, authorized EXCLUDE: in HALTED_INITIAL with no cause and no live heartbeat (and nowhere else)
   the chip closes its own loop switch so the rest of the rack can run, and sets ``excluded``. Its own levers stay
   asserted because the state stays HALTED_INITIAL (brake, reset, power off). It leaves exclusion when a valid
   heartbeat arms it normally, or on reset; a tamper or a HALT moves it to SAFE or HALT with the loop open, which also
   ends the exclusion (the safe direction).

States: 0 HALTED_INITIAL, 1 RUN, 2 THROTTLE, 3 HALT, 4 SAFE. Levers per rung: HALTED_INITIAL
brake, reset and power off; RUN released; THROTTLE brake; HALT brake and reset; SAFE brake, reset
and power off. PWRBRK# and PERST# are active low open-drain in the pinout; here they are modelled
active high (``pwrbrk``, ``perst``) and inverted at the pad. ``tick`` is one millisecond.
"""
from amaranth import Elaboratable, Module, Signal

HALTED_INITIAL, RUN, THROTTLE, HALT, SAFE = 0, 1, 2, 3, 4
C_NONE, C_LOOP, C_LOCAL, C_TAMPER, C_COMMAND = 0, 1, 2, 3, 4


class HaltSeq(Elaboratable):
    def __init__(self, t_throttle: int = 30_000, t_halt: int = 300_000, timer_bits: int = 20, t_boot: int = 5_000,
                 boot_bits: int = 16):
        assert 1 <= t_boot < (1 << boot_bits)
        self.t_throttle, self.t_halt, self.t_boot = t_throttle, t_halt, t_boot
        # causes (level or strobe)
        self.loop_lost = Signal()           # from LoopIO: no current sensed
        self.hb_expired = Signal()          # from Heartbeat
        self.tamper = Signal()
        self.cmd_halt = Signal()            # authorized command strobes (after sig check)
        self.cmd_throttle = Signal()
        self.local_trip = Signal()          # e.g. output budget: local safe mode, loop stays closed
        self.clear = Signal()               # authorized clear strobe (after sig, log and neighbor checks)
        self.cmd_exclude = Signal()         # authorized EXCLUDE strobe (after sig check; same authority as CLEAR)
        self.hb_ok = Signal()               # a valid heartbeat is live: may arm
        self.loop_sense = Signal()          # loop current present: may go to RUN once armed
        self.tick = Signal()                # one per millisecond
        # outputs
        self.state = Signal(3)
        self.pwrbrk = Signal()
        self.perst = Signal()
        self.pwr_en = Signal()
        self.switch_open = Signal(init=1)   # our loop switch: open until armed
        self.ports_closed = Signal()
        self.cause = Signal(3)              # 0 none, 1 loop, 2 local (heartbeat, trip, throttle), 3 tamper, 4 command
        self.timer = Signal(timer_bits)
        self.hb_seen = Signal()             # armed at least once since reset
        self.boot_timer = Signal(boot_bits) # ms waited for the first heartbeat (saturating; frozen once armed)
        self.no_first_hb = Signal()         # the boot window passed and the chip has never been armed
        self.excluded = Signal()            # an authorized EXCLUDE closed this chip's switch; its own levers stay on

    def elaborate(self, platform):
        m = Module()
        in_run = (self.state == RUN) | (self.state == THROTTLE)

        # tamper outranks everything, CLEAR included: a tamper strobe in the same cycle as an authorized CLEAR still
        # lands in SAFE (conformance finding F-05, 23 October 2026; before this the CLEAR won and the strobe was lost)
        with m.If(self.tamper):
            m.d.sync += [self.state.eq(SAFE), self.cause.eq(C_TAMPER), self.switch_open.eq(1)]
        with m.Elif(self.clear & (self.state != HALTED_INITIAL)):
            # clear: back to the boot state; the switch closes again only when armed (or excluded)
            m.d.sync += [self.state.eq(HALTED_INITIAL), self.cause.eq(C_NONE), self.timer.eq(0)]
        with m.Elif(self.loop_lost & in_run):
            m.d.sync += [self.state.eq(HALT), self.cause.eq(C_LOOP), self.switch_open.eq(1), self.timer.eq(0)]
        with m.Elif(self.cmd_halt & (self.state == SAFE)):
            # a HALT to a chip already in SAFE: SAFE outranks HALT, so the state stays; the loop opens and the command
            # is the cause on record, unless the cause is tamper 
            with m.If(self.cause != C_TAMPER):
                m.d.sync += self.cause.eq(C_COMMAND)
            m.d.sync += self.switch_open.eq(1)
        with m.Elif(self.cmd_halt):
            m.d.sync += [self.state.eq(HALT), self.cause.eq(C_COMMAND), self.switch_open.eq(1), self.timer.eq(0)]
        with m.Elif((self.hb_expired | self.local_trip | self.cmd_throttle) & (self.state == RUN)):
            m.d.sync += [self.state.eq(THROTTLE), self.cause.eq(C_LOCAL), self.timer.eq(0)]
        with m.Elif((self.state == HALTED_INITIAL) & (self.cause == C_NONE) & self.hb_ok):
            m.d.sync += [self.switch_open.eq(0), self.hb_seen.eq(1), self.excluded.eq(0)]   # armed (ends an exclusion)
            # RUN needs a clean loop sample: current present AND the debounce no longer saying lost. Without the
            # second term an armed core entered RUN with a stale loop_lost and halted itself a cycle later (FPGA
            # finding F1, 23 October 2026)
            with m.If(self.loop_sense & ~self.loop_lost):
                m.d.sync += self.state.eq(RUN)
        with m.Elif(self.cmd_exclude & (self.state == HALTED_INITIAL) & (self.cause == C_NONE)):
            # EXCLUDE: no cause and no live heartbeat (a live one armed the chip in the branch above).
            # Close our switch so the rest of the rack can run; the state, and so the levers, stay HALTED_INITIAL
            m.d.sync += [self.switch_open.eq(0), self.excluded.eq(1)]
        with m.Elif(self.tick & (self.state == THROTTLE)):
            with m.If(self.timer + 1 >= self.t_throttle):
                m.d.sync += [self.state.eq(HALT), self.timer.eq(0)]
            with m.Else():
                m.d.sync += self.timer.eq(self.timer + 1)
        with m.Elif(self.tick & (self.state == HALT)):
            with m.If(self.timer + 1 >= self.t_halt):
                m.d.sync += [self.state.eq(SAFE), self.timer.eq(0)]
            with m.Else():
                m.d.sync += self.timer.eq(self.timer + 1)

        # exclusion lasts only while the chip sits in HALTED_INITIAL with no cause; a tamper or a HALT ends it
        with m.If(self.tamper | self.cmd_halt):
            m.d.sync += self.excluded.eq(0)
        # the boot window: milliseconds spent waiting for the first heartbeat, counted only before the first arming
        waiting = ~self.hb_seen & (self.state == HALTED_INITIAL) & (self.cause == C_NONE) & ~self.hb_ok
        with m.If(waiting & self.tick & (self.boot_timer != (1 << len(self.boot_timer)) - 1)):
            m.d.sync += self.boot_timer.eq(self.boot_timer + 1)
        m.d.comb += self.no_first_hb.eq(~self.hb_seen & (self.boot_timer >= self.t_boot))

        # levers follow the state combinationally: no register the host could flip
        m.d.comb += [
            self.pwrbrk.eq(self.state != RUN),
            self.perst.eq((self.state == HALTED_INITIAL) | (self.state == HALT) | (self.state == SAFE)),
            self.pwr_en.eq((self.state != HALTED_INITIAL) & (self.state != SAFE)),
            self.ports_closed.eq(self.state != RUN),
        ]
        return m
