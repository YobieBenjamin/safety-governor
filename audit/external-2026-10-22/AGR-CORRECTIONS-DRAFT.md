# Corrections for autonomic-graph-regulation, from the external audit of 22 October 2026 (draft)

These entries belong in `CORRECTIONS.md` of
[autonomic-graph-regulation](https://github.com/YobieBenjamin/autonomic-graph-regulation). They
are drafted here because the publishing pipeline that carries safety-governor and
hardware-and-silicon does not push that repository yet. Each one was checked against the
committed data at `4c1374d` before it was written down (`check_research.py` in this folder).
Copy them across as they stand; the reviewer is credited in each.

## C1. YB-0051: the pooled false-alarm rate hides a 13% rate on one task family

**Claim corrected.** The README reports C2 at a 1% false-alarm budget: 339 of 541 errors caught,
59 false alarms among 5,922 correct answers (0.996%).

**What the data also says.** 46 of those 59 false alarms fall on modular exponentiation: 46 of 352
correct modpow answers, 13.07%. The other families: weekday 8 of 986 (0.81%), mul_hard 5 of 1,047
(0.48%), count, mul_easy and add_hard none. With the threshold frozen on the reference data before
the test (307 caught, 44 false alarms, 0.743% pooled), modpow is still 41 of 352, 11.65%.

**Change.** Every operating point in this repository is reported per task family as well as
pooled, with the worst family named. A pooled rate alone is not a deployment number.

## C2. YB-0051: an output-only baseline nearly matches C2

**Claim corrected.** The README attributes the gain at 1% to combining self-disagreement with
non-LLM internal-state scores.

**What the data also says.** Four-sample self-consistency plus the trained text-monitor score, with
C2's regularisation, fitted on the same reference and evaluated on the same test seeds, catches 336
at C2's 59 false alarms, against C2's 339. This comparison was chosen after the results existed and
its threshold was set on test labels like the published one, so it does not prove equivalence. It
does mean the contribution of internal-state access is not established.

**Change.** No claim that activation telemetry adds value is made until a preregistered comparison
against self-consistency plus text, with separate training, calibration and untouched test data,
shows it. Until then the hardware program does not plan telemetry into silicon on the strength of
YB-0051.

## C3. YB-0051: operating points use thresholds set on the test labels

**Claim qualified.** The published recalls at each false-alarm budget set the threshold from the
correct answers of the evaluation sample, inside every bootstrap resample. That is a retrospective
ROC point, not the rate a threshold frozen before deployment would give (already noted for earlier
experiments in B6 of this ledger).

**Change.** Every operating point is reported twice: as published, and with the threshold frozen on
data the test never saw. For C2 the frozen numbers are 307 caught and 44 false alarms (0.743%).

## C4. YB-0047: the held-out task still shaped model selection

**Claim qualified.** The leave-one-task-out transfer result selects the probe layer and the
regularisation on the full derivation mixture (`tests/experiment.py` lines 52 to 56), then refits
the weights with one task removed using those selections (lines 75 to 85). The held-out task's
labels therefore influenced model selection. Its numerical effect has not been measured.

**Change.** Rerun with layer and regularisation selected inside each outer task holdout (nested
selection), and report both results.

## C5. YB-0051 H3: "not supported" was read as "no effect"

**Claim corrected.** H3 found +7.4 points of recall for eight samples over four at 1% false alarms,
with a 95% interval of -5.8 to +16.8, and the README concluded that the tie-break, not more samples,
supplies the resolution.

**What the data says.** The interval includes both no improvement and a large one. The experiment
did not show that more samples add nothing; it failed to show that they add something.

**Change.** The sentence becomes: "Eight samples were not shown to beat four (+7.4 points, 95%
interval -5.8 to +16.8). Four stays the default on cost (3.8 times generation time against 7.6),
not because more samples were shown not to help."

## C6. Scope: what these detectors measure

**Qualification added to YB-0050 and YB-0051.** The tasks are generated arithmetic, counting and
calendar questions; the outcome is a wrong answer. That is error detection, not detection of
unauthorized actions, deception or harmful planning. The runtime observer in `observer/` is a
different scorer with hand-set weights, not the probe or C2. Results here say nothing yet about
the witness the chip's rulebook would require for an irreversible action.

---

Credit: the external reviewer of 22 October 2026 (memo in this folder, `MEMO.md`). Recomputed by
`check_research.py` from the committed scores.
