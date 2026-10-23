#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Deterministic checks on an agent's branch before any model is asked about it. No judgment here:
everything is a rule a script can apply, and a failed rule names the file and line.

    verify_pr.py --repo DIR --branch exp/l4 --base main --spec experiments.json --id L4 [--accept CMD] [--json]

Checks (each a finding with a severity; "block" findings stop a merge, "warn" findings go to the reviewer):
  block  an existing test file was deleted
  block  an existing test file lost assertions, or gained skip/xfail markers
  block  a new skip/xfail marker anywhere under tests
  block  the CI workflow or the acceptance command's test file was removed
  block  a file outside the issue's owned paths changed (EXPERIMENTS.md, HYPOTHESES.md, LEDGER.md and patches/ are always allowed)
  block  the full existing test suite fails on the branch (regression), run in a clean worktree
  block  the acceptance command fails in a clean worktree (not the agent's own, which may hold untracked files)
  block  an em dash in any added line
  warn   placeholder markers in added code: TODO, FIXME, XXX, NotImplementedError, "pass  # ", "stub", "placeholder"
  warn   a result line added to EXPERIMENTS.md, HYPOTHESES.md or LEDGER.md names a path that does not exist on the branch
  warn   a number added to a document (docs/, *.md) that appears in no added code, test, data or result file of the branch
  info   lines added and removed, files touched, commits, agent trailers present

Exit status: 0 when nothing blocks, 1 when something does, 2 on a usage error.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ALWAYS_OWNED = ["EXPERIMENTS.md", "HYPOTHESES.md", "LEDGER.md", "patches/**", "results/**"]
PLACEHOLDER = re.compile(r"\b(TODO|FIXME|XXX|NotImplementedError|stub|placeholder)\b|^\s*pass\s+#", re.I)
NUMBER = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?:\s*(?:%|percent|ms|us|µs|µ|s|MB|GB|mm|cycles))?(?![\w.])")


def git(repo: str, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def owned(path: str, globs: list[str]) -> bool:
    for g in globs + ALWAYS_OWNED:
        if fnmatch.fnmatch(path, g) or (g.endswith("/**") and path.startswith(g[:-3] + "/")):
            return True
    return False


def count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, re.M))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True); ap.add_argument("--branch", required=True); ap.add_argument("--base", default="main")
    ap.add_argument("--spec", required=True); ap.add_argument("--id", required=True); ap.add_argument("--accept", default="")
    ap.add_argument("--suite", default="", help="the repository's full test command for the regression check (default by repository)")
    ap.add_argument("--json", action="store_true"); ap.add_argument("--no-run", action="store_true", help="skip the two test runs")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    issue = next((i for i in spec["issues"] if i["id"] == a.id), None)
    if issue is None:
        print(f"no issue {a.id} in {a.spec}", file=sys.stderr); return 2
    globs = issue.get("owns", [])
    accept = a.accept or issue.get("accept", "")
    repo_name = os.path.basename(os.path.abspath(a.repo))
    suite = a.suite or {"safety-governor": "python3 -m pytest -x tests", "safety": "python3 -m pytest -x observer/tests"}.get(repo_name, "")
    findings: list[dict] = []

    def add(sev: str, what: str, where: str = "") -> None:
        findings.append({"severity": sev, "finding": what, "where": where})

    base, head = git(a.repo, "rev-parse", a.base).strip(), git(a.repo, "rev-parse", a.branch).strip()
    merge_base = git(a.repo, "merge-base", base, head).strip()
    names = [l for l in git(a.repo, "diff", "--name-status", f"{merge_base}..{head}").splitlines() if l.strip()]
    changed = [(l.split("\t")[0][0], l.split("\t")[-1]) for l in names]
    diff = git(a.repo, "diff", "--unified=0", f"{merge_base}..{head}")
    commits = git(a.repo, "log", "--format=%H%x00%s%x00%b%x01", f"{merge_base}..{head}")
    n_commits = commits.count("\x01")
    trailers = commits.count("Agent: wave")

    # 1. tests kept whole
    for status, path in changed:
        is_test = path.startswith("tests/") or "/tests/" in path or os.path.basename(path).startswith("test_")
        if status == "D" and is_test:
            add("block", "an existing test file was deleted", path)
        if status == "M" and is_test:
            before = git(a.repo, "show", f"{merge_base}:{path}", check=False)
            after = git(a.repo, "show", f"{head}:{path}", check=False)
            if count(r"^\s*assert\b|\bassert\w*\(", after) < count(r"^\s*assert\b|\bassert\w*\(", before):
                add("block", "an existing test file lost assertions", path)
            if count(r"pytest\.mark\.(skip|xfail)|pytest\.skip\(|@skip", after) > count(r"pytest\.mark\.(skip|xfail)|pytest\.skip\(|@skip", before):
                add("block", "an existing test file gained skip or xfail markers", path)
        if status == "A" and is_test:
            after = git(a.repo, "show", f"{head}:{path}", check=False)
            if re.search(r"pytest\.mark\.(skip|xfail)|pytest\.skip\(", after):
                add("block", "a new test file carries skip or xfail markers", path)
        if status == "D" and (path.startswith(".github/workflows/") or (accept and path in accept)):
            add("block", "the CI workflow or the acceptance command's own file was removed", path)
        if path.startswith(".github/workflows/") and status == "M" and not any(g.startswith(".github") for g in globs):
            add("block", "the CI workflow was changed by an issue that does not own it", path)

    # 2. scope
    for status, path in changed:
        if not owned(path, globs):
            add("block", "a file outside the issue's owned paths changed", path)

    # 3. the text of the change
    added_lines: list[tuple[str, int, str]] = []
    cur, lineno = "", 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line); lineno = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            added_lines.append((cur, lineno, line[1:])); lineno += 1
        elif not line.startswith("-"):
            lineno += 1
    removed = sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))
    for path, ln, text in added_lines:
        if "\u2014" in text:   # an em dash
            add("block", "an em dash in an added line", f"{path}:{ln}")
        if (path.endswith((".py", ".sh", ".v", ".sv", ".c", ".h")) or "/tests/" in path) and PLACEHOLDER.search(text):
            add("warn", "a placeholder marker in added code", f"{path}:{ln}: {text.strip()[:80]}")
        if os.path.basename(path) in ("EXPERIMENTS.md", "HYPOTHESES.md", "LEDGER.md"):
            for ref in re.findall(r"`([\w./-]+\.[\w]+)`", text):
                if "/" in ref and subprocess.run(["git", "-C", a.repo, "cat-file", "-e", f"{head}:{ref}"], capture_output=True).returncode != 0:
                    add("warn", "a result line names a path that does not exist on the branch", f"{path}:{ln}: {ref}")
    # numbers in documents must have a home in code, tests, data or results of the same branch
    doc_numbers = [(p, ln, n) for p, ln, t in added_lines if p.endswith(".md") and p.startswith("docs/") for n in NUMBER.findall(t) if "." in n or len(n) >= 2]
    if doc_numbers:
        evidence = "\n".join(t for p, _, t in added_lines if not (p.endswith(".md") and p.startswith("docs/")))
        for p, ln, n in doc_numbers:
            if n not in evidence and not re.fullmatch(r"(19|20)\d\d|0\d", n):
                add("warn", "a number added to a document appears in no added code, test, data or result of this branch", f"{p}:{ln}: {n}")

    # 4. the two runs, in a clean worktree of the branch
    ran = {}
    if not a.no_run:
        wt = tempfile.mkdtemp(prefix="verify-")
        try:
            git(a.repo, "worktree", "add", "-q", "--detach", wt, head)
            if git(a.repo, "config", "--get", "core.sparseCheckout", check=False).strip() == "true":
                cone = git(a.repo, "sparse-checkout", "list", check=False).split()
                subprocess.run(["git", "-C", wt, "sparse-checkout", "set", "--cone", *cone], capture_output=True)
                subprocess.run(["git", "-C", wt, "reset", "-q", "--hard"], capture_output=True)
            for label, cmd in (("suite", suite), ("acceptance", accept)):
                if not cmd:
                    continue
                r = subprocess.run(["bash", "-c", cmd], cwd=wt, capture_output=True, text=True, timeout=3600)
                ran[label] = {"command": cmd, "exit": r.returncode, "tail": (r.stdout + r.stderr)[-1500:]}
                if r.returncode != 0:
                    add("block", f"the {label} command fails in a clean checkout of the branch (exit {r.returncode})", cmd)
        finally:
            subprocess.run(["git", "-C", a.repo, "worktree", "remove", "--force", wt], capture_output=True)
            shutil.rmtree(wt, ignore_errors=True)

    blocks = [f for f in findings if f["severity"] == "block"]
    out = {"id": a.id, "branch": a.branch, "base": a.base, "head": head[:7], "commits": n_commits, "agent_trailers": trailers,
           "files": len(changed), "added": len(added_lines), "removed": removed, "ok": not blocks, "findings": findings, "runs": ran}
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        print(f"{a.id} {a.branch} ({head[:7]}): {len(changed)} files, +{len(added_lines)} -{removed}, {n_commits} commits ({trailers} with agent trailers)")
        for f in findings:
            print(f"  [{f['severity']}] {f['finding']}: {f['where']}")
        for label, r in ran.items():
            print(f"  {label}: exit {r['exit']} ({r['command']})")
        print("  verdict:", "nothing blocks" if not blocks else f"{len(blocks)} blocking finding(s)")
    return 0 if not blocks else 1


if __name__ == "__main__":
    sys.exit(main())
