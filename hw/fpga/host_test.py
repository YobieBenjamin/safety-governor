#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Bench host for the governor FPGA: run on a Raspberry Pi wired as in hw/fpga/BENCH.md.

    python3 hw/fpga/host_test.py selftest            # no hardware: the frame and PEC code against known vectors
    python3 hw/fpga/host_test.py check               # CSR window, doorbell, malformed traffic (about 10 s)
    python3 hw/fpga/host_test.py levers              # walk the sequencer, read PERST#/PWRBRK#/PWR_EN back as wires
    python3 hw/fpga/host_test.py fwchain             # the firmware stand-in chain reaches the core (meter, alarms, CAUSE)
    python3 hw/fpga/host_test.py exclude             # no first heartbeat: named alarm; EXCLUDE closes the loop, levers stay on
    python3 hw/fpga/host_test.py soak --hours 168    # the false-halt soak: RUN, heartbeats, count every halt
    python3 hw/fpga/host_test.py all --hours 24      # all of the above in order; exit 0 only if every step passed

Every run writes hw/fpga/results/<step>-<UTC time>.json with what it measured, pass or fail.

What this measures of N3 (docs/20): the false-halt rate of the hardware halt path (sequencer, loop debounce, levers,
heartbeat timer) on real silicon, real wires and a real loop, and the host-visible latencies (CSR read over SMBus,
lever response to a halt command as the Pi sees it, which is coarse: a scope on PERST# gives the real figure).
What it cannot measure on this bitstream: firmware share, crypto engine utilisation and record latency. The FPGA
carries no Ibex and no crypto engines, so those three numbers wait for the OpenTitan integration. The JSON says so.

Needs on the Pi: python3 -m pip install smbus2 gpiozero spidev (gpiozero ships with Raspberry Pi OS), I2C and SPI
enabled (sudo raspi-config nonint do_i2c 0; sudo raspi-config nonint do_spi 0), and the board flashed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ADDR = 0x58
I2C_BUS = 1
DOORBELL_CMD = 0x40
HB_PERIOD_S = 1.0                    # the authority's heartbeat period (docs/04 section 9)
HB_WINDOW_MS = 5000                  # what one FW_HB pulse loads (hw/fpga/top.py)
BOOT_WINDOW_MS = 5000                # governor_core t_boot_ms: no first heartbeat for this long raises NO_FIRST_HEARTBEAT

# docs/04-specification.md section 2: byte offsets; the SMBus command code is offset >> 2
REG = {"ID": 0x000, "LIFECYCLE": 0x004, "STATE": 0x008, "CAUSE": 0x00C, "MONO_LO": 0x070, "MONO_HI": 0x074,
       "HB_REMAIN": 0x078, "LOOP": 0x07C, "LEVERS": 0x080, "ALARMS": 0x084, "MBOX_STATUS": 0x104, "MBOX_SEQ": 0x108,
       **{f"EPOCH{i}": 0x010 + 4 * i for i in range(8)}, **{f"MEAS0_{i}": 0x030 + 4 * i for i in range(8)},
       **{f"MEAS1_{i}": 0x050 + 4 * i for i in range(8)}, "METER0_TOKENS_LO": 0x200, "METER0_TOKENS_HI": 0x204}
STATIC = [n for n in REG if n not in ("MONO_LO", "MONO_HI", "HB_REMAIN")]
STATES = {0: "HALTED_INITIAL", 1: "RUN", 2: "THROTTLE", 3: "HALT", 4: "SAFE"}
ID_VALUE = 0x5347_0001

# Raspberry Pi BCM GPIO numbers (BENCH.md wiring table)
PIN = {"FW_HB": 17, "FW_CLEAR": 27, "FW_HALT": 22, "TAMPER_N": 23, "BENCH_RST": 24, "LOOP_BREAK": 26,
       "PERST_N": 5, "PWRBRK_N": 6, "PWR_EN": 13, "LOOP_CLOSED": 19}


# ---- protocol (pure functions; rtl/tests/test_smbus.py runs these frames against the RTL)

class PECError(Exception):
    pass


def crc8(data: bytes, crc: int = 0) -> int:
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def read_frames(offset: int) -> tuple[bytes, int]:
    """A CSR read as i2c_rdwr messages: write [cmd], repeated start, read 6 (count, 4 data, PEC)."""
    assert offset % 4 == 0 and 0 <= offset < 0x400
    return bytes([offset >> 2]), 6


def parse_read(addr: int, offset: int, data: bytes) -> int:
    if len(data) != 6 or data[0] != 4:
        raise PECError(f"bad block read frame {data.hex()}")
    want = crc8(bytes([addr << 1, offset >> 2, (addr << 1) | 1]) + data[:5])
    if data[5] != want:
        raise PECError(f"PEC {data[5]:#04x}, expected {want:#04x}")
    return int.from_bytes(data[1:5], "little")


def doorbell_frame(addr: int, value: int) -> bytes:
    body = bytes([DOORBELL_CMD, 4]) + value.to_bytes(4, "little")
    return body + bytes([crc8(bytes([addr << 1]) + body)])


def malformed_frames(addr: int) -> list[bytes]:
    """Writes the target must refuse without changing anything. Payloads after the address byte."""
    good = doorbell_frame(addr, 0x5A5A5A5A)
    frames = [good[:-1] + bytes([good[-1] ^ 0x01]),                       # bad PEC
              good[:-1],                                                   # no PEC
              good[:4],                                                    # truncated data
              good + b"\x00"]                                              # a byte after the PEC
    for off in (0x000, 0x004, 0x008, 0x00C, 0x010, 0x080, 0x084, 0x104, 0x108):
        body = bytes([off >> 2, 4]) + (0xFFFFFFFF).to_bytes(4, "little")
        frames.append(body + bytes([crc8(bytes([addr << 1]) + body)]))      # block write to a read-only register
        frames.append(bytes([off >> 2, 0x01]))                              # SMBus Write Byte
    body = bytes([DOORBELL_CMD, 5]) + (1).to_bytes(4, "little")
    frames.append(body + bytes([crc8(bytes([addr << 1]) + body)]))          # wrong count
    return frames


# ---- hardware

class Link:
    """SMBus to the target through the Pi's I2C controller. Every frame is built here, PEC included, and sent with
    i2c_rdwr, so the result does not depend on whether the adapter driver implements SMBus block reads or PEC."""

    def __init__(self, bus: int = I2C_BUS, addr: int = ADDR):
        from smbus2 import SMBus, i2c_msg            # noqa: F401
        self.SMBus, self.i2c_msg = SMBus, i2c_msg
        self.bus = SMBus(bus)
        self.addr = addr
        self.pec_errors = 0
        self.nacks = 0

    def read(self, name_or_offset) -> int:
        off = REG[name_or_offset] if isinstance(name_or_offset, str) else name_or_offset
        wr, n = read_frames(off)
        w = self.i2c_msg.write(self.addr, list(wr))
        r = self.i2c_msg.read(self.addr, n)
        self.bus.i2c_rdwr(w, r)
        try:
            return parse_read(self.addr, off, bytes(list(r)))
        except PECError:
            self.pec_errors += 1
            raise

    def write(self, payload: bytes) -> bool:
        """True if the target ACKed every byte."""
        try:
            self.bus.i2c_rdwr(self.i2c_msg.write(self.addr, list(payload)))
            return True
        except OSError:
            self.nacks += 1
            return False

    def doorbell(self, value: int) -> bool:
        return self.write(doorbell_frame(self.addr, value))


class Pins:
    def __init__(self):
        from gpiozero import DigitalInputDevice, DigitalOutputDevice
        self.out = {n: DigitalOutputDevice(PIN[n], initial_value=(n == "TAMPER_N")) for n in
                    ("FW_HB", "FW_CLEAR", "FW_HALT", "TAMPER_N", "BENCH_RST")}
        self.inp = {n: DigitalInputDevice(PIN[n], pull_up=None, active_state=True) for n in
                    ("PERST_N", "PWRBRK_N", "PWR_EN", "LOOP_CLOSED")}
        self._DigitalOutputDevice = DigitalOutputDevice
        self.loop_break = None

    def pulse(self, name: str, width_s: float = 0.001):
        self.out[name].on()
        time.sleep(width_s)
        self.out[name].off()

    def level(self, name: str) -> int:
        return int(self.inp[name].value)

    def reset_board(self):
        self.out["BENCH_RST"].on()
        time.sleep(0.01)
        self.out["BENCH_RST"].off()
        time.sleep(0.01)                               # 2^16 cycles of power-on reset at 50 MHz is 1.3 ms

    def break_loop(self, on: bool):
        """Pull LOOP_SENSE low through the Pi (an injected loop fault); off releases the pin to an input."""
        if on and self.loop_break is None:
            self.loop_break = self._DigitalOutputDevice(PIN["LOOP_BREAK"], initial_value=False)
        elif not on and self.loop_break is not None:
            self.loop_break.close()
            self.loop_break = None


class Chain:
    """The firmware stand-in shift chain (hw/fpga/top.py) over the Pi's SPI0, CE0 as FW_CS_N."""

    def __init__(self, path: str = os.path.join(HERE, "fw_chain.json")):
        import spidev
        self.map = json.load(open(path, encoding="utf-8"))
        self.L = self.map["length"]
        self.inputs = {e["name"]: e for e in self.map["inputs"]}
        self.outputs = {e["name"]: e for e in self.map["outputs"]}
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.mode = 0
        self.spi.max_speed_hz = 1_000_000
        self.levels: dict[str, int] = {}

    def apply(self, **ports) -> dict[str, int]:
        """Apply one vector (levels persist across calls unless given again; strobes pulse once). Returns the
        readback captured by the PREVIOUS apply."""
        vec = 0
        for n, v in ports.items():
            e = self.inputs[n]
            if not e["strobe"]:
                self.levels[n] = v
        for n, v in {**self.levels, **{k: v for k, v in ports.items() if self.inputs[k]["strobe"]}}.items():
            e = self.inputs[n]
            vec |= (v & ((1 << e["width"]) - 1)) << e["offset"]
        rx = self.spi.xfer2(list(vec.to_bytes(self.L // 8, "big")))
        rb = int.from_bytes(bytes(rx), "big")
        return {n: (rb >> e["offset"]) & ((1 << e["width"]) - 1) for n, e in self.outputs.items()}


# ---- steps

def record(step: str, ok: bool, data: dict) -> bool:
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(HERE, "results", f"{step}-{stamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"step": step, "pass": ok, "utc": stamp, **data}, f, indent=1)
    print(f"{'PASS' if ok else 'FAIL'}  {step}  -> {os.path.relpath(path)}")
    return ok


def step_selftest(_args) -> bool:
    checks = {
        "crc8 check value (CRC-8/SMBUS of '123456789' is 0xF4)": crc8(b"123456789") == 0xF4,
        "doorbell frame layout": doorbell_frame(ADDR, 0x11223344)[:6] == bytes([0x40, 4, 0x44, 0x33, 0x22, 0x11]),
        "doorbell PEC covers the address byte": doorbell_frame(ADDR, 0)[-1] == crc8(bytes([ADDR << 1, 0x40, 4, 0, 0, 0, 0])),
        "read parse accepts a good frame": parse_read(ADDR, 0, bytes([4, 1, 0, 0x47, 0x53,
                                                                       crc8(bytes([ADDR << 1, 0, (ADDR << 1) | 1, 4, 1, 0, 0x47, 0x53]))])) == ID_VALUE,
    }
    try:
        parse_read(ADDR, 0, bytes([4, 1, 0, 0x47, 0x53, 0]))
        checks["read parse rejects a bad PEC"] = False
    except PECError:
        checks["read parse rejects a bad PEC"] = True
    for k, v in checks.items():
        print(f"  {'ok ' if v else 'BAD'} {k}")
    return all(checks.values())


def step_check(args) -> bool:
    link, pins = Link(), Pins()
    pins.reset_board()
    out, ok = {}, True
    t0 = time.perf_counter()
    for _ in range(100):
        link.read("ID")
    out["csr_read_ms"] = round((time.perf_counter() - t0) * 10, 3)
    snap = {n: link.read(n) for n in STATIC}
    out["after_reset"] = {n: hex(v) for n, v in snap.items()}
    ok &= snap["ID"] == ID_VALUE and snap["STATE"] == 0 and snap["LEVERS"] == 0b111 and snap["MBOX_STATUS"] == 0
    # malformed traffic first: nothing may change. Most frames are NACKed on the bus; the two that stop short of
    # the PEC (no PEC, truncated data) are ACKed byte by byte and simply never commit, so the test is the registers.
    nacked = [not link.write(f) for f in malformed_frames(ADDR)]
    after = {n: link.read(n) for n in STATIC}
    out["malformed_frames"] = len(nacked)
    out["malformed_nacked_on_the_bus"] = sum(nacked)
    out["registers_changed_by_malformed"] = sorted(n for n in STATIC if after[n] != snap[n])
    ok &= not out["registers_changed_by_malformed"]
    # then the one legal write: the doorbell reaches the mailbox (status 4, bad sequence: no firmware behind it)
    acked = link.doorbell(64)
    status = link.read("MBOX_STATUS")
    out["doorbell_acked"], out["mbox_status_after_doorbell"] = acked, status
    ok &= acked and status == 4
    out["pec_errors"], out["unexpected_nacks"] = link.pec_errors, link.nacks - sum(nacked)
    return record("check", bool(ok), out)


def wait_state(link, want, timeout_s):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        s = link.read("STATE")
        if s == want:
            return True, time.monotonic() - t0
        time.sleep(0.001)
    return False, timeout_s


def to_run(link, pins) -> bool:
    """Back to RUN the way the chip does it: an authorized clear, then a valid heartbeat with the loop closed."""
    pins.out["TAMPER_N"].on()
    pins.pulse("FW_CLEAR")
    pins.pulse("FW_HB")
    return wait_state(link, 1, 1.0)[0]


def step_levers(args) -> bool:
    link, pins = Link(), Pins()
    rows, ok = [], True

    def observe(label, want_state):
        s = link.read("STATE")
        lev = link.read("LEVERS")
        wires = {n: pins.level(n) for n in ("PERST_N", "PWRBRK_N", "PWR_EN", "LOOP_CLOSED")}
        # the wires must agree with the LEVERS register: bit0 brake asserted, bit1 PERST# asserted, bit2 PWR_EN low
        agree = (wires["PWRBRK_N"] == 1 - (lev & 1) and wires["PERST_N"] == 1 - ((lev >> 1) & 1)
                 and wires["PWR_EN"] == 1 - ((lev >> 2) & 1))
        rows.append({"step": label, "state": STATES.get(s, s), "levers": lev, "wires": wires, "agree": agree})
        return s == want_state and agree

    pins.reset_board()
    ok &= observe("after reset", 0)
    ok &= to_run(link, pins) and observe("heartbeat, loop closed", 1)
    t0 = time.perf_counter()
    pins.pulse("FW_HALT", 0.0001)
    while pins.level("PERST_N") and time.perf_counter() - t0 < 0.1:
        pass
    halt_s = time.perf_counter() - t0
    ok &= observe("halt command", 3)
    pins.pulse("FW_CLEAR")
    ok &= observe("clear", 0) or observe("clear (re-armed)", 1)
    ok &= to_run(link, pins)
    pins.out["TAMPER_N"].off()
    time.sleep(0.01)
    ok &= observe("tamper", 4)
    pins.out["TAMPER_N"].on()
    ok &= to_run(link, pins)
    pins.break_loop(True)
    time.sleep(0.01)                                    # two 100 us sense periods, with room
    ok &= observe("loop broken", 3)
    ok &= (link.read("CAUSE") & 7) == 1
    pins.break_loop(False)
    ok &= to_run(link, pins)
    time.sleep(HB_WINDOW_MS / 1000 + 0.5)               # no heartbeat for the whole window
    ok &= observe("heartbeat expired", 2)
    return record("levers", bool(ok), {"rows": rows, "halt_cmd_to_perst_low_s_pi_polled": round(halt_s, 6)})


def step_fwchain(args) -> bool:
    link, pins, ch = Link(), Pins(), Chain()
    pins.reset_board()
    ok, out = True, {}
    t0 = link.read("METER0_TOKENS_LO")
    ch.apply(meter_slot=0, meter_add_tokens=7, meter_strobe=1)
    ch.apply(meter_add_tokens=0)
    t1 = link.read("METER0_TOKENS_LO")
    out["meter_tokens_before_after"] = [t0, t1]
    ok &= t1 == t0 + 7
    ch.apply(cause_fw=0x2A)
    out["cause"] = link.read("CAUSE")
    ok &= (out["cause"] >> 8) == 0x2A
    ch.apply(alarms_set_mask=0x10)
    out["alarms"] = link.read("ALARMS")
    ok &= (out["alarms"] & 0x10) == 0x10
    ch.apply(tickets_id_in=0xCAFE, tickets_burn=1)
    ch.apply(tickets_id_in=0xCAFE, tickets_query=1)
    rb = ch.apply(tickets_id_in=0)
    out["ticket_seen_after_burn"] = rb["tickets_seen"]
    ok &= rb["tickets_seen"] == 1
    return record("fwchain", bool(ok), out)


def step_exclude(args) -> bool:
    """Yobie's call 2 on the board: a chip that never gets its first heartbeat holds the loop open, says so by name
    after the boot window, and an authorized EXCLUDE closes its loop switch while its own levers stay asserted."""
    link, pins, ch = Link(), Pins(), Chain()
    pins.reset_board()
    out, ok = {}, True
    pins.out["TAMPER_N"].on()
    time.sleep(0.2)
    out["before_window"] = {"alarms": link.read("ALARMS"), "cause": link.read("CAUSE"), "loop_closed": pins.level("LOOP_CLOSED")}
    ok &= not (out["before_window"]["alarms"] >> 31) & 1            # not yet: the window has not passed
    ok &= out["before_window"]["loop_closed"] == 0                  # our switch is open: the rack is held
    time.sleep(BOOT_WINDOW_MS / 1000 + 0.5)                         # no heartbeat for the whole boot window
    a, c = link.read("ALARMS"), link.read("CAUSE")
    out["after_window"] = {"alarms": a, "cause": c, "boot_wait_ms": link.read(0x088), "loop_closed": pins.level("LOOP_CLOSED"),
                           "pwr_en": pins.level("PWR_EN")}
    ok &= (a >> 31) & 1 == 1 and (c >> 3) & 1 == 1                  # NO_FIRST_HEARTBEAT: named, sticky, live
    ok &= out["after_window"]["loop_closed"] == 0
    ch.apply(halt_cmd_exclude=1)                                    # the authorized EXCLUDE, as the firmware would strobe it
    time.sleep(0.01)
    a, c = link.read("ALARMS"), link.read("CAUSE")
    out["after_exclude"] = {"alarms": a, "cause": c, "loop_closed": pins.level("LOOP_CLOSED"), "pwr_en": pins.level("PWR_EN"),
                            "perst_n": pins.level("PERST_N"), "pwrbrk_n": pins.level("PWRBRK_N"), "state": link.read("STATE")}
    ok &= out["after_exclude"]["loop_closed"] == 1                  # the rest of the rack can run
    ok &= (a >> 30) & 1 == 1 and (c >> 4) & 1 == 1                  # EXCLUDED: named
    ok &= out["after_exclude"]["state"] == 0 and out["after_exclude"]["pwr_en"] == 0 \
        and out["after_exclude"]["perst_n"] == 0 and out["after_exclude"]["pwrbrk_n"] == 0   # this chip's own GPU stays off
    pins.pulse("FW_HB")                                             # a valid heartbeat arms it the normal way
    out["after_heartbeat_state"] = STATES.get(link.read("STATE"))
    ok &= wait_state(link, 1, 1.0)[0]
    return record("exclude", bool(ok), out)


def step_soak(args) -> bool:
    link, pins = Link(), Pins()
    pins.reset_board()
    if not to_run(link, pins):
        return record("soak", False, {"error": "could not reach RUN"})
    end = time.monotonic() + args.hours * 3600
    halts, smbus_errors, samples = [], 0, 0
    last_hb = 0.0
    csv_path = os.path.join(HERE, "results", f"soak-{int(time.time())}.csv")
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", encoding="utf-8") as csv:
        csv.write("t_s,state,cause,loop,levers,alarms\n")
        t_start = time.monotonic()
        while time.monotonic() < end:
            now = time.monotonic()
            if now - last_hb >= HB_PERIOD_S:
                pins.pulse("FW_HB")
                last_hb = now
            try:
                s, c, lp, lev, al = (link.read(n) for n in ("STATE", "CAUSE", "LOOP", "LEVERS", "ALARMS"))
            except (OSError, PECError):
                smbus_errors += 1
                time.sleep(0.05)
                continue
            samples += 1
            csv.write(f"{now - t_start:.3f},{s},{c},{lp},{lev},{al}\n")
            if s != 1:
                halts.append({"t_s": round(now - t_start, 3), "state": STATES.get(s, s), "cause": c, "loop": lp})
                csv.flush()
                if not to_run(link, pins):                  # record it, bring it back, keep counting
                    break
            time.sleep(0.2)
    hours = (time.monotonic() - t_start) / 3600
    out = {"hours": round(hours, 4), "samples": samples, "false_halts": len(halts), "halts": halts[:1000],
           "false_halts_per_hour": round(len(halts) / hours, 6) if hours else None, "smbus_errors": smbus_errors,
           "csv": os.path.relpath(csv_path),
           "not_measured_here": ["firmware share", "crypto engine utilisation", "record latency"],
           "why_not": "this bitstream has no Ibex firmware and no crypto engines (docs/08); they come with the "
                      "OpenTitan integration"}
    return record("soak", not halts and smbus_errors == 0, out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["selftest", "check", "levers", "fwchain", "exclude", "soak", "all"])
    ap.add_argument("--hours", type=float, default=24.0, help="soak duration (default 24)")
    args = ap.parse_args(argv)
    steps = {"selftest": step_selftest, "check": step_check, "levers": step_levers, "fwchain": step_fwchain,
             "exclude": step_exclude, "soak": step_soak}
    order = ["selftest", "check", "levers", "fwchain", "exclude", "soak"] if args.step == "all" else [args.step]
    ok = True
    for s in order:
        ok &= bool(steps[s](args))
        if not ok and args.step == "all":
            print(f"stopping: {s} failed")
            break
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
