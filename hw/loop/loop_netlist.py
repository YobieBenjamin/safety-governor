#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Netlist generator for the halt loop: N governors on one supervised series current loop.

Writes an ngspice deck (and optionally runs it) for N governors threaded on the loop
described in docs/02-safety-fabric.md section 1 and hw/pcb/rack-integration.md section 4:

* a loop driver, modelled as a voltage source with a series resistor sized at design time
  so the closed loop carries the nominal 20 mA at the nominal temperature (a real driver is
  a current regulator with the same compliance voltage; the resistor is the simplest model
  that opens and discharges the same way, and it is stated as an assumption);
* per governor, a fail-open series switch (ngspice voltage-controlled switch, Ron about
  1 ohm, Roff 1 Mohm, driven by a PULSE source so that one chosen governor opens at t_open)
  and a sense resistor (10 ohm, 200 mV at 20 mA) read by a behavioural comparator that trips
  at 50 percent of the nominal sense voltage;
* per tray-to-tray hop, one lumped RC pi section of twisted pair (series R per conductor,
  pair capacitance split half at each end, optional series inductance), the return
  conductor lumped as one resistor at the bottom of the loop;
* a wire break can be simulated instead of a switch opening: the chosen hop opens at t_open.

Resistors carry a stated temperature coefficient and the deck sets .temp, so the loop current
and the sense voltage move with temperature. A .measure line per governor records the time
at which that governor's sense voltage falls through the comparator threshold. Everything
here is electrical; the digital path (sense period, debounce, lever driver) is added by
run_loop.py.

Usage:
    python3 hw/loop/loop_netlist.py --n 8 --open 4 --hop 1 --temp 25 > deck.cir
    python3 hw/loop/loop_netlist.py --n 72 --open 72 --hop 3 --temp 85 --run
    python3 hw/loop/loop_netlist.py --n 36 --break-hop 18 --run
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

NGSPICE = "ngspice"
_MEASURE_RE = re.compile(r"^\s*(\w+)\s*=\s*([-+0-9.][-+0-9.eE]*)\s*$", re.M)


@dataclass
class LoopParams:
    """Every number the deck depends on. Defaults are the plan-of-record assumptions."""

    n: int = 8                      # governors in the domain (72 is the largest domain)
    open_gov: int | None = 4        # 1-based governor whose switch opens at t_open
    break_hop: int | None = None    # 1-based hop (1..n-1) whose wire breaks at t_open instead
    t_open: float = 20e-6           # s, when the switch opens or the wire breaks
    hop_m: float = 1.0              # m of twisted pair per tray-to-tray hop
    temp_c: float = 25.0            # circuit temperature (.temp)
    tnom_c: float = 25.0            # temperature at which resistor values are nominal
    v_supply: float = 24.0          # V, loop driver compliance voltage
    i_nom: float = 20e-3            # A, nominal loop current (live zero: 0 mA means stop)
    r_on: float = 1.0               # ohm, switch closed
    r_off: float = 1e6              # ohm, switch open
    r_sense: float = 10.0           # ohm, sense element: 200 mV at 20 mA
    threshold_frac: float = 0.5     # comparator trips at this fraction of the nominal sense voltage
    tc_src: float = 200e-6          # 1/K, loop driver series resistor (thick film class)
    tc_sense: float = 100e-6        # 1/K, sense resistor (metal film current-sense class)
    tc_cable: float = 3930e-6       # 1/K, copper
    cable_r_per_m: float = 0.1      # ohm/m per conductor (24 AWG class)
    cable_c_per_m: float = 50e-12   # F/m, pair capacitance
    cable_l_per_m: float = 0.0      # H/m, optional series inductance (0.6e-6 is a typical pair)
    t_edge: float = 100e-9          # s, switch control edge (the driver's opening time)
    t_step: float = 1e-6            # s, .tran print step
    t_max: float = 100e-9           # s, .tran maximum internal step
    t_after: float = 200e-6         # s, simulated time after t_open

    def __post_init__(self) -> None:
        if self.n < 1:
            raise ValueError("n must be at least 1")
        if self.open_gov is not None and not 1 <= self.open_gov <= self.n:
            raise ValueError(f"open_gov must be in 1..{self.n}")
        if self.break_hop is not None and not 1 <= self.break_hop <= self.n - 1:
            raise ValueError(f"break_hop must be in 1..{self.n - 1}")
        if self.open_gov is not None and self.break_hop is not None:
            raise ValueError("choose a governor to open or a hop to break, not both")
        if self.r_source() <= 0:
            raise ValueError(
                f"supply {self.v_supply} V cannot drive {self.i_nom * 1e3:g} mA through "
                f"{self.r_loop_nominal():.1f} ohm of loop; raise v_supply")

    # Derived values -----------------------------------------------------------------

    @property
    def v_sense_nom(self) -> float:
        return self.i_nom * self.r_sense

    @property
    def v_threshold(self) -> float:
        return self.threshold_frac * self.v_sense_nom

    @property
    def r_hop(self) -> float:
        return self.cable_r_per_m * self.hop_m

    @property
    def c_hop_half(self) -> float:
        return self.cable_c_per_m * self.hop_m / 2

    @property
    def t_stop(self) -> float:
        return self.t_open + self.t_after

    def r_loop_nominal(self) -> float:
        """Closed-loop resistance at tnom, driver resistor excluded: switches, sense
        resistors, forward conductor of every hop and the return conductor."""
        return self.n * (self.r_on + self.r_sense) + 2 * (self.n - 1) * self.r_hop

    def r_source(self) -> float:
        """Driver series resistor: sized so the closed loop carries i_nom at tnom."""
        return self.v_supply / self.i_nom - self.r_loop_nominal()

    def measure_name(self, k: int) -> str:
        return f"t_sense_{k}"

    # The deck -------------------------------------------------------------------------

    def _pulse(self) -> str:
        """Control waveform that opens a switch at t_open: 1 V (closed) to 0 V (open)."""
        return f"PULSE(1 0 {self.t_open:.6g} {self.t_edge:.6g} {self.t_edge:.6g} 1 2)"

    def netlist(self) -> str:
        p = self
        lines = [
            f"* halt loop: {p.n} governors, "
            + (f"governor {p.open_gov} opens" if p.open_gov else
               f"hop {p.break_hop} breaks" if p.break_hop else "nothing opens")
            + f" at {p.t_open * 1e6:g} us, {p.hop_m:g} m hops, {p.temp_c:g} C",
            f".option tnom={p.tnom_c:g}",
            f".temp {p.temp_c:g}",
            f".model SWOPEN SW(Ron={p.r_on:g} Roff={p.r_off:g} Vt=0.5 Vh=0.1)",
            "* loop driver: voltage source and series resistor sized for the nominal current",
            f"Vsup top 0 DC {p.v_supply:g}",
            f"Rsrc top li_1 {p.r_source():.6g} tc1={p.tc_src:g}",
        ]
        for k in range(1, p.n + 1):
            ctl = p._pulse() if k == p.open_gov else "DC 1"
            lines += [
                f"* governor {k}: switch, sense resistor, comparator",
                f"Vc{k} ctl_{k} 0 {ctl}",
                f"S{k} li_{k} sw_{k} ctl_{k} 0 SWOPEN",
                f"Rs{k} sw_{k} lo_{k} {p.r_sense:g} tc1={p.tc_sense:g}",
                f"Bs{k} sense_{k} 0 V=V(sw_{k},lo_{k})",
                f"Bc{k} cmp_{k} 0 V=V(sense_{k}) > {p.v_threshold:.6g} ? 1 : 0",
            ]
            if k < p.n:
                nxt = f"li_{k + 1}"
                end = nxt
                if p.break_hop == k:
                    end = f"mb_{k}"
                    lines += [f"Vcb{k} ctlb_{k} 0 {p._pulse()}",
                              f"Sb{k} mb_{k} {nxt} ctlb_{k} 0 SWOPEN"]
                lines.append(f"* hop {k}: {p.hop_m:g} m of twisted pair as an RC pi section")
                if p.cable_l_per_m > 0:
                    lines += [f"Rh{k} lo_{k} mh_{k} {p.r_hop:.6g} tc1={p.tc_cable:g}",
                              f"Lh{k} mh_{k} {end} {p.cable_l_per_m * p.hop_m:.6g}"]
                else:
                    lines.append(f"Rh{k} lo_{k} {end} {p.r_hop:.6g} tc1={p.tc_cable:g}")
                lines += [f"Ch{k}a lo_{k} 0 {p.c_hop_half:.6g}",
                          f"Ch{k}b {nxt} 0 {p.c_hop_half:.6g}"]
        r_ret = max((p.n - 1) * p.r_hop, 1e-6)
        lines += [
            "* return conductor, lumped",
            f"Rret lo_{p.n} 0 {r_ret:.6g} tc1={p.tc_cable:g}",
            f".tran {p.t_step:.6g} {p.t_stop:.6g} 0 {p.t_max:.6g}",
            f".measure tran v_sense_nom FIND v(sense_1) AT={p.t_open / 2:.6g}",
        ]
        lines += [f".measure tran {p.measure_name(k)} WHEN v(sense_{k})={p.v_threshold:.6g} FALL=1"
                  for k in range(1, p.n + 1)]
        lines.append(".end")
        return "\n".join(lines) + "\n"


@dataclass
class SimResult:
    params: LoopParams
    t_cross: dict[int, float | None] = field(default_factory=dict)  # governor -> crossing time, s
    v_sense_nom: float | None = None
    stdout: str = ""

    @property
    def complete(self) -> bool:
        return bool(self.t_cross) and all(t is not None for t in self.t_cross.values())

    @property
    def last_governor(self) -> int | None:
        done = {k: t for k, t in self.t_cross.items() if t is not None}
        return max(done, key=done.get) if done else None

    @property
    def propagation_s(self) -> float | None:
        """Time from the switch opening (or wire break) to the last governor's crossing."""
        k = self.last_governor
        if k is None or not self.complete:
            return None
        return self.t_cross[k] - self.params.t_open


def parse_measures(text: str) -> dict[str, float]:
    return {m.group(1).lower(): float(m.group(2)) for m in _MEASURE_RE.finditer(text)}


def simulate(p: LoopParams, ngspice: str = NGSPICE, keep_dir: Path | None = None) -> SimResult:
    """Write the deck, run ngspice in batch mode, parse the .measure results."""
    if shutil.which(ngspice) is None:
        raise RuntimeError(f"{ngspice} not found on PATH")
    with tempfile.TemporaryDirectory(prefix="halt-loop-") as tmp:
        workdir = keep_dir or Path(tmp)
        workdir.mkdir(parents=True, exist_ok=True)
        deck = workdir / f"loop_n{p.n}_{'gov' + str(p.open_gov) if p.open_gov else 'hop' + str(p.break_hop)}" \
                         f"_{p.hop_m:g}m_{p.temp_c:g}C.cir"
        deck.write_text(p.netlist())
        proc = subprocess.run([ngspice, "-b", deck.name], cwd=workdir, capture_output=True,
                              text=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"ngspice failed on {deck}:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    measures = parse_measures(proc.stdout)
    result = SimResult(params=p, stdout=proc.stdout, v_sense_nom=measures.get("v_sense_nom"))
    result.t_cross = {k: measures.get(p.measure_name(k)) for k in range(1, p.n + 1)}
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--n", type=int, default=8, help="governors in the domain")
    ap.add_argument("--open", type=int, default=None, help="1-based governor whose switch opens")
    ap.add_argument("--break-hop", type=int, default=None, help="1-based hop whose wire breaks")
    ap.add_argument("--t-open", type=float, default=20e-6, help="s")
    ap.add_argument("--hop", type=float, default=1.0, help="m of twisted pair per hop")
    ap.add_argument("--temp", type=float, default=25.0, help="C")
    ap.add_argument("--supply", type=float, default=24.0, help="V")
    ap.add_argument("--cable-l", type=float, default=0.0, help="H/m of series inductance")
    ap.add_argument("-o", "--out", type=Path, default=None, help="write the deck here (default stdout)")
    ap.add_argument("--run", action="store_true", help="run ngspice and print the crossing times")
    a = ap.parse_args(argv)
    open_gov = a.open if (a.open is not None or a.break_hop is not None) else (a.n + 1) // 2
    p = LoopParams(n=a.n, open_gov=open_gov, break_hop=a.break_hop, t_open=a.t_open, hop_m=a.hop,
                   temp_c=a.temp, v_supply=a.supply, cable_l_per_m=a.cable_l)
    if a.run:
        r = simulate(p)
        for k in range(1, p.n + 1):
            t = r.t_cross[k]
            print(f"governor {k:3d}: {'no crossing' if t is None else f'{(t - p.t_open) * 1e6:8.3f} us'}")
        print(f"nominal sense voltage {r.v_sense_nom * 1e3:.1f} mV, threshold {p.v_threshold * 1e3:.0f} mV")
        print(f"electrical propagation {r.propagation_s * 1e6:.3f} us (last: governor {r.last_governor})"
              if r.complete else "incomplete: some governor never crossed the threshold")
        return 0 if r.complete else 1
    deck = p.netlist()
    if a.out:
        a.out.write_text(deck)
    else:
        sys.stdout.write(deck)
    return 0


if __name__ == "__main__":
    sys.exit(main())
