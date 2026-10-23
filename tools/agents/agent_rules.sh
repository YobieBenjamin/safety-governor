#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
# Sourced by run_wave.sh and revise_pr.sh: the tool rules every build agent runs under.
# What an agent may run without asking, and what it may never run. Everything else is denied and
# the agent is told not to retry it (no prompt can be answered in an unattended run).
#
# The CLI matches a rule against each simple command in a line, so a pipe or an && chain passes only
# when every piece is listed, and a command with an environment prefix (PYTHONPATH=x python3 ...)
# matches nothing. Wave 2's local run lost four turns to exactly that; the text tools it reached for
# are listed now, and SHELL_RULE below tells the agent how to write a command that passes.
ALLOW=( "Read" "Edit" "Write" "Glob" "Grep"
  "Bash(python3 *)" "Bash(python *)" "Bash(pytest *)" "Bash(make *)" "Bash(pip *)" "Bash(pip3 *)"
  "Bash(git add *)" "Bash(git commit *)" "Bash(git status *)" "Bash(git diff *)" "Bash(git log *)" "Bash(git show *)" "Bash(git rev-parse *)" "Bash(git ls-files *)"
  "Bash(ls *)" "Bash(cat *)" "Bash(head *)" "Bash(tail *)" "Bash(wc *)" "Bash(grep *)" "Bash(find *)" "Bash(diff *)"
  "Bash(sed *)" "Bash(awk *)" "Bash(sort *)" "Bash(uniq *)" "Bash(tr *)" "Bash(cut *)" "Bash(xargs *)" "Bash(printf *)" "Bash(date *)" "Bash(which *)" "Bash(basename *)" "Bash(dirname *)" "Bash(true)"
  "Bash(mkdir *)" "Bash(cp *)" "Bash(mv *)" "Bash(touch *)" "Bash(echo *)" "Bash(shasum *)" "Bash(sha256sum *)" )
DENY=( "WebFetch" "WebSearch" "Agent"
  "Bash(git push *)" "Bash(git checkout *)" "Bash(git switch *)" "Bash(git reset *)" "Bash(git rebase *)" "Bash(git stash *)" "Bash(git worktree *)"
  "Bash(rm -rf *)" "Bash(sudo *)" )
# One line for the brief: how to write a shell command that the rules let through.
SHELL_RULE="Shell commands run without anyone to approve them: a command passes only when every program in it is one of python3, python, pytest, make, pip, git (add, commit, status, diff, log, show, rev-parse, ls-files), ls, cat, head, tail, wc, grep, find, diff, sed, awk, sort, uniq, tr, cut, xargs, printf, mkdir, cp, mv, touch, echo, shasum. Write plain commands: no environment-variable prefix (put a path on sys.path inside the script instead), no sudo, no network, nothing outside this directory. A denied command is denied for good; do not retry it, rewrite it."
