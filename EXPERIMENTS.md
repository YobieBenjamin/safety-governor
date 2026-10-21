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

## L4 trace conformance (issue #4)

`python3 -m pytest -q tests/test_h19_conformance.py` passes: every test of H0 to H18 is rerun with the trace sink on (`govsim/trace.py`) and its trace replayed through the machines of `proofs/` (`proofs/replay.py`). Two broken-governor fixtures (a halted governor that signs, a stale-edition ticket that executes) fail replay with the event named.

Findings from replay:

- Gap in the theorem: a power cycle is not a step. `core_invariants.py` leaves `halted` free in the initial state, but govsim boots into HALTED_INITIAL and reaches RUN on the first heartbeat with no clear. The replayer accepts this as an explicit `arm` step, only from a halt that a boot put there (counted in `Report.arms`). The theorem should either add a boot/arm step or constrain init.
- Gap in the theorem: an endpoint burns a ticket before the governor commit and the device checks, and may then refuse. The machine has no burn-without-execute step (`used` without `executed`); the replayer tracks it as `burned`.
- Refusals for expiry, wrong endpoint, parameter mismatch and bad signature are stutter steps of `forged execute`; the machine is looser than the system there, which is sound.
- Not a gap: `test_governor_cannot_clear_itself` injects a firmware fault (RUN with no clear). Replay refuses it as it must; the plugin lists it in `FAULT_INJECTION` and asserts the refusal.
- Not modelled: `allows` and `witness` are inputs of the machine, so replay does not check that the rule and witnesses were right; heartbeat is observed (governor hb_expiry at issue, endpoint hb_expiry at execute), not driven by explicit events; `quorum` is taken as true for an accepted policy image and for an authority clear.
- z3 is not installed here, so replay executes the guards on concrete values (copied from the Z3 steps) and a test checks the step names against the proof files; it does not run the prover.
