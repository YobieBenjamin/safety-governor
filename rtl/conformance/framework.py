# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The small test framework the conformance suite runs on.

Every test is a plain function registered with ``@conformance("R-0xx", ...)``: it names the requirement ids
it checks. A test that reproduces a finding is registered with ``finding="F-0n"``: it asserts what the spec
requires, so on today's RTL it FAILS BY ASSERTION, and the runner reports that as a disagreement, not as a pass.
If a finding test ever passes, the finding no longer reproduces and the runner fails until FINDINGS.md is
updated (the record has to stay exact).

DUTs are built through ``B`` (``B.HaltSeq(...)``, ``B.GovernorCore(...)``), which looks the class up in its
module at call time. That is what lets the mutation run swap one block's source for a mutant without the
tests knowing.
"""
from __future__ import annotations

import importlib
import time
import traceback
from dataclasses import dataclass, field
from typing import Callable

from amaranth.sim import Simulator

MODULES = {
    "MonotonicCounter": "monotonic", "MeasureReg": "measure_reg", "EpochReg": "epoch_reg", "Lifecycle": "lifecycle",
    "CapTable": "cap_table", "TicketStore": "ticket_store", "Heartbeat": "heartbeat", "HaltSeq": "halt",
    "LoopIO": "halt_loop", "Meter": "meter", "Mailbox": "mailbox", "Alarms": "alarms", "GovernorCore": "top",
}


class _Blocks:
    """``B.Name(...)`` builds the block from whatever class its module holds right now."""

    def __getattr__(self, name: str):
        if name not in MODULES:
            raise AttributeError(name)
        return getattr(importlib.import_module("rtl.governor_rtl." + MODULES[name]), name)


B = _Blocks()


@dataclass
class Test:
    name: str
    fn: Callable[[], None]
    reqs: tuple[str, ...]
    finding: str | None = None
    doc: str = ""


@dataclass
class Outcome:
    test: Test
    status: str            # "pass", "assert" (failed by assertion), "error" (anything else: never a catch)
    detail: str = ""
    seconds: float = 0.0
    extra: dict = field(default_factory=dict)


REGISTRY: list[Test] = []


def conformance(*reqs: str, finding: str | None = None):
    def wrap(fn):
        REGISTRY.append(Test(fn.__name__, fn, tuple(reqs), finding, (fn.__doc__ or "").strip().split("\n")[0]))
        return fn
    return wrap


def run_one(t: Test) -> Outcome:
    t0 = time.time()
    try:
        extra = t.fn() or {}
        return Outcome(t, "pass", "", time.time() - t0, extra if isinstance(extra, dict) else {})
    except AssertionError as e:
        tb = traceback.extract_tb(e.__traceback__)
        where = next((f"{f.filename.split('/')[-1]}:{f.lineno}" for f in reversed(tb) if "conformance" in f.filename), "")
        return Outcome(t, "assert", (str(e) or "assertion failed") + (f" ({where})" if where else ""), time.time() - t0)
    except Exception as e:   # noqa: BLE001 - a tool or harness error is reported as such, never as a catch
        return Outcome(t, "error", f"{type(e).__name__}: {e}", time.time() - t0)


def sim(dut, testbench, clock: float = 1e-6) -> None:
    s = Simulator(dut)
    s.add_clock(clock)
    s.add_testbench(testbench)
    s.run()


def levers(ctx, dut) -> tuple[int, int, int]:
    return ctx.get(dut.pwrbrk), ctx.get(dut.perst), ctx.get(dut.pwr_en)
