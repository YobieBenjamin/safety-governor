# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""governor_core behind the SMBus target: the host's management-bus view of the chip.

The SMBus target reads the core's CSR window through ``csr_addr``/``csr_rdata`` (a read mux, no
state) and rings ``doorbell``. Nothing else of the target reaches the core. The 1 us ``tick``
comes from dividing the system clock by ``tick_div`` (50 at 50 MHz), and the loop sense strobe
from dividing the tick by ``sample_div`` (100 us, the sense period in docs/04 section 9).

The firmware-side ports of the core (heartbeat verdicts, clears, capability inserts and the
rest) are left to whoever instantiates this: the Ibex firmware on the chip, the bench harness
in ``hw/fpga/top.py`` on the FPGA.
"""
from amaranth import Elaboratable, Module, Signal

from .smbus import DEFAULT_ADDRESS, SMBusTarget
from .top import GovernorCore


class GovernorSMBus(Elaboratable):
    def __init__(self, tick_div: int = 50, sample_div: int = 100, address: int = DEFAULT_ADDRESS,
                 timeout_ticks: int = 25_000, target_cls=SMBusTarget, **core_kwargs):
        self.tick_div, self.sample_div = tick_div, sample_div
        self.core = GovernorCore(**core_kwargs)
        self.smb = target_cls(address=address, timeout_ticks=timeout_ticks)
        self.scl_i = Signal(init=1)
        self.sda_i = Signal(init=1)
        self.scl_oe = Signal()
        self.sda_oe = Signal()
        self.pwrbrk_n = Signal()
        self.perst_n = Signal()
        self.pwr_en = Signal()
        self.loop_out_open = Signal()
        self.loop_sense = Signal()
        self.tick = Signal()
        self.sample = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules.core = core = self.core
        m.submodules.smb = smb = self.smb
        if self.tick_div == 1:
            m.d.comb += self.tick.eq(1)
        else:
            div = Signal(range(self.tick_div))
            with m.If(div == self.tick_div - 1):
                m.d.sync += div.eq(0)
            with m.Else():
                m.d.sync += div.eq(div + 1)
            m.d.comb += self.tick.eq(div == self.tick_div - 1)
        sdiv = Signal(range(self.sample_div))
        with m.If(self.tick):
            with m.If(sdiv == self.sample_div - 1):
                m.d.sync += sdiv.eq(0)
            with m.Else():
                m.d.sync += sdiv.eq(sdiv + 1)
        m.d.comb += [
            self.sample.eq(self.tick & (sdiv == self.sample_div - 1)),
            core.tick.eq(self.tick),
            core.sample.eq(self.sample),
            smb.tick.eq(self.tick),
            smb.scl_i.eq(self.scl_i),
            smb.sda_i.eq(self.sda_i),
            self.scl_oe.eq(smb.scl_oe),
            self.sda_oe.eq(smb.sda_oe),
            core.csr_addr.eq(smb.csr_addr),
            smb.csr_rdata.eq(core.csr_rdata),
            core.doorbell.eq(smb.doorbell),
            core.loop_sense.eq(self.loop_sense),
            self.pwrbrk_n.eq(core.pwrbrk_n),
            self.perst_n.eq(core.perst_n),
            self.pwr_en.eq(core.pwr_en),
            self.loop_out_open.eq(core.loop_out_open),
        ]
        return m
