#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# The hardware red team, gated on the Cyber Verification Program. It does nothing until the program has approved
# an API workspace and that workspace's key is configured, because without it Anthropic's safeguards stop adversarial
# work even on our own design (it happened on 22 October, docs/26 workstream 3).
#
#   CVP_APPROVED=1 ANTHROPIC_API_KEY=<key of the CVP-enrolled workspace> bash tools/agents/redteam_hw.sh
#
# Or put both in ~/.config/governor/cvp.env (mode 600) and run with no variables.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
[ -f "$HOME/.config/governor/cvp.env" ] && . "$HOME/.config/governor/cvp.env"
if [ "${CVP_APPROVED:-0}" != 1 ] || [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "red team: WAITING for the Cyber Verification Program."
  echo "  When Anthropic approves, enrol a workspace, create a key in it, then write ~/.config/governor/cvp.env:"
  echo "    CVP_APPROVED=1"
  echo "    ANTHROPIC_API_KEY=sk-ant-..."
  echo "  (chmod 600 that file) and run this again. Nothing was started."
  exit 3
fi
command -v claude >/dev/null || { echo "the claude CLI is not installed"; exit 2; }
DATE=$(date +%Y-%m-%d)
BR=exp/redteam-hw-$DATE
WT=$REPO/.worktrees/redteam-hw-$DATE
git -C "$REPO" worktree add -q "$WT" -b "$BR" main 2>/dev/null || git -C "$REPO" worktree add -q "$WT" "$BR"
cd "$WT" || exit 2
LOG=$REPO/.agents/redteam/$DATE; mkdir -p "$LOG"
echo "red team: branch $BR in $WT, log $LOG/claude.log"
claude -p "Read tools/agents/briefs/redteam-hw.md and carry it out on branch $BR. Date: $DATE." \
  --model "${REDTEAM_MODEL:-opus}" --max-turns "${REDTEAM_TURNS:-400}" --permission-mode acceptEdits \
  --allowedTools "Read" "Edit" "Write" "Glob" "Grep" "Bash(python*)" "Bash(.venv/*)" "Bash(git add*)" "Bash(git commit*)" \
  "Bash(git status*)" "Bash(git diff*)" "Bash(git log*)" "Bash(make *)" "Bash(bash rtl/*)" "Bash(ls*)" \
  --disallowedTools "Bash(git push*)" "WebFetch" "WebSearch" > "$LOG/claude.log" 2>&1
rc=$?
echo "red team finished (exit $rc). Findings: $WT/audit/redteam-$DATE/FINDINGS.md"
git -C "$WT" log --oneline main.."$BR" | head -20
exit $rc
