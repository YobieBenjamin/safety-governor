# Status of every finding from the external audit of 22 October 2026

One row per finding, with five statuses kept apart, as the reviewer asked, so that one word,
"fixed", is never doing the work of all five:

- **Implemented:** the change exists at the named commit.
- **Locally tested:** the reproduction and the regressions were run against that commit, and each
  regression was shown to fail *for the intended security reason* when the fix is reverted
  ([EVIDENCE.md](EVIDENCE.md): an assertion every time, never an import, attribute, type or name error),
  while the legitimate operation still works.
- **Propagated:** GitHub `main` of that repository contains the commit.
- **Rechecked:** the finding was reassessed against the propagated version, on fresh clones from GitHub.
- **Open or partial:** what of the original finding is still not resolved.

As of 22 October 2026, 23:30 UTC. GitHub `main`: safety-governor `911672b`, hardware-and-silicon
`8331f76`. Commit `28927e3` (finding 1's key rotation, the evidence stage, the Mac fix for the verify
script) is committed and packaged but **not yet on GitHub**; its rows say so.

Not every finding is the kind a code change closes. The reviewer's own table, which this record follows:

| Kind of finding | What can legitimately close it |
|---|---|
| An implementation accepts an unauthorized operation | A correction, a regression that detects the original failure, and evidence that legitimate operations still work |
| A formal model omits a required property | A revised property and model, then verification of their relationship to the implementation |
| A conclusion exceeds an experiment's evidence | A corrected interpretation and corrected claims |
| An experiment lacks a necessary comparison | The additional experiment, with an appropriate evaluation design |
| A physical enforcement dependency is unresolved | The interface evidence and physical measurements |

The reproduce, fix, revert sequence applies to the first kind only. It was carried out for every
implementation finding below, and for nothing else.

## 1. Implementation findings

| # | Finding | Repo | Implemented | Locally tested | Propagated | Rechecked | Open or partial |
|---|---|---|---|---|---|---|---|
| 1 | A policy chose its own quorum (threshold 0, no signatures, accepted and committed) | safety-governor | [`c7df7cb`](https://github.com/YobieBenjamin/safety-governor/commit/c7df7cb60bca338da4f023ca15f2d4ce5d03b398) (fused floor; k from trusted state); [`28927e3`](https://github.com/YobieBenjamin/safety-governor/commit/28927e386d564160dc018a17a2745ebc2b9a7298) (the configuration in force authorizes its replacement, keys and threshold included) | Yes: reproduced on `dccc1e0` (propose and commit accepted, installed threshold 0); 3 regressions fail by assertion when reverted; rotation, self-install and floor tests pass | `c7df7cb`: yes. `28927e3`: **no, pending** | `c7df7cb`: yes, on a fresh clone of `911672b`. `28927e3`: no | Changing the fused manufacture floor itself is a provisioning act, not modelled. The protected record is modelled as a fuse-block field; its silicon form (a monotonic register or OTP banks) is not designed |
| 2 | A signed heartbeat cleared a halt | safety-governor | [`c7df7cb`](https://github.com/YobieBenjamin/safety-governor/commit/c7df7cb60bca338da4f023ca15f2d4ce5d03b398): every signed command names itself; HALT and CLEAR name the chip and expire within 60 s; HALT and CLEAR use authority keys separate from the heartbeat key; the RTL mailbox compares the signed command byte (status 7) | Yes: reproduced on `dccc1e0` (2 of 4 governors cleared here, 4 of 4 in the reviewer's run); 6 regressions fail by assertion with all three locks reverted; each CLEAR test shows the right CLEAR works under the same setup; the replay sweep accepts nothing | Yes | Yes, `911672b` | The same sweep for the fabric's own messages and for signed objects inside bodies (G13). The test-strengthening in `28927e3` is not yet on GitHub |
| 3 | The reference gate's signing key was computable from public quotes | hardware-and-silicon | [`b36ed52`](https://github.com/YobieBenjamin/hardware-and-silicon/commit/b36ed52fb7b2db6b682ff942b3c2af020642a551): `SiliconRoot.derive_key()` from the secret CDI | Yes: reproduced on `11eb119`; the regression fails by assertion when reverted; the key is stable across restart and differs per chip | Yes | Yes, `8331f76` | Lifecycle across a firmware change: a new CDI gives a new gate key, and endpoints provisioned with the old public key then refuse its tickets (fails closed); re-provisioning is not modelled or tested |
| 4 | An old approval released a hold the stricter current policy refuses | hardware-and-silicon | [`b36ed52`](https://github.com/YobieBenjamin/hardware-and-silicon/commit/b36ed52fb7b2db6b682ff942b3c2af020642a551): holds carry their policy; a new policy drops them; approval of a hold from another policy is refused | Yes: reproduced on `11eb119` ($5,000 paid after the cap fell to $2,000); 2 regressions fail by assertion; a hold under the current policy still approves and executes | Yes | Yes, `8331f76` | A deliberate override lane (a human approving what current rules refuse) does not exist; if wanted, it needs its own rule, quorum and reason code |
| 5 | A replayed older epoch moved the endpoint back and a revoked ticket executed | hardware-and-silicon | [`b36ed52`](https://github.com/YobieBenjamin/hardware-and-silicon/commit/b36ed52fb7b2db6b682ff942b3c2af020642a551): versioned epochs, a durable high-water mark at the endpoint, and the gate refusing to commit a ticket from a replaced policy | Yes: reproduced on `11eb119`; each lock's regression fails by assertion when that lock alone is reverted | Yes | Yes, `8331f76` | An endpoint restart replaying an old epoch is covered by the durable state but has no test of its own |
| 5b | (found while fixing 5) the gate reloaded an older governance-signed policy | hardware-and-silicon | [`b36ed52`](https://github.com/YobieBenjamin/hardware-and-silicon/commit/b36ed52fb7b2db6b682ff942b3c2af020642a551): every governance document carries a version; older refused; restart reloads the newest | Yes: reproduced on `11eb119`; regression fails by assertion | Yes | Yes, `8331f76` | None known |
| 5c | (found while fixing 5) an older revocation list un-revoked a device | hardware-and-silicon | [`b36ed52`](https://github.com/YobieBenjamin/hardware-and-silicon/commit/b36ed52fb7b2db6b682ff942b3c2af020642a551) | Yes: reproduced on `11eb119`; regression fails by assertion | Yes | Yes, `8331f76` | None known |
| G1 | Revocations stored, never enforced (our gap list; the reviewer called it a failure) | safety-governor | [`6743c9f`](https://github.com/YobieBenjamin/safety-governor/commit/6743c9f8ac951becc1e5fad8c47cf685120ea297) | Yes: 3 regressions fail by assertion when reverted | Yes | Yes, `911672b` | A revoked governor's chip id on the fabric is not refused by the fabric layer yet |
| G2 | `CAP_REQUEST` ignored the sandbox flag | safety-governor | [`6743c9f`](https://github.com/YobieBenjamin/safety-governor/commit/6743c9f8ac951becc1e5fad8c47cf685120ea297) | Yes; the same request without the sandbox is still granted | Yes | Yes, `911672b` | None known |
| G3 | Hazard budget counted per governor | safety-governor | [`6743c9f`](https://github.com/YobieBenjamin/safety-governor/commit/6743c9f8ac951becc1e5fad8c47cf685120ea297): one named owner across the rack, fail closed if unreachable | Yes | Yes | Yes, `911672b` | None known |
| G5 | A workload token survived a rulebook change | safety-governor | [`6743c9f`](https://github.com/YobieBenjamin/safety-governor/commit/6743c9f8ac951becc1e5fad8c47cf685120ea297) | Yes (the first version of this test did not catch the bug; rewritten, now it does) | Yes | Yes, `911672b` | None known |
| G4 | Tokens read from the GPU's counter, not from presented streams | safety-governor | Not implemented | No | No | No | **Open.** A simplification in the model, not a hole an attacker can use (the counter is not host-writable) |

## 2. The formal model

| # | Finding | Implemented | Locally tested | Propagated | Rechecked | Open or partial |
|---|---|---|---|---|---|---|
| 6 | The abstract machine let a ticket issued before a halt execute during it (SAT on the reviewer's query); P5 only said the halt flag stays set | [`6743c9f`](https://github.com/YobieBenjamin/safety-governor/commit/6743c9f8ac951becc1e5fad8c47cf685120ea297): `execute` requires RUN; P13 proved; the file checks P13 fails on the old machine | Yes; the code side is pinned by a test that fails by assertion when the RUN check is reverted | Yes | Yes, `911672b` | **Partial.** Implementation-to-proof conformance is not established: nothing mechanically links `governor.py` to the abstract machine (experiment L4, in revision) |
| 6b | A proof that takes "a quorum signed" as a given cannot find a bug in how the quorum is counted | [`c7df7cb`](https://github.com/YobieBenjamin/safety-governor/commit/c7df7cb60bca338da4f023ca15f2d4ce5d03b398), restated in [`28927e3`](https://github.com/YobieBenjamin/safety-governor/commit/28927e386d564160dc018a17a2745ebc2b9a7298): the quorum and the clear are computed from what was signed; P10 to P12; P10 and P12 fail on the old rules | Yes | `c7df7cb`: yes. `28927e3`: no, pending | `c7df7cb`: yes | **Partial**, same reason as 6. Every other boolean input the proof takes on trust is a place to test the code directly; not all have been |

## 3. Research findings (autonomic-graph-regulation)

None of these is closed by a code change, and none was. The numbers were recomputed from the committed
YB-0051 scores at `4c1374d` by [`check_research.py`](check_research.py); every one matched the memo exactly.

| # | Finding | Kind | Disposition | Status |
|---|---|---|---|---|
| R1 | YB-0050: the layered system lost to self-consistency (469 against 498 of 530) | Negative result | Stays in the record as a negative result. Nothing to correct | Unchanged, as it should be |
| R2 | YB-0051: 1% pooled false alarms hide 13.07% on modular exponentiation (46 of 352); 11.65% with a frozen threshold | Conclusion exceeds evidence | Corrected claim drafted: every operating point reported per task family ([AGR-CORRECTIONS-DRAFT.md](AGR-CORRECTIONS-DRAFT.md), C1) | **Drafted, not applied**: autonomic-graph-regulation has not been changed (its `main` is still `4c1374d`, 11 October) |
| R3 | Self-consistency plus text reaches 336 against C2's 339 | Missing comparison | The preregistered comparison (separate training, calibration, untouched test) is the closure; a claim restriction is drafted meanwhile (C2) | **Open** (experiment not run); correction drafted, not applied |
| R4 | Thresholds set on test labels | Conclusion exceeds evidence | Report each operating point twice, published and frozen (C3) | Drafted, not applied |
| R5 | YB-0047: the held-out task shaped model selection | Methodology | Nested selection inside each outer fold, rerun (C4) | **Open** (rerun not done); correction drafted, not applied |
| R6 | YB-0051 H3 read "not shown" as "no effect" | Conclusion exceeds evidence | Sentence corrected (C5) | Drafted, not applied |
| R7 | The detectors measure arithmetic errors, not harmful actions; the runtime observer is not the probe | Scope | Scope statement (C6) | Drafted, not applied |

## 4. Deployment and physical findings

| # | Finding | Disposition | Status |
|---|---|---|---|
| D1 | Per-GPU reset, power brake and power enable unresolved on HGX (board-lever register B2 to B4) | Interface evidence and a measured deadline on one named board (roadmap stage 3, experiment P2) | **Open.** No software change addresses it |
| D2 | One complete action path end to end, with a real observer, through a policy change, a delayed approval, a replay, a restart, a partition and a revocation | Build and run it | **Open** |
| D3 | The probe's reported cost times scoring only, not live telemetry acquisition | Label the cost honestly; measure the full path when it exists | **Open** |

## 5. Exactly what each repository received

**safety-governor** ([commits since the audited `dccc1e0`](https://github.com/YobieBenjamin/safety-governor/compare/dccc1e028caa0dfc4fa5798112dc6e22262a03c5...main)):

| Commit | On GitHub | What it changed |
|---|---|---|
| `c7df7cb` | yes | Findings 1 and 2: fused threshold floor, k from trusted state, signed commands name themselves, HALT and CLEAR bound to chip and expiry, authority keys apart from the heartbeat key, RTL mailbox status 7; H19 (15 tests); P10 to P12 |
| `6743c9f` | yes | Finding 6 (`execute` requires RUN, P13); G1, G2, G3, G5 closed (H20, 8 tests); review record section 9; reproduction scripts |
| `48af736` | yes | The memo verbatim, the response, the drafted research corrections |
| `911672b` | yes | `tools/verify_audit_fixes.sh` (first version, which used plain `python3` and failed on a Mac) |
| `28927e3` | **no, pending** | Finding 1 in full (governance configuration in force, key rotation, 4 tests), the CLEAR tests rebuilt with controls, `tools/audit_evidence.py` and `EVIDENCE.md`, the verify script building its own environments |
| (this record) | **no, pending** | This file; the narrowed claims in the memo header, the response and the review record |

**hardware-and-silicon** ([commits since the audited `11eb119`](https://github.com/YobieBenjamin/hardware-and-silicon/compare/11eb1199debd833abfa3ec9840f719af9c816087...main)):

| Commit | On GitHub | What it changed |
|---|---|---|
| `b36ed52` | yes | Findings 3, 4, 5, 5b, 5c; `tests/test_audit_2026_10_22.py` (11 tests); `docs/CHIP_DESIGN.md`, `docs/USAGE.md` |
| `8331f76` | yes | The memo verbatim, the response, the reproduction scripts, a README section on reviews |

**autonomic-graph-regulation:** **nothing.** Its `main` is still `4c1374d` (11 October). The research
corrections are drafted in safety-governor (`AGR-CORRECTIONS-DRAFT.md`) and have not been applied there,
because this session's publishing pipeline does not push that repository.

**safety:** **nothing from this audit.** Its one commit today, `280fb78` (08:38 Pacific), is the agent
program refreshing the wave-1 audit packet for YB-0052 (two files under `audit/wave-1/`), unrelated to
the reviewer's findings. YB-0052 itself is still on its branch `exp/yb-0052`, in revision.

## 6. How to recheck

```
git clone https://github.com/YobieBenjamin/safety-governor
git clone https://github.com/YobieBenjamin/hardware-and-silicon
cd safety-governor && bash tools/verify_audit_fixes.sh
```

On `911672b` the script itself needs Linux with the libraries installed (the Mac failure above). From
`28927e3` it builds its own environments; from a cold start it reports 18 of 18.
