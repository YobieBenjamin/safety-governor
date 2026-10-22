## Review of `exp/c3`: **revise**

Verifier: clean; model review on ?: 1 blocking, 6 warnings, 2 unsupported claim(s) of 13; estimated $0.22, 5 turns.

### Reviewer's summary

The brief's goal says to cite the ML-DSA-65 figure. The 10,000,000-cycle constant has no checked source: bench.py:41-48 says it is from memory. Its placeholder labelling is honest, and the docs row no longer states derived numbers.
The acceptance (make bench plus 8 tests) passes. It shows the model's arithmetic is consistent, not that the engine keeps up on real hardware.
The "Disproof did not hold" verdict rests on that unsourced constant and on an untested 1.0x M4 to OTBN scaling. It should not be read as a result until the cycle count is sourced or measured.
hybrid_report ignores the run it is given for its signature time and window. test_verdict_text only partly backs the summary's "flips the verdict" claim.
The search test uses a smaller load (gpus=2, requests=20) than the modelled one.
Question for the owner: is an unsourced placeholder acceptable for closing issue #10, or should it stay open until pqm4 is checked?

### Verifier findings

- [warn] a placeholder marker in added code: `govsim/bench.py:41: # UNVERIFIED PLACEHOLDER: the 10,000,000 figure has NO checked source at revisio`
- [warn] a placeholder marker in added code: `govsim/bench.py:48: MLDSA65_SIGN_CYCLES = 10_000_000           # UNVERIFIED placeholder: Cortex-M4 p`
- [warn] a placeholder marker in added code: `govsim/bench.py:105: src = "sourced" if MLDSA65_COST_SOURCED else "UNVERIFIED placeholder, no checked`
- [warn] a placeholder marker in added code: `tests/test_hybrid_signature.py:2: engine. ML-DSA's cycle count on OTBN is an UNVERIFIED placeholder (see govsim/be`

### Reviewer findings

- [block] unsupported_claim at `govsim/bench.py:41`: The brief says 'cite the figure'. MLDSA65_SIGN_CYCLES = 10_000_000 (line 48) is from the agent's memory of the pqm4 tables, with no source (the comment says so). The disproof verdict printed by `make bench` and the margins the tests pin depend on it. The code is honest about this, but the brief's acceptance (a cited figure) is not met and the 'did not hold' result is not established. Source it, or have the issue accept an explicit placeholder.
- [warn] unsupported_claim at `govsim/bench.py:29`: The 1.0x M4 to OTBN scaling is an assumption with no source or test. The brief asks for a stated scaling assumption, which is met. The comment itself says a software SHAKE on OTBN could make 1.0x optimistic, so the direction of the error is unknown and the verdict rests on it.
- [warn] correctness at `govsim/bench.py:106`: hybrid_report(h) prints HYBRID_SIGN_S, HYBRID_BATCH_WINDOW_S and MLDSA65_SIGN_CYCLES from module constants, and computes `holds` from the constant window, not from the run it is given. For a run with a different hybrid_sign_s or hybrid_window_s, the printed batch time and the 'did not hold' wording would not match the run, even though the summary says the verdict is 'computed from the run'. Only the two utilisation values come from h.
- [warn] test_integrity at `tests/test_hybrid_signature.py:79`: The summary says the test 'checks that a 1.5 s signature flips the verdict'. It only asserts that utilisation exceeds 100 for hybrid_sign_s=1.5. It never calls hybrid_report on that run, so the flip to 'HOLDS: a second engine is needed' is not tested. The comment above says 'one-second signature' but the value is 1.5.
- [warn] test_integrity at `tests/test_hybrid_signature.py:55`: The brief asks for a test that engine utilisation stays under 100 percent 'at the modelled load'. The window search uses a different, smaller load (gpus=2, requests=20), so it does not check the load `make bench` prints. The other tests mirror the implementation formula (100*sign/window), so they check consistency with the code, not an independent expectation.
- [warn] unsupported_claim at `docs/04-specification.md:245`: The spec row says 'the hybrid cost is far above the P-384 cost' and that the 50 ms window cannot hold it. Both depend on the unsourced 10M-cycle constant and are not shown independently of it. The row itself says the constant is not a spec figure. The 'window longer than the combined sign time keeps the engine under 100 percent' statement is true by construction (utilisation = sign/window).
- [warn] scope at `docs/04-specification.md:245`: The brief owns govsim/bench.py and the test. The agent added a row to the spec table docs/04 §9, with a threshold cell, though the brief does not ask for a doc change. The row is hedged and carries no numbers, so the harm is small, but it puts the placeholder in a spec document.

### Claims

- supported (summary): The 10M-cycle ML-DSA-65 figure is still unsourced; the model carries it flagged as an unverified placeholder (bench.py:41-48) (evidence: govsim/bench.py:41-48 says UNVERIFIED PLACEHOLDER and MLDSA65_COST_SOURCED = False)
- NOT SUPPORTED (code): The ML-DSA-65 figure is a Cortex-M4 pqm4 count of about 10 million cycles (evidence: bench.py:21-24 and :33 cite pqm4 but the comment at :26-28 admits it is from memory. No source in the repo.)
- supported (code): Scaling M4 to OTBN is 1.0x (evidence: bench.py:29: labelled an assumption, not measured. Stated as an assumption, so not a claim of fact.)
- NOT SUPPORTED (summary): The verdict is computed from the run in hybrid_report() (evidence: Utilisation values come from h, but the sign time, window and `holds` use module constants (bench.py:103-115).)
- NOT SUPPORTED (summary): A test checks that a 1.5 s signature flips the verdict (evidence: tests/test_hybrid_signature.py:79-81 asserts only utilisation > 100, not the report text.)
- supported (summary): test_a_window_under_one_second_exists_by_search scans 10 to 990 ms and asserts the shortest window sits just above the combined sign time and 250 ms is among them (evidence: tests/test_hybrid_signature.py:52-60 does this, on a reduced load (gpus=2, requests=20).)
- supported (summary): The 2x slack is computed from the formula; a new test pins utilisation and latency to sign time over window (evidence: tests/test_hybrid_signature.py:23-28 and :42-49)
- supported (summary): The 8x test also checks record latency, which exceeds 1 s (evidence: tests/test_hybrid_signature.py:63-70)
- supported (summary): Unsourced derived figures (117 ms, 234%, 47%, 367 ms) were cut from the docs/04 row (evidence: The diff against main adds the row without those numbers (docs/04-specification.md:245). The earlier version is only in the commit history.)
- supported (summary): Verification and session setup claim removed; only signing is counted (evidence: bench.py hybrid_report ends with 'Only signing is counted; other uses of the engine are not modelled' and docs/04:245 says the same)
- supported (document): ML-DSA is not in Earl Grey silicon and no OTBN-specific measured cycle count is in the repo (docs/04 §7, docs/08, docs/18 §9) (evidence: docs/04:206, docs/08-silicon-plan.md:40 and docs/18:166 say ML-DSA is not in Earl Grey silicon; no cycle count was found by grep for 'ML-DSA' in those files.)
- NOT SUPPORTED (code): The model shows a window under 1 s keeps the one engine under 100 percent, so the disproof did not hold (evidence: Computed by `make bench` (acceptance.log) as sign/window = 47%. It is conditional on the unsourced constant and the 1.0x scaling, which the output says.)
- supported (summary): The 250 ms window is a modelling choice with no latency target behind it; widening it is a spec decision (evidence: No latency target found in the diff, so the choice is a modelling assumption; the spec-decision statement is a judgement, not a checked fact.)

### suite in a clean checkout: exit 0

```
........................................................................ [ 34%]
........................................................................ [ 69%]
................................................................         [100%]
208 passed in 17.18s

```

### acceptance in a clean checkout: exit 0

```
 50, 'fabric_msg': 100, 'fabric_rx': 300, 'action': 50, 'ticket': 50}
hybrid (P-384 + ML-DSA-65, both per batch): 117 ms per batch (ML-DSA-65 10,000,000 cycles, Cortex-M4 pqm4 figure, UNVERIFIED placeholder, no checked source; re-check pqm4 and the M4->OTBN scaling; OTBN 1.0x assumed); engine 234% at the 50 ms window (cannot keep up) -> 47% at a 250 ms window (keeps up); record latency <= 367 ms. Disproof did not hold: a window under 1 s keeps the one engine under 100 percent, conditional on the unverified ML-DSA figure. Only signing is counted; other uses of the engine are not modelled.
short responses (100 tokens): engine 272% unbatched, which cannot keep up, -> 34% batched (why the spec batches, docs/04 §9)
........                                                                 [100%]

```
