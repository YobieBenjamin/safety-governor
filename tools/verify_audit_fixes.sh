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
# Exits non-zero on the first thing that does not hold, and says which.
set -uo pipefail
SG="$(cd "$(dirname "$0")/.." && pwd)"
HS="${HS:-$(cd "$SG/../hardware-and-silicon" 2>/dev/null && pwd)}"
[ -d "$HS/hardware_ref" ] || { echo "hardware-and-silicon not found beside safety-governor (set HS=)"; exit 2; }
A="$SG/audit/external-2026-10-22"
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
out=$(python3 -m pytest -p no:cacheprovider tests rtl/tests 2>&1); [ $? -eq 0 ] && ok "safety-governor tests: $(count "$out")" || { bad "safety-governor tests"; echo "$out" | tail -20; }
check "proofs: P0 to P13, the regression checks, the commit point, K0 to K5" make -s proof
check "governor harness" python3 -m govsim.harness
cp results/report.md "$TMP/report.before"; python3 -m govsim.cli sweep >/dev/null 2>&1
if diff <(grep -v Generated "$TMP/report.before") <(grep -v Generated results/report.md) >/dev/null; then ok "governor sweep: same verdicts as before"; else bad "governor sweep verdicts changed"; fi
git checkout -q results/report.md
if command -v ngspice >/dev/null; then check "halt-loop circuit simulation (39 ngspice runs, worst case under 1 ms)" bash -c 'o=$(python3 hw/loop/run_loop.py 2>&1); git checkout -q hw/loop/results.md; echo "$o" | grep -q "^PASS: every configuration halts every governor inside 1 ms"'; else echo "  SKIP  halt-loop simulation: ngspice not installed"; fi
cd "$HS"
out=$(python3 -m pytest -p no:cacheprovider tests 2>&1); [ $? -eq 0 ] && ok "hardware-and-silicon tests: $(count "$out")" || { bad "hardware-and-silicon tests"; echo "$out" | tail -20; }
out=$(python3 -m hardware_ref sweep --out "$TMP/hs-results" 2>&1)
echo "$out" | grep -q "RESULT: PASS" && ok "reference attack sweep: $(echo "$out" | grep -Eo '[0-9]+ attacks? blocked[^.]*' | head -1)$(echo "$out" | grep -q PASS && echo 'all categories pass')" || { bad "reference attack sweep"; echo "$out" | tail -10; }

echo "== 2. Every finding against the fixed code (must be NOT reproduced)"
cd "$SG"; expect "findings 1 and 2 (governor)" "NOT reproduced" "REPRODUCED" env PYTHONPATH=. python3 "$A/repro_sg.py"
cd "$HS"; expect "findings 3, 4 and 5 (reference stack)" "NOT reproduced" " REPRODUCED" env PYTHONPATH=. python3 "$A/repro_hs.py"
expect "5b: an older signed policy reloaded" "refused" "REPRODUCED" env PYTHONPATH=. python3 "$A/repro_rollback.py"

echo "== 3. Every finding against the audited snapshots (must be REPRODUCED)"
git -C "$SG" worktree add -q "$TMP/sg-old" dccc1e0 2>/dev/null && git -C "$HS" worktree add -q "$TMP/hs-old" 11eb119 2>/dev/null || { bad "could not check out dccc1e0 / 11eb119"; }
cd "$TMP/sg-old"; n=$(PYTHONPATH=. python3 "$A/repro_sg.py" 2>&1 | grep -c " REPRODUCED"); [ "$n" = 2 ] && ok "findings 1 and 2 reproduce on dccc1e0" || bad "findings 1 and 2 on dccc1e0: $n of 2 reproduced"
cd "$TMP/hs-old"; n=$(PYTHONPATH=. python3 "$A/repro_hs.py" 2>&1 | grep -c " REPRODUCED"); [ "$n" = 3 ] && ok "findings 3, 4 and 5 reproduce on 11eb119" || bad "findings 3 to 5 on 11eb119: $n of 3 reproduced"
expect "5b reproduces on 11eb119" "REPRODUCED" "refused" env PYTHONPATH=. python3 "$A/repro_rollback.py"

echo "== 4. The regression tests against the audited snapshots (must fail there)"
cp "$HS/tests/test_audit_2026_10_22.py" "$TMP/hs-old/tests/"
cd "$TMP/hs-old"; out=$(python3 -m pytest -q -p no:cacheprovider tests/test_audit_2026_10_22.py 2>&1); nf=$(echo "$out" | grep -c '^FAILED ')   # this repo's pytest config hides the summary count
[ "${nf:-0}" -ge 9 ] && ok "hardware-and-silicon regressions: ${nf} of 11 fail on 11eb119 (the other 2 check that what should still work does)" || bad "hardware-and-silicon regressions fail on 11eb119: only ${nf:-0}"
cd "$TMP/sg-old"; out=$(python3 -c "
from govsim.cluster import build_rack
r = build_rack(1, 'rack'); r.bring_up(); g = r.nodes[0].governor
print('quorum', g.command('POLICY_PROPOSE', {'image': {**r.make_policy_image(r.policy_version + 1), 'threshold': 0, 'signatures': []}})['ok'])
" 2>&1); echo "$out" | grep -q "quorum True" && ok "the governor's old code accepts the unsigned image the H19 test refuses" || bad "old governor check: $out"

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
