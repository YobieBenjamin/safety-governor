# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""WAVE-FORMAL-PROOFS-ON-VERILOG: prove the chip's properties on the generated Verilog, then prove the proofs can fail.

    python -m rtl.formal          # every block that has a property file; exit 1 on anything that does not hold
    python -m rtl.formal meter    # only the blocks named (any number)

For each block: yosys reads rtl/gen/<block>.v and rtl/formal/<block>.sv, a bounded check runs to DEPTH cycles,
then k-induction at the same depth, which, when it passes, makes every assertion hold in every reachable state.
The same proof is then repeated with every other SMT solver this machine has (yices, boolector), so a solver bug
cannot carry a result alone. Then each mutant (a one-line change to the block's Amaranth source, a bug on purpose)
is regenerated and must FAIL the same properties. A property that passes on the mutant proves nothing about that line.

Blocks may add, in rtl/formal/blocks_*.py, extra checks (miters on the full-size core), a randomized simulation
against a reference model written from the spec, and a parameterized build for blocks too big to prove at full size.

Tools: yowasp-yosys (yosys and yosys-smtbmc as Python wheels) and z3, all pip-installed by ".[dev]",
so this runs the same on a Mac, on Linux and in CI with no system packages. yowasp-boolector (portable) and
yices-solver (Linux x86-64 only) are the second and third solvers; a missing one is reported, not hidden.
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
        ("CLEAR outranks tamper again (CONFORMANCE-CLEAR-BEATS-TAMPER)",
         "with m.If(self.tamper):", "with m.If(self.tamper & ~(self.clear & (self.state != HALTED_INITIAL))):"),
        ("RUN entered on a stale loop_lost (RTL-CORE-HALTS-AFTER-REACHING-RUN)",
         "with m.If(self.loop_sense & ~self.loop_lost):", "with m.If(self.loop_sense):"),
        ("a halt command is ignored once throttled",
         "with m.Elif(self.cmd_halt):", "with m.Elif(self.cmd_halt & (self.state != THROTTLE)):"),
        # Yobie's calls, 23 October 2026: HALT in SAFE opens the loop; EXCLUDE; NO_FIRST_HEARTBEAT
        ("a HALT to a chip in SAFE leaves the loop closed (the old behaviour, CONFORMANCE-HALT-TO-SAFE-CHIP)",
         "            m.d.sync += self.switch_open.eq(1)\n        with m.Elif(self.cmd_halt):",
         "            pass\n        with m.Elif(self.cmd_halt):"),
        ("a HALT to a chip in SAFE drops it to HALT and powers the slot (govsim's old CONFORMANCE-HALT-TO-SAFE-CHIP)",
         "with m.Elif(self.cmd_halt & (self.state == SAFE)):", "with m.Elif(self.cmd_halt & (self.state == SAFE) & 0):"),
        ("EXCLUDE closes the loop of a chip halted by loop loss, a command or tamper",
         "with m.Elif(self.cmd_exclude & (self.state == HALTED_INITIAL) & (self.cause == C_NONE)):",
         "with m.Elif(self.cmd_exclude):"),
        ("an excluded chip's slot gets power (EXCLUDE moves it to the HALT rung)",
         "m.d.sync += [self.switch_open.eq(0), self.excluded.eq(1)]",
         "m.d.sync += [self.switch_open.eq(0), self.excluded.eq(1), self.state.eq(HALT)]"),
        ("an excluded chip runs without a heartbeat",
         "with m.Elif((self.state == HALTED_INITIAL) & (self.cause == C_NONE) & self.hb_ok):",
         "with m.Elif((self.state == HALTED_INITIAL) & (self.cause == C_NONE) & (self.hb_ok | self.excluded)):"),
        ("a tamper leaves the exclusion standing",
         "with m.If(self.tamper | self.cmd_halt):", "with m.If(self.cmd_halt):"),
        ("the boot alarm is raised after the chip was armed",
         "self.no_first_hb.eq(~self.hb_seen & (self.boot_timer >= self.t_boot))", "self.no_first_hb.eq(self.boot_timer >= self.t_boot)"),
        ("the boot window never runs out (the timer does not count)",
         "m.d.sync += self.boot_timer.eq(self.boot_timer + 1)", "m.d.sync += self.boot_timer.eq(self.boot_timer)"),
        ("arming records the first heartbeat only if it also enters RUN (the alarm can fire on an armed chip)",
         "self.switch_open.eq(0), self.hb_seen.eq(1), self.excluded.eq(0)",
         "self.switch_open.eq(0), self.hb_seen.eq(self.hb_seen | (self.loop_sense & ~self.loop_lost)), self.excluded.eq(0)"),
    ]),
}
OPTIONS: dict = {}

# blocks proven in other files (one file per work stream, so parallel branches do not collide here)
try:
    from .blocks_b import BLOCKS_B, OPTIONS_B
    BLOCKS.update(BLOCKS_B)
    OPTIONS.update(OPTIONS_B)
except ImportError as e:                                   # pragma: no cover - only when the file is absent
    if "blocks_b" not in str(e):
        raise

try:                                     # blocks added by the FPGA push (the SMBus target); absent on older trees
    from rtl.formal.blocks_fpga import BLOCKS_FPGA
except ImportError:
    BLOCKS_FPGA = {}
BLOCKS.update(BLOCKS_FPGA)

# the second set of blocks (mailbox, cap_table, ticket_store, epoch_reg, monotonic_counter, lifecycle) lives in its own
# file so two people can extend WAVE-FORMAL-PROOFS-ON-VERILOG at once; CHECKS_A are its extra, independent checks (a second solver, a random
# simulation against a reference model). Missing file, missing blocks: the halt sequencer still runs.
try:
    from .blocks_a import BLOCKS_A, CHECKS_A, DEPTH_A
except ImportError:
    BLOCKS_A, CHECKS_A, DEPTH_A = {}, [], {}
BLOCKS = {**BLOCKS, **BLOCKS_A}


def tool(name: str) -> str:
    here = os.path.join(os.path.dirname(sys.executable), name)
    return here if os.path.exists(here) else (shutil.which(name) or sys.exit(f"{name} not found: pip install -e '.[dev]'"))


_SOLVERS: list | None = None


def solvers() -> list:
    """The SMT solvers yosys-smtbmc can reach here, z3 first. Boolector is the portable yowasp wheel, run through a
    two-line shim named 'boolector' because smtbmc calls it by that name."""
    global _SOLVERS
    if _SOLVERS is None:
        _SOLVERS = ["z3"]
        venv = os.path.dirname(sys.executable)
        if shutil.which("yices-smt2", path=venv + os.pathsep + os.environ.get("PATH", "")):
            _SOLVERS.append("yices")
        bl = shutil.which("yowasp-boolector", path=venv + os.pathsep + os.environ.get("PATH", ""))
        if bl and os.name == "posix":
            shim = os.path.join(tempfile.gettempdir(), f"rtl-formal-shim-{os.getuid()}")
            os.makedirs(shim, exist_ok=True)
            with open(os.path.join(shim, "boolector"), "w") as f:
                f.write(f'#!/bin/sh\nexec "{bl}" "$@"\n')
            os.chmod(os.path.join(shim, "boolector"), 0o755)
            os.environ["PATH"] = shim + os.pathsep + os.environ.get("PATH", "")
            # the wheel compiles itself on first use and prints a banner smtbmc would misread; get that over with
            subprocess.run([bl, "--version"], capture_output=True, text=True)
            _SOLVERS.append("boolector")
        os.environ["PATH"] = venv + os.pathsep + os.environ.get("PATH", "")
    return _SOLVERS


# Registered name: WAVE-FORMAL-PROOFS-ON-VERILOG (old ID L7 is kept because code matches on it)
SPLICE = "// L7-SPLICE"


def smt(work: str, top: str, yosys_extra: str = "") -> str | None:
    """yosys: dut.v + props.sv in work -> design.smt2. Returns an error text, or None.

    A props file that starts with SPLICE is pasted into the block's own module, just before endmodule, so its
    assertions can name the block's internal registers (yosys has no hierarchical references); the block's logic is
    untouched. Any yosys warning is refused: a misspelt signal name becomes a free wire, a variable driven from two
    blocks becomes a conflict, and an assertion over either proves nothing (found by the WAVE-FORMAL-PROOFS-ON-VERILOG group A work)."""
    text = open(os.path.join(work, "props.sv"), encoding="utf-8").read()
    if text.startswith(SPLICE):
        dut = open(os.path.join(work, "dut.v"), encoding="utf-8").read()
        top = dut.split("module ", 1)[1].split("(", 1)[0].strip()
        at = dut.rfind("endmodule")
        with open(os.path.join(work, "props.sv"), "w", encoding="utf-8") as f:
            f.write(dut[:at] + text + "\n" + dut[at:])
        read = "read_verilog -formal -sv props.sv;"
    else:
        read = "read_verilog -sv dut.v; read_verilog -formal -sv props.sv;"
    y = subprocess.run([tool("yowasp-yosys"), "-q", "-p",
                        f"{read} {yosys_extra} prep -top {top}; "
                        f"async2sync; dffunmap; write_smt2 -wires design.smt2"], capture_output=True, text=True, cwd=work)
    if y.returncode:
        return "TOOL ERROR (yosys): " + (y.stderr or y.stdout)[-800:]
    if "Warning:" in y.stderr:
        return "TOOL ERROR (yosys warning): " + y.stderr.strip()[:600]
    return None


def bmc_and_induction(work: str, depth: int, solver: str, smt2: str = "design.smt2") -> tuple[bool, str]:
    for mode in ([], ["-i"]):
        r = subprocess.run([tool("yowasp-yosys-smtbmc"), "-s", solver, *mode, "-t", str(depth), smt2],
                           capture_output=True, text=True, cwd=work)
        if "Status: PASSED" not in r.stdout:
            failed = [l.split("Assert failed in ")[-1] for l in r.stdout.splitlines() if "Assert failed" in l]
            if not failed:
                return False, f"TOOL ERROR (smtbmc, {solver}): " + (r.stderr or r.stdout)[-400:]
            return False, ("induction" if mode else "bounded check") + f" failed ({solver}): " + ", ".join(failed)
    return True, "ok"


def prove(verilog_path: str, props: str, work: str, depth: int = DEPTH, all_solvers: bool = False,
          yosys_extra: str = "", props_text: str | None = None, solver: str = "z3") -> tuple[bool, str]:
    # yowasp's yosys runs in WebAssembly and sees only the folder it starts in, so everything is copied there
    top = os.path.splitext(os.path.basename(props))[0] + "_props"
    if os.path.abspath(verilog_path) != os.path.join(work, "dut.v"):
        shutil.copy(verilog_path, os.path.join(work, "dut.v"))
    with open(os.path.join(work, "props.sv"), "w", encoding="utf-8") as f:
        f.write(props_text if props_text is not None else open(props, encoding="utf-8").read())
    err = smt(work, top, yosys_extra)
    if err:
        return False, err
    first = solver if solver in solvers() else "z3"
    order = [first] + ([s for s in solvers() if s != first] if all_solvers else [])
    for s in order:
        ok, why = bmc_and_induction(work, depth, s)
        if not ok:
            return False, why
    return True, f"bounded to {depth} cycles and k-induction: every reachable state ({', '.join(order)})"


def load_block(src_file: str, cls: str, old: str | None = None, new: str | None = None, kwargs: dict | None = None):
    """Instantiate a block from its Amaranth source, optionally with one text change (a mutant). The source runs as a
    module of rtl.governor_rtl, so the core's relative imports resolve to the real (unmutated) sub-blocks."""
    src = open(os.path.join(RTL, "governor_rtl", src_file), encoding="utf-8").read()
    if old is not None:
        if src.count(old) != 1:
            sys.exit(f"mutant text not found exactly once in {src_file}: {old!r} (the source moved; update BLOCKS)")
        src = src.replace(old, new)
    ns: dict = {"__name__": "rtl.governor_rtl._mutant", "__package__": "rtl.governor_rtl"}
    exec(compile(src, src_file + (" (mutant)" if old is not None else ""), "exec"), ns)
    return ns[cls](**(kwargs or {}))


def mutant_verilog(src_file: str, cls: str, old: str, new: str, out: str, name: str) -> None:
    dut = load_block(src_file, cls, old, new)
    ports = [v for v in vars(dut).values() if isinstance(v, Signal)]
    with open(out, "w", encoding="utf-8") as f:
        f.write(verilog.convert(dut, name=name, ports=ports, emit_src=False))


def check_block(block: str, src_file: str, cls: str, work: str, mutant: tuple | None, all_solvers: bool) -> tuple[bool, str]:
    """The block's properties (and any extra checks) on the checked-in Verilog, or on one mutant of it."""
    opt = OPTIONS.get(block, {})
    props = os.path.join(HERE, block + ".sv")
    mv = os.path.join(work, "dut.v")
    if "verilog" in opt:                                     # a parameterized build (the core)
        opt["verilog"](mv, mutant)
        src_v = mv
    elif mutant is None:
        src_v = os.path.join(GEN, block + ".v")
    else:
        mutant_verilog(src_file, cls, mutant[1], mutant[2], mv, block)
        src_v = mv
    props_text = opt["props_text"](open(src_v, encoding="utf-8").read()) if "props_text" in opt else None
    # group A's blocks run one solver here; their second solver is one of CHECKS_A, which says NOT RUN where it times out
    ok, why = prove(src_v, props, work, depth=opt.get("depth", DEPTH_A.get(block, DEPTH)),
                    all_solvers=all_solvers and block not in BLOCKS_A,
                    yosys_extra=opt.get("yosys_extra", ""), props_text=props_text, solver=opt.get("solver", "z3"))
    notes = [why]
    for label, fn in opt.get("checks", []):
        sub = os.path.join(work, label.replace(" ", "_"))
        os.makedirs(sub, exist_ok=True)
        c_ok, c_why = fn(sub, mutant, all_solvers)
        notes.append(f"{label}: {c_why}")
        if not c_ok:
            ok = False
            if "TOOL ERROR" in c_why and "TOOL ERROR" not in why:
                notes[0] = c_why                              # never let a tool error pass as a catch
    return ok, "; ".join(notes)


def main(argv: list) -> int:
    sys.stdout.reconfigure(line_buffering=True)              # a long run shows its progress line by line
    bad = 0
    names = [a for a in argv if not a.startswith("-")] or list(BLOCKS)
    print("  solvers here: " + ", ".join(solvers()) + ("" if len(solvers()) > 1 else " (no second solver installed)"))
    for block in names:
        src_file, cls, mutants = BLOCKS[block]
        opt = OPTIONS.get(block, {})
        with tempfile.TemporaryDirectory() as work:
            ok, why = check_block(block, src_file, cls, work, None, all_solvers=True)
            print(f"  {'PROVED' if ok else 'FAILED'}  {block}: {why}")
            bad += not ok
            if "sim" in opt:
                s_ok, s_why = opt["sim"]()
                print(f"  {'SIM-OK' if s_ok else 'SIM-FAILED'}  {block}: {s_why}")
                bad += not s_ok
            for desc, old, new in mutants:
                with tempfile.TemporaryDirectory() as mwork:
                    passed, why = check_block(block, src_file, cls, mwork, (desc, old, new), all_solvers=False)
                # a mutant counts as caught only when an assertion fails; a tool error proves nothing. For group A's
                # blocks the rule is stricter: the bounded check must fail, on a concrete trace from reset, because an
                # induction failure alone may start from a state the mutant can never reach. halt_seq keeps the old
                # rule: its "never escalates to SAFE" mutant needs 300,000 ticks, which only induction reaches.
                if block in BLOCKS_A:
                    caught = why.startswith("bounded check failed")
                else:
                    caught = not passed and "TOOL ERROR" not in why
                extra = ""
                if "sim_mutant" in opt:                      # information only: does the simulation see it too?
                    try:
                        s_ok, _ = opt["sim_mutant"](lambda _o=old, _n=new, **kw: load_block(src_file, cls, _o, _n, kw))
                        extra = " [simulation: " + ("missed it" if s_ok else "caught it too") + "]"
                    except Exception as e:                   # e.g. the mutant drives a port the bench sets
                        extra = f" [simulation: could not run it, {type(e).__name__}]"
                print(f"  {'caught' if caught else 'MISSED'}  {block} mutant: {desc}" + ("" if caught else f" ({why})") + extra)
                bad += not caught
        for label, fn in opt.get("facts", []):
            f_ok, f_why = fn()
            print(f"  {'FACT' if f_ok else 'FACT-FAILED'}  {block}: {label}: {f_why}")
            bad += not f_ok
    for check in CHECKS_A:
        for ok, line in check(prove, names):
            print(f"  {line}")
            bad += not ok
    print("WAVE-FORMAL-PROOFS-ON-VERILOG: every property proven on the Verilog, every mutant caught" if not bad else f"WAVE-FORMAL-PROOFS-ON-VERILOG: {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
