# Start here: how to check this work

This is a chip that says no, and a program that tries to prove or disprove it in software before anyone cuts silicon. If you want to check the work rather than take my word for it, this page is the route: the theory first, then the logic, then the math, then the code that proves the code, then what is still open. Every path below exists in a public repository, every number comes from a command you can run, and the commands are listed. Yobie Benjamin, yobie AT ieee DOT org.

## The claim, in three sentences

You cannot trust an AI to police another AI, because the second AI fails the same ways as the first. The thing that stops an action has to be a small, dumb, physical component that the model cannot talk to: it checks a typed form against a signed rulebook, issues a signed ticket or refuses, and holds the levers (brake, reset, power, links) when a GPU will not listen. That component is a chip of the BMC's class, added to the server board the way management hardware already is, one per NVIDIA GPU, changing nothing in the GPU or in CUDA.

## The map: five repositories, one command each

| Repository | What it is | What it proves | Run it |
|---|---|---|---|
| [safety-governor](https://github.com/YobieBenjamin/safety-governor) (this one) | The chip: design documents, a functional model of a governed rack, the hypothesis suite, the RTL for the hard-core blocks, the Z3 proofs, the experiment program and the agents that run it | The logic of the governor and its fabric; the proofs; the silicon plan | `./run.sh` (200 model tests, 20 RTL tests, the sweep); `make proof` |
| [hardware-and-silicon](https://github.com/YobieBenjamin/hardware-and-silicon) | The control-plane reference stack and the blog series *The Chip That Says No* | The protocol: attestation, gate, tickets, budgets, holds, epochs, the audit trail, the OpenShell path | `./run.sh` (56 tests, 75 attacks blocked, 12 baselines allowed) |
| [Watermark](https://github.com/YobieBenjamin/Watermark) | A test copy of OpenAI's textGrain watermark, a hardened detector, retrieval, a signed registry, 13 attacks | What a watermark can and cannot do; the provenance verdict the gate consumes | `./run.sh` |
| [safety](https://github.com/YobieBenjamin/safety) | The algorithm mine: hypotheses YB-XXXX, each coded, tested and ledgered; the observer package (`observer/`), the witness lane | The observer as a measured witness, never the lock | `make all` |
| [autonomic-graph-regulation](https://github.com/YobieBenjamin/autonomic-graph-regulation) | The public snapshot of `safety` | Same | `make all` |

The three repositories that exchange messages agree on one wire contract: [hardware-and-silicon/docs/LANES.md](https://github.com/YobieBenjamin/hardware-and-silicon/blob/main/docs/LANES.md). Signed fixtures for every message type, and the checker the governor model runs, are experiment H1 (`make lanes`, on branch `exp/h1` until it merges).

## 1. Follow the theory

Read in this order. Each one stands alone.

1. The argument in plain words: *The Chip That Says No*, Parts 1 and 2, in [hardware-and-silicon/blog](https://github.com/YobieBenjamin/hardware-and-silicon/tree/main/blog). The reflex, the referee who is also a player, STOP but never GO, "can you undo it".
2. The layer model and why only silicon can be the lock: [A Multi-Layer Approach to AI Safety](https://github.com/YobieBenjamin/hardware-and-silicon/blob/main/blog/01-a-multi-layer-approach-to-ai-safety.md).
3. The whole chip as one story: [docs/10-plain-english-walkthrough.md](docs/10-plain-english-walkthrough.md). Under every section a box names the technical document, the model code, the test and the hardware block behind it. [docs/09-analogies.md](docs/09-analogies.md) is the same vocabulary as a table.
4. What the design is for and what it refuses to claim: [docs/00-objectives.md](docs/00-objectives.md), goals G1 to G8, requirements R1 to R32 with where each is tested, non-goals N1 to N7.
5. How solid any of it is: [docs/19-how-solid-is-the-theory.md](docs/19-how-solid-is-the-theory.md).
6. Why there is no kill switch for AI and why there is one at the exits, with the theorem and the check: [docs/23-there-is-no-kill-switch.md](docs/23-there-is-no-kill-switch.md).
7. The ladder every safety measure sits on, from a prompt that says "don't" to the chip to a person with a key, with what each rung catches, how it gets removed and the paper that showed it: [docs/24-the-ladder.md](docs/24-the-ladder.md).
8. The rulebook field by field, every no the chip can say and the evidence behind it, and how the chip talks to the NVIDIA GPU and the host CPU on the board, handshake by handshake: [docs/25-the-rulebook-and-the-board.md](docs/25-the-rulebook-and-the-board.md).
9. Where it sits next to the hardware-governance literature (flexHEGs and the rest), and what it borrows from them: [docs/18 §8b](docs/18-viability-and-open-questions.md). It takes the story apart into claims (L the logic, P the physical paths, C the cryptography, S the semantics, N the numbers) and says for each whether it is a theorem, engineering, trust, or not yet measured.

## 2. Follow the logic

The design documents, numbered, each opening with a plain-words summary and a "backed by" box: [docs/README.md](docs/README.md) is the index. The ones that carry the logic:

| Document | What it settles |
|---|---|
| [01-architecture.md](docs/01-architecture.md) | Where the governor lives in the rack, every block on the die and the code that models it, boot, the job lifecycle, the safe-mode ladder |
| [02-safety-fabric.md](docs/02-safety-fabric.md) | The halt loop and the signed message fabric: roster, cluster-atomic edition change, heartbeat, shared budgets, cross-linked logs, partitions |
| [03-interfaces.md](docs/03-interfaces.md) | Every plug: the GPU, the switches, the host mailbox, the DPU, the endpoints, the other governors; the asks to NVIDIA, all firmware and software; the pin summary |
| [04-specification.md](docs/04-specification.md) | The register map, the mailbox commands, the policy image, the request and the ticket (§5), the device-provenance record (§6), the crypto suite, timing, memory, physical targets (§11) |
| [05-threat-model.md](docs/05-threat-model.md) | Adversaries; what is stopped, with the test that shows it; what is only made expensive; what is not addressed |
| [06-assumptions-register.md](docs/06-assumptions-register.md) | One row per input the gate trusts: who signs it, how fresh it must be, what a failure means, what is not covered |
| [07-verification-plan.md](docs/07-verification-plan.md) | Hypotheses H0 to H18 and what falsifies each; RTL invariants; silicon validation; FMEA |
| [11-loop-timing.md](docs/11-loop-timing.md) | The halt loop as a circuit: ngspice across 72 governors, 39 configurations including cut wires, worst case 317 microseconds against a 1 millisecond bound |

The logic runs. [govsim/](govsim/) is the functional model of a rack of governed GPUs: the governor (`governor.py`, the order of checks is `_cmd_request`), the rulebook (`policy.py`), the ledger, the log, the fabric, the GPU with its levers, the switches as enforcement points. [tests/](tests/) holds one file per hypothesis, `test_h00_contract.py` to `test_h18_oversight.py`, 200 tests; each test is a thing that would knock a claim down. [rtl/](rtl/) holds the hard-core blocks in Amaranth (measurement registers, monotonic counter, epoch register, ticket store, capability table, halt sequencer, heartbeat, mailbox, lifecycle) with 20 simulation tests and generated Verilog. Forty-eight single-point mutations of the model and the RTL were run to confirm the tests bite (see the README).

```bash
git clone https://github.com/YobieBenjamin/safety-governor && cd safety-governor
./run.sh          # venv, 200 model tests, 20 RTL tests, Verilog, the sweep into results/report.md
```

## 3. Follow the math

Two machine-checked proofs and one checked graph argument, in [proofs/](proofs/), run by `make proof` in under five seconds. Both write the governor down as a small state machine and ask Z3 to prove by induction that certain states are unreachable, for any number of actions and any sequence of steps. Each file says in its docstring what it is about and what it is not about; read that first.

[proofs/core_invariants.py](proofs/core_invariants.py) proves, in the words of the file:

- P0. The edition counter never goes negative.
- P1. Nothing executes unless, when its ticket was issued, a rule allowed it and the witnesses were present.
- P2. A ticket exists only for an action the rule allowed, with witnesses, at issue time.
- P3. No replay: anything executed has its ticket marked spent, and a spent ticket is refused.
- P4. A ticket carries an edition no newer than the current one, and only the current edition is honoured.
- P5. Halt is absorbing: halted and no quorum means still halted after any step.
- P6. Fail closed: with the heartbeat lost, no step executes anything.
- P7. No ticket is issued while halted or while the heartbeat is lost.
- P8. The edition only moves forward.
- P9. An edition change needs a quorum.

Plus a non-vacuity check: an allowed action can in fact execute, so the proofs are not true because nothing ever happens.

[proofs/commit_point.py](proofs/commit_point.py) proves three safety properties of the hold, clearance and alarm protocol: (1) no irreversible high-severity action commits without a reviewer clearance, or a regulator all-clear inside its budget; (2) a clearance is bound to the action version it judged, and a re-parameterised action needs a new one; (3) a monitor that misses its budget always raises an alarm, and the action cannot commit on that verdict. Two liveness checks show the machine is not vacuous.

What the proofs found: the first draft of the core invariant let the edition counter go negative, and a state with edition minus one let an action with no ticket (also marked minus one) execute. The first draft of the commit-point protocol left the old deadline in place after a re-parameterisation, so a version bumped after the budget ran out sat with no verdict and no alarm. Both are described in the files and in docs/19 §2.

[proofs/no_global_kill_switch.py](proofs/no_global_kill_switch.py) is the third file: the model-to-world graph, minimum separators computed by max-flow and cross-checked by brute force, backing [docs/23](docs/23-there-is-no-kill-switch.md): no separator exists in the deep network, the cheapest network-side one sits next to every machine and takes bystanders with it, the ends give a separator of one node per instance or per effector, and reversibility shrinks it to the irreversible exits. The theorem is Menger's; the script checks the instance.

What the proofs are not about, in the files' own words: the physics (whether the wire really carries no bytes without a ticket), the cryptography (signatures are modelled as unforgeable), the lists and observers (an allowed action is whatever the signed rule says), and the link from the model to the RTL. That link is the formal work on the Verilog itself, experiment L7 in the program, not yet done. Whether the simulation takes only the steps the proven machine allows is experiment L4, which found that the model takes two steps the machine does not have (an "arm" step and burned tickets); that is open.

## 4. Follow the code proof

Three suites and an attack catalogue, all runnable in minutes without hardware.

| What | Where | Count | Command |
|---|---|---|---|
| Governor model: hypotheses H0 to H18 | `safety-governor/tests/` | 200 tests | `./run.sh` or `make test` |
| RTL blocks | `safety-governor/rtl/tests/` | 20 tests | `make rtl-test` |
| Halt-loop circuit | `safety-governor/hw/loop/` | 39 ngspice configurations | `make loop` |
| Reference stack: gate, ledger, endpoints, OASP path, transactional contract | `hardware-and-silicon/tests/` | 56 tests | `./run.sh` |
| Attack catalogue, every entry against a freshly built node | `hardware-and-silicon/hardware_ref/attacks.py`, report in `results/report.md` | 75 attacks blocked, 12 baselines allowed; 17 on the OpenShell and Sentry path, 5 on the provenance interface | `./run.sh` |
| Watermark study: 13 attacks through detector, retrieval and registry, plus a real-model run | `Watermark/` | 13 attacks, two committed runs | `./run.sh` |

A baseline is a legitimate operation that must go through; the catalogue carries them so a gate cannot pass by refusing everything. The report shows the reason code every entry produced, not a pass mark.

## 5. What is proven, tested, simulated, assumed, and open

| Grade | What | Where to check |
|---|---|---|
| Proven (Z3, by induction) | The core invariants P0 to P9 and the commit-point properties (1) to (3), on the abstract machine | `make proof`; docs/19 §2 |
| Tested (every run) | The functional model follows the rules (200 tests); the RTL blocks follow the model (20); the protocol holds against 75 attacks and lets 12 baselines through; OpenShell's shipped middleware contract (5 tests) | `./run.sh` in both repositories |
| Simulated | The halt loop opens and every governor detects it inside 1 ms, worst case 317 µs | docs/11; `make loop` |
| Assumed, and written down | Every input the gate trusts: who signs it, how fresh, what failure means | docs/06 |
| Open, with an experiment | Simulation conforms to the proven machine (L4); two gates read one policy the same way (L5); the physical path enumeration with a source per row and the retrofit columns (P2); the overhead numbers (N); the observer's miss rate (YB-0052 to 0054); the proofs on the Verilog (L7) | docs/20, the pull requests, `audit/wave-N/` |
| Not claimed | That the chip knows what words mean, whether the rulebook is good, whether a witness is right, or that fabrication and physical attack are solved | docs/19 §3 and §6 |

## 6. The experiment program, and how to read a result

[docs/20-experiment-program.md](docs/20-experiment-program.md) lists twenty experiments, one per claim, each with the condition that would disprove it and the exit criteria for leaving software. [docs/21-agent-run-plan.md](docs/21-agent-run-plan.md) says how coding agents run them in waves, on a budget, with a gate between waves. The gate has three readers: a script that checks what a script can check (no test weakened, no file outside the brief, the suite and the acceptance command in a clean checkout, no number without an artifact), a local model that lists every claim with the diff line that backs it, and a cloud model that must answer in a fixed shape with a file and a line for every finding, whose citations are checked before its verdict counts. A merge takes all three and a person.

Every wave leaves a packet: [audit/wave-1/](audit/wave-1/) holds the briefs, the agents' summaries, the acceptance logs, the verifier's output and the reviews, with `MANIFEST.sha256`. The pull requests carry the gate's findings as comments: [#14](https://github.com/YobieBenjamin/safety-governor/pull/14) (L4), [#15](https://github.com/YobieBenjamin/safety-governor/pull/15) (L5), [#17](https://github.com/YobieBenjamin/safety-governor/pull/17) (H1), [safety #7](https://github.com/YobieBenjamin/safety/pull/7) (YB-0052). Nothing merges until the gate passes it, so a result on a branch is a result under review, not a result.

If you are a model, or a person with time: [audit/PROMPT.md](audit/PROMPT.md) is the brief for an outside audit. Run the tests, reproduce every number, find a change that would make each test fail, and name what the program's own disproof conditions required and nobody tested.

## 7. Where this is going

[docs/22-roadmap-to-tapeout.md](docs/22-roadmap-to-tapeout.md) is the whole program in five stages: prove or disprove the theory in software (where we are), design the chip to fit NVIDIA's boards through documented interfaces, run the tests and the proofs on the chip itself, finish the design to the point where a foundry could take it, then stop and run it anyway, in RTL, in gates and on an FPGA, against the same catalogue. It says what done means at each stage and names the two walls: the rows of the physical-path register that only NVIDIA's NDA design guide can settle, and the fab.

## 8. Corrections, on the record

[docs/AUDIT-2026-10.md](docs/AUDIT-2026-10.md) lists what an audit found wrong in the first drafts, with sources: signature sizes, what DC-SCM actually carries, how DICE derives keys, and more. The catalogue count the first posts gave (66 attacks and 10 baselines) was stale; it is 75 and 12, corrected with a dated note. The two proof holes above are corrections too. The program publishes what it finds, whichever way it goes.

## Licence and citation

Documentation is CC BY-NC 4.0 ([LICENSE-DOCS.txt](LICENSE-DOCS.txt)); code is PolyForm Noncommercial 1.0.0 ([LICENSE.md](LICENSE.md)); attribution is required and commercial use needs a separate licence (yobie AT ieee DOT org). The terms and the notice text are kept once, in [autonomic-graph-regulation](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/main/LICENSING.md), and the other repositories point there.
