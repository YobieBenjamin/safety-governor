"""The bench bitstream's logic: governor_core behind the SMBus target, plus the bench harness that stands in for
the firmware the FPGA does not have.

    python3 hw/fpga/top.py OUTDIR [CLK_MHZ]   # writes OUTDIR/bench_top.v and OUTDIR/fw_chain.json (default 50 MHz)

What is in it:
- GovernorSMBus (rtl/governor_rtl/smbus_top.py): the whole governor_core and the SMBus target, at 50 MHz with a
  1 us tick. The host's only way in is the SMBus target: read-only CSR window plus the doorbell.
- The firmware stand-in, BENCH ONLY. On the chip the Ibex firmware and the crypto engines drive the core's
  firmware-side ports (heartbeat verdicts, clears, capability inserts, hash results). The FPGA has neither, so:
    * four discrete pins carry the halt-path verdicts the soak test needs: FW_HB (a valid heartbeat, rising edge,
      loads a 5,000 ms window, the policy expiry of docs/04 section 9), FW_CLEAR (an authorized clear), FW_HALT
      (an authorized halt command), TAMPER_N (the enclosure switch, low = tripped);
    * every other firmware-side input of the core sits on a shift chain (FW_SCK, FW_SDI, FW_CS_N, FW_SDO: SPI mode 0,
      a Raspberry Pi's SPI0). The rising edge of FW_CS_N applies the shifted vector: level ports hold their value
      until the next vector, strobe ports pulse for exactly one clock. The core's firmware-side outputs are captured
      on that pulse cycle (one-bit outputs are sticky since the previous capture) and shift out on FW_SDO during the
      next transfer. The map of bits is fw_chain.json.
  These pins do not exist on the governor module. They are the firmware's wires, brought out so a bench host can
  play the firmware, and so synthesis keeps the whole core instead of pruning logic whose inputs are tied off.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from amaranth import Cat, Elaboratable, Module, Signal  # noqa: E402
from amaranth.back import verilog  # noqa: E402
from amaranth.lib.cdc import FFSynchronizer  # noqa: E402

from rtl.governor_rtl import GovernorSMBus  # noqa: E402

HB_WINDOW_MS = 5000
# core ports the bench drives some other way, or that are not firmware-side
NOT_ON_CHAIN = {"clk", "rst", "csr_addr", "csr_rdata", "doorbell", "tick", "sample", "loop_sense", "hb_hb_valid",
                "hb_window", "halt_clear", "halt_cmd_halt", "halt_tamper", "pwrbrk_n", "perst_n", "pwr_en", "loop_out_open"}
STROBE_SUFFIXES = ("_ins", "_lk", "_burn", "_query", "_extend", "_hash_done", "_commit", "_host_wr", "_advance", "_load",
                   "_strobe", "_dec_req", "_load_hwm", "_sig_done")
STROBE_NAMES = {"halt_cmd_throttle", "halt_local_trip", "alarms_set_mask", "alarms_clear_authorized"}


def core_port_directions() -> dict[str, str]:
    """name -> 'input'/'output' for the top module of the checked-in rtl/gen/governor_core.v."""
    text = open(os.path.join(ROOT, "rtl", "gen", "governor_core.v"), encoding="utf-8").read()
    start = text.index("module governor_core(")
    body = text[start: text.index("endmodule", start)]
    dirs = {}
    for d, name in re.findall(r"^\s*(input|output)\s+(?:\[\d+:\d+\]\s+)?(\w+)\s*;", body, re.M):
        dirs[name] = d
    return dirs


def is_strobe(name: str) -> bool:
    return name in STROBE_NAMES or name.endswith(STROBE_SUFFIXES)


class BenchTop(Elaboratable):
    def __init__(self, clk_mhz: int = 50):
        self.clk_mhz = clk_mhz
        self.gov = GovernorSMBus(tick_div=clk_mhz, sample_div=100)       # 1 us tick at any whole-MHz clock
        # pads
        self.scl_i = Signal(init=1)
        self.sda_i = Signal(init=1)
        self.scl_oe = Signal()
        self.sda_oe = Signal()
        self.perst_n_oe = Signal()       # open drain: 1 pulls PERST# low (reset asserted)
        self.pwrbrk_n_oe = Signal()      # open drain: 1 pulls PWRBRK# low (brake asserted)
        self.pwr_en = Signal()
        self.loop_closed = Signal()      # our loop switch closed (jumper to loop_sense on a one-governor bench)
        self.loop_sense = Signal()
        self.fw_hb = Signal()
        self.fw_clear = Signal()
        self.fw_halt = Signal()
        self.tamper_n = Signal(init=1)
        self.fw_sck = Signal()
        self.fw_sdi = Signal()
        self.fw_cs_n = Signal(init=1)
        self.fw_sdo = Signal()
        self.led = Signal(8)

        dirs = core_port_directions()
        by_name = {s.name: s for s in self.gov.core.ports()}
        missing = set(dirs) - set(by_name) - {"clk", "rst"}
        assert not missing, f"governor_core.v ports with no Amaranth signal: {sorted(missing)} (run python -m rtl.gen)"
        self.chain_in = [(n, by_name[n]) for n in sorted(dirs) if dirs[n] == "input" and n not in NOT_ON_CHAIN]
        self.chain_out = [(n, by_name[n]) for n in sorted(dirs) if dirs[n] == "output" and n not in NOT_ON_CHAIN]
        n_in = sum(len(s) for _, s in self.chain_in)
        n_out = sum(len(s) for _, s in self.chain_out)
        self.length = (max(n_in, n_out) + 7) // 8 * 8

    def chain_map(self) -> dict:
        def entries(items, strobes):
            out, off = [], 0
            for n, s in items:
                e = {"name": n, "offset": off, "width": len(s)}
                if strobes:
                    e["strobe"] = is_strobe(n)
                out.append(e)
                off += len(s)
            return out
        return {"length": self.length, "spi_mode": 0, "bit_order": "msb_first_of_the_whole_vector",
                "inputs": entries(self.chain_in, True), "outputs": entries(self.chain_out, False),
                "hb_window_ms": HB_WINDOW_MS}

    def elaborate(self, platform):
        m = Module()
        m.submodules.gov = gov = self.gov
        core = gov.core

        def sync_in(pad, init=0):
            s = Signal(init=init, name=pad.name + "_s")
            m.submodules["sync_" + pad.name] = FFSynchronizer(pad, s, init=init)
            return s

        def rising(sig):
            p = Signal(name=sig.name + "_p")
            m.d.sync += p.eq(sig)
            return sig & ~p

        hb, clr, hlt = sync_in(self.fw_hb), sync_in(self.fw_clear), sync_in(self.fw_halt)
        tamper_n = sync_in(self.tamper_n, 1)
        sense = sync_in(self.loop_sense)
        sck, sdi, cs_n = sync_in(self.fw_sck), sync_in(self.fw_sdi), sync_in(self.fw_cs_n, 1)

        m.d.comb += [
            gov.scl_i.eq(self.scl_i), gov.sda_i.eq(self.sda_i),
            self.scl_oe.eq(gov.scl_oe), self.sda_oe.eq(gov.sda_oe),
            self.perst_n_oe.eq(~gov.perst_n), self.pwrbrk_n_oe.eq(~gov.pwrbrk_n), self.pwr_en.eq(gov.pwr_en),
            self.loop_closed.eq(~gov.loop_out_open), gov.loop_sense.eq(sense),
            core.hb.window.eq(HB_WINDOW_MS),
            core.hb.hb_valid.eq(rising(hb)),
            core.halt.clear.eq(rising(clr)),
            core.halt.cmd_halt.eq(rising(hlt)),
            core.halt.tamper.eq(~tamper_n),
        ]

        # ---- the firmware stand-in chain
        L = self.length
        shadow = Signal(L)
        rb = Signal(L)
        apply = Signal()
        pulse = Signal()
        sck_rise = rising(sck)
        cs_rise = rising(cs_n)
        m.d.comb += self.fw_sdo.eq(rb[L - 1])
        m.d.sync += [apply.eq(cs_rise), pulse.eq(apply)]
        with m.If(sck_rise & ~cs_n):
            m.d.sync += shadow.eq(Cat(sdi, shadow[:L - 1]))
        off = 0
        for n, s in self.chain_in:
            w = len(s)
            reg = Signal(w, name="fw_" + n)
            if is_strobe(n):
                with m.If(apply):
                    m.d.sync += reg.eq(shadow[off: off + w])
                with m.Else():
                    m.d.sync += reg.eq(0)
            else:
                with m.If(apply):
                    m.d.sync += reg.eq(shadow[off: off + w])
            m.d.comb += s.eq(reg)
            off += w
        outs = []
        for n, s in self.chain_out:
            if len(s) == 1:
                sticky = Signal(name="sticky_" + n)
                with m.If(pulse):
                    m.d.sync += sticky.eq(0)
                with m.Elif(s):
                    m.d.sync += sticky.eq(1)
                outs.append(s | sticky)
            else:
                outs.append(s)
        packed = Cat(*outs)
        with m.If(pulse):                       # the cycle the strobes are live
            m.d.sync += rb.eq(packed)
        with m.Elif(sck_rise & ~cs_n):
            m.d.sync += rb.eq(Cat(0, rb[:L - 1]))

        # ---- LEDs: state, loop switch open, brake, doorbell blink, SMBus timeout seen, heartbeat blink
        blink = 100_000 * self.clk_mhz                                  # 0.1 s
        blink_db = Signal(range(blink + 1))
        blink_hb = Signal(range(blink + 1))
        to_seen = Signal()
        with m.If(gov.smb.doorbell):
            m.d.sync += blink_db.eq(blink)
        with m.Elif(blink_db != 0):
            m.d.sync += blink_db.eq(blink_db - 1)
        with m.If(core.hb.hb_valid):
            m.d.sync += blink_hb.eq(blink)
        with m.Elif(blink_hb != 0):
            m.d.sync += blink_hb.eq(blink_hb - 1)
        with m.If(gov.smb.timeout):
            m.d.sync += to_seen.eq(1)
        m.d.comb += self.led.eq(Cat(core.halt.state, core.halt.switch_open, core.halt.pwrbrk, blink_db != 0, to_seen,
                                    blink_hb != 0))
        return m

    def ports(self):
        return [self.scl_i, self.sda_i, self.scl_oe, self.sda_oe, self.perst_n_oe, self.pwrbrk_n_oe, self.pwr_en,
                self.loop_closed, self.loop_sense, self.fw_hb, self.fw_clear, self.fw_halt, self.tamper_n,
                self.fw_sck, self.fw_sdi, self.fw_cs_n, self.fw_sdo, self.led]


def main(out: str, clk_mhz: int = 50) -> int:
    os.makedirs(out, exist_ok=True)
    top = BenchTop(clk_mhz)
    text = verilog.convert(top, name="bench_top", ports=top.ports(), emit_src=False)
    with open(os.path.join(out, "bench_top.v"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(out, "fw_chain.json"), "w", encoding="utf-8") as f:
        json.dump(top.chain_map(), f, indent=1)
        f.write("\n")
    print(f"bench_top.v and fw_chain.json written to {out}: chain of {top.length} bits, "
          f"{len(top.chain_in)} input ports, {len(top.chain_out)} output ports")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "build"),
                  int(sys.argv[2]) if len(sys.argv) > 2 else 50))
