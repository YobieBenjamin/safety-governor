# The design documents

Two reading orders. Both cover the whole design; they differ in depth.

**Plain English first.** `10-plain-english-walkthrough.md` tells the design as one story in
fifteen sections, with the six figures, and under every section a box that names the
technical document, the model code, the test and the hardware block behind it.
`09-analogies.md` is the same vocabulary as a table: one everyday picture per feature, the
reason for the feature, and what it does not do.

**Technical first.** The numbered documents, in order. Each one opens with a plain-words
summary and a "backed by" box.

| Doc | What it settles | Plain-English section |
|---|---|---|
| `00-objectives.md` | Goals G1 to G8, requirements R1 to R32 with where each is tested, non-goals N1 to N7, the three tiers, the acceptance rule | §1, §15 |
| `01-architecture.md` | Where the governor lives in the rack, the blocks on the die, boot, the job lifecycle, the safe-mode ladder, multi-GPU | §2 to §5 |
| `02-safety-fabric.md` | The halt loop and the message fabric: rules, message types, roster formation, cluster-atomic epoch change, heartbeat fan-out, shared budgets, cross-linked logs, partitions | §6 |
| `03-interfaces.md` | Every plug: the GPU, the switches, the host, memory, the DPU, action endpoints, other governors; the asks to NVIDIA; the pin summary | §2, §7 |
| `04-specification.md` | Register map, mailbox commands, policy image, request and ticket formats, provenance record, crypto suite and key hierarchy, firmware, timing, memory, physical targets | §8, §9, §14 |
| `05-threat-model.md` | Adversaries; what is stopped (with tests), what is only made expensive, what is not addressed | §10 |
| `06-assumptions-register.md` | The one-row-per-input register the policy loader demands | §11 |
| `07-verification-plan.md` | Hypotheses H0 to H16 and what falsifies each; tiers in simulation; RTL invariants; silicon validation; FMEA; proof assumptions | §12 |
| `08-silicon-plan.md` | OpenTitan as the base; Leg A on sky130 through LibreLane and a shuttle, with lithography explained; Leg B on 22FDX; Leg C the rack module; schedule and cost classes; the tape-out checklist | §13 |
| `09-analogies.md` | Every feature as an everyday picture | all |
| `10-plain-english-walkthrough.md` | The whole design in plain English, cross-referenced | itself |
| `11-loop-timing.md` | The halt loop as a circuit: ngspice simulation of propagation and detection time across 72 governors | §6 |
| `AUDIT-2026-10.md` | The audit: hallucinations and fake conditions found and fixed, sources checked, what is still unverified | §15 |
| `../tools/console/` | The live program console published on claude.ai: agents, work items, event log | n/a |
| `../tools/github/` | `setup_and_publish.sh`: one script for a fresh machine (gh, login, clones, bundles, push, publish); `publish_experiments.sh`: labels and one issue per experiment in each repository, from `experiments.json` | n/a |
| `../tools/archive/` | The archive on claude.ai: `make archive` stages every file, full git bundles, zips and the index page, and builds the Project's consolidated documents | n/a |
| `17-use-cases.md` | How the governor catches a safety issue before the action initiates: the five paths, a weapons release, a hazardous-knowledge request, an agent with a plan, and oversight that survives the model | all |
| `18-viability-and-open-questions.md` | Is it plausible, is it a firewall, where its authority ends (a payment three hops away), who adopts first, whether it strengthens NVIDIA's promise, fourteen open questions and the next three moves | §15 |
| `19-how-solid-is-the-theory.md` | What is a theorem (with the Z3 proofs in `../proofs/`), what is engineering, what is trust; the review protocol for another model | §15 |
| `20-experiment-program.md` | The experiment program across `safety-governor`, `safety` and `autonomic-graph-regulation`: every claim's experiment, where it lives, what disproves it, the exit criteria; the ledger is `../EXPERIMENTS.md` | §15 |
| `21-agent-run-plan.md` | Running the program with agents: waves, budgets, where the tokens go; the launcher is `../tools/agents/run_wave.sh`, the issues come from `../tools/github/experiments.json` | §15 |
| `research/board-lever-register.md` | Evidence register: which boards expose which lever signals, with sources and evidence levels | §15 |
| `research/nvswitch-management.md` | Evidence register: NVLink authority out of band and in band; the seven firmware asks | §7, §15 |

## One document

`safety-governor-design.docx` is all of the above plus the hardware references, the audit and
the sweep report in one file with the figures, built by `tools/build_master_docx.py` (`make
docx`; pandoc and python-docx). The Markdown files are the originals.

## Figures

Drawn by `figures/make_figures.py` (matplotlib only) from the same facts the text states;
regenerate them with `python3 docs/figures/make_figures.py` after a design change.

| Figure | Shows | Used in |
|---|---|---|
| `figures/fig-rack.png` | The compute tray: system board, governor module, per-slot wires, baseboard, switches, the loop and the fabric | README, `01`, `03`, `10` |
| `figures/fig-die.png` | The governor die: root of trust, rules and permissions, record, stopping, interfaces | `01`, `10` |
| `figures/fig-boot.png` | Boot, the two measurements, the DICE key chain, what comes up halted | `01`, `10` |
| `figures/fig-safe-mode.png` | HALTED_INITIAL, RUN, THROTTLE, HALT, SAFE; local versus loop-opening causes; CLEAR | `01`, `10` |
| `figures/fig-halt-loop.png` | The series current loop through the governors, as a circuit | `02`, `10` |
| `figures/fig-request.png` | One request through the mailbox, the four questions, ticket or hold or refusal, the endpoint comparator | `04`, `10` |

## The code behind the documents

| Layer | Where | Run |
|---|---|---|
| Functional model of the governor and a simulated rack | `../govsim/` | `python -m govsim.cli demo`, `bench`, `sweep` |
| Hypothesis tests H0 to H18 (200 tests) | `../tests/` | `python -m pytest tests` |
| Machine-checked proofs: the core invariants and the commit-point protocol (Z3) | `../proofs/` | `make proof` |
| Hard-core RTL blocks (Amaranth) and their simulations | `../rtl/governor_rtl/`, `../rtl/tests/` | `make rtl`, `python -m pytest rtl/tests` |
| Generated Verilog | `../rtl/gen/` | checked in; CI regenerates and diffs |
| Silicon flow, pinout, rack wiring | `../hw/` | `make gds` (Docker) |
| The current pass/gap matrix | `../results/report.md` | `./run.sh` |
