#!/usr/bin/env bash
# The whole software phase of the experiment program, unattended: wave after wave, in both
# repositories, with the gates between them, GitHub kept current at every step, and a backup of
# everything on the external drive after every step.
#
#   bash ~/safety-governor/tools/agents/run_program.sh --detach      # start it and close the terminal
#   bash ~/safety-governor/tools/agents/run_program.sh --status      # where it is
#   bash ~/safety-governor/tools/agents/run_program.sh --from 2      # resume at wave 2 (it also skips what is already merged)
#   bash ~/safety-governor/tools/agents/run_program.sh --dry-run     # print the plan, start nothing
#
# For each wave: the agents (run_wave.sh, in safety-governor then in safety); then for every branch
# the wave produced, the gate: verify_pr.py (deterministic), the local second reader, the bounded
# cloud review with a fixed answer shape (review_pr.sh); a branch merges only when the verifier is
# clean, the verdict is merge, every citation is real, CI on GitHub is green, and nothing it depends
# on is still open. Everything else stays open with the review on it, for a person. Then the audit
# packet for the wave is committed (audit/wave-N/), the backup is refreshed, and the next wave's
# issues whose dependencies did not merge are skipped with a note on the issue.
#
# Knobs: everything run_wave.sh and review_pr.sh read (AGENT_MODEL, EFFORT, MAX_TURNS, BUDGET_USD,
# PARALLEL, LOCAL_URL, LOCAL_MODEL, REVIEW_MODEL, ...), plus
#   WAVES="1 2 3"   BACKUP_DIR="/Volumes/External_4TB/Safety Experiments"   MERGE=1 (0: never merge, only review)
#   REVISE_ROUNDS=2 (a "revise" verdict goes back to the agent that many times before a person is needed)
#   START_AT=23:00 (wait before the first wave)
set -euo pipefail
set -E; trap 'echo "error: line $LINENO: $BASH_COMMAND (exit status $?)" >&2' ERR
OWNER="${GITHUB_OWNER:-YobieBenjamin}"
HERE="$(cd "$(dirname "$0")" && pwd)"; SPEC="${EXPERIMENTS_SPEC:-$HERE/../github/experiments.json}"
WAVES="${WAVES:-1 2 3}"; MERGE="${MERGE:-1}"; REVISE_ROUNDS="${REVISE_ROUNDS:-2}"
BACKUP_DIR="${BACKUP_DIR:-/Volumes/External_4TB/Safety Experiments}"
REPOS="${PROGRAM_REPOS:-safety-governor safety}"; ALL_REPOS="${BACKUP_REPOS:-safety-governor safety hardware-and-silicon autonomic-graph-regulation}"
PROG="$HOME/safety-governor/.agents/program"; mkdir -p "$PROG"
MODE=run; FROM=""
while [ $# -gt 0 ]; do
  case "$1" in
    --detach) MODE=detach ;; --dry-run) MODE=dry ;; --status) MODE=status ;;
    --from) FROM="$2"; shift ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
  shift
done
say() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$PROG/program.log"; }
# one program at a time: a second start while one runs would race it on the same branches and pull requests
if [ "$MODE" = run ] || [ "$MODE" = detach ]; then
  if [ -f "$PROG/pid" ] && kill -0 "$(cat "$PROG/pid" 2>/dev/null || echo 0)" 2>/dev/null; then
    echo "the program is already running (pid $(cat "$PROG/pid")); follow it with: tail -f $PROG/program.log" >&2; exit 0
  fi
fi
notify() { command -v osascript >/dev/null 2>&1 && osascript -e "display notification \"$2\" with title \"$1\"" >/dev/null 2>&1 || true; }
export PATH="$HOME/.local/bin:$PATH"

if [ "$MODE" = status ]; then
  echo "program log: $PROG/program.log"; tail -15 "$PROG/program.log" 2>/dev/null || echo "(not started)"
  for repo in $REPOS; do for d in "$HOME/$repo"/.agents/wave-*; do [ -f "$d/STATUS.md" ] && { echo; echo "== $repo/$(basename "$d")"; sed -n '1,12p' "$d/STATUS.md"; }; done; done
  exit 0
fi
if [ "$MODE" = detach ]; then
  # preparation first, in this terminal: the Claude CLI login may need the browser, which a background process cannot drive
  bash "$HERE/launch.sh" prepare 2>&1 | tee -a "$PROG/program.log" || { say "preparation failed; see $PROG/program.log"; exit 1; }
  WRAP=""; command -v caffeinate >/dev/null 2>&1 && WRAP="caffeinate -i -s"
  # shellcheck disable=SC2086
  PREPARED=1 UNDER_CAFFEINATE=1 nohup $WRAP "$0" ${FROM:+--from "$FROM"} > "$PROG/launcher.log" 2>&1 < /dev/null &
  echo "program started in the background (pid $!). Follow it with:"
  echo "  tail -f $PROG/program.log         # the program's own line per step"
  echo "  bash $0 --status                  # the waves' status tables"
  exit 0
fi

# ---- helpers -------------------------------------------------------------------------------------
issues_of() { python3 "$HERE/wave_lib.py" issues "$SPEC" "$1" "$2"; }   # wave repo -> id, title, accept, backend
field() { python3 -c "
import json, sys
i = next((i for i in json.load(open(sys.argv[1]))['issues'] if i['id'] == sys.argv[2]), {})
v = i.get(sys.argv[3], '')
print(' '.join(v) if isinstance(v, list) else v)" "$SPEC" "$1" "$2"; }
repo_of() { field "$1" repo; }
pr_state() {   # id repo -> merged | open:<number> | none
  local branch="exp/$(echo "$1" | tr '[:upper:]' '[:lower:]')" out
  out=$(gh pr list --repo "$OWNER/$2" --head "$branch" --state all --json number,state --limit 5 2>/dev/null || echo "[]")
  python3 -c "
import json, sys
prs = json.loads(sys.argv[1])
if any(p['state'] == 'MERGED' for p in prs): print('merged')
elif any(p['state'] == 'OPEN' for p in prs): print('open:' + str([p for p in prs if p['state'] == 'OPEN'][0]['number']))
else: print('none')" "$out"
}
issue_number() { gh issue list --repo "$OWNER/$2" --state all --search "in:title \"$1\"" --json number,title --limit 10 2>/dev/null | python3 -c "
import json, sys
m = [i for i in json.load(sys.stdin) if i['title'] == sys.argv[1]]
print(m[0]['number'] if m else '')" "$1"; }
deps_merged() {   # id -> 0 if every dependency has a merged pull request (or none is listed)
  local d
  for d in $(field "$1" depends); do
    [ "$(pr_state "$d" "$(repo_of "$d")")" = merged ] || return 1
  done
  return 0
}
ci_green() {   # number repo -> 0 when every check passed, or the repository has no checks
  local n; n=$(gh pr view "$1" --repo "$OWNER/$2" --json statusCheckRollup -q '.statusCheckRollup | length' 2>/dev/null || echo "")
  [ "$n" = 0 ] && return 0
  gh pr checks "$1" --repo "$OWNER/$2" --watch --fail-fast >/dev/null 2>&1
}
push_main() { git -C "$HOME/$1" push -q origin HEAD:main 2>>"$PROG/program.err" || say "$1: push of main failed (see program.err)"; }

backup() {   # mirrors of all four repositories, a browsable clone of each, the agents' logs, the bundles
  local root="$BACKUP_DIR" repo m
  if [ ! -d "$(dirname "$root")" ]; then say "backup: $(dirname "$root") is not mounted; skipped"; return 0; fi
  mkdir -p "$root/mirrors" "$root/clones" "$root/runs" "$root/bundles"
  for repo in $ALL_REPOS; do
    m="$root/mirrors/$repo.git"
    # A first mirror can be large (safety carries its recordings): it is cloned in the background and
    # never holds up a wave. A marker file holds the clone's pid; its exit status lands beside it.
    if [ -f "$m.cloning" ]; then
      if kill -0 "$(cat "$m.cloning" 2>/dev/null || echo 0)" 2>/dev/null; then
        say "backup: first mirror of $repo still copying in the background ($(du -sh "$m" 2>/dev/null | cut -f1) so far)"; continue
      elif [ "$(cat "$m.rc" 2>/dev/null || echo 1)" = 0 ]; then
        rm -f "$m.cloning" "$m.rc"; say "backup: first mirror of $repo complete"
      else
        say "backup: the first mirror of $repo did not complete (see $m.log); starting it again"; rm -rf "$m" "$m.cloning" "$m.rc"
      fi
    fi
    if [ -d "$m" ] && [ ! -f "$m.cloning" ] && ! git -C "$m" rev-parse -q --verify main >/dev/null 2>&1; then
      say "backup: $m is an incomplete mirror (an interrupted copy); removing it"; rm -rf "$m"
    fi
    if [ -d "$m" ] && [ ! -f "$m.cloning" ]; then
      git -C "$m" remote update --prune >/dev/null 2>&1 || say "backup: mirror update of $repo failed"
    elif [ ! -d "$m" ]; then
      say "backup: first mirror of $repo starts in the background (the safety one carries 8 GB of recordings)"
      ( rm -f "$m.rc"; git clone -q --mirror "https://github.com/$OWNER/$repo.git" "$m" > "$m.log" 2>&1; echo $? > "$m.rc" ) &
      echo $! > "$m.cloning"
      continue
    fi
    if [ -d "$root/clones/$repo/.git" ]; then
      git -C "$root/clones/$repo" fetch -q origin main 2>/dev/null && git -C "$root/clones/$repo" merge -q --ff-only origin/main 2>/dev/null || say "backup: clone update of $repo failed"
    else
      git clone -q "$m" "$root/clones/$repo" 2>>"$PROG/program.err" || say "backup: clone of $repo failed"
    fi
  done
  for repo in $REPOS; do
    [ -d "$HOME/$repo/.agents" ] && { mkdir -p "$root/runs/$repo"; cp -R "$HOME/$repo/.agents/." "$root/runs/$repo/" 2>/dev/null || true; }
  done
  ls "$HOME"/Downloads/*.bundle >/dev/null 2>&1 && cp "$HOME"/Downloads/*.bundle "$root/bundles/" 2>/dev/null || true
  { date '+%Y-%m-%d %H:%M'; for repo in $ALL_REPOS; do printf '  %-28s %s\n' "$repo" "$(git -C "$root/mirrors/$repo.git" rev-parse --short main 2>/dev/null || echo 'copying')"; done; } >> "$root/BACKUP.log"
  say "backup refreshed at $root"
}

gate() {   # wave repo: review every branch the wave produced here; merge what passes
  local wave="$1" repo="$2" id title accept backend st num verdict rc
  cd "$HOME/$repo"
  issues_of "$wave" "$repo" | while IFS=$'\t' read -r id title accept backend; do
    st=$(pr_state "$id" "$repo")
    case "$st" in
      merged) say "$repo $id: already merged"; continue ;;
      none) say "$repo $id: no pull request (the agent produced no commit, or was skipped)"; continue ;;
    esac
    num="${st#open:}"
    round=0
    while :; do
      say "$repo $id: gate on PR #$num$( [ "$round" -gt 0 ] && echo " (after revision $round)")"
      rc=0; bash "$HERE/review_pr.sh" "$wave" "$id" >> "$PROG/program.log" 2>&1 || rc=$?
      verdict=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('verdict','?'))" "$HOME/$repo/.agents/wave-$wave/review/$id/review.json" 2>/dev/null || echo "?")
      if [ "$rc" = 1 ] && [ "$round" -lt "$REVISE_ROUNDS" ]; then
        round=$((round + 1))
        say "$repo $id: verdict revise; the findings go back to the agent (revision $round of $REVISE_ROUNDS)"
        bash "$HERE/revise_pr.sh" "$wave" "$id" "$round" >> "$PROG/program.log" 2>&1 || say "$repo $id: revision $round ended without a passing acceptance; reviewing it anyway"
        continue
      fi
      break
    done
    if [ "$rc" = 0 ] && [ "$MERGE" = 1 ]; then
      if ! deps_merged "$id"; then say "$repo $id: verdict merge, but a dependency is not merged; left open"; continue; fi
      if ci_green "$num" "$repo"; then
        if gh pr merge "$num" --repo "$OWNER/$repo" --merge --delete-branch --body "Merged by the program's gate: verifier clean, review verdict merge with every citation real, CI green. Review on the pull request." >/dev/null 2>>"$PROG/program.err"; then
          say "$repo $id: merged PR #$num"
          git -C "$HOME/$repo" fetch -q origin main && git -C "$HOME/$repo" merge -q --ff-only origin/main 2>/dev/null || say "$repo: local main could not fast-forward after the merge"
        else
          say "$repo $id: merge of PR #$num refused by GitHub (see program.err); left open"
        fi
      else
        say "$repo $id: CI is not green on PR #$num; left open"
        gh pr comment "$num" --repo "$OWNER/$repo" --body "The gate did not merge: CI is not green. The review above stands." >/dev/null 2>&1 || true
      fi
    else
      say "$repo $id: verdict $verdict after $round revision(s); left open for a person"
    fi
  done
}

packet() {   # wave repo: the audit packet, committed to main
  local wave="$1" repo="$2" src dst
  src="$HOME/$repo/.agents/wave-$wave"; dst="$HOME/$repo/audit/wave-$wave"
  [ -d "$src" ] || return 0
  mkdir -p "$dst"
  cp "$src"/REPORT.md "$dst"/ 2>/dev/null || true
  cp "$src"/*.brief.md "$src"/*.comment.md "$src"/*.accept.log "$dst"/ 2>/dev/null || true
  [ -d "$src/review" ] && cp -R "$src/review" "$dst/" 2>/dev/null || true
  rm -f "$dst"/review/*/review.raw.json "$dst"/review/*/review.err 2>/dev/null || true
  (cd "$dst" && find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 shasum -a 256 > MANIFEST.sha256)
  cd "$HOME/$repo" || return 0
  [ "$(git config --get core.sparseCheckout 2>/dev/null)" = true ] && git sparse-checkout add audit >/dev/null 2>&1
  git add audit 2>>"$PROG/program.err" || { say "$repo: could not stage audit/wave-$wave (see program.err)"; return 0; }
  if ! git diff --cached --quiet; then
    git -c user.name="Yobie Benjamin" -c user.email="yobie@icloud.com" commit -q -m "audit/wave-$wave: the wave's briefs, agent summaries, acceptance logs, reviews and report, with a manifest

Written by the program's gate for the external audit (Codex, Gemini) described in audit/PROMPT.md." && push_main "$repo" && say "$repo: audit/wave-$wave committed and pushed"
  fi
}

# ---- the program ---------------------------------------------------------------------------------
[ "$MODE" = run ] && echo $$ > "$PROG/pid"
say "== program start (waves: $WAVES; merge: $MERGE; backup: $BACKUP_DIR)"
if [ "$MODE" = dry ]; then
  for wave in $WAVES; do for repo in $REPOS; do echo "wave $wave, $repo:"; issues_of "$wave" "$repo" | while IFS=$'\t' read -r id title accept backend; do printf '  %-8s %-12s %s\n' "$id" "$backend" "$(pr_state "$id" "$repo" 2>/dev/null || echo '?')"; done; done; done
  exit 0
fi
if [ "${PREPARED:-0}" != 1 ]; then
  bash "$HERE/launch.sh" prepare >> "$PROG/program.log" 2>&1 || { say "preparation failed; see $PROG/program.log"; exit 1; }
fi
backup
if [ -n "${START_AT:-}" ]; then
  secs=$(python3 -c "
import datetime as d, sys
h, m = map(int, sys.argv[1].split(':')); now = d.datetime.now(); t = now.replace(hour=h, minute=m, second=0, microsecond=0)
if t <= now: t += d.timedelta(days=1)
print(int((t - now).total_seconds()))" "$START_AT"); say "waiting until $START_AT"; sleep "$secs"
fi
for wave in $WAVES; do
  if [ -n "$FROM" ] && [ "$wave" -lt "$FROM" ]; then say "wave $wave: skipped (--from $FROM)"; continue; fi
  say "== wave $wave"
  for repo in $REPOS; do
    [ -d "$HOME/$repo/.git" ] || continue
    issues_of "$wave" "$repo" | grep -q . || { say "$repo: no issues in wave $wave"; continue; }
    # issues already merged, or whose dependencies did not merge, are taken out before the agents start
    skip=""
    issues_of "$wave" "$repo" | while IFS=$'\t' read -r id title accept backend; do
      st=$(pr_state "$id" "$repo")
      case "$st" in
        merged) echo "$id merged" ;;
        open:*) echo "$id open" ;;
        *) deps_merged "$id" || echo "$id deps" ;;
      esac
    done > "$PROG/skip-$wave-$repo.txt"
    while read -r id why; do
      [ -n "$id" ] || continue
      case "$why" in
        deps) n=$(issue_number "$(field "$id" title)" "$repo")
              [ -n "$n" ] && gh issue comment "$n" --repo "$OWNER/$repo" --body "Not started in wave $wave: a dependency ($(field "$id" depends)) has no merged pull request yet. It runs when that merges (run_program.sh --from $wave)." >/dev/null 2>&1 || true
              say "$repo $id: skipped, dependency not merged" ;;
        open) say "$repo $id: has an open pull request already; the gate reviews it, no new agent" ;;
        *) say "$repo $id: already merged" ;;
      esac
      skip="$skip $id"
    done < "$PROG/skip-$wave-$repo.txt"
    cd "$HOME/$repo"
    issues_of "$wave" "$repo" | while IFS=$'\t' read -r id title accept backend; do
      case " $skip " in *" $id "*) continue ;; esac
      echo "$id"
    done > "$PROG/run-$wave-$repo.txt"
    if [ -s "$PROG/run-$wave-$repo.txt" ]; then
      say "$repo: agents for wave $wave: $(tr '\n' ' ' < "$PROG/run-$wave-$repo.txt")"
      rc=0; UNDER_CAFFEINATE=1 bash "$HERE/run_wave.sh" "$wave" >> "$PROG/program.log" 2>&1 || rc=$?
      say "$repo: wave $wave agents finished (exit $rc); $(grep -l '"phase": "done' "$HOME/$repo/.agents/wave-$wave"/*.state.json 2>/dev/null | wc -l | tr -d ' ') done"
    fi
    backup || say "backup had an error; continuing"
    say "$repo: gate for wave $wave"
    gate "$wave" "$repo" || say "$repo: the gate had an error; continuing"
    packet "$wave" "$repo" || say "$repo: the audit packet had an error; continuing"
    backup || say "backup had an error; continuing"
  done
  notify "Program: wave $wave finished" "see program.log and the pull requests"
done
say "== program finished: $(gh pr list --repo "$OWNER/safety-governor" --state open --json number -q 'length' 2>/dev/null || echo '?') PR(s) still open in safety-governor, $(gh pr list --repo "$OWNER/safety" --state open --json number -q 'length' 2>/dev/null || echo '?') in safety; the ones left open carry their review and wait for a person"
notify "Program finished" "see $PROG/program.log"
