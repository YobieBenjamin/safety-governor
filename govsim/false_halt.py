"""N2: the false-halt rate model (``docs/07-verification-plan.md`` section 5, numeric).

A *false halt* is a halt with no hazard behind it. Each failure mode of the FMEA gets a rate, a
scope (it halts the whole rack by opening the loop, or only one slot or segment), and, where the
loop's or the beacon's filtering applies, the probability that a transient survives it.

Rates are in FIT (failures per 1e9 device-hours). They are planning values, each tagged with the
source family its order of magnitude comes from. They were not copied from a licensed table: the
IEC 61508 tables (IEC 61508-6 annex of failure-rate data, IEC 62380, SN 29500, MIL-HDBK-217F) are
the places to check them. Every row marked ``assumed`` is something N3 (an FPGA beside a real GPU)
must measure. The model is arithmetic only; ``tests/test_false_halt_model.py`` reproduces it and
injects each mode into ``govsim`` to confirm the effect column.
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

# Where "operators would switch the governor off" begins. Reference: Meta's Llama 3 paper reports
# 419 unexpected interruptions in 54 days on 16384 GPUs, i.e. about 12.4 per 72-GPU rack-year
# (computed below). A governor that adds more than a tenth of that baseline, about 1.2 rack halts
# per rack-year, is a visible new source of lost work. The tenth is a judgement, not a measurement;
# the interruption count is quoted from memory and must be checked against the paper.
LLAMA3_INTERRUPTIONS, LLAMA3_DAYS, LLAMA3_GPUS = 419, 54, 16384
BASELINE_INTERRUPTIONS_PER_RACK_YEAR = LLAMA3_INTERRUPTIONS / LLAMA3_GPUS * RACK_GOVERNORS * 365.0 / LLAMA3_DAYS
SWITCH_OFF_FRACTION = 0.10
SWITCH_OFF_THRESHOLD = SWITCH_OFF_FRACTION * BASELINE_INTERRUPTIONS_PER_RACK_YEAR


@dataclass(frozen=True)
class Mode:
    key: str
    failure: str                # the FMEA row
    fit: float                  # hard-fault rate per governor, FIT (0 for rows driven by transients)
    scope: str                  # "rack" opens the loop; "slot" halts one governor's GPU only
    source: str
    sim_effect: str             # what govsim must show when the mode is injected
    runtime: bool = True        # False: acts only at boot, no runtime halt


MODES = [
    Mode("gov_power", "Governor loses power", 200, "rack",
         "regulator plus connector, IEC 62380 / SN 29500 order of magnitude (assumed)",
         "loop opens; every GPU halts"),
    Mode("fw_hang", "Governor firmware hang (watchdog reset)", 500, "rack",
         "watchdog trips of small firmware, IEC 61508-6 software-fault allowance (assumed)",
         "no heartbeat consumed; heartbeat expiry halts the slot"),
    Mode("loop_wire", "Loop wire or connector opens", 40, "rack",
         "two connectors per governor at 20 FIT, MIL-HDBK-217F connector class",
         "loop reads open; every GPU halts"),
    Mode("comparator_stuck_open", "Loop sense comparator stuck open", 50, "rack",
         "analogue comparator IC datasheet failure class (assumed)",
         "the governor reads the loop open and halts the rack"),
    Mode("clock_glitch_detector", "Glitch detector false trip (clock glitch row)", 100, "rack",
         "on-die monitor, no public rate; assumed",
         "zeroize, SAFE, loop opens"),
    Mode("fabric_port", "Fabric port failure", 100, "slot",
         "PHY and connector, IEC 62380 order of magnitude (assumed)",
         "the cut-off governor halts its own slot at heartbeat expiry; the loop stays closed"),
    Mode("beacon_readback_stuck", "Switch readback stuck open (beacon names it)", 50, "rack",
         "readback comparator, same class as the loop sense (assumed)",
         "LOOP_JUMPERED: the rack halts at the next beacon"),
    Mode("fuse_read", "Fuse read failure", 20, "slot",
         "OTP macro, foundry qualification (assumed)", "boot refused", runtime=False),
    Mode("nvm_corruption", "NVM corruption", 100, "slot",
         "NVM macro with ECC, datasheet class (assumed)", "refuse to RUN on the next boot", runtime=False),
]
MODE = {m.key: m for m in MODES}

# Transient processes (events per device-hour, mean duration seconds). All assumed, N3 measures them.
SENSE_GLITCH_RATE_PER_H = 1e-4          # an EMI or supply glitch on the sense comparator, per governor
SENSE_GLITCH_MEAN_S = 20e-6
READBACK_GLITCH_RATE_PER_H = 1e-4
READBACK_GLITCH_MEAN_S = 20e-6
HEARTBEAT_HOP_LOSS = 1e-3               # per-frame loss on one ring link
AUTHORITY_OUTAGE_RATE_PER_H = 1e-5      # heartbeat authority unavailable for longer than the expiry


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
    """Expected false halts per rack-year: ``rack`` (loop opened, every GPU) and ``slot`` (one GPU),
    with the per-mode breakdown."""
    rows: dict[str, float] = {}
    for m in MODES:
        if m.runtime:
            rows[m.key] = fit_to_per_year(m.fit, n)
    rows["sense_glitch"] = SENSE_GLITCH_RATE_PER_H * HOURS_PER_YEAR * n * survive_debounce(SENSE_GLITCH_MEAN_S, samples=samples)
    rows["heartbeat_loss"] = heartbeat_loss_rate_per_h() * HOURS_PER_YEAR * n
    rows["authority_outage"] = AUTHORITY_OUTAGE_RATE_PER_H * HOURS_PER_YEAR      # one event halts every slot
    rows["beacon_transient"] = beacon_transient_rate_per_h(confirm) * HOURS_PER_YEAR * n
    scope = {m.key: m.scope for m in MODES}
    scope.update(sense_glitch="rack", heartbeat_loss="slot", authority_outage="slot", beacon_transient="rack")
    rack = sum(v for k, v in rows.items() if scope[k] == "rack")
    slot = sum(v for k, v in rows.items() if scope[k] == "slot")
    return {"rows": rows, "scope": scope, "rack": rack, "slot": slot, "total": rack + slot}


def verdict(total: float) -> str:
    return "below" if total < SWITCH_OFF_THRESHOLD else "ABOVE"
