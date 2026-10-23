#!/usr/bin/env bash
# Stamp a repository with the PolyForm Noncommercial / CC BY-NC 4.0 licensing so the terms are
# indicated everywhere: the five license files at the root, and an SPDX header on every own-source
# file that lacks one. Idempotent and safe to run again: it never overwrites an existing file and
# never re-stamps a file that already carries an SPDX line.
#
#   bash tools/license/stamp.sh                 # stamp the current repository (run from its root)
#   bash tools/license/stamp.sh /path/to/repo   # stamp the repository at that path
#
# It stamps ONLY the project's own source (the directories in SRC_DIRS below). It never touches
# .venv, __pycache__, *.egg-info, .git, or vendored code, so third-party Apache/MIT headers are
# left alone. The canonical license texts live in the autonomic-graph-regulation repository; the
# copies this writes are for convenience and for GitHub's license detection, as the NOTICE says.
set -euo pipefail

REPO_DIR="$(cd "${1:-$(pwd)}" && pwd)"   # resolve to an absolute path so a "." argument still names the repo
cd "$REPO_DIR"
REPO="$(basename "$REPO_DIR")"
YEAR=2026
AUTHOR="Yobie Benjamin"
CANON="https://github.com/YobieBenjamin/autonomic-graph-regulation"
SELF="https://github.com/YobieBenjamin/$REPO"

# A human title per repository, for CITATION.cff. Unknown repos get a generic one.
case "$REPO" in
  safety-governor)            TITLE="safety-governor: a hardware safety governor that enforces AI action rules from outside the model" ;;
  hardware-and-silicon)       TITLE="hardware-and-silicon: the control-plane lane of a layered AI-safety architecture, and the silicon under it" ;;
  autonomic-graph-regulation) TITLE="autonomic-graph-regulation: detectors and the observer lane of a layered AI-safety architecture" ;;
  safety)                     TITLE="safety: the experiment program for a layered AI-safety architecture" ;;
  Watermark)                  TITLE="Watermark: provenance and watermarking experiments, and why they are not a lock" ;;
  *)                          TITLE="$REPO" ;;
esac

say() { printf '  %s\n' "$*"; }
echo "license stamp: $REPO ($REPO_DIR)"

# ---------------------------------------------------------------------------- root license files
# Create-if-missing only. Existing files (a repo that already carries them) are left untouched.
write_if_missing() { # path  <<heredoc body on stdin
  local path="$1"
  if [ -f "$path" ]; then say "keep   $path"; return; fi
  cat > "$path"; say "create $path"
}

if [ ! -f LICENSE.md ]; then
  say "WARN   LICENSE.md is missing; copy the PolyForm Noncommercial 1.0.0 text from $CANON/blob/main/LICENSE.md"
fi
if [ ! -f LICENSE-DOCS.txt ]; then
  say "WARN   LICENSE-DOCS.txt is missing; copy the CC BY-NC 4.0 text from $CANON/blob/main/LICENSE-DOCS.txt"
fi

write_if_missing NOTICE <<EOF
NOTICE

Copyright (c) $YEAR $AUTHOR. All rights reserved except as licensed below.

This repository ($SELF) is source-available, not open source.

  Software (all code: *.py, *.sh, *.sv, *.v, Makefile, pyproject.toml, source trees):
    PolyForm Noncommercial License 1.0.0 (see LICENSE.md)
    Required Notice: Copyright (c) $YEAR $AUTHOR ($SELF)

  Documentation, data and figures (README.md, docs/, blog/, results/ reports and JSON):
    Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) (see LICENSE-DOCS.txt)

Attribution is required for any use of this work, in whole or in part, including excerpts, derived
works, benchmarks, talks, papers and products. Attribution must include: the author's name
($AUTHOR), the repository URL, the version or commit used, and a copy of or link to this NOTICE.
Cite the work using the repository's CITATION.cff.

Commercial use of any part of this work requires a separate written license from the author. See
LICENSING.md for scope and contact.

The canonical copies of these licensing files for all of the author's repositories are kept at
$CANON.

Third-party names: NVIDIA, OpenShell, Sentry, BlueField and DOCA are trademarks of NVIDIA
Corporation; textGrain is OpenAI's. This work is independent and is not affiliated with, sponsored
by or endorsed by NVIDIA or OpenAI.
EOF

write_if_missing CITATION.cff <<EOF
cff-version: 1.2.0
message: "If you use this work, in whole or in part, please cite it as below. Attribution is required (see NOTICE)."
type: software
title: "$TITLE"
authors:
  - family-names: Benjamin
    given-names: Yobie
version: "0.1.0"
date-released: "$YEAR-10-23"
repository-code: "$SELF"
url: "$SELF"
license: PolyForm-Noncommercial-1.0.0
license-url: "$CANON/blob/main/LICENSE.md"
keywords:
  - "AI safety"
  - "hardware root of trust"
  - "reference monitor"
abstract: "Part of a layered AI-safety architecture. Software is licensed under PolyForm Noncommercial 1.0.0; documentation, data and figures under CC BY-NC 4.0. Attribution is required; commercial use requires a separate license (see LICENSING.md)."
EOF

write_if_missing LICENSING.md <<EOF
# Licensing

Source-available, not open source. Copyright (c) $YEAR $AUTHOR. Software is licensed under the
PolyForm Noncommercial License 1.0.0 ([LICENSE.md]($CANON/blob/main/LICENSE.md)); documentation,
data and figures under CC BY-NC 4.0 ([LICENSE-DOCS.txt]($CANON/blob/main/LICENSE-DOCS.txt)).
Attribution is required for any use in whole or in part ([NOTICE]($CANON/blob/main/NOTICE));
commercial use requires a separate written license from the author.

This repository is [$REPO]($SELF). The canonical copies of these licensing files for all of the
author's repositories live in [autonomic-graph-regulation]($CANON); the files beside this one are
copies for convenience and for GitHub's license detection.

## What is covered by which license

| Part of a repository | License | File |
|---|---|---|
| Software: all code (\`*.py\`, \`*.sh\`, \`*.sv\`, \`*.v\`, \`Makefile\`, \`pyproject.toml\`, \`tests/\`) | PolyForm Noncommercial License 1.0.0 | [LICENSE.md]($CANON/blob/main/LICENSE.md) |
| Documentation, data and figures: README.md, docs/, blog/, results/ | CC BY-NC 4.0 | [LICENSE-DOCS.txt]($CANON/blob/main/LICENSE-DOCS.txt) |

Both licenses permit noncommercial use with attribution, and changes and redistribution under the
same terms. Neither permits commercial use. The license texts govern; this page is a map.

## Commercial use

Commercial use of any part of this work, including use inside a product or service, use by or on
behalf of a for-profit company, paid consulting built on it, and training or evaluating commercial
models with it, requires a separate written license from the author.

## Contact

Yobie Benjamin, via GitHub: https://github.com/YobieBenjamin.

## Scope notes

- If a copy here differs from the canonical copy, the canonical copy governs.
- Third-party names and marks are their owners' (see NOTICE); nothing here grants rights in them.
EOF

# ---------------------------------------------------------------------------- SPDX source headers
# Own-source directories only. Never .venv, caches, egg-info, or .git.
SRC_DIRS="govsim rtl proofs tools hw tests hardware_ref observer safety_observer agr miner orchestrator sandbox scripts textgrain_ref src"
SPDX="SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0"
COPY="Copyright (c) $YEAR $AUTHOR. Noncommercial use only; see NOTICE and LICENSING.md."

stamped=0; skipped=0
stamp_file() {
  local f="$1"
  grep -q "SPDX-License-Identifier" "$f" 2>/dev/null && { skipped=$((skipped+1)); return; }
  local tmp; tmp="$(mktemp)"
  local first; first="$(head -1 "$f" 2>/dev/null || true)"
  case "$first" in
    "#!"*)  # keep the shebang on line 1
      { printf '%s\n' "$first"; printf '# %s\n# %s\n' "$SPDX" "$COPY"; tail -n +2 "$f"; } > "$tmp" ;;
    *)
      { printf '# %s\n# %s\n' "$SPDX" "$COPY"; cat "$f"; } > "$tmp" ;;
  esac
  cat "$tmp" > "$f"; rm -f "$tmp"; stamped=$((stamped+1))
}

for d in $SRC_DIRS; do
  [ -d "$d" ] || continue
  # find our own .py and .sh, excluding caches and any stray venv under a source dir
  while IFS= read -r f; do
    case "$f" in
      *.venv/*|*/__pycache__/*|*.egg-info/*) continue ;;
    esac
    stamp_file "$f"
  done < <(find "$d" -type f \( -name '*.py' -o -name '*.sh' \) 2>/dev/null)
done

say "SPDX: stamped $stamped file(s), left $skipped already-stamped or vendored file(s) alone"
echo "done: $REPO"
