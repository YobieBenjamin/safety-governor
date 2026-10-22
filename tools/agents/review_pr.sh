#!/usr/bin/env bash
# Review one agent branch: the deterministic verifier first (free), then a second reader on the local
# model when there is one (free), then one bounded cloud review that must answer in a fixed JSON
# shape with a file and line for every finding. The three results are posted on the pull request.
#
#   tools/agents/review_pr.sh <wave> <id>            # inside the clone that holds the branch exp/<id>
#   REVIEW_MODEL=sonnet REVIEW_EFFORT=high REVIEW_TURNS=12 REVIEW_BUDGET_USD=3
#
# Exit status: 0 the branch may merge (verifier clean, verdict merge, every citation real);
#              1 revise (a person or the next wave decides); 2 reject; 3 the review itself could not be trusted.
# Writes .agents/wave-N/review/<id>/{brief.md,diff.patch,verify.json,acceptance.log,summary.md,claims-local.md,review.json,review.md}.
set -euo pipefail
set -E; trap 'echo "error: line $LINENO: $BASH_COMMAND (exit status $?)" >&2' ERR
WAVE="${1:?wave}"; ID="${2:?issue id}"
OWNER="${GITHUB_OWNER:-YobieBenjamin}"
RMODEL="${REVIEW_MODEL:-sonnet}"; REFFORT="${REVIEW_EFFORT:-high}"; RTURNS="${REVIEW_TURNS:-12}"; RBUDGET="${REVIEW_BUDGET_USD:-3}"
READER_MIN="${SECOND_READER_MIN:-25}"; REVIEW_MIN="${REVIEW_MIN:-45}"   # wall-clock caps: a stuck local model or review must not stall the gate
LOCAL_URL="${LOCAL_URL:-http://localhost:11434}"; LOCAL_MODEL="${LOCAL_MODEL:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"; SPEC="${EXPERIMENTS_SPEC:-$HERE/../github/experiments.json}"; . "$HERE/paths.sh"
ROOT="$(git rev-parse --show-toplevel)"; REPO="$(basename "$ROOT")"
[ -d "$ROOT/.venv/bin" ] && export PATH="$ROOT/.venv/bin:$PATH"
LOG="$ROOT/.agents/wave-$WAVE"; P="$LOG/review/$ID"; mkdir -p "$P"
BRANCH="exp/$(echo "$ID" | tr '[:upper:]' '[:lower:]')"
say() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }
jget() { python3 -c "import json,sys; v=json.load(open(sys.argv[1])).get(sys.argv[2]); print(json.dumps(v) if isinstance(v,(dict,list)) else ('' if v is None else v))" "$1" "$2"; }
claude_local() { if [ "$LOCAL_URL" = cloud ]; then claude "$@"; else ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_API_KEY="" ANTHROPIC_BASE_URL="$LOCAL_URL" claude "$@"; fi; }
# run a command in the background with a wall-clock cap (minutes); returns its exit status, 124 when the cap hit
with_cap() {
  local mins="$1"; shift
  ( trap - ERR; "$@" ) & local pid=$!
  ( trap - ERR; sleep "$((mins * 60))"; sig_tree "$pid" INT; sleep 60; sig_tree "$pid" TERM; sleep 30; sig_tree "$pid" KILL ) & local wd=$!; disown $wd 2>/dev/null || true
  local rc=0; wait "$pid" || rc=$?
  if kill -0 "$wd" 2>/dev/null; then sig_tree "$wd" TERM; else rc=124; fi
  sig_tree "$pid" KILL   # nothing of the reader or the reviewer survives its run
  return $rc
}

git -C "$ROOT" rev-parse -q --verify "$BRANCH" >/dev/null || git -C "$ROOT" fetch -q origin "$BRANCH:$BRANCH" || { echo "no branch $BRANCH"; exit 3; }
title=$(python3 -c "import json,sys; print(next(i['title'] for i in json.load(open(sys.argv[1]))['issues'] if i['id']==sys.argv[2]))" "$SPEC" "$ID")
accept=$(python3 -c "import json,sys; print(next(i.get('accept','') for i in json.load(open(sys.argv[1]))['issues'] if i['id']==sys.argv[2]))" "$SPEC" "$ID")

# 1. The packet.
{ echo "# $title"; echo; python3 "$HERE/wave_lib.py" brief "$SPEC" "$ID"; echo; [ -f "$LOG/$ID.brief.md" ] && sed -n '/## Rules for this run/,$p' "$LOG/$ID.brief.md"; } > "$P/brief.md"
mb=$(git -C "$ROOT" merge-base main "$BRANCH")
git -C "$ROOT" diff "$mb..$BRANCH" > "$P/diff.patch"
[ -f "$LOG/$ID.accept.log" ] && tail -200 "$LOG/$ID.accept.log" > "$P/acceptance.log" || echo "(no acceptance log)" > "$P/acceptance.log"
{ [ -f "$LOG/$ID.comment.md" ] && cat "$LOG/$ID.comment.md" || echo "(no agent summary)"; echo; echo "## Commit messages"; git -C "$ROOT" log --format='- %s%n%b' "$mb..$BRANCH"; } > "$P/summary.md"
say "$ID: verifier"
set +e; python3 "$HERE/verify_pr.py" --repo "$ROOT" --branch "$BRANCH" --spec "$SPEC" --id "$ID" --accept "$accept" --json > "$P/verify.json"; vrc=$?; set -e
python3 "$HERE/verify_pr.py" --repo "$ROOT" --branch "$BRANCH" --spec "$SPEC" --id "$ID" --accept "$accept" --no-run > "$P/verify.txt" || true
say "$ID: verifier $( [ "$vrc" = 0 ] && echo clean || echo "found blocking problems")"

# 2. A second reader on the local model, when one answers: claims and evidence, no tools, the diff on stdin.
rm -f "$P/claims-local.md"
# shellcheck source=tools/agents/local_model.sh
. "$HERE/local_model.sh"
find_local_model
if [ "$LOCAL_OK" = 1 ]; then
  if [ -n "$LOCAL_MODEL" ] && [ "$(wc -c < "$P/diff.patch")" -lt 400000 ]; then
    say "$ID: second reader on $LOCAL_MODEL"
    { cat "$P/summary.md"; echo; echo "=== DIFF ==="; cat "$P/diff.patch"; } > "$P/reader-input.txt"
    reader() { claude_local -p "$(local_prefix)Below are an agent's summary of its work and the full diff. List every claim the summary and the commit messages make (one per line, numbered). For each, quote the line of the diff that is the evidence, or write NOT FOUND. Then list every number that appears in a changed document and where in the diff it is computed or recorded, or NOT FOUND. No other text." \
      --model "$LOCAL_MODEL" --max-turns 1 --tools "" --permission-prompts none --output-format text < "$P/reader-input.txt" > "$P/claims-local.md" 2> "$P/reader.err"; }
    set +e; with_cap "$READER_MIN" reader; rrc=$?; set -e
    if [ "$rrc" = 124 ]; then echo "(second reader stopped after $READER_MIN minutes; the local model did not answer in time)" > "$P/claims-local.md"; say "$ID: second reader stopped after $READER_MIN minutes"
    elif [ "$rrc" != 0 ] || [ ! -s "$P/claims-local.md" ]; then echo "(second reader failed: $(tail -1 "$P/reader.err" 2>/dev/null))" > "$P/claims-local.md"; say "$ID: second reader failed (see reader.err)"; fi
    rm -f "$P/reader-input.txt"
  fi
fi

# 3. The cloud review, read-only, in a clean checkout, with a fixed answer shape.
SCHEMA='{"type":"object","required":["verdict","summary","findings","claims"],"properties":{"verdict":{"type":"string","enum":["merge","revise","reject"]},"summary":{"type":"string"},"findings":{"type":"array","items":{"type":"object","required":["kind","severity","file","line","detail"],"properties":{"kind":{"type":"string","enum":["hallucination","unsupported_claim","test_integrity","scope","correctness","protocol","style"]},"severity":{"type":"string","enum":["block","warn"]},"file":{"type":"string"},"line":{"type":"integer"},"detail":{"type":"string"}}}},"claims":{"type":"array","items":{"type":"object","required":["claim","where","evidence","supported"],"properties":{"claim":{"type":"string"},"where":{"type":"string","enum":["document","code","commit","summary"]},"evidence":{"type":"string"},"supported":{"type":"boolean"}}}}}}'
SIBLINGS=""; for other in safety-governor safety hardware-and-silicon; do [ "$other" != "$REPO" ] && [ -d "$WORK/$other/.git" ] && SIBLINGS="$SIBLINGS $WORK/$other"; done
WT="$ROOT/.worktrees/review-$ID"; git -C "$ROOT" worktree remove -f "$WT" 2>/dev/null || true
git -C "$ROOT" worktree add -q --detach "$WT" "$BRANCH"
say "$ID: cloud review on $RMODEL (effort $REFFORT, $RTURNS turns, \$$RBUDGET cap)"
set +e
review_run() { (cd "$WT" && claude -p "$(cat "$HERE/review_prompt.md")

The packet directory is $P. Begin with brief.md, verify.json and summary.md, then diff.patch; open files of the checkout only where the diff needs context.${SIBLINGS:+ The other repositories of the program are readable at:$SIBLINGS (for LANES.md, the catalogue, the observer).}" \
  --model "$RMODEL" --effort "$REFFORT" --max-turns "$RTURNS" --max-budget-usd "$RBUDGET" \
  --permission-mode default --permission-prompts none --tools "Read,Glob,Grep,Bash" \
  --allowedTools "Read" "Glob" "Grep" "Bash(git diff *)" "Bash(git log *)" "Bash(git show *)" "Bash(git blame *)" \
  --disallowedTools "Edit" "Write" "WebFetch" "WebSearch" "Agent" --add-dir "$P" $SIBLINGS \
  --output-format json --json-schema "$SCHEMA" < /dev/null > "$P/review.raw.json" 2> "$P/review.err"); }
# shellcheck disable=SC2086
with_cap "$REVIEW_MIN" review_run; rrc=$?
[ "$rrc" = 124 ] && say "$ID: the review stopped after $REVIEW_MIN minutes"
set -e
git -C "$ROOT" worktree remove -f "$WT" 2>/dev/null || true

# 4. The review is checked before it is believed: every cited file must exist in the diff or the checkout.
status=0
python3 - "$P" "$ROOT" "$BRANCH" "$vrc" "$rrc" <<'PY' || status=$?
import json, os, subprocess, sys
P, root, branch, vrc, rrc = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
try:
    raw = json.load(open(os.path.join(P, "review.raw.json")))
    rev = raw.get("structured_output") or {}
    cost = raw.get("total_cost_usd", 0); turns = raw.get("num_turns", 0)
except Exception as e:
    raw, rev, cost, turns = {}, {}, 0, 0
verify = json.load(open(os.path.join(P, "verify.json"))) if os.path.exists(os.path.join(P, "verify.json")) else {"ok": False, "findings": [{"severity": "block", "finding": "verifier did not run", "where": ""}]}
diff_files = set()
for line in open(os.path.join(P, "diff.patch"), encoding="utf-8", errors="replace"):
    if line.startswith("+++ b/") or line.startswith("--- a/"):
        diff_files.add(line[6:].strip())
packet_files = set(os.listdir(P))
def exists(f):
    if not f: return False
    f = f.split(":")[0].strip()
    if f in diff_files or f in packet_files or os.path.basename(f) in packet_files: return True
    return subprocess.run(["git", "-C", root, "cat-file", "-e", f"{branch}:{f}"], capture_output=True).returncode == 0
trusted = bool(rev) and "verdict" in rev
bad_cites = [f for f in rev.get("findings", []) if not exists(f.get("file", ""))]
if bad_cites:
    trusted = False
verdict = rev.get("verdict", "revise") if trusted else "revise"
blocks = [f for f in verify.get("findings", []) if f["severity"] == "block"]
rblocks = [f for f in rev.get("findings", []) if f.get("severity") == "block"]
# an unsupported claim blocks when it reaches a document or the code; one made only in the summary or a commit message is a warning
unsupported = [c for c in rev.get("claims", []) if not c.get("supported") and c.get("where") in ("document", "code")]
unsupported_soft = [c for c in rev.get("claims", []) if not c.get("supported") and c.get("where") not in ("document", "code")]
if blocks or rblocks or unsupported:
    verdict = "reject" if verdict == "reject" else "revise"
status = {"merge": 0, "revise": 1, "reject": 2}[verdict]
if not trusted:
    status = 3
out = {"id": os.path.basename(P), "verdict": verdict, "trusted": trusted, "verifier_ok": verify.get("ok", False), "verifier_blocks": len(blocks),
       "review_blocks": len(rblocks), "unsupported_claims": len(unsupported), "unsupported_soft": len(unsupported_soft), "bad_citations": [f.get("file") for f in bad_cites],
       "review_cost_usd": cost, "review_turns": turns, "review_exit": rrc, "review": rev, "verify": verify}
json.dump(out, open(os.path.join(P, "review.json"), "w"), indent=1)
lines = [f"## Review of `{branch}`: **{verdict}**" + ("" if trusted else " (the model review could not be trusted; a person decides)"), ""]
lines.append(f"Verifier: {'clean' if verify.get('ok') else str(len(blocks)) + ' blocking finding(s)'}; model review on {raw.get('model', '?') if isinstance(raw, dict) else '?'}: {len(rblocks)} blocking, {len(rev.get('findings', [])) - len(rblocks)} warnings, {len(unsupported)} unsupported claim(s) of {len(rev.get('claims', []))}; estimated ${cost:.2f}, {turns} turns.")
lines.append("")
if rev.get("summary"):
    lines += ["### Reviewer's summary", "", rev["summary"], ""]
if verify.get("findings"):
    lines += ["### Verifier findings", ""] + [f"- [{f['severity']}] {f['finding']}: `{f['where']}`" for f in verify["findings"]] + [""]
if rev.get("findings"):
    lines += ["### Reviewer findings", ""] + [f"- [{f.get('severity')}] {f.get('kind')} at `{f.get('file')}:{f.get('line')}`: {f.get('detail')}" for f in rev["findings"]] + [""]
if rev.get("claims"):
    lines += ["### Claims", ""] + [f"- {'supported' if c.get('supported') else 'NOT SUPPORTED'} ({c.get('where')}): {c.get('claim')} (evidence: {c.get('evidence')})" for c in rev["claims"]] + [""]
if bad_cites:
    lines += ["### Citations that do not exist (the review itself failed its check)", ""] + [f"- `{f.get('file')}`: {f.get('detail')}" for f in bad_cites] + [""]
runs = verify.get("runs", {})
for k, r in runs.items():
    lines += [f"### {k} in a clean checkout: exit {r['exit']}", "", "```", r["tail"][-800:], "```", ""]
open(os.path.join(P, "review.md"), "w").write("\n".join(lines))
print(f"verdict {verdict} (trusted={trusted}, verifier ok={verify.get('ok')}, review blocks={len(rblocks)}, unsupported={len(unsupported)} hard / {len(unsupported_soft)} soft, ${cost:.2f})")
sys.exit(status)
PY
pr=$(gh pr list --repo "$OWNER/$REPO" --head "$BRANCH" --state open --json number -q '.[0].number' 2>/dev/null || true)
if [ -n "$pr" ]; then gh pr comment "$pr" --repo "$OWNER/$REPO" --body-file "$P/review.md" >/dev/null 2>&1 || say "$ID: could not post the review on PR #$pr"; fi
exit "$status"
