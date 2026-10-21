# Experiment ledger

One row per experiment in `docs/20-experiment-program.md`. Every result, including a negative one, stays. A row changes only by appending to its result column with a date. The claims are the five of `docs/19`: L logic, P physical paths, C cryptography, S semantics (delegated), N numbers.

| ID | Claim | Experiment | Where | Status | Result |
|---|---|---|---|---|---|
| L1 | L | Core invariants proven by induction on the abstract machine (P0 to P9, non-vacuity) | `proofs/core_invariants.py` | done | 2026-10-20: all proofs hold; the prover found a sentinel collision (edition -1 equal to "no ticket") in the first draft, closed by P0 |
| L2 | L | Commit-point protocol: hold, clearance bound to the action version, all-clear inside the budget, alarm on expiry (YB-0039 extension, properties 1 to 3) | `proofs/commit_point.py` | done | 2026-10-20: all proofs hold; the prover found that a re-parameterised action kept an expired budget with no alarm; a new version now gets a fresh budget |
| L3 | L | Widen the abstract machine: budgets, k-of-n approvals, buffer classes, egress release, loop beacon and clear | `proofs/` | open | |
| L4 | L | Trace conformance of `govsim` to the abstract machines | `govsim/trace.py`, `tests/test_h19_conformance.py` | open | |
| L5 | L | Differential test: reference-stack gate against `govsim` on the catalogue and random requests | `tests/test_h21_differential.py` | open | |
| L6 | L | Mutation testing as a standing gate | `make mutants` | open | 2026-10 (second audit): twenty surviving mutants found and fixed by hand; not yet automated |
| L7 | L | Formal proofs on the Verilog; gate-level equivalence | `rtl/formal/` | open | |
| P1 | P | Every enumerated exit governed or bricked at the rack tier; the H2b gap recorded | `tests/test_h02_enforcement_points.py` | done | passes; the gap is named, closed only at the integrated tier |
| P2 | P | The exit register with no unaccounted row | `docs/research/exit-register.md`, `tests/test_h20_exits.py` | open | public sources first; the HGX design guide is an ask |
| P3 | P | Covert-channel budget as a number per hour | `tests/test_h10_leakage.py` | open | |
| P4 | P | Halt loop in ngspice: 72 governors, 39 configurations | `hw/loop/results.md` | done | worst case 317.15 µs against 1 ms; measured on hardware: not yet |
| C1 | C | Negative tests for every signed object | `tests/` | done | passes |
| C2 | C | Key hygiene and nonce replay | `tests/test_h01`, `test_h18` | done | passes |
| C3 | C | Post-quantum hybrid signature cost in the batching model | `govsim/bench.py` | open | |
| YB-0052 | S | Observer evaluation set and per-family miss and false-alarm rates | `safety/observer/bench/` | open | hypothesis filed in `safety/HYPOTHESES.md` |
| YB-0053 | S | Observer independence from the model's own failures | `safety/observer/bench/independence.py` | open | filed |
| YB-0054 | S | Quorum arithmetic for the gate's `observer` list and `max_risk` | `safety/observer/bench/quorum.py` | open | filed |
| YB-0055 | S | Chip-visible tier-0 vitals as an early warning | `safety/algorithms/YB-0055-*` | open | filed; prior: YB-0018 found no signal in power alone |
| YB-0056 | S | Verdict latency inside the gate's windows | `safety/observer/bench/latency.py` | open | filed |
| YB-0057 | S | The use-case narrations with the real observer over the lanes contract | `govsim/cli.py usecase --observer lanes` | open | filed |
| N1 | N | Whole-deployment overhead simulation | `govsim/deploy.py` | open | the per-chip model gives 34 percent engine utilisation batched and under 0.1 percent firmware share |
| N2 | N | False-halt rate model | `docs/07` FMEA, fault injection | open | |
| N3 | N | FPGA beside a real GPU | pre-hardware plan, phase 4 | later | needs a lab with a rack |

## H1 (#13): lanes conformance suite and the catalogue as data

- `lanes/` holds signed fixtures (`lanes/fixtures`), the generator (`python3 -m lanes.generate`) and the checker (`python3 -m lanes.check [--observer DIR]`). `make lanes` passes here, including a run of the `safety` observer and a live comparison of `catalogue/attacks.json` (75 attacks, 12 baselines) with `hardware_ref.attacks`.
- Known gap: govsim's envelope differs from the contract (16-hex signer, hex signature, no embedded pub). The checker pins only what must agree today: canonical bytes, digest, and the deterministic signature.
- `patches/safety/lanes.patch` and `patches/hardware-and-silicon/lanes.patch` are diffs in git format: a CI workflow in each, `tests/test_catalogue_data.py` for hardware, and `test_contract.py` reading its pin from `lanes/fixtures/request.json` for safety. They are not applied, and `git apply --check` was not run against those repositories (this run could not). The workflows clone safety-governor `main`, so they bite only once these fixtures are merged there.
- The audit fixture chains from `sha256("audit-genesis")` and `make lanes` runs it through `hardware_ref.audit.AuditLog.verify_export`. `make lanes` now fails, not skips, when `../safety` or `../hardware-and-silicon` cannot be found (override with `SAFETY=` and `HW=`).
- govsim does not read the catalogue yet; `catalogue.load()` is ready for it.
