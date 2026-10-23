#!/usr/bin/env python3
"""Formal jobs on the generated Verilog (rtl/gen/*.v). Used by ``make formal``.

    python3 rtl/formal/run_formal.py            # every block, then the netlist equivalence
    python3 rtl/formal/run_formal.py mailbox    # one block
    python3 rtl/formal/run_formal.py equiv      # only the netlist equivalence

For each block the properties in ``rtl/formal/<block>.svh`` are injected in front of the last
``endmodule`` of the generated file (so they can read the block's registers; ``rtl/gen`` is never
edited), and SymbiYosys runs ``mode prove`` (bounded model check, then k-induction: an unbounded
proof when the induction closes).

Outcomes are printed in four classes so a green ``make formal`` is never mistaken for a proof that
did not run, and an expected counterexample is never mistaken for a pass:

    PROVED  <job>     a property held (the ``prove`` task, ``mode prove``)
    GAP OK  <job>     a task marked ``expect fail`` found its counterexample: the RTL gap it
                     documents is real, and the task did its job. This is not a PASS.
    SKIP    <job>     the tool the job needs is not on PATH; it was not run. Skips do not fail
                     the command, but a SKIP is not a PROVED -- it says nothing was checked.
    FAIL    <job>     a property that should hold was broken, or an expected counterexample was
                     not found (the documented gap was not reproduced).

The program's container has ``sby``, ``yosys`` and ``z3``; where they are absent (as in a plain
checkout) the jobs are skipped and the command still exits 0, with a banner saying so -- the
properties are checked for real when the command is run in the container.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "..", "gen")
BUILD = os.path.join(HERE, "build")

# block -> tasks: name -> (mode, depth, defines, expected).
# expected is "pass" for a property that must hold, "fail" for a task that documents an RTL gap and
# is written to produce the counterexample (SymbiYosys ``expect fail``).
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

# tools each kind of job needs; smtbmc z3 runs under sby, the equivalence runs under yosys
NEEDS_BLOCK = ("sby", "z3")
NEEDS_EQUIV = ("yosys",)


def inject(block: str, dest: str) -> None:
    with open(os.path.join(GEN, block + ".v")) as f:
        lines = f.read().splitlines()
    with open(os.path.join(HERE, block + ".svh")) as f:
        props = f.read()
    last = max(i for i, line in enumerate(lines) if line.startswith("endmodule"))
    out = lines[:last] + ["// ---- injected by rtl/formal/run_formal.py ----", props] + lines[last:]
    with open(dest, "w") as f:
        f.write("\n".join(out) + "\n")


def _tail(p: subprocess.CompletedProcess) -> str:
    return "\n".join((p.stdout + p.stderr).strip().splitlines()[-12:])


def run_block(block: str, missing: list[str]) -> list[tuple[str, str, str]]:
    tasks = BLOCKS[block]
    if any(t in missing for t in NEEDS_BLOCK):
        return [(f"{block}:{t}", "skip", f"{', '.join(t for t in NEEDS_BLOCK if t in missing)} not on PATH; not run")
                for t in tasks]
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
        held = p.returncode == 0
        if expected == "fail":
            # the task is written to find the counterexample; a clean run means the gap is real
            status = "gap" if held else "fail"
            note = ("expected counterexample found: " + _tail(p).splitlines()[-1]
                    if held else
                    "expected counterexample not found -- the documented gap was not reproduced")
        else:
            status = "proved" if held else "fail"
            note = "" if held else _tail(p)
        results.append((f"{block}:{t}", status, note))
    return results


def run_equiv(block: str, missing: list[str]) -> tuple[str, str, str]:
    """rtl/gen/<block>.v against the same design synthesized to a gate netlist (yosys synth + abc).

    This is the in-flow Yosys gate netlist, not the LibreLane netlist: ``make gds`` needs Docker
    and the PDK and no netlist from it is checked in. It proves the abc-mapped netlist is equivalent
    to the generated Verilog; comparing the real ``governor_core`` netlist would need its cell models.
    """
    if any(t in missing for t in NEEDS_EQUIV):
        return (f"equiv:{block}", "skip", f"{', '.join(missing)} not on PATH; not run")
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
    held = p.returncode == 0
    return (f"equiv:{block}",
            "proved" if held else "fail",
            "" if held else _tail(p))


def main(argv: list[str]) -> int:
    missing = [t for t in ("sby", "yosys", "z3") if shutil.which(t) is None]
    if missing:
        print(f"SKIP    tooling absent: {', '.join(missing)} not on PATH "
              f"(the program's container has sby/yosys-smtbmc/z3). No property was checked; "
              f"run `make formal` in the container to run them.")
    want = argv or list(BLOCKS) + ["equiv"]
    results: list[tuple[str, str, str]] = []
    for w in want:
        if w == "equiv":
            results += [run_equiv(b, missing) for b in EQUIV]
        elif w in BLOCKS:
            results += run_block(w, missing)
        else:
            print(f"unknown job {w}")
            return 2
    labels = {"proved": "PROVED  ", "gap": "GAP OK  ", "skip": "SKIP    ", "fail": "FAIL    "}
    for name, status, note in results:
        line = labels[status] + name
        if status in ("gap", "fail") and note:
            line += "  " + " ".join(note.split())
        print(line)
    for name, status, note in results:
        if status == "fail" and note:
            print("      " + note.replace("\n", "\n      "))
    fails = [r for r in results if r[1] == "fail"]
    skipped = sum(1 for r in results if r[1] == "skip")
    if skipped:
        print(f"SKIP    {skipped} job(s) not run (tools absent). A SKIP is not a PROVED; "
              f"run in the container to check the properties.")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
