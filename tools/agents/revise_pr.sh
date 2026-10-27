#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# One revision round for an agent's branch: the gate's findings (verifier and reviewer) go back to the
# agent that built it, in its own session so it keeps its context, inside the same worktree and the
# same tool rules. Then the acceptance command, a commit of anything left over, a push (the pull
# request updates itself) and a comment on the pull request with what changed and what the agent
# disagrees with. Nothing merges here; the gate reviews the result again.
#
#   tools/agents/revise_pr.sh <wave> <id> <round>       # inside the clone that holds exp/<id>
#   REVISE_TURNS=30  BUDGET_USD=10  (the agent's model and effort as in run_wave.sh)
#   REVISE_BACKEND=auto|local|cloud   auto (default): the local model for the first round when one answers,
#     the cloud for the second. The local model gets a fresh session with the brief and the review (its
#     context is 64k; the cloud build session is often larger); the cloud resumes the agent's own session.
#     Wave 1 taught the split: two local rounds on WAVE-TRACE-CONFORMANCE-REPLAY took three and four hours, the second hit the clock
#     with no summary, and the gate still said revise; a cloud round is minutes and about a dollar.
#   REVISE_LOCAL_TURNS=40  REVISE_LOCAL_TIMEOUT_MIN=90   the local round's own caps (not the build's 80 / 240)
set -euo pipefail
set -E; trap 'echo "error: line $LINENO: $BASH_COMMAND (exit status $?)" >&2' ERR
WAVE="${1:?wave}"; ID="${2:?issue id}"; ROUND="${3:-1}"
OWNER="${GITHUB_OWNER:-YobieBenjamin}"
MODEL="${AGENT_MODEL:-sonnet}"; EFFORT="${EFFORT:-medium}"; TURNS="${REVISE_TURNS:-30}"; BUDGET="${BUDGET_USD:-10}"; TIMEOUT_MIN="${AGENT_TIMEOUT_MIN:-120}"
REVISE_BACKEND="${REVISE_BACKEND:-auto}"; LOCAL_TURNS="${REVISE_LOCAL_TURNS:-40}"; LOCAL_TIMEOUT_MIN="${REVISE_LOCAL_TIMEOUT_MIN:-90}"; LOCAL_LOCK="$HOME/.agents-local.lock"
HERE="$(cd "$(dirname "$0")" && pwd)"; SPEC="${EXPERIMENTS_SPEC:-$HERE/../github/experiments.json}"; . "$HERE/paths.sh"
ROOT="$(git rev-parse --show-toplevel)"; REPO="$(basename "$ROOT")"
[ -d "$ROOT/.venv/bin" ] && export PATH="$ROOT/.venv/bin:$PATH"
LOG="$ROOT/.agents/wave-$WAVE"; P="$LOG/review/$ID"
BRANCH="exp/$(echo "$ID" | tr '[:upper:]' '[:lower:]')"; WT="$ROOT/.worktrees/$ID"
say() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }
jget() { python3 -c "import json,sys; v=json.loads(sys.argv[1]).get(sys.argv[2]); print('' if v is None else v)" "$1" "$2"; }
# shellcheck source=tools/agents/agent_rules.sh
. "$HERE/agent_rules.sh"
# shellcheck source=tools/agents/local_model.sh
. "$HERE/local_model.sh"
claude_local() { if [ "$LOCAL_URL" = cloud ]; then claude "$@"; else ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_API_KEY="" ANTHROPIC_BASE_URL="$LOCAL_URL" claude "$@"; fi; }
local_lock_wait() { until mkdir "$LOCAL_LOCK" 2>/dev/null; do sleep 30; done; echo $$ > "$LOCAL_LOCK/pid"; }
local_lock_release() { rm -rf "$LOCAL_LOCK" 2>/dev/null || true; }
backend=cloud
case "$REVISE_BACKEND" in
  cloud) ;;
  local) find_local_model; [ "$LOCAL_OK" = 1 ] && backend=local || echo "REVISE_BACKEND=local but no local model answers; using the cloud" >&2 ;;
  *) if [ "$ROUND" -le 1 ]; then find_local_model; [ "$LOCAL_OK" = 1 ] && backend=local; fi ;;
esac
CLAUDE_VERSION=$(claude -v 2>/dev/null | head -1); PROMPTS_FLAG=""; python3 "$HERE/wave_lib.py" version_ok "$CLAUDE_VERSION" 2.1.259 && PROMPTS_FLAG="--permission-prompts none"
ADD_DIRS="$LOG"; for other in safety-governor safety hardware-and-silicon; do [ "$other" != "$REPO" ] && [ -d "$WORK/$other/.git" ] && ADD_DIRS="$ADD_DIRS $WORK/$other"; done

[ -f "$P/review.md" ] || { echo "no review at $P/review.md; run review_pr.sh first" >&2; exit 2; }
[ -d "$WT" ] || { git -C "$ROOT" worktree add -q "$WT" "$BRANCH"; }
number=$(gh issue list --repo "$OWNER/$REPO" --state all --limit 1000 --json number,title 2>/dev/null | python3 -c "
import json, sys
t = next(i['title'] for i in json.load(open(sys.argv[1]))['issues'] if i['id'] == sys.argv[2])
m = [i for i in json.load(sys.stdin) if i['title'] == t]; print(m[0]['number'] if m else '')" "$SPEC" "$ID")
accept=$(python3 -c "import json,sys; print(next(i.get('accept','') for i in json.load(open(sys.argv[1]))['issues'] if i['id']==sys.argv[2]))" "$SPEC" "$ID")
session=$(python3 "$HERE/wave_lib.py" summarize "$LOG/$ID.1.jsonl" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('session_id') or '')" || true)

{ echo "# Revision $ROUND of your work on #$number ($ID)"; echo
  echo "The gate reviewed the pull request made from your branch. Below are the deterministic verifier's findings and the reviewer's findings and claims list. You are in the same worktree, on branch \`$BRANCH\`, with your commits in place."; echo
  echo "For each finding: fix it, or, if you are sure it is mistaken, leave it and say exactly why in your final summary, with the file and line. Findings marked block must be fixed or refuted; a claim marked NOT SUPPORTED must be shown by a test or an artifact, or removed from the document that makes it. Where a finding says the acceptance tests less than the brief asks, widen the test, not the excuse."; echo
  echo "Rules, unchanged: never weaken, skip or delete a test; touch only the files the brief owns and the files already on this branch; no web, no sub-agents; run the acceptance command (\`${accept:-as in the brief}\`) at most three times; commit each fix with a message that names #$number and ends with the line: Agent: wave $WAVE, issue #$number (revision $ROUND). Do not push. Finish with a summary of at most fifteen lines: what changed, what you did not change and why."; echo
  echo "## The review"; echo; cat "$P/review.md"; echo
  [ -f "$P/verify.txt" ] && { echo "## The verifier, in full"; echo; echo '```'; cat "$P/verify.txt"; echo '```'; }
} > "$LOG/$ID.revise-$ROUND.md"

rlog="$LOG/$ID.revise-$ROUND.jsonl"
set +e
cd "$WT"
if [ "$backend" = local ]; then
  say "$ID: revision $ROUND on the local model $LOCAL_MODEL (fresh session; one local run at a time)"
  local_lock_wait
  # shellcheck disable=SC2086
  claude_local -p "$(local_prefix)$(python3 "$HERE/wave_lib.py" brief "$SPEC" "$ID")

$(cat "$LOG/$ID.revise-$ROUND.md")" --model "$LOCAL_MODEL" --max-turns "$LOCAL_TURNS" \
    --permission-mode acceptEdits $PROMPTS_FLAG --allowedTools "${ALLOW[@]}" --disallowedTools "${DENY[@]}" --add-dir $ADD_DIRS \
    --output-format stream-json --verbose < /dev/null > "$rlog" 2> "$rlog.err" &
  TIMEOUT_MIN="$LOCAL_TIMEOUT_MIN"
elif [ -n "$session" ]; then
  say "$ID: revision $ROUND on $MODEL (resuming session)"
  # shellcheck disable=SC2086
  claude -p "$(cat "$LOG/$ID.revise-$ROUND.md")" --resume "$session" --model "$MODEL" --effort "$EFFORT" --max-turns "$TURNS" --max-budget-usd "$BUDGET" \
    --permission-mode acceptEdits $PROMPTS_FLAG --allowedTools "${ALLOW[@]}" --disallowedTools "${DENY[@]}" --add-dir $ADD_DIRS \
    --output-format stream-json --verbose < /dev/null > "$rlog" 2> "$rlog.err" &
else
  say "$ID: revision $ROUND on $MODEL (fresh session)"
  # shellcheck disable=SC2086
  claude -p "$(python3 "$HERE/wave_lib.py" brief "$SPEC" "$ID")

$(cat "$LOG/$ID.revise-$ROUND.md")" --model "$MODEL" --effort "$EFFORT" --max-turns "$TURNS" --max-budget-usd "$BUDGET" \
    --permission-mode acceptEdits $PROMPTS_FLAG --allowedTools "${ALLOW[@]}" --disallowedTools "${DENY[@]}" --add-dir $ADD_DIRS \
    --output-format stream-json --verbose < /dev/null > "$rlog" 2> "$rlog.err" &
fi
cpid=$!
( trap - ERR; sleep "$((TIMEOUT_MIN * 60))"; sig_tree "$cpid" INT; sleep 90; sig_tree "$cpid" TERM; sleep 30; sig_tree "$cpid" KILL ) & wpid=$!; disown $wpid 2>/dev/null || true
rc=0; wait "$cpid" || rc=$?
sig_tree "$wpid" TERM; sig_tree "$cpid" KILL   # nothing of the agent survives its run
[ "$backend" = local ] && local_lock_release
cd "$ROOT"
set -e
summary=$(python3 "$HERE/wave_lib.py" summarize "$rlog")
say "$ID: revision $ROUND ended (exit $rc, $(jget "$summary" turns) turns, \$$(jget "$summary" cost_usd))"

# anything left uncommitted is committed as found; then the acceptance, the push, the comment
if [ -n "$(git -C "$WT" status --porcelain 2>/dev/null)" ]; then
  git -C "$WT" add -A >/dev/null 2>&1 && git -C "$WT" commit -q -m "Revision $ROUND: work left uncommitted by the agent, committed by the launcher (#$number)

Agent: wave $WAVE, issue #$number (revision $ROUND, launcher commit)" 2>/dev/null || true
fi
acc="not run"
if [ -n "$accept" ]; then
  set +e; (trap - ERR; cd "$WT" && bash -c "$accept") > "$LOG/$ID.accept.log" 2>&1; arc=$?; set -e
  if [ "$arc" = 0 ]; then acc="pass"; else acc="fail (exit $arc)"; fi
fi
git -C "$WT" push -q origin "$BRANCH" 2>>"$LOG/launcher.err" || say "$ID: push failed"
{ echo "**Revision $ROUND** ($(date '+%Y-%m-%d %H:%M')) on $( [ "$backend" = local ] && echo "the local model $LOCAL_MODEL" || echo "$MODEL"): $(jget "$summary" turns) turns, estimated \$$(jget "$summary" cost_usd), acceptance \`${accept:-n/a}\`: **$acc**. The gate reviews the branch again."
  echo; echo "Agent summary:"; echo
  if [ -n "$(jget "$summary" result)" ]; then jget "$summary" result; else echo "(none: the run ended at the ${TIMEOUT_MIN}-minute limit or without a final message; exit $rc)"; fi; } > "$LOG/$ID.revise-$ROUND.comment.md"
cp "$LOG/$ID.revise-$ROUND.comment.md" "$LOG/$ID.comment.md"
pr=$(gh pr list --repo "$OWNER/$REPO" --head "$BRANCH" --state open --json number -q '.[0].number' 2>/dev/null || true)
[ -n "$pr" ] && gh pr comment "$pr" --repo "$OWNER/$REPO" --body-file "$LOG/$ID.revise-$ROUND.comment.md" >/dev/null 2>&1 || true
say "$ID: revision $ROUND done; acceptance $acc"
[ "$acc" = pass ]
