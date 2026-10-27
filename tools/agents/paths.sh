# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# Where the clones live. Sourced by every script under tools/; setup_and_publish.sh carries the
# same three lines itself, because it runs before any clone exists.
#
# The four repositories (safety-governor, safety, hardware-and-silicon, Watermark) sit beside each
# other in one directory. On the Mac mini that is the external drive, /Volumes/External_4TB/Safety
# Experiments, whenever it is mounted; anywhere else it is $HOME. PROJECT_WORK overrides both.
# After the move, ~/<repo> stays behind as a symlink to the moved clone, so an old command still
# lands in the right place. GitHub (github.com/YobieBenjamin) is the source of truth either way.
WORK="${PROJECT_WORK:-}"
if [ -z "$WORK" ]; then
  if [ -d "/Volumes/External_4TB/Safety Experiments" ]; then WORK="/Volumes/External_4TB/Safety Experiments"; else WORK="$HOME"; fi
fi
INBOX="$WORK/inbox"   # bundles made in the program's container land here (setup_and_publish.sh also looks beside itself)

# Signal a process and everything under it, children first. Every watchdog here used to signal the
# shell around an agent; the shell died on TERM and its claude lived on as an orphan (WAVE-MUTATION-TESTING-GATE on 21 October
# kept writing its log for an hour after its launcher had reported it done).
sig_tree() { local pid="$1" sig="${2:-TERM}" c; for c in $(pgrep -P "$pid" 2>/dev/null || true); do sig_tree "$c" "$sig"; done; kill -"$sig" "$pid" 2>/dev/null || true; }
# An agent is a claude process a launcher started with --add-dir <clone>/.agents/wave-N; a person's own claude session never carries that.
orphan_agents() { pgrep -f -- "--add-dir [^ ]*/\.agents/wave-" 2>/dev/null || true; }
