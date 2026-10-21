#!/usr/bin/env bash
# One revision round for an agent's branch: the gate's findings (verifier and reviewer) go back to the
# agent that built it, in its own session so it keeps its context, inside the same worktree and the
# same tool rules. Then the acceptance command, a commit of anything left over, a push (the pull
# request updates itself) and a comment on the pull request with what changed and what the agent
# disagrees with. Nothing merges here; the gate reviews the result again.
#
#   tools/agents/revise_pr.sh <wave> <id> <round>       # inside the clone that holds exp/<id>
#   REVISE_TURNS=30  BUDGET_USD=10  (the agent's model and effort as in run_wave.sh)
set -euo pipefail
set -E; trap 'echo "error: line $LINENO: $BASH_COMMAND (exit status $?)" >&2' ERR
WAVE="${1:?wave}"; ID="${2:?issue id}"; ROUND="${3:-1}"
OWNER="${GITHUB_OWNER:-YobieBenjamin}"
MODEL="${AGENT_MODEL:-sonnet}"; EFFORT="${EFFORT:-medium}"; TURNS="${REVISE_TURNS:-30}"; BUDGET="${BUDGET_USD:-10}"; TIMEOUT_MIN="${AGENT_TIMEOUT_MIN:-120}"
HERE="$(cd "$(dirname "$0")" && pwd)"; SPEC="${EXPERIMENTS_SPEC:-$HERE/../github/experiments.json}"
ROOT="$(git rev-parse --show-toplevel)"; REPO="$(basename "$ROOT")"
[ -d "$ROOT/.venv/bin" ] && export PATH="$ROOT/.venv/bin:$PATH"
LOG="$ROOT/.agents/wave-$WAVE"; P="$LOG/review/$ID"
BRANCH="exp/$(echo "$ID" | tr '[:upper:]' '[:lower:]')"; WT="$ROOT/.worktrees/$ID"
say() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }
jget() { python3 -c "import json,sys; v=json.loads(sys.argv[1]).get(sys.argv[2]); print('' if v is None else v)" "$1" "$2"; }
# shellcheck source=tools/agents/agent_rules.sh
. "$HERE/agent_rules.sh"
CLAUDE_VERSION=$(claude -v 2>/dev/null | head -1); PROMPTS_FLAG=""; python3 "$HERE/wave_lib.py" version_ok "$CLAUDE_VERSION" 2.1.259 && PROMPTS_FLAG="--permission-prompts none"
ADD_DIRS="$LOG"; for other in safety-governor safety hardware-and-silicon; do [ "$other" != "$REPO" ] && [ -d "$HOME/$other/.git" ] && ADD_DIRS="$ADD_DIRS $HOME/$other"; done

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
say "$ID: revision $ROUND on $MODEL ($( [ -n "$session" ] && echo "resuming session" || echo "fresh session"))"
set +e
cd "$WT"
if [ -n "$session" ]; then
  # shellcheck disable=SC2086
  claude -p "$(cat "$LOG/$ID.revise-$ROUND.md")" --resume "$session" --model "$MODEL" --effort "$EFFORT" --max-turns "$TURNS" --max-budget-usd "$BUDGET" \
    --permission-mode acceptEdits $PROMPTS_FLAG --allowedTools "${ALLOW[@]}" --disallowedTools "${DENY[@]}" --add-dir $ADD_DIRS \
    --output-format stream-json --verbose < /dev/null > "$rlog" 2> "$rlog.err" &
else
  # shellcheck disable=SC2086
  claude -p "$(python3 "$HERE/wave_lib.py" brief "$SPEC" "$ID")

$(cat "$LOG/$ID.revise-$ROUND.md")" --model "$MODEL" --effort "$EFFORT" --max-turns "$TURNS" --max-budget-usd "$BUDGET" \
    --permission-mode acceptEdits $PROMPTS_FLAG --allowedTools "${ALLOW[@]}" --disallowedTools "${DENY[@]}" --add-dir $ADD_DIRS \
    --output-format stream-json --verbose < /dev/null > "$rlog" 2> "$rlog.err" &
fi
cpid=$!
( trap - ERR; sleep "$((TIMEOUT_MIN * 60))"; kill -INT "$cpid" 2>/dev/null || true; sleep 90; kill -TERM "$cpid" 2>/dev/null || true ) & wpid=$!; disown $wpid 2>/dev/null || true
rc=0; wait "$cpid" || rc=$?
pkill -P "$wpid" 2>/dev/null || true; kill "$wpid" 2>/dev/null || true
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
{ echo "**Revision $ROUND** ($(date '+%Y-%m-%d %H:%M')): $(jget "$summary" turns) turns, estimated \$$(jget "$summary" cost_usd), acceptance \`${accept:-n/a}\`: **$acc**. The gate reviews the branch again."
  echo; echo "Agent summary:"; echo; jget "$summary" result; } > "$LOG/$ID.revise-$ROUND.comment.md"
cp "$LOG/$ID.revise-$ROUND.comment.md" "$LOG/$ID.comment.md"
pr=$(gh pr list --repo "$OWNER/$REPO" --head "$BRANCH" --state open --json number -q '.[0].number' 2>/dev/null || true)
[ -n "$pr" ] && gh pr comment "$pr" --repo "$OWNER/$REPO" --body-file "$LOG/$ID.revise-$ROUND.comment.md" >/dev/null 2>&1 || true
say "$ID: revision $ROUND done; acceptance $acc"
[ "$acc" = pass ]
