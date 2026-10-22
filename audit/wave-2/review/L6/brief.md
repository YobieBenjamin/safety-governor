# L6 · Mutation testing as a standing gate: every check-removing mutant of the governor model must be killed by some test

**Goal.** Automate what the second audit did by hand (twenty surviving mutants found and fixed). Add a `make mutants` target (mutmut or a small custom mutator over `govsim/governor.py`, `policy.py`, `endpoints.py`, `fabric.py`) that removes one check, flips one comparison or skips one log write at a time and runs the suite; report survivors.

**Acceptance.** Zero surviving mutants that remove a check; the report is committed under `results/mutants.md`; CI runs it weekly.

**Budget.** Mechanical; suited to the local orchestrator. A cloud agent only to set up the mutator, about 60k tokens.

**Acceptance command (the launcher runs it after the agent).** `python3 -m pytest -q tests/test_mutants.py`

## Rules for this run
- You are in a git worktree on branch `exp/l6`; it is the only place you write. Run commands from this directory with relative paths; do not cd elsewhere.
- The other repositories of the program are readable at: /Users/yb/safety /Users/yb/hardware-and-silicon. Never edit them: a change they need goes into `patches/<repo>/<file>.patch` here, with a note in your final summary.
- Acceptance: `python3 -m pytest -q tests/test_mutants.py`. Run it at most three times. Stop when it passes, or after the third failure; then record exactly what fails in EXPERIMENTS.md (safety-governor) or in the hypothesis's section (safety), with the failing output.
- Read only the files the brief names under Read first and the files you create. Do not read whole directories, do not run the full test suite (the acceptance command is enough), do not search the web, do not start sub-agents.
- Never weaken, skip or delete an existing test. Do not refactor beyond the brief. No em dashes in anything you write.
- Commit as you go with messages that name the issue (#6) and end with the line: Agent: wave 2, issue #6. Do not push, do not open a pull request; the launcher does both.
- This run is capped at 40 turns and an estimated spend of $10. Keep the tree in a working, committed state at all times, so a cap mid-way still leaves usable work.
- Finish with a summary of at most fifteen lines: what was built, what passes, what does not and why, open questions. It is posted on the issue as is.
