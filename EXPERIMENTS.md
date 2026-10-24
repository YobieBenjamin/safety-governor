# Experiment ledger

One row per experiment in `docs/20-experiment-program.md`. Every result, including a negative one, stays. A row changes only by appending to its result column with a date. The claims are the five of `docs/19`: L logic, P physical paths, C cryptography, S semantics (delegated), N numbers.

## Three claims, kept apart (F24)

These five claims must not be run together into one headline. The design makes three separable safety claims, each scoped to its own evidence, and none may borrow another's standing. A machine-checkable copy is `govsim/claims.py`.

1. **Structural enforcement (proven).** Nothing executes without a rule, a stamp and a present witness (claim L; `proofs/core_invariants.py`). This is enforcement *of* a verdict, not the *truth* of the verdict: a structurally valid action can still be harmful.
2. **Observer accuracy (unquantified).** Whether the lists and observers tell allowed from harmful is unmeasured; it needs a frozen evaluation set and per-family rates, not a pooled figure (claim S; YB-0052 to YB-0057). Two honest witnesses can share a mistake, so defeating a dual-witness pair does not require compromising two keys, and a second witness is not a second independent key (YB-0053).
3. **End-to-end harm reduction (not established).** That the whole stack lowers real-world harm is neither proven nor measured. The chip's structural failures surface as halts and holds; the semantic residual, a wrong verdict faithfully enforced, is not a halt and not a hold, and is not counted here.

| ID | Claim | Experiment | Where | Status | Result |
|---|---|---|---|---|---|
| L1 | L | Core invariants proven by induction on the abstract machine (P0 to P13, non-vacuity) | `proofs/core_invariants.py` | done | 2026-10-20: all proofs hold; the prover found a sentinel collision (edition -1 equal to "no ticket") in the first draft, closed by P0 |
| L2 | L | Commit-point protocol: hold, clearance bound to the action version, all-clear inside the budget, alarm on expiry (YB-0039 extension, properties 1 to 3) | `proofs/commit_point.py` | done | 2026-10-20: all proofs hold; the prover found that a re-parameterised action kept an expired budget with no alarm; a new version now gets a fresh budget |
| L3 | L | Widen the abstract machine: budgets, k-of-n approvals, buffer classes, egress release, loop beacon and clear | `proofs/` | open | |
| L4 | L | Trace conformance of `govsim` to the abstract machines | `govsim/trace.py`, `tests/test_h19_conformance.py` | open | |
| L5 | L | Differential test: reference-stack gate against `govsim` on the catalogue and random requests | `tests/test_h21_differential.py` | open | |
| L6 | L | Mutation testing as a standing gate | `make mutants` | open | 2026-10 (second audit): twenty surviving mutants found and fixed by hand; not yet automated |
| L7 | L | Formal proofs on the Verilog; gate-level equivalence | `rtl/formal/` | open | |
| P1 | P | Every enumerated exit governed or bricked at the rack tier; the H2b gap recorded | `tests/test_h02_enforcement_points.py` | done | passes; the gap is named, closed only at the integrated tier |
| P2 | P | The exit register with no unaccounted row | `docs/research/exit-register.md`, `tests/test_h20_exits.py` | open | public sources first; the HGX design guide is an ask |
| P3 | P | Covert-channel budget as a number per hour | `tests/test_h10_leakage.py` | open | |
| P3b | P | Containment rate: bytes/hour that leave a governed rack, measured at the egress boundary | `govsim/containment.py`, `tests/test_p3b_containment.py`, `tests/test_f12_containment_channels.py`, `tests/test_f13_p3b_policy_and_egress.py` | open | 2026-10-24 (F12, F13): corrected. The named policy is now installed and its live limits read back before measuring (old code ran the reference rulebook for every case, giving the spurious 6,135 and 26,200 B/h); delivered bytes are read at the egress boundary, not counted as signing calls; every permitted channel is inventoried, so a listed-recipient `message.send` with an unbounded body makes the finite-ceiling claim FAIL until bounded; and the one-time burst is reported separately from the sustained per-hour rate, never summed. The "50 years / centuries / 11 days" interpretations are withdrawn; corrected sustained figures are in `results/containment.md`. REMAINS OPEN: the inventory covers the signed-response and message.send channels; a complete register of every typed action's byte-bearing parameters and downstream relays is still owed |
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
| N1 | N | Whole-deployment overhead simulation | `govsim/deploy.py` | open | the per-chip model gives 34 percent engine utilisation batched and under 0.1 percent firmware share; 2026-10-24 (F23): that 34 percent is the BATCHED PROVENANCE RECORDS ONLY. The real request-to-effect path also signs one release ticket per response (`govsim/bench.py run_full_path`, `tests/test_f23_response_signature_cost.py`); those per-item tickets are not batchable, and the honest full-path engine load is 88 percent at 500-token responses and 306 percent (over one engine) at 100-token responses. Pricing is now honest; the DESIGN remedy (faster signing hardware, verifiable batch authorisation with atomic per-item consumption, or a keyed endpoint MAC for release tickets) is a spec/RTL change and stays open |
| N2 | N | False-halt rate model | `docs/07` FMEA, fault injection | open | |
| N3 | N | FPGA beside a real GPU | pre-hardware plan, phase 4 | later | needs a lab with a rack |
