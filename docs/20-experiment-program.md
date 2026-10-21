# 20. The experiment program: proving or disproving the chip in software, then in design, before any circuit

The rule of the program has not changed: nothing goes to circuitry, tape-out or an add-on chip until the design has been proven in software and then in design. This document turns that rule into experiments, and it attaches every one of them to one of three repositories: `safety-governor` (the chip), `safety` (the Autonomic Graph Regulation research program and the Layer 3 observer) and its public snapshot `autonomic-graph-regulation`. The fourth repository, `hardware-and-silicon`, is used as a source: the software reference stack, the 66-attack catalogue, and the lanes contract (`docs/LANES.md`) that fixes the signed message formats between the layers. New work goes into the three.

Each experiment names the claim it tests, where it lives, what it would take to run, and the result that would count as a disproof. The claims are the five from `docs/19`: L (the logic), P (the physical paths), C (the cryptography), S (the semantics, which the chip delegates to lists and observers), N (the numbers). Where an experiment belongs to the `safety` program it carries a YB number and follows that program's protocol (`docs/PROTOCOL.md` there): pre-registered code, fresh test sets touched once, matched false-alarm rates, no number without an artifact, an independent audit before a claim.

## 1. Where the chip meets the organism

The two programs were designed to meet, and the lanes contract is the seam. It is worth saying in plain words what each gives the other, because the experiments follow from it.

The AGR program's Independence Principle says the safety system must not be a transformer, must not contain one, and must never read the model's words: it is an external organism that reads numeric vital signs (tier 0: compute time, token rate, power; tier 2: entropy, margins, activations read from outside) and acts through effectors: throttle, pause, require a human, halt. Its results so far are the strongest evidence the chip has for its semantic layer: a text-blind regulator caught wrong answers before they were committed more often than an LLM judge at a matched false-alarm rate (YB-0033, replicated in YB-0034, YB-0035 and YB-0045); holding an action until cleared beat blocking it reactively (YB-0044); and GPU power alone carried no failure signal (YB-0018, a negative result the chip must respect).

The chip gives the organism what software cannot: effectors with teeth. "Throttle, pause, require a human, halt" are, in the governor, the compute budget, the hold, the human quorum and the halt loop, driven from a die the model and the operator cannot patch. And it gives the organism a guarantee about itself: the gate proves (section 2 of `docs/19`) that the observer is always invoked, cannot be impersonated and is separate from the thing judged. The organism supplies the verdict; the chip makes the verdict impossible to skip.

So the experiments below do three things: carry the proofs from the chip's abstract machine down toward gates and up toward the organism's protocol (claim L); check that the chip's paths are what the design says (P); and measure, never assume, how good the organism is as a witness, in the chip's own terms (S).

## 2. The experiments

Status: **done** exists and passes today; **build** is software to write; **ask** needs something from outside the program; **later** waits for hardware.

### Claim L: the logic (`safety-governor`, with `safety` YB-0039)

| ID | Experiment | Where | Falsified if | Status |
|---|---|---|---|---|
| L1 | Inductive proofs of the core invariants on the abstract machine: P0 to P9 and non-vacuity | `proofs/core_invariants.py`, `make proof` | any step breaks an invariant | done |
| L2 | The commit-point protocol proven: the hold, the reviewer's clearance bound to an action version, the regulator's all-clear inside its budget, the alarm when the budget runs out. This is the chip-side answer to YB-0039 (extension) in `safety/HYPOTHESES.md`, whose properties (1) to (3) are now theorems on the abstract machine; (4) is the hash chain's job and (5), no deadlock, is checked as non-vacuity | `proofs/commit_point.py` | a sequence commits a high-severity action without a clearance for its version, or lets a budget expire silently | done; the prover found and closed one hole (a re-parameterised action kept its expired budget) |
| L3 | Widen the abstract machine to budgets and rate windows, k-of-n approvals, buffer classes at the switches, the egress hold and release, the loop beacon and clear | `proofs/`, one file per protocol | the prover finds a step that executes, releases or clears without the rule, the quorum or the beacon | build |
| L4 | Trace conformance: `govsim` writes every transition to a trace; a replayer runs each trace through the abstract machines and fails on the first step a machine refuses | `govsim/trace.py`, `tests/test_h19_conformance.py` | the simulation takes a step the theorem's machine does not have | build |
| L5 | Differential test of the two gates: `hardware_ref.gate` from the reference stack and `govsim`'s gate, fed identical rulebooks, requests, witnesses and tickets; answers and reason codes must agree on the 75 attacks, the 12 baselines (87 catalogue entries; `results/report.md` in the reference stack), and random requests from property-based testing | `tests/test_h21_differential.py` (imports `hardware_ref` as a dependency) | any input on which the two disagree | build |
| L6 | Mutation testing as a standing gate: mutate the model (drop a check, flip a comparison, skip a log write); every mutant must be killed by some test; the twenty survivors found in the second audit set the method | `make mutants` | a mutant that removes a check survives | build |
| L7 | Formal proofs on the Verilog: the invariants of L1 and L2 restated on the hard-core blocks and proven with an unbounded model checker; gate-level equivalence between RTL and the synthesized netlist | `rtl/formal/`, the pre-hardware plan | a block admits an input sequence that violates its invariant | build (design phase) |

### Claim P: the physical paths (`safety-governor`)

| ID | Experiment | Where | Falsified if | Status |
|---|---|---|---|---|
| P1 | Model-level enumeration: every exit is governed or bricked at the rack tier; the one gap (two roster peers exchanging buffers the governor cannot classify) is recorded | `tests/test_h02_enforcement_points.py` | an enumerated exit without a checker | done |
| P2 | The exit register: a machine-readable list of every path by which bytes, requests, responses, weights, power, reset or clock can leave or reach a GPU on a named tray (HGX eight-GPU baseboard; NVL72 compute tray), each row marked governed by a named lever, bricked, or unaccounted, with a source; a test fails on any unaccounted row | `docs/research/exit-register.md`, `tests/test_h20_exits.py` | an unaccounted path, or a path the design guide shows that the register lacks | build, then ask (the design guide under NDA) |
| P3 | Covert-channel budget: the maximum rate at which weights could leak through permitted traffic under the byte and rate budgets, as a number per hour at the tightest serviceable policy | `tests/test_h10_leakage.py` extended | the rate would exfiltrate a frontier model in practical time under any serviceable policy | build |
| P4 | The halt loop in circuit simulation: 72 governors, cut wires, temperature, cable length | `hw/loop/`, `make loop` | any configuration misses the 1 ms bound | done (simulated); measured later |

### Claim C: the cryptography (`safety-governor`)

| ID | Experiment | Where | Falsified if | Status |
|---|---|---|---|---|
| C1 | Negative tests for every signed object: forged, altered, replayed, stale-edition, wrong-endpoint and wrong-key tickets, capabilities, verdicts, approvals and policy images refused with the predicted code | `tests/test_h02`, `h03`, `h06`, `h08`, `h12`, `h17` | any forged or replayed object accepted | done |
| C2 | Key hygiene: a different measurement derives a different key; a quote nonce cannot be replayed | `tests/test_h01`, `test_h18` | a quote accepted twice, or one key for two measurements | done |
| C3 | Post-quantum path: cost a hybrid signature (P-384 plus a lattice scheme) in the batching model, since OTBN has no ML-DSA today | `govsim/bench.py` | batched engine utilisation above 100 percent at the modelled load | build |

### Claim S: the semantics, delegated to lists and observers (`safety`, mirrored to `autonomic-graph-regulation`)

The chip proves the observer is always invoked, cannot be impersonated and is separate. Whether the observer is right is measured, never proven. The `safety/observer/README.md` says it in its own words: the scoring weights "are judgment, not measurement. They need a labelled evaluation set before anyone relies on the numbers. That set is the next piece of work." These are that work, written as hypotheses in the backlog's own format and numbered after the last entry there.

| ID | Experiment | Where | Falsified if | Status |
|---|---|---|---|---|
| YB-0052 | The observer evaluation set: labelled requests in the gate's typed form (`request_id, measurement, action, params, context`), with abstract hazard classes and no real hazardous content, including disguised requests a model would answer and benign requests that look alarming; the Layer 3 observer scored per signal family on miss rate and false-alarm rate at matched false-alarm budgets | `safety/observer/bench/` | the miss rate on disguised requests stays above the policy's hazard budget for every weighting tried | build |
| YB-0053 | Observer independence: the adversarial inputs that defeat the model's own refusal must not defeat the observer at the same rate; measure the correlation of failures between the model, the text-blind regulator (vitals), the Layer 3 observer (request structure) and a Sentry-shaped filter | `safety/observer/bench/independence.py`, on YB-0045's recorded episodes plus YB-0052's set | failures correlate so strongly that a quorum of observers adds nothing | build |
| YB-0054 | Quorum arithmetic for the gate: from measured per-observer miss rates and their correlation, the joint miss rate of k-of-n observers per hazard class, and the policy's `observer` list and `max_risk` derived from it | `safety/observer/bench/quorum.py`, feeding `safety-governor/docs/06` register rows | no affordable quorum reaches the hazard budget for the weapons and knowledge use cases | build |
| YB-0055 | Chip-visible vitals: can a regulator built only on tier-0 signals the governor can read out of band with no host cooperation (token rate, cycles, bytes, latency from the meter; board power from the BMC) catch wrong answers before commitment at a matched false-alarm rate? YB-0018 says power alone cannot. If token rate and latency alone cannot either, the chip's own sensing is for enforcement and accountability, and the early warning must arrive as a signed verdict from an observer with substrate access | `safety/algorithms/YB-0055-*` on the existing recordings, features restricted to the chip-visible set | tier-0-only is not distinguishable from the length and question-type baselines | build |
| YB-0056 | Verdict latency inside the gate's windows: the regulator's and the observer's time-to-verdict against the ticket freshness window and the release path's 50 ms batching window at the modelled load | `safety/observer/bench/latency.py` against `safety-governor/govsim/bench.py` constants | verdicts arrive late often enough to push the release path over the overhead target | build |
| YB-0057 | The use cases with a real witness: `strike`, `hazard`, `plot` and `oversight` run with the Layer 3 observer over the lanes contract instead of the stand-in; the regulator's effectors mapped onto the governor's levers (throttle to the compute budget, pause to the hold, require-a-human to the quorum, halt to the loop) | `safety-governor/govsim/cli.py usecase --observer lanes` with the `safety_observer` package | a bad action initiates, or a benign one is refused for the wrong reason | build |
| S-mine | Mined indicators as witnesses: any algorithm the mine promotes as a text-blind indicator must emit a lanes observer assertion and be scored on YB-0052 before it counts; the score is recorded in the ledger beside the baseline result | `safety/miner/` promotion gate | an indicator passes its own baseline and adds nothing to the joint miss rate | build |

### Claim N: the numbers (`safety-governor`)

| ID | Experiment | Where | Falsified if | Status |
|---|---|---|---|---|
| N1 | Whole-deployment overhead: 72 GPUs, batching, tail latency, logging, revocation, as a discrete-event simulation | `govsim/deploy.py`, `docs/12` | above one percent of throughput at any serviceable policy | build |
| N2 | False-halt model: component failure rates, debounce, beacon windows and heartbeat loss combined into expected false halts per rack-year | `docs/07` FMEA made numeric; fault injection in `govsim` | a rate operators would switch the governor off for | build |
| N3 | FPGA beside a real GPU: the three cost numbers and the false-halt rate measured | the pre-hardware plan, phase 4 | measurements disagree with the models beyond their margins | later, ask |

## 3. The harness the three repositories share

- **A lanes conformance suite in `safety-governor`.** Signed fixtures for every message type the gate consumes (observer assertion, provenance assertion, attestation token, action ticket, audit record, policy image), checked by the governor model; the `safety` observer already pins its subject hash to the gate's (`observer/tests/test_contract.py`). The suite makes a format change in one repository fail the other's build.
- **The catalogue as data.** The 75 attacks and 12 baselines (the catalogue grew from 66 and 10 with the third and fourth posts; the blog and the README still said the old numbers, which the first wave's agent caught) expressed as fixtures, so one file drives the software gate, the governor model, the RTL simulation and later the FPGA.
- **A ledger for the chip, `EXPERIMENTS.md`,** in the mine's style: one row per experiment above, with date, result and what it rules in or out. Negative results stay.

## 4. Order of work

1. L4 and L5: conformance and the differential test. The cheapest places for a real mistake to show.
2. YB-0052 and YB-0053: the labelled set and independence. They decide whether the knowledge and plot use cases are worth the chip or only worth the log.
3. P2: the exit register, from public documents first, finished with the design guide.
4. L3, L6, C3, YB-0054 to YB-0057, N1, N2.
5. Then design: L7 on the Verilog, the loop re-run against a real board's parasitics.
6. Then circuitry: the FPGA with the same catalogue, hardware in the loop, N3.

## 5. Exit criteria

The program leaves software when: every invariant in L1 to L3 is proven and L4 shows every trace conforms; L5 shows the two gates agree on the whole catalogue and on random inputs; L6 leaves no check-removing mutant alive; P2 has no unaccounted row for at least one real tray; YB-0052 to YB-0054 give a quorum under the hazard budget for each modelled use case, or the design records that the chip's value for that use case is accountability rather than prevention; N1 is under one percent and N2 is a rate an operator would accept; and a third independent audit finds no claim without a source.

It leaves design when L7 passes, the loop simulation is re-run against the real board, and the FPGA passes the catalogue with the same reason codes.

And it stops, honestly, if any of these happens: L5 disagreement that shows the policy itself is ambiguous; P2 with a path that cannot be governed or bricked at the rack tier and that NVIDIA will not close; YB-0054 with no affordable quorum for the use cases that justify the chip; N1 or N3 above what a buyer will pay. Each is a disproof of the chip as designed, and the point of the software phase is to find it there, where it is cheap.

## 6. What this adds to each repository

- `safety-governor`: `proofs/commit_point.py` (added), `EXPERIMENTS.md` (added), and the builds above: `govsim/trace.py`, `tests/test_h19_conformance.py`, `tests/test_h20_exits.py`, `tests/test_h21_differential.py`, `govsim/deploy.py`, the `--observer lanes` option on the narrations, `rtl/formal/`.
- `safety`: hypotheses YB-0052 to YB-0057 appended to `HYPOTHESES.md` in the backlog's format with status open, and the promotion gate for indicators; `observer/bench/` to hold the evaluation set and the three measurements.
- `autonomic-graph-regulation`: receives the same through the public snapshot.
