#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# One command: governor_core RTL to GDS on sky130A, then the signoff gate.
#
#   hw/librelane/run.sh              build toolchain if needed, run the flow, collect evidence, check
#   hw/librelane/run.sh --check RUN  only collect evidence from an existing run dir and check it
#
# GOV_FLOW picks the engine:
#   local (default)    OpenLane 2.0.0 + conda tools from setup_toolchain.sh (works on the shared box)
#   librelane-docker   current LibreLane in its Docker image (a Mac or Linux box with Docker)
#   librelane-nix      current LibreLane through Nix
# Exit status is non-zero if the flow fails, any signoff check fails (latches, negative or thin
# slack, DRC, LVS, antenna, IR drop), the netlist-vs-RTL co-simulation fails, or the planted-bug
# control does NOT fail.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
CFG=${GOV_CONFIG:-$HERE/governor_core/config.json}   # a variant config lives beside it (dir:: paths are relative)
EVID=${GOV_EVIDENCE:-$HERE/evidence}
FLOW=${GOV_FLOW:-local}
TAG=${GOV_RUN_TAG:-signoff}
PY=${PYTHON:-python3}
[ -x "$REPO/.venv/bin/python" ] && PY=$REPO/.venv/bin/python

if [ "${1:-}" = "--check" ]; then
  RUN=$(cd "$2" && pwd)
else
  RUN=$HERE/governor_core/runs/$TAG
  rm -rf "$RUN"
  case "$FLOW" in
    local)
      "$HERE/setup_toolchain.sh" || { echo "FAIL: toolchain setup"; exit 1; }
      . "${GOV_TOOLS:-/tmp/exp-layout}/env.sh"
      nice -n 10 openlane --manual-pdk --pdk-root "$PDK_ROOT" --run-tag "$TAG" "$CFG"
      ;;
    librelane-docker)
      $PY -m pip install -q --upgrade librelane
      nice -n 10 librelane --dockerized --pdk sky130A --pdk-root "$HOME/.ciel" --run-tag "$TAG" "$CFG"
      export PDK_ROOT=$HOME/.ciel
      ;;
    librelane-nix)
      nix-shell "github:librelane/librelane/main" --run \
        "librelane --pdk sky130A --pdk-root $HOME/.ciel --run-tag $TAG $CFG"
      export PDK_ROOT=$HOME/.ciel
      ;;
    *) echo "unknown GOV_FLOW=$FLOW"; exit 2 ;;
  esac
  echo "flow exit status: $?"
fi

fails=0
"$PY" "$HERE/collect_evidence.py" "$RUN" "$EVID" || fails=$((fails + 1))
"$PY" "$HERE/check_signoff.py" "$RUN" --evidence "$EVID" | tee "$EVID/signoff-gate.txt"
[ "${PIPESTATUS[0]}" -eq 0 ] || fails=$((fails + 1))

# The routed netlist must behave exactly like the RTL, cycle by cycle, and a planted bug must be caught.
NL=$RUN/final/nl/governor_core.nl.v
PDK=${PDK_ROOT:-${GOV_TOOLS:-/tmp/exp-layout}/pdk}
if [ -f "$NL" ]; then
  {
    echo "== final routed netlist vs RTL"
    nice -n 10 "$PY" "$HERE/equiv/cosim.py" --rtl "$REPO/rtl/gen/governor_core.v" --netlist "$NL" \
      --pdk-root "$PDK" --cycles "${GOV_COSIM_CYCLES:-2000}" --seed 7
    echo "exit $?"
    for k in 0 1 2 3; do
      echo "== control: planted bug $k (must FAIL)"
      nice -n 10 "$PY" "$HERE/equiv/cosim.py" --rtl "$REPO/rtl/gen/governor_core.v" --netlist "$NL" \
        --pdk-root "$PDK" --cycles 500 --seed 7 --mutate "$k"
      echo "exit $?"
    done
  } 2>&1 | tee "$EVID/cosim.txt"
  "$PY" - "$EVID/cosim.txt" <<'EOF' || fails=$((fails + 1))
import sys
blocks = open(sys.argv[1]).read().split("== ")[1:]
ok = "COSIM PASS" in blocks[0] and blocks[0].rstrip().endswith("exit 0")
caught = sum("COSIM FAIL" in b and b.rstrip().endswith("exit 1") for b in blocks[1:])
print(f"cosim: routed netlist {'matches' if ok else 'DOES NOT match'} RTL; planted bugs caught {caught}/{len(blocks) - 1}")
sys.exit(0 if ok and caught == len(blocks) - 1 else 1)
EOF
else
  echo "FAIL: no final netlist at $NL"; fails=$((fails + 1))
fi

if [ "$fails" -eq 0 ]; then echo "run.sh: ALL CHECKS PASS"; else echo "run.sh: $fails check group(s) FAILED"; fi
exit $(( fails > 0 ))
