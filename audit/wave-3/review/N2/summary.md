**Revision 2** (2026-10-23 00:14) on sonnet: 13 turns, estimated $1.0394, acceptance `python3 -m pytest -q tests/test_false_halt_model.py`: **pass**. The gate reviews the branch again.

Agent summary:

All three blocking findings are fixed. The acceptance command now passes (20 tests, two runs this revision), and the fix is committed as `dcb6f68`. I did not run the full suite.

**What changed**
- **Collection failure:** `govsim/false_halt.py` had been renamed to `govsim/faults.py` in the launcher's revision-1 commit, so the old import failed. `tests/test_false_halt_model.py` now imports `govsim.faults`.
- **Dead injectors:** The injection tests now call the `inject_*` functions in `faults.py` and read which slots halted. The old tests set state by hand.
- **Firmware hang:** The test now does a real watchdog reset with `governor.restart()`. The governor goes to `HALTED_INITIAL`, its switch is open, the loop loses current and the whole rack halts. That matches the model's rack scope. The old test only downed one fabric port and checked a single slot.
- **Authority outage:** `faults.py` counts it as a rack event, since every GPU halts with the loop closed. The doc and the `EXPERIMENTS.md` split are now 0.767 rack-wide and 0.063 one-slot. The total is still 0.830 and the threshold is still 1.24.
- **Doc numbers:** `test_doc_carries_the_numbers` now checks every table row, the debounce figures (0.00134 and 12.5), both break-evens and the 12.4 baseline against the text of `docs/07`. This covers the verifier's "number in no code or test" warnings.
- **Break-evens:** The firmware figure was 1100 in the doc and 1150 in a docstring. The computed value is 1157 and both now say so. The sense-transient break-even is 5.9e-4 per hour. A new test checks that both cross the threshold exactly.
- **Debounce wording:** The comparator injector's docstring now says `govsim` senses the loop with one sample. The two-sample debounce lives in the model only.

**What I did not change**
- **Rate sources:** The brief's "with sources" is only partly met. I have no web access and did not read the IEC 61508, IEC 62380, SN 29500 or MIL-HDBK-217F tables. The rates are planning values at those sources' order of magnitude, and `docs/07` §5.1 says so. Giving them real citations needs someone with the tables.
- **Threshold basis:** The Llama 3 figures are still quoted from memory and the "one tenth" is still my judgement. Both are stated in the doc.
- **Injection tests:** The power-loss and wire-cut tests still set the very state that halts the rack. That is how the simulator models those modes, and the tests confirm the rack scope, not the rates.
- **Test name in the doc:** `test_jumpered_governor_is_caught_by_the_beacon_within_two_heartbeats` is an existing test in `tests/test_h11_halt_loop.py`, not part of this diff, so I left the doc's reference to it as it is.

## Commit messages
- N2: test imports govsim.faults and calls its injectors; firmware hang injected as a real watchdog restart; authority outage counted as a rack event; doc numbers and break-evens tied to tests (#12)
Agent: wave 3, issue #12 (revision 2)

- Revision 1: work left uncommitted by the agent, committed by the launcher (#12)
Agent: wave 3, issue #12 (revision 1, launcher commit)

- N2: false-halt rate model, numeric FMEA in docs/07, fault injection tests (#12)
Agent: wave 3, issue #12

