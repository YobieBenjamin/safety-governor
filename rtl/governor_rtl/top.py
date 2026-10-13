"""governor_core: the hard-core blocks wired together with the read-only CSR window from
``docs/04-specification.md`` §2. The firmware side (Ibex, the crypto engines, the fabric MAC)
attaches to the strobes exposed as ports.

The CSR bus is read-only by construction: ``csr_rdata`` is a mux over the blocks' outputs
and there is no ``csr_wdata`` port. The only host-writable location is the mailbox doorbell.
"""
from amaranth import Cat, Elaboratable, Module, Signal

from .alarms import Alarms
from .cap_table import CapTable
from .epoch_reg import EpochReg
from .halt import HaltSeq
from .halt_loop import LoopIO
from .heartbeat import Heartbeat
from .lifecycle import Lifecycle
from .mailbox import Mailbox
from .measure_reg import MeasureReg
from .meter import Meter
from .monotonic import MonotonicCounter
from .ticket_store import TicketStore

POINTS = ("nvswitch", "pcie", "dpu", "storage")


class GovernorCore(Elaboratable):
    def __init__(self, cap_entries: int = 8, ticket_entries: int = 8):
        self.mono = MonotonicCounter()
        self.meas0 = MeasureReg()
        self.meas1 = MeasureReg()
        self.epoch = EpochReg()
        self.life = Lifecycle()
        self.caps = {p: CapTable(entries=cap_entries) for p in POINTS}
        self.tickets = TicketStore(entries=ticket_entries)
        self.hb = Heartbeat()
        self.halt = HaltSeq()
        self.loop = LoopIO()
        self.meter = Meter()
        self.mbox = Mailbox()
        self.alarms = Alarms()
        # CSR window
        self.csr_addr = Signal(12)
        self.csr_rdata = Signal(32)
        self.doorbell = Signal()
        # pads
        self.pwrbrk_n = Signal()
        self.perst_n = Signal()
        self.pwr_en = Signal()
        self.loop_out_open = Signal()
        self.loop_sense = Signal()
        self.tick = Signal()
        self.sample = Signal()
        # give the submodules' ports unique, readable names at the top level
        for prefix, blk in (("meas0", self.meas0), ("meas1", self.meas1), ("epoch", self.epoch), ("life", self.life),
                            ("tickets", self.tickets), ("hb", self.hb), ("halt", self.halt), ("meter", self.meter),
                            ("mbox", self.mbox), ("alarms", self.alarms), ("mono", self.mono)):
            for attr, sig in vars(blk).items():
                if isinstance(sig, Signal):
                    sig.name = f"{prefix}_{attr}"
        for p, c in self.caps.items():
            for attr, sig in vars(c).items():
                if isinstance(sig, Signal):
                    sig.name = f"cap_{p}_{attr}"

    def elaborate(self, platform):
        m = Module()
        m.submodules.mono = self.mono
        m.submodules.meas0 = self.meas0
        m.submodules.meas1 = self.meas1
        m.submodules.epoch = self.epoch
        m.submodules.life = self.life
        for p, c in self.caps.items():
            m.submodules["cap_" + p] = c
        m.submodules.tickets = self.tickets
        m.submodules.hb = self.hb
        m.submodules.halt = self.halt
        m.submodules.loop = self.loop
        m.submodules.meter = self.meter
        m.submodules.mbox = self.mbox
        m.submodules.alarms = self.alarms

        # ---- wiring between blocks
        m.d.comb += [
            self.mono.inc.eq(self.tick),
            self.hb.tick.eq(self.tick),
            self.halt.tick.eq(self.tick),
            self.loop.sample.eq(self.sample),
            self.loop.loop_sense.eq(self.loop_sense),
            self.loop.switch_open.eq(self.halt.switch_open),
            self.loop_out_open.eq(self.loop.loop_out_open),
            self.halt.loop_lost.eq(self.loop.loop_lost),
            self.halt.hb_expired.eq(self.hb.expired),
            self.halt.armed_ok.eq(~self.hb.expired & self.loop.loop_sense),
            self.mbox.running.eq(self.halt.state == 1),
            self.mbox.doorbell.eq(self.doorbell),
            self.pwrbrk_n.eq(~self.halt.pwrbrk),
            self.perst_n.eq(~self.halt.perst),
            self.pwr_en.eq(self.halt.pwr_en),
        ]
        for c in self.caps.values():
            m.d.comb += [c.now.eq(self.mono.value[:32]), c.epoch_tag.eq(self.epoch.epoch_tag), c.clear_all.eq(self.halt.ports_closed)]

        # ---- CSR read mux (word addresses from the register map)
        a = self.csr_addr
        with m.Switch(a):
            with m.Case(0x000):
                m.d.comb += self.csr_rdata.eq(0x5347_0001)             # 'SG', revision 1
            with m.Case(0x004):
                m.d.comb += self.csr_rdata.eq(self.life.state)
            with m.Case(0x008):
                m.d.comb += self.csr_rdata.eq(self.halt.state)
            with m.Case(0x00C):
                m.d.comb += self.csr_rdata.eq(self.halt.cause)
            with m.Case(0x070):
                m.d.comb += self.csr_rdata.eq(self.mono.value[:32])
            with m.Case(0x074):
                m.d.comb += self.csr_rdata.eq(self.mono.value[32:])
            with m.Case(0x078):
                m.d.comb += self.csr_rdata.eq(self.hb.remaining)
            with m.Case(0x07C):
                m.d.comb += self.csr_rdata.eq(Cat(self.loop.loop_sense, self.halt.switch_open))
            with m.Case(0x080):
                m.d.comb += self.csr_rdata.eq(Cat(self.halt.pwrbrk, self.halt.perst, ~self.halt.pwr_en))
            with m.Case(0x084):
                m.d.comb += self.csr_rdata.eq(self.alarms.alarms)
            with m.Case(0x104):
                m.d.comb += self.csr_rdata.eq(self.mbox.status)
            with m.Default():
                m.d.comb += self.csr_rdata.eq(0)
        for i in range(8):                                               # EPOCH[0..7] at 0x010.., MEAS0 at 0x030.., MEAS1 at 0x050..
            with m.If(a == 0x010 + 4 * i):
                m.d.comb += self.csr_rdata.eq(self.epoch.epoch[32 * i: 32 * i + 32])
            with m.If(a == 0x030 + 4 * i):
                m.d.comb += self.csr_rdata.eq(self.meas0.value[32 * i: 32 * i + 32])
            with m.If(a == 0x050 + 4 * i):
                m.d.comb += self.csr_rdata.eq(self.meas1.value[32 * i: 32 * i + 32])
        return m

    def ports(self) -> list:
        p = [self.csr_addr, self.csr_rdata, self.doorbell, self.pwrbrk_n, self.perst_n, self.pwr_en,
             self.loop_out_open, self.loop_sense, self.tick, self.sample,
             self.mono.hwm, self.mono.load_hwm, self.mono.dec_req, self.mono.refused,
             self.meas0.extend, self.meas0.data, self.meas0.hash_req, self.meas0.hash_in, self.meas0.hash_done, self.meas0.hash_out,
             self.meas1.extend, self.meas1.data, self.meas1.hash_req, self.meas1.hash_in, self.meas1.hash_done, self.meas1.hash_out,
             self.epoch.commit, self.epoch.quorum_ok, self.epoch.new_epoch, self.epoch.host_wr, self.epoch.host_data,
             self.life.fuse_state, self.life.load, self.life.advance, self.life.advance_to, self.life.debug_req, self.life.debug_grant,
             self.tickets.query, self.tickets.burn, self.tickets.id_in, self.tickets.seen, self.tickets.burned, self.tickets.full,
             self.hb.hb_valid, self.hb.window,
             self.halt.tamper, self.halt.cmd_halt, self.halt.cmd_throttle, self.halt.local_trip, self.halt.clear,
             self.meter.slot, self.meter.add_tokens, self.meter.add_cycles, self.meter.add_in, self.meter.add_out, self.meter.strobe,
             self.meter.rd_slot, self.meter.rd_tokens,
             self.mbox.frame_seq, self.mbox.signer_class, self.mbox.cmd, self.mbox.epoch_match, self.mbox.epoch_exempt,
             self.mbox.needs_run, self.mbox.sig_done, self.mbox.sig_ok, self.mbox.verify_req, self.mbox.dispatch, self.mbox.cmd_out,
             self.alarms.set_mask, self.alarms.clear_mask, self.alarms.clear_authorized]
        for c in self.caps.values():
            p += [c.ins, c.ins_point, c.ins_peer, c.ins_dir, c.ins_budget, c.ins_expiry, c.ins_epoch_tag, c.mac_ok, c.ins_ok,
                  c.lk, c.lk_point, c.lk_peer, c.lk_dir, c.lk_bytes, c.allow, c.reason]
        return p
