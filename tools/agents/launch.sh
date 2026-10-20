#!/usr/bin/env bash
# One command for one wave: the Claude CLI (installed and logged in), a Python environment with the
# dependencies in each repository, the preflight, then the wave in every repository that has issues
# in it, detached, so the terminal can be closed.
#
#   bash ~/safety-governor/tools/agents/launch.sh 1            # wave 1: safety-governor (L4, L5, H1) and safety (YB-0052)
#   START_AT=23:00 bash ~/safety-governor/tools/agents/launch.sh 2
#
# Everything run_wave.sh accepts as an environment variable passes through (AGENT_MODEL, EFFORT,
# MAX_TURNS, BUDGET_USD, PARALLEL, FIVE_HOUR_CEILING, ...). Safe to run again.
set -euo pipefail
set -E; trap 'echo "error: line $LINENO: $BASH_COMMAND (exit status $?)" >&2' ERR
WAVE="${1:?usage: launch.sh <wave>}"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
export PATH="$HOME/.local/bin:$PATH"

# 1. The Claude CLI: the native installer when it is missing (into ~/.local/bin, no sudo), then a login.
step "Claude CLI"
if ! command -v claude >/dev/null 2>&1; then
  curl -fsSL https://claude.ai/install.sh | bash
  grep -q '.local/bin' "$HOME/.zshrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
fi
claude -v | head -1
if ! claude auth status >/dev/null 2>&1; then
  echo "log in to Claude in the browser (the account with the subscription)"
  claude auth login
fi
claude auth status --text 2>/dev/null | head -2 || true

# 2. A Python environment per repository, with its own tests' dependencies. run_wave.sh uses
#    .venv/bin when it exists; so do the agents' python3 and pytest commands.
step "Python environments"
for repo in safety-governor safety; do
  [ -d "$HOME/$repo/.git" ] || { echo "$repo: no clone at ~/$repo (run setup_and_publish.sh first)"; continue; }
  cd "$HOME/$repo"
  [ -x .venv/bin/python3 ] || python3 -m venv .venv
  .venv/bin/python3 -m pip install -q --upgrade pip
  case "$repo" in
    safety-governor)
      .venv/bin/python3 -m pip install -q -e ".[dev]"
      [ -d "$HOME/hardware-and-silicon" ] && .venv/bin/python3 -m pip install -q -e "$HOME/hardware-and-silicon"
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
LOCAL_URL="${LOCAL_URL:-http://localhost:11434}"
if [ "$LOCAL_URL" = cloud ]; then
  echo "LOCAL_URL=cloud: the cheap cloud model (${LOCAL_MODEL:-haiku}) takes the local tier's jobs"
elif command -v ollama >/dev/null 2>&1; then
  curl -fs --max-time 5 "$LOCAL_URL/api/tags" >/dev/null 2>&1 || { (ollama serve > /dev/null 2>&1 &) ; sleep 4; }
  if curl -fs --max-time 5 "$LOCAL_URL/api/tags" >/dev/null 2>&1; then
    base="${LOCAL_MODEL:-$(ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -i qwen3 | grep -v -- '-64k' | head -1)}"
    if [ -n "$base" ]; then
      case "$base" in
        *-64k) tag="$base" ;;
        *) tag="$(echo "$base" | tr ':' '-')-64k"
           if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$tag:latest"; then
             printf 'FROM %s\nPARAMETER num_ctx 65536\n' "$base" > /tmp/agents-64k.modelfile
             ollama create "$tag" -f /tmp/agents-64k.modelfile >/dev/null && echo "made $tag: $base with a 64k context"
           fi ;;
      esac
      export LOCAL_MODEL="$tag"
      echo "local model: $LOCAL_MODEL (from $base) at $LOCAL_URL; it takes the local-only issues and the repair passes"
    else
      echo "Ollama runs but no qwen3 model is pulled; set LOCAL_MODEL=<tag> or: ollama pull qwen3.5"
    fi
  else
    echo "Ollama is installed but not answering at $LOCAL_URL; local work goes to the cloud this wave"
  fi
else
  echo "no Ollama on this Mac (https://ollama.com/download); local work goes to the cloud this wave, or set LOCAL_URL=cloud for the cheap cloud model"
fi
export LOCAL_URL

# 4. Preflight, then the wave, in each repository that has issues in this wave.
RUN="$HOME/safety-governor/tools/agents/run_wave.sh"
for repo in safety-governor safety; do
  [ -d "$HOME/$repo/.git" ] || continue
  cd "$HOME/$repo"
  if ! python3 "$HOME/safety-governor/tools/agents/wave_lib.py" issues "$HOME/safety-governor/tools/github/experiments.json" "$WAVE" "$repo" | grep -q .; then
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
