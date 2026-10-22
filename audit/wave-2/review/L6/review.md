## Review of `exp/l6`: **reject**

Verifier: 2 blocking finding(s); model review on ?: 4 blocking, 5 warnings, 5 unsupported claim(s) of 6; estimated $0.63, 5 turns.

### Reviewer's summary

The branch adds only govsim/mutants.py (423 lines). The acceptance file tests/test_mutants.py does not exist, so acceptance fails (exit 4).
No Makefile target, no results/mutants.md and no weekly CI job are in the diff, so every brief acceptance item except "a mutator exists" is missing.
The agent summary is empty and gives no evidence that the mutator has ever run or killed anything.
The mutator itself has gaps: GtE is never flipped (line 59), only single-statement refusal guards count as checks (lines 144-154), and any pytest ERROR line counts as a kill.
It is unproven that mutated copies are the code the tests import (suite run from the copy's cwd, tests path under ROOT).
Open question: this is a partial draft, not a gate. Redo it with the test, make target, report and CI, and with the mutator run against the real suite.

### Verifier findings

- [block] a file outside the issue's owned paths changed: `govsim/mutants.py`
- [block] the acceptance command fails in a clean checkout of the branch (exit 4): `python3 -m pytest -q tests/test_mutants.py`

### Reviewer findings

- [block] test_integrity at `govsim/mutants.py:52`: IGNORE refers to tests/test_mutants.py, the acceptance file, which is not in the diff or the checkout. The acceptance command exits 4 (file not found), per acceptance.log:1 and verify.json. Nothing tests the gate.
- [block] scope at `govsim/mutants.py:1`: The only change is a new file under govsim/, which the issue's owned paths do not include (verify.json scope finding). The brief's deliverables (make mutants target, results/mutants.md, weekly CI workflow, tests/test_mutants.py) are all absent from the diff.
- [block] unsupported_claim at `govsim/mutants.py:13`: The docstring says that `make mutants` writes results/mutants.md and that CI runs it weekly. No Makefile change, no report file and no workflow are in the diff, so the claim is not shown.
- [block] unsupported_claim at `govsim/mutants.py:323`: The report text claims results (killed/survived counts, a gate that fails the build) but no committed artifact shows a run. The acceptance criterion 'zero surviving check-removing mutants' has no evidence; summary.md is empty.
- [warn] correctness at `govsim/mutants.py:59`: _FLIP has the key 'Ge', but the ast class is 'GtE', so >= is never flipped. The docstring (line 21-22) promises the classic operators 'and the rest'. Coverage is silently smaller than described.
- [warn] correctness at `govsim/mutants.py:150`: _check_sites only treats an `if` with a single-statement refusal body and no else as a check. Multi-statement guards, `continue` or `break` guards and checks written as other constructs are never mutated, so 'zero surviving check-removing mutants' would be a weaker claim than the brief's. The reason for the narrow definition is not shown.
- [warn] correctness at `govsim/mutants.py:278`: Any output line containing 'ERROR' or 'FAILED' counts as a kill, and the fallback 'a test failed' covers any nonzero exit (collection errors, usage errors). A mutant that breaks collection is counted killed without a behavioural test failing, which can inflate the kill score. Nothing checks that the unmutated copy passes the suite in the same setup (a baseline).
- [warn] correctness at `govsim/mutants.py:270`: The suite is run with cwd=copy_dir but the tests path is ROOT/tests. Whether the tests import the mutated govsim copy or the real one at ROOT is not shown by any test. If it is the real one, every mutant would survive or the gate would be vacuous.
- [warn] correctness at `govsim/mutants.py:239`: Mutants that time out or fail to import are classed 'invalid' and excluded from the score (line 312). A check-removing mutant that hangs the suite is therefore never counted as a survivor, nor as killed.

### Claims

- NOT SUPPORTED (code): The second audit found and fixed twenty surviving mutants by hand (module docstring). (evidence: No artifact of the second audit is in the diff; origin of the number is not found.)
- NOT SUPPORTED (code): `make mutants` runs the gate and writes results/mutants.md; CI runs it weekly. (evidence: No Makefile, results/mutants.md or workflow in the diff.)
- NOT SUPPORTED (code): Three mutant classes (remove_check, flip, skip_log) are implemented, each a single change to one file. (evidence: _check_sites, _flip_sites and _log_sites exist at lines 144-174; the flip table is wrong for >= (line 59) and no test exercises them.)
- NOT SUPPORTED (code): The model is never mutated in place; each worker mutates a private copy. (evidence: _work_dir copies govsim to a temp dir (line 220-225); that the suite then imports the copy is not tested.)
- NOT SUPPORTED (code): The gate passes only when no check-removing mutant survives; the report states killed/survived counts. (evidence: gate()/main() return code from survivors (lines 395-425), but there is no run output, no report and no test in the diff.)
- NOT SUPPORTED (summary): Acceptance: python3 -m pytest -q tests/test_mutants.py passes. (evidence: acceptance.log: file or directory not found, exit 4. Summary is empty.)

### suite in a clean checkout: exit 0

```
........................................................................ [ 36%]
........................................................................ [ 72%]
........................................................                 [100%]
200 passed in 2.81s

```

### acceptance in a clean checkout: exit 4

```

ERROR: file or directory not found: tests/test_mutants.py


```
