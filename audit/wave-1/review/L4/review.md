## Review of `exp/l4`: **revise**

Verifier: 1 blocking finding(s); model review on ?: 1 blocking, 10 warnings, 3 unsupported claim(s) of 12; estimated $0.76, 11 turns.

### Reviewer's summary

The acceptance command passes and tests what the brief says: 200 traced tests plus two broken-governor fixtures that fail replay with the event named.
Block: tests/h19_plugin.py is outside the owned paths (verify.json); the brief owns only trace.py, replay.py and the test file. Either get it approved or move the plugin into the test file.
The brief asks for heartbeat lost/back events. No such events are recorded; heartbeat is read off flags on issue and execute, so heartbeat lost/back are not driven and the Z3 steps beat_lost/beat_back are not exercised.
The commit_point replay is almost a stub: hold_released does reviewer_clears and commit in one step with version never changing, so only a double commit or a missing hold can fail it. The ordering hack in trace.py (hold_released inserted before the ticket) is what lets it pass.
Documents say refusals are "stutter steps ... sound" and that the guards are copied "one for one" from the Z3 steps. Replay allows any refusal, which is looser than forged_execute's guard. I found no test that checks the guard copy, and z3 is not run.
Questions: should "no model bug found" stand when the replayer was widened (arm, burned) to accept what the simulation does? Is a name-keyed fault-injection allowlist acceptable?

### Verifier findings

- [block] a file outside the issue's owned paths changed: `tests/h19_plugin.py`
- [warn] a placeholder marker in added code: `govsim/trace.py:219: pass          # the edition change itself is recorded by the _accept_policy wrap`

### Reviewer findings

- [block] scope at `tests/h19_plugin.py:1`: New file outside the paths the brief assigns (govsim/trace.py, proofs/replay.py, tests/test_h19_conformance.py); verify.json flags it. It is the mechanism that reruns all 200 tests, so the acceptance depends on a file the brief did not own. Needs explicit approval or a move into the test file.
- [warn] test_integrity at `tests/h19_plugin.py:24`: FAULT_INJECTION exempts test_governor_cannot_clear_itself by test name, and for that test replay is expected to fail. The test is not skipped, but its pass now depends on a name-keyed allowlist. A reviewer should confirm that this is the only test whose trace the machine must refuse.
- [warn] correctness at `proofs/replay.py:153`: Brief requires 'heartbeat lost and back' events. None are emitted by govsim/trace.py. _observe_hb sets m.heartbeat from the flag carried on the issue or execute event itself, so there is no stateful heartbeat in the machine and the beat_lost/beat_back steps are only counted when the flag differs between observations. Observers are also mixed (governor at issue, endpoint at execute) into one machine variable.
- [warn] correctness at `proofs/replay.py:99`: CommitPoint replay cannot fail meaningfully: hold_released performs reviewer_clears and commit back to back (line ~265 of the feed), version[a] is never changed, so the 'cleared for this version' guard always holds. 'commit_point.py where holds occur' is covered in name only; the reparameterise/regulator steps are absent and not reported as unmodelled in EXPERIMENTS.md.
- [warn] correctness at `govsim/trace.py:206`: hold_released is inserted into the event list before the already recorded ticket_issued and the events are renumbered. The trace is then not in the order the transitions happened, contradicting the module docstring ('in the order the transitions happened'), and the fallback appends it at the end if no ticket is found. The reordering is what lets the commit-point guard pass.
- [warn] correctness at `proofs/replay.py:249`: _refuse accepts any refusal whatever the state (core forged_execute is only enabled when ticket != epoch, used, or no heartbeat; core_invariants.py:126). Only replay, stale and heartbeat reasons are cross-checked. EXPERIMENTS.md calls this 'sound' without a test. Report.stutters (line 134) is declared and never used. _refuse_unknown (line 262) accepts every ownerless refusal with no check.
- [warn] correctness at `proofs/replay.py:85`: check_invariants checks P1 to P4 on state the replayer builds itself (okay_at_issue is set only in _issue, which already requires the guards), so P1 to P3 cannot fail independently. P6 and P7 of core_invariants.py are not checked. The summary and the docstring say the invariants are 'checked after every step' without saying this.
- [warn] unsupported_claim at `EXPERIMENTS.md:16`: 'No model bug found' (summary) and the two 'gap in the theorem' findings rest on a replayer that was widened to accept what govsim does (arm step, burned set). That is a defensible finding, but the claim 'counted in Report.arms' has no test asserting it: no test asserts arms > 0 or inspects h19_plugin RESULTS.
- [warn] style at `govsim/trace.py:219`: Dead branch: 'policy.committed: pass' is flagged by verify.json as a placeholder marker. Remove it or record the event.
- [warn] test_integrity at `tests/test_h19_conformance.py:24`: The 200-test check runs the tests in a subprocess and requires only len(results) >= 200 and that six step names occur at least once across all traces. It does not require hold, heartbeat or arm to occur, and does not check that the 200 tests produce non-empty traces. The brief's acceptance 'against all 200 tests' traces' is met in count only.
- [warn] test_integrity at `tests/test_h19_conformance.py:55`: The brief says a broken governor with one check commented out, in a fixture. The fixtures monkeypatch instead: test 1 forces self.state to RUN around Governor.command, test 2 removes two checks at once (endpoint epoch and commit_from_endpoint). They show replay catches those faults, not the removal of a single named check from governor.py.

### Claims

- supported (summary): The acceptance command passes (5 tests) and traces all 200 hypothesis tests (evidence: verify.json acceptance exit 0; test_every_hypothesis_test_trace_replays asserts len(results) >= 200; suite 205 passed)
- supported (code): The sink does not change the governor; it wraps methods at class level and restores them on stop (evidence: govsim/trace.py start()/stop() wrap and restore; diff touches no governor file. Note: it wraps behaviour at runtime, which is the 'beside the log' approach the brief allows)
- supported (summary): The trace records heartbeat lost and back (brief) / heartbeat is observed rather than driven by events (evidence: Summary admits it is observed. No heartbeat event kind exists in trace.py's event list)
- NOT SUPPORTED (document): Z3 guards are copied one for one into the concrete machines, and a test checks the step names against the proof files (evidence: Names are checked by test_step_names_match_the_proof_files (names only). The guard copy was not shown by a test; z3 not run. _refuse is looser than forged_execute)
- NOT SUPPORTED (summary): P1 to P4 are checked after every step (evidence: check_invariants runs after each feed (replay.py:85), but on replayer-built state; P1-P3 cannot fail independently)
- supported (document): Two broken-governor fixtures fail replay with the event named (evidence: tests in test_h19_conformance.py assert 'ticket_issued'/'halted' and 'execute_ok' in the NoTransition message)
- supported (document): Theorem gap: a power cycle is not a step; govsim reaches RUN with no clear, accepted as an explicit arm step (evidence: replay.py arm branch in feed(); core_invariants leaves halted free at init. Arm count is not asserted by a test)
- NOT SUPPORTED (document): Theorem gap: an endpoint burns a ticket and may then refuse; machine has no burn-without-execute step (evidence: Core.burned and _refuse in replay.py; the machine has no such step in core_invariants.py. No test shows a trace that needs it)
- NOT SUPPORTED (document): Refusals for expiry, wrong endpoint, parameter mismatch and bad signature are stutter steps of forged execute; the machine is looser than the system, which is sound (evidence: _refuse allows these without checking; 'sound' is asserted, with no test or proof)
- supported (document): test_governor_cannot_clear_itself injects a firmware fault; replay refuses it as it must (evidence: FAULT_INJECTION in tests/h19_plugin.py asserts NoTransition naming run_entered and 'RUN entered with no clear')
- NOT SUPPORTED (summary): No model bug found (evidence: All 200 traces replay after the replayer was extended with arm and burned handling; that absence is only as strong as the replayer's guards (see findings))
- supported (document): Not modelled: allows/witness, heartbeat events, quorum (evidence: Stated in EXPERIMENTS.md and consistent with the code; commit_point's version/reparameterise steps are not listed)

### suite in a clean checkout: exit 0

```
........................................................................ [ 35%]
........................................................................ [ 70%]
.............................................................            [100%]
205 passed in 6.05s

```

### acceptance in a clean checkout: exit 0

```
.....                                                                    [100%]

```
