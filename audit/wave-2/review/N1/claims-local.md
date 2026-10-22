## Claims (summary + commit messages)

1. All the findings are addressed, in c7b9882. — NOT FOUND (c7b9882 not among the listed commits; no diff line asserts it)
2. The deploy sweep and all 12 tests in `tests/test_deploy_overhead.py` pass. — 12 `def test_` functions present (`test_plan_of_record_costs_under_one_percent_and_tail_is_bounded` … `test_mailbox_sweep_stall_share_matches_measured_token_loss`); "pass" NOT FOUND
3. I ran the full acceptance command twice and a variant of it once. — NOT FOUND
4. The first run's failures led to the fixes below. — NOT FOUND
5. Open-loop latency now runs from the arrival time; a request that finds its slot busy carries its queueing delay. — `+            arrived = t_next if mode == "open" else env.now` (with `+                lat.append(done_gpu - arrived)` / `+                    lat.append(released - arrived)`)
6. The p99 is now 3337 ms against 3291 ms, so p99 added latency is 46 ms. — `+| p99 added latency | 46 ms (p99 3337 ms against 3291 ms without the governor, queueing included) |`; "(it was 42)" NOT FOUND
7. The "a request never queues" claim is deleted from docs/12, and a new test asserts the baseline p99 is above 2 s. — test `+    assert r["p99_latency_base_s"] > 2.0, r`; "deleted from docs/12" NOT FOUND (docs/12 is new in this diff; `deploy.py`'s docstring still says "a request never queues")
8. docs/12 and the test docstring now say "slot freed while the receipt is pending" is my reading; `bench.py` and docs/04 §9 don't say whether the slot is held. — `+That condition is this note's reading of the plan of record, not a sentence of the spec (section 2).`; test docstring `+    The plan of record, read as the slot freed while the receipt is pending (docs/12's assumption, not stated in docs/04)`; `+neither says whether the GPU slot is held meanwhile.`
9. The slot-held reading is above 1% at every serviceable window, so the disproof would stand under it. — `+The slot-held reading is therefore swept in section 3 as the alternative, and it is above one percent.`
10. I left that as an open question for whoever owns docs/04 §9. — `+which reading is the spec's is an open question for the owner of docs/04 §9.`
11. "Agree within rounding": now 0.0151% against 0.0168%, within 0.003 points; test tolerance tightened from 0.01 to 0.003. — `+the two agree to within 0.003 percentage points (0.0151 and 0.0168 percent;`; `+    assert abs(r["overhead_pct"] - r["stall_pct"]) < 0.003, r`; "from 0.01" NOT FOUND
12. New tests pin the slot-held table, the sensitivity figures, the token counts, the engine and firmware utilisation, and the p99 and max receipt waits. — `+def test_slot_held_table_in_docs_12():`, `+def test_sensitivity_figures_in_docs_12():`, `+def test_numbers_used_in_docs_12_are_computed():`
13. `measure` and the sweeps are cached so the tests stay fast. — `+@lru_cache(maxsize=None)` above `measure`, `sweep_actions`, `sweep_window_held`, `sensitivity`; "stay fast" NOT FOUND
14. Max receipt wait is 68.4 ms with the edition change and 67.0 ms without it. — `+| Max receipt wait | 68.4 ms with the mid-run edition change, 67.0 ms without it |`; `+    assert abs(r["max_receipt_wait_s"] * 1e3 - 68.4) < 1` / `+    assert abs(r0["max_receipt_wait_s"] * 1e3 - 67.0) < 0.5`
15. The excess is 1.4 ms, not 18 ms, because the firmware queue interleaves operations. — `+The excess is 1.4 ms; the test asserts it is under 5 ms, so the 18 ms is a ceiling, not the observed delay.`; reason `+the queue is FIFO, so it waits for the operations ahead of it, not the whole 18 ms`
16. The doc is corrected, and a test asserts the excess is under 5 ms. — `+    assert 0 < r["max_receipt_wait_s"] - r0["max_receipt_wait_s"] < 0.005   # the edition change adds ~1.4 ms, one firmware op, not 18 ms`
17. The sweep tables and printed output now say "stall share" rather than "overhead". — `+| stall share (percent) |`; `+    print(f"  actions/response={a:>6g}  stall share={o:.4f} %")`; "rather than 'overhead'" NOT FOUND
18. A new test checks that at 80 mailbox calls/response the token loss (1.71%) is within 0.35 points of the stall share (1.45%). — `+    r = measure(replace(PLAN_OF_RECORD, actions_per_response=80), 10.0, 2.0)`; `+    assert abs(r["overhead_pct"] - r["stall_pct"]) < 0.35, r      # 1.71 against 1.45 at 10 s`
19. So the token-based crossing is a little lower than 55 calls, and I don't give a figure for it. — `+so the token-based crossing is a little lower and both are far above the reference workload`; "I don't give a figure" NOT FOUND
20. docs/12 now says the 72 chips are independent copies with no cross-chip traffic. — `+72 independent chips: there is no cross-chip traffic, so the 72 add sample size, not interaction`
21. The sweeps still run 10 s against 30 s for the headline. docs/12 already says so. — `+The results table runs 30 s and the sweeps 10 s, so the edition-change term, one event per chip, is divided by a shorter simulated time and reads a little higher at 10 s`
22. No final summary was recorded for revision 1 (`summary.md:5`); this is the summary for revision 2. — NOT FOUND (summary.md not in diff)
23. Several shell commands were denied, so I ran the sweeps only through the acceptance command. — NOT FOUND

Commit messages:
24. (N1 #11) open-loop latency includes queueing. — `+            arrived = t_next if mode == "open" else env.now`
25. (N1 #11) every number in docs/12 pinned by a test. — `+def test_numbers_used_in_docs_12_are_computed():` (plus `test_slot_held_table_in_docs_12`, `test_sensitivity_figures_in_docs_12`)
26. (N1 #11) plan-of-record slot-freed reading flagged as an assumption. — `+That condition is this note's reading of the plan of record, not a sentence of the spec (section 2).`
27. (N1 #11) edition-change attribution corrected. — `+The excess is 1.4 ms; the test asserts it is under 5 ms, so the 18 ms is a ceiling, not the observed delay.`
28. (Revision 1) work left uncommitted by the agent, committed by the launcher. — NOT FOUND
29. (N1 #11) whole-deployment overhead, 72 governors x 8 slots in a discrete-event simulation. — `+GOVERNORS = 72`; `+72 governors with eight GPU slots each, as a simulation with queues`
30. (N1 #11) docs/12 with method and numbers. — `+++ b/docs/12-deployment-overhead.md` with `+## 1. Method` and the results table

## Numbers in docs/12-deployment-overhead.md

- 1% (one percent) — recorded as threshold `+ONE_PERCENT = 1.0`; asserted throughout (`< ONE_PERCENT`)
- 72 — computed `+GOVERNORS = 72`; recorded `+    assert PLAN_OF_RECORD.governors * SLOTS_PER_CHIP == 576`
- 8 (eight slots) — NOT FOUND as a literal (imported `SLOTS_PER_CHIP`); only via 576
- 0.015% — computed `overhead_pct` in `measure()`; recorded `+    assert abs(r["overhead_pct"] - 0.0151) < 0.002`
- 46 ms — computed `p99_added_s` via `pct()`; recorded `+    assert abs(r["p99_added_s"] * 1e3 - 45.6) < 5`
- 72 independent chips — same as 72
- 20 µs (mailbox/ticket) — NOT FOUND (imported `COST_S["mailbox"]`/`COST_S["ticket"]`, value not in diff)
- 1 ms (per port change) — NOT FOUND (imported `COST_S["switch_program"]`)
- 2 ms (attestation) — NOT FOUND (imported `COST_S["attest"]`)
- 17 ms — computed via `SIGN_S`; recorded `+    assert abs(SIGN_S * 1e3 - 17) < 0.5`
- 50 ms (batch window) — computed via `BATCH_WINDOW_S`; recorded `+    assert BATCH_WINDOW_S * 1e3 == 50.0`
- 500 tokens — computed `+MEAN_TOKENS = 500`
- 2,000 tokens/s — NOT FOUND as literal (imported `GPU_SECONDS_PER_TOKEN`); only via 250 ms
- 250 ms — recorded `+    assert abs(MEAN_TOKENS * GPU_SECONDS_PER_TOKEN * 1e3 - 250) < 1e-9`
- 0.05 — computed `+ACTIONS_PER_RESPONSE = 50 / 1000`; recorded `+    assert ACTIONS_PER_RESPONSE == 0.05`
- 1 s (heartbeat) — computed `+HEARTBEAT_PERIOD_S = 1.0`
- 5 µs × 9 — computed `+HEARTBEAT_FANOUT_S = COST_S["heartbeat"] * (1 + SLOTS_PER_CHIP)`; recorded `+    assert HEARTBEAT_FANOUT_S / 5e-6 == 1 + SLOTS_PER_CHIP`
- 70% — computed `+OPEN_LOAD = 0.7`
- 30 µs (log write) — computed `+LOG_WRITE_S = 30e-6`; recorded `+    assert abs(LOG_WRITE_S * 1e6 - 30) < 1e-9`
- 20 µs (Merkle root) — computed `+MERKLE_S = 20e-6`; recorded `+    assert abs(MERKLE_S * 1e6 - 20) < 1e-9`
- 576 GPUs — computed `pol.governors * SLOTS_PER_CHIP * horizon`; recorded `+    assert PLAN_OF_RECORD.governors * SLOTS_PER_CHIP == 576`
- 30 s — `measure(pol, horizon: float = 30.0)`
- 34,273,417 — computed `sum(c.tokens ...)` in `run_one`; recorded `+    assert abs(r["tokens_governed"] / 34_273_417 - 1) < 1e-3`
- 34,278,595 — recorded `+    assert abs(r["tokens_baseline"] / 34_278_595 - 1) < 1e-3`
- 0.017% — computed `stall_pct`; recorded as 0.0168 `+    assert abs(r["stall_pct"] - 0.0168) < 0.002`
- 3337 ms — computed `pct(open_g["lat"], 0.99)`; recorded `+    assert abs(r["p99_latency_s"] * 1e3 - 3337) < 20`
- 3291 ms — recorded `+    assert abs(r["p99_latency_base_s"] * 1e3 - 3291) < 20`
- 66.5 ms — computed `pct(open_g["waits"], 0.99)`; recorded `+    assert abs(r["p99_receipt_wait_s"] * 1e3 - 66.5) < 3`
- 67 ms (idle-core bound) — computed `(p.window_s+SIGN_S)*1e3` in `main()`; recorded `+    assert abs(r0["max_receipt_wait_s"] * 1e3 - 67.0) < 0.5`
- 68.4 ms — computed `max(open_g["waits"])`; recorded `+    assert abs(r["max_receipt_wait_s"] * 1e3 - 68.4) < 1`
- 67.0 ms — recorded `+    assert abs(r0["max_receipt_wait_s"] * 1e3 - 67.0) < 0.5`
- 28.5% — computed `engine_util_pct`; recorded `+    assert abs(r["engine_util_pct"] - 28.5) < 1.5`
- 50 (engine limit) — recorded `+    assert r["engine_util_pct"] < 50.0`
- 0.21% — computed `fw_util_pct`; recorded `+    assert abs(r["fw_util_pct"] - 0.209) < 0.02`
- 1.4 ms — computed `max_receipt_wait` with vs without edition change; recorded `+    assert 0 < r["max_receipt_wait_s"] - r0["max_receipt_wait_s"] < 0.005`
- 18 ms — computed `edition_firmware_s()`; recorded `+    assert abs(ed * 1e3 - 18) < 1.0`
- 5 ms — recorded via `... < 0.005` (above)
- 0.0151% — recorded `+    assert abs(r["overhead_pct"] - 0.0151) < 0.002`
- 0.0168% — recorded `+    assert abs(r["stall_pct"] - 0.0168) < 0.002`
- 0.003 (points) — recorded `+    assert abs(r["overhead_pct"] - r["stall_pct"]) < 0.003`
- 10 s — `sweep_actions(..., horizon: float = 10.0)` / `sweep_window_held(horizon=10.0)` / `sensitivity(horizon=10.0)`
- 80 calls — `+    r = measure(replace(PLAN_OF_RECORD, actions_per_response=80), 10.0, 2.0)`; in `expect = {... 80: 1.45 ...}`
- 1.71% — NOT FOUND as asserted (only in comment `# 1.71 against 1.45 at 10 s`; test asserts only `abs(overhead-stall) < 0.35`)
- 1.45 — recorded `+    expect = {0.05: 0.02, 5: 0.11, 20: 0.38, 40: 0.73, 80: 1.45, 160: 3.01}`
- 0.02, 0.11, 0.38, 0.73, 3.01 — recorded in the same `expect` dict (via `sweep_actions`)
- 55 — computed by `crossing(pts)`, printed `c:.0f`; recorded only as a range `+    assert 40 < c < 70, c`
- 1,100x — computed `mult = round(c / p.actions_per_response / 100) * 100`; recorded `+    assert mult == 1100, mult`
- 0.05 (reference) — `+ACTIONS_PER_RESPONSE = 50 / 1000`
- 30 s / 10 s (table vs sweep) — `measure` default 30.0 vs sweep default 10.0
- 20, 30, 50, 100, 200 (windows) — `+WINDOW_AXIS = (0.020, 0.030, 0.050, 0.100, 0.200)`; recorded in `test_slot_held_table_in_docs_12` `expect`
- 9.9, 11.4, 14.3, 21.2, 32.9 — recorded `+    expect = {0.020: 9.9, 0.030: 11.4, 0.050: 14.3, 0.100: 21.2, 0.200: 32.9}`
- 17 ms signature (serviceable) — `self.window_s > SIGN_S`
- 0.13% — computed in `sensitivity()`; recorded `+    for name, e in {"log write 10x": 0.134, "merkle root 10x": 0.025, "heartbeat 10x": 0.025}.items():`
- 0.02% (Merkle, heartbeat) — recorded via the same `0.025` entries
- 70% load (section 4) — `+OPEN_LOAD = 0.7`
- "one a second under two percent" — recorded `+    assert ed / HEARTBEAT_PERIOD_S * 100 < 2.0`
- per-port 1 ms (section 4) — NOT FOUND (imported `COST_S["switch_program"]`)
- 72 chips (section 4) — `+GOVERNORS = 72`
