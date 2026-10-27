# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Copy the signoff reports (not the multi-GB run directory) from a LibreLane/OpenLane 2 run into
hw/librelane/evidence/, and record the GDS size and SHA-256.

Usage: python3 collect_evidence.py RUN_DIR EVIDENCE_DIR
Exit 1 if the run has no final/metrics.json (the flow did not finish).
"""
import hashlib
import pathlib
import re
import shutil
import sys

MAX_BYTES = 400_000          # anything bigger is truncated to head + tail, so the repo stays small
GDS_COMMIT_LIMIT = 20 * 1024 * 1024

# (step-dir suffix, glob inside it, name prefix in evidence/)
WANT = [
    ("yosys-synthesis", "reports/stat.log", "synth"),
    ("yosys-synthesis", "reports/stat.json", "synth"),
    ("yosys-synthesis", "reports/chk.rpt", "synth"),
    ("yosys-synthesis", "reports/latch.rpt", "synth"),
    ("verilator-lint", "*.log", "lint"),
    ("openroad-floorplan", "*.log", "floorplan"),
    ("openroad-ioplacement", "*.log", "ioplacement"),
    ("openroad-cts", "*.log", "cts"),
    ("openroad-globalrouting", "*.log", "grt"),
    ("openroad-detailedrouting", "*.log", "drt"),
    ("openroad-checkantennas-1", "reports/*", "antenna-postdrt"),
    ("openroad-checkantennas-1", "*.log", "antenna-postdrt"),
    ("openroad-fillinsertion", "*.log", "fill"),
    ("openroad-stapostpnr", "summary.rpt", "sta"),
    ("openroad-stapostpnr", "*/ws.*.rpt", "sta"),
    ("openroad-stapostpnr", "*/wns.*.rpt", "sta"),
    ("openroad-stapostpnr", "*/tns.*.rpt", "sta"),
    ("openroad-stapostpnr", "*/checks.rpt", "sta"),
    ("openroad-stapostpnr", "*/power.rpt", "sta"),
    ("openroad-stapostpnr", "*/skew.*.rpt", "sta"),
    ("openroad-stapostpnr", "*/max.rpt", "sta-paths"),
    ("openroad-stapostpnr", "*/min.rpt", "sta-paths"),
    ("openroad-irdropreport", "*.log", "irdrop"),
    ("openroad-irdropreport", "*.rpt", "irdrop"),
    ("magic-drc", "reports/*", "magic-drc"),
    ("magic-drc", "*.log", "magic-drc"),
    ("klayout-drc", "reports/*", "klayout-drc"),
    ("klayout-drc", "*.log", "klayout-drc"),
    ("klayout-xor", "*.log", "xor"),
    ("netgen-lvs", "reports/*", "lvs"),
    ("netgen-lvs", "*.log", "lvs"),
    ("checker-illegaloverlap", "*.log", "overlap"),
    ("misc-reportmanufacturability", "*.rpt", "manufacturability"),
]


def clip(src, dst):
    data = src.read_bytes()
    if len(data) > MAX_BYTES:
        half = MAX_BYTES // 2
        data = (data[:half] + f"\n\n[... {len(data) - MAX_BYTES} bytes cut by collect_evidence.py; "
                f"full file in the run dir ...]\n\n".encode() + data[-half:])
    dst.write_bytes(data)


def main():
    run, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    steps = sorted(p for p in run.iterdir() if p.is_dir() and re.match(r"\d+-", p.name))
    copied = 0
    for suffix, pattern, prefix in WANT:
        # the last step with this suffix wins (e.g. the post-route antenna check)
        match = [s for s in steps if re.sub(r"^\d+-", "", s.name) == suffix]
        if not match:
            continue
        step = match[-1]
        for f in sorted(step.glob(pattern)):
            if not f.is_file():
                continue
            rel = f.relative_to(step).as_posix().replace("/", "__").replace("reports__", "")
            clip(f, out / f"{prefix}__{rel}")
            copied += 1
    for name in ("metrics.json", "metrics.csv"):
        f = run / "final" / name
        if f.exists():
            shutil.copy(f, out / f"final__{name}")
    for name in ("resolved.json", "warning.log", "error.log"):
        f = run / name
        if f.exists():
            clip(f, out / f"run__{name}")
    gds = sorted((run / "final").glob("gds/*.gds")) if (run / "final").exists() else []
    lines = []
    for g in gds:
        h = hashlib.sha256(g.read_bytes()).hexdigest()
        size = g.stat().st_size
        lines.append(f"{h}  {size}  {g.name}")
        if size < GDS_COMMIT_LIMIT:
            shutil.copy(g, out / g.name)
    (out / "gds.sha256").write_text("\n".join(lines) + ("\n" if lines else "no GDS produced\n"))
    print(f"collect_evidence: {copied} reports copied to {out}; GDS: {lines or 'none'}")
    return 0 if (run / "final" / "metrics.json").exists() else 1


if __name__ == "__main__":
    sys.exit(main())
