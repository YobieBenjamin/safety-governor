## Review of `exp/n2`: **revise**

Verifier: clean; model review on ?: 1 blocking, 8 warnings, 6 unsupported claim(s) of 12; estimated $0.33, 8 turns.

### Reviewer's summary

The arithmetic is reproduced by the tests and the suite and acceptance pass, but the brief's acceptance ("docs/07 carries the numbers with sources") is not met.
The agent says the rates were not read from IEC 61508/62380, SN 29500 or MIL-HDBK-217F, and the Llama 3 baseline is quoted from memory. 6 of the 9 hard-fault rates are labelled "assumed".
EXPERIMENTS.md marks N2 "done" anyway.
Two injectors do not model the mode they are named for (readback stuck, firmware hang). The two-sample debounce, the point of the brief, is not in govsim.
The doc-number test matches substrings, so it cannot tie each table row to its number.
Question: the 5.6e-13, 2e-21 and "67 percent" figures in docs/07 have no test that computes them against the doc text.

### Verifier findings

- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:102: 5.1`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:110: 0.126`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:111: 0.316`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:112: 0.025`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:113: 0.032`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:115: 0.032`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:116: 0.00134`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:116: 0.084`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:119: 0.088`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:123: 0.084`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:123: 12.5`
- [warn] a number added to a document appears in no added code, test, data or result of this branch: `docs/07-verification-plan.md:123: 0.316`

### Reviewer findings

- [block] unsupported_claim at `docs/07-verification-plan.md:106`: The brief's acceptance requires the numbers 'with sources'. This paragraph says the rates were not read out of IEC 61508-6, IEC 62380, SN 29500 or MIL-HDBK-217F. Six of nine hard-fault rows are 'assumed' (the Rate column also marks firmware hang, comparator stuck open and glitch detector false trip). The 200 FIT, 40 FIT and 100 FIT rows carry no committed source; the table cites no passage of any named standard. The honesty is good, but acceptance is not met: either cite checkable sources, or have the brief and EXPERIMENTS.md say 'planning values, sources outstanding'.
- [warn] unsupported_claim at `govsim/faults.py:56`: The `source` strings (e.g. 'IEC 62380 / SN 29500 connector class', 'MIL-HDBK-217F connector class', 'IEC 61508-6 software-fault allowance', 'IEC 62380 class') read as citations in the code. The module docstring (line 8) says none was looked up. A reader of the Mode table alone would take them as sourced; label them 'unverified' in the field itself.
- [warn] unsupported_claim at `docs/07-verification-plan.md:125`: The disproof threshold rests on 419 interruptions / 54 days / 16384 GPUs, 'quoted from memory; confirm against the paper'. The 'one tenth' is a judgement. The brief asks where the threshold came from. The text says so, but no artifact or source excerpt is committed, so 1.24 and the 67 percent margin are unsupported. The '67 percent' figure is computed nowhere in code or tests.
- [warn] unsupported_claim at `EXPERIMENTS.md:28`: The row is set to 'done' and carries 0.830 and 1.24 while the rates are unsourced and the debounce is not in govsim. It states the caveats, but 'done' overstates a result whose acceptance clause on sources is open. 'open (sources outstanding)' would match the evidence.
- [warn] test_integrity at `tests/test_false_halt_model.py:77`: test_doc_carries_the_numbers checks `f"{x:.3f}" in text` over the whole document. 0.032 and 0.063 each belong to two table rows, '0.001' matches inside '0.00134', and any short token can match elsewhere. A wrong number in one row would pass if another row shows the same value. The table figures 5.6e-13 and 2e-21 and the 67 percent are not checked at all. Parse the table rows, or assert row label next to value.
- [warn] correctness at `govsim/faults.py:246`: inject_readback_stuck_open wires the governor around with `rack.loop.jumper(...)` and sets `loop_switch_open = True`. That is the real jumpered-switch hazard (what test_h11 already covers), not a faulty readback on a healthy closed switch, which is the false-halt mode the table row ('Switch readback stuck open', 50 FIT) models. The test at tests/test_false_halt_model.py:145 therefore confirms an existing true-positive path, not the effect of the modelled fault.
- [warn] correctness at `govsim/faults.py:219`: inject_firmware_hang calls `governor.restart()`, whose docstring is 'Power loss and return' (govsim/governor.py:154). It is a reboot, not a watchdog reset triggered by a hang, and no watchdog is modelled. The reset reaches HALTED_INITIAL only because boot does. The comment 'the watchdog reset' and the summary claim of 'a real watchdog restart' overstate this. It is also the same effect as the gov_power test.
- [warn] correctness at `govsim/faults.py:104`: The 0.084 sense-glitch row and the 12.5 single-sample figure depend on a two-sample debounce that govsim does not implement (the Not-modelled note at docs/07:129 and the comparator docstring at faults.py:209 admit this). The brief asked fault injection to confirm each mode's effect under the loop's debounce; the debounce itself, the largest-sensitivity assumption (exponential 20 us glitches), is checked only against a Monte Carlo (survive_debounce_mc) written with the same assumption, so the test cannot fail on the assumption. It is disclosed, but it is not shown.
- [warn] test_integrity at `tests/test_false_halt_model.py:104`: The power-loss and wire-cut tests set the state that opens the loop (`loop_switch_open = True`, `loop.cut()`) and then assert the loop is open. They check that govsim's loop is a series circuit, not the model's rate or scope; the `scope == 'rack'` assertion compares the model's own constant to a string. The summary says so for these two, but the test names ('halts_the_rack') promise more.

### Claims

- supported (document): A false-halt model gives 0.830 false halts per rack-year (0.767 rack-wide, 0.063 one slot). (evidence: govsim/faults.py rack_year() and tests test_rack_year_is_the_sum_of_its_rows_by_hand and test_doc_carries_the_numbers compute it, given the assumed rates.)
- NOT SUPPORTED (document): The failure rates carry sources (IEC 61508-6, IEC 62380, SN 29500, MIL-HDBK-217F, datasheets). (evidence: docs/07:106 says the rates were not read from these tables; no committed source for any rate. Tables not found in the repo.)
- NOT SUPPORTED (document): The switch-off threshold is 1.24 false halts per rack-year (a tenth of the Llama 3 interruption rate of 12.4 per 72-GPU rack-year). (evidence: Arithmetic is tested (test_threshold_and_verdict); inputs 419/54/16384 are 'quoted from memory' and the tenth is a judgement, with no artifact.)
- NOT SUPPORTED (document): Without the two-sample debounce the same glitches would give 12.5 rack halts per rack-year. (evidence: Computed by rack_year(samples=1) and checked in tests; relies on assumed 1e-4/h and 20 us exponential glitches, and the debounce is not in govsim.)
- supported (document): The model's claim fails if N3 measures sense transients above 5.9e-4 per hour or firmware watchdog trips above about 1157 FIT. (evidence: sense_glitch_break_even_rate and fw_hang_break_even_fit, with test_break_even_points_cross_the_threshold_exactly.)
- NOT SUPPORTED (code): Each failure mode injected into govsim has the effect the model assumes (rack vs slot scope). (evidence: Injector tests pass for power, wire, comparator, fabric port, authority outage; readback-stuck injects a real jumper and firmware hang injects a power-loss restart, so those two do not show the named mode.)
- NOT SUPPORTED (summary): The firmware hang is injected as a real watchdog restart. (evidence: faults.py:219 calls governor.restart(), which models power loss and return; no watchdog exists in the diff.)
- supported (code): Authority outage is a rack event (0.088 per rack-year). (evidence: faults.py:201 and test_inject_authority_outage... (all slots halt, loop closed); rate 1e-5/h is assumed.)
- supported (document): Requiring the odd beacon report in two consecutive beacons would remove the transient row but not the stuck row. (evidence: beacon_transient_rate_per_h(confirm) tested for 2 vs 1; the stuck-row part follows from the model structure; no govsim test of confirm=2.)
- NOT SUPPORTED (document): The 5.6e-13 per window, 2e-21 and 0.001 values in the table. (evidence: Computable from beacon_transient_rate_per_h and heartbeat_loss_rate_per_h (0.001 matches only by substring); 5.6e-13 and 2e-21 are not compared to the doc text by any test.)
- supported (document): The existing test test_jumpered_governor_is_caught_by_the_beacon_within_two_heartbeats gives the two-heartbeat latency. (evidence: Test exists at tests/test_h11_halt_loop.py:116 in the checkout.)
- NOT SUPPORTED (document): EXPERIMENTS.md N2 is done. (evidence: Acceptance clause 'with sources' is not met and the debounce is not in govsim; the row's own caveats say so.)

### suite in a clean checkout: exit 0

```
........................................................................ [ 29%]
........................................................................ [ 58%]
........................................................................ [ 87%]
...............................                                          [100%]
247 passed in 3.33s

```

### acceptance in a clean checkout: exit 0

```
....................                                                     [100%]

```
