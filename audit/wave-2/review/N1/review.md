## Review of `exp/n1`: **revise**

Verifier: clean; model review on ?: 1 blocking, 10 warnings, 4 unsupported claim(s) of 15; estimated $0.37, 7 turns.

### Reviewer's summary

Sound, honest work: three new files, no existing test touched, acceptance passes, and the numbers in docs/12 are pinned by tests.
The headline "claim holds, 0.015 percent" rests on the agent's own reading that the GPU slot is freed while the receipt is pending. docs/04 §9 and bench.py do not say that. The doc flags it, but under the slot-held reading the brief's disproof stands, so the verdict is conditional.
Must fix: the deploy.py module docstring still says "a request never queues", which the revision made false.
Should fix or show: the token-loss/stall-share agreement is overstated (1.71 vs 1.45 at 80 calls), and the crossing and the disproof are reported on stall share, not the measured metric.
Also should fix or show: the single-seed p99 difference with no spread, per-slot queues with no dispatcher, and several untested prose claims (1.15 s, bursty traffic, "any plausible action rate").
Question for the owner of docs/04 §9: is the slot held while the receipt is pending?

### Verifier findings

- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/12-deployment-overhead.md:7: 46`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/12-deployment-overhead.md:45: 3.3`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/12-deployment-overhead.md:45: 1.15`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/12-deployment-overhead.md:64: 0.017`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/12-deployment-overhead.md:65: 46`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/12-deployment-overhead.md:69: 0.21`

### Reviewer findings

- [block] correctness at `govsim/deploy.py:23`: The module docstring still says 'In this one-process-per-slot model a request never queues, so the added latency is the receipt wait'. The revision made open-loop latency include queueing (line 171 'arrived = t_next', baseline p99 3.3 s), and docs/12 deleted the claim. The code now documents the opposite of what it does. Fix the docstring.
- [warn] unsupported_claim at `govsim/deploy.py:264`: measure() docstring: 'the two agree because the only stalls are the ones that reduce the token count'. docs/12 line 38 gives a different reason for the 0.0151 vs 0.0168 gap (unfinished requests at the horizon). The sweep shows token loss 1.71 against stall share 1.45 at 80 calls (docs/12 line 81), a gap of 0.26 points or 18 percent. The two metrics are not the same, and the explanation for the gap is not tested.
- [warn] correctness at `docs/12-deployment-overhead.md:55`: The headline conclusion depends on one modelling choice made by the agent: the slot is freed while the receipt is pending. Neither bench.py nor docs/04 §9 says so (§9 says only that the record trails the response and that a gating runtime adds up to 67 ms). The doc discloses this, which is right. But lines 7-10 still say 'The claim holds', and the test at tests/test_deploy_overhead.py:16 asserts under 1 percent only for the default Policy(hold_slot=False). Under the other reading the disproof stands (lines 101-106). The result is conditional until the spec owner answers.
- [warn] test_integrity at `tests/test_deploy_overhead.py:49`: test_disproof_is_not_met_for_the_plan_of_record asserts that the default Policy is under 1 percent and that the hold_slot=True sweep is over 1 percent. Both follow from how the two policies are defined in deploy.py, so the test shows the assumption's consequence, not that the assumption is the spec's plan of record. The brief's acceptance (under 1 percent at the plan of record) is met only on the agent's definition.
- [warn] unsupported_claim at `govsim/deploy.py:311`: The slot-held disproof (every serviceable window above 1 percent) and the crossing at about 55 calls (sweep_actions, line 304) are both computed from stall_pct, the bookkeeping sum. The headline metric was changed to measured token loss precisely because the stall sum is a weaker measure. Only one point (80 calls, test line 159-163) is cross-checked, and there the metrics differ. The reported crossing therefore has no measured-token counterpart, which docs/12 line 81 admits.
- [warn] unsupported_claim at `docs/12-deployment-overhead.md:81`: '1.71 percent' appears in the doc, but the test asserts only |overhead - stall| < 0.35 and carries the value in a comment (tests/test_deploy_overhead.py:163). The figure is not pinned, contrary to the claim that every number in docs/12 is pinned.
- [warn] unsupported_claim at `docs/12-deployment-overhead.md:45`: 'p99 about 3.3 s, against 1.15 s for the exponential service-time tail alone, 250 ms times ln 100'. 1.15 is hand-derived and appears in no code or test (the verify warnings 3.3 and 1.15). The test only asserts the baseline p99 > 2.0 (tests/test_deploy_overhead.py:136).
- [warn] correctness at `govsim/deploy.py:259`: A single seed (seed=1) is used for every figure. p99 added latency is the difference of two simulated p99s (3337 vs 3291 ms), and the test pins it at 45.6 +/- 5 (tests/test_deploy_overhead.py:126). No spread across seeds is shown, so '46 ms' and the 0.0151 vs 0.0168 agreement within 0.003 are single draws. The 0.003 tolerance was tightened against that one draw.
- [warn] correctness at `govsim/deploy.py:157`: Open mode gives each slot its own independent Poisson stream and queue, with no dispatcher across the 8 slots. Queueing delay is therefore the M/G/1 tail at 70 percent load, which dominates the 3.3 s p99. The doc notes 'one queue per slot' (line 118) but does not say a shared queue would give a much smaller baseline tail. The 46 ms 'added' is relative to that baseline.
- [warn] correctness at `govsim/deploy.py:199`: In the hold_slot branch, slot.release(req) runs at line 199, before the process yields on the receipt event at line 202. The slot is held only because the same loop process blocks. In the saturated sweeps nothing else wants the slot, but the edition-change _reprogram process can take it during the wait. The 'slot held' worst case is held by control flow rather than by the resource, which is fragile and unexplained.
- [warn] unsupported_claim at `docs/12-deployment-overhead.md:119`: 'Bursty traffic ... changes nothing for the engine ... but would raise the tail wait for the unlucky first record', and line 89 'A governor firmware core is not the constraint at any plausible action rate'. Neither was simulated. Arrivals are Poisson only, and the action sweep stops at 160 calls per response.

### Claims

- supported (summary): Open-loop latency now runs from the arrival, so queueing is included; p99 3337 ms vs 3291 ms, 46 ms added (evidence: deploy.py lines 165-171 (arrived = t_next); test_numbers_used_in_docs_12_are_computed pins 3337 +/-20, 3291 +/-20, 45.6 +/-5; single seed only)
- NOT SUPPORTED (summary): The 'a request never queues' claim is deleted (evidence: Absent from docs/12 (new file), but still present in the govsim/deploy.py module docstring at lines 23-25)
- supported (document): Plan of record = slot freed while the receipt is pending; flagged as an assumption (evidence: docs/12 lines 8-10, 55-59, 101-106 state it is the note's reading. bench.py and docs/04 §9 do not say the slot is held or freed)
- supported (document): The claim holds at the plan of record: about 0.015 percent throughput lost, measured against a no-governor baseline (evidence: tokens_governed 34,273,417 vs tokens_baseline 34,278,595 in measure(); pinned in test_numbers_used_in_docs_12_are_computed. Single seed, and valid only under the slot-freed reading)
- NOT SUPPORTED (document): Measured loss and stall share agree within 0.003 points (0.0151 vs 0.0168), because the stall share also counts slot time in unfinished requests (evidence: tests/test_deploy_overhead.py line 45 asserts <0.003 and pins both values. The explanation of the gap is not tested. At 80 calls the gap is 0.26 points)
- supported (document): The mailbox load crosses 1 percent at about 55 calls per response, about 1,100x the reference (evidence: crossing(sweep_actions()) in main(); test asserts 40<c<70 and mult==1100. The metric is stall share, not measured token loss)
- supported (document): The slot-held reading is above 1 percent at every serviceable window (14.3, 21.2, 32.9 percent at 50, 100, 200 ms) (evidence: test_slot_held_table_in_docs_12 pins the table; test_slot_held_until_receipt... asserts >1 percent for serviceable windows. Computed from the stall share)
- supported (document): Max receipt wait is 68.4 ms with the edition change and 67.0 ms without; the excess is 1.4 ms (evidence: Pinned at 68.4 +/-1 and 67.0 +/-0.5, and the excess is asserted in (0, 5 ms). The 1.4 figure is not pinned precisely)
- supported (document): Ten times any of the log write, Merkle root or heartbeat fan-out stays under 1 percent (0.13, 0.02, 0.02 percent) (evidence: test_sensitivity_figures_in_docs_12 and test_named_assumptions_do_not_move_the_conclusion)
- NOT SUPPORTED (document): 1.71 percent token loss at 80 calls per response (evidence: Only in a test comment (tests/test_deploy_overhead.py line 163); the assertion is |diff|<0.35, so the value is not pinned)
- NOT SUPPORTED (document): p99 about 3.3 s against 1.15 s for the exponential service-time tail alone (evidence: 3.3 s is pinned via 3337 ms. 1.15 is hand-derived (250 ms x ln 100) and appears in no code or test)
- NOT SUPPORTED (document): Bursty traffic changes nothing for the engine; a firmware core is not the constraint at any plausible action rate (evidence: No bursty-arrival run in the diff; the action sweep stops at 160)
- supported (document): The 72 chips are independent copies with no cross-chip traffic (evidence: Chip objects share nothing in run_one(); stated as a limitation in docs/12)
- supported (document): The 17 ms signature, 50 ms window, 2,000 tokens/s, and the 20 us / 1 ms / 2 ms costs come from bench.py and docs/04 §9 (evidence: govsim/bench.py COST_S, SIGN_S, BATCH_WINDOW_S; docs/04 table row at line 244 states the 17 ms and 67 ms)
- supported (code): Throughput lost is measured as the tokens the governed run produces below the baseline (common random numbers) (evidence: measure() computes (base_tokens - gov_tokens)/base_tokens with identical token and arrival streams (seeded 'sizes'))

### suite in a clean checkout: exit 0

```
........................................................................ [ 33%]
........................................................................ [ 67%]
....................................................................     [100%]
212 passed in 44.26s

```

### acceptance in a clean checkout: exit 0

```
ep 2, the slot held until the receipt, by batch window (10 s):
  window=  20 ms  serviceable=False  stall share=9.90 %
  window=  30 ms  serviceable=False  stall share=11.36 %
  window=  50 ms  serviceable=True   stall share=14.33 %
  window= 100 ms  serviceable=True   stall share=21.19 %
  window= 200 ms  serviceable=True   stall share=32.90 %
  slot-held release stays under 1 percent at: no serviceable window (above 1 percent at every serviceable policy)
sensitivity, each named assumption 10x (plan of record otherwise, 10 s):
  log write 10x     stall share=0.1336 %
  merkle root 10x   stall share=0.0248 %
  heartbeat 10x     stall share=0.0246 %
  none moves the plan of record off the sub-one-percent figure
............                                                             [100%]

```
