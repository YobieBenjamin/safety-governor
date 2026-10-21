#!/usr/bin/env bash
# Sourced by run_wave.sh and revise_pr.sh: the tool rules every build agent runs under.
# What an agent may run without asking, and what it may never run. Everything else is denied and
# the agent is told not to retry it (no prompt can be answered in an unattended run).
ALLOW=( "Read" "Edit" "Write" "Glob" "Grep"
  "Bash(python3 *)" "Bash(python *)" "Bash(pytest *)" "Bash(make *)" "Bash(pip *)" "Bash(pip3 *)"
  "Bash(git add *)" "Bash(git commit *)" "Bash(git status *)" "Bash(git diff *)" "Bash(git log *)" "Bash(git show *)" "Bash(git rev-parse *)" "Bash(git ls-files *)"
  "Bash(ls *)" "Bash(cat *)" "Bash(head *)" "Bash(tail *)" "Bash(wc *)" "Bash(grep *)" "Bash(find *)" "Bash(diff *)"
  "Bash(mkdir *)" "Bash(cp *)" "Bash(mv *)" "Bash(touch *)" "Bash(echo *)" "Bash(shasum *)" "Bash(sha256sum *)" )
DENY=( "WebFetch" "WebSearch" "Agent"
  "Bash(git push *)" "Bash(git checkout *)" "Bash(git switch *)" "Bash(git reset *)" "Bash(git rebase *)" "Bash(git stash *)" "Bash(git worktree *)"
  "Bash(rm -rf *)" "Bash(sudo *)" )

