"""L7: prove the chip's properties on the generated Verilog, then prove the proofs can fail.

    python -m rtl.formal          # every block that has a property file; exit 1 on anything that does not hold

For each block: yosys reads rtl/gen/<block>.v and rtl/formal/<block>.sv, a bounded check runs to DEPTH cycles,
then k-induction at the same depth, which, when it passes, makes every assertion hold in every reachable state.
Then each mutant (a one-line change to the block's Amaranth source, a bug on purpose) is regenerated and must
FAIL the same properties. A property that passes on the mutant proves nothing about that line.

Tools: yowasp-yosys (yosys and yosys-smtbmc as Python wheels) and z3, all pip-installed by ".[dev]",
so this runs the same on a Mac, on Linux and in CI with no system packages.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

from amaranth import Signal
from amaranth.back import verilog

HERE = os.path.dirname(os.path.abspath(__file__))
RTL = os.path.dirname(HERE)
GEN = os.path.join(RTL, "gen")
DEPTH = 25

# block -> (Amaranth source file, class name, mutants as (description, old text, new text))
BLOCKS = {
    "halt_seq": ("halt.py", "HaltSeq", [
        ("a commanded halt leaves the loop switch closed",
         "self.cause.eq(C_COMMAND), self.switch_open.eq(1),", "self.cause.eq(C_COMMAND),"),
        ("tamper does not open the loop",
         "self.cause.eq(C_TAMPER), self.switch_open.eq(1)]", "self.cause.eq(C_TAMPER)]"),
        ("HALT never escalates to SAFE",
         "m.d.sync += [self.state.eq(SAFE), self.timer.eq(0)]", "m.d.sync += [self.state.eq(HALT), self.timer.eq(0)]"),
        ("the power brake releases in THROTTLE",
         "self.pwrbrk.eq(self.state != RUN),", "self.pwrbrk.eq((self.state != RUN) & (self.state != THROTTLE)),"),
        ("a halt command is ignored once throttled",
         "with m.Elif(self.cmd_halt & (self.state != SAFE)):", "with m.Elif(self.cmd_halt & (self.state != SAFE) & (self.state != THROTTLE)):"),
    ]),
}

try:                                     # blocks added by the FPGA push (the SMBus target); absent on older trees
    from rtl.formal.blocks_fpga import BLOCKS_FPGA
except ImportError:
    BLOCKS_FPGA = {}
BLOCKS.update(BLOCKS_FPGA)


def tool(name: str) -> str:
    here = os.path.join(os.path.dirname(sys.executable), name)
    return here if os.path.exists(here) else (shutil.which(name) or sys.exit(f"{name} not found: pip install -e '.[dev]'"))


def prove(verilog_path: str, props: str, work: str) -> tuple[bool, str]:
    # yowasp's yosys runs in WebAssembly and sees only the folder it starts in, so everything is copied there
    smt = "design.smt2"
    top = os.path.splitext(os.path.basename(props))[0] + "_props"
    if os.path.abspath(verilog_path) != os.path.join(work, "dut.v"):
        shutil.copy(verilog_path, os.path.join(work, "dut.v"))
    shutil.copy(props, os.path.join(work, "props.sv"))
    y = subprocess.run([tool("yowasp-yosys"), "-q", "-p",
                        f"read_verilog -sv dut.v; read_verilog -formal -sv props.sv; prep -top {top}; "
                        f"async2sync; dffunmap; write_smt2 -wires {smt}"], capture_output=True, text=True, cwd=work)
    if y.returncode:
        return False, "TOOL ERROR (yosys): " + (y.stderr or y.stdout)[-800:]
    for mode in ([], ["-i"]):
        r = subprocess.run([tool("yowasp-yosys-smtbmc"), "-s", "z3", *mode, "-t", str(DEPTH), smt],
                           capture_output=True, text=True, cwd=work)
        if "Status: PASSED" not in r.stdout:
            failed = [l.split("Assert failed in ")[-1] for l in r.stdout.splitlines() if "Assert failed" in l]
            if not failed:
                return False, "TOOL ERROR (smtbmc): " + (r.stderr or r.stdout)[-400:]
            return False, ("induction" if mode else "bounded check") + " failed: " + ", ".join(failed)
    return True, f"bounded to {DEPTH} cycles and k-induction: every reachable state"


def mutant_verilog(src_file: str, cls: str, old: str, new: str, out: str, name: str) -> None:
    src = open(os.path.join(RTL, "governor_rtl", src_file), encoding="utf-8").read()
    if src.count(old) != 1:
        sys.exit(f"mutant text not found exactly once in {src_file}: {old!r} (the source moved; update BLOCKS)")
    ns: dict = {"__name__": "mutant"}
    exec(compile(src.replace(old, new), src_file + " (mutant)", "exec"), ns)
    dut = ns[cls]()
    ports = [v for v in vars(dut).values() if isinstance(v, Signal)]
    with open(out, "w", encoding="utf-8") as f:
        f.write(verilog.convert(dut, name=name, ports=ports, emit_src=False))


def main() -> int:
    bad = 0
    for block, (src_file, cls, mutants) in BLOCKS.items():
        props = os.path.join(HERE, block + ".sv")
        with tempfile.TemporaryDirectory() as work:
            ok, why = prove(os.path.join(GEN, block + ".v"), props, work)
            print(f"  {'PROVED' if ok else 'FAILED'}  {block}: {why}")
            bad += not ok
            for desc, old, new in mutants:
                mv = os.path.join(work, "dut.v")
                mutant_verilog(src_file, cls, old, new, mv, block)
                passed, why = prove(mv, props, work)
                # a mutant counts as caught only when an assertion fails; a tool error proves nothing
                caught = not passed and "TOOL ERROR" not in why
                print(f"  {'caught' if caught else 'MISSED'}  {block} mutant: {desc}" + ("" if caught else f" ({why})"))
                bad += not caught
    print("L7: every property proven on the Verilog, every mutant caught" if not bad else f"L7: {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
