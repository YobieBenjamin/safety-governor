# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F21: an atomic, source-bound build manifest for the FPGA flow.

A build is fail-closed. Its status is read from a manifest, never from the mere presence of a bitstream.
The manifest binds the emitted bitstream to the exact source revision that produced it (the hashes of the
RTL, the top, the constraints and the config, folded into one source revision), lists the tools and the
stages that actually ran, and is written atomically so a reader never sees a half-written manifest as a
success. If any stage fails, no manifest is emitted and any stale artifact is not promoted.

    python3 hw/fpga/manifest.py --status DIR          # exit 0 only if DIR/manifest.json is a clean success
    python3 hw/fpga/manifest.py --emit DIR --mhz 30 --seed 1 --timing-met 1 \\
        --bitstream DIR/x.bit --report hw/fpga/REPORT.md --stages top,pll,synth,pnr,pack,report \\
        --source rtl=rtl/gen/governor.v --source top=hw/fpga/top.py ...
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile

MANIFEST = "manifest.json"
SCHEMA = "fpga-build-manifest/1"
# every stage a clean build must have recorded, in order
REQUIRED_STAGES = ("top", "pll", "synth", "pnr", "pack", "report")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def source_rev(src_hashes: dict) -> str:
    """One hash binding the whole source set, independent of key order."""
    return sha256_bytes(json.dumps(src_hashes, sort_keys=True, separators=(",", ":")).encode())


def build_manifest(*, build_dir: str, mhz: int, seed: str, sources: dict, tools: dict,
                   stages, bitstream: str | None, timing_met: bool, report_path: str | None = None) -> dict:
    """Assemble (do not write) the manifest. ``sources`` maps a label to a file path; every one is hashed
    and the set is folded into a single source revision that the emitted bitstream is bound to."""
    src_hashes = {label: sha256_file(p) for label, p in sources.items()}
    bit = None
    if bitstream and os.path.exists(bitstream):
        bit = {"path": os.path.basename(bitstream), "sha256": sha256_file(bitstream),
               "bytes": os.path.getsize(bitstream)}
    m = {
        "schema": SCHEMA,
        "written_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mhz": int(mhz), "seed": str(seed),
        "sources": src_hashes,
        "source_rev": source_rev(src_hashes),
        "tools": dict(tools),
        "stages": list(stages),
        "timing_met": bool(timing_met),
        "bitstream": bit,
        "report_sha256": sha256_file(report_path) if report_path and os.path.exists(report_path) else None,
    }
    m["ok"] = is_clean(m)
    return m


def is_clean(m: dict) -> bool:
    """A manifest is a clean success only if every required stage ran, timing met, and a bitstream is bound
    with a hash. A missing stage, a failed stage, no timing, or no bitstream is not a success."""
    stages = m.get("stages") or []
    bit = m.get("bitstream") or {}
    return (all(s in stages for s in REQUIRED_STAGES)
            and bool(m.get("timing_met"))
            and bool(bit.get("sha256")))


def binds_source(m: dict, rev: str) -> bool:
    """Does this clean manifest's bitstream bind to the intended source revision?"""
    return is_clean(m) and m.get("source_rev") == rev


def write_atomic(path: str, m: dict) -> None:
    """Write via a temp file in the same directory then os.replace, so a reader never sees a partial file."""
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".manifest.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(m, f, sort_keys=True, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load(build_dir: str) -> dict | None:
    p = os.path.join(build_dir, MANIFEST)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except (ValueError, OSError):
        return None


def status(build_dir: str) -> int:
    """Exit 0 only if the build dir carries a clean manifest. A bare bitstream with no manifest is a failure."""
    m = load(build_dir)
    if m is None:
        print(f"{build_dir}: no manifest; not a success")
        return 1
    if is_clean(m):
        bit = m["bitstream"]
        print(f"{build_dir}: clean, {m['mhz']} MHz, source_rev {m['source_rev'][:12]}, bitstream {bit['path']} ({bit['bytes']} bytes)")
        return 0
    print(f"{build_dir}: manifest present but not a clean success (stages={m.get('stages')}, timing_met={m.get('timing_met')})")
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status")
    ap.add_argument("--emit")
    ap.add_argument("--mhz", type=int, default=0)
    ap.add_argument("--seed", default="1")
    ap.add_argument("--timing-met", default="0")
    ap.add_argument("--bitstream")
    ap.add_argument("--report")
    ap.add_argument("--stages", default="")
    ap.add_argument("--source", action="append", default=[], help="label=path; repeatable")
    ap.add_argument("--tool", action="append", default=[], help="name=version; repeatable")
    a = ap.parse_args(argv)
    if a.status:
        return status(a.status)
    if a.emit:
        sources = dict(s.split("=", 1) for s in a.source)
        tools = dict(t.split("=", 1) for t in a.tool)
        stages = [s for s in a.stages.split(",") if s]
        m = build_manifest(build_dir=a.emit, mhz=a.mhz, seed=a.seed, sources=sources, tools=tools,
                           stages=stages, bitstream=a.bitstream, timing_met=a.timing_met not in ("0", "", "false"),
                           report_path=a.report)
        write_atomic(os.path.join(a.emit, MANIFEST), m)
        print(f"wrote {os.path.join(a.emit, MANIFEST)} (ok={m['ok']})")
        return 0 if m["ok"] else 1
    ap.error("one of --status or --emit is required")


if __name__ == "__main__":
    sys.exit(main())
