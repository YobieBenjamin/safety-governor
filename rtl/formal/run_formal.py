#!/usr/bin/env python3
"""Formal jobs on the generated Verilog (rtl/gen/*.v). Used by ``make formal``.

    python3 rtl/formal/run_formal.py            # every block, then the netlist equivalence
    python3 rtl/formal/run_formal.py mailbox    # one block
    python3 rtl/formal/run_formal.py equiv      # only the netlist equivalence

For each block the properties in ``rtl/formal/<block>.svh`` are injected in front of the last
``endmodule`` of the generated file (so they can read the block's registers; ``rtl/gen`` is never
edited), and SymbiYosys runs ``mode prove`` (bounded model check, then k-induction: an unbounded
proof when the induction closes). Tasks marked ``fail`` are expected to produce a counterexample;
they document a gap in the RTL and are reported as findings, not as passes.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "..", "gen")
BUILD = os.path.join(HERE, "build")

# block -> tasks: name -> (mode, depth, defines, expected)
BLOCKS = {
    "ticket_store": {"prove": ("prove", 6, [], "pass")},
    "epoch_reg": {"prove": ("prove", 4, [], "pass")},
    "halt_seq": {"prove": ("prove", 8, [], "pass")},
    "cap_table": {"prove": ("prove", 5, [], "pass")},
    "monotonic_counter": {"prove": ("prove", 4, [], "pass"), "wrap": ("bmc", 3, ["WRAP"], "fail")},
    "mailbox": {"prove": ("prove", 8, [], "pass"),
                "nolatch": ("bmc", 6, ["NOLATCH"], "fail"),
                "midhalt": ("bmc", 6, ["MIDHALT"], "fail")},
}
# blocks whose gate-level netlist is compared with the generated Verilog
EQUIV = ["ticket_store", "epoch_reg", "halt_seq", "cap_table", "monotonic_counter", "mailbox"]


def inject(block: str, dest: str) -> None:
    with open(os.path.join(GEN, block + ".v")) as f:
        lines = f.read().splitlines()
    with open(os.path.join(HERE, block + ".svh")) as f:
        props = f.read()
    last = max(i for i, line in enumerate(lines) if line.startswith("endmodule"))
    out = lines[:last] + ["// ---- injected by rtl/formal/run_formal.py ----", props] + lines[last:]
    with open(dest, "w") as f:
        f.write("\n".join(out) + "\n")


def run_block(block: str) -> list[tuple[str, bool, str]]:
    tasks = BLOCKS[block]
    d = os.path.join(BUILD, block)
    os.makedirs(d, exist_ok=True)
    inject(block, os.path.join(d, block + ".v"))
    sby = ["[tasks]"] + list(tasks) + ["", "[options]"]
    for t, (mode, depth, _defs, expected) in tasks.items():
        sby += [f"{t}: mode {mode}", f"{t}: depth {depth}"]
        if expected == "fail":
            sby.append(f"{t}: expect fail")
    sby += ["", "[engines]", "smtbmc z3", "", "[script]"]
    for t, (_m, _d, defs, _e) in tasks.items():
        flags = "".join(f" -D {x}" for x in defs)
        sby.append(f"{t}: read_verilog -formal -sv{flags} {block}.v")
    sby += [f"prep -top {block}", "", "[files]", f"{block}.v", ""]
    with open(os.path.join(d, block + ".sby"), "w") as f:
        f.write("\n".join(sby))
    results = []
    for t, (_m, _d, _defs, expected) in tasks.items():
        p = subprocess.run(["sby", "-f", f"{block}.sby", t], cwd=d, capture_output=True, text=True, timeout=3000)
        tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-12:])
        results.append((f"{block}:{t}", p.returncode == 0, tail if p.returncode else ("expected counterexample found" if expected == "fail" else "proved")))
    return results


def run_equiv(block: str) -> tuple[str, bool, str]:
    """rtl/gen/<block>.v against the same design synthesized to a gate netlist (yosys synth + abc)."""
    d = os.path.join(BUILD, "equiv")
    os.makedirs(d, exist_ok=True)
    src = os.path.abspath(os.path.join(GEN, block + ".v"))
    script = f"""
read_verilog -sv {src}
hierarchy -top {block}
proc
flatten
dffunmap
opt_clean
design -stash gold
read_verilog -sv {src}
hierarchy -top {block}
synth -flatten -top {block}
dffunmap
abc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX
opt_clean
tee -o {block}.gates.stat stat
write_verilog -noattr {block}.gates.v
design -stash gate
design -copy-from gold -as gold {block}
design -copy-from gate -as gate {block}
equiv_make gold gate equiv
hierarchy -top equiv
equiv_simple -seq 5
equiv_induct -seq 5
equiv_status -assert
"""
    path = os.path.join(d, block + ".ys")
    with open(path, "w") as f:
        f.write(script)
    p = subprocess.run(["yosys", "-q", "-l", block + ".log", block + ".ys"], cwd=d, capture_output=True, text=True, timeout=3000)
    tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-12:])
    return (f"equiv:{block}", p.returncode == 0, tail if p.returncode else "gate netlist equivalent to rtl/gen")


def main(argv: list[str]) -> int:
    for tool in ("sby", "yosys", "z3"):
        if shutil.which(tool) is None:
            print(f"FAIL  tool '{tool}' not found on PATH (the program's container has it)")
            return 1
    want = argv or list(BLOCKS) + ["equiv"]
    results: list[tuple[str, bool, str]] = []
    for w in want:
        if w == "equiv":
            results += [run_equiv(b) for b in EQUIV]
        elif w in BLOCKS:
            results += run_block(w)
        else:
            print(f"unknown job {w}")
            return 2
    for name, ok, note in results:
        print(("PASS  " if ok else "FAIL  ") + name + ("  " + note.splitlines()[0] if ok else ""))
        if not ok:
            print("      " + note.replace("\n", "\n      "))
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
