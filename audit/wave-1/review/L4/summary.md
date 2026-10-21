**Revision 2** (2026-10-21 02:52) on the local model qwen3.8-27b-64k:latest: 77 turns, estimated $0.0, acceptance `python3 -m pytest -q tests/test_h19_conformance.py`: **pass**. The gate reviews the branch again.

Agent summary:



## Commit messages
- Revision 2: work left uncommitted by the agent, committed by the launcher (#4)
Agent: wave 1, issue #4 (revision 2, launcher commit)

- govsim/trace.py, proofs/replay.py, tests/test_h19_conformance.py: heartbeat as a first-class event; arm/burn gap tests (#4)
Revision 1. The heartbeat is now a first-class event (heartbeat_back /
heartbeat_lost) that drives the machine's heartbeat state, so the issue and
execute guards read m.heartbeat -- a state the events set -- instead of a flag
carried on the guarded event (the circularity finding). The endpoint's own
expiry is recorded as a heartbeat_lost observed at the endpoint. Report.burned
tracks the burn-without-execute gap (the endpoint burns the ticket before the
commit and device checks and may refuse; the core machine has no such step),
isolated by a test; the boot/arm gap is isolated the same way. The "one for
one" claim is softened to a concrete re-encoding: step_names cross-checks the
step names, but the guard logic is not compared symbolically (z3 is absent).
The fault-injection assertion is widened to check the faulted set is exactly
FAULT_INJECTION and that each refusal names its event and reason. EXPERIMENTS.md
records the findings.

Co-Authored-By: Claude Code <noreply@anthropic.com>
Agent: wave 1, issue #4 (revision 1)

- govsim/trace.py, proofs/replay.py: boot, ticket owner, injected-fault test; EXPERIMENTS.md L4 findings (#4)
Agent: wave 1, issue #4

- govsim/trace.py, proofs/replay.py, tests/test_h19_conformance.py: replay every trace through the abstract machines (#4)
Agent: wave 1, issue #4

