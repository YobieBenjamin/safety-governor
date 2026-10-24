# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""WAVE-FORMAL-PROOFS-ON-VERILOG, work stream b: heartbeat, meter, alarms, measure_reg, loop_io, governor_core.

Merged into rtl/formal/__main__.py's BLOCKS by a guarded import; same shape:
    block -> (Amaranth source file, class name, [(mutant description, old text, new text)])
OPTIONS_B adds, per block: the randomized simulation against a spec model (sim_b.py), a proof depth, and for the
core a parameterized build, full-size miter checks and recorded design facts (FINDINGS-b.md).

Every mutant is a security-relevant bug on purpose. Each must fail an assertion: of the block's properties, of an
extra check, or both. The simulation is also run on every mutant and its verdict printed for information.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess

from amaranth.back import verilog

from . import sim_b

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------------------------------------ the mutants
BLOCKS_B = {
    "heartbeat": ("heartbeat.py", "Heartbeat", [
        ("an expired timer revives itself with no heartbeat",
         "with m.If(self.hb_valid):", "with m.If(self.hb_valid | (self.remaining == 0)):"),
        ("the countdown stops at one and never expires",
         "with m.Elif(self.tick & (self.remaining != 0)):", "with m.Elif(self.tick & (self.remaining > 1)):"),
        ("a heartbeat buys twice the window it signed",
         "m.d.sync += self.remaining.eq(self.window)", "m.d.sync += self.remaining.eq(self.window << 1)"),
        ("expiry is hidden on every tick cycle",
         "m.d.comb += self.expired.eq(self.remaining == 0)", "m.d.comb += self.expired.eq((self.remaining == 0) & ~self.tick)"),
    ]),
    "meter": ("meter.py", "Meter", [
        ("the old wrapping add (the bug fixed on 23 October 2026)",
         "return Mux(s[len(a)], (1 << len(a)) - 1, s[:len(a)])", "return s[:len(a)]"),
        ("the host's read slot steers which slot is charged",
         "self.tokens[self.slot].eq(_sat_add(self.tokens[self.slot], self.add_tokens))",
         "self.tokens[self.rd_slot].eq(_sat_add(self.tokens[self.rd_slot], self.add_tokens))"),
        ("a host write zeroes the cycle counter it is reading",
         "        m.d.comb += [self.rd_tokens.eq(",
         "        with m.If(self.host_wr):\n            m.d.sync += self.cycles[self.rd_slot].eq(0)\n        m.d.comb += [self.rd_tokens.eq("),
        ("a host write is not flagged",
         "self.host_wr_refused.eq(self.host_wr)]", "self.host_wr_refused.eq(0)]"),
        ("bytes out are overwritten instead of added",
         "self.bout[self.slot].eq(_sat_add(self.bout[self.slot], self.add_out))", "self.bout[self.slot].eq(self.add_out)"),
    ]),
    "alarms": ("alarms.py", "Alarms", [
        ("an alarm clears without authorization",
         "cleared.eq(self.alarms & ~(self.clear_mask & self.clear_authorized.replicate(len(self.alarms))))",
         "cleared.eq(self.alarms & ~self.clear_mask)"),
        ("an authorized clear of one alarm wipes them all",
         "~(self.clear_mask & self.clear_authorized.replicate(len(self.alarms)))",
         "~self.clear_authorized.replicate(len(self.alarms))"),
        ("a clear racing a fresh alarm swallows it",
         "m.d.sync += self.alarms.eq(cleared | raise_)", "m.d.sync += self.alarms.eq(cleared | (raise_ & ~self.clear_mask))"),
        ("the summary bit sees only alarm 0",
         "self.any.eq(self.alarms != 0)", "self.any.eq(self.alarms[0])"),
        ("an unauthorized clear attempt is not flagged",
         "self.clear_refused.eq((self.clear_mask != 0) & ~self.clear_authorized)", "self.clear_refused.eq(0)"),
    ]),
    "measure_reg": ("measure_reg.py", "MeasureReg", [
        ("an engine answer nobody asked for is latched",
         '            with m.State("IDLE"):\n                with m.If(self.extend):',
         '            with m.State("IDLE"):\n                with m.If(self.hash_done):\n'
         '                    m.d.sync += self.value.eq(self.hash_out)\n                with m.If(self.extend):'),
        ("extend writes the data straight into the register",
         "                    m.d.comb += self.hash_req.eq(1)",
         "                    m.d.comb += self.hash_req.eq(1)\n                    m.d.sync += self.value.eq(self.data)"),
        ("the old value drops out of the hash input (no chain)",
         "Cat(self.data, self.value)", "Cat(self.data, self.data)"),
        ("the register latches the engine bus before the engine answers",
         "                with m.If(self.hash_done):\n                    m.d.sync += self.value.eq(self.hash_out)",
         "                m.d.sync += self.value.eq(self.hash_out)\n                with m.If(self.hash_done):"),
        ("a second extend while busy re-requests the engine",
         "                m.d.comb += self.busy.eq(1)", "                m.d.comb += [self.busy.eq(1), self.hash_req.eq(self.extend)]"),
    ]),
    "loop_io": ("halt_loop.py", "LoopIO", [
        ("the pad opens only while current flows",
         "self.loop_out_open.eq(self.switch_open)", "self.loop_out_open.eq(self.switch_open & self.loop_sense)"),
        ("the debounce forgets between samples, so a loss is never declared",
         "        m.d.comb += self.loop_lost.eq(self.count >= self.debounce)",
         "        with m.Else():\n            m.d.sync += self.count.eq(0)\n        m.d.comb += self.loop_lost.eq(self.count >= self.debounce)"),
        ("the threshold is one past where the counter stops: never declared",
         "self.loop_lost.eq(self.count >= self.debounce)", "self.loop_lost.eq(self.count > self.debounce)"),
        ("a third low sample clears the loss",
         "                    m.d.sync += self.count.eq(self.count + 1)",
         "                    m.d.sync += self.count.eq(self.count + 1)\n                with m.Else():\n"
         "                    m.d.sync += self.count.eq(0)"),
        ("the debounce counts current instead of its absence",
         "with m.If(~self.loop_sense):", "with m.If(self.loop_sense):"),
    ]),
    "governor_core": ("top.py", "GovernorCore", [
        ("the old millisecond tap on the monotonic counter (the bug fixed on 23 October 2026)",
         "self.tick_ms.eq(self.tick & (self.ms_div == (1 << self.ms_shift) - 1)),",
         "self.tick_ms.eq(self.tick & (self.mono.value[:self.ms_shift] == (1 << self.ms_shift) - 1)),"),
        ("reading MBOX_STATUS restarts the millisecond (a CSR read with a side effect)",
         "                m.d.comb += self.csr_rdata.eq(self.mbox.status)",
         "                m.d.comb += self.csr_rdata.eq(self.mbox.status)\n                m.d.sync += self.ms_div.eq(0)"),
        ("the doorbell masks a heartbeat expiry that cycle",
         "self.halt.hb_expired.eq(self.hb.expired),", "self.halt.hb_expired.eq(self.hb.expired & ~self.doorbell),"),
        ("the brake pad releases whenever the heartbeat is live",
         "self.pwrbrk_n.eq(~self.halt.pwrbrk),", "self.pwrbrk_n.eq(~self.halt.pwrbrk | self.halt.hb_ok),"),
        ("SAFE closes the loop pad again",
         "self.loop.switch_open.eq(self.halt.switch_open),", "self.loop.switch_open.eq(self.halt.switch_open & (self.halt.state != 4)),"),
        ("a loop loss is acted on only once the heartbeat has also expired",
         "self.halt.loop_lost.eq(self.loop.loop_lost),", "self.halt.loop_lost.eq(self.loop.loop_lost & self.hb.expired),"),
        # Yobie's calls, 23 October 2026: the operator signals
        ("firmware can raise NO_FIRST_HEARTBEAT and the hardware's raise never lands",
         "HW_ALARMS = (1 << ALARM_NO_FIRST_HEARTBEAT) | (1 << ALARM_EXCLUDED)", "HW_ALARMS = (1 << ALARM_EXCLUDED)"),
        ("the boot alarm bit follows the wrong signal (raised once armed)",
         "(self.halt.no_first_hb << ALARM_NO_FIRST_HEARTBEAT)", "(self.halt.hb_seen << ALARM_NO_FIRST_HEARTBEAT)"),
        ("CAUSE hides the wait for the first heartbeat",
         "Cat(self.halt.cause, self.halt.no_first_hb, self.halt.excluded,", "Cat(self.halt.cause, Const(0, 1), self.halt.excluded,"),
        ("an excluded chip's PERST# pad releases",
         "self.perst_n.eq(~self.halt.perst),", "self.perst_n.eq(~self.halt.perst | self.halt.excluded),"),
        ("the host's CSR address selects the meter slot that gets charged",
         "m.d.comb += self.meter.rd_slot.eq(meter_off[5:7])",
         "m.d.comb += [self.meter.rd_slot.eq(meter_off[5:7]), self.meter.slot.eq(meter_off[5:7])]"),
    ]),
}

# ------------------------------------------------------------------------------------------------ helpers
SMALL = dict(cap_entries=2, ticket_entries=2, t_throttle_ms=3, t_halt_ms=4, ms_shift=2, t_boot_ms=3)


def _tool(name: str) -> str:
    from .__main__ import tool
    return tool(name)


def _core(mutant, kwargs):
    from .__main__ import load_block
    if mutant is None:
        from rtl.governor_rtl import GovernorCore
        return GovernorCore(**kwargs)
    return load_block("top.py", "GovernorCore", mutant[1], mutant[2], kwargs)


def _probes(core) -> list:
    """Internal signals the core properties talk about, brought out as extra ports of the proof build only."""
    for attr in ("loop_lost", "count"):
        getattr(core.loop, attr).name = "loop_" + attr
    return [core.halt.state, core.halt.cause, core.halt.switch_open, core.halt.timer, core.hb.remaining,
            core.hb.expired, core.loop.loop_lost, core.loop.count, core.ms_div,
            core.halt.excluded, core.halt.hb_seen, core.halt.boot_timer, core.halt.no_first_hb, core.alarms.alarms]


def core_verilog(out: str, mutant=None, kwargs=None, probes: bool = True) -> None:
    core = _core(mutant, SMALL if kwargs is None else kwargs)
    ports = core.ports() + (_probes(core) if probes else [])
    if mutant is not None and "self.meter.slot.eq(" in mutant[2]:
        ports = [p for p in ports if p is not core.meter.slot]   # now driven inside, so no longer an input
    text = verilog.convert(core, name="governor_core", ports=ports, emit_src=False)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)


def module_ports(vtext: str, name: str) -> list:
    """[(direction, width, port name)] of one module in yosys/amaranth Verilog, escaped names included."""
    start = re.search(r"^module " + re.escape(name) + r"\s*\(", vtext, re.M)
    body = vtext[start.start(): vtext.index("endmodule", start.start())]
    body = re.sub(r"^\s*function\b.*?^\s*endfunction\b", "", body, flags=re.M | re.S)   # yosys's pmux helpers
    out = []
    for d, w, n in re.findall(r"^\s*(input|output)\s+(?:wire\s+|reg\s+)?(\[\d+:0\]\s*)?(\\\S+|\w+)\s*;", body, re.M):
        out.append((d, (w or "").strip(), n))
    return out


def dut_instance(vtext: str, inst: str = "dut") -> str:
    """Declarations and an instance of governor_core with every port on a same-named wire; inputs are free
    (anyseq) except clk and rst, which come from the property module's own ports."""
    lines, conns = [], []
    for d, w, n in module_ports(vtext, "governor_core"):
        if n in ("clk", "rst"):
            conns.append(f".{n}({n})")
            continue
        lines.append(("  (* anyseq *) wire " if d == "input" else "  wire ") + f"{w} {n};")
        conns.append(f".{n}({n})")
    return "\n".join(lines) + f"\n  governor_core {inst}({', '.join(conns)});\n"


def core_props_text(vtext: str, props_file: str = "governor_core.sv") -> str:
    src = open(os.path.join(HERE, props_file), encoding="utf-8").read()
    return src.replace("  //@@DUT@@\n", dut_instance(vtext))


# ------------------------------------------------------------------------------------------------ host miters
HOST_PATHS = {
    # which inputs the host (untrusted OS, hypervisor, BMC) can drive, which outputs it may legitimately change,
    # and which registers it may legitimately change
    "csr": (("csr_addr", "epoch_host_wr", "epoch_host_data"), ("csr_rdata",), None),
    "doorbell": (("doorbell",), ("csr_rdata", "mbox_verify_req", "mbox_dispatch", "mbox_cmd_out"), "core.mbox."),
}


def _wrappers(vtext: str, host: tuple, free_out: tuple) -> str:
    ports = module_ports(vtext, "governor_core")

    def wrap(name, alt):
        decl, conn, plist = [], [], []
        for d, w, n in ports:
            if d == "input":
                plist.append(n); decl.append(f"  input {w} {n};")
                if n in host:
                    plist.append(n + "_b"); decl.append(f"  input {w} {n}_b;")
                conn.append(f".{n}({n + '_b' if (alt and n in host) else n})")
            elif n in free_out:
                decl.append(f"  wire {w} {n};"); conn.append(f".{n}({n})")
            else:
                plist.append(n); decl.append(f"  output {w} {n};"); conn.append(f".{n}({n})")
        return f"module {name}({', '.join(plist)});\n" + "\n".join(decl) + \
            f"\n  governor_core core({', '.join(conn)});\nendmodule\n"
    return wrap("wrap_gold", False) + wrap("wrap_gate", True)


def host_miter(work: str, vpath: str, path: str, solver_list: list) -> tuple[bool, str]:
    """Two copies of the core, same inputs except the host's, which differ freely. Every register (exposed as an
    output; mailbox registers excepted for the doorbell) and every pin other than the allowed ones must agree in
    every cycle. All registers are compared, so the property is 1-inductive: the induction proves it for all time."""
    host, free_out, own = HOST_PATHS[path]
    vtext = open(vpath, encoding="utf-8").read()
    shutil.copy(vpath, os.path.join(work, "dut.v"))
    with open(os.path.join(work, "wrap.v"), "w") as f:
        f.write(_wrappers(vtext, host, free_out))
    sel = "wrap_gold wrap_gate" if own is None else \
        f"wrap_gold/w:* wrap_gold/w:{own}* %d wrap_gate/w:* wrap_gate/w:{own}* %d"
    y = subprocess.run([_tool("yowasp-yosys"), "-q", "-p",
                        "read_verilog -sv dut.v; read_verilog -sv wrap.v; setattr -mod -unset top; hierarchy -check; "
                        f"proc; flatten; opt_clean; expose -dff {sel}; select wrap_gold wrap_gate; "
                        "write_verilog -noattr -selected exposed.v"], capture_output=True, text=True, cwd=work)
    if y.returncode:
        return False, "TOOL ERROR (yosys, miter pass 1): " + (y.stderr or y.stdout)[-600:]
    exposed = open(os.path.join(work, "exposed.v"), encoding="utf-8").read()
    gp = module_ports(exposed, "wrap_gold")
    if [p for p in gp] != module_ports(exposed, "wrap_gate"):
        return False, "TOOL ERROR (miter): the two copies expose different ports"
    regs = [n for d, w, n in gp if d == "output" and n.startswith("\\")]
    if not regs:
        return False, "TOOL ERROR (miter): no registers exposed"
    decl, cg, cb, asserts = [], [], [], []
    for k, (d, w, n) in enumerate(gp):
        if d == "input":
            if n == "clk":
                cg.append(".clk(clk)"); cb.append(".clk(clk)")
            else:
                decl.append(f"  (* anyseq *) wire {w} i{k};"); cg.append(f".{n} (i{k})"); cb.append(f".{n} (i{k})")
        else:
            decl.append(f"  wire {w} g{k}, b{k};"); cg.append(f".{n} (g{k})"); cb.append(f".{n} (b{k})")
            asserts.append(f"    assert(g{k} == b{k});")
    with open(os.path.join(work, "props.sv"), "w") as f:
        f.write("module miter_props(input clk);\n" + "\n".join(decl) +
                f"\n  wrap_gold gold({', '.join(cg)});\n  wrap_gate gate({', '.join(cb)});\n"
                "  always @(*) begin\n" + "\n".join(asserts) + "\n  end\nendmodule\n")
    y = subprocess.run([_tool("yowasp-yosys"), "-q", "-p",
                        "read_verilog -sv exposed.v; read_verilog -formal -sv props.sv; prep -top miter_props; "
                        "async2sync; dffunmap; write_smt2 -wires design.smt2"], capture_output=True, text=True, cwd=work)
    if y.returncode:
        return False, "TOOL ERROR (yosys, miter pass 2): " + (y.stderr or y.stdout)[-600:]
    from .__main__ import bmc_and_induction
    for s in solver_list:
        ok, why = bmc_and_induction(work, 2, s)
        if not ok:
            return False, why
    return True, f"{len(regs)} registers and {len(asserts) - len(regs)} pins unaffected, induction ({', '.join(solver_list)})"


def host_cone(work: str, vpath: str, path: str) -> tuple[bool, str]:
    """Structural proof on the netlist: follow every wire the host's inputs can reach, through every cell, to the
    end (yosys select %co*). No register may be in that cone (for the doorbell: none outside the mailbox) and no pin
    but the allowed ones. A register outside the cone cannot depend on the host in any cycle, so this holds for all
    time and at any size; it is stronger than the semantic miter (it also refuses paths that happen to cancel).
    A failure is yosys's 'select -assert-none' assertion, reported as an assertion, never as a tool error."""
    host, free_out, own = HOST_PATHS[path]
    shutil.copy(vpath, os.path.join(work, "dut.v"))
    src = " ".join(f"i:{h}" for h in host) + " %u" * (len(host) - 1)
    ffs = "t:$dff t:$adff t:$sdff t:$dffe t:$adffe t:$sdffe t:$aldff t:$dlatch t:$mem* " + "%u " * 8
    regs_bad = f"@cone {ffs}%i" + (f" c:$flatten\\{own[5:-1]}.* %d" if own else "")
    outs_bad = "@cone o:* %i " + " ".join(f"o:{o} %d" for o in free_out)
    script = (f"read_verilog -sv dut.v; hierarchy -top governor_core; proc; flatten; opt_clean; "
              f"select -set cone {src} %co*; select -count @cone; "
              f"tee -o regs.txt select -list {regs_bad}; tee -o outs.txt select -list {outs_bad}; "
              f"select -assert-none {regs_bad}; select -assert-none {outs_bad}")
    y = subprocess.run([_tool("yowasp-yosys"), "-p", script], capture_output=True, text=True, cwd=work)
    if y.returncode:
        if "Assertion failed: selection is not empty" in (y.stdout + y.stderr):
            found = [l.strip().split("/", 1)[-1] for f in ("regs.txt", "outs.txt") if os.path.exists(os.path.join(work, f))
                     for l in open(os.path.join(work, f)) if l.startswith("governor_core/")]
            return False, f"assertion failed: the host reaches {', '.join(found[:4])}" + (" ..." if len(found) > 4 else "")
        return False, "TOOL ERROR (yosys, cone): " + (y.stderr or y.stdout)[-600:]
    n = re.findall(r"(\d+) objects", y.stdout)
    return True, f"the host's inputs reach {n[0] if n else '?'} netlist objects, no register" + \
        (" outside the mailbox" if own else "") + " and no pin but " + ", ".join(free_out)


def _miter_solvers(all_solvers: bool) -> list:
    """One solver for the core's heavy checks: yices when present. z3 needs about a minute where yices needs a
    second on these netlists, and boolector (WebAssembly) is slower still; z3 runs when it is the only one."""
    from .__main__ import solvers
    return ["yices"] if "yices" in solvers() else ["z3"]


HOST_MUTANTS = ("reading MBOX_STATUS", "the doorbell masks", "the host's CSR address")


def _miter_check(path: str, full: bool):
    def run(work, mutant, all_solvers):
        # about two minutes per run here, so on mutants it runs only for the ones that plant a host path
        if mutant is not None and not mutant[0].startswith(HOST_MUTANTS):
            return True, "not run on this mutant (not a host-path bug)"
        v = os.path.join(work, "core.v")
        core_verilog(v, mutant, kwargs={} if full else None, probes=False)
        return host_miter(work, v, path, _miter_solvers(all_solvers))
    return run


def _cone_check(path: str):
    def run(work, mutant, all_solvers):
        v = os.path.join(work, "core.v")
        core_verilog(v, mutant, kwargs={}, probes=False)        # the full-size core, as checked in
        return host_cone(work, v, path)
    return run


# ------------------------------------------------------------------------------------------------ design facts
def _cover_fact(props_file: str, depth: int, want: str) -> tuple[bool, str]:
    """Bounded cover on the small core: a trace must exist that reaches the cover() in props_file."""
    import tempfile
    with tempfile.TemporaryDirectory() as work:
        v = os.path.join(work, "dut.v")
        core_verilog(v)
        with open(os.path.join(work, "props.sv"), "w") as f:
            f.write(core_props_text(open(v).read(), props_file))
        from .__main__ import smt
        top = os.path.splitext(props_file)[0] + "_props"
        err = smt(work, top)
        if err:
            return False, err
        r = subprocess.run([_tool("yowasp-yosys-smtbmc"), "-s", _miter_solvers(False)[0], "-c", "-t", str(depth),
                            "--dump-vcd", "trace.vcd", "design.smt2"], capture_output=True, text=True, cwd=work)
        reached = [l for l in r.stdout.splitlines() if "Reached cover statement" in l]
        if "Status: PASSED" not in r.stdout or not reached:
            return False, "cover not reached: " + r.stdout[-300:]
        step = re.search(r"in step (\d+)", reached[-1])
        return True, f"{want} (trace of {step.group(1) if step else '?'} cycles found)"


def _assert_fact(props_file: str, depth: int, want: str) -> tuple[bool, str]:
    import tempfile
    from .__main__ import prove
    with tempfile.TemporaryDirectory() as work:
        v = os.path.join(work, "dut.v")
        core_verilog(v)
        ok, why = prove(v, os.path.join(HERE, props_file), work, depth=depth,
                        props_text=core_props_text(open(v).read(), props_file), solver=_miter_solvers(False)[0])
        return ok, (want + "; " + why) if ok else why


FACTS = [
    ("lost heartbeat climbs to SAFE with the loop closed", lambda: _cover_fact(
        "governor_core_cover.sv", 60, "from boot, a heartbeat that runs out reaches SAFE, power off, loop pad closed")),
    ("a local cause never opens the loop", lambda: _assert_fact(
        "governor_core_facts.sv", 12, "proven: cause LOCAL implies the loop pad is closed (the old fact that a HALT "
        "to a chip in SAFE leaves the pad closed is gone: Yobie's call 1, now rule RTL-HALT-REACHES-PINS)")),
]


# ------------------------------------------------------------------------------------------------ halt_seq extras
def _exclude_miter(work, mutant, all_solvers):
    """Two copies of halt_seq, one that never sees cmd_exclude: outside HALTED_INITIAL with no cause they never
    differ (rtl/formal/halt_seq_exclude_miter.sv). Runs on the checked-in Verilog or on the mutant."""
    from .__main__ import GEN, mutant_verilog, prove
    v = os.path.join(work, "dut.v")
    if mutant is None:
        shutil.copy(os.path.join(GEN, "halt_seq.v"), v)
    else:
        mutant_verilog("halt.py", "HaltSeq", mutant[1], mutant[2], v, "halt_seq")
    ok, why = prove(v, os.path.join(HERE, "halt_seq_exclude_miter.sv"), work, depth=4, solver="yices")
    return ok, why


# ------------------------------------------------------------------------------------------------ options
def _sims(name):
    return {"sim": lambda: sim_b.SIMS[name](), "sim_mutant": lambda factory: sim_b.SIMS[name](cls=factory)}


OPTIONS_B = {
    "halt_seq": {"checks": [("EXCLUDE changes nothing outside HALTED_INITIAL with no cause (two-copy miter)", _exclude_miter)],
                 **_sims("halt_seq")},
    "heartbeat": {**_sims("heartbeat"), "depth": 25, "solver": "yices"},
    "meter": {**_sims("meter"), "depth": 6, "solver": "yices"},
    "alarms": {**_sims("alarms"), "depth": 25, "solver": "yices"},
    "measure_reg": {**_sims("measure_reg"), "depth": 25, "solver": "yices"},
    "loop_io": {**_sims("loop_io"), "depth": 25, "solver": "yices"},
    "governor_core": {
        "verilog": lambda out, mutant: core_verilog(out, mutant),
        "props_text": core_props_text,
        "depth": 20,
        "solver": "yices",
        **_sims("governor_core"),
        "checks": [("host CSR reads write nothing (full-size netlist)", _cone_check("csr")),
                   ("doorbell reaches only the mailbox (full-size netlist)", _cone_check("doorbell")),
                   ("host CSR reads write nothing (two-copy miter, small build)", _miter_check("csr", False)),
                   ("doorbell reaches only the mailbox (two-copy miter, small build)", _miter_check("doorbell", False))],
        "facts": FACTS,
    },
}
