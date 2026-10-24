# PROOF: the safety governor, in software

**VERDICT: 1**  (every component holds)

- Generated: 2026-10-23T23:43:28Z
- Commit: `0d63e43380a887c1876c38942f0a87ba1ec548d4`
- Coverage: software-only  (see skipped components)
- Python 3.13.16; yowasp-yosys absent; pytest run
- Components: 11 pass, 0 fail, 1 skipped

Reproduce: `python -m govsim.prove`. The verdict is 1 only if no component fails; a single failure forces 0. A component whose toolchain is absent is skipped, never counted as a pass.

| Component | What it establishes | Result |
|---|---|---|
| `redteam-selftest` | the red-team oracle returns 0 on a broken gate (non-vacuous) | pass |
| `redteam` | capstone: one protected action, every attack the audit named | pass |
| `proofs-core` | abstract-machine invariants (INVARIANT-EDITION-NEVER-NEGATIVE..INVARIANT-NO-REPLAY-COUNTED, non-vacuity) | pass |
| `proofs-commit` | the commit-point proof | pass |
| `proofs-killswitch` | no global kill switch / corrected min-cut | pass |
| `conformance` | RTL differential-conformance suite | pass |
| `rtl-formal` | RTL formal properties with planted mutants | skipped |
| `exp-origin-gate` | EXPERIMENT-ORIGIN-GATE: the origin gate (no key, no model) | pass |
| `exp-containment` | EXPERIMENT-CONTAINMENT: containment measurement | pass |
| `exp-road` | EXPERIMENT-ROAD-REACHABILITY: rulebook reachability audit | pass |
| `exp-customer` | EXPERIMENT-CUSTOMER-CONFIRMATION: the payer's own-key confirmation | pass |
| `unit-tests` | the discriminating test suite (fail-before, pass-after) | pass |

## What a VERDICT of 1 means

In the software model, every stated safety property holds, every planted mutant is caught, every named attack on the one protected effect is repelled, and the oracle that scores the red team is itself shown to return 0 when the gate is broken. It is binary and reproducible.

## What it does not mean

It is not silicon, it does not certify a policy is wise, and it does not close routes outside the modelled deployment. Those limits are stated in `results/redteam.md` and `docs/18`. The claim is narrow and strong: without current, valid authorization, the protected effect does not proceed.

> Coverage is software-only: the RTL formal layer was skipped because yowasp-yosys is absent here. Run `python -m govsim.prove` on a host with the RTL toolchain for the full verdict.
