#!/usr/bin/env bash
# Run one wave of the experiment program as unattended coding agents: one agent per issue, each in
# its own git worktree and branch, on the mid-tier model, with a turn cap and a spend cap, no
# permission prompts, a watchdog, and a pause-and-resume when the subscription window runs out.
# When an agent finishes, the launcher runs the acceptance command itself, pushes the branch, opens
# the pull request, comments the outcome on the issue and shows a notification. It never merges.
#
#   tools/agents/run_wave.sh 1                 # wave 1 of this repository's issues, PARALLEL agents at a time
#   tools/agents/run_wave.sh 1 --detach        # same, in the background; log in .agents/wave-1/launcher.log
#   tools/agents/run_wave.sh 1 --check         # preflight only: gh, claude, python, baseline tests
#   tools/agents/run_wave.sh 1 --dry-run       # write the briefs and print the commands; start nothing
#   tools/agents/run_wave.sh 1 --only L4       # one issue
#   START_AT=23:00 tools/agents/run_wave.sh 1 --detach    # start at 23:00 (tonight, or tomorrow if past)
#
# Knobs, as environment variables (defaults chosen for a Claude subscription, see docs/21):
#   AGENT_MODEL=sonnet   EFFORT=medium   MAX_TURNS=40   BUDGET_USD=10   PARALLEL=2
#   AGENT_TIMEOUT_MIN=120 (wall clock per attempt)   RETRIES=6 (resumes after a window pause)
#   FIVE_HOUR_CEILING=0.70  SEVEN_DAY_CEILING=0.85 (no new agent starts above these utilizations)
#   BASELINE=1 (run the repository's own tests before spending a token; 0 to skip)
# The local model (Ollama's Anthropic-compatible API; free, one run at a time):
#   LOCAL_URL=http://localhost:11434   LOCAL_MODEL=<an Ollama tag; auto-detected: the first qwen3 model>
#   LOCAL_URL=cloud LOCAL_MODEL=haiku  (no local model: the cheapest cloud model takes the local tier's jobs)
#   LOCAL_TURNS=80   LOCAL_TIMEOUT_MIN=240   BACKEND=cloud|local|cloud+local (overrides the spec for every issue)
# Each issue's "backend" in experiments.json says who does it: cloud (the subscription), local (the
# Mac's own model), or cloud+local (the cloud agent builds; if the acceptance command then fails,
# the local model gets a repair pass in the same worktree before the pull request is opened).
#
# Needs: gh (logged in as the owner), the claude CLI (logged in), git, python3, and the experiments
# spec tools/github/experiments.json. Run inside a clone of the repository whose issues the wave
# holds (safety-governor or safety); the other clones beside it in $HOME are given to the agents
# read-only. A sparse clone (safety without its recordings) gives sparse worktrees.
# Works with the bash 3.2 that macOS ships.
set -euo pipefail
set -E; trap 'echo "error: line $LINENO: $BASH_COMMAND (exit status $?)" >&2' ERR

WAVE="${1:?usage: run_wave.sh <wave> [--detach|--check|--dry-run] [--only ID]}"; shift
MODE=run; ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE=dry ;; --check) MODE=check ;; --detach) MODE=detach ;;
    --only) ONLY="$2"; shift ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
  shift
done
OWNER="${GITHUB_OWNER:-YobieBenjamin}"
MODEL="${AGENT_MODEL:-sonnet}"; EFFORT="${EFFORT:-medium}"; TURNS="${MAX_TURNS:-40}"; BUDGET="${BUDGET_USD:-10}"
PAR="${PARALLEL:-2}"; TIMEOUT_MIN="${AGENT_TIMEOUT_MIN:-120}"; RETRIES="${RETRIES:-6}"
FH_CEIL="${FIVE_HOUR_CEILING:-0.70}"; SD_CEIL="${SEVEN_DAY_CEILING:-0.85}"; BASELINE="${BASELINE:-1}"
LOCAL_URL="${LOCAL_URL:-http://localhost:11434}"; LOCAL_MODEL="${LOCAL_MODEL:-}"; LOCAL_TURNS="${LOCAL_TURNS:-80}"; LOCAL_TIMEOUT_MIN="${LOCAL_TIMEOUT_MIN:-240}"
BACKEND_OVERRIDE="${BACKEND:-}"; LOCAL_LOCK="$HOME/.agents-local.lock"
HERE="$(cd "$(dirname "$0")" && pwd)"
LIB="$HERE/wave_lib.py"; SPEC="${EXPERIMENTS_SPEC:-$HERE/../github/experiments.json}"
ROOT="$(git rev-parse --show-toplevel)"; REPO="$(basename "$ROOT")"
[ -d "$ROOT/.venv/bin" ] && export PATH="$ROOT/.venv/bin:$PATH"   # the repository's own environment, for the launcher and the agents
LOG="$ROOT/.agents/wave-$WAVE"; mkdir -p "$LOG"
say() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }
fail() { echo "error: $*" >&2; exit 1; }
notify() { command -v osascript >/dev/null 2>&1 && osascript -e "display notification \"$2\" with title \"$1\"" >/dev/null 2>&1 || true; }
py() { python3 "$LIB" "$@"; }
# The "local" tier: Ollama's Anthropic-compatible API at LOCAL_URL, or, with LOCAL_URL=cloud, the
# cheapest cloud model (LOCAL_MODEL, default haiku) when no local model exists.
claude_local() { if [ "$LOCAL_URL" = cloud ]; then claude "$@"; else ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_API_KEY="" ANTHROPIC_BASE_URL="$LOCAL_URL" claude "$@"; fi; }
local_lock_wait() { until mkdir "$LOCAL_LOCK" 2>/dev/null; do sleep 30; done; echo $$ > "$LOCAL_LOCK/pid"; }   # one local run on the Mac at a time, across repositories
local_lock_release() { rm -rf "$LOCAL_LOCK" 2>/dev/null || true; }
stop_bg() { pkill -P "$1" 2>/dev/null || true; kill "$1" 2>/dev/null || true; wait "$1" 2>/dev/null || true; }
watchdog() { ( trap - ERR; sleep "$1"; kill -INT "$2" 2>/dev/null || true; sleep 90; kill -TERM "$2" 2>/dev/null || true ) & disown $! 2>/dev/null || true; }
jget() { python3 -c "import json,sys; v=json.loads(sys.argv[1]).get(sys.argv[2]); print('' if v is None else v)" "$1" "$2"; }

# Detach when asked (the background process is the one kept awake), else keep this one awake (macOS).
WRAP=""; command -v caffeinate >/dev/null 2>&1 && WRAP="caffeinate -i -s"
if [ "$MODE" = detach ]; then
  # shellcheck disable=SC2086
  UNDER_CAFFEINATE=1 nohup $WRAP "$0" "$WAVE" ${ONLY:+--only "$ONLY"} > "$LOG/launcher.log" 2>&1 < /dev/null &
  echo "wave $WAVE started in the background (pid $!). Follow it with:"
  echo "  tail -f $LOG/launcher.log      # or open $LOG/STATUS.md, rewritten every 10 minutes"
  exit 0
fi
if [ "$MODE" = run ] && [ -n "$WRAP" ] && [ -z "${UNDER_CAFFEINATE:-}" ]; then
  # shellcheck disable=SC2086
  UNDER_CAFFEINATE=1 exec $WRAP "$0" "$WAVE" ${ONLY:+--only "$ONLY"}
fi
if [ -n "${START_AT:-}" ] && [ "$MODE" = run ]; then
  secs=$(python3 -c "
import datetime as d, sys
h, m = map(int, sys.argv[1].split(':')); now = d.datetime.now(); t = now.replace(hour=h, minute=m, second=0, microsecond=0)
if t <= now: t += d.timedelta(days=1)
print(int((t - now).total_seconds()))" "$START_AT")
  say "waiting until $START_AT ($((secs / 60)) minutes) before starting"
  sleep "$secs"
fi

# 1. Preflight: everything that would waste tokens if wrong is checked before the first agent starts.
say "== preflight for wave $WAVE in $REPO"
[ -f "$SPEC" ] || fail "no $SPEC"
command -v gh >/dev/null 2>&1 || fail "gh is not installed"
login=$(gh api user -q .login 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)
[ "$login" = "$(echo "$OWNER" | tr '[:upper:]' '[:lower:]')" ] || fail "gh is logged in as '${login:-nobody}', not $OWNER"
command -v claude >/dev/null 2>&1 || fail "the claude CLI is not installed (https://code.claude.com/docs/en/setup)"
claude auth status >/dev/null 2>&1 || fail "the claude CLI is not logged in; run: claude auth login"
CLAUDE_VERSION=$(claude -v 2>/dev/null | head -1)
PROMPTS_FLAG=""
if py version_ok "$CLAUDE_VERSION" 2.1.259; then PROMPTS_FLAG="--permission-prompts none"; else say "claude $CLAUDE_VERSION is older than 2.1.259: prompts are denied anyway in -p mode, but update it when you can"; fi
python3 -c "import pytest" 2>/dev/null || fail "pytest is missing in this python3: pip3 install -e '.[dev]' (safety-governor) or pip3 install pytest"
# the agents commit as the program's author; a machine with no git identity would fail every commit
[ -n "$(git -C "$ROOT" config --get user.email || true)" ] || { git -C "$ROOT" config user.name "Yobie Benjamin"; git -C "$ROOT" config user.email "yobie@icloud.com"; say "git identity set for this clone: Yobie Benjamin <yobie@icloud.com>"; }
git -C "$ROOT" fetch -q origin main
[ "$(git -C "$ROOT" rev-parse main)" = "$(git -C "$ROOT" rev-parse origin/main)" ] || say "note: local main differs from origin/main; worktrees branch from local main"
free_gb=$(df -g "$ROOT" 2>/dev/null | awk 'NR==2 {print $4}' || echo 99); [ "${free_gb:-99}" -ge 5 ] || fail "under 5 GB free on this disk"
ADD_DIRS=""
for other in safety-governor safety hardware-and-silicon; do
  if [ "$other" != "$REPO" ] && [ -d "$HOME/$other/.git" ]; then ADD_DIRS="$ADD_DIRS $HOME/$other"; fi
done
say "gh: $OWNER; claude $CLAUDE_VERSION ($MODEL, effort $EFFORT, $TURNS turns, \$$BUDGET cap); parallel $PAR; readable clones:${ADD_DIRS:- none}"
# The local model: the Ollama server at LOCAL_URL (started if it is installed but not running) and a
# qwen3 tag with a 64k context. Missing is not an error unless an issue is local-only; cloud+local
# then runs as cloud.
# shellcheck source=tools/agents/local_model.sh
. "$HERE/local_model.sh"
find_local_model
if [ "$LOCAL_URL" = cloud ]; then say "local tier: no local model; the cheap cloud model $LOCAL_MODEL stands in for it"
elif [ "$LOCAL_OK" = 1 ]; then say "local model: $LOCAL_MODEL at $LOCAL_URL (free; one run at a time)"
else say "local model: nothing answers at $LOCAL_URL and none could be started; local work runs in the cloud instead"; fi
if [ "$BASELINE" = 1 ] && [ "$MODE" != dry ]; then
  case "$REPO" in
    safety-governor) base_cmd="python3 -m pytest -x tests" ;;        # the repository's pytest config already adds -q
    safety) base_cmd="python3 -m pytest -x observer/tests" ;;
    *) base_cmd="" ;;
  esac
  if [ -n "$base_cmd" ]; then
    say "baseline: $base_cmd"
    (cd "$ROOT" && $base_cmd > "$LOG/baseline.log" 2>&1) || { tail -5 "$LOG/baseline.log"; fail "the repository's own tests fail on main; agents would chase that first. See $LOG/baseline.log"; }
    say "baseline passes: $(grep -E 'passed|failed' "$LOG/baseline.log" | tail -1 || true)"
  fi
fi
[ "$MODE" = check ] && { say "preflight OK"; exit 0; }

# 2. The wave's issues in this repository, with their numbers on GitHub (one listing, exact titles).
py issues "$SPEC" "$WAVE" "$REPO" "$ONLY" > "$LOG/issues.tsv"
[ -s "$LOG/issues.tsv" ] || { say "no wave-$WAVE issue belongs to $REPO$( [ -n "$ONLY" ] && echo " (or $ONLY is not one)")"; exit 0; }
gh issue list --repo "$OWNER/$REPO" --state open --json number,title --limit 1000 > "$LOG/open-issues.json"
number_of() { python3 -c "
import json, sys
m = [i for i in json.load(open(sys.argv[1])) if i['title'] == sys.argv[2]]
print(m[0]['number'] if m else '')" "$LOG/open-issues.json" "$1"; }

# shellcheck source=tools/agents/agent_rules.sh
. "$HERE/agent_rules.sh"

# 3. One agent.
run_agent() {
  local id="$1" number="$2" title="$3" accept="$4" backend="${5:-cloud}"
  local branch wt brief state session attempt log rc summary finished is_error limit subtype resets secs prompt t0 pr primary
  branch="exp/$(echo "$id" | tr '[:upper:]' '[:lower:]')"; wt="$ROOT/.worktrees/$id"; brief="$LOG/$id.brief.md"; state="$LOG/$id.state.json"
  t0=$(date +%s)
  setstate() { printf '{"id": "%s", "phase": "%s", "wall_s": %s, "acceptance": "%s", "pr": "%s", "issue": "%s", "backend": "%s"}\n' "$id" "$1" "$(( $(date +%s) - t0 ))" "${2:-not run}" "${3:-none}" "#$number" "$backend" > "$state"; }
  primary=cloud; [ "$backend" = local ] && primary=local
  setstate starting
  if [ -d "$wt" ] && [ "$(git -C "$ROOT" rev-list --count "main..$branch" 2>/dev/null || echo 0)" = 0 ]; then
    git -C "$wt" reset -q --hard main 2>/dev/null || true   # a worktree left by an earlier run with nothing on it: start from today's main
  fi
  if [ ! -d "$wt" ]; then
    git -C "$ROOT" worktree add -q --no-checkout -B "$branch" "$wt" main 2>/dev/null || git -C "$ROOT" worktree add -q --no-checkout "$wt" "$branch"
    if [ "$(git -C "$ROOT" config --get core.sparseCheckout 2>/dev/null)" = true ]; then
      # shellcheck disable=SC2046
      git -C "$wt" sparse-checkout set --cone $(git -C "$ROOT" sparse-checkout list)
    fi
    git -C "$wt" reset -q --hard
  fi
  { echo "# $title"; echo; echo "GitHub issue #$number in $OWNER/$REPO. Wave $WAVE of the experiment program (docs/20-experiment-program.md)."; echo
    py brief "$SPEC" "$id"; echo
    echo "## Rules for this run"
    echo "- You are in a git worktree on branch \`$branch\`; it is the only place you write. Run commands from this directory with relative paths; do not cd elsewhere."
    [ -n "$ADD_DIRS" ] && echo "- The other repositories of the program are readable at:$ADD_DIRS. Never edit them: a change they need goes into \`patches/<repo>/<file>.patch\` here, with a note in your final summary."
    echo "- Acceptance: \`${accept:-the command the brief names}\`. Run it at most three times. Stop when it passes, or after the third failure; then record exactly what fails in EXPERIMENTS.md (safety-governor) or in the hypothesis's section (safety), with the failing output."
    echo "- Read only the files the brief names under Read first and the files you create. Do not read whole directories, do not run the full test suite (the acceptance command is enough), do not search the web, do not start sub-agents."
    echo "- Never weaken, skip or delete an existing test. Do not refactor beyond the brief. No em dashes in anything you write."
    echo "- Commit as you go with messages that name the issue (#$number) and end with the line: Agent: wave $WAVE, issue #$number. Do not push, do not open a pull request; the launcher does both."
    echo "- This run is capped at $TURNS turns and an estimated spend of \$$BUDGET. Keep the tree in a working, committed state at all times, so a cap mid-way still leaves usable work."
    echo "- Finish with a summary of at most fifteen lines: what was built, what passes, what does not and why, open questions. It is posted on the issue as is."
  } > "$brief"
  session=$(uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' || python3 -c "import uuid; print(uuid.uuid4())")
  prompt="$(cat "$brief")"
  attempt=1; pr="none"
  while :; do
    log="$LOG/$id.$attempt.jsonl"
    setstate "running (attempt $attempt)"
    say "$id: attempt $attempt on $MODEL, log $log"
    set +e
    cd "$wt" || { say "$id: no worktree at $wt"; break; }
    if [ "$primary" = local ]; then
      local_lock_wait
      # shellcheck disable=SC2086
      claude_local -p "$prompt" --session-id "$session" --model "$LOCAL_MODEL" --max-turns "$LOCAL_TURNS" \
        --permission-mode acceptEdits $PROMPTS_FLAG --allowedTools "${ALLOW[@]}" --disallowedTools "${DENY[@]}" --add-dir "$LOG" $ADD_DIRS \
        --output-format stream-json --verbose < /dev/null > "$log" 2> "$log.err" &
    elif [ "$attempt" = 1 ]; then
      # shellcheck disable=SC2086
      claude -p "$prompt" --session-id "$session" --model "$MODEL" --effort "$EFFORT" --max-turns "$TURNS" --max-budget-usd "$BUDGET" \
        --permission-mode acceptEdits $PROMPTS_FLAG --allowedTools "${ALLOW[@]}" --disallowedTools "${DENY[@]}" --add-dir "$LOG" $ADD_DIRS \
        --output-format stream-json --verbose < /dev/null > "$log" 2> "$log.err" &
    else
      # shellcheck disable=SC2086
      claude -p "The previous run was interrupted (a usage window or a timeout). Re-read $brief, check git status and git log, and continue the task from where it stopped." \
        --resume "$session" --model "$MODEL" --effort "$EFFORT" --max-turns "$TURNS" --max-budget-usd "$BUDGET" \
        --permission-mode acceptEdits $PROMPTS_FLAG --allowedTools "${ALLOW[@]}" --disallowedTools "${DENY[@]}" --add-dir "$LOG" $ADD_DIRS \
        --output-format stream-json --verbose < /dev/null > "$log" 2> "$log.err" &
    fi
    cpid=$!
    if [ "$primary" = local ]; then watchdog "$((LOCAL_TIMEOUT_MIN * 60))" "$cpid"; else watchdog "$((TIMEOUT_MIN * 60))" "$cpid"; fi; wpid=$!
    rc=0; wait "$cpid" || rc=$?
    stop_bg "$wpid"
    [ "$primary" = local ] && local_lock_release
    cd "$ROOT"
    set -e
    summary=$(py summarize "$log")
    finished=$(jget "$summary" finished); is_error=$(jget "$summary" is_error); limit=$(jget "$summary" limit_hit); subtype=$(jget "$summary" subtype); resets=$(jget "$summary" resets_at)
    say "$id: attempt $attempt ended (exit $rc, $(jget "$summary" turns) turns, \$$(jget "$summary" cost_usd), window 5h $(jget "$summary" five_hour) 7d $(jget "$summary" seven_day), ${subtype:-no result})"
    if [ "$finished" = True ] && [ "$is_error" = False ]; then break; fi
    if [ "$primary" = local ]; then say "$id: the local run ended without a clean result (exit $rc); see $log.err"; break; fi
    if [ "$rc" = 130 ] || [ "$rc" = 143 ]; then say "$id: stopped by the $TIMEOUT_MIN-minute watchdog"; break; fi
    case "$subtype" in *max_turns*|*budget*) say "$id: hit its cap ($subtype)"; break ;; esac
    if [ "$limit" = True ]; then
      secs=$(py sleep_until "${resets:-0}")
      [ "$attempt" -lt "$RETRIES" ] || { say "$id: out of retries"; break; }
      setstate "waiting for the usage window ($((secs / 60)) min)"
      say "$id: usage window exhausted; resuming in $((secs / 60)) minutes"
      sleep "$secs"
    elif [ "$attempt" -ge 2 ]; then
      say "$id: failed twice; see $log and $log.err"; break
    else
      say "$id: no result (exit $rc); one retry in 2 minutes. stderr: $(tail -1 "$log.err" 2>/dev/null)"; sleep 120
    fi
    attempt=$((attempt + 1))
  done

  # 4. Acceptance, by the launcher, in the worktree (free: no tokens). If it fails and the issue is
  #    cloud+local, the local model gets one repair pass in the same worktree, then acceptance again.
  local acc="not run" accfile="$LOG/$id.accept.log" repaired=""
  run_acceptance() {
    [ -n "$accept" ] || { acc="not run"; return 0; }
    set +e; (trap - ERR; cd "$wt" && bash -c "$accept") > "$accfile" 2>&1 & apid=$!
    watchdog 1800 "$apid"; awd=$!
    arc=0; wait "$apid" || arc=$?; stop_bg "$awd"; set -e
    if [ "$arc" = 0 ]; then acc="pass"; else acc="fail (exit $arc)"; fi
    say "$id: acceptance $acc: $accept"
  }
  run_acceptance
  if [ "$backend" = "cloud+local" ] && [ "$LOCAL_OK" = 1 ] && [ "$acc" != pass ] && [ "$acc" != "not run" ]; then
    setstate "local repair pass" "$acc"
    say "$id: acceptance failed after the cloud run; the local model ($LOCAL_MODEL) gets a repair pass"
    { echo "# Repair pass: $title"; echo; echo "The brief is in $brief. The work so far is committed on this branch. The acceptance command failed:"; echo; echo '```'; echo "$accept"; echo '```'; echo
      echo "Its output (last 150 lines):"; echo; echo '```'; tail -150 "$accfile"; echo '```'; echo
      echo "Fix the cause so the acceptance command passes. The rules of the brief hold: never weaken or delete a test, touch only the files the brief names and the files already created on this branch, no web, no sub-agents, commit when it passes with a message that names #$number and ends with: Agent: wave $WAVE, issue #$number (local repair). Run the acceptance command at most five times. If you cannot make it pass, commit nothing further and finish with three lines on what is wrong."; } > "$LOG/$id.repair.md"
    local rlog="$LOG/$id.repair.jsonl"
    set +e; cd "$wt"; local_lock_wait
    # shellcheck disable=SC2086
    claude_local -p "$(cat "$LOG/$id.repair.md")" --model "$LOCAL_MODEL" --max-turns "$LOCAL_TURNS" \
      --permission-mode acceptEdits $PROMPTS_FLAG --allowedTools "${ALLOW[@]}" --disallowedTools "${DENY[@]}" --add-dir "$LOG" $ADD_DIRS \
      --output-format stream-json --verbose < /dev/null > "$rlog" 2> "$rlog.err" &
    cpid=$!; watchdog "$((LOCAL_TIMEOUT_MIN * 60))" "$cpid"; wpid=$!
    rc=0; wait "$cpid" || rc=$?; stop_bg "$wpid"; local_lock_release; cd "$ROOT"; set -e
    repaired=" after a local repair pass ($(jget "$(py summarize "$rlog")" turns) turns on $LOCAL_MODEL, exit $rc)"
    run_acceptance
  fi
  if [ -n "$(git -C "$wt" status --porcelain 2>/dev/null)" ]; then
    git -C "$wt" add -A >/dev/null 2>&1 && git -C "$wt" commit -q -m "Work left uncommitted by the agent, committed by the launcher (#$number)

The agent ended (cap, timeout or its own stop) with these files unstaged. They are committed as found so the gate can judge them and a revision can continue from them; nothing here is claimed to pass.

Agent: wave $WAVE, issue #$number (launcher commit)" 2>>"$LOG/launcher.err" && say "$id: the agent left uncommitted work; committed as found"
  fi
  local commits; commits=$(git -C "$wt" rev-list --count "main..$branch" 2>/dev/null || echo 0)
  if [ "$commits" -gt 0 ]; then
    git -C "$wt" push -q -u origin "$branch" 2>>"$LOG/launcher.err" || say "$id: push failed (see $LOG/launcher.err)"
    pr=$(gh pr list --repo "$OWNER/$REPO" --head "$branch" --json url -q '.[0].url' 2>/dev/null || true)
    if [ -z "$pr" ]; then
      { echo "Wave $WAVE agent run for #$number. Acceptance \`${accept:-n/a}\`: **$acc**. Review before merging; EXPERIMENTS.md carries the result line."; echo
        echo "Refs #$number"; echo; echo '```'; jget "$summary" result; echo '```'; } > "$LOG/$id.pr.md"
      pr=$(gh pr create --repo "$OWNER/$REPO" --head "$branch" --base main --title "$id: $title" --body-file "$LOG/$id.pr.md" --label experiment 2>>"$LOG/launcher.err" || echo "none")
    fi
  fi
  { echo "**Agent run, wave $WAVE** ($(date '+%Y-%m-%d %H:%M')): $primary ($([ "$primary" = local ] && echo "$LOCAL_MODEL" || echo "$MODEL, effort $EFFORT")), $(jget "$summary" turns) turns, estimated \$$(jget "$summary" cost_usd), $attempt attempt(s), $commits commit(s), acceptance \`${accept:-n/a}\`: **$acc**$repaired, pull request: $pr"
    echo; echo "Agent summary:"; echo; jget "$summary" result; } > "$LOG/$id.comment.md"
  gh issue comment "$number" --repo "$OWNER/$REPO" --body-file "$LOG/$id.comment.md" >/dev/null 2>>"$LOG/launcher.err" || say "$id: could not comment on #$number"
  setstate "done: $commits commit(s), $(jget "$summary" turns) turns" "$acc$repaired" "$pr"
  say "$id: done. $commits commit(s), acceptance $acc$repaired, PR $pr"
  notify "Wave $WAVE: $id finished" "acceptance $acc, $commits commits, \$$(jget "$summary" cost_usd)"
}

# 5. The ticker: STATUS.md every ten minutes, and a pause flag when the subscription window is high.
ticker() {
  trap - ERR
  while :; do
    sleep 600
    py status "$LOG" > "$LOG/STATUS.md" 2>/dev/null || true
    python3 - "$LOG" "$FH_CEIL" "$SD_CEIL" <<'PY' || true
import glob, json, os, sys
logdir, fh_ceil, sd_ceil = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
latest = None
for path in glob.glob(os.path.join(logdir, "*.jsonl")):
    for line in open(path, encoding="utf-8"):
        if '"rate_limit_event"' in line:
            try: r = json.loads(line)
            except ValueError: continue
            w = (r.get("rate_limit_info") or {}).get("unifiedWindows") or {}
            latest = (os.path.getmtime(path), w.get("five_hour", {}).get("utilization"), w.get("seven_day", {}).get("utilization"), w.get("five_hour", {}).get("resetsAt"))
flag = os.path.join(logdir, "PAUSE")
if latest and ((latest[1] or 0) >= fh_ceil or (latest[2] or 0) >= sd_ceil):
    open(flag, "w").write(f"{latest[3] or 0}\n5h {latest[1]} 7d {latest[2]}\n")
elif os.path.exists(flag):
    os.remove(flag)
PY
    say "tick: $(grep -l '"phase": "running' "$LOG"/*.state.json 2>/dev/null | wc -l | tr -d ' ') running; see $LOG/STATUS.md"
  done
}

# 6. Launch, PARALLEL at a time, never while the pause flag is up.
say "== wave $WAVE: $(wc -l < "$LOG/issues.tsv" | tr -d ' ') issue(s) in $REPO"
rm -f "$LOG/PAUSE"
if [ -d "$LOCAL_LOCK" ] && ! kill -0 "$(cat "$LOCAL_LOCK/pid" 2>/dev/null || echo 0)" 2>/dev/null; then rm -rf "$LOCAL_LOCK"; fi
[ "$MODE" = run ] && { ticker & TICK=$!; }
while IFS=$'\t' read -r id title accept backend; do
  number=$(number_of "$title")
  backend="${BACKEND_OVERRIDE:-${backend:-cloud+local}}"
  if [ "$LOCAL_OK" = 0 ]; then
    case "$backend" in
      local) say "-- $id: local-only and no local model is running; skipped"; continue ;;
      cloud+local) backend=cloud ;;
    esac
  fi
  [ -n "$number" ] || { say "-- $id: no open issue with this title in $OWNER/$REPO; publish first (tools/github/publish_experiments.sh)"; continue; }
  if [ "$MODE" = dry ]; then
    say "would run $id (#$number) as $backend in $ROOT/.worktrees/$id on exp/$(echo "$id" | tr '[:upper:]' '[:lower:]'): claude -p <brief> --model $([ "$backend" = local ] && echo "$LOCAL_MODEL via $LOCAL_URL" || echo "$MODEL --effort $EFFORT --max-budget-usd $BUDGET") --max-turns $([ "$backend" = local ] && echo "$LOCAL_TURNS" || echo "$TURNS") --permission-mode acceptEdits $PROMPTS_FLAG ...; acceptance: ${accept:-(none)}"
    continue
  fi
  while [ "$(jobs -rp | grep -vc "^$TICK$")" -ge "$PAR" ]; do sleep 20; done
  while [ -f "$LOG/PAUSE" ]; do
    secs=$(py sleep_until "$(head -1 "$LOG/PAUSE")"); say "subscription window above the ceiling ($(tail -1 "$LOG/PAUSE")); next agent in $((secs / 60)) minutes"; sleep "$secs"
  done
  run_agent "$id" "$number" "$title" "$accept" "$backend" &
  sleep 5
done < "$LOG/issues.tsv"
[ "$MODE" = dry ] && exit 0
while [ "$(jobs -rp | grep -vc "^$TICK$")" -gt 0 ]; do sleep 30; done
stop_bg "$TICK"
py status "$LOG" > "$LOG/STATUS.md"; py report "$LOG" > "$LOG/REPORT.md"
failed=$(grep -L '"phase": "done' "$LOG"/*.state.json 2>/dev/null | wc -l | tr -d ' ')
say "== wave $WAVE finished: report $LOG/REPORT.md; pull requests: gh pr list --repo $OWNER/$REPO"
notify "Wave $WAVE finished" "$(grep -l '"phase": "done' "$LOG"/*.state.json 2>/dev/null | wc -l | tr -d ' ') done, $failed not; see REPORT.md"
exit "$failed"
