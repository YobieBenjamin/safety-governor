# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F21 (external audit): fail-closed FPGA builds with a source-bound manifest.

Before the fix the build reused build directories, several stages had no explicit failure return, callers
invoked build_at inside && / || lists that suppress errexit, and the success check only tested that a
bitstream existed and met timing, so a failed build could consume or leave a stale artifact and be read as a
success. The fix: fresh build directories, an explicit failure return after every stage, and an atomic
manifest that binds the emitted bitstream to the source revision that produced it, with status read from the
manifest rather than from a bitstream's mere presence.

Driving the 26-minute toolchain is out of scope here, so this exercises the build script's fail-closed logic
(hw/fpga/lib.sh) and the manifest builder (hw/fpga/manifest.py) directly. These fail on the pre-fix source
(neither module exists) and pass after the fix."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

FPGA = Path(__file__).resolve().parents[1] / "hw" / "fpga"


def _load_manifest_module():
    spec = importlib.util.spec_from_file_location("fpga_manifest_under_test", FPGA / "manifest.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


manifest = _load_manifest_module()


def _sources(tmp_path):
    a = tmp_path / "a.v"; a.write_text("module a; endmodule\n")
    b = tmp_path / "b.v"; b.write_text("module b; endmodule\n")
    return {"a": str(a), "b": str(b)}


def _bitstream(tmp_path):
    bit = tmp_path / "x.bit"; bit.write_bytes(b"\x00\x01\x02bits")
    return str(bit)


def test_a_clean_manifest_binds_the_bitstream_to_its_source_revision(tmp_path):
    srcs = _sources(tmp_path)
    m = manifest.build_manifest(build_dir=str(tmp_path), mhz=30, seed="1", sources=srcs, tools={"yosys": "x"},
                                stages=list(manifest.REQUIRED_STAGES), bitstream=_bitstream(tmp_path), timing_met=True)
    assert m["ok"] and manifest.is_clean(m)
    rev = m["source_rev"]
    assert manifest.binds_source(m, rev)
    # Change a source byte: the source revision moves, and the manifest no longer binds the old revision.
    Path(srcs["a"]).write_text("module a; wire changed; endmodule\n")
    m2 = manifest.build_manifest(build_dir=str(tmp_path), mhz=30, seed="1", sources=srcs, tools={"yosys": "x"},
                                 stages=list(manifest.REQUIRED_STAGES), bitstream=_bitstream(tmp_path), timing_met=True)
    assert m2["source_rev"] != rev
    assert not manifest.binds_source(m, m2["source_rev"])
    assert not manifest.binds_source(m2, rev)


def test_a_manifest_is_not_clean_if_a_stage_is_missing_or_timing_failed_or_no_bitstream(tmp_path):
    srcs = _sources(tmp_path)
    full = list(manifest.REQUIRED_STAGES)
    # a missing stage
    m = manifest.build_manifest(build_dir=str(tmp_path), mhz=30, seed="1", sources=srcs, tools={},
                                stages=full[:-1], bitstream=_bitstream(tmp_path), timing_met=True)
    assert not manifest.is_clean(m)
    # timing not met
    m = manifest.build_manifest(build_dir=str(tmp_path), mhz=30, seed="1", sources=srcs, tools={},
                                stages=full, bitstream=_bitstream(tmp_path), timing_met=False)
    assert not manifest.is_clean(m)
    # no bitstream
    m = manifest.build_manifest(build_dir=str(tmp_path), mhz=30, seed="1", sources=srcs, tools={},
                                stages=full, bitstream=None, timing_met=True)
    assert not manifest.is_clean(m)


def test_status_reads_the_manifest_not_the_mere_presence_of_a_bitstream(tmp_path):
    # A build dir with a bitstream but NO manifest is a failure: presence of a .bit is not a success.
    (tmp_path / "governor.bit").write_bytes(b"stale")
    assert manifest.status(str(tmp_path)) == 1
    # Write a clean manifest atomically; now status is a success.
    srcs = _sources(tmp_path)
    m = manifest.build_manifest(build_dir=str(tmp_path), mhz=30, seed="1", sources=srcs, tools={},
                                stages=list(manifest.REQUIRED_STAGES), bitstream=_bitstream(tmp_path), timing_met=True)
    manifest.write_atomic(str(tmp_path / manifest.MANIFEST), m)
    assert manifest.status(str(tmp_path)) == 0


# ---- fail-closed shell logic (hw/fpga/lib.sh) ----

_HARNESS = r'''
set -uo pipefail
. "{lib}"
D="$1"; FAIL_AT="$2"
build_once() {{
  local -a STAGES=()
  fresh_dir "$D"                                   # never reuse: wipe any stale artifact first
  run_stage top   -- true  || return 1
  run_stage pll   -- true  || return 1
  if [ "$FAIL_AT" = synth ]; then
    run_stage synth -- false || return 1           # a stubbed stage returns nonzero: the build must abort here
  else
    run_stage synth -- true  || return 1
  fi
  run_stage pnr   -- true  || return 1
  printf 'bits\n' > "$D/out.bit"                   # the artifact is written only after every prior stage passed
  run_stage report -- true || return 1
  printf '%s\n' "$(join_stages)" > "$D/stages.txt"
}}
build_once
'''


def _run(tmp_path, fail_at):
    d = tmp_path / "build" / "30mhz"
    script = _HARNESS.format(lib=str(FPGA / "lib.sh"))
    return subprocess.run(["bash", "-c", script, "_", str(d), fail_at], capture_output=True, text=True), d


def test_a_clean_run_writes_the_artifact_and_records_every_stage(tmp_path):
    proc, d = _run(tmp_path, "none")
    assert proc.returncode == 0, proc.stderr
    assert (d / "out.bit").read_text() == "bits\n"
    assert (d / "stages.txt").read_text().strip() == "top,pll,synth,pnr,report"


def test_a_failed_stage_aborts_and_does_not_promote_a_stale_artifact(tmp_path):
    d = tmp_path / "build" / "30mhz"
    d.mkdir(parents=True)
    # Seed an OLD successful artifact and a stale success marker, as an earlier build would have left.
    (d / "out.bit").write_text("OLD-STALE-BITSTREAM\n")
    (d / "stages.txt").write_text("top,pll,synth,pnr,report\n")
    proc, d = _run(tmp_path, "synth")
    assert proc.returncode != 0, "a failed stage must make the build fail"
    assert "stage 'synth' FAILED" in proc.stderr
    # The stale artifact was wiped by the fresh build dir and no new one was written: nothing is promoted.
    assert not (d / "out.bit").exists(), "the stale bitstream must not survive a failed build"
    assert not (d / "stages.txt").exists()


def test_build_script_wires_in_the_fail_closed_helpers_and_manifest(tmp_path):
    # The logic must be connected to the real build, not merely present in a library.
    txt = (FPGA / "build.sh").read_text()
    assert ". \"$HERE/lib.sh\"" in txt or 'source "$HERE/lib.sh"' in txt
    assert "fresh_dir" in txt and "run_stage" in txt
    assert "manifest.py" in txt and "--status" in txt       # the verdict is read from the manifest
    # build_at must return nonzero after a failed stage (explicit `|| return 1`).
    assert "|| return 1" in txt
