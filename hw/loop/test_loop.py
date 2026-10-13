"""Halt loop timing: the ngspice model of eight governors halts inside the budget.

    source .venv/bin/activate && python -m pytest -q hw/loop/test_loop.py

The electrical test is skipped when ngspice is not installed; the netlist shape test always runs.
"""

import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import loop_netlist as ln  # noqa: E402
import run_loop as rl  # noqa: E402

needs_ngspice = pytest.mark.skipif(shutil.which(ln.NGSPICE) is None, reason="ngspice not installed")


def test_netlist_has_one_stage_per_governor():
    p = ln.LoopParams(n=8, open_gov=4, hop_m=1.0, temp_c=25.0)
    deck = p.netlist()
    lines = deck.splitlines()
    assert sum(bool(re.match(r"S\d+ ", l)) for l in lines) == 8    # one series switch per governor
    assert sum(bool(re.match(r"Rs\d+ ", l)) for l in lines) == 8   # one sense resistor per governor
    assert sum(bool(re.match(r"Rh\d+ ", l)) for l in lines) == 7   # one hop between neighbours
    assert sum(l.startswith(".measure tran t_sense_") for l in lines) == 8
    assert "PULSE(1 0 2e-05" in deck and deck.count("PULSE(") == 1  # only governor 4 opens
    assert ".temp 25" in deck and ".tran 1e-06" in deck
    assert abs(p.r_source() - (24 / 0.02 - 8 * 11 - 2 * 7 * 0.1)) < 1e-9


def test_supply_must_cover_the_loop():
    with pytest.raises(ValueError):
        ln.LoopParams(n=200, open_gov=1, v_supply=24.0)


def test_digital_path_is_311_us():
    assert abs(rl.digital_path_s() - 311e-6) < 1e-12


@needs_ngspice
def test_eight_governors_halt_inside_the_budget():
    p = ln.LoopParams(n=8, open_gov=4, hop_m=1.0, temp_c=25.0)
    r = ln.simulate(p)
    assert r.complete, "every governor must see the loss of current"
    assert abs(r.v_sense_nom - 0.2) < 0.01, "20 mA through 10 ohm reads 200 mV before the opening"
    assert r.propagation_s < 100e-6, f"electrical propagation {r.propagation_s * 1e6:.2f} us"
    assert r.propagation_s + rl.digital_path_s() < rl.BOUND_S


@needs_ngspice
def test_wire_break_reads_as_open():
    p = ln.LoopParams(n=8, open_gov=None, break_hop=4, hop_m=3.0, temp_c=85.0)
    r = ln.simulate(p)
    assert r.complete
    assert r.propagation_s + rl.digital_path_s() < rl.BOUND_S
