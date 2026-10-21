**Claims (summary + commit messages)**

1. "I fixed the wrong numbers" — `The two gates agree on 17 of 20 replayed catalogue entries (the other 67 of 87 are listed in `NOT_COMPARED` with reasons)`
2. "I fixed the unsupported wording" — `G3, G4 and G5 look ambiguous on my reading of the policy docstrings only; no test shows it, so treat that as a hypothesis for the design owner, not a settled finding.`
3. "I did not widen the test" — NOT FOUND
4. "the blocking finding about filing the disagreements as issues is still open" — `they were not filed as separate GitHub issues from this run (no `gh` access in the sandbox), so that step remains for the launcher or YB.` / `## Not filed as GitHub issues`
5. "The acceptance command passed once more with 31 tests" — `2026-10-20 (issue #16, wave 1): the acceptance command was run once more through pytest and passes (31 tests).`
6. "(one of three runs)" — `the acceptance command was run twice with a failure each (...), plus one filtered run; after that the test functions were called directly once`
7. "The fixes are in commit 3dbe3d3" — NOT FOUND (hash appears nowhere in the diff or commit messages)
8. "nothing is pushed" — `The agent run does not push and has no network authority in this brief`
9. "EXPERIMENTS.md now says 17 of 20 replayed entries agree" — `The two gates agree on 17 of 20 replayed catalogue entries`
10. "with the other 67 of 87 listed in NOT_COMPARED" — `(the other 67 of 87 are listed in `NOT_COMPARED` with reasons)`
11. "Its test counts are corrected to 31" — `the file now has 31 tests`
12. "the earlier 30 noted as the count at that time" — `(30 passed then; the file now has 31 tests)`
13. "results/l5-disagreements.md:7 now says 20 replayed and 67 listed" — `Brief versus repository: ... All 87 are classified: 20 replayed in both gates, 67 listed with the reason they are not gate decisions in govsim.` (line 7 of the new file)
14. "G3 to G5: both documents call the ambiguity a hypothesis from the docstrings only, not a settled finding" — EXPERIMENTS.md `G3, G4 and G5 look ambiguous on my reading of the policy docstrings only ... not a settled finding.`; l5-disagreements.md G3 `looks AMBIGUOUS on the docstrings alone, a hypothesis about the design, not settled.`, G4 `AMBIGUOUS.`, G5 `AMBIGUOUS but low severity`
15. "stale comment no longer claims filed under results/issues/" — NOT FOUND as a removal (file is new in this diff); current state: `# Each is written up in results/l5-disagreements.md; filing them as GitHub issues is still open.`
16. "It points to results/l5-disagreements.md and says filing is still open" — `# Each is written up in results/l5-disagreements.md; filing them as GitHub issues is still open.`
17. "Filing G1 to G5 as separate issues remains for the launcher or YB (gh denied)" — `so that step remains for the launcher or YB` / `so these are written here for the launcher or a person to file, one issue each (G1 to G5).`
18. "the 67 excluded entries are not gate decisions in govsim, so each would need a new comparison harness" — `NOT_A_GATE_DECISION = "not a gate decision in govsim"` (the "needs a new harness" half is the agent's reasoning, NOT FOUND as a diff line)
19. "Reason-code table still maps several distinct codes to one class (attestation.*, min/max), only the first reason compared" — `"attestation.missing": "not_attested", "attestation.signature": "not_attested", "attestation.type": "not_attested",` / `"attestation.expired": "not_attested", "attestation.measurement_mismatch": "not_attested",`; `HW_KINDS = {"max": "range", "min": "range", ...}`; `return Outcome("hold" if res.decision.value == "hold" else "deny", hw_class(res.reasons[0]))`
20. "the random-request sweep still accepts any disagreement that matches a GAPS signature" — `assert hw == gov or gap_of(scn, hw, gov), f"reference {hw} vs govsim {gov} for {scn}"`
21. "TX.concurrent_overspend: NOT_COMPARED reason says govsim's H13 covers it; did not check tests/test_h13_shared_budget.py" — H13 reference: `"TX.concurrent_overspend": "concurrency; the sequential form is TX.budget_exhausted (govsim's own H13 covers the concurrent form)",`; the "did not check test_h13" half NOT FOUND (test not in diff)
22. "requirements-differential.txt and the results file left both; not named in brief, judged necessary support" — files present: `+hypothesis>=6` / `+-e ../hardware-and-silicon`; "not named in brief / necessary support" NOT FOUND (brief not in diff)
23. CM1 "correct counts (17 of 20 agree, 31 tests, 67 not compared)" — `17 of 20` / `67 of 87` recorded; `assert (len(REPLAYED), agree, len(gaps)) == (20, 17, 3)` computes 20/17; 31 tests NOT computed (prose only)
24. CM1 "soften G3 to G5 claim" — `G3, G4 and G5 look ambiguous on my reading of the policy docstrings only ... not a settled finding.`
25. CM1 "fix stale comment" — `# Each is written up in results/l5-disagreements.md; filing them as GitHub issues is still open.`
26. CM1 "(#16)" — `2026-10-20 (issue #16, wave 1)`
27. CM2 "Revision 1: work left uncommitted by the agent, committed by the launcher (#16)" — NOT FOUND (describes a separate commit, not this diff)
28. CM3 "L5 acceptance run passes under pytest" — `the acceptance command was run once more through pytest and passes (31 tests)`
29. CM3 "disagreement issues still to be filed" — `they were not filed as separate GitHub issues from this run ... so that step remains for the launcher or YB.`
30. CM4 "correct the agreement count (#5)" — `The two gates agree on 17 of 20 replayed catalogue entries`
31. CM5 "reference gate against govsim on the catalogue and a random sweep" — `from hardware_ref.attacks import CATALOGUE` / `def test_random_typed_requests_agree(scn):`
32. CM5 "five disagreements pinned and written up" — `GAP_CASES = {` (5 keys, G1–G5) / `def test_pinned_disagreement(gap):` / `results/l5-disagreements.md`
33. CM5 "(#5)" — `## L5 / H21: ... (issue #5)` / `Found by `tests/test_h21_differential.py` (issue #5)`

**Numbers in the changed documents (where computed / recorded / NOT FOUND)**

EXPERIMENTS.md
- 34, 0.1, 7 ("docs/07"), 4 ("phase 4") — recorded, context lines (unchanged, not computed)
- 5 / 21 ("L5 / H21 ... issue #5") — recorded
- 17 — recorded in prose; computed by `assert (len(REPLAYED), agree, len(gaps)) == (20, 17, 3)`
- 20 — recorded in prose; computed (`len(REPLAYED) == 20`)
- 67 — recorded in prose; NOT computed (no test asserts 67; derivable as 87−20)
- 87 — recorded in prose; computed as 75+12 via `== (75, 12)` (87 itself not a literal in a test)
- 30 ("30 passed then") — recorded; NOT computed
- 31 ("the file now has 31 tests", "passes (31 tests)") — recorded; NOT computed (pytest collection, no test asserts 31)
- 2026, 10, 20 (date "2026-10-20"), 16 ("#16"), 1 ("wave 1") — recorded
- gap labels G1–G5 (1,3,4,5) — recorded

results/l5-disagreements.md
- 5 ("issue #5"), header "L5" — recorded
- 66 ("brief says 66 attacks"), 10 ("10 baselines") — recorded; NOT computed (test asserts 75/12, not 66/10)
- 75 — recorded; computed by `== (75, 12)`
- 12 — recorded; computed by `== (75, 12)`
- 87 ("All 87") — recorded; computed as 75+12
- 20 ("20 replayed") — recorded; computed
- 67 ("67 listed") — recorded; NOT computed
- 0, 1000, 0.3, 3, 60, 2000, 1000.01, 50000 (line 4 rulebook summary) — recorded
- G-section inputs: 250 (G1, G4, G5), 999 (G2), 25000 + 654321 (G3 acct-654321), 2 ("two approvals"), 60 ("60 s"), 123456 (G5 acct-123456), 4 ("L4.type_confusion") — recorded
- G1–G5 (1,5) — recorded

tests/requirements-differential.txt
- 6 ("hypothesis>=6") — recorded

tests/test_h21_differential.py
- 0, 1000, 0.3, 3, 60, 2000, 3600, 1000.01, 50000 (NEUTRAL rulebook) — recorded
- 0.1, 0.95 (LOW, HIGH) — recorded
- 250 (Scn default), 123456 (default acct) — recorded
- 1 (token_ttl+1, observer_freshness_s+1, hold_ttl_s+1) — recorded
- 999999 (acct-999999 swap) — recorded
- 4.0 (min(4.0, left)), 3601 (advance), 8 (random_id(8)), 0.0 (witness risk), 30 (expires_at+30), 61 (advance) — recorded
- 25000 (pay(...,approve=True), pay(...,labels=True)), 500000 (pay(500000)), 900 (pay(900,prior=(900,900))) — recorded
- amounts st: 0, 1, 999.99, 1000, 1000.01, 50000, 50000.01, -1, 25000; -10, 60000; acct-1, 1234567; 3 (max_size), 2000 (sum≤2000) — recorded
- 120 (max_examples=120) — recorded
- 20, 17, 3 — computed: `assert (len(REPLAYED), agree, len(gaps)) == (20, 17, 3)`
- 75, 12 — computed: `assert (sum(a.expect == "blocked" ...), sum(a.expect == "allowed" ...)) == (75, 12)`
- 64 ("0" * 64) — recorded
- 5 (GAP_CASES keys / `sorted(GAP_CASES)`) — recorded as a 5-entry dict; NOT asserted as the literal 5
