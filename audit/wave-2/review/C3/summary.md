**Revision 2** (2026-10-22 13:36) on sonnet: 11 turns, estimated $0.5365, acceptance `make bench && python3 -m pytest -q tests/test_hybrid_signature.py`: **pass**. The gate reviews the branch again.

Agent summary:

Revision 2 is committed as 2f7579a and not pushed. `make bench` and the 8 tests in `tests/test_hybrid_signature.py` pass. I ran the acceptance command twice, and the first run's output was only read from its background file. I ran no other test suite.

**What changed**
- **Unsourced figure (block).** I can't reach the web, so the 10M-cycle ML-DSA-65 figure is still unsourced. The model still carries it, flagged as an unverified placeholder (`govsim/bench.py:41-48`). I cut every derived number from `docs/04-specification.md:245` (117 ms, 234, 47, 367, ~13 percent slack) along with the spec threshold. The row now says the constant is not a spec figure, and its threshold cell reads "to be set after the cycle count is sourced or measured".
- **Hardcoded verdict.** The verdict is now computed from the run in the new `hybrid_report()` (`govsim/bench.py`). It prints "cannot keep up", "keeps up", "did not hold" or "HOLDS: a second engine is needed" from the utilisation values, and adds the caveat only while `MLDSA65_COST_SOURCED` is False.
- **Engine scope claim.** I removed the claim that verification and session setup are off the engine, because nothing shows it. The bench line and the docs row now say only that signing is counted and other uses of the engine are not modelled.
- **Duplicate test.** `test_a_window_under_one_second_exists_by_search` now scans windows from 10 ms to 990 ms. It asserts that one works, that the shortest sits just above the combined sign time, and that 250 ms is among them.
- **Slack and latency.** The 2x slack is now computed from the formula, and a new test pins utilisation and latency to sign time over window, which are the figures `make bench` prints. The 8x test now also checks record latency, which exceeds 1 s there. I removed the false "recorded in docs/04" comment, since the numbers no longer live in the docs.
- **Flag-pinning test.** I replaced the test that asserted `MLDSA65_COST_SOURCED is False` with `test_verdict_text_is_computed_and_carries_the_caveat`. It checks the printed text, and that a 1.5 s signature flips the verdict.

**Not changed**
- The 250 ms window is still a modelling choice with no latency target behind it. At 2x ML-DSA cost it leaves little slack, which the test records. Widening it is a spec decision.
- I did not add a committed artifact for the bench numbers. With the figures out of the docs, `make bench` and the tests are the record.

**Still open:** someone with web access needs to check the pqm4 ML-DSA-65 sign cycle count and the Cortex-M4 to OTBN scaling. After that, set `MLDSA65_COST_SOURCED = True` and restore the spec row.

## Commit messages
- C3 (#10) revision 2: cut the unsourced figures from the spec row; compute the bench verdict; search windows in the test; computed slack and latency checks
Agent: wave 2, issue #10 (revision 2)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

- C3 (#10) revision 1: mark the ML-DSA-65 figure an unverified placeholder; make the disproof verdict conditional
- bench.py: label MLDSA65_SIGN_CYCLES an UNVERIFIED placeholder (MLDSA65_COST_SOURCED=False) with the
  re-check pointer; drop the unsourced "neutral to slightly pessimistic / no Keccak" scaling rationale and
  state 1.0x as an unverified assumption; point "OTBN has no ML-DSA" at the in-repo docs.
- bench main(): the hybrid line now flags the placeholder, notes signing-only scope (tickets are a firmware
  path; verification and session setup are not on the engine), and states "disproof did not hold" conditional.
- tests: fix the 1.0 s window to the modelled 0.25 s window (genuinely under 1 s); widen the tautological
  both-signatures test to check run() charges both; record the tight 2x slack, the 8x headroom on the 1 s
  boundary, and a test that the result is conditional on the unsourced figure.
- docs/04 §9: record the 250 ms / 47% / 367 ms result durably, the placeholder, the scaling assumption, the
  2x tail caveat, and the signing-only scope.

Co-Authored-By: Claude Code <noreply@anthropic.com>

Agent: wave 2, issue #10 (revision 1)

- C3 (#10): hybrid P-384 + ML-DSA-65 signature cost in the batching model; bench reports hybrid engine utilisation; tests
Agent: wave 2, issue #10

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

