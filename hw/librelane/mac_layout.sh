#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# The sky130 layout on a Mac (or any Linux box), on the current Verilog, with the antenna and timing fixes tried in
# order until the signoff gate passes. One command, nothing to type in between:
#
#   bash hw/librelane/mac_layout.sh            # engine, then variants a, b, c until one passes every check
#   VARIANTS="b-antenna-timing" bash hw/librelane/mac_layout.sh     # just one
#
# Engine: Docker if one is running (Docker Desktop, OrbStack, colima); otherwise it installs colima and the docker
# CLI with Homebrew (no sudo, no GUI) and starts a VM sized to this machine, with Rosetta so the image runs on Apple
# silicon whichever architecture it was built for. Nix is used only if GOV_FLOW=librelane-nix is set.
#
# The variants (configs beside config.json, each a documented change from it):
#   a-antenna                antenna repair back on; run 4 switched it off after a crash in the 2024 OpenROAD
#   b-antenna-timing         a + timing repair after global routing; the resizer may not trade setup for hold
#   c-antenna-timing-margin  b + diodes on every port, a lower antenna threshold, setup slack margins
# Each run's evidence goes to hw/librelane/evidence/<variant>/ and one line per variant to evidence/variants.md, pass
# or fail, so a failed variant is on the record like a passing one. Exit 0 only if a variant passes every check.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
VARIANTS=${VARIANTS:-"a-antenna b-antenna-timing c-antenna-timing-margin"}
OUT=$HERE/evidence
mkdir -p "$OUT"
say() { printf '\n== %s\n' "$*"; }

say "engine"
if [ "${GOV_FLOW:-}" = librelane-nix ]; then
  command -v nix >/dev/null || { echo "GOV_FLOW=librelane-nix but nix is not installed"; exit 2; }
elif docker info >/dev/null 2>&1; then
  echo "docker is running: $(docker info --format '{{.OperatingSystem}} {{.Architecture}}' 2>/dev/null)"
  export GOV_FLOW=librelane-docker
else
  command -v brew >/dev/null || { echo "no running Docker and no Homebrew to install colima: install Docker Desktop or Homebrew, then rerun"; exit 2; }
  for p in colima docker; do command -v "$p" >/dev/null || brew install "$p" || { echo "brew install $p failed"; exit 2; }; done
  CPUS=$( (sysctl -n hw.ncpu 2>/dev/null || nproc) | tr -d ' ')
  MEM=$(( $( (sysctl -n hw.memsize 2>/dev/null || echo 17179869184) ) / 1073741824 * 3 / 4 ))
  [ "$MEM" -gt 48 ] && MEM=48
  colima status >/dev/null 2>&1 || colima start --cpu "$CPUS" --memory "$MEM" --disk 80 --vm-type vz --vz-rosetta \
    || colima start --cpu "$CPUS" --memory "$MEM" --disk 80 \
    || { echo "colima would not start"; exit 2; }
  docker info >/dev/null 2>&1 || { echo "colima started but docker does not answer"; exit 2; }
  echo "colima: $CPUS cpus, $MEM GB"
  export GOV_FLOW=librelane-docker
fi

say "python environment"
PY=$REPO/.venv/bin/python
[ -x "$PY" ] || { python3 -m venv "$REPO/.venv" && "$PY" -m pip install -q -e "$REPO[dev]"; } || { echo "venv failed"; exit 2; }
"$PY" -m pip install -q --upgrade librelane || { echo "pip install librelane failed"; exit 2; }
echo "librelane $("$PY" -m pip show librelane 2>/dev/null | awk '/^Version/ {print $2}')"
"$PY" -m rtl.gen --check || { echo "the checked-in Verilog is stale; run python -m rtl.gen first"; exit 2; }
NETLIST_COMMIT=$(git -C "$REPO" rev-parse --short HEAD)

[ -f "$OUT/variants.md" ] || printf '| When | Commit | Variant | Result | Gate summary |\n|---|---|---|---|---|\n' > "$OUT/variants.md"
passed=""
for v in $VARIANTS; do
  cfg=$HERE/governor_core/config.$v.json
  [ -f "$cfg" ] || { echo "no $cfg"; continue; }
  say "variant $v"
  mkdir -p "$OUT/$v"
  t0=$(date +%s)
  GOV_CONFIG=$cfg GOV_EVIDENCE=$OUT/$v GOV_RUN_TAG=$v PYTHON=$PY bash "$HERE/run.sh" 2>&1 | tee "$OUT/$v/run.log"
  rc=${PIPESTATUS[0]}
  mins=$(( ($(date +%s) - t0) / 60 ))
  summary=$(grep -hE "^signoff gate:|^FAIL: .*missing" "$OUT/$v/signoff-gate.txt" 2>/dev/null | head -1)
  [ -n "$summary" ] || summary="no gate output (flow stopped: see run.log)"
  res=$([ "$rc" -eq 0 ] && echo PASS || echo FAIL)
  printf '| %s | %s | %s | %s (%s min) | %s |\n' "$(date '+%Y-%m-%d %H:%M')" "$NETLIST_COMMIT" "$v" "$res" "$mins" "$summary" >> "$OUT/variants.md"
  if [ "$rc" -eq 0 ]; then passed=$v; break; fi
done

say "result"
cat "$OUT/variants.md"
if [ -n "$passed" ]; then
  echo "mac_layout: variant $passed passes every signoff check on commit $NETLIST_COMMIT; evidence in $OUT/$passed"
  exit 0
fi
echo "mac_layout: no variant passed every check yet; each one's gate and log are in $OUT/<variant>/ (that is the next fix to make)"
exit 1
