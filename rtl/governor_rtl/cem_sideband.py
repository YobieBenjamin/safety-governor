"""PCIe CEM sideband shaper: sits between the halt sequencer's levers and one slot's pads, and
adds the CEM reset timing the sequencer does not enforce on its own.

Found by ``govsim/hardware_ref/cem.py`` (docs/interfaces/02-pcie-cem-sideband.md): ``HaltSeq``
releases PERST# on the same clock edge that it raises PWR_EN, and a HALT followed at once by an
authorized CLEAR and a live loop can release PERST# a few cycles after asserting it. The CEM
timing table (members-only; quoted publicly on LKML and in the Linux kernel, see
docs/interfaces/sources.csv LKMLCEM and LINUXPCI) wants PERST# held for T_PVPERL = 100 ms
after power is valid and asserted for at least T_PERST = 100 us.

Invariants (each checked on simulation traces by ``govsim.hardware_ref.cem.check_trace``):
- PERST# is asserted whenever the sequencer asks, whenever PWR_EN is low, and whenever the slot's
  power-good is low, combinationally: no added latency on the way down (T_FAIL).
- PERST# is released only after power-good has been continuously high for ``t_pvperl_us``.
- Once asserted, PERST# stays asserted for at least ``t_perst_us``.
- The power brake and PWR_EN pass straight through: this block never delays a brake.

``tick_us`` is the monotonic counter's 1 us strobe. All outputs are active high here and inverted
at the pad like the sequencer's.

This block is additive and is not yet wired into ``GovernorCore``; see the doc for why.
"""
from amaranth import Elaboratable, Module, Signal


class CemSideband(Elaboratable):
    def __init__(self, t_pvperl_us: int = 100_000, t_perst_us: int = 100):
        self.t_pvperl_us, self.t_perst_us = t_pvperl_us, t_perst_us
        # from the halt sequencer (active high)
        self.perst_req = Signal()
        self.pwr_en_req = Signal()
        self.pwrbrk_req = Signal()
        # from the slot
        self.pwr_good = Signal()
        self.tick_us = Signal()
        # to the pads (active high)
        self.perst = Signal()
        self.pwr_en = Signal()
        self.pwrbrk = Signal()
        # state
        self.pg_timer = Signal(range(t_pvperl_us + 1))
        self.hold_timer = Signal(range(t_perst_us + 1))
        self.perst_q = Signal(init=1)

    def elaborate(self, platform):
        m = Module()
        power_ok = self.pwr_en_req & self.pwr_good
        pg_settled = self.pg_timer >= self.t_pvperl_us
        base = self.perst_req | ~power_ok | ~pg_settled
        held = self.perst_q & (self.hold_timer < self.t_perst_us)
        m.d.comb += [
            self.perst.eq(base | held),
            self.pwr_en.eq(self.pwr_en_req),
            self.pwrbrk.eq(self.pwrbrk_req),
        ]
        m.d.sync += self.perst_q.eq(self.perst)
        with m.If(~power_ok):
            m.d.sync += self.pg_timer.eq(0)
        with m.Elif(self.tick_us & ~pg_settled):
            m.d.sync += self.pg_timer.eq(self.pg_timer + 1)
        with m.If(~self.perst):
            m.d.sync += self.hold_timer.eq(0)
        with m.Elif(~self.perst_q):
            m.d.sync += self.hold_timer.eq(0)                 # first cycle of a new assertion
        with m.Elif(self.tick_us & (self.hold_timer < self.t_perst_us)):
            m.d.sync += self.hold_timer.eq(self.hold_timer + 1)
        return m
