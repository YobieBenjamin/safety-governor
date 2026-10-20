#!/usr/bin/env bash
# One script for a Mac that has nothing set up yet. In order: make sure gh is installed, log in to
# GitHub in the browser if needed, clone the three repositories where they are missing, bring each
# clone up to date, apply the bundles made in the program's container, push, then publish the
# experiments as labels and issues in all three repositories.
#
#   bash ~/Downloads/setup_and_publish.sh              # bundles are looked for next to the script
#   bash ~/Downloads/setup_and_publish.sh ~/some/dir   # or in the directory given
#
# Safe to run again: every step checks before it acts. It never force-pushes and never deletes.
# The safety repository is cloned without its 8 GB of recordings (a blobless, sparse clone); add a
# directory later with: git -C ~/safety sparse-checkout add algorithms/<name>
set -euo pipefail
OWNER="${GITHUB_OWNER:-YobieBenjamin}"
BASE="${GITHUB_BASE:-https://github.com/$OWNER}"   # where the repositories are cloned from
BUNDLES="${1:-$(cd "$(dirname "$0")" && pwd)}"
REPOS="${REPOS:-safety-governor safety hardware-and-silicon}"
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

# 3. Clones, where they are missing.
step "Clones"
for repo in $REPOS; do
  clone="$HOME/$repo"
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

# 4. Each clone: up to date with GitHub, then fast-forwarded from <repo>-N.bundle (lowest N first),
#    then pushed. A bundle the clone already contains is skipped.
step "Bundles from $BUNDLES"
for repo in $REPOS; do
  clone="$HOME/$repo"
  branch=$(git -C "$clone" rev-parse --abbrev-ref HEAD)
  [ "$branch" = main ] || fail "$repo is on branch '$branch'; check out main and run again"
  [ -z "$(git -C "$clone" status --porcelain --untracked-files=no)" ] || fail "$repo has uncommitted changes; commit or stash them and run again"
  git -C "$clone" fetch -q origin main
  git -C "$clone" merge -q --ff-only origin/main || fail "$repo has local commits that are not on GitHub; push or move them first"
  found=0
  err=$(mktemp)
  for b in $(ls "$BUNDLES" 2>/dev/null | grep -E "^$repo-[0-9]+\.bundle$" | sed -E "s/^$repo-([0-9]+)\.bundle$/\1 &/" | sort -n | cut -d' ' -f2); do
    found=1
    path="$BUNDLES/$b"
    if ! git -C "$clone" fetch -q "$path" main:refs/claude/incoming 2>"$err"; then
      grep -q prerequisite "$err" && fail "$repo: $b builds on commits this clone does not have (a newer bundle may be needed, or an older one applied first)"
      cat "$err" >&2; exit 1
    fi
    if git -C "$clone" merge-base --is-ancestor refs/claude/incoming HEAD; then
      echo "$repo: already contains $b"
    else
      git -C "$clone" merge -q --ff-only refs/claude/incoming
      echo "$repo: applied $b -> $(git -C "$clone" log --oneline -1)"
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
    echo "$repo: no $repo-N.bundle in $BUNDLES; nothing to apply"
  fi
done

# 5. Labels and issues, from the spec that arrived in the safety-governor bundle.
step "Labels and issues"
PUB="$HOME/safety-governor/tools/github/publish_experiments.sh"
[ -f "$PUB" ] || fail "$PUB is missing: the safety-governor bundle was not applied"
bash "$PUB"

step "Done"
for repo in $REPOS autonomic-graph-regulation; do
  echo "https://github.com/$OWNER/$repo/issues"
done
