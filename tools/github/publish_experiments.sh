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
HERE="$(cd "$(dirname "$0")" && pwd)"; . "$HERE/../agents/paths.sh"   # WORK: where the clones live
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
    clone="$WORK/$repo"
    [ -d "$clone/.git" ] || { echo "no clone at $clone, skipping" >&2; continue; }
    for b in "$BUNDLES"/"$repo"-*.bundle; do
      [ -f "$b" ] || continue
      echo "== $repo: applying $(basename "$b")"
      run git -C "$clone" fetch "$b" "+main:refs/claude/incoming"
      run git -C "$clone" merge --ff-only refs/claude/incoming
    done
    run git -C "$clone" push origin main
  done
fi

# 1b. The spec itself, against GitHub's limits, before anything is touched: label descriptions at
#     most 100 characters, titles at most 256, every label an issue uses defined, colors six hex digits.
python3 - "$SPEC" <<'PY' || exit 1
import json, re, sys
s = json.load(open(sys.argv[1])); bad = []
names = {l["name"] for l in s["labels"]}
for l in s["labels"]:
    if len(l["description"]) > 100: bad.append(f"label {l['name']}: description is {len(l['description'])} characters (max 100)")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", l["color"]): bad.append(f"label {l['name']}: color {l['color']!r} is not six hex digits")
for i in s["issues"]:
    if len(i["title"]) > 256: bad.append(f"issue {i['id']}: title is {len(i['title'])} characters (max 256)")
    for lab in i["labels"]:
        if lab not in names: bad.append(f"issue {i['id']}: label {lab!r} is not defined")
if bad:
    print("experiments.json is not publishable:\n  " + "\n  ".join(bad), file=sys.stderr); sys.exit(1)
print(f"spec: {len(s['labels'])} labels, {len(s['issues'])} issues, within GitHub's limits")
PY

# 2. Labels, in every repository the spec names. A failure is reported and the run continues.
repos=$(python3 -c "import json,sys; s=json.load(open(sys.argv[1])); print(' '.join(sorted({i['repo'] for i in s['issues']})))" "$SPEC")
lfail=$(mktemp)
python3 -c "import json,sys; [print(l['name'], l['color'], l['description'], sep='\t') for l in json.load(open(sys.argv[1]))['labels']]" "$SPEC" |
while IFS=$'\t' read -r name color desc; do
  for repo in $repos; do
    out=$(run gh label create "$name" --repo "$OWNER/$repo" --color "$color" --description "$desc" --force 2>&1) || { echo "label $name in $repo FAILED: $out"; echo fail >> "$lfail"; }
  done
done
if [ -s "$lfail" ]; then echo "labels: $(wc -l < "$lfail" | tr -d ' ') FAILED in $repos (see above)"; else echo "labels: done in $repos"; fi
rm -f "$lfail"

# 3. One issue per experiment; update the body and labels if the title already exists. The
#    existing issues of each repository are listed once (no search: titles are long and contain
#    quotes). A failure is reported with gh's message and the run continues; the exit status says
#    whether every issue went through.
failed=0
for repo in $repos; do
  have=$(mktemp)
  gh issue list --repo "$OWNER/$repo" --state all --json number,title,state --limit 1000 > "$have" 2>/dev/null || echo "[]" > "$have"
  python3 -c "
import json, sys
for i in json.load(open(sys.argv[1]))['issues']:
    if i['repo'] == sys.argv[2]:
        print(json.dumps(i))" "$SPEC" "$repo" |
  while IFS= read -r line; do
    title=$(printf '%s' "$line" | python3 -c "import json,sys; print(json.load(sys.stdin)['title'])")
    labels=$(printf '%s' "$line" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin)['labels']))")
    body=$(mktemp); printf '%s' "$line" | python3 -c "import json,sys; sys.stdout.write(json.load(sys.stdin)['body'])" > "$body"
    # the issue is matched by its exact title, else by its id prefix ("L5 · ") when a brief's title was
    # corrected; the lowest-numbered one is kept and retitled, later duplicates are closed
    ident=$(printf '%s' "$line" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
    match=$(python3 -c "
import json, sys
issues = json.load(open(sys.argv[1])); title, ident = sys.argv[2], sys.argv[3]
exact = [i for i in issues if i['title'] == title]
# a closed issue still counts as the issue (closing #7 by hand must not make the next run open a new L7);
# only open ones are ever closed as duplicates
pref = sorted([i for i in issues if i['title'].startswith(ident + ' \u00b7 ')], key=lambda i: i['number'])
cands = sorted({i['number']: i for i in exact + pref}.values(), key=lambda i: i['number'])
keep = cands[0] if cands else None   # the oldest issue is the issue: pull requests and comments point at it
dupes = [i['number'] for i in pref if keep and i['number'] != keep['number'] and i.get('state', 'OPEN') == 'OPEN']
print((str(keep['number']) if keep else '') + '|' + ' '.join(map(str, dupes)) + '|' + ('retitle' if keep and keep['title'] != title else '') + '|' + (keep.get('state', 'OPEN') if keep else ''))" "$have" "$title" "$ident")
    existing="${match%%|*}"; rest="${match#*|}"; dupes="${rest%%|*}"; rest="${rest#*|}"; retitle="${rest%%|*}"; state="${rest#*|}"
    if [ -n "$existing" ] && [ "$retitle" = retitle ]; then
      printf '== %s #%s: title updated to match the corrected brief\n' "$repo" "$existing"
      run gh issue edit "$existing" --repo "$OWNER/$repo" --title "$title" >/dev/null 2>&1 || echo "   could not retitle #$existing"
    fi
    for d in $dupes; do
      printf '== %s #%s: closed as a duplicate of #%s\n' "$repo" "$d" "$existing"
      run gh issue close "$d" --repo "$OWNER/$repo" --comment "Duplicate of #$existing: the brief's title changed when it was corrected, and the publisher matched by title. #$existing is the issue; nothing else changes." >/dev/null 2>&1 || echo "   could not close #$d"
    done
    if [ -n "$existing" ]; then
      printf '== %s #%s (update): %s\n' "$repo" "$existing" "$title"
      out=$(run gh issue edit "$existing" --repo "$OWNER/$repo" --body-file "$body" --add-label "$labels" 2>&1) && echo "   $out" || { echo "   FAILED: $out"; echo fail >> "$have.failed"; }
      # a finished experiment: --add-label never removes, so drop status:open, and close the issue if it is open
      case ",$labels," in *,status:done,*)
        run gh issue edit "$existing" --repo "$OWNER/$repo" --remove-label "status:open" >/dev/null 2>&1 || true
        if [ "$state" = OPEN ]; then
          printf '== %s #%s: closed, the experiment is done (see its body)\n' "$repo" "$existing"
          run gh issue close "$existing" --repo "$OWNER/$repo" --comment "Done: the result is in the issue body." >/dev/null 2>&1 || echo "   could not close #$existing"
        fi ;;
      esac
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
