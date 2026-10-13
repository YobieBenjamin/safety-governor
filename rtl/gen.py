"""Emit Verilog for every block and for governor_core into rtl/gen/.

    python -m rtl.gen            # writes rtl/gen/*.v
    python -m rtl.gen --check    # exit 1 if the checked-in Verilog is stale

Uses Amaranth's built-in Yosys (the amaranth-yosys wheel), so no system tools are needed.
"""
from __future__ import annotations

import os
import sys

from amaranth.back import verilog

from rtl.governor_rtl import (Alarms, CapTable, EpochReg, GovernorCore, HaltSeq, Heartbeat, Lifecycle, LoopIO, Mailbox,
                              MeasureReg, Meter, MonotonicCounter, TicketStore)

OUT = os.path.join(os.path.dirname(__file__), "gen")


def blocks():
    core = GovernorCore()
    items = {
        "monotonic_counter": (MonotonicCounter(), None),
        "measure_reg": (MeasureReg(), None),
        "epoch_reg": (EpochReg(), None),
        "lifecycle": (Lifecycle(), None),
        "cap_table": (CapTable(), None),
        "ticket_store": (TicketStore(), None),
        "heartbeat": (Heartbeat(), None),
        "halt_seq": (HaltSeq(), None),
        "loop_io": (LoopIO(), None),
        "meter": (Meter(), None),
        "mailbox": (Mailbox(), None),
        "alarms": (Alarms(), None),
        "governor_core": (core, core.ports()),
    }
    return items


def auto_ports(dut):
    from amaranth import Signal
    return [v for k, v in vars(dut).items() if isinstance(v, Signal)]


def emit(check: bool = False) -> int:
    os.makedirs(OUT, exist_ok=True)
    stale = 0
    for name, (dut, ports) in blocks().items():
        text = verilog.convert(dut, name=name, ports=ports or auto_ports(dut), emit_src=False)
        text = "\n".join(line for line in text.splitlines() if not line.startswith("(* generator"))  # drop the version banner
        path = os.path.join(OUT, name + ".v")
        if check:
            try:
                current = open(path, encoding="utf-8").read()
            except FileNotFoundError:
                current = ""
            if current != text:
                print(f"stale: {path}")
                stale += 1
        else:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(f"wrote {path} ({len(text.splitlines())} lines)")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(emit(check="--check" in sys.argv))
