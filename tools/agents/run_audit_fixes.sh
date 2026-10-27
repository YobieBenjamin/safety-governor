#!/usr/bin/env bash
# Address the external audit (2026-10-23) end to end, on the Mac, in the correct order, unattended.
# It reuses the existing program machinery (run_program.sh: a wave of coding agents, then for every
# branch the gate of verify_pr.py + a local second read + a bounded cloud review, merging only when
# all are clean and CI is green, then the audit packet and a backup) and adds two things the audit
# asked for: the 28 findings as the spec, in dependency-ordered waves, and the PolyForm/CC-BY-NC
# license stamped across every repository.
#
#   bash tools/agents/run_audit_fixes.sh                 # stamp licenses, publish the issues, run waves 1-4
#   bash tools/agents/run_audit_fixes.sh --detach        # the same, in the background (nap-friendly)
#   bash tools/agents/run_audit_fixes.sh --stamp-only     # just stamp the licenses in every clone, then stop
#   bash tools/agents/run_audit_fixes.sh --publish-only   # just create the labels and issues on GitHub, then stop
#   bash tools/agents/run_audit_fixes.sh --dry-run        # print the plan, change nothing
#   bash tools/agents/run_audit_fixes.sh --from 2         # resume at wave 2 (skips what already merged)
#   bash tools/agents/run_audit_fixes.sh --status         # where the program is
#   bash tools/agents/run_audit_fixes.sh --stop           # stop every instance and its agents
#
# Waves follow the audit's section 6 roadmap:
#   1  the executable authority contract   F01 F02 F03 F04 F05 F06 F10 F11 (SG) + F07 F08 F22 (HS)
#   2  honest experiments and claims       F12 F13 F23 F04-audit F24 F25 (SG) + F09 (safety) + F27 (Watermark)
#   3  persistence and hardware contracts  F14 F15 F16 F17 F18 F19 F20 (SG)
#   4  build evidence and governance       F21 F26 F28 (SG)
# Each agent must add a discriminating test that fails on current source and passes after its fix,
# at the acceptance command the brief names, and never weaken an existing test. The gate enforces
# the rest. Nothing merges that the verifier, the review, CI and its dependencies do not all clear;
# everything else stays open with its review for a person, which is the point of the whole setup.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/paths.sh"   # WORK: where the clones live (the external drive when mounted, else $HOME)
SPEC="$HERE/../github/audit-fixes.json"
export EXPERIMENTS_SPEC="$SPEC"
export PROGRAM_REPOS="${PROGRAM_REPOS:-safety-governor safety hardware-and-silicon Watermark}"
export WAVES="${WAVES:-1 2 3 4}"
ALL_REPOS="${ALL_REPOS:-safety-governor safety hardware-and-silicon autonomic-graph-regulation Watermark}"

MODE=run; FROM=""
while [ $# -gt 0 ]; do
  case "$1" in
    --detach|--dry-run|--status|--stop) MODE="${1#--}" ;;
    --stamp-only) MODE="stamp-only" ;;
    --publish-only) MODE="publish-only" ;;
    --from) FROM="$2"; shift ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

# 1. License, in every repository. Deterministic, idempotent, no agent: the terms are indicated
#    everywhere before any code changes land, which is the standing requirement for all our work.
stamp_all() {
  local stamp="$WORK/safety-governor/tools/license/stamp.sh"
  [ -f "$stamp" ] || stamp="$HERE/../license/stamp.sh"
  for repo in $ALL_REPOS; do
    if [ -d "$WORK/$repo/.git" ]; then
      say "license: stamping $repo"
      bash "$stamp" "$WORK/$repo" || say "license: stamp of $repo reported a problem (continuing)"
    else
      say "license: $WORK/$repo is not a clone here; skipped (run setup_and_publish.sh first)"
    fi
  done
}

case "$MODE" in
  stamp-only) stamp_all; say "stamped; stopping (--stamp-only)"; exit 0 ;;
  stop)       exec bash "$HERE/run_program.sh" --stop ;;
  status)     exec bash "$HERE/run_program.sh" --status ;;
esac

if [ "$MODE" = "dry-run" ]; then
  say "DRY RUN"
  say "spec: $SPEC"
  python3 - "$SPEC" <<'PY' 2>/dev/null || true
import json, sys, collections
d = json.load(open(sys.argv[1]))
w = collections.defaultdict(list)
for i in d["issues"]:
    w[i["wave"]].append(i["id"])
for k in sorted(w):
    print(f"  wave {k}: " + ", ".join(w[k]))
PY
  say "would stamp licenses in: $ALL_REPOS"
  say "would publish labels+issues from the spec, then run waves $WAVES across: $PROGRAM_REPOS"
  exec bash "$HERE/run_program.sh" --dry-run
fi

# 2. Labels and issues from the audit spec (idempotent; it will not duplicate an existing issue).
publish_issues() {
  say "publishing audit-fix labels and issues from $(basename "$SPEC")"
  EXPERIMENTS_SPEC="$SPEC" bash "$HERE/../github/publish_experiments.sh" || say "publish reported a problem (continuing)"
}

case "$MODE" in
  publish-only) publish_issues; say "published; stopping (--publish-only)"; exit 0 ;;
esac

# 3. Stamp, publish, then run the gated waves. --detach hands off to run_program's own backgrounding.
stamp_all
publish_issues
say "handing off to run_program.sh (waves $WAVES, repos: $PROGRAM_REPOS)"
if [ -n "$FROM" ]; then
  exec bash "$HERE/run_program.sh" ${MODE:+--${MODE}} --from "$FROM"
else
  [ "$MODE" = "detach" ] && exec bash "$HERE/run_program.sh" --detach
  exec bash "$HERE/run_program.sh"
fi
