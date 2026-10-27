# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Signoff gate for a governor_core LibreLane/OpenLane 2 run.

Reads <run>/final/metrics.json (and the step reports for the bits metrics.json does not carry),
prints one line per tape-out check, writes evidence/metrics-summary.json and exits 1 if any
check that ran has failed. A check whose metric is missing counts as NOT RUN, which also fails
unless --allow-not-run names it.

Usage: python3 check_signoff.py RUN_DIR [--evidence DIR] [--allow-not-run NAME ...]
"""
import argparse
import json
import pathlib
import sys

CLOCK_NS = 20.0
MARGIN_NS = 0.10 * CLOCK_NS          # docs/08 section 5: 10 % margin at 50 MHz
IR_LIMIT_V = 0.05 * 1.8              # under 5 % of VDD


def corners(m, prefix):
    """{corner: value} for every per-corner metric key starting with prefix."""
    out = {}
    for k, v in m.items():
        if k.startswith(prefix + "__corner:"):
            out[k.split("__corner:", 1)[1]] = v
    return out


def checks(m):
    """Yield (name, status, detail). status is PASS, FAIL or NOT RUN."""
    def get(k):
        return m.get(k)

    def zero(name, key):
        v = get(key)
        if v is None:
            return (name, "NOT RUN", f"{key} missing")
        return (name, "PASS" if v == 0 else "FAIL", f"{key} = {v}")

    yield zero("synth: no latches", "design__inferred_latch__count")
    yield zero("synth: yosys check (loops, multiple drivers)", "synthesis__check_error__count")
    yield zero("synth: no unmapped cells", "design__instance_unmapped__count")
    yield zero("lint: no Verilator errors", "design__lint_error__count")

    for kind, floor in (("setup", MARGIN_NS), ("hold", 0.0)):
        per = corners(m, f"timing__{kind}__ws")
        if not per:
            yield (f"timing: {kind}", "NOT RUN", f"timing__{kind}__ws__corner:* missing")
            continue
        worst = min(per.values())
        wc = min(per, key=per.get)
        need = {"tt", "ss", "ff"}
        have = {c for c in need if any(f"_{c}_" in k for k in per)}
        status = "PASS" if worst >= floor and have == need else "FAIL"
        yield (f"timing: {kind} slack >= {floor:.2f} ns at tt/ss/ff", status,
               f"worst {worst:.3f} ns at {wc}; corners {len(per)}; " +
               ", ".join(f"{c}={v:.3f}" for c, v in sorted(per.items())))
    for key in ("design__max_slew_violation__count", "design__max_cap_violation__count"):
        yield zero(f"timing: {key.split('__')[1]}", key)

    yield zero("route: detailed-route DRC", "route__drc_errors")
    yield zero("DRC: Magic", "magic__drc_error__count")
    yield zero("DRC: KLayout", "klayout__drc_error__count")
    yield zero("LVS: Netgen", "design__lvs_error__count")
    yield zero("antenna: violating nets", "antenna__violating__nets")
    yield zero("power grid: disconnected", "design__power_grid_violation__count")
    yield zero("XOR: Magic vs KLayout stream-out", "design__xor_difference__count")

    ir = get("ir__drop__worst")
    if ir is None:
        yield ("IR drop < 5 % VDD", "NOT RUN", "ir__drop__worst missing")
    else:
        yield ("IR drop < 5 % VDD", "PASS" if ir < IR_LIMIT_V else "FAIL",
               f"worst {ir * 1000:.2f} mV vs limit {IR_LIMIT_V * 1000:.0f} mV")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--evidence")
    ap.add_argument("--allow-not-run", nargs="*", default=[])
    a = ap.parse_args()
    run = pathlib.Path(a.run)
    mpath = run / "final" / "metrics.json"
    if not mpath.exists():
        print(f"FAIL: {mpath} missing (flow did not finish)")
        return 1
    m = json.loads(mpath.read_text())
    rows = list(checks(m))
    bad = 0
    for name, status, detail in rows:
        allowed = status == "NOT RUN" and any(s in name for s in a.allow_not_run)
        flag = status if not allowed else "NOT RUN (allowed)"
        print(f"{flag:18s} {name:52s} {detail}")
        if status == "FAIL" or (status == "NOT RUN" and not allowed):
            bad += 1
    keep = {k: v for k, v in m.items() if not k.startswith("timing__unannotated")}
    summary = {"checks": [dict(name=n, status=s, detail=d) for n, s, d in rows],
               "headline": {k: m.get(k) for k in (
                   "design__instance__count", "design__instance__area", "design__die__area",
                   "design__core__area", "design__instance__utilization", "route__wirelength",
                   "ir__drop__worst", "power__total")},
               "metrics": keep}
    if a.evidence:
        out = pathlib.Path(a.evidence)
        out.mkdir(parents=True, exist_ok=True)
        (out / "metrics-summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(f"signoff gate: {len(rows) - bad} of {len(rows)} checks pass, {bad} failing")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
