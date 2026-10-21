#!/usr/bin/env bash
# Sourced by launch.sh and run_wave.sh. Sets LOCAL_OK (1 or 0) and LOCAL_MODEL for the Ollama server at
# LOCAL_URL: probes the API; if nothing answers, starts the Ollama app or the ollama binary from the
# places the installers use; then picks (or makes, through the API) a qwen3 model with a 64k context.
# LOCAL_URL=cloud means: no local model, the cheap cloud model (LOCAL_MODEL, default haiku) stands in.
LOCAL_THINK="${LOCAL_THINK:-0}"
local_prefix() { [ "$LOCAL_THINK" = 1 ] || printf '/no_think '; }   # Qwen3's soft switch; harmless for models without one
ollama_answers() { curl -fs --noproxy '*' --max-time 5 "$1/api/tags" >/dev/null 2>&1; }
find_local_model() {
  LOCAL_OK=0
  if [ "${LOCAL_URL:-}" = cloud ]; then LOCAL_MODEL="${LOCAL_MODEL:-haiku}"; LOCAL_OK=1; return 0; fi
  # Ollama's own OLLAMA_HOST (host:port, or a URL) wins when LOCAL_URL is not given; then the usual addresses
  if [ -z "${LOCAL_URL:-}" ] && [ -n "${OLLAMA_HOST:-}" ]; then
    case "$OLLAMA_HOST" in http*) LOCAL_URL="$OLLAMA_HOST" ;; *) LOCAL_URL="http://${OLLAMA_HOST/0.0.0.0/127.0.0.1}" ;; esac
  fi
  LOCAL_URL="${LOCAL_URL:-http://localhost:11434}"
  local lib; lib="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/wave_lib.py"
  if ! ollama_answers "$LOCAL_URL"; then
    local alt; for alt in http://127.0.0.1:11434 http://localhost:11434 "http://[::1]:11434"; do
      if ollama_answers "$alt"; then LOCAL_URL="$alt"; break; fi
    done
  fi
  if ! ollama_answers "$LOCAL_URL"; then
    local bin=""
    for cand in ollama /usr/local/bin/ollama /opt/homebrew/bin/ollama "/Applications/Ollama.app/Contents/Resources/ollama" "$HOME/Applications/Ollama.app/Contents/Resources/ollama"; do
      if command -v "$cand" >/dev/null 2>&1; then bin="$cand"; break; fi
    done
    if [ -d /Applications/Ollama.app ] || [ -d "$HOME/Applications/Ollama.app" ]; then open -a Ollama >/dev/null 2>&1 || true
    elif [ -n "$bin" ]; then ("$bin" serve >/dev/null 2>&1 &); fi
    local i=0; while [ $i -lt 15 ] && ! ollama_answers "$LOCAL_URL"; do sleep 2; i=$((i + 1)); done
  fi
  if ollama_answers "$LOCAL_URL"; then
    local pick; pick=$(python3 "$lib" local "$LOCAL_URL" "${LOCAL_MODEL:-}" 2>/dev/null | head -1 || true)
    if [ -n "$pick" ]; then LOCAL_MODEL="$pick"; LOCAL_OK=1; fi
  fi
  export LOCAL_URL LOCAL_MODEL LOCAL_OK
}
