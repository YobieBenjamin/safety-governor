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

build_at() {   # build_at MHZ: one full build into $B/${MHZ}mhz; returns 0 if timing met
  local MHZ="$1" D="$B/${1}mhz"
  mkdir -p "$D"
  echo "== [$MHZ MHz] bench top from Amaranth"
  "$PY" "$HERE/top.py" "$D" "$MHZ"
  echo "== [$MHZ MHz] PLL 25 -> $MHZ MHz"
  ( cd "$D" && "$ECPPLL" -i 25 -o "$MHZ" -n pll50 --clkin_name clkin --clkout0_name clkout0 -f pll50.v > ecppll.log 2>&1 )
  grep -q "clkout0 frequency: $MHZ MHz" "$D/ecppll.log" || { echo "PLL cannot make exactly $MHZ MHz"; cat "$D/ecppll.log"; return 1; }
  cp "$HERE/ulx3s_top.v" "$HERE/ulx3s.lpf" "$D/"
  echo "== [$MHZ MHz] synthesis (yosys synth_ecp5)"
  ( cd "$D" && nice -n 10 "$YOSYS" -q -l yosys.log -p "read_verilog bench_top.v pll50.v ulx3s_top.v; \
      synth_ecp5 -top ulx3s_top -json top.json; tee -q -o synth_stat.txt stat" )
  echo "== [$MHZ MHz] place and route (nextpnr-ecp5 --85k, router2, seed $SEED)"
  if ! ( cd "$D" && nice -n 10 "$NEXTPNR" --85k --package CABGA381 --speed 6 --json top.json --lpf ulx3s.lpf \
        --textcfg top.config --report pnr_report.json --freq "$MHZ" --seed "$SEED" --router router2 \
        --timing-allow-fail -l nextpnr.log > /dev/null 2>&1 ); then
    echo "nextpnr failed; last lines of $D/nextpnr.log:"; tail -20 "$D/nextpnr.log"; return 1
  fi
  echo "== [$MHZ MHz] bitstream (ecppack)"
  ( cd "$D" && "$ECPPACK" --compress top.config "governor_ulx3s_85f_${MHZ}mhz.bit" > ecppack.log 2>&1 )
  "$PY" "$HERE/report.py" --met "$D"
}

BUILT=()
if [ -n "${CLK_MHZ:-}" ]; then
  build_at "$CLK_MHZ" && OK=1 || OK=0
  BUILT+=("$B/${CLK_MHZ}mhz")
else
  build_at 50 && OK=1 || OK=0
  BUILT+=("$B/50mhz")
  if [ $OK -eq 0 ]; then
    FB="$("$PY" "$HERE/report.py" --fallback "$B/50mhz" 40 30 25)"
    echo "== 50 MHz did not close; building the bench bitstream at $FB MHz"
    build_at "$FB" && OK=1 || OK=0
    BUILT+=("$B/${FB}mhz")
  fi
fi
cp "$B/${BUILT[0]##*/}/fw_chain.json" "$HERE/fw_chain.json"
"$PY" "$HERE/report.py" --write "$HERE/REPORT.md" --seed "$SEED" "${BUILT[@]}" || true
[ $OK -eq 1 ] && echo "OK: a timing-clean bitstream was built; see hw/fpga/REPORT.md" || echo "FAILED: no timing-clean bitstream"
[ $OK -eq 1 ]
