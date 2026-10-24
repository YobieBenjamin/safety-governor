# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# F21: fail-closed build helpers, sourced by hw/fpga/build.sh and exercised directly by
# tests/test_f21_build_manifest.py. The logic lives here so it can be tested without the 26-minute toolchain.
#
# A build dir is never reused: fresh_dir wipes it first, so a stale artifact from an earlier run cannot
# survive into a new one. Every stage runs through run_stage, which returns nonzero the moment a tool fails,
# whatever the caller's errexit state; a build that calls `run_stage ... || return 1` after each stage cannot
# walk past a failed stage and consume a stale artifact. STAGES accumulates only the stages that actually
# succeeded, and goes into the manifest.

# fresh_dir DIR: remove DIR and recreate it empty. A build dir is never reused.
fresh_dir() {
  rm -rf "$1" && mkdir -p "$1"
}

# run_stage NAME -- CMD...: run CMD as stage NAME. On success, append NAME to STAGES and return 0. On any
# nonzero exit, print the failure and return 1, so the caller's `|| return 1` aborts the whole build. Never
# swallows a tool error.
run_stage() {
  local name="$1"; shift
  [ "${1:-}" = "--" ] && shift
  if "$@"; then
    STAGES+=("$name")
    return 0
  fi
  local rc=$?
  echo "== stage '$name' FAILED (exit $rc); build aborts fail-closed, no artifact promoted" >&2
  return 1
}

# join_stages: print the successful STAGES as a comma-separated list for the manifest.
join_stages() {
  local IFS=,
  echo "${STAGES[*]:-}"
}
