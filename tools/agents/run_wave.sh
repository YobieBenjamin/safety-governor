#!/usr/bin/env bash
# Launch one wave of the experiment program as parallel coding agents, one per issue, each in its
# own git worktree on its own branch, on the mid-tier model, with a turn cap. The brief is the
# issue body (tools/github/experiments.json, published by tools/github/publish_experiments.sh).
#
#   tools/agents/run_wave.sh 1              # wave 1, up to 3 agents at a time
#   tools/agents/run_wave.sh 2 --dry-run    # print briefs and commands, start nothing
#   AGENT_MODEL=sonnet MAX_TURNS=60 PARALLEL=3 tools/agents/run_wave.sh 1
#
# Needs: gh (logged in), git, the claude CLI, python3. Run inside a clone of the repository the
# wave's issues belong to; issues in another repository are listed, not started, with the command
# to run there. A sparse clone (the safety repository without its recordings) gives sparse
# worktrees. Review each pull request before merging; the launcher never merges.
set -euo pipefail
WAVE="${1:?wave number}"; shift || true
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
OWNER="${GITHUB_OWNER:-YobieBenjamin}"
MODEL="${AGENT_MODEL:-sonnet}"
TURNS="${MAX_TURNS:-60}"
PAR="${PARALLEL:-3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SPEC="$HERE/../github/experiments.json"
ROOT="$(git rev-parse --show-toplevel)"
THIS_REPO="$(basename "$ROOT")"
LOG="$ROOT/.agents/wave-$WAVE"; mkdir -p "$LOG"

python3 - "$SPEC" "$WAVE" <<'EOF' > "$LOG/issues.tsv"
import json, sys
spec = json.load(open(sys.argv[1])); wave = sys.argv[2]
for i in spec["issues"]:
    if str(i.get("wave")) == wave:
        print(i["id"], i["repo"], i["title"], sep="\t")
EOF

while IFS=$'\t' read -r id repo title; do
  branch="exp/$(echo "$id" | tr '[:upper:]' '[:lower:]')"
  if [ "$repo" != "$THIS_REPO" ]; then
    echo "-- $id belongs to $repo: run this launcher inside ~/$repo"
    continue
  fi
  number=$(gh issue list --repo "$OWNER/$repo" --search "in:title \"$title\"" --state open --json number,title --limit 5 |
           python3 -c "import json,sys; t=sys.argv[1]; m=[i for i in json.load(sys.stdin) if i['title']==t]; print(m[0]['number'] if m else '')" "$title")
  [ -n "$number" ] || { echo "-- $id: no open issue titled as in the spec; publish first"; continue; }
  brief="$LOG/$id.md"
  { echo "# $title"; echo; gh issue view "$number" --repo "$OWNER/$repo" --json body -q .body; echo;
    echo "## Rules for this run"; echo "- Work only in this worktree, on branch $branch. Edit only the files the brief says you own.";
    echo "- Acceptance is the command the brief names; run it, and stop when it passes or when you have failed it three times.";
    echo "- Never weaken or delete a test to make the build pass. Record every hole you find in EXPERIMENTS.md.";
    echo "- Commit with a message that names the issue (#$number) and open a pull request; do not merge it."; } > "$brief"
  wt="$ROOT/.worktrees/$id"
  cmd="cd '$wt' && claude -p \"\$(cat '$brief')\" --model '$MODEL' --max-turns '$TURNS' > '$LOG/$id.log' 2>&1"
  echo "== $id -> $wt on $branch (issue #$number)"
  if [ "$DRY" = 1 ]; then echo "   $cmd"; continue; fi
  git worktree add -q --no-checkout -B "$branch" "$wt" main 2>/dev/null || git worktree add -q --no-checkout "$wt" "$branch"
  if [ "$(git config --get core.sparseCheckout 2>/dev/null)" = true ]; then   # a sparse clone (safety: no recordings) stays sparse in its worktrees
    # shellcheck disable=SC2046
    git -C "$wt" sparse-checkout set --cone $(git sparse-checkout list)
  fi
  git -C "$wt" reset -q --hard
  bash -c "$cmd" &
  # at most PAR agents at once (a polling wait: macOS ships bash 3.2, which has no "wait -n")
  while [ "$(jobs -rp | wc -l | tr -d ' ')" -ge "$PAR" ]; do sleep 10; done
done < "$LOG/issues.tsv"
wait
echo "wave $WAVE: agents finished; logs in $LOG; branches exp/*; review the pull requests before merging."
