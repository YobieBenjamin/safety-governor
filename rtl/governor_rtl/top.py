"""governor_core: the hard-core blocks wired together with the read-only CSR window from
``docs/04-specification.md`` section 2. The firmware side (Ibex, the crypto engines, the fabric
MAC) attaches to the strobes exposed as ports.

The CSR bus is read-only by construction: ``csr_rdata`` is a mux over the blocks' outputs
and there is no ``csr_wdata`` port. The only host-writable location is the mailbox doorbell.
``tick`` is the 1 us monotonic tick; the heartbeat and the sequencer run on ``tick_ms``, one
strobe every 2^10 ticks. LOG_HEAD and LOG_SIZE are firmware-mapped and not decoded here.

``tick_ms`` comes from its own prescaler (``ms_div``) counting ``tick``, not from the low bits of the
monotonic counter. Until 23 October 2026 it tapped ``mono.value[:10]``; ``load_hwm`` has priority over the
increment and can move the value anywhere upward, so whoever drives ``load_hwm``/``hwm`` could hold the low
bits off 1023 and stop every millisecond strobe: the heartbeat never expired and the rung timers froze,
with no valid heartbeat. L7 found it (rtl/formal/governor_core.sv, rule G5; FINDINGS-b.md, F2).
``ms_shift`` is a parameter only so the proof can run a short millisecond; the chip uses 10.
"""
from amaranth import Cat, Const, Elaboratable, Module, Mux, Signal

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
MS_SHIFT = 10            # 2^10 microsecond ticks per millisecond strobe


class GovernorCore(Elaboratable):
    def __init__(self, cap_entries: int = 8, ticket_entries: int = 8, t_throttle_ms: int = 30_000, t_halt_ms: int = 300_000,
                 ms_shift: int = MS_SHIFT):
        self.ms_shift = ms_shift
        self.ms_div = Signal(ms_shift, name="ms_div")     # microsecond ticks into the current millisecond
        self.mono = MonotonicCounter()
        self.meas0 = MeasureReg()
        self.meas1 = MeasureReg()
        self.epoch = EpochReg()
        self.life = Lifecycle()
        self.caps = {p: CapTable(entries=cap_entries) for p in POINTS}
        self.tickets = TicketStore(entries=ticket_entries)
        self.hb = Heartbeat()
        self.halt = HaltSeq(t_throttle=t_throttle_ms, t_halt=t_halt_ms)
        self.loop = LoopIO()
        self.meter = Meter()
        self.mbox = Mailbox()
        self.alarms = Alarms()
        # CSR window
        self.csr_addr = Signal(12)
        self.csr_rdata = Signal(32)
        self.doorbell = Signal()
        self.cause_fw = Signal(8)           # firmware-written reason code, CAUSE[15:8]
        # pads
        self.pwrbrk_n = Signal()
        self.perst_n = Signal()
        self.pwr_en = Signal()
        self.loop_out_open = Signal()
        self.loop_sense = Signal()
        self.tick = Signal()
        self.tick_ms = Signal()
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
            self.tick_ms.eq(self.tick & (self.ms_div == (1 << self.ms_shift) - 1)),
            self.hb.tick.eq(self.tick_ms),
            self.halt.tick.eq(self.tick_ms),
            self.loop.sample.eq(self.sample),
            self.loop.loop_sense.eq(self.loop_sense),
            self.loop.switch_open.eq(self.halt.switch_open),
            self.loop_out_open.eq(self.loop.loop_out_open),
            self.halt.loop_lost.eq(self.loop.loop_lost),
            self.halt.hb_expired.eq(self.hb.expired),
            self.halt.hb_ok.eq(~self.hb.expired),
            self.halt.loop_sense.eq(self.loop_sense),
            self.mbox.running.eq(self.halt.state == 1),
            self.mbox.doorbell.eq(self.doorbell),
            self.pwrbrk_n.eq(~self.halt.pwrbrk),
            self.perst_n.eq(~self.halt.perst),
            self.pwr_en.eq(self.halt.pwr_en),
        ]
        with m.If(self.tick):
            m.d.sync += self.ms_div.eq(self.ms_div + 1)
        for c in self.caps.values():
            m.d.comb += [c.now.eq(self.mono.value[:32]), c.epoch_tag.eq(self.epoch.epoch_tag), c.clear_all.eq(self.halt.ports_closed)]

        # ---- CSR read mux (word addresses from the register map)
        a = self.csr_addr
        meter_off = Signal(12)
        meter_val = Signal(64)
        m.d.comb += meter_off.eq(a - 0x200)
        m.d.comb += self.meter.rd_slot.eq(meter_off[5:7])                      # 32 bytes per slot: four 64-bit counters
        with m.Switch(meter_off[3:5]):
            with m.Case(0):
                m.d.comb += meter_val.eq(self.meter.rd_tokens)
            with m.Case(1):
                m.d.comb += meter_val.eq(self.meter.rd_cycles)
            with m.Case(2):
                m.d.comb += meter_val.eq(self.meter.rd_in)
            with m.Default():
                m.d.comb += meter_val.eq(self.meter.rd_out)
        with m.Switch(a):
            with m.Case(0x000):
                m.d.comb += self.csr_rdata.eq(0x5347_0001)             # 'SG', revision 1
            with m.Case(0x004):
                m.d.comb += self.csr_rdata.eq(self.life.state)
            with m.Case(0x008):
                m.d.comb += self.csr_rdata.eq(self.halt.state)
            with m.Case(0x00C):
                m.d.comb += self.csr_rdata.eq(Cat(self.halt.cause, Const(0, 5), self.cause_fw))   # CAUSE: [2:0] hardware, [15:8] firmware
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
            with m.Case(0x108):
                m.d.comb += self.csr_rdata.eq(self.mbox.last_seq[0])  # MBOX_SEQ: the first key slot's last accepted seq
            with m.Default():
                m.d.comb += self.csr_rdata.eq(0)
        for i in range(8):                                               # EPOCH[0..7] at 0x010.., MEAS0 at 0x030.., MEAS1 at 0x050..
            with m.If(a == 0x010 + 4 * i):
                m.d.comb += self.csr_rdata.eq(self.epoch.epoch[32 * i: 32 * i + 32])
            with m.If(a == 0x030 + 4 * i):
                m.d.comb += self.csr_rdata.eq(self.meas0.value[32 * i: 32 * i + 32])
            with m.If(a == 0x050 + 4 * i):
                m.d.comb += self.csr_rdata.eq(self.meas1.value[32 * i: 32 * i + 32])
        with m.If((a >= 0x200) & (a < 0x200 + 32 * self.meter.slots)):   # METER_SLOT[n]: tokens, cycles, bytes in, bytes out
            m.d.comb += self.csr_rdata.eq(Mux(meter_off[2], meter_val[32:], meter_val[:32]))
        return m

    def ports(self) -> list:
        p = [self.csr_addr, self.csr_rdata, self.doorbell, self.cause_fw, self.pwrbrk_n, self.perst_n, self.pwr_en,
             self.loop_out_open, self.loop_sense, self.tick, self.tick_ms, self.sample,
             self.mono.hwm, self.mono.load_hwm, self.mono.dec_req, self.mono.refused,
             self.meas0.extend, self.meas0.data, self.meas0.hash_req, self.meas0.hash_in, self.meas0.hash_done, self.meas0.hash_out,
             self.meas1.extend, self.meas1.data, self.meas1.hash_req, self.meas1.hash_in, self.meas1.hash_done, self.meas1.hash_out,
             self.epoch.commit, self.epoch.quorum_ok, self.epoch.new_epoch, self.epoch.host_wr, self.epoch.host_data,
             self.life.fuse_state, self.life.load, self.life.advance, self.life.advance_to, self.life.debug_req, self.life.debug_grant,
             self.tickets.query, self.tickets.burn, self.tickets.id_in, self.tickets.seen, self.tickets.burned, self.tickets.full,
             self.hb.hb_valid, self.hb.window,
             self.halt.tamper, self.halt.cmd_halt, self.halt.cmd_throttle, self.halt.local_trip, self.halt.clear,
             self.meter.slot, self.meter.add_tokens, self.meter.add_cycles, self.meter.add_in, self.meter.add_out, self.meter.strobe,
             self.mbox.frame_seq, self.mbox.key_slot, self.mbox.cmd, self.mbox.signed_cmd, self.mbox.epoch_match, self.mbox.epoch_exempt,
             self.mbox.needs_run, self.mbox.sig_done, self.mbox.sig_ok, self.mbox.verify_req, self.mbox.dispatch, self.mbox.cmd_out,
             self.alarms.set_mask, self.alarms.clear_mask, self.alarms.clear_authorized]
        for c in self.caps.values():
            p += [c.ins, c.ins_point, c.ins_peer, c.ins_dir, c.ins_budget, c.ins_expiry, c.ins_epoch_tag, c.mac_ok, c.ins_ok,
                  c.lk, c.lk_point, c.lk_peer, c.lk_dir, c.lk_bytes, c.allow, c.reason]
        return p
