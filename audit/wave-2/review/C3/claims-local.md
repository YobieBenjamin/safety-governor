Claims:

1. Revision 2 is committed as 2f7579a and not pushed. — NOT FOUND (git metadata, not in diff).
2. `make bench` and the 8 tests in `tests/test_hybrid_signature.py` pass. — 8 tests: `+++ b/tests/test_hybrid_signature.py` / `index 0000000..44195d2` (new file with `test_hybrid_costs_both_signatures`, `test_hybrid_utilisation_matches_sign_time_over_window`, `test_hybrid_at_the_classical_window_does_not_keep_up`, `test_hybrid_window_keeps_engine_under_100_percent`, `test_hybrid_holds_under_pessimistic_ml_dsa_cost`, `test_a_window_under_one_second_exists_by_search`, `test_under_one_second_disproof_has_headroom_and_its_latency_cost`, `test_verdict_text_is_computed_and_carries_the_caveat`); "pass" itself NOT FOUND.
3. I ran the acceptance command twice, first run's output only read from its background file. — NOT FOUND.
4. I ran no other test suite. — NOT FOUND.
5. The 10M-cycle ML-DSA-65 figure is still unsourced. — `+MLDSA65_SIGN_CYCLES = 10_000_000           # UNVERIFIED placeholder: Cortex-M4 pqm4 ML-DSA-65 sign, mean; no checked source`
6. The model still carries it, flagged as an unverified placeholder (`govsim/bench.py:41-48`). — `+# UNVERIFIED PLACEHOLDER: the 10,000,000 figure has NO checked source at revision 1 (no web access). It is from`
7. I cut every derived number from `docs/04-specification.md:245` (117 ms, 234, 47, 367, ~13 percent slack) along with the spec threshold. — NOT FOUND as a removal (diff adds one row, no removed line); resulting row: `+... so this row states no cycle count, utilisation or latency: `
8. The row now says the constant is not a spec figure. — `+**That constant has no checked source and is not a spec figure**, so this row states no cycle count, utilisation or latency: `
9. ...its threshold cell reads "to be set after the cycle count is sourced or measured". — `+... | to be set after the ML-DSA-65 cycle count on OTBN is sourced or measured (Phase 2) |` (exact wording differs).
10. The verdict is now computed from the run in the new `hybrid_report()` (`govsim/bench.py`). — `+def hybrid_report(h: dict) -> str:` / `+    """The hybrid line of ``make bench``. Every verdict word is computed from the run, none is fixed text."""`
11. It prints "cannot keep up", "keeps up", "did not hold" or "HOLDS: a second engine is needed" from the utilisation values. — `+    keeps_up = lambda u: "keeps up" if u < 100.0 else "cannot keep up"` and `+            f"Disproof {'did not hold' if holds else 'HOLDS: a second engine is needed'}: "`
12. ...adds the caveat only while `MLDSA65_COST_SOURCED` is False. — `+            f"{'' if MLDSA65_COST_SOURCED else ', conditional on the unverified ML-DSA figure'}. "`
13. I removed the claim that verification and session setup are off the engine. — NOT FOUND as a removal; new wording `+            f"Only signing is counted; other uses of the engine are not modelled.")`
14. The bench line and the docs row now say only that signing is counted and other uses of the engine are not modelled. — `+            f"Only signing is counted; other uses of the engine are not modelled.")` and `+... Only signing is counted; other uses of the engine are not modelled. |`
15. `test_a_window_under_one_second_exists_by_search` now scans windows from 10 ms to 990 ms. — `+    windows = [w / 100.0 for w in range(1, 100)]`
16. It asserts that one works. — `+    assert ok, "disproof: no window under one second keeps the engine under 100 percent"`
17. ...the shortest sits just above the combined sign time. — `+    assert min(ok) > HYBRID_SIGN_S` / `+    assert min(ok) - HYBRID_SIGN_S < 0.01`
18. ...and that 250 ms is among them. — `+    assert HYBRID_BATCH_WINDOW_S in ok` (with `+HYBRID_BATCH_WINDOW_S = 0.25`)
19. The 2x slack is now computed from the formula. — `+    assert 100.0 - util == pytest.approx(100.0 - 100.0 * sign / HYBRID_BATCH_WINDOW_S)`
20. A new test pins utilisation and latency to sign time over window. — `+def test_hybrid_utilisation_matches_sign_time_over_window():` / `+    assert r["hybrid_engine_utilization_pct"] == pytest.approx(100.0 * HYBRID_SIGN_S / HYBRID_BATCH_WINDOW_S)`
21. ...which are the figures `make bench` prints. — `+    # window-limited, so utilisation is sign time over window; the bench's printed figures are these values` / `+    print(hybrid_report(run("rack")))`
22. The 8x test now also checks record latency, which exceeds 1 s there. — `+    w, k = 0.999, 8.0` / `+    assert r["hybrid_record_latency_s"] > 1.0`
23. I removed the false "recorded in docs/04" comment. — NOT FOUND as a removal (new file); replacement `+    # window-limited, so utilisation is sign time over window; the bench's printed figures are these values`
24. I replaced the test that asserted `MLDSA65_COST_SOURCED is False` with `test_verdict_text_is_computed_and_carries_the_caveat`. — `+def test_verdict_text_is_computed_and_carries_the_caveat():` (old test NOT FOUND)
25. It checks the printed text. — `+    text = hybrid_report(r)` / `+    assert "did not hold" in text and "cannot keep up" in text and "keeps up" in text`
26. ...and that a 1.5 s signature flips the verdict. — `+    bad = run("rack", hybrid_sign_s=1.5)` / `+    assert bad["hybrid_engine_utilization_pct"] > 100.0`
27. The 250 ms window is still a modelling choice with no latency target behind it. — `+HYBRID_BATCH_WINDOW_S = 0.25               # window, under 1 s, that keeps the single engine under 100 percent; must exceed HYBRID_SIGN_S` ("no latency target" NOT FOUND)
28. At 2x ML-DSA cost it leaves little slack, which the test records. — `+    assert 100.0 - util < 20.0, "the chosen window is tight at 2x; widen it if this stops being so"`
29. Widening it is a spec decision. — NOT FOUND.
30. I did not add a committed artifact for the bench numbers; `make bench` and the tests are the record. — NOT FOUND.
31. Someone with web access needs to check the pqm4 ML-DSA-65 sign cycle count and the Cortex-M4 to OTBN scaling. — `+# memory of the pqm4 tables and MUST be re-checked against the current pqm4 release, with the M4->OTBN scaling,`
32. After that, set `MLDSA65_COST_SOURCED = True` and restore the spec row. — NOT FOUND.
33. (rev2 commit) "cut the unsourced figures from the spec row". — `+... so this row states no cycle count, utilisation or latency: ` (removal NOT FOUND)
34. (rev2 commit) "compute the bench verdict". — `+def hybrid_report(h: dict) -> str:`
35. (rev2 commit) "search windows in the test". — `+    windows = [w / 100.0 for w in range(1, 100)]`
36. (rev2 commit) "computed slack and latency checks". — `+    assert 100.0 - util == pytest.approx(100.0 - 100.0 * sign / HYBRID_BATCH_WINDOW_S)` / `+    assert r["hybrid_record_latency_s"] > 1.0`
37. (rev1 commit) "mark the ML-DSA-65 figure an unverified placeholder". — `+MLDSA65_SIGN_CYCLES = 10_000_000           # UNVERIFIED placeholder: Cortex-M4 pqm4 ML-DSA-65 sign, mean; no checked source`
38. (rev1 commit) "make the disproof verdict conditional". — `+            f"{'' if MLDSA65_COST_SOURCED else ', conditional on the unverified ML-DSA figure'}. "`
39. (rev1 commit) "label MLDSA65_SIGN_CYCLES an UNVERIFIED placeholder (MLDSA65_COST_SOURCED=False) with the re-check pointer". — `+MLDSA65_COST_SOURCED = False               # no checked source at revision 1; re-check pqm4 + M4->OTBN scaling before relying`
40. (rev1 commit) "drop the unsourced 'neutral to slightly pessimistic / no Keccak' scaling rationale and state 1.0x as an unverified assumption". — rationale drop NOT FOUND; `+# Scaling assumption (UNVERIFIED, 1.0x): the M4 count is assumed equal on the OTBN-class engine. This is an`
41. (rev1 commit) "point 'OTBN has no ML-DSA' at the in-repo docs". — `+... ML-DSA is not in Earl Grey silicon and no OTBN-specific measured cycle count is in the repo (§7, docs/08, docs/18 §9).` / `+# repo (docs/04 §7, docs/08, docs/18 §9: a future OpenTitan release or a software implementation, cost measured in`
42. (rev1 commit) "the hybrid line now flags the placeholder". — `+    src = "sourced" if MLDSA65_COST_SOURCED else "UNVERIFIED placeholder, no checked source; re-check pqm4 and the M4->OTBN scaling"`
43. (rev1 commit) "notes signing-only scope (tickets are a firmware path; verification and session setup are not on the engine)". — "verification and session setup are not on the engine" NOT FOUND (reversed); final `+            f"Only signing is counted; other uses of the engine are not modelled.")`
44. (rev1 commit) "states 'disproof did not hold' conditional". — `+            f"Disproof {'did not hold' if holds else 'HOLDS: a second engine is needed'}: "`
45. (rev1 commit) "fix the 1.0 s window to the modelled 0.25 s window (genuinely under 1 s)". — `+HYBRID_BATCH_WINDOW_S = 0.25               # window, under 1 s, that keeps the single engine under 100 percent; must exceed HYBRID_SIGN_S` / `+    assert HYBRID_BATCH_WINDOW_S < 1.0`
46. (rev1 commit) "widen the tautological both-signatures test to check run() charges both". — `+def test_hybrid_costs_both_signatures():` / `+    assert r["hybrid_engine_utilization_pct"] > r["engine_utilization_pct"]`
47. (rev1 commit) "record the tight 2x slack". — `+    assert 100.0 - util < 20.0, "the chosen window is tight at 2x; widen it if this stops being so"`
48. (rev1 commit) "the 8x headroom on the 1 s boundary". — `+def test_under_one_second_disproof_has_headroom_and_its_latency_cost():` / `+    w, k = 0.999, 8.0`
49. (rev1 commit) "a test that the result is conditional on the unsourced figure". — `+    if not MLDSA65_COST_SOURCED:` / `+        assert "conditional on the unverified" in text`
50. (rev1 commit) "docs/04 §9: record the 250 ms / 47% / 367 ms result durably". — 47% / 367 ms NOT FOUND in docs/04 (row states no figures); `+... this row states no cycle count, utilisation or latency: `
51. (rev1 commit) "the placeholder" (recorded in docs/04). — `+**That constant has no checked source and is not a spec figure**, so this row states no cycle count, utilisation or latency: `
52. (rev1 commit) "the scaling assumption" (recorded in docs/04). — `+... and an assumed 1.0x scaling to OTBN.`
53. (rev1 commit) "the 2x tail caveat" (recorded in docs/04). — NOT FOUND in docs/04 row (only in bench.py `+# the tests (a 2x factor standing in for it -- an assumption, not a measurement)`).
54. (rev1 commit) "and the signing-only scope" (recorded in docs/04). — `+... Only signing is counted; other uses of the engine are not modelled. |`
55. (initial commit) "hybrid P-384 + ML-DSA-65 signature cost in the batching model". — `+HYBRID_SIGN_S = SIGN_S + MLDSA65_SIGN_S    # both signatures per batch, one engine: 117 ms`
56. (initial commit) "bench reports hybrid engine utilisation". — `+            "hybrid_engine_utilization_pct": 100.0 * hybrid_batched * hybrid_sign_s / gpu_s if gpu_s else 0.0,`
57. (initial commit) "tests". — `+++ b/tests/test_hybrid_signature.py` / `index 0000000..44195d2`

Numbers in changed documents (numbers literally in the diff's added content; "where computed or recorded"):

- 1.0x — assumption, not computed: `+# Scaling assumption (UNVERIFIED, 1.0x): the M4 count is assumed equal on the OTBN-class engine. This is an`; docs/04 `+... an assumed 1.0x scaling to OTBN.`
- 50 (ms) — classical window, recorded as constant: `BATCH_WINDOW_S = 0.05` (context, unchanged); docs/04 `+... so the 50 ms window of the classical row cannot hold it`.
- 100 (percent) — threshold: `+    keeps_up = lambda u: "keeps up" if u < 100.0 else "cannot keep up"`; docs/04 `+... keeps the single engine under 100 percent`.
- Phase 2 — text label, not a computable number: `+... cost measured in` / `+# Phase 2)`; docs/04 `+... (Phase 2) |`.
- 10,000,000 / "10 million" — recorded unverified constant (not computed): `+MLDSA65_SIGN_CYCLES = 10_000_000           # UNVERIFIED placeholder`; comment `+# cycles on average.`
- 2x — recorded assumption: `+# the tests (a 2x factor standing in for it -- an assumption, not a measurement), not by this constant.`; in test `+HYBRID_PESSIMISM = 2.0`.
- 100 (ms) — computed: `+MLDSA65_SIGN_S = MLDSA65_SIGN_CYCLES / OTBN_CLOCK_HZ    # 100 ms` (10_000_000 / 100e6 = 0.1 s).
- 117 (ms) — computed: `+HYBRID_SIGN_S = SIGN_S + MLDSA65_SIGN_S    # both signatures per batch, one engine: 117 ms` (0.017 + 0.1 = 0.117 s).
- 0.25 — recorded constant: `+HYBRID_BATCH_WINDOW_S = 0.25               # window, under 1 s, that keeps the single engine under 100 percent; must exceed HYBRID_SIGN_S`.
- 1.0 (s) — threshold, recorded: `+    holds = HYBRID_BATCH_WINDOW_S < 1.0 and win < 100.0`; test `+    assert HYBRID_BATCH_WINDOW_S < 1.0`.
- printed batch ms `{HYBRID_SIGN_S*1e3:.0f}` — computed in `hybrid_report`: `+    return (f"hybrid (P-384 + ML-DSA-65, both per batch): {HYBRID_SIGN_S*1e3:.0f} ms per batch ...`.
- printed cycle count `{MLDSA65_SIGN_CYCLES:,}` — recorded constant formatted: `+            f"Cortex-M4 pqm4 figure, {src}; OTBN 1.0x assumed); engine {base:.0f}% at the {BATCH_WINDOW_S*1e3:.0f} ms window "`.
- printed base-window pct `{base:.0f}%` — computed: `+    base, win = h["hybrid_engine_utilization_at_base_window_pct"], h["hybrid_engine_utilization_pct"]` from `+            "hybrid_engine_utilization_at_base_window_pct": 100.0 * sig_batched * hybrid_sign_s / gpu_s if gpu_s else 0.0,`.
- printed window pct `{win:.0f}%` — computed from `+            "hybrid_engine_utilization_pct": 100.0 * hybrid_batched * hybrid_sign_s / gpu_s if gpu_s else 0.0,`.
- printed window ms `{HYBRID_BATCH_WINDOW_S*1e3:.0f}` — recorded constant formatted: `+            f"({keeps_up(base)}) -> {win:.0f}% at a {HYBRID_BATCH_WINDOW_S*1e3:.0f} ms window ({keeps_up(win)}); "`.
- printed record latency ms `{h['hybrid_record_latency_s']*1e3:.0f}` — computed: `+            "hybrid_record_latency_s": hybrid_window_s + hybrid_sign_s,`.
- 1e-12, 1e-9 — tolerances, recorded: `+    assert abs(HYBRID_SIGN_S - (SIGN_S + MLDSA65_SIGN_S)) < 1e-12` / `+               - 100.0 * r["hybrid_signatures_batched"] * HYBRID_SIGN_S / r["gpu_seconds"]) < 1e-9`.
- 100.0 — threshold, computed/recorded: `+    assert r["hybrid_engine_utilization_at_base_window_pct"] > 100.0, r` / `+    assert r["hybrid_engine_utilization_pct"] < 100.0, r`.
- 0.01 — tolerance, recorded: `+    assert min(ok) - HYBRID_SIGN_S < 0.01`.
- 10 ms to 990 ms — computed by search: `+    windows = [w / 100.0 for w in range(1, 100)]`.
- 0.999, 8.0 — recorded constants: `+    w, k = 0.999, 8.0`.
- 1.0 (latency) — threshold: `+    assert r["hybrid_record_latency_s"] > 1.0` / `+    assert r["hybrid_record_latency_s"] == pytest.approx(w + sign)`.
- 20.0 — threshold, recorded: `+    assert 100.0 - util < 20.0, "the chosen window is tight at 2x; widen it if this stops being so"`.
- 1.5 — recorded: `+    bad = run("rack", hybrid_sign_s=1.5)`.
- computed slack `100.0 - 100.0 * sign / HYBRID_BATCH_WINDOW_S` — computed: `+    assert 100.0 - util == pytest.approx(100.0 - 100.0 * sign / HYBRID_BATCH_WINDOW_S)` (≈13% at 2x).
- utilisation `100.0 * HYBRID_SIGN_S / HYBRID_BATCH_WINDOW_S` — computed: `+    assert r["hybrid_engine_utilization_pct"] == pytest.approx(100.0 * HYBRID_SIGN_S / HYBRID_BATCH_WINDOW_S)` (≈46.8%, i.e. ~47%).
- 117 ms, 234, 47, 367, ~13 percent slack (cited in summary as cut from docs/04:245) — NOT FOUND as literals in the diff; 117 computed at `+HYBRID_SIGN_S = SIGN_S + MLDSA65_SIGN_S    # both signatures per batch, one engine: 117 ms`; 234 = base-window pct `+            "hybrid_engine_utilization_at_base_window_pct": 100.0 * sig_batched * hybrid_sign_s / gpu_s if gpu_s else 0.0,` (100·0.117/0.05); 47 = `+    assert r["hybrid_engine_utilization_pct"] == pytest.approx(100.0 * HYBRID_SIGN_S / HYBRID_BATCH_WINDOW_S)`; 367 = `+            "hybrid_record_latency_s": hybrid_window_s + hybrid_sign_s,` (0.25+0.117=0.367 s); ~13% = `+    assert 100.0 - util == pytest.approx(100.0 - 100.0 * sign / HYBRID_BATCH_WINDOW_S)` at 2x.
