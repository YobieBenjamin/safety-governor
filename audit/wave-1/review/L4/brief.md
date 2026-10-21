# L4 · Trace conformance: replay every govsim trace through the abstract machines and fail on the first step they refuse

**Goal.** Make the link between the theorem and the simulation mechanical. Add `govsim/trace.py`: a trace sink that records every governor transition (ticket issued with its action hash and edition; endpoint execute; refused execute with reason; edition change; halt; clear; heartbeat lost and back) as a list of typed events. Add `proofs/replay.py`: a replayer that drives the abstract machine of `proofs/core_invariants.py` (and `commit_point.py` where holds occur) with the trace and raises on the first event the machine has no enabled transition for. Add `tests/test_h19_conformance.py` that runs every existing hypothesis test's rack with the sink on and replays its trace.

**Read first.** `govsim/governor.py` (`command`, `_cmd_request`, `_release_gate`, `_on_loop_*`), `govsim/log.py` (the events already logged), `govsim/harness.py`, the two proof files.

**Acceptance.** `python3 -m pytest -q tests/test_h19_conformance.py` passes against all 200 tests' traces; a deliberately broken governor (one check commented out, in a fixture) fails replay with the event named.

**Disproof.** The simulation takes a step the theorem's machine does not have. That is either a model bug or a gap in the theorem; report which.

**Budget.** One cloud agent, about 150k tokens. Do not refactor the governor; add the sink beside the existing log.

**Acceptance command (the launcher runs it after the agent).** `python3 -m pytest -q tests/test_h19_conformance.py`

## Rules for this run
- You are in a git worktree on branch `exp/l4`; it is the only place you write. Run commands from this directory with relative paths; do not cd elsewhere.
- The other repositories of the program are readable at: /Users/yb/safety /Users/yb/hardware-and-silicon. Never edit them: a change they need goes into `patches/<repo>/<file>.patch` here, with a note in your final summary.
- Acceptance: `python3 -m pytest -q tests/test_h19_conformance.py`. Run it at most three times. Stop when it passes, or after the third failure; then record exactly what fails in EXPERIMENTS.md (safety-governor) or in the hypothesis's section (safety), with the failing output.
- Read only the files the brief names under Read first and the files you create. Do not read whole directories, do not run the full test suite (the acceptance command is enough), do not search the web, do not start sub-agents.
- Never weaken, skip or delete an existing test. Do not refactor beyond the brief. No em dashes in anything you write.
- Commit as you go with messages that name the issue (#4) and end with the line: Agent: wave 1, issue #4. Do not push, do not open a pull request; the launcher does both.
- This run is capped at 40 turns and an estimated spend of $10. Keep the tree in a working, committed state at all times, so a cap mid-way still leaves usable work.
- Finish with a summary of at most fifteen lines: what was built, what passes, what does not and why, open questions. It is posted on the issue as is.
