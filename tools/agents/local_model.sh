#!/usr/bin/env bash
# Sourced by launch.sh and run_wave.sh. Sets LOCAL_OK (1 or 0) and LOCAL_MODEL for the Ollama server at
# LOCAL_URL: probes the API; if nothing answers, starts the Ollama app or the ollama binary from the
# places the installers use; then picks (or makes, through the API) a qwen3 model with a 64k context.
# LOCAL_URL=cloud means: no local model, the cheap cloud model (LOCAL_MODEL, default haiku) stands in.
find_local_model() {
  LOCAL_URL="${LOCAL_URL:-http://localhost:11434}"; LOCAL_OK=0
  if [ "$LOCAL_URL" = cloud ]; then LOCAL_MODEL="${LOCAL_MODEL:-haiku}"; LOCAL_OK=1; return 0; fi
  local lib; lib="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/wave_lib.py"
  if ! curl -fs --max-time 5 "$LOCAL_URL/api/tags" >/dev/null 2>&1; then
    local bin=""
    for cand in ollama /usr/local/bin/ollama /opt/homebrew/bin/ollama "/Applications/Ollama.app/Contents/Resources/ollama" "$HOME/Applications/Ollama.app/Contents/Resources/ollama"; do
      if command -v "$cand" >/dev/null 2>&1; then bin="$cand"; break; fi
    done
    if [ -d /Applications/Ollama.app ] || [ -d "$HOME/Applications/Ollama.app" ]; then open -a Ollama >/dev/null 2>&1 || true
    elif [ -n "$bin" ]; then ("$bin" serve >/dev/null 2>&1 &); fi
    local i=0; while [ $i -lt 15 ] && ! curl -fs --max-time 2 "$LOCAL_URL/api/tags" >/dev/null 2>&1; do sleep 2; i=$((i + 1)); done
  fi
  if curl -fs --max-time 5 "$LOCAL_URL/api/tags" >/dev/null 2>&1; then
    local pick; pick=$(python3 "$lib" local "$LOCAL_URL" "${LOCAL_MODEL:-}" 2>/dev/null | head -1 || true)
    if [ -n "$pick" ]; then LOCAL_MODEL="$pick"; LOCAL_OK=1; fi
  fi
  export LOCAL_URL LOCAL_MODEL LOCAL_OK
}
