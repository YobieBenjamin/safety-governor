#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# One command: Amaranth -> Verilog -> Yosys -> nextpnr-ecp5 -> ecppack, for the ULX3S (ECP5 LFE5U-85F, -6, CABGA381).
#
#   hw/fpga/build.sh                  # build at 50 MHz (the ASIC flow's clock); if timing fails there, also build
#                                     # at the fastest of 40/30/25 MHz that the 50 MHz result says should close
#   CLK_MHZ=25 hw/fpga/build.sh       # one build at a chosen clock, no fallback
#
# Writes hw/fpga/build/<MHz>mhz/governor_ulx3s_85f_<MHz>mhz.bit and hw/fpga/REPORT.md (utilisation, Fmax, critical
# path, for every build tried). Every tool is a pip wheel (yowasp-yosys, yowasp-nextpnr-ecp5 with ecppack and
# ecppll), so nothing is installed on the system.
# Exit status: 0 if at least one timing-clean bitstream was built (REPORT.md says whether that was at 50 MHz),
# 1 if none was.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
B="$HERE/build"
SEED="${SEED:-1}"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"
BIN="$(dirname "$PY")"
# shellcheck source=lib.sh
. "$HERE/lib.sh"      # F21: fresh_dir, run_stage, join_stages (fail-closed build helpers)
mkdir -p "$B"
cd "$ROOT"

need() { [ -x "$BIN/$1" ] || command -v "$1" >/dev/null 2>&1; }
if ! need yowasp-yosys || ! need yowasp-nextpnr-ecp5; then
  echo "== installing the open toolchain wheels (yowasp-yosys, yowasp-nextpnr-ecp5)"
  "$PY" -m pip install -q yowasp-yosys yowasp-nextpnr-ecp5
fi
t() { if [ -x "$BIN/$1" ]; then echo "$BIN/$1"; else command -v "$1"; fi; }
YOSYS="$(t yowasp-yosys)"; NEXTPNR="$(t yowasp-nextpnr-ecp5)"; ECPPACK="$(t yowasp-ecppack)"; ECPPLL="$(t yowasp-ecppll)"

echo "== checked-in Verilog is current (python -m rtl.gen --check)"
"$PY" -m rtl.gen --check

pll_ok() {   # the PLL stage: run ecppll and confirm it makes exactly MHZ, else fail
  local D="$1" MHZ="$2"
  ( cd "$D" && "$ECPPLL" -i 25 -o "$MHZ" -n pll50 --clkin_name clkin --clkout0_name clkout0 -f pll50.v > ecppll.log 2>&1 ) || return 1
  grep -q "clkout0 frequency: $MHZ MHz" "$D/ecppll.log" || { echo "PLL cannot make exactly $MHZ MHz"; cat "$D/ecppll.log"; return 1; }
  cp "$HERE/ulx3s_top.v" "$HERE/ulx3s.lpf" "$D/"
}

pnr_ok() {   # place and route; on failure show the tail and fail
  local D="$1" MHZ="$2"
  if ! ( cd "$D" && nice -n 10 "$NEXTPNR" --85k --package CABGA381 --speed 6 --json top.json --lpf ulx3s.lpf \
        --textcfg top.config --report pnr_report.json --freq "$MHZ" --seed "$SEED" --router router2 \
        --timing-allow-fail -l nextpnr.log > /dev/null 2>&1 ); then
    echo "nextpnr failed; last lines of $D/nextpnr.log:"; tail -20 "$D/nextpnr.log"; return 1
  fi
}

build_at() {   # build_at MHZ: one full build into a FRESH $B/${MHZ}mhz; returns 0 only if timing met
  local MHZ="$1" D="$B/${1}mhz"
  local -a STAGES=()
  fresh_dir "$D"                                            # F21: never reuse a build dir; no stale artifact survives
  echo "== [$MHZ MHz] bench top from Amaranth"
  run_stage top -- "$PY" "$HERE/top.py" "$D" "$MHZ" || return 1
  echo "== [$MHZ MHz] PLL 25 -> $MHZ MHz"
  run_stage pll -- pll_ok "$D" "$MHZ" || return 1
  echo "== [$MHZ MHz] synthesis (yosys synth_ecp5)"
  run_stage synth -- bash -c 'cd "$1" && nice -n 10 "$2" -q -l yosys.log -p "read_verilog bench_top.v pll50.v ulx3s_top.v; synth_ecp5 -top ulx3s_top -json top.json; tee -q -o synth_stat.txt stat"' _ "$D" "$YOSYS" || return 1
  echo "== [$MHZ MHz] place and route (nextpnr-ecp5 --85k, router2, seed $SEED)"
  run_stage pnr -- pnr_ok "$D" "$MHZ" || return 1
  echo "== [$MHZ MHz] bitstream (ecppack)"
  run_stage pack -- bash -c 'cd "$1" && "$2" --compress top.config "governor_ulx3s_85f_${3}mhz.bit" > ecppack.log 2>&1' _ "$D" "$ECPPACK" "$MHZ" || return 1
  run_stage report -- "$PY" "$HERE/report.py" --met "$D" || return 1
  # F21: emit an atomic, source-bound manifest only after every stage above succeeded. Status is read from it.
  emit_manifest "$D" "$MHZ"
}

emit_manifest() {   # emit_manifest DIR MHZ: bind the emitted bitstream to the source revision that built it
  local D="$1" MHZ="$2" BIT="$D/governor_ulx3s_85f_${2}mhz.bit"
  "$PY" "$HERE/manifest.py" --emit "$D" --mhz "$MHZ" --seed "$SEED" --timing-met 1 \
    --bitstream "$BIT" \
    --stages "$(join_stages)" \
    --source rtl_governor="$ROOT/rtl/gen/governor_core.v" \
    --source rtl_smbus="$ROOT/rtl/gen/smbus.v" \
    --source fpga_top="$HERE/top.py" \
    --source ulx3s_top="$HERE/ulx3s_top.v" \
    --source ulx3s_lpf="$HERE/ulx3s.lpf" \
    --source bench_top="$D/bench_top.v" \
    --source pll="$D/pll50.v" \
    --source top_config="$D/top.config" \
    --tool yowasp-yosys="$("$YOSYS" --version 2>/dev/null | head -1 || echo unknown)" \
    --tool yowasp-nextpnr-ecp5="$("$NEXTPNR" --version 2>&1 | head -1 || echo unknown)"
}

BUILT=()
if [ -n "${CLK_MHZ:-}" ]; then
  build_at "$CLK_MHZ" || true
  BUILT+=("$B/${CLK_MHZ}mhz")
else
  build_at 50 || true
  BUILT+=("$B/50mhz")
  # F21: a fallback is attempted only if the 50 MHz run did not leave a clean manifest.
  if ! "$PY" "$HERE/manifest.py" --status "$B/50mhz" >/dev/null 2>&1; then
    FB="$("$PY" "$HERE/report.py" --fallback "$B/50mhz" 40 30 25)"
    echo "== 50 MHz did not close; building the bench bitstream at $FB MHz"
    build_at "$FB" || true
    BUILT+=("$B/${FB}mhz")
  fi
fi
# F21: the verdict is read from the manifests the builds left, not from a bitstream's presence or timing alone.
CLEAN=""
for D in "${BUILT[@]}"; do
  if "$PY" "$HERE/manifest.py" --status "$D" >/dev/null 2>&1; then CLEAN="$D"; break; fi
done
if [ -n "$CLEAN" ]; then
  cp "$CLEAN/fw_chain.json" "$HERE/fw_chain.json"
  "$PY" "$HERE/report.py" --write "$HERE/REPORT.md" --seed "$SEED" "${BUILT[@]}" || true
  # keep a dated historical copy of the report and the winning manifest, so history is not overwritten
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$B/history"
  cp "$HERE/REPORT.md" "$B/history/REPORT-$STAMP.md" || true
  cp "$CLEAN/manifest.json" "$B/history/manifest-$STAMP.json" || true
  echo "OK: a timing-clean bitstream was built and bound by manifest ($CLEAN); see hw/fpga/REPORT.md"
  exit 0
else
  "$PY" "$HERE/report.py" --write "$HERE/REPORT.md" --seed "$SEED" "${BUILT[@]}" || true
  echo "FAILED: no timing-clean bitstream with a clean manifest"
  exit 1
fi
