"""Safe-mode sequencer and the levers. Invariants: the levers assert on any cause and never
release without an authorized ``clear``; causes that open the loop open it; rungs escalate on
the policy timers and never descend on their own; the loop switch is open at reset, closes only
when armed (no cause, a valid heartbeat), and once opened by a cause never closes without clear.

States: 0 HALTED_INITIAL, 1 RUN, 2 THROTTLE, 3 HALT, 4 SAFE. Levers per rung: HALTED_INITIAL
brake, reset and power off; RUN released; THROTTLE brake; HALT brake and reset; SAFE brake, reset
and power off. PWRBRK# and PERST# are active low open-drain in the pinout; here they are modelled
active high (``pwrbrk``, ``perst``) and inverted at the pad. ``tick`` is one millisecond.
"""
from amaranth import Elaboratable, Module, Signal

HALTED_INITIAL, RUN, THROTTLE, HALT, SAFE = 0, 1, 2, 3, 4
C_NONE, C_LOOP, C_LOCAL, C_TAMPER, C_COMMAND = 0, 1, 2, 3, 4


class HaltSeq(Elaboratable):
    def __init__(self, t_throttle: int = 30_000, t_halt: int = 300_000, timer_bits: int = 20):
        self.t_throttle, self.t_halt = t_throttle, t_halt
        # causes (level or strobe)
        self.loop_lost = Signal()           # from LoopIO: no current sensed
        self.hb_expired = Signal()          # from Heartbeat
        self.tamper = Signal()
        self.cmd_halt = Signal()            # authorized command strobes (after sig check)
        self.cmd_throttle = Signal()
        self.local_trip = Signal()          # e.g. output budget: local safe mode, loop stays closed
        self.clear = Signal()               # authorized clear strobe (after sig, log and neighbor checks)
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

    def elaborate(self, platform):
        m = Module()
        in_run = (self.state == RUN) | (self.state == THROTTLE)

        with m.If(self.clear & (self.state != HALTED_INITIAL)):
            # clear: back to the boot state; the switch closes again only when armed
            m.d.sync += [self.state.eq(HALTED_INITIAL), self.cause.eq(C_NONE), self.timer.eq(0)]
        with m.Elif(self.tamper):
            m.d.sync += [self.state.eq(SAFE), self.cause.eq(C_TAMPER), self.switch_open.eq(1)]
        with m.Elif(self.loop_lost & in_run):
            m.d.sync += [self.state.eq(HALT), self.cause.eq(C_LOOP), self.switch_open.eq(1), self.timer.eq(0)]
        with m.Elif(self.cmd_halt & (self.state != SAFE)):
            m.d.sync += [self.state.eq(HALT), self.cause.eq(C_COMMAND), self.switch_open.eq(1), self.timer.eq(0)]
        with m.Elif((self.hb_expired | self.local_trip | self.cmd_throttle) & (self.state == RUN)):
            m.d.sync += [self.state.eq(THROTTLE), self.cause.eq(C_LOCAL), self.timer.eq(0)]
        with m.Elif((self.state == HALTED_INITIAL) & (self.cause == C_NONE) & self.hb_ok):
            m.d.sync += self.switch_open.eq(0)                      # armed
            with m.If(self.loop_sense):
                m.d.sync += self.state.eq(RUN)
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

        # levers follow the state combinationally: no register the host could flip
        m.d.comb += [
            self.pwrbrk.eq(self.state != RUN),
            self.perst.eq((self.state == HALTED_INITIAL) | (self.state == HALT) | (self.state == SAFE)),
            self.pwr_en.eq((self.state != HALTED_INITIAL) & (self.state != SAFE)),
            self.ports_closed.eq(self.state != RUN),
        ]
        return m
