# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Read FPGA build directories and say what happened. Called by hw/fpga/build.sh.

    python3 hw/fpga/report.py --met DIR                    # exit 0 if DIR's bitstream exists and timing met
    python3 hw/fpga/report.py --fallback DIR 40 30 25      # print the fastest candidate clock DIR's Fmax supports
    python3 hw/fpga/report.py --write REPORT.md --seed 1 DIR [DIR...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sys
from importlib import metadata

ASIC_MHZ = 50.0

NOTES = """## Findings from this build

**RTL-CORE-HALTS-AFTER-REACHING-RUN. The core halts itself one cycle after it first reaches RUN when the loop sense strobe runs from power-on.**
`LoopIO` counts sense samples with no current. Before the governor arms, its own loop switch is open, so on a
one-governor loop (and on any loop where this governor's switch is the open one) there is no current and the
debounce counter saturates: `loop_lost` is high while the core sits in HALTED_INITIAL. The heartbeat arms the core,
the switch closes, current flows, and `HaltSeq` goes to RUN without looking at `loop_lost`. The next cycle
`loop_lost & in_run` wins the priority chain and the core halts with cause LOOP. The counter clears only on the next
sample with current, up to 100 us later, and by then the switch is open again, so it never clears. The same happens
after every clear that follows a loop halt.
Reproducer: `rtl/tests/test_smbus.py::test_core_reaches_run_and_stays_there_with_the_sense_strobe_running_from_power_on`
(strict xfail: it fails by assertion today and turns red as XPASS the day the RTL is fixed).
`rtl/tests/test_blocks.py` does not see it because it raises `sample` only after the core is in RUN.
Proposed fix, not applied (halt.py is not this branch's): in `HaltSeq`, enter RUN only on `loop_sense & ~loop_lost`,
so an armed core waits for one clean sense sample (at most 100 us). Until then the bench (`host_test.py levers` and
`soak`) cannot hold RUN and will say so.

**RTL-FPGA-MISSES-50-MHZ. 50 MHz is not met on the ECP5: the design reaches about 38 MHz, limited by the capability table's one-cycle
lookup.** The critical path (below) runs from a lookup input of `cap_dpu` through the eight-entry CAM compare, the
priority select and the 24-bit budget compare and decrement, into the budget register, in one cycle (docs/04
section 9: "1 cycle at the checker clock"). In the router2 run at seed 1: 26.4 ns, 4.7 ns logic and 21.7 ns routing.
Nothing in the SMBus target or the bench harness is on it. Options, none applied: register the match and decrement a
cycle later (a two-cycle lookup the spec would have to say), or run the bench slower. The build does the second on
its own: the timers run on a 1 us tick divided from the clock, so the slower bench bitstream behaves the same at the
heartbeat, throttle, halt and loop-sense scale. This says nothing about sky130 at 50 MHz; that is LibreLane's STA.

**Spec and RTL disagreements noticed (recorded, not changed).** docs/04 section 2 lists MBOX_STATUS codes 0 to 6;
`mailbox.py` also returns 7 (wrong command, added 22 October), and the register is 3 bits where the table says 8.
docs/04 says 16 meter slots; the RTL meter has 4, so CSR reads of METER_SLOT[4..15] return 0.

## What did not work on the way here

| Attempt | What happened | Numbers | What I did |
|---|---|---|---|
| First CRC-8 in Amaranth, written as a loop of `Mux` | every level referenced the previous one twice, so the expression tree doubled eight times | `rtl/gen/smbus.v` came out at 109,431 lines | rewrote it as the XOR matrix CRC-8 really is: 1,451 lines |
| Formal proof, first three runs | k-induction failed on states no real bus reaches (receive shift register out of step with the monitor; a bit counter of 15; a write step after a repeated start) | each failure found in 6 to 9 s | added the invariants that tie the target to the monitor; then bounded (25 cycles) in 29 s and induction in about 1 s |
| Catching the 11 mutants in the bounded check | impossible at depth 25: one doorbell write is 8 bytes of 9 clocks through a 2-flop synchronizer and a 3-cycle filter, hundreds of cycles | 11 of 11 caught, all by the induction step | replayed every mutant as concrete bus traffic in `rtl/tests/test_smbus.py`; each fails a named rule there by assertion |
| `assign pad = oe ? 0 : 1'bz` for SDA/SCL | yosys left two `$_TBUF_` cells ("limited support for tri-state logic") | 2 cells | instantiated the ECP5 `BB` pad primitive directly |
| `ecppll -f /some/path/pll.v` | the WebAssembly build of ecppll can only write inside its working directory | no file written | run it inside the build directory |
| First structural check that `csr_addr` reaches no flip-flop | passed on the planted bug too: `yosys -q` swallows `select -list` output, so the list was always empty | 0 hits on a planted register | write the selection to a file; now 0 hits on the real core, more than 0 on the planted one |
| nextpnr with its default router (router1) at 50 MHz | did not converge: after about 20 minutes of routing 38,495 of 88,079 arcs were still overused and the count had stopped falling | stopped by hand at iteration 119,000 | switched to router2: routed in 193 s |
| `yosys ltp` to find the long path before routing | the WebAssembly yosys ran out of call stack on this netlist | trap: call stack exhausted | read the critical path from nextpnr after routing instead |
| A smaller part: ECP5 12F (ULX3S 12F, the cheaper board) | Lattice rates the part at 12k LUTs and the design needs 17,306 LUT4, so by the datasheet it does not fit. But nextpnr models the 12F as the 25F die it is built on and places the design anyway | `nextpnr-ecp5 --12k`: 17,284 of 24,288 LUT cells (71 percent), 12,828 flip-flops (52 percent), placement finished | stayed on the 85F. Whether a 12F board runs a design over its rated size is untested here and outside Lattice's ratings; worth one try on real hardware because the 12F board is cheaper |
| iCE40 (the yowasp-nextpnr-ice40 path in the brief) | does not fit | the core alone maps to 14,531 LUT4 on ECP5 out of context; the largest iCE40 HX8K has 7,680 logic cells | not attempted further |
| Raspberry Pi price lookup | the fetch was not approved in time | none | BENCH.md lists a price only where I read one (the ULX3S) |
"""
CELLS = ("LUT4", "TRELLIS_FF", "CCU2C", "PFUMX", "L6MUX21", "DP16KD", "MULT18X18D", "EHXPLLL", "TRELLIS_IO")


def load(d: str) -> dict:
    r = {"dir": d, "mhz": int(re.search(r"(\d+)mhz$", d.rstrip("/")).group(1))}
    p = os.path.join(d, "pnr_report.json")
    r["pnr"] = json.load(open(p)) if os.path.exists(p) else None
    bits = glob.glob(os.path.join(d, "*.bit"))
    r["bit"] = bits[0] if bits else None
    st = os.path.join(d, "synth_stat.txt")
    r["cells"] = {}
    if os.path.exists(st):
        for n, name in re.findall(r"^\s+(\d+)\s+(\S+)\s*$", open(st).read(), re.M):
            if name in CELLS:
                r["cells"][name] = int(n)
    fmax = (r["pnr"] or {}).get("fmax", {})
    r["fmax"] = {k: v for k, v in fmax.items()}
    r["met"] = bool(r["bit"]) and bool(fmax) and all(v["achieved"] >= v["constraint"] for v in fmax.values())
    r["achieved"] = min((v["achieved"] for v in fmax.values()), default=None)
    log = os.path.join(d, "nextpnr.log")
    r["log_tail"] = open(log).read().splitlines()[-5:] if os.path.exists(log) else []
    return r


def critical_path(r: dict, limit: int = 14) -> list[str]:
    paths = (r["pnr"] or {}).get("critical_paths", [])
    if not paths:
        return []
    p = paths[0]
    out = [f"From `{p.get('from')}` to `{p.get('to')}`:", "", "| Step | Delay (ns) | Net or cell |", "|---|---|---|"]
    segs = p.get("path", [])
    shown = segs if len(segs) <= limit else segs[: limit // 2] + [None] + segs[-limit // 2:]
    for s in shown:
        if s is None:
            out.append(f"| ... | | {len(segs) - limit} more steps |")
            continue
        what = s.get("net") or f"{s.get('from', {}).get('cell', '')} -> {s.get('to', {}).get('cell', '')}"
        out.append(f"| {s.get('type')} | {s.get('delay', 0):.2f} | `{what[:90]}` |")
    total = sum(s.get("delay", 0) for s in segs)
    out += ["", f"{len(segs)} steps, {total:.2f} ns in total."]
    return out


def versions() -> dict:
    out = {}
    for p in ("amaranth", "amaranth-yosys", "yowasp-yosys", "yowasp-nextpnr-ecp5"):
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = "not installed"
    return out


def write(path: str, seed: str, dirs: list[str]) -> int:
    builds = [load(d) for d in dirs]
    first = builds[0]
    clean = [b for b in builds if b["met"]]
    L = ["# FPGA build report: governor core + SMBus target on the ULX3S (ECP5 LFE5U-85F-6BG381C)", "",
         f"Written by `hw/fpga/build.sh` on {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}, "
         f"nextpnr seed {seed}, router2. Do not edit by hand: rerun the build.", "", "## Verdict", ""]
    fifty = next((b for b in builds if b["mhz"] == 50), None)
    if fifty and fifty["met"]:
        L.append(f"- 50 MHz (the ASIC flow's clock): **met**, Fmax {fifty['achieved']:.2f} MHz.")
    elif fifty:
        a = f"{fifty['achieved']:.2f} MHz" if fifty["achieved"] else "no timing result"
        L.append(f"- 50 MHz (the ASIC flow's clock): **NOT met**. The design reaches {a} on this part.")
    for b in builds:
        if b["mhz"] != 50:
            L.append(f"- {b['mhz']} MHz: {'met' if b['met'] else 'NOT met'}"
                     + (f", Fmax {b['achieved']:.2f} MHz" if b["achieved"] else "") + ".")
    if clean:
        c = clean[0]
        L.append(f"- Bench bitstream: `build/{os.path.basename(c['dir'])}/{os.path.basename(c['bit'])}` at {c['mhz']} MHz. "
                 "The governor's timers run on a 1 us tick divided from whatever the clock is, so the heartbeat, "
                 "throttle, halt and loop-sense timings are the same at any of these clocks.")
        mpath = os.path.join(c["dir"], "manifest.json")
        if os.path.exists(mpath):
            try:
                m = json.load(open(mpath, encoding="utf-8"))
                bit = m.get("bitstream") or {}
                L.append(f"- Build manifest (`{os.path.basename(c['dir'])}/manifest.json`): fail-closed, source_rev "
                         f"`{m.get('source_rev', '')[:16]}`, stages {','.join(m.get('stages', []))}, bitstream sha256 "
                         f"`{(bit.get('sha256') or '')[:16]}`. The verdict is read from this manifest, not from the bitstream's presence.")
            except (ValueError, OSError):
                pass
    else:
        L.append("- No timing-clean bitstream.")
    L += ["", "## Utilisation", "", "After synthesis (yosys `synth_ecp5`) and after place and route (nextpnr), "
          f"{first['mhz']} MHz build:", "", "| Cell | Synthesis |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(first["cells"].items())]
    if first["pnr"]:
        L += ["", "| Resource | Used | Available | Percent |", "|---|---|---|---|"]
        for res, u in sorted(first["pnr"].get("utilization", {}).items()):
            if u["used"]:
                L.append(f"| {res} | {u['used']} | {u['available']} | {100.0 * u['used'] / u['available']:.1f} |")
    for b in builds:
        L += ["", f"## Timing, {b['mhz']} MHz build", ""]
        if b["fmax"]:
            L += ["| Clock | Achieved (MHz) | Constraint (MHz) | Met |", "|---|---|---|---|"]
            for k, v in sorted(b["fmax"].items()):
                L.append(f"| `{k}` | {v['achieved']:.2f} | {v['constraint']:.2f} | {'yes' if v['achieved'] >= v['constraint'] else 'NO'} |")
            cp = critical_path(b)
            if cp:
                L += ["", "Critical path:", ""] + cp
        else:
            L += ["No timing result. Last lines of nextpnr.log:", "", "```"] + b["log_tail"] + ["```"]
        if b["bit"]:
            h = hashlib.sha256(open(b["bit"], "rb").read()).hexdigest()
            L += ["", f"Bitstream `{os.path.basename(b['bit'])}`: {os.path.getsize(b['bit'])} bytes, sha256 `{h}`."]
    L += ["", "## What is in the bitstream", "",
          "- `governor_core`, all of it (default sizes: 8-entry capability tables on four points, 8-entry ticket store, "
          "4 meter slots), with a 1 us tick.",
          "- The SMBus target (`rtl/governor_rtl/smbus.py`), address 0x58.",
          "- The bench firmware stand-in (`hw/fpga/top.py`): four halt-path pins and a shift chain over SPI that drives "
          "every other firmware-side port of the core and reads its outputs back (`fw_chain.json`). It is how a host "
          "plays the firmware, and it keeps synthesis from pruning the parts of the core whose inputs would otherwise "
          "be tied off.",
          "- Not in it: Ibex, the crypto engines, SRAM macros, NVM, PCIe and SGMII PHYs (they come with the OpenTitan "
          "integration, docs/08).", "",
          "Bitstreams are build products and are not committed. Flash: `openFPGALoader -b ulx3s <file>.bit` (add `-f` "
          "to write the SPI flash).", ""]
    L += [NOTES.rstrip(), ""]
    L += ["## Toolchain", "", "| Package | Version |", "|---|---|"] + [f"| {k} | {v} |" for k, v in versions().items()]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"wrote {path}")
    return 0 if clean else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--met")
    ap.add_argument("--fallback", nargs="+")
    ap.add_argument("--write")
    ap.add_argument("--seed", default="1")
    ap.add_argument("dirs", nargs="*")
    a = ap.parse_args()
    if a.met:
        r = load(a.met)
        print(f"   {r['mhz']} MHz: Fmax {r['achieved']} MHz, {'met' if r['met'] else 'NOT met'}")
        return 0 if r["met"] else 1
    if a.fallback:
        r = load(a.fallback[0])
        cands = sorted((int(c) for c in a.fallback[1:]), reverse=True)
        ach = r["achieved"] or 0
        pick = next((c for c in cands if c <= 0.95 * ach), cands[-1])
        print(pick)
        return 0
    return write(a.write, a.seed, a.dirs)


if __name__ == "__main__":
    sys.exit(main())
