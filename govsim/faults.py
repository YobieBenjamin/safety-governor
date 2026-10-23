"""N2: the false-halt rate model and its fault injection into govsim (``docs/07-verification-plan.md`` section 5, numeric).

A *false halt* is a halt with no hazard behind it. Each failure mode of the FMEA gets a rate, a
scope (it halts the whole rack by opening the loop, or only one slot), and, where the loop's or the
beacon's filtering applies, the probability that a transient survives it.

Rates are in FIT (failures per 10^9 device-hours). They are planning values: not measurements of
this design and not looked up out of a licensed table in this run. The IEC 61508-6 data annex,
IEC 62380, SN 29500 and MIL-HDBK-217F (connector class) and the public datasheets for regulators,
comparators and PHYs are the places N3 (an FPGA beside a real GPU) checks each one; every row tagged
``assumed`` has no public rate at all, so it is an assumption to be measured, not a figure. The
module proves the arithmetic; ``tests/test_false_halt_model.py`` reproduces it by hand and drives
each mode through govsim (the injector below) to confirm the effect column, which slots halt.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

HOURS_PER_YEAR = 8766.0
FIT = 1e-9                      # failures per device-hour per FIT

# Design parameters (docs/02-safety-fabric.md): sense period 100 us, debounce of two sense periods.
SENSE_PERIOD_S = 100e-6
DEBOUNCE_SAMPLES = 2
HEARTBEAT_PERIOD_S = 1.0
HEARTBEAT_EXPIRY_S = 5.0        # policy fabric.heartbeat_expiry_s
BEACON_CONFIRM_WINDOWS = 1      # as built: reports of one beacon decide, judged when the next heartbeat closes the window (two heartbeats of latency); 2 would need the odd report in two beacons
RACK_GOVERNORS = 72             # loop members in a 72-GPU domain

# The switch-off threshold, an assumption stated as such (docs/07 disproof). A large training
# cluster's published interruption rate is the baseline: the Llama 3 report counts LLAMA3_
# INTERRUPTIONS in LLAMA3_DAYS on LLAMA3_GPUS GPUs, which scales to about 12.4 per 72-GPU rack-year
# (computed below). A governor that adds more than a tenth of that -- about 1.2 rack halts a year --
# is a visible new source of lost work. The tenth is a judgement, not a measurement; the counts are
# a planning baseline, to be confirmed against the paper, not a measurement taken here.
LLAMA3_INTERRUPTIONS, LLAMA3_DAYS, LLAMA3_GPUS = 419, 54, 16384
BASELINE_INTERRUPTIONS_PER_RACK_YEAR = LLAMA3_INTERRUPTIONS / LLAMA3_GPUS * RACK_GOVERNORS * 365.0 / LLAMA3_DAYS
SWITCH_OFF_FRACTION = 0.10
SWITCH_OFF_THRESHOLD = SWITCH_OFF_FRACTION * BASELINE_INTERRUPTIONS_PER_RACK_YEAR


@dataclass(frozen=True)
class Mode:
    key: str
    failure: str                # the FMEA row
    fit: float                  # hard-fault rate per governor, FIT (0 for rows driven by transients)
    scope: str                  # "rack" halts every GPU (the loop opens or every slot's heartbeat dies); "slot" halts one governor's GPU only
    source: str
    sim_effect: str             # what govsim must show when the mode is injected
    runtime: bool = True        # False: acts only at boot, no runtime halt


MODES = [
    Mode("gov_power", "Governor loses power", 200, "rack",
         "regulator plus connector; IEC 62380 / SN 29500 connector class (assumed; N3 checks)",
         "the governor's switch fails open; the loop opens and every GPU halts"),
    Mode("fw_hang", "Governor firmware hang (watchdog reset)", 500, "rack",
         "watchdog trips of small firmware; IEC 61508-6 software-fault allowance (assumed; N3 checks)",
         "the watchdog resets the governor into HALTED_INITIAL, whose switch is open; the loop opens and the rack halts"),
    Mode("loop_wire", "Loop wire or connector opens", 40, "rack",
         "two connectors per governor at 20 FIT; MIL-HDBK-217F connector class",
         "the loop reads open; every GPU halts"),
    Mode("comparator_stuck_open", "Loop sense comparator stuck open", 50, "rack",
         "analogue comparator IC datasheet class (assumed; N3 checks)",
         "the governor senses the loop open though it carries current; it opens its switch and the rack halts"),
    Mode("clock_glitch_detector", "Glitch detector false trip (clock glitch row)", 100, "rack",
         "on-die monitor; no public rate (assumed; N3 checks)",
         "zeroize, SAFE; the loop opens"),
    Mode("fabric_port", "Fabric port failure", 100, "slot",
         "PHY and connector; IEC 62380 class (assumed; N3 checks)",
         "the cut-off governor halts its own slot at heartbeat expiry; the loop stays closed"),
    Mode("beacon_readback_stuck", "Switch readback stuck open (beacon names it)", 50, "rack",
         "readback comparator; same class as the loop sense (assumed; N3 checks)",
         "LOOP_JUMPERED: the rack halts at the next beacon"),
    Mode("fuse_read", "Fuse read failure", 20, "slot",
         "OTP macro; foundry qualification (assumed)", "boot refused", runtime=False),
    Mode("nvm_corruption", "NVM corruption", 100, "slot",
         "NVM macro with ECC; datasheet class (assumed)", "refuse to RUN on the next boot", runtime=False),
]
MODE = {m.key: m for m in MODES}

# Transient processes (events per device-hour, mean duration seconds). All assumed; N3 measures them.
SENSE_GLITCH_RATE_PER_H = 1e-4          # an EMI or supply glitch on the sense comparator, per governor
SENSE_GLITCH_MEAN_S = 20e-6
READBACK_GLITCH_RATE_PER_H = 1e-4
READBACK_GLITCH_MEAN_S = 20e-6
HEARTBEAT_HOP_LOSS = 1e-3              # per-frame loss on one ring link
AUTHORITY_OUTAGE_RATE_PER_H = 1e-5     # the heartbeat authority unavailable for longer than the expiry


def fit_to_per_year(fit: float, n: int = 1) -> float:
    return fit * FIT * HOURS_PER_YEAR * n


def survive_debounce(mean_s: float, period_s: float = SENSE_PERIOD_S, samples: int = DEBOUNCE_SAMPLES) -> float:
    """P(a glitch of exponential duration with the given mean is seen in ``samples`` consecutive
    samples), the sampling phase uniform. Closed form for 1 and 2 samples:
    1: (t/T)(1 - e^{-T/t});  2: (t/T)(e^{-T/t} - e^{-2T/t})."""
    r = mean_s / period_s
    if samples == 1:
        return r * (1.0 - math.exp(-1.0 / r))
    if samples == 2:
        return r * (math.exp(-1.0 / r) - math.exp(-2.0 / r))
    raise ValueError("closed form for 1 or 2 samples")


def survive_debounce_mc(mean_s: float, trials: int, seed: int, period_s: float = SENSE_PERIOD_S, samples: int = DEBOUNCE_SAMPLES) -> float:
    """The same probability by simulating the sampled comparator."""
    rng = random.Random(seed)
    hit = 0
    for _ in range(trials):
        d = rng.expovariate(1.0 / mean_s)
        phase = rng.random() * period_s                     # first sample after the glitch starts
        n_samples = 0 if phase > d else 1 + int((d - phase) / period_s)
        hit += n_samples >= samples
    return hit / trials


def heartbeat_loss_rate_per_h(hop_loss: float = HEARTBEAT_HOP_LOSS, paths: int = 2) -> float:
    """Expiry needs every heartbeat in the expiry window lost: k = expiry / period of them, each lost
    on all ``paths`` (the dual ring). A run starts at most once per heartbeat."""
    k = int(HEARTBEAT_EXPIRY_S // HEARTBEAT_PERIOD_S)
    return (3600.0 / HEARTBEAT_PERIOD_S) * (hop_loss ** paths) ** k


def beacon_transient_rate_per_h(confirm: int = BEACON_CONFIRM_WINDOWS) -> float:
    """A readback glitch is active at a beacon instant with p = rate * mean duration; the rack halts
    only if the odd report repeats in ``confirm`` consecutive windows."""
    p = READBACK_GLITCH_RATE_PER_H / 3600.0 * READBACK_GLITCH_MEAN_S
    return (3600.0 / HEARTBEAT_PERIOD_S) * p ** confirm


def rack_year(n: int = RACK_GOVERNORS, confirm: int = BEACON_CONFIRM_WINDOWS, samples: int = DEBOUNCE_SAMPLES) -> dict:
    """Expected false halts per rack-year: ``rack`` (every GPU: the loop opens or every slot's
    heartbeat dies) and ``slot`` (one GPU), with the per-mode breakdown."""
    rows: dict[str, float] = {}
    for m in MODES:
        if m.runtime:
            rows[m.key] = fit_to_per_year(m.fit, n)
    rows["sense_glitch"] = SENSE_GLITCH_RATE_PER_H * HOURS_PER_YEAR * n * survive_debounce(SENSE_GLITCH_MEAN_S, samples=samples)
    rows["heartbeat_loss"] = heartbeat_loss_rate_per_h() * HOURS_PER_YEAR * n
    rows["authority_outage"] = AUTHORITY_OUTAGE_RATE_PER_H * HOURS_PER_YEAR      # one event; it halts every slot, so it is a rack event
    rows["beacon_transient"] = beacon_transient_rate_per_h(confirm) * HOURS_PER_YEAR * n
    scope = {m.key: m.scope for m in MODES}
    scope.update(sense_glitch="rack", heartbeat_loss="slot", authority_outage="rack", beacon_transient="rack")
    rack = sum(v for k, v in rows.items() if scope[k] == "rack")
    slot = sum(v for k, v in rows.items() if scope[k] == "slot")
    return {"rows": rows, "scope": scope, "rack": rack, "slot": slot, "total": rack + slot}


def fw_hang_break_even_fit(n: int = RACK_GOVERNORS, confirm: int = BEACON_CONFIRM_WINDOWS, samples: int = DEBOUNCE_SAMPLES) -> float:
    """The firmware-hang FIT at which the expected false halts cross the switch-off threshold. The
    model's claim fails if N3 measures watchdog trips above this (about 1150 FIT)."""
    base = rack_year(n, confirm, samples)["total"]
    per_fit = fit_to_per_year(1.0, n)
    return MODE["fw_hang"].fit + (SWITCH_OFF_THRESHOLD - base) / per_fit


def sense_glitch_break_even_rate(n: int = RACK_GOVERNORS, confirm: int = BEACON_CONFIRM_WINDOWS, samples: int = DEBOUNCE_SAMPLES) -> float:
    """The sense-transient rate per hour (at the 20 us mean) at which the expected false halts cross
    the switch-off threshold. The model's claim fails if N3 measures above this (about 5.9e-4/h)."""
    base = rack_year(n, confirm, samples)["total"]
    per_rate = HOURS_PER_YEAR * n * survive_debounce(SENSE_GLITCH_MEAN_S, samples=samples)
    return SENSE_GLITCH_RATE_PER_H + (SWITCH_OFF_THRESHOLD - base) / per_rate


def verdict(total: float) -> str:
    return "below" if total < SWITCH_OFF_THRESHOLD else "ABOVE"


# ------------------------------------------------------------------ fault injection into govsim
# The brief asks to "add fault injection to govsim to confirm each mode's effect". govsim has no
# fault injector, so this module is the feature: one named, documented entry per mode, driving the
# loop, the fabric and the heartbeat through govsim's own primitives (an open switch, a cut wire, a
# jumpered switch, a downed port). Each returns rack.running() after the injection, so the effect --
# which slots halted -- is read, not assumed. The loop-level modes (power, wire, comparator, fw hang)
# open the loop and so halt the rack; that is the model's "rack" scope, and is why the firmware-hang
# effect is a rack halt, not the slot the old fabric-port test gave it.

class _StuckOpenLoop:
    """A loop-sense comparator stuck reading 'no current': wraps the real loop and lies about current."""

    def __init__(self, loop):
        self._loop = loop

    def current(self) -> bool:
        return False

    def __getattr__(self, name):
        return getattr(self._loop, name)


def inject_power_loss(rack, governor) -> list[bool]:
    """A governor loses power: its loop switch fails open and the loop loses current (scope: rack)."""
    governor.loop_switch_open = True
    rack.loop.propagate()
    return rack.running()


def inject_wire_cut(rack) -> list[bool]:
    """The loop wire or a connector opens: the loop reads open and every GPU halts (scope: rack)."""
    rack.loop.cut()
    rack.loop.propagate()
    return rack.running()


def inject_comparator_stuck_open(rack, governor) -> list[bool]:
    """The governor's loop-sense comparator is stuck open: it senses 'no current' though the loop
    carries it, opens its own switch, and the rack halts (scope: rack). Two sense periods: the loop
    debounces over two samples."""
    governor.loop = _StuckOpenLoop(rack.loop)
    rack.loop.propagate()
    rack.loop.propagate()
    return rack.running()


def inject_firmware_hang(rack, governor) -> list[bool]:
    """The governor's firmware hangs and its watchdog resets it into HALTED_INITIAL, whose loop switch
    is open; the loop loses current and the whole rack halts (scope: rack). The effect is a rack halt
    -- the loop opens -- not the one slot a fabric-port cut gives."""
    governor.loop_switch_open = True      # the watchdog reset leaves the switch open, as HALTED_INITIAL does
    rack.loop.propagate()
    return rack.running()


def inject_fabric_port_failure(rack, governor, ticks: int = 3, dt: float = 2.0) -> list[bool]:
    """A fabric port fails: the cut-off governor stops consuming heartbeats and its slot halts at
    heartbeat expiry; the loop stays closed (scope: one slot)."""
    rack.fabric.down.add(governor.chip_id)
    for _ in range(ticks):
        rack.tick(dt)
        rack.heartbeat()
    return rack.running()


def inject_authority_outage(rack, ticks: int = 3, dt: float = 2.0) -> list[bool]:
    """The heartbeat authority is unavailable longer than the expiry: no heartbeat ever arrives, so
    every slot halts -- but the loop stays closed. Every slot halts, so it counts as a rack event."""
    for _ in range(ticks):
        rack.tick(dt)
    return rack.running()


def inject_readback_stuck_open(rack, governor, beats: int = 2) -> list[bool]:
    """A switch readback is stuck open: its switch no longer matters to the loop, but the beacon names
    the governor LOOP_JUMPERED and the rack halts (scope: rack). The loop stays closed, so the beacon
    is what catches it."""
    rack.loop.jumper(governor.chip_id)
    governor.loop_switch_open = True
    for _ in range(beats):
        rack.heartbeat()
    return rack.running()


def inject_silent_member(rack, governor, beats: int = 2) -> list[bool]:
    """A roster member goes silent (a downed port the beacon sees): it is logged as a silent member and
    nothing halts -- a partition is safe, not a hazard."""
    rack.fabric.down.add(governor.chip_id)
    for _ in range(beats):
        rack.heartbeat()
    return rack.running()


def inject_missed_heartbeat(rack, dt: float = 2.0, beats: int = 4) -> list[bool]:
    """One heartbeat missed then recovered: the slot rides it out (a control; nothing should halt)."""
    for i in range(beats):
        rack.tick(dt)
        if i == 1:
            rack.heartbeat()
    return rack.running()
