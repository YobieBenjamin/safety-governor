#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# The discussion forum, kept apart from the product: a separate public repository with GitHub Discussions on, its own
# license (CC BY 4.0, contributors keep their copyright), and a pinned first post explaining what goes where.
# Idempotent: run it again and it updates the files, creates nothing twice.
#
#   bash tools/github/discussion_repo.sh
#
# Needs gh logged in as YobieBenjamin.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OWNER=${GITHUB_OWNER:-YobieBenjamin}
NAME=${DISCUSSION_REPO:-chip-that-says-no-discussion}
REPO=$OWNER/$NAME
gh auth status >/dev/null 2>&1 || { echo "gh is not logged in: gh auth login"; exit 1; }

if gh repo view "$REPO" >/dev/null 2>&1; then
  echo "$REPO exists"
else
  gh repo create "$REPO" --public --description "Questions, answers and proposals about The Chip That Says No, kept apart from the product repositories" >/dev/null
  echo "$REPO created"
fi
gh api -X PATCH "repos/$REPO" -F has_discussions=true -F has_issues=false -F has_wiki=false -F has_projects=false >/dev/null
echo "Discussions on; issues, wiki and projects off (the product repositories hold those)"

# the starter files: clone, copy, commit only if something changed, push
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
git clone -q "https://github.com/$REPO.git" "$tmp/r" 2>/dev/null || { mkdir -p "$tmp/r"; git -C "$tmp/r" init -q -b main; git -C "$tmp/r" remote add origin "https://github.com/$REPO.git"; }
cp "$HERE/discussion/README.md" "$HERE/discussion/CONTRIBUTING.md" "$HERE/discussion/LICENSE" "$tmp/r/"
git -C "$tmp/r" add -A
if git -C "$tmp/r" diff --cached --quiet; then
  echo "starter files already current"
else
  git -C "$tmp/r" -c user.name="Yobie Benjamin" -c user.email="yobie@icloud.com" commit -q -m "The discussion space: what goes here, what stays in the product repositories, CC BY 4.0 for contributions"
  gh auth setup-git >/dev/null 2>&1 || true
  git -C "$tmp/r" push -q -u origin HEAD:main
  echo "starter files pushed"
fi

# the first post, in Announcements, once
rid=$(gh api graphql -f query='query($o:String!,$n:String!){repository(owner:$o,name:$n){id discussionCategories(first:20){nodes{id name}} discussions(first:50){nodes{title}}}}' -F o="$OWNER" -F n="$NAME")
if printf '%s' "$rid" | grep -q '"title":"Start here: what goes where"'; then
  echo "first post already there"
else
  repo_id=$(printf '%s' "$rid" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["repository"]["id"])')
  cat_id=$(printf '%s' "$rid" | python3 -c 'import json,sys; c=json.load(sys.stdin)["data"]["repository"]["discussionCategories"]["nodes"]; print(next((x["id"] for x in c if x["name"]=="Announcements"), c[0]["id"] if c else ""))')
  [ -n "$cat_id" ] || { echo "no discussion categories yet: GitHub creates the defaults a few seconds after Discussions is enabled; rerun"; exit 1; }
  body=$(python3 - <<'PY'
print("""This space is for questions, critiques and proposals from outside the project. Yobie's own work (the design, the code, the proofs, the experiments, the chip) lives in the product repositories:

- https://github.com/YobieBenjamin/safety-governor
- https://github.com/YobieBenjamin/hardware-and-silicon

**Announcements** are Yobie's posts. **Q&A** is for anyone's questions and answers. **Ideas** is for proposals from outside; an idea posted here stays its author's, shared under CC BY 4.0.

Nothing posted here becomes part of the product by being posted. When a discussion changes the design, the change is written in the product repository in Yobie's own words, linking back here.

Good places to start: the open questions in docs/18 (https://github.com/YobieBenjamin/safety-governor/blob/main/docs/18-viability-and-open-questions.md), including who reads the log (WAVE-WHO-READS-THE-LOG), how an affected party contests (WAVE-AFFECTED-PARTY-CONTEST-LANE), an agent that adds roads (EXPERIMENT-ROAD-REACHABILITY) and the wire the customer never meant (EXPERIMENT-CUSTOMER-CONFIRMATION).""")
PY
)
  gh api graphql -f query='mutation($r:ID!,$c:ID!,$t:String!,$b:String!){createDiscussion(input:{repositoryId:$r,categoryId:$c,title:$t,body:$b}){discussion{url}}}' \
    -F r="$repo_id" -F c="$cat_id" -f t="Start here: what goes where" -f b="$body" --jq .data.createDiscussion.discussion.url
fi
echo "https://github.com/$REPO/discussions"
