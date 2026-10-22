#!/usr/bin/env bash
# One command: does every fix from the 22 October audit hold, and was every finding real?
#
#   bash tools/verify_audit_fixes.sh            (from safety-governor; hardware-and-silicon beside it)
#
# 1. The fixed code: every test suite, every proof, both attack sweeps, the harness, the loop simulation.
# 2. Every finding against the fixed code: each reproduction script must print NOT reproduced.
# 3. Every finding against the snapshot the auditor used (dccc1e0, 11eb119), in throwaway worktrees:
#    each must print REPRODUCED, or the test proves nothing.
# 4. The new regression tests run against those old snapshots: they must fail there.
# 5. Each fix reverted on its own: its regressions must fail by assertion, never by an interface error,
#    and the legitimate operations must still pass (tools/audit_evidence.py).
# Exits non-zero on the first thing that does not hold, and says which.
set -uo pipefail
SG="$(cd "$(dirname "$0")/.." && pwd)"
HS="${HS:-$(cd "$SG/../hardware-and-silicon" 2>/dev/null && pwd)}"
[ -d "$HS/hardware_ref" ] || { echo "hardware-and-silicon not found beside safety-governor (set HS=)"; exit 2; }
A="$SG/audit/external-2026-10-22"

# Each repository runs in its own .venv, built the way its run.sh builds it, so this works on a Mac whose
# python3 has none of the libraries (the first version called plain python3 and failed there).
pick_python() {
  if [ -n "${PYTHON:-}" ]; then echo "$PYTHON"; return; fi
  for p in python3.14 python3.13 python3.12 python3.11 python3; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then echo "$p"; return; fi
  done
  echo "no Python 3.11 or newer on PATH (set PYTHON=/path/to/python3.x)" >&2; exit 2
}
venv() {   # $1 repo dir; prints the venv's python, creating and filling the venv on first use
  local d="$1" base; base="$(pick_python)" || exit 2
  if [ ! -x "$d/.venv/bin/python" ]; then echo "  setting up $d/.venv (first run only)" >&2; "$base" -m venv "$d/.venv" || exit 2; fi
  if ! "$d/.venv/bin/python" -c 'import pytest' >/dev/null 2>&1 || [ "$d/pyproject.toml" -nt "$d/.venv/.verified" ]; then
    (cd "$d" && .venv/bin/python -m pip install -q -U pip >/dev/null && .venv/bin/python -m pip install -q -e ".[dev]" >/dev/null) \
      || { echo "pip could not install $d's dependencies (offline?)" >&2; exit 2; }
    touch "$d/.venv/.verified"
  fi
  echo "$d/.venv/bin/python"
}
SGPY="$(venv "$SG")" || exit 2
HSPY="$(venv "$HS")" || exit 2
TMP="$(mktemp -d)"; trap 'git -C "$SG" worktree remove --force "$TMP/sg-old" >/dev/null 2>&1; git -C "$HS" worktree remove --force "$TMP/hs-old" >/dev/null 2>&1; rm -rf "$TMP"' EXIT
pass=0; fail=0
ok()  { echo "  PASS  $*"; pass=$((pass+1)); }
bad() { echo "  FAIL  $*"; fail=$((fail+1)); }
check() { local name="$1"; shift; local out; if out="$("$@" 2>&1)"; then ok "$name"; else bad "$name"; echo "$out" | tail -15 | sed 's/^/        /'; fi; }
expect() { local name="$1" want="$2" notwant="$3"; shift 3; local out; out="$("$@" 2>&1)"
  if echo "$out" | grep -q "$want" && ! echo "$out" | grep -q "$notwant"; then ok "$name"; else bad "$name"; echo "$out" | sed 's/^/        /'; fi; }
count() { echo "$1" | grep -Eo '[0-9]+ passed' | tail -1; }

echo "== 1. The fixed code"
cd "$SG"
out=$("$SGPY" -m pytest -p no:cacheprovider tests rtl/tests 2>&1); [ $? -eq 0 ] && ok "safety-governor tests: $(count "$out")" || { bad "safety-governor tests"; echo "$out" | tail -20; }
check "proofs: P0 to P13, the regression checks, the commit point, K0 to K5" bash -c "\"$SGPY\" proofs/core_invariants.py && \"$SGPY\" proofs/commit_point.py && \"$SGPY\" proofs/no_global_kill_switch.py"
check "checked-in Verilog matches the Amaranth source (CI's rtl.gen --check)" "$SGPY" -m rtl.gen --check
check "governor harness" "$SGPY" -m govsim.harness
cp results/report.md "$TMP/report.before"; "$SGPY" -m govsim.cli sweep >/dev/null 2>&1
if diff <(grep -v Generated "$TMP/report.before") <(grep -v Generated results/report.md) >/dev/null; then ok "governor sweep: same verdicts as before"; else bad "governor sweep verdicts changed"; fi
git checkout -q results/report.md
if command -v ngspice >/dev/null; then check "halt-loop circuit simulation (39 ngspice runs, worst case under 1 ms)" bash -c 'o=$("$0" hw/loop/run_loop.py 2>&1); git checkout -q hw/loop/results.md; echo "$o" | grep -q "^PASS: every configuration halts every governor inside 1 ms"' "$SGPY"; else echo "  SKIP  halt-loop simulation: ngspice not installed"; fi
cd "$HS"
out=$("$HSPY" -m pytest -p no:cacheprovider tests 2>&1); [ $? -eq 0 ] && ok "hardware-and-silicon tests: $(count "$out")" || { bad "hardware-and-silicon tests"; echo "$out" | tail -20; }
out=$("$HSPY" -m hardware_ref sweep --out "$TMP/hs-results" 2>&1)
echo "$out" | grep -q "RESULT: PASS" && ok "reference attack sweep: $(echo "$out" | grep -Eo '[0-9]+ attacks? blocked[^.]*' | head -1)$(echo "$out" | grep -q PASS && echo 'all categories pass')" || { bad "reference attack sweep"; echo "$out" | tail -10; }

echo "== 2. Every finding against the fixed code (must be NOT reproduced)"
cd "$SG"; expect "findings 1 and 2 (governor)" "NOT reproduced" "REPRODUCED" env PYTHONPATH=. "$SGPY" "$A/repro_sg.py"
cd "$HS"; expect "findings 3, 4 and 5 (reference stack)" "NOT reproduced" " REPRODUCED" env PYTHONPATH=. "$HSPY" "$A/repro_hs.py"
expect "5b: an older signed policy reloaded" "refused" "REPRODUCED" env PYTHONPATH=. "$HSPY" "$A/repro_rollback.py"

echo "== 3. Every finding against the audited snapshots (must be REPRODUCED)"
own() { (cd "$1" && PYTHONPATH=. "$2" -c "import os, $3; print(os.path.realpath($3.__file__))") 2>/dev/null; }
git -C "$SG" worktree add -q "$TMP/sg-old" dccc1e0 2>/dev/null && git -C "$HS" worktree add -q "$TMP/hs-old" 11eb119 2>/dev/null || { bad "could not check out dccc1e0 / 11eb119"; }
w=$(own "$TMP/sg-old" "$SGPY" govsim); case "$w" in "$(cd "$TMP/sg-old" && pwd -P)"/*) ok "the old governor worktree imports its own code";; *) bad "the old governor worktree imports $w, not dccc1e0";; esac
w=$(own "$TMP/hs-old" "$HSPY" hardware_ref); case "$w" in "$(cd "$TMP/hs-old" && pwd -P)"/*) ok "the old reference-stack worktree imports its own code";; *) bad "the old reference worktree imports $w, not 11eb119";; esac
cd "$TMP/sg-old"; n=$(PYTHONPATH=. "$SGPY" "$A/repro_sg.py" 2>&1 | grep -c " REPRODUCED"); [ "$n" = 2 ] && ok "findings 1 and 2 reproduce on dccc1e0" || bad "findings 1 and 2 on dccc1e0: $n of 2 reproduced"
cd "$TMP/hs-old"; n=$(PYTHONPATH=. "$HSPY" "$A/repro_hs.py" 2>&1 | grep -c " REPRODUCED"); [ "$n" = 3 ] && ok "findings 3, 4 and 5 reproduce on 11eb119" || bad "findings 3 to 5 on 11eb119: $n of 3 reproduced"
expect "5b reproduces on 11eb119" "REPRODUCED" "refused" env PYTHONPATH=. "$HSPY" "$A/repro_rollback.py"

echo "== 4. The regression tests against the audited snapshots (must fail there)"
cp "$HS/tests/test_audit_2026_10_22.py" "$TMP/hs-old/tests/"
cd "$TMP/hs-old"; out=$(PYTHONPATH=. "$HSPY" -m pytest -q -p no:cacheprovider tests/test_audit_2026_10_22.py 2>&1); nf=$(echo "$out" | grep -c '^FAILED ')   # this repo's pytest config hides the summary count
[ "${nf:-0}" -ge 9 ] && ok "hardware-and-silicon regressions: ${nf} of 11 fail on 11eb119 (the other 2 check that what should still work does)" || bad "hardware-and-silicon regressions fail on 11eb119: only ${nf:-0}"
cd "$TMP/sg-old"; out=$(PYTHONPATH=. "$SGPY" -c "
from govsim.cluster import build_rack
r = build_rack(1, 'rack'); r.bring_up(); g = r.nodes[0].governor
print('quorum', g.command('POLICY_PROPOSE', {'image': {**r.make_policy_image(r.policy_version + 1), 'threshold': 0, 'signatures': []}})['ok'])
" 2>&1); echo "$out" | grep -q "quorum True" && ok "the governor's old code accepts the unsigned image the H19 test refuses" || bad "old governor check: $out"

echo "== 5. Each regression fails for the intended reason (an assertion, not an interface error)"
cd "$SG"; ev=$("$SGPY" tools/audit_evidence.py --python "$SGPY" --hs-python "$HSPY" --hs "$HS" --out "$TMP/EVIDENCE.md" 2>&1)
if [ $? -eq 0 ]; then ok "every revert makes its regressions fail by assertion, and every legitimate path still works ($(echo "$ev" | grep -c '\] ok') findings)"; else bad "evidence"; echo "$ev" | grep -v '\] ok' | sed 's/^/        /'; fi

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
