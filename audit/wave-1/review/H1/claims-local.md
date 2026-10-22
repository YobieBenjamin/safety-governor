**Claims (summary + commit messages)**

1. Revision 2 committed on `exp/h1`, `make lanes` passes after the last commit — NOT FOUND (diff shows the target but no record of it passing).
2. "Ran it once this revision and haven't pushed" — NOT FOUND.
3. `lanes/audit.py` deleted — NOT FOUND (no deletion in this diff).
4. Nothing imported `audit.py`; its "mirrors `hardware_ref` byte for byte" claim unsupported — NOT FOUND.
5. Audit chain logic now lives in `chain_ok` in `lanes/check.py` — `+def chain_ok(audit: dict) -> bool:`
6. Old edit check compared a hash that never included the previous head, so it could not fail — NOT FOUND (old code not in diff).
7. Replaced with two checks on an edited copy and a deleted copy, both detected — `+    check("audit record: editing an entry is detected", not chain_ok(broken))` and `+    check("audit record: deleting an entry is detected", not chain_ok(cut))`
8. All five signed fixtures go through govsim `verify_object` via an adapter; a tampered copy of each is rejected — `+        check(f"govsim: verifies {name} under the {signer} key", C.verify_object(adapted, vk))` and `+        check(f"govsim: rejects a tampered {name}", not C.verify_object(adapted, vk))` (over the 5-tuple `for name, signer in (...)`).
9. The check now makes 54 `ok` lines without `--hardware` — NOT FOUND (no `54` anywhere in the diff).
10. `EXPERIMENTS.md` no longer names `tests/test_catalogue_data.py` as on the branch; says it exists only inside the hardware patch — `+- `patches/safety/lanes.patch` and `patches/hardware-and-silicon/lanes.patch` are diffs in git format: a CI workflow in each, a `tests/test_catalogue_data.py` that exists only inside the hardware patch, and ...`
11. The safety workflow's CI step is now one `run:` line — `++      - run: cd ../safety-governor && python3 -m lanes.check --observer "$GITHUB_WORKSPACE/observer"`
12. Cross-repository failure is not demonstrated; needs patches applied and branch merged (workflows clone `main`); notes say so — `+- Not demonstrated, stated plainly: that a format change in one repository fails the other's build. It needs the patches applied and this branch merged (the workflows clone `main`).`
13. `git apply --check` was not run (shell approvals denied) — `+... They are not applied, and `git apply --check` was not run against those repositories (this run could not).`
14. The pin in `safety`'s `test_contract.py` stays a literal until `patches/safety/lanes.patch` is applied — evidenced by the patch's removed literal `+-GATE_SUBJECT = "c2daf12eb9a1654349e8c5715220d89e4b87c3ce0f6d854251b035aba1dc58ae"` (the unapplied state).
15. The pin in `lanes/generate.py` stays a literal on purpose, so one canonicalisation change cannot move both sides — `+PINNED_SUBJECT = "c2daf12eb9a1654349e8c5715220d89e4b87c3ce0f6d854251b035aba1dc58ae"` and `+# canonicalisation cannot move both sides at once.`
16. `govsim` has no catalogue code; `hardware_ref` can't be edited from here; `attacks.json` is exported from and compared against `hardware_ref`, not read by it — `+"""Write catalogue/attacks.json from hardware_ref/attacks.py (the source of truth for the entries today).` and `+    from hardware_ref.attacks import CATALOGUE` and `+    python3 catalogue/export.py ../hardware-and-silicon --check    # fail if attacks.json differs from the live catalogue`.
17. `AuditLog.verify_export` runs under `make lanes` but not under `tests/test_lanes.py`; a skip-when-missing test would break the no-skipping rule — `+    r = subprocess.run([sys.executable, "-m", "lanes.check"], capture_output=True, text=True)` (no `--hardware`) and `+... hardware_ref's `AuditLog.verify_export` runs under `make lanes` (`--hardware`), not under `tests/test_lanes.py`.`
18. The govsim/contract envelope-shape difference remains a recorded gap, not a native check — `+- Known gap: govsim's envelope differs from the contract (16-hex signer, hex signature, no embedded pub).`
19. (Open question) whether `safety-governor` should get its own `make lanes` CI step; not added because it needs sibling clones — NOT FOUND (a question; no evidence in diff).
20. Launcher commit: "work left uncommitted by the agent, committed by the launcher" — NOT FOUND (meta).
21. (C1) audit tamper checks that can fail — `+    check("audit record: editing an entry is detected", not chain_ok(broken))`.
22. (C1) every signed fixture through govsim — `+    for name, signer in (("observer-assertion.json", "obs-main"), ...)` loop.
23. (C1) dead `audit.py` removed — NOT FOUND.
24. (C1) notes and one-line CI step corrected — EXPERIMENTS.md `+` lines and `++      - run: cd ../safety-governor && python3 -m lanes.check --observer ...`.
25. (C3) applyable git diffs for safety and hardware-and-silicon — `+diff --git a/.github/workflows/lanes.yml b/.github/workflows/lanes.yml` (patch files exist), but "applyable" is NOT FOUND (unverified; `git apply --check` not run).
26. (C3) CI workflow — `+diff --git a/.github/workflows/lanes.yml ...` in both patches.
27. (C3) shared pin — `++GATE_SUBJECT, GATE_CANONICAL_CORE = _PIN["subject"], _PIN["canonical_core"]` with `++_PIN = json.loads((_LANES / "fixtures" / "request.json").read_text())`.
28. (C3) catalogue test — `++def test_catalogue_matches_shared_data():` in `patches/hardware-and-silicon/lanes.patch`.
29. (C3) notes corrected — EXPERIMENTS.md `+` lines.
30. (C4) audit fixture chains from the reference genesis — `+GENESIS = bytes.fromhex(E.sha256_hex(b"audit-genesis"))` and `+    head, good = bytes.fromhex(E.sha256_hex(b"audit-genesis")), True`.
31. (C4) run through `AuditLog.verify_export` — `+    rep = AuditLog.verify_export(audit)`.
32. (C4) scratch script removed — NOT FOUND.
33. (C4) `make lanes` fails when a repository is missing — `+	@test -n "$(SAFETY)" || { echo "lanes: the safety repository was not found; set SAFETY=<path>"; exit 1; }`.
34. (C6) signed fixtures — e.g. `+  "sig": "i4cjpiK3gCe2em0kuPnTIaKCKNkBkBzNeb9ByRCir1SxNgGkkg4nQ6Ksv9R3rcW3+O8m2xgvU7hKwL8gRMLiAQ==",` in `lanes/fixtures/observer-assertion.json`.
35. (C6) conformance checker — `+"""Lanes conformance checker.` in `lanes/check.py`.
36. (C6) catalogue as data — `+"""The attack and baseline catalogue as data.` in `catalogue/__init__.py`.
37. (C6) `make lanes` — `+lanes:` target in `Makefile`.

**Numbers in changed documents**

- 75 (attacks) — recorded in `catalogue/attacks.json` `"attacks": 75` and `EXPERIMENTS.md` `(75 attacks)`; computed in `catalogue/export.py` `sum(e["expect"] == "blocked" for e in entries)`; asserted in `tests/test_lanes.py` `assert len(catalogue.names("blocked")) == 75`.
- 12 (baselines) — recorded in `catalogue/attacks.json` `"baselines": 12` and `EXPERIMENTS.md` `(12 baselines)`; computed in `catalogue/export.py` `sum(e["expect"] == "allowed" for e in entries)`; asserted in `tests/test_lanes.py` `== 12`.
- 16 (in "16-hex signer") — recorded in `EXPERIMENTS.md` and `lanes/check.py` comment; computed in `lanes/envelope.py` `return hashlib.sha256(pub_raw).digest()[:8].hex()` (8 bytes → 16 hex chars).
- 13 (issue id) — recorded in `EXPERIMENTS.md` `## H1 (#13)`; not computed (issue reference).
- 34, 0.1 (`34 percent engine utilisation ... under 0.1 percent firmware share`, N1 row) — pre-existing context line, NOT added by this diff; computation is in `govsim/deploy.py`, NOT FOUND in this diff.
- `exit 1` (×2) — Makefile guards `+	@test -n "$(SAFETY)" || { ...; exit 1; }` and the `$(HW)` guard.
- 3 (`python3`, ×2) — Makefile `+	python3 -m lanes.check ...` and `+	python3 catalogue/export.py ...`.
- `catalogue/attacks.json` description-text numbers (recorded as prose, NOT computed in diff): 0.95 (`L3.observer_high_risk`, `NV.sentry_drift_quarantine`, `NV.dual_witness_sentry_high`), 0.3 (`L3.observer_high_risk`), 250 and 250000 USD (`EP.ticket_param_swap`), 900 and 2,000 USD (`TX.budget_exhausted`), 40 and 2,000 USD and "more than 8" (`TX.concurrent_overspend`), 25,000 USD (`TX.risk_label_ignored`), "60 s" and "limit is 3" (`L4.rate_limit_burst`), "fifth" (`NV.repeated_denials_quarantine`).
- `catalogue/export.py`: `indent=1`; `75`/`12` via `sum(...)` in `document()`; `return 1` / `return 0`.
- `lanes/envelope.py`: `8` (the `[:8]` slice in `key_id`).
- `lanes/generate.py`: `1800000000.0` (`NOW`), `16` (`"ab" * 16`, `[:16]` policy_id), `12.5`, `0.5`, `1000`, `60`, `3600`, `3`, `5`, `300`, `0.12`, `TICKET_ID = "00112233445566778899aabbccddeeff"`, byte prefixes `b"\x00"`/`b"\x01"`.
- `lanes/check.py`: `1`/`0` in `return 1 if FAILS else 0`, `0.99` (tampered risk), `9999` (`amount=9999`), `2` (`broken["entries"][0]["record"]["rules"] = 2`), `+1` and `0` in expiry tampers (`expires_at + 1`, `.get("expires_at", 0) + 1`), `0 <= p["risk"] <= 1`.
- `lanes/fixtures/keys.json`: 16-hex signer ids (`"6bc61058f6dd43a4"`, `"0117838d8b06a514"`, `"3dd4eb68f25c4e34"`, `"3cda73124afab04f"`, `"fd955b09cebc9d33"`, `"15819035db6bc230"`) plus seeds/pubs.
- `lanes/fixtures/request.json`: `1800000000.0`, `12.5`, subject/core hashes.
- `lanes/fixtures/observer-assertion.json`: `1800000060.0`, `1800000000.0`, `0.12`.
- `lanes/fixtures/provenance-assertion.json`: `1800000300.0`, content_digest.
- `lanes/fixtures/attestation-token.json`: `1800000300.0`, `svn 3`, `svn 5`.
- `lanes/fixtures/action-ticket.json`: `1800000060.0`, `1800000000.0`, `ticket_id` hex, `params_digest`, `request_hash`.
- `lanes/fixtures/policy-image.json`: `3600`, `60`, `1000`, `0.5`.
- `lanes/fixtures/audit-record.json`: `size 2`, ts `1800000000.0`/`1800000001.0`/`1800000002.0`, `rules 1`, head/root/entry hashes.
- `lanes/fixtures/content.json`: none.
- `patches/hardware-and-silicon/lanes.patch`: `@v4`, `--depth 1`, hunk `@@ -0,0 +1,10 @@`, `parents[2]`.
- `patches/safety/lanes.patch`: `@v4`, `--depth 1`, hunks `@@ -0,0 +1,8 @@`, `@@ -6,3 +6,7 @@`, `@@ -17,7 +21,5 @@`, `parents[3]`, removed literal `"c2daf12...58ae"` and `12.5` in the removed `GATE_CANONICAL_CORE`.
- `tests/test_lanes.py`: `75`, `12`.

Note: the summary's claim of **54** `ok` lines (claim 9) and the **deletion of `lanes/audit.py`** (claims 3, 23) and **scratch script removed** (claim 32) have no corresponding line in this diff.
