## Part 1 — Claims in the summary and commit messages

1. *All three blocking findings are fixed.* — NOT FOUND (meta assertion; no single diff line).
2. *The acceptance command now passes.* — NOT FOUND in diff (stated only in the revision header `acceptance ... : **pass**`, which is not part of the diff).
3. *(20 tests, two runs this revision)* — NOT FOUND (no test count or run count anywhere in the diff).
4. *The fix is committed as `dcb6f68`.* — NOT FOUND (the hash does not appear in the diff).
5. *I did not run the full suite.* — NOT FOUND (statement of omission).
6. *`govsim/false_halt.py` had been renamed to `govsim/faults.py` ... so the old import failed.* — Partial: the new file's existence is shown by `diff --git a/govsim/faults.py b/govsim/faults.py` / `new file mode 100644`; the rename history and the "old import failed" are NOT FOUND in this diff.
7. *`tests/test_false_halt_model.py` now imports `govsim.faults`.* — `+from govsim import faults as fh` (tests/test_false_halt_model.py).
8. *The injection tests now call the `inject_*` functions in `faults.py` and read which slots halted.* — `+    assert fh.inject_power_loss(rack, rack.nodes[1].governor) == [False] * 4` (and the parallel `inject_*` calls throughout the test file); injectors defined in `govsim/faults.py` (`+def inject_power_loss ...`).
9. *The old tests set state by hand.* — NOT FOUND (concerns the pre-diff tests).
10. *The test now does a real watchdog reset with `governor.restart()`.* — `+    governor.restart()                    # the watchdog reset: govsim reboots into HALTED_INITIAL, switch open` (inject_firmware_hang, govsim/faults.py).
11. *The governor goes to `HALTED_INITIAL`, its switch is open, the loop loses current and the whole rack halts.* — `+    assert g.state == "HALTED_INITIAL" and g.loop_switch_open and not rack.loop.current()` (test_inject_firmware_hang_watchdog_reset_opens_the_loop_and_halts_the_rack).
12. *That matches the model's rack scope.* — `+    assert fh.MODE["fw_hang"].scope == "rack"` (same test).
13. *The old test only downed one fabric port and checked a single slot.* — NOT FOUND (concerns the pre-diff test; the new slot-scoped test is `+    assert fh.inject_fabric_port_failure(...) == [True, True, False, True]` but that is the new behaviour, not the old).
14. *`faults.py` counts [the authority outage] as a rack event, since every GPU halts with the loop closed.* — `+    rows["authority_outage"] = AUTHORITY_OUTAGE_RATE_PER_H * HOURS_PER_YEAR      # one event; it halts every slot, so it is a rack event` and `+    scope.update(..., authority_outage="rack", ...)`.
15. *The doc and the `EXPERIMENTS.md` split is now 0.767 rack-wide and 0.063 one-slot.* — EXPERIMENTS.md `+(0.767 rack-wide, 0.063 one slot)`; docs/07 `+**Result.** Rack-wide false halts 0.767 ... single-slot false halts 0.063`.
16. *The total is still 0.830 and the threshold is still 1.24.* — docs/07 `+... together **0.830 per rack-year**` and `+... one tenth of that, **1.24 false halts per rack-year**`.
17. *`test_doc_carries_the_numbers` now checks every table row, the debounce figures (0.00134 and 12.5), both break-evens and the 12.4 baseline against the text of `docs/07`.* — `+    for key in (...): assert f"{rows[key]:.3f}" in text`; `+    assert f"{fh.survive_debounce(20e-6):.5f}" in text` (0.00134); `+    assert f"{fh.rack_year(samples=1)['rows']['sense_glitch']:.1f}" in text` (12.5); `+    assert f"{fh.fw_hang_break_even_fit():.0f}" in text and f"{fh.sense_glitch_break_even_rate() * 1e4:.1f}e-4" in text`; `+    assert f"{fh.BASELINE_INTERRUPTIONS_PER_RACK_YEAR:.1f}" in text` (12.4).
18. *This covers the verifier's "number in no code or test" warnings.* — NOT FOUND (meta).
19. *The firmware figure was 1100 in the doc and 1150 in a docstring.* — NOT FOUND (those are the pre-diff values; the diff carries only the new 1157).
20. *The computed value is 1157 and both now say so.* — faults.py docstring `+... above this (about 1157 FIT).` and docs/07 `+... firmware watchdog trips above about 1157 FIT.`; checked by `+    assert 1150 < hang < 1160`.
21. *The sense-transient break-even is 5.9e-4 per hour.* — faults.py docstring `+... N3 measures above this (about 5.9e-4 per hour).` and docs/07 `+... above about 5.9e-4 per hour at 20 us mean duration`; checked by `+    assert 5.8e-4 < g < 6.0e-4`.
22. *A new test checks that both cross the threshold exactly.* — `+def test_break_even_points_cross_the_threshold_exactly():` with `+    assert fh.fit_to_per_year(hang - fh.MODE["fw_hang"].fit, 72) + fh.rack_year()["total"] == pytest.approx(fh.SWITCH_OFF_THRESHOLD)` and `+    assert extra + fh.rack_year()["total"] == pytest.approx(fh.SWITCH_OFF_THRESHOLD)`.
23. *The comparator injector's docstring now says `govsim` senses the loop with one sample.* — `+... (scope: rack). govsim senses the loop with one sample, so the second propagate is harmless; the two-sample debounce is in the model, not here."""` (inject_comparator_stuck_open).
24. *The two-sample debounce lives in the model only.* — `+... the two-sample debounce is in the model, not here.` and docs/07 `+**Not modelled.** `govsim` senses the loop with one sample; the two-sample debounce exists in the doc and in this model, not yet in the simulator or the RTL claim.`
25. *The brief's "with sources" is only partly met.* — NOT FOUND (meta).
26. *I have no web access and did not read the IEC 61508, IEC 62380, SN 29500 or MIL-HDBK-217F tables.* — NOT FOUND (statement of omission).
27. *The rates are planning values at those sources' order of magnitude, and `docs/07` §5.1 says so.* — `+**Sources, stated plainly.** The rates are planning values chosen to the order of magnitude of the IEC 61508-6 data annex, IEC 62380, SN 29500 and MIL-HDBK-217F (connector class) ... They were not read out of those tables in this run`.
28. *Giving them real citations needs someone with the tables.* — NOT FOUND (meta).
29. *The Llama 3 figures are still quoted from memory and the "one tenth" is still my judgement.* — docs/07 `+... which scales to 12.4 per 72-GPU rack-year (quoted from memory; confirm against the paper).` and `+The tenth is a judgement, not a measurement from any operator.`
30. *Both are stated in the doc.* — same two lines as #29 (both in docs/07 §5.1).
31. *The power-loss and wire-cut tests still set the very state that halts the rack.* — `+    governor.loop_switch_open = True` (inject_power_loss) and `+    rack.loop.cut()` (inject_wire_cut) in govsim/faults.py.
32. *That is how the simulator models those modes, and the tests confirm the rack scope, not the rates.* — `+    assert fh.inject_power_loss(rack, rack.nodes[1].governor) == [False] * 4` / `+    assert fh.inject_wire_cut(rack) == [False] * 4` plus `+    assert fh.MODE["..."].scope == "rack"` (scope asserted, no rate checked in those tests).
33. *`test_jumpered_governor_is_caught_by_the_beacon_within_two_heartbeats` is an existing test in `tests/test_h11_halt_loop.py`, not part of this diff.* — Partial: the reference appears in docs/07 `+... two heartbeats of latency, `test_jumpered_governor_is_caught_by_the_beacon_within_two_heartbeats`.`; the claim that it lives in `tests/test_h11_halt_loop.py` is NOT FOUND (that file is not in the diff).
34. *N2 commit: "test imports govsim.faults and calls its injectors; firmware hang injected as a real watchdog restart; authority outage counted as a rack event; doc numbers and break-evens tied to tests (#12)"* — `+from govsim import faults as fh` + the `inject_*` calls; `+    governor.restart()`; `+    rows["authority_outage"] = ... # ... a rack event` + `scope.update(... authority_outage="rack" ...)`; `+def test_doc_carries_the_numbers` + `+def test_break_even_points_cross_the_threshold_exactly`.
35. *Revision-1 launcher commit: "work left uncommitted by the agent, committed by the launcher (#12)"* — NOT FOUND (process claim, no diff evidence).
36. *N2 original commit: "false-halt rate model, numeric FMEA in docs/07, fault injection tests (#12)"* — the new files `govsim/faults.py`, docs/07 §5.1, and `tests/test_false_halt_model.py` (all `new file mode 100644`).

## Part 2 — Numbers in the changed documents

**EXPERIMENTS.md, N2 row**
- `0.830` — recorded here; computed as `rack_year()["total"]` (govsim/faults.py), checked in `test_threshold_and_verdict` / `test_doc_carries_the_numbers`.
- `0.767` — recorded here; = `rack_year()["rack"]`, checked in `test_rack_year_is_the_sum_of_its_rows_by_hand`.
- `0.063` — recorded here; = `rack_year()["slot"]`, checked in `test_rack_year_is_the_sum_of_its_rows_by_hand`.
- `1.24` — recorded here; = `SWITCH_OFF_THRESHOLD`, checked in `test_threshold_and_verdict` (`1.1 < ... < 1.3`).
- `a tenth` (=0.1) — `SWITCH_OFF_FRACTION = 0.10` (govsim/faults.py).
- `2026-10-22` — recorded only (a date); NOT FOUND as computed anywhere.

**docs/07 §5.1, prose**
- `72` (rack is 72 governors) — `RACK_GOVERNORS = 72` (govsim/faults.py).
- `10^9` (FIT = failures per 10^9 device-hours) — `FIT = 1e-9`.
- `419` / `54` / `16384` (Llama 3 interruptions/days/GPUs) — `LLAMA3_INTERRUPTIONS, LLAMA3_DAYS, LLAMA3_GPUS = 419, 54, 16384`; checked in `test_threshold_and_verdict`.
- `12.4` (per rack-year baseline) — computed `BASELINE_INTERRUPTIONS_PER_RACK_YEAR`, checked in `test_doc_carries_the_numbers`.
- `1.24` (threshold) — `SWITCH_OFF_THRESHOLD` (as above).
- `67` percent (0.830 is 67% of threshold) — recorded in prose only; NOT FOUND as computed (verdict() returns only "below"/"ABOVE").
- `5.9e-4` (sense-transient break-even /h) — `sense_glitch_break_even_rate()`, checked in `test_break_even_points_cross_the_threshold_exactly` (`5.8e-4 < g < 6.0e-4`).
- `1157` (firmware break-even FIT) — `fw_hang_break_even_fit()`, checked `1150 < hang < 1160`.
- `0.001` (transient row removed by two-beacon confirm) — = `beacon_transient` row; checked in `test_doc_carries_the_numbers`.
- `confirm=2` / "two heartbeats" / "one beacon" — `BEACON_CONFIRM_WINDOWS = 1` and the `beacon_transient_rate_per_h(confirm)` logic; "two heartbeats of latency" prose only.
- "one sample" / "two-sample debounce" — `DEBOUNCE_SAMPLES = 2` / `SENSE_PERIOD_S = 100e-6` (the one-vs-two-sample contrast).

**docs/07 §5.1, table (Rate / Per rack-year columns)**
- `200` FIT (gov_power) — `Mode("gov_power", ..., 200, ...)`; per-year `0.126` = `fit_to_per_year(200,72)`, summed in `test_rack_year_is_the_sum_of_its_rows_by_hand`.
- `500` FIT (fw_hang) — `Mode("fw_hang", ..., 500, ...)`; `0.316` = `fit_to_per_year(500,72)`.
- `40` FIT (loop_wire) — `Mode("loop_wire", ..., 40, ...)`; `0.025` = `fit_to_per_year(40,72)`.
- `50` FIT (comparator stuck open) — `Mode("comparator_stuck_open", ..., 50, ...)`; `0.032` = `fit_to_per_year(50,72)`.
- `100` FIT (glitch detector false trip) — `Mode("clock_glitch_detector", ..., 100, ...)`; `0.063` = `fit_to_per_year(100,72)`.
- `50` FIT (switch readback stuck open) — `Mode("beacon_readback_stuck", ..., 50, ...)`; `0.032` = `fit_to_per_year(50,72)`.
- `1e-4` per hour, `20` us (sense transient inputs) — `SENSE_GLITCH_RATE_PER_H = 1e-4`, `SENSE_GLITCH_MEAN_S = 20e-6`.
- `0.00134` (two-sample survival) — `survive_debounce(20e-6)`, checked in `test_two_sample_debounce_hand_numbers` and `test_doc_carries_the_numbers`.
- `0.084` (sense-glitch rack-year row) — `rows["sense_glitch"]`, summed in `test_rack_year_is_the_sum_of_its_rows_by_hand`.
- `5.6e-13` per window (beacon readback transient) — recorded in the table only; NOT FOUND as a literal in code (code carries the per-hour `beacon_transient_rate_per_h(1)` = `3600 * p` and the per-rack-year `0.001`).
- `0.001` (beacon transient rack-year row) — `rows["beacon_transient"]`, checked in `test_beacon_transient_needs_the_glitch_live_at_the_report_instant` and the doc test.
- `100` FIT (fabric port) — `Mode("fabric_port", ..., 100, "slot", ...)`; `0.063` = `fit_to_per_year(100,72)`.
- `1e-5` per hour, `5` s expiry (authority outage) — `AUTHORITY_OUTAGE_RATE_PER_H = 1e-5`, `HEARTBEAT_EXPIRY_S = 5.0`; `0.088` = that rate `* HOURS_PER_YEAR`.
- `1e-3` per frame, `5` beats, dual ring (heartbeat loss) — `HEARTBEAT_HOP_LOSS = 1e-3`, `k = int(HEARTBEAT_EXPIRY_S // HEARTBEAT_PERIOD_S)` = 5, `paths = 2`; `2e-21` = `heartbeat_loss` row, checked in `test_heartbeat_loss_needs_every_heartbeat_of_the_window_on_both_paths`.
- `20`, `100` FIT (fuse read, NVM corruption) — `Mode("fuse_read", ..., 20, ...)` and `Mode("nvm_corruption", ..., 100, ...)` with `runtime=False`; per-rack-year `0` since they are excluded from `rows` (checked `assert "fuse_read" not in r["rows"] and "nvm_corruption" not in r["rows"]`).
- `0.767` / `0.063` / `0.830` (Result line) — = `rack_year()["rack" / "slot" / "total"]`, checked in `test_rack_year_is_the_sum_of_its_rows_by_hand` and `test_threshold_and_verdict`.
- `12.5` (single-sample rack halts) — `rack_year(samples=1)["rows"]["sense_glitch"]`, checked in `test_the_debounce_is_what_keeps_glitches_out` (`without > 100 * with_debounce`) and `test_doc_carries_the_numbers`.
- `0.316` (firmware-hang row, "largest hard-fault row") — = `fit_to_per_year(500,72)` (as above).

**docs/07 / govsim constants that feed the table but are not themselves printed in the table**
- `8766` (HOURS_PER_YEAR), `1e-9` (FIT), `100e-6` (SENSE_PERIOD_S), `2` (DEBOUNCE_SAMPLES), `1.0` (HEARTBEAT_PERIOD_S) — all defined in govsim/faults.py and used in the computations above; checked in `test_fit_conversion`, `test_debounce_closed_forms_match_the_sampled_comparator`.
