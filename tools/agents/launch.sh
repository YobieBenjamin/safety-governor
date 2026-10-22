#!/usr/bin/env bash
# One command for one wave: the Claude CLI (installed and logged in), a Python environment with the
# dependencies in each repository, the preflight, then the wave in every repository that has issues
# in it, detached, so the terminal can be closed.
#
#   bash ~/safety-governor/tools/agents/launch.sh 1            # wave 1: safety-governor (L4, L5, H1) and safety (YB-0052)
#   START_AT=23:00 bash ~/safety-governor/tools/agents/launch.sh 2
#   bash ~/safety-governor/tools/agents/launch.sh prepare      # only the CLI, the environments and the local model (run_program.sh uses this)
#
# Everything run_wave.sh accepts as an environment variable passes through (AGENT_MODEL, EFFORT,
# MAX_TURNS, BUDGET_USD, PARALLEL, FIVE_HOUR_CEILING, ...). Safe to run again.
set -euo pipefail
set -E; trap 'echo "error: line $LINENO: $BASH_COMMAND (exit status $?)" >&2' ERR
WAVE="${1:?usage: launch.sh <wave> | launch.sh prepare}"   # "prepare": steps 1 to 3 only (the CLI, the environments, the local model)
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
export PATH="$HOME/.local/bin:$PATH"
. "$(cd "$(dirname "$0")" && pwd)/paths.sh"   # WORK: where the clones live

# 1. The Claude CLI, at a version the launcher needs (2.1.259 or later: --permission-prompts, --max-budget-usd,
#    --json-schema, claude auth). An older or missing one is replaced by the native installer (into
#    ~/.local/bin, first on PATH here, no sudo). Then a login, in the browser, when the stored one is not valid.
step "Claude CLI"
MIN=2.1.259
have=$(claude -v 2>/dev/null | head -1 || true)
if [ -z "$have" ] || ! python3 "$WORK/safety-governor/tools/agents/wave_lib.py" version_ok "$have" "$MIN"; then
  echo "claude ${have:-is missing}; installing the current one"
  curl -fsSL https://claude.ai/install.sh | bash
  hash -r 2>/dev/null || true
  grep -q '.local/bin' "$HOME/.zshrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
  have=$(claude -v 2>/dev/null | head -1 || true)
  python3 "$WORK/safety-governor/tools/agents/wave_lib.py" version_ok "$have" "$MIN" || { echo "claude is still $have at $(command -v claude); remove the old one and run again" >&2; exit 1; }
fi
echo "claude $have at $(command -v claude)"
if ! claude auth status >/dev/null 2>&1; then
  echo "log in to Claude in the browser (the account with the subscription)"
  claude auth login
  claude auth status >/dev/null 2>&1 || { echo "the Claude CLI is still not logged in" >&2; exit 1; }
fi
claude auth status --text 2>/dev/null | head -2 || true

# 2. A Python environment per repository, with its own tests' dependencies. run_wave.sh uses
#    .venv/bin when it exists; so do the agents' python3 and pytest commands.
step "Python environments"
# The repositories need Python 3.11 or later; macOS ships 3.9. Find one, or install one with Homebrew.
PY=""
for cand in python3.13 python3.12 python3.11 /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then PY="$(command -v "$cand")"; break; fi
done
if [ -z "$PY" ]; then
  command -v brew >/dev/null 2>&1 || { echo "no Python 3.11+ and no Homebrew to install one (https://brew.sh, then run again)" >&2; exit 1; }
  echo "no Python 3.11+ on this Mac; installing python@3.12 with Homebrew"
  brew install -q python@3.12
  PY="$(brew --prefix python@3.12)/bin/python3.12"
fi
echo "python: $PY ($("$PY" --version 2>&1))"
for repo in safety-governor safety; do
  [ -d "$WORK/$repo/.git" ] || { echo "$repo: no clone at $WORK/$repo (run setup_and_publish.sh first)"; continue; }
  cd "$WORK/$repo"
  if [ -x .venv/bin/python3 ] && ! .venv/bin/python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    echo "$repo: the existing .venv is $(.venv/bin/python3 --version 2>&1); remaking it"; rm -rf .venv
  fi
  [ -x .venv/bin/python3 ] || "$PY" -m venv .venv
  .venv/bin/python3 -m pip install -q --upgrade pip
  case "$repo" in
    safety-governor)
      .venv/bin/python3 -m pip install -q -e ".[dev]"
      [ -d "$WORK/hardware-and-silicon" ] && .venv/bin/python3 -m pip install -q -e "$WORK/hardware-and-silicon"
      ;;
    safety)
      .venv/bin/python3 -m pip install -q -e "observer[dev]"
      ;;
  esac
  echo "$repo: $(.venv/bin/python3 --version), pytest $(.venv/bin/python3 -c 'import pytest; print(pytest.__version__)')"
done

# 3. The local model, when Ollama is on this Mac: the Qwen3 tag (or LOCAL_MODEL), with a 64k context
#    variant made once (Claude Code needs 64k or more; Ollama's default is smaller). Nothing here is
#    fatal: without Ollama the local tier's jobs go to the cloud, or to the cheap cloud model with
#    LOCAL_URL=cloud.
step "Local model"
# shellcheck source=tools/agents/local_model.sh
. "$WORK/safety-governor/tools/agents/local_model.sh"
find_local_model
if [ "$LOCAL_URL" = cloud ]; then echo "LOCAL_URL=cloud: the cheap cloud model ($LOCAL_MODEL) takes the local tier's jobs"
elif [ "$LOCAL_OK" = 1 ]; then echo "local model: $LOCAL_MODEL at $LOCAL_URL; it takes the local-only issues, the repair passes and the second reading of every review"
else echo "no Ollama server answers at $LOCAL_URL and none could be started (https://ollama.com/download; then: ollama pull qwen3.5:27b); local work goes to the cloud this wave"; fi

[ "$WAVE" = prepare ] && { step "Prepared"; exit 0; }

# 4. Preflight, then the wave, in each repository that has issues in this wave.
RUN="$WORK/safety-governor/tools/agents/run_wave.sh"
for repo in safety-governor safety; do
  [ -d "$WORK/$repo/.git" ] || continue
  cd "$WORK/$repo"
  if ! python3 "$WORK/safety-governor/tools/agents/wave_lib.py" issues "$WORK/safety-governor/tools/github/experiments.json" "$WAVE" "$repo" | grep -q .; then
    echo "$repo: no issues in wave $WAVE"; continue
  fi
  step "$repo: preflight"
  bash "$RUN" "$WAVE" --check
  step "$repo: wave $WAVE, detached"
  bash "$RUN" "$WAVE" --detach
done

step "Running"
echo "Close the terminal if you like. Progress: .agents/wave-$WAVE/STATUS.md in each repository (every ten minutes),"
echo "the GitHub issues (a comment per finished agent), and a notification per agent. The wave ends with REPORT.md."
