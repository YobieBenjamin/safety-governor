#!/usr/bin/env bash
# Publish the chip program's experiments to GitHub: labels and one issue per experiment, in the
# repository each experiment belongs to, from tools/github/experiments.json. Idempotent: labels
# are created or updated, and an issue whose title already exists is updated, not duplicated.
#
#   tools/github/publish_experiments.sh                # labels + issues in all three repositories
#   tools/github/publish_experiments.sh --apply-bundles DIR   # first fast-forward each local clone from
#                                                      # DIR/<repo>-*.bundle and push, then publish
#   tools/github/publish_experiments.sh --dry-run      # print what would be done
#
# Needs: gh (logged in as YobieBenjamin), python3, git. Run from any directory.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SPEC="$HERE/experiments.json"
OWNER="${GITHUB_OWNER:-YobieBenjamin}"
DRY=0; BUNDLES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --apply-bundles) BUNDLES="$2"; shift ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
  shift
done
run() { if [ "$DRY" = 1 ]; then echo "+ $*"; else "$@"; fi; }

gh auth status >/dev/null 2>&1 || { echo "gh is not logged in; run: gh auth login" >&2; exit 1; }

# 1. Optionally bring the local clones up to date from bundles made in the program's container
#    (the container cannot push), then push each repository.
if [ -n "$BUNDLES" ]; then
  for repo in safety-governor safety hardware-and-silicon; do
    clone="$HOME/$repo"
    [ -d "$clone/.git" ] || { echo "no clone at $clone, skipping" >&2; continue; }
    for b in "$BUNDLES"/"$repo"-*.bundle; do
      [ -f "$b" ] || continue
      echo "== $repo: applying $(basename "$b")"
      run git -C "$clone" fetch "$b" main:refs/claude/incoming
      run git -C "$clone" merge --ff-only refs/claude/incoming
    done
    run git -C "$clone" push origin main
  done
fi

# 2. Labels, in every repository the spec names.
repos=$(python3 -c "import json,sys; s=json.load(open(sys.argv[1])); print(' '.join(sorted({i['repo'] for i in s['issues']})))" "$SPEC")
python3 -c "import json,sys; [print(l['name'], l['color'], l['description'], sep='\t') for l in json.load(open(sys.argv[1]))['labels']]" "$SPEC" |
while IFS=$'\t' read -r name color desc; do
  for repo in $repos; do
    run gh label create "$name" --repo "$OWNER/$repo" --color "$color" --description "$desc" --force >/dev/null
  done
done
echo "labels: done in $repos"

# 3. One issue per experiment; update the body and labels if the title already exists. The
#    existing issues of each repository are listed once (no search: titles are long and contain
#    quotes). A failure is reported with gh's message and the run continues; the exit status says
#    whether every issue went through.
failed=0
for repo in $repos; do
  have=$(mktemp)
  gh issue list --repo "$OWNER/$repo" --state all --json number,title --limit 1000 > "$have" 2>/dev/null || echo "[]" > "$have"
  python3 -c "
import json, sys
for i in json.load(open(sys.argv[1]))['issues']:
    if i['repo'] == sys.argv[2]:
        print(json.dumps(i))" "$SPEC" "$repo" |
  while IFS= read -r line; do
    title=$(printf '%s' "$line" | python3 -c "import json,sys; print(json.load(sys.stdin)['title'])")
    labels=$(printf '%s' "$line" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin)['labels']))")
    body=$(mktemp); printf '%s' "$line" | python3 -c "import json,sys; sys.stdout.write(json.load(sys.stdin)['body'])" > "$body"
    existing=$(python3 -c "
import json, sys
m = [i for i in json.load(open(sys.argv[1])) if i['title'] == sys.argv[2]]
print(m[0]['number'] if m else '')" "$have" "$title")
    if [ -n "$existing" ]; then
      printf '== %s #%s (update): %s\n' "$repo" "$existing" "$title"
      out=$(run gh issue edit "$existing" --repo "$OWNER/$repo" --body-file "$body" --add-label "$labels" 2>&1) && echo "   $out" || { echo "   FAILED: $out"; echo fail >> "$have.failed"; }
    else
      printf '== %s (create): %s\n' "$repo" "$title"
      out=$(run gh issue create --repo "$OWNER/$repo" --title "$title" --body-file "$body" --label "$labels" 2>&1) && echo "   $out" || { echo "   FAILED: $out"; echo fail >> "$have.failed"; }
    fi
    rm -f "$body"
  done
  [ -f "$have.failed" ] && failed=$((failed + $(wc -l < "$have.failed" | tr -d ' ')))
  rm -f "$have" "$have.failed"
done
if [ "$failed" -gt 0 ]; then echo "issues: $failed FAILED (see above)"; exit 1; fi
echo "issues: done"
