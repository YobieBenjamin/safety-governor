#!/usr/bin/env bash
# One script for a Mac that has nothing set up yet. In order: make sure gh is installed, log in to
# GitHub in the browser if needed, move the clones to the external drive if they still sit in the
# home directory, clone the four repositories where they are missing, bring each clone up to date,
# apply the bundles made in the program's container, push, then publish the experiments as labels
# and issues in the three repositories that carry them.
#
#   bash "/Volumes/External_4TB/Safety Experiments/setup_and_publish.sh"   # bundles: beside the script, and in the inbox
#   bash ~/Downloads/setup_and_publish.sh                                   # the same script from anywhere
#   bash setup_and_publish.sh ~/some/dir                                    # bundles in the directory given as well
#
# Where the work lives: the four clones sit beside each other in WORK, which is the external drive
# (/Volumes/External_4TB/Safety Experiments) whenever it is mounted, else $HOME; PROJECT_WORK
# overrides. A clone still in $HOME is moved (copied, compared file by file, then removed) and a
# symlink ~/<repo> is left behind so old commands keep working. If the program is running with
# agents in flight, the move waits for them to finish (MIGRATE_NOW=1 stops them instead), in the
# background, and the rest of this script runs after it; the log says where it is.
#
# Safe to run again: every step checks before it acts. It never force-pushes and, apart from the
# move itself (which deletes a clone only after its copy compared equal), never deletes.
# The safety repository is cloned without its 8 GB of recordings (a blobless, sparse clone); add a
# directory later with: git -C "$WORK/safety" sparse-checkout add algorithms/<name>
set -euo pipefail
set -E; trap 'echo "error: line $LINENO: $BASH_COMMAND (exit status $?)" >&2' ERR   # nothing fails silently
OWNER="${GITHUB_OWNER:-YobieBenjamin}"
BASE="${GITHUB_BASE:-https://github.com/$OWNER}"   # where the repositories are cloned from
WORK="${PROJECT_WORK:-}"   # the same three lines as tools/agents/paths.sh, which does not exist yet on a fresh Mac
if [ -z "$WORK" ]; then
  if [ -d "/Volumes/External_4TB/Safety Experiments" ]; then WORK="/Volumes/External_4TB/Safety Experiments"; else WORK="$HOME"; fi
fi
INBOX="$WORK/inbox"
HERE_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_DIRS="$HERE_DIR"; [ -d "$INBOX" ] && [ "$INBOX" != "$HERE_DIR" ] && BUNDLE_DIRS="$BUNDLE_DIRS $INBOX"
[ -n "${1:-}" ] && [ "${1:-}" != "--migrate-when-idle" ] && BUNDLE_DIRS="$BUNDLE_DIRS $1"
REPOS="${REPOS:-safety-governor safety hardware-and-silicon Watermark}"   # Watermark carries no experiments; it is cloned, fast-forwarded from its bundles and pushed like the others
SAFETY_DIRS="agr data docs miner observer orchestrator sandbox scripts"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
fail() { echo "error: $*" >&2; exit 1; }

# 1. gh: Homebrew if present, otherwise the official binary into ~/.local/bin (no sudo).
step "GitHub CLI"
if ! command -v gh >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    brew install gh
  else
    arch=$(uname -m); [ "$arch" = "arm64" ] || arch="amd64"
    tag=$(curl -fsSL https://api.github.com/repos/cli/cli/releases/latest | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p')
    [ -n "$tag" ] || fail "could not find the latest gh release"
    tmp=$(mktemp -d)
    curl -fsSL -o "$tmp/gh.zip" "https://github.com/cli/cli/releases/download/v${tag}/gh_${tag}_macOS_${arch}.zip"
    (cd "$tmp" && unzip -q gh.zip)
    mkdir -p "$HOME/.local/bin" && cp "$tmp"/gh_*/bin/gh "$HOME/.local/bin/gh"
    export PATH="$HOME/.local/bin:$PATH"
    grep -q '.local/bin' "$HOME/.zshrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
  fi
fi
gh --version | head -1

# 2. Logged in as the owner of the repositories, not another account; gh then supplies git's
#    credentials over HTTPS. A different account already in gh's keyring is switched to; otherwise
#    the browser login runs (sign out of the other account on github.com first, or use a private
#    window, or the browser will authorize the account it is signed in to).
step "GitHub login"
want=$(echo "$OWNER" | tr '[:upper:]' '[:lower:]')
login=""
for attempt in 1 2 3; do
  login=$(gh api user -q .login 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)
  [ "$login" = "$want" ] && break
  if [ -n "$login" ]; then
    echo "gh is logged in as $login; the repositories belong to $OWNER"
    if gh auth switch --hostname github.com --user "$OWNER" >/dev/null 2>&1; then echo "switched to $OWNER"; continue; fi
  fi
  echo "log in as $OWNER in the browser"
  gh auth login --hostname github.com --git-protocol https --web
done
[ "$login" = "$want" ] || fail "gh is logged in as '${login:-nobody}', not $OWNER; run: gh auth login"
gh auth setup-git >/dev/null 2>&1 || true
echo "account: $OWNER"

# 3. The move: a clone still in $HOME goes to WORK. The program, if it is running from the old
#    place with agents in flight, is left to finish them first (its ten-minute tick says how many
#    are running); then it is stopped, the clones move, and it is started again from WORK.
program_pids() { pgrep -f "tools/agents/run_program.sh" 2>/dev/null | while read -r p; do [ "$p" = "$$" ] || ps -o command= -p "$p" 2>/dev/null | grep -q -- "--mirror-job" || echo "$p"; done; }
kill_tree() { local c; for c in $(pgrep -P "$1" 2>/dev/null || true); do kill_tree "$c"; done; kill -TERM "$1" 2>/dev/null || true; }
stop_program() {   # the program and its agents, whichever version of run_program.sh is installed: the one before 21 October did not know --stop
  local pats="tools/agents/run_program.sh tools/agents/run_wave.sh tools/agents/review_pr.sh tools/agents/revise_pr.sh" pat p
  bash "$HOME/safety-governor/tools/agents/run_program.sh" --stop >/dev/null 2>&1 || true
  for pat in $pats; do for p in $(pgrep -f "$pat" 2>/dev/null || true); do
    [ "$p" = "$$" ] && continue; ps -o command= -p "$p" 2>/dev/null | grep -q -- "--mirror-job" && continue; kill_tree "$p"
  done; done
  sleep 5
  for pat in $pats; do for p in $(pgrep -f "$pat" 2>/dev/null || true); do
    [ "$p" = "$$" ] && continue; ps -o command= -p "$p" 2>/dev/null | grep -q -- "--mirror-job" && continue; kill -KILL "$p" 2>/dev/null || true
  done; done
  rm -f "$HOME/safety-governor/.agents/program/pid" "$HOME/.agents-local.lock/pid" 2>/dev/null; rmdir "$HOME/.agents-local.lock" 2>/dev/null || true
  echo "program stopped ($(program_pids | wc -l | tr -d ' ') instance(s) left); the backup's mirror jobs and the Ollama server were left running"
}
agents_running() {   # the last tick of the old program's log: "tick: N running"
  local log="$HOME/safety-governor/.agents/program/program.log" n
  [ -f "$log" ] || { echo 0; return; }
  n=$(grep -o 'tick: [0-9]* running' "$log" | tail -1 | awk '{print $2}' || true); echo "${n:-0}"
}
needs_move() { local r; for r in $REPOS; do [ -d "$HOME/$r/.git" ] && [ ! -L "$HOME/$r" ] && return 0; done; return 1; }
move_repo() {
  local r="$1" src="$HOME/$1" dst="$WORK/$1"
  echo "$r: copying $src to $dst"
  mkdir -p "$dst"
  if command -v rsync >/dev/null 2>&1; then rsync -a --delete --exclude .venv "$src/" "$dst/"
  else rm -rf "$dst"; cp -a "$src" "$dst"; rm -rf "$dst/.venv"; fi   # a copy that was interrupted is finished by rsync, or started over by cp
  # compared file by file before anything is removed; .venv is remade at the new place by launch.sh
  if diff -rq -x .venv "$src" "$dst" >/dev/null 2>&1; then
    rm -rf "$src"
    # worktrees under .worktrees name the old absolute path on both sides; repaired while that path is gone, before the symlink makes it resolve again
    for w in "$dst"/.worktrees/*/; do [ -d "$w" ] && git -C "$dst" worktree repair "$w" >/dev/null 2>&1 || true; done
    ln -s "$dst" "$src"
    echo "$r: moved; $src is now a symlink to $dst"
  else
    fail "$r: the copy at $dst does not match $src; nothing was removed. Run again (rsync resumes), or compare with: diff -rq -x .venv \"$src\" \"$dst\""
  fi
}
if [ "$WORK" != "$HOME" ] && needs_move; then
  step "Move to $WORK"
  mkdir -p "$INBOX"
  was_running=""
  if [ -n "$(program_pids)" ]; then
    was_running=1
    if [ "${MIGRATE_NOW:-0}" != 1 ] && [ "$(agents_running)" != 0 ] && [ "${1:-}" != "--migrate-when-idle" ]; then
      log="$WORK/migrate.log"
      echo "the program is running with $(agents_running) agent(s) in flight; the move waits for them, in the background, then runs the rest of this script"
      echo "follow it with: tail -f \"$log\"   (MIGRATE_NOW=1 bash \"$0\" moves now instead, stopping the agents)"
      nohup caffeinate -i bash "$0" --migrate-when-idle >> "$log" 2>&1 < /dev/null &
      echo "background pid $!; log: $log"
      exit 0
    fi
    if [ "${1:-}" = "--migrate-when-idle" ]; then
      while [ -n "$(program_pids)" ] && [ "$(agents_running)" != 0 ]; do
        echo "$(date '+%Y-%m-%d %H:%M') waiting: $(agents_running) agent(s) running"; sleep 600
      done
    fi
    echo "stopping the program at $HOME/safety-governor (it restarts from $WORK at the end)"
    stop_program
    sleep 3
  fi
  for repo in $REPOS; do
    if [ -d "$HOME/$repo/.git" ] && [ ! -L "$HOME/$repo" ]; then move_repo "$repo"; fi
  done
  # bundles and this script: into the inbox on the drive, out of Downloads
  for repo in $REPOS; do ls "$HOME/Downloads/$repo"-*.bundle >/dev/null 2>&1 && mv "$HOME/Downloads/$repo"-*.bundle "$INBOX/" 2>/dev/null || true; done
  [ -f "$HOME/Downloads/setup_and_publish.sh" ] && [ "$HERE_DIR" = "$HOME/Downloads" ] && cp "$HOME/Downloads/setup_and_publish.sh" "$WORK/setup_and_publish.sh" || true
  BUNDLE_DIRS="$BUNDLE_DIRS $INBOX"
  echo "moved; the clones live in $WORK, bundles go to $INBOX, and ~/<repo> are symlinks"
fi

# 4. Clones, where they are missing.
step "Clones"
for repo in $REPOS; do
  clone="$WORK/$repo"
  if [ -d "$clone/.git" ]; then
    echo "$repo: present"
    url=$(git -C "$clone" remote get-url origin 2>/dev/null || true)
    shopt -s nocasematch
    case "$url" in "$BASE/$repo"|"$BASE/$repo.git"|*"$OWNER/$repo"|*"$OWNER/$repo.git") ;; *) fail "$clone is not a clone of $OWNER/$repo (origin is '$url')" ;; esac
    shopt -u nocasematch
  elif [ -e "$clone" ]; then
    fail "$clone exists but is not a git repository; move it aside"
  elif [ "$repo" = safety ]; then
    echo "$repo: cloning without the recordings"
    git clone --filter=blob:none --no-checkout "$BASE/$repo.git" "$clone"
    git -C "$clone" sparse-checkout init --cone
    # shellcheck disable=SC2086
    git -C "$clone" sparse-checkout set $SAFETY_DIRS
    git -C "$clone" checkout main
  else
    git clone "$BASE/$repo.git" "$clone"
  fi
done

# 5. Each clone: up to date with GitHub, then fast-forwarded from <repo>-N.bundle (lowest N first),
#    then pushed. A bundle the clone already contains is skipped.
step "Bundles from:$(for d in $BUNDLE_DIRS; do printf ' %s' "$d"; done | sort -u | tr '\n' ' ')"
for repo in $REPOS; do
  clone="$WORK/$repo"
  branch=$(git -C "$clone" rev-parse --abbrev-ref HEAD)
  [ "$branch" = main ] || fail "$repo is on branch '$branch'; check out main and run again"
  [ -z "$(git -C "$clone" status --porcelain --untracked-files=no)" ] || fail "$repo has uncommitted changes; commit or stash them and run again"
  err=$(mktemp)
  # "+" so the remote-tracking ref follows GitHub even if it was left ahead or aside; -q hides git's refusal otherwise
  git -C "$clone" fetch -q origin "+refs/heads/main:refs/remotes/origin/main" 2>"$err" || { cat "$err" >&2; fail "$repo: could not fetch main from GitHub"; }
  git -C "$clone" merge -q --ff-only origin/main || fail "$repo has local commits that are not on GitHub; push or move them first"
  found=0
  for path in $(for d in $BUNDLE_DIRS; do ls "$d"/"$repo"-[0-9]*.bundle 2>/dev/null; done | awk '{n=$0; sub(/.*-/, "", n); sub(/\.bundle$/, "", n); print n, $0}' | sort -n -u -k1,1 | cut -d' ' -f2-); do
    found=1
    b=$(basename "$path")
    # the bundle's head, read from the file (inside the clone: some git builds want a repository
    # for this): a bundle already in the clone's history is skipped unread
    head=$(git -C "$clone" bundle list-heads "$path" 2>"$err" | awk '$2 == "refs/heads/main" {print $1}' || true)
    [ -n "$head" ] || { [ -s "$err" ] && cat "$err" >&2; fail "$repo: $b has no main branch or cannot be read"; }
    if git -C "$clone" cat-file -e "$head" 2>/dev/null && git -C "$clone" merge-base --is-ancestor "$head" HEAD; then
      echo "$repo: already contains $b"; continue
    fi
    # "+" lets the scratch ref move backwards or sideways between bundles; it is never the branch
    rc=0; git -C "$clone" fetch -q "$path" "+main:refs/claude/incoming" 2>"$err" || rc=$?
    if [ "$rc" != 0 ]; then
      grep -q prerequisite "$err" && fail "$repo: $b builds on commits this clone does not have (a newer bundle may be needed, or an older one applied first)"
      [ -s "$err" ] && cat "$err" >&2
      fail "$repo: git could not read $b (exit status $rc)"
    fi
    if git -C "$clone" merge -q --ff-only refs/claude/incoming 2>/dev/null; then
      echo "$repo: applied $b -> $(git -C "$clone" log --oneline -1)"
    else
      # made from a line of history this clone has moved past (a commit landed on main in between): a later bundle carries its content
      echo "$repo: $b does not fast-forward main at $(git -C "$clone" rev-parse --short HEAD); skipped (superseded by a later bundle, or stale)"
    fi
  done
  rm -f "$err"
  if [ "$found" = 1 ]; then
    if [ "$(git -C "$clone" rev-parse HEAD)" = "$(git -C "$clone" rev-parse origin/main)" ]; then
      echo "$repo: GitHub already has everything"
    else
      git -C "$clone" push -q origin HEAD:main
      echo "$repo: pushed $(git -C "$clone" log --oneline -1)"
    fi
  else
    echo "$repo: no $repo-N.bundle in$BUNDLE_DIRS; nothing to apply"
  fi
done

# 6. Labels and issues, from the spec that arrived in the safety-governor bundle.
step "Labels and issues"
PUB="$WORK/safety-governor/tools/github/publish_experiments.sh"
[ -f "$PUB" ] || fail "$PUB is missing: the safety-governor bundle was not applied"
bash "$PUB"

step "Done"
for repo in safety-governor safety hardware-and-silicon autonomic-graph-regulation; do
  echo "https://github.com/$OWNER/$repo/issues"
done
echo "clones: $WORK   bundles inbox: $INBOX"
if [ -n "${was_running:-}" ]; then
  step "Program"
  bash "$WORK/safety-governor/tools/agents/run_program.sh" --detach
fi
