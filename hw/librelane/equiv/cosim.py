"""Lock-step co-simulation: RTL governor_core vs a sky130 gate netlist of it.

Both copies get the same pseudo-random inputs every clock (reset held for the first cycles,
then pulsed now and then). Every output bit of the netlist must equal the RTL's on every cycle
after the first reset, and must never be X or Z. Any difference stops the run and fails it.

Usage: python3 cosim.py --rtl rtl/gen/governor_core.v --netlist NL.v --pdk-root PDK
                        [--cycles N] [--seed S] [--mutate K] [--work DIR]
--mutate K plants bug number K into a copy of the netlist first (swaps one 2-input cell for
another), to show that the check fails by assertion when the netlist is wrong.
"""
import argparse
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile

PORT_RE = re.compile(r"^\s*(input|output)\s*(?:\[(\d+):(\d+)\])?\s*\\?(\S+)\s*;", re.M)


def top_ports(rtl_text):
    start = rtl_text.index("module governor_core(")
    body = rtl_text[start:rtl_text.index("endmodule", start)]
    ports = []
    for d, hi, lo, name in PORT_RE.findall(body):
        w = int(hi) - int(lo) + 1 if hi else 1
        ports.append((d, w, name))
    return ports


SWAPS = [("sky130_fd_sc_hd__and2_", "sky130_fd_sc_hd__or2_"),
         ("sky130_fd_sc_hd__or2_", "sky130_fd_sc_hd__and2_"),
         ("sky130_fd_sc_hd__xor2_", "sky130_fd_sc_hd__xnor2_"),
         ("sky130_fd_sc_hd__nand2_", "sky130_fd_sc_hd__nor2_")]


def mutate(nl_text, k):
    """Bug k: replace the (k // len(SWAPS))-th instance of cell type SWAPS[k % len(SWAPS)][0]."""
    a, b = SWAPS[k % len(SWAPS)]
    hits = [m.start() for m in re.finditer(re.escape(a), nl_text)]
    if not hits:
        raise SystemExit(f"mutation {k}: no {a} cells in netlist")
    pos = hits[(k // len(SWAPS) * 7919) % len(hits)]
    end = nl_text.index(" ", pos)
    old = nl_text[pos:end]
    new = b + old[len(a):]
    return nl_text[:pos] + new + nl_text[end:], f"{old} -> {new} at byte {pos}"


def testbench(ports, cycles, seed):
    ins = [(w, n) for d, w, n in ports if d == "input" and n not in ("clk", "rst")]
    outs = [(w, n) for d, w, n in ports if d == "output"]
    L = []
    L.append("`timescale 1ns/1ps")
    L.append("module tb;")
    L.append("  reg clk = 0; reg rst = 1; integer cyc; integer errs = 0; integer seed = %d;" % seed)
    for w, n in ins:
        L.append(f"  reg [{w - 1}:0] i_{n};")
    for w, n in outs:
        L.append(f"  wire [{w - 1}:0] g_{n}, n_{n};")
        L.append(f"  reg [{w - 1}:0] s1_{n} = 0, s0_{n} = 0;")

    def conns(prefix):
        c = [".clk(clk)", ".rst(rst)"] + [f".{n}(i_{n})" for _, n in ins]
        c += [f".{n}({prefix}_{n})" for _, n in outs]
        return ", ".join(c)

    L.append(f"  governor_core_rtl gold ({conns('g')});")
    L.append(f"  governor_core gate ({conns('n')});")
    L.append("  task randomize; begin")
    for w, n in ins:
        words = (w + 31) // 32
        expr = "{" + ", ".join(["$random(seed)"] * words) + "}"
        L.append(f"    i_{n} = {expr};")
    L.append("  end endtask")
    L.append("  always #10 clk = ~clk;")
    L.append("  initial begin")
    L.append("    randomize;")
    L.append(f"    for (cyc = 0; cyc < {cycles}; cyc = cyc + 1) begin")
    L.append("      @(negedge clk);")
    L.append("      if (cyc >= 4) begin")
    for w, n in outs:
        L.append(f"        if (n_{n} !== g_{n}) begin errs = errs + 1; "
                 f"if (errs <= 10) $display(\"MISMATCH cycle %0d {n}: rtl=%h gate=%h\", cyc, g_{n}, n_{n}); end")
    for w, n in outs:
        L.append(f"        s1_{n} = s1_{n} | g_{n}; s0_{n} = s0_{n} | ~g_{n};")
    L.append("        if (errs > 0) begin $display(\"COSIM FAIL errors=%0d by cycle %0d\", errs, cyc); $finish; end")
    L.append("      end")
    L.append("      randomize;")
    L.append("      rst = (cyc < 3) || (($random(seed) & 255) == 0);")
    L.append("    end")
    tog = " + ".join(f"$countones(s1_{n} & s0_{n})" for _, n in outs)
    L.append(f"    $display(\"COSIM PASS cycles=%0d output_bits={sum(w for w, _ in outs)} "
             f"output_bits_seen_at_0_and_1=%0d\", cyc, {tog});")
    L.append("    $finish;")
    L.append("  end")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtl", required=True)
    ap.add_argument("--netlist", required=True)
    ap.add_argument("--pdk-root", required=True)
    ap.add_argument("--cycles", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--mutate", type=int)
    ap.add_argument("--work")
    a = ap.parse_args()
    work = pathlib.Path(a.work or tempfile.mkdtemp(prefix="cosim-"))
    work.mkdir(parents=True, exist_ok=True)
    rtl = pathlib.Path(a.rtl).read_text()
    gold = rtl.replace("module governor_core(", "module governor_core_rtl(", 1)
    # Yosys's Verilog backend puts a dummy "dump_module" reg in every always @* block so that the
    # block runs once at time zero. Icarus does not treat the "= 0" initialiser as an event, so a
    # block whose real inputs never change stays X forever. Toggle the dummy once to wake them.
    gold = re.sub(r"(reg (\\\$auto\$verilog_backend\.cc:\d+:dump_module\$\d+ ) = 0;)",
                  r"\1 initial #0.001 \2 = 1;", gold)
    (work / "gold.v").write_text(gold)
    nl = pathlib.Path(a.netlist).read_text()
    if a.mutate is not None:
        nl, what = mutate(nl, a.mutate)
        print(f"planted bug {a.mutate}: {what}")
    (work / "gate.v").write_text(nl)
    (work / "tb.v").write_text(testbench(top_ports(rtl), a.cycles, a.seed))
    cells = pathlib.Path(a.pdk_root) / "sky130A/libs.ref/sky130_fd_sc_hd/verilog"
    cmd = ["iverilog", "-g2012", "-DFUNCTIONAL", "-DUNIT_DELAY=#0", "-o", str(work / "sim"),
           str(cells / "primitives.v"), str(cells / "sky130_fd_sc_hd.v"),
           str(work / "gold.v"), str(work / "gate.v"), str(work / "tb.v")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        print("COSIM ERROR: iverilog failed to compile (this is a tool error, not a result)")
        return 2
    r = subprocess.run(["vvp", "-n", str(work / "sim")], capture_output=True, text=True)
    out = r.stdout
    print("\n".join(l for l in out.splitlines() if l.startswith(("MISMATCH", "COSIM"))))
    if a.work is None:
        shutil.rmtree(work, ignore_errors=True)
    if "COSIM PASS" in out:
        return 0
    if "COSIM FAIL" in out:
        return 1
    print(out[-2000:], r.stderr[-2000:])
    print("COSIM ERROR: simulation ended without a verdict")
    return 2


if __name__ == "__main__":
    sys.exit(main())
