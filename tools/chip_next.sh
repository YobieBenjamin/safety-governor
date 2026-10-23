#!/usr/bin/env bash
# The chip-side next steps, in order, in one command on the Mac mini:
#
#   bash ~/Downloads/chip_next.sh               # everything below, in order
#   ONLY="fpga discussion" bash ~/Downloads/chip_next.sh   # just some steps
#
#   publish     setup_and_publish.sh: apply the bundles in the inbox (91 and later), push, verify (19 checks)
#   layout      hw/librelane/mac_layout.sh: the sky130 layout on the current Verilog, antenna and timing variants
#               tried in order until the signoff gate passes (Docker, or colima installed with Homebrew)
#   fpga        hw/fpga/build.sh: the ULX3S bitstream with EXCLUDE driven through the firmware stand-in chain
#   redteam     tools/agents/redteam_hw.sh: the hardware red team, which waits (and says so) until the Cyber
#               Verification Program has approved a workspace (~/.config/governor/cvp.env)
#   discussion  tools/github/discussion_repo.sh: the separate discussion forum on GitHub
#
# Each step runs whether or not the one before it passed (they do not depend on each other once published), and
# the end prints one line per step: PASS, FAIL, WAITING or SKIPPED, with where its evidence is. Everything goes to
# chip_next.log beside the clones. Exit 0 only if every step that ran passed (WAITING is not a failure).
set -uo pipefail
W="${PROJECT_WORK:-}"
[ -n "$W" ] || { [ -d "/Volumes/External_4TB/Safety Experiments" ] && W="/Volumes/External_4TB/Safety Experiments" || W="$HOME"; }
SG="$W/safety-governor"
LOG="$W/chip_next.log"
ONLY=${ONLY:-"publish layout fpga redteam discussion"}
exec > >(tee -a "$LOG") 2>&1
echo; echo "---- $(date '+%Y-%m-%d %H:%M:%S') chip_next ($ONLY) ----"
declare -a RESULTS
want() { case " $ONLY " in *" $1 "*) return 0;; esac; return 1; }
run() {   # name, evidence, command...
  local name=$1 ev=$2; shift 2
  if ! want "$name"; then RESULTS+=("SKIPPED  $name"); return; fi
  printf '\n==================== %s ====================\n' "$name"
  local t0=$(date +%s); "$@"; local rc=$?; local mins=$(( ($(date +%s) - t0) / 60 ))
  case $rc in
    0) RESULTS+=("PASS     $name ($mins min)  $ev") ;;
    3) RESULTS+=("WAITING  $name  $ev") ;;
    *) RESULTS+=("FAIL     $name ($mins min, exit $rc)  $ev") ;;
  esac
}

# publish first: the later steps run from the drive clone, so it has to carry the newest scripts
if want publish; then
  if [ -f "$HOME/Downloads/setup_and_publish.sh" ]; then
    run publish "$W/setup.log" bash "$HOME/Downloads/setup_and_publish.sh"
  else
    run publish "$W/setup.log" bash "$SG/tools/github/setup_and_publish.sh"
  fi
fi
[ -d "$SG/.git" ] || { echo "no clone at $SG; the publish step has to create it first"; exit 2; }
cd "$SG" || exit 2

run layout     "$SG/hw/librelane/evidence/variants.md"          bash hw/librelane/mac_layout.sh
run fpga       "$SG/hw/fpga/REPORT.md"                           bash hw/fpga/build.sh
run redteam    "$SG/.agents/redteam/"                            bash tools/agents/redteam_hw.sh
run discussion "https://github.com/YobieBenjamin/chip-that-says-no-discussion/discussions" bash tools/github/discussion_repo.sh

# record: the evidence the layout and FPGA steps wrote is part of the record, pass or fail, so it is committed and
# pushed (author Yobie, like every commit in these repositories)
record() {
  git add hw/librelane/evidence hw/fpga/REPORT.md hw/fpga/fw_chain.json 2>/dev/null
  if git diff --cached --quiet; then echo "nothing new to record"; return 0; fi
  git -c user.name="Yobie Benjamin" -c user.email="yobie@icloud.com" commit -q -m "chip_next $(date '+%Y-%m-%d %H:%M'): layout variants and FPGA build results, pass or fail

$(for r in "${RESULTS[@]}"; do echo "$r"; done)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DkQpVYNjMdJtfzj74tR8ZC" && git push -q origin main && echo "recorded and pushed: $(git log --oneline -1)"
}
if want layout || want fpga; then ONLY="$ONLY record"; run record "git log" record; fi

printf '\n==================== summary ====================\n'
fail=0
for r in "${RESULTS[@]}"; do echo "$r"; case $r in FAIL*) fail=1;; esac; done
echo "full log: $LOG"
if [ "$fail" -eq 0 ]; then
  echo "chip_next: every step that ran passed or is waiting on someone else"
else
  echo "chip_next: a step failed; its evidence is named above. Nothing was undone."
fi
exit $fail
