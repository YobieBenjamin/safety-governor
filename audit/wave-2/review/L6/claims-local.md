**Claims (summary + commit messages)**

1. Agent summary — no claims; the summary block is empty.
2. The agent left work uncommitted and the launcher committed it. — NOT FOUND (the diff adds `govsim/mutants.py` as a new file; no line records commit provenance).
3. The agent ended by cap, timeout, or its own stop. — NOT FOUND.
4. The files are committed "as found" (untouched by the launcher). — NOT FOUND.
5. The commit exists so the gate can judge the files and a revision can continue from them. — NOT FOUND.
6. "nothing here is claimed to pass." — NOT FOUND as positive evidence; the diff asserts no passing state (`+    The gate passes only when no check-removing mutant survives.` describes the criterion, not a pass).
7. The agent was "wave 2." — NOT FOUND.
8. The work is "issue #6." — `L6` appears (`+"""L6: mutation testing as a standing gate.`, `+    ap = argparse.ArgumentParser(description="L6 mutation gate")`); the literal "#6" is NOT FOUND.

**Numbers in the changed document (`govsim/mutants.py`)**

1. `423` / `0,0` / `1` — `@@ -0,0 +1,423 @@` — recorded by the diff header (added-line count); not computed in the file.
2. `second` (2) — `+The second audit found and fixed twenty surviving mutants by hand.` — recorded in prose; computation NOT FOUND.
3. `twenty` (20) — `+The second audit found and fixed twenty surviving mutants by hand.` — recorded in prose (prior-audit count); computation NOT FOUND.
4. `Three` (3) — `+Three mutant classes, each a single change to one file:` — recorded in prose; reflected by `_check_sites`/`_flip_sites`/`_log_sites` and the 3-tuple loop in `to_lines`; count not computed.
5. `one`/`single` (1) — `+it walks the model's checks and, one at a time, removes a check, flips a comparison` — recorded in prose.
6. `four` (4) — `+             "One mutant at a time over the model's four files (\`govsim/governor.py\`, \`policy.py\`,"` and `+# The model the gate guards. These are the four files named in the L6 brief.` — recorded in prose; `+TARGETS = ("govsim/governor.py", "govsim/policy.py", "govsim/endpoints.py", "govsim/fabric.py")` lists 4; the 4 is not computed.
7. `80` — `+        return ast.unparse(call)[:80]` — recorded as a literal truncation width.
8. `70` — `+        return ast.unparse(node.test)[:70]` — recorded as a literal.
9. `60` — `+        return ast.unparse(stmt)[:60]` — recorded as a literal.
10. `20.0` — `+                                       cwd=str(copy_dir), capture_output=True, text=True, timeout=20.0)` — recorded as a literal timeout.
11. `120` — `+            return line.strip()[:120]` — recorded as a literal.
12. `1` — `+    if n <= 1:` — recorded as a literal threshold.
13. `1` — `+    per = (len(specs) + n - 1) // n` — computed in the chunk-size formula.
14. `0.0` — `+    seconds: float = 0.0` — recorded as a literal default.
15. `1`, `100`, `1`, `100.0` — `+        return round(sum(1 for m in real if m.status == "killed") / len(real) * 100, 1) if real else 100.0` — computed (`1` counts killed, `100` scales to percent, `1` is round precision, `100.0` is the no-mutants default).
16. `120.0` — `+def run(files=TARGETS, workers: int | None = None, timeout: float = 120.0,` — recorded as a literal default.
17. `8`, `1` — `+    n = workers or min(8, (os.cpu_count() or 1))` — recorded as literals (worker cap / cpu fallback).
18. `1`, `1` — `+    if n > 1 and len(specs) > 1:` — recorded as literal thresholds.
19. `2` — `+    rep = Report(out, seconds=round(time.time() - started, 2))` — computed (elapsed seconds, rounded to 2 places).
20. `0`, `0` — `+    ap.add_argument("--workers", type=int, default=0, help="parallel workers (0: auto)")` — recorded as literals (`default=0` and the "0: auto" in help).
21. `1`, `0` — `+        return 1 if not args.keep_surface else 0` — recorded as exit-code literals.
22. `0` — `+# a bare defensive return (``return []``, ``return 0``, ``return {}``, a normal` — recorded as a literal example in a comment.
23. `193` (turns), `0.0` (`$0.0` cost), `4` (exit code), `1` (attempt), `1` (commit), `2` (wave), `6` (#6), `18` (PR), `2026-10-21 19:45` (timestamp) — appear only in the run report / commit-message metadata; NOT FOUND in the diff (no changed document contains them).
