# Where every claim in the brief comes from

A check of the deck against the repositories, run on 21 October 2026, after the first wave of
experiments and the kill-switch work. Each line names the slide, the claim, the source in this
program's own work, and how it was verified. Nothing on a slide should be here as "my idea for
the talk"; the last section records what was removed from earlier drafts for not being from the
research. Slide numbers are the deck's own (34 slides).

## Numbers

| Slide | Claim | Source | Verified by |
|---|---|---|---|
| 4, 26, 28, 31 | 200 hypothesis tests pass (nineteen contracts) | `tests/` | `python3 -m pytest tests`: 200 passed |
| 4, 26, 28, 31 | 20 RTL block tests pass | `rtl/tests/test_blocks.py` | `python3 -m pytest rtl/tests`: 20 passed |
| 4, 16, 26, 31 | three proof files hold: the fourteen core invariants, the commit-point properties (1) to (3), the original kill-switch checks | `proofs/core_invariants.py`, `proofs/commit_point.py`, `proofs/no_global_kill_switch.py` | `make proof`: "All proofs hold" twice, "All checks hold" once; 3.7 s |
| 19, 26 | 56 tests in the reference stack, five of them the OpenShell contract | `hardware-and-silicon/tests/`, `hardware-and-silicon/tests/test_oasp.py` | `python3 -m pytest tests` in that repository: 56 passed; `hardware-and-silicon/docs/NVIDIA.md` describes the five contract tests; their names are in `hardware-and-silicon/tests/test_oasp.py` (five of its fourteen) |
| 2, 19, 26 | 75 attacks blocked, 12 baselines allowed; 17 of the 87 on the OpenShell and Sentry path (13 attacks, 4 baselines) | `hardware-and-silicon/results/report.md` | the report's own header line; the "NVIDIA OASP path" section counted: 17 rows |
| 26 | 317 µs worst case for the halt loop across 72 governors, 1 ms bound, 39 configurations | `hw/loop/results.md` | table row for N=72, last opener, 3 m hops: 317.15 µs total; 39 configuration rows; `docs/11` |
| 4, 26 | about 2 mm² of core logic, 1.4 by 1.4 mm, in a 10 mm² harness | `docs/04-specification.md` §11; `hw/librelane/governor_core/config.json`; `docs/AUDIT-2026-10.md` REVIEW-DIE-AREA-OVERSTATED | 1.4 × 1.4 mm = 1.96 mm² |
| 18, 29, 30 | P-384 signature 1,697,985 OTBN cycles, 17 ms at 100 MHz, one signature per 50 ms batch | `govsim/bench.py` constants; `tests/test_h09_overhead.py` | `OTBN_P384_SIGN_CYCLES = 1_697_985`, `SIGN_S ≈ 0.017`, `BATCH_WINDOW_S = 0.05` |
| 30 | engine 34 percent busy batched, 272 percent unbatched; firmware share under 0.1 percent | `govsim.bench.run("rack", gpus=2, requests=100, tokens_per_request=100, actions=0)` (the CONTRACT-GOVERNOR-OVERHEAD-BOUNDED test's call) | 33.96 percent, 271.7 percent, 0.044 percent (0.084 percent with the default actions); the test bound is 0.1 percent |
| 18 | mailbox of 21 signed commands, checked in order: sequence, edition, signature | `govsim/governor.py` `MAILBOX_CODES`, `_check_signed` | 21 codes; docstring and code order |
| 18 | HGX reset grouped: three PERST inputs for eight GPUs | `docs/research/board-lever-register.md` | register row, verified level |
| 18 | per-slot SMBus (SMBPBI), power brake, PERST#, PWR_EN, present and fault at the connector | `docs/figures/fig-rack.png`; `docs/03-interfaces.md`; the lever register | figure labels and register rows |
| 18, 33 | NSM port disable out of band; seven firmware asks | `docs/research/nvswitch-management.md` | `NSM_SET_PORT_DISABLE_FUTURE`; the asks section |
| 18 | AES-256-CTR with HMAC-SHA-256 for storage | `docs/04-specification.md` crypto table | table row |
| 2, 17, 18 | DC-SCM-class management module; the retrofit module in the slot a BMC card uses | `docs/01`, `docs/03`, `hw/pcb/rack-integration.md`, `docs/22` stage 2 | eight documents use the term; the retrofit columns are in `tools/github/experiments.json` (WAVE-EXIT-REGISTER: `from_module`, `undo_paths`) |
| 10, 11, 12 | the kill-switch model: a 60-node 6-regular core, 12 instances, 10 effectors, 20 users and 20 services (40 bystanders), one local pair | `proofs/no_global_kill_switch.py` `build()` | the script's docstring and `--percolation` header |
| 10, 11, 12 | 43-node edge cut; 72 percent of the core (43 of 60); 19 percent of bystander pairs (77 of 400); 11 effector controllers; 13 compute nodes; 6 irreversible effectors; no deep separator; local pair survives | `proofs/no_global_kill_switch.py` INVARIANT-NO-DEEP-NETWORK-SEPARATOR, INVARIANT-CHEAPEST-CUT-AT-ACCESS-LAYER, INVARIANT-NETWORK-CUT-HITS-BYSTANDERS, INVARIANT-LOCAL-PAIR-SURVIVES-CUT, INVARIANT-CONTROLLER-CUT-ONE-PER-EFFECTOR, INVARIANT-COMPUTE-CUT-ONE-PER-INSTANCE, INVARIANT-ONLY-IRREVERSIBLE-NEED-GATE | `python3 proofs/no_global_kill_switch.py` prints each line HOLDS with those numbers |
| 12 | INVARIANT-MAX-FLOW-MATCHES-BRUTE-FORCE: max-flow min cut 3 equals the brute-force cut 3 on the tiny instance | same, INVARIANT-MAX-FLOW-MATCHES-BRUTE-FORCE | same run |
| 12 | percolation: 70 percent of the core gone leaves 0.796 of AI roads and 0.792 of bystander roads; 90 percent leaves 0.202 and 0.210; 40 trials per point | `python3 proofs/no_global_kill_switch.py --percolation` | the CSV printed on 21 October 2026, copied into `build_deck.js` for the chart |
| 19 | OpenShell middleware: gRPC, gateway TOML, after network policy and before credentials, allow with header changes or deny with a code, reason-code grammar (lowercase letter first, then lowercase letters, digits, underscores, 64 bytes), timeout 10 ms to 30 s default 500 ms, 4 MiB payloads, fail closed when the service is down | `hardware-and-silicon/docs/NVIDIA.md`, "OpenShell's shipped middleware contract", read from `github.com/NVIDIA/OpenShell` `docs/extensibility/supervisor-middleware/` at main `837fdfd` on 21 October 2026 | the table in that section |
| 19, 25 | the three fixes: dotted codes to the grammar with a `gate_` prefix where needed; hold as a denial `hold_pending` with a once-only approved retry; a decision inside the timeout | `hardware-and-silicon/hardware_ref/oasp.py` (`openshell_reason_code`, `OpenShellResult`, `SupervisorMiddleware.approve`); `hardware-and-silicon/tests/test_oasp.py` | the five tests pass; Part 5, "How it plugs into OpenShell" |
| 27 | WAVE-TRACE-CONFORMANCE-REPLAY: all 200 traces replay; two broken governors fail with the event named; the replayer widened for a boot ("arm") step and burned tickets; heartbeat events never recorded; PR #14 | `audit/wave-1/REPORT.md` (the section on WAVE-TRACE-CONFORMANCE-REPLAY, runner id L4), `audit/wave-1/review/L4/`, `audit/wave-1/L4.revise-*.comment.md` | the agent's last words and the review in the packet |
| 27 | WAVE-DIFFERENTIAL-GATE-TEST: 21 catalogue entries compared, 18 agree, five disagreements, each pinned with its inputs; the policy document never read; one point at a bug; 21 of 87; PR #15 | `audit/wave-1/REPORT.md` (the section on WAVE-DIFFERENTIAL-GATE-TEST, runner id L5), `audit/wave-1/review/L5/` | same |
| 27 | WAVE-LANES-CONFORMANCE-SUITE: fixtures for every message type, `make lanes` passes, catalogue exported as 87 entries, the envelope mismatch (16-hex signer, hex signature, no key versus 8, base64, embedded key); PR #17 | `audit/wave-1/REPORT.md` (the section on WAVE-LANES-CONFORMANCE-SUITE, runner id H1), `audit/wave-1/review/H1/` | same |
| 27 | WAVE-OBSERVER-EVALUATION-SET: 134 requests, six hazard families, scorer with bootstrap intervals, two baselines, pre-registration note, 36 tests; the four review findings | the `safety` repository's wave-1 review, quoted in Part 5 ("The observer's evaluation set") | Part 5's text; the packet lives in that repository, not in this one |
| 26, 27 | nothing merged from wave 1; PRs 14, 15 and 17 open and unmerged (WAVE-TRACE-CONFORMANCE-REPLAY and WAVE-LANES-CONFORMANCE-SUITE carry the waiting-for-a-person marker; WAVE-DIFFERENTIAL-GATE-TEST's last comment says the gate reviews the branch again); WAVE-OBSERVER-EVALUATION-SET in revision | GitHub refs on 21 October 2026 (`exp/l4` = pull 14, `exp/l5` = pull 15, `exp/h1` = pull 17, main at 96dc5cc) | `git ls-remote` of the repository |
| 6 | the papers behind each rung of the ladder | `docs/24-the-ladder.md` §7, with arXiv addresses | each address opened on 21 October 2026 |
| 31 | flexHEG Part I (Petrie, Aarne, Ammann, Dalrymple; ARIA; April 2025; arXiv 2506.15093); CNAS "Secure, Governable Chips" (January 2024); RAND; Ansari's feasibility taxonomy (University of Chester; April 2026; arXiv 2604.04712) | `docs/18-viability-and-open-questions.md` §8b | the section's own citations |
| 2, 28 | the five stages and where each stands | `docs/22-roadmap-to-tapeout.md` | the document's stage headings and "where it stands" lines |

## Mechanisms and reason codes

| Slide | Claim | Source |
|---|---|---|
| 4 | tamperproof, always invoked, verifiable: the three tests of a reference monitor | `docs/00-objectives.md` GOAL-SMALL-ENOUGH-TO-VERIFY; `docs/18` §1; `docs/24` rung 4 |
| 4, 13 | a monitor is complete only where every path passes through it, and Menger says that is the ends | `docs/23-there-is-no-kill-switch.md` §3 and §5 |
| 4 | fused secret, ROM boot, extend-only registers, anti-rollback counter, k-of-n signatures | blog post 01 layer 0; `docs/00` GOAL-KEYS-OUT-OF-VENDOR-HANDS; `tests/test_h03_quorum.py` |
| 4 | the five crossings | `docs/17-use-cases.md` §1 (four) plus power, reset and clock in `docs/18` §1 |
| 5, 6, 7, 8 | the ladder: six rungs, where each lives, what removes it, what it sees, what it can say; witnesses versus locks; the person on the only path | `docs/24-the-ladder.md` §2, §3 and §4; `docs/figures/fig-ladder-witnesses.png`, `fig-ladder-person.png` |
| 9, 11 | three corrections to the popular argument (replicated, not interconnected; no deep switch, only an edge cut; too little as well as too much); three assumptions; three claims | `docs/23` §1 and §3a; Part 6, "The proof, for those who want it" |
| 10 | the Iran and North Korea point: an edge cut on one region with a hole | Part 6, "But Iran switched off the Internet"; its source list (Access Now, #KeepItOn; Kwangmyong) |
| 11 | the standing offer: show one network node every AI depends on and the post comes down | Part 6, "What the proof does not say" |
| 13 | a separator stops traffic; a gate in the separator lets through what a signed rule allows; the device checks again | `docs/23` §5; `proofs/core_invariants.py` |
| 15 | what is seen at a crossing; never seen; delegated with three guarantees; two bridges | `docs/17-use-cases.md` §1; `test_observer_is_always_invoked_and_cannot_be_impersonated` (CONTRACT-OVERSIGHT-SURVIVES-MODEL) |
| 16 | the ten original core invariants in the words of the proof file; the commit-point properties; the two holes (negative edition; the stale deadline) | `proofs/core_invariants.py`, `proofs/commit_point.py`; `docs/19` §2; Part 5, "What proving found" |
| 16 | the chain from proof to silicon: govsim (200 tests), RTL (20 tests), WAVE-FORMAL-PROOFS-ON-VERILOG on the Verilog | `docs/19` §2 and §3; `docs/20` WAVE-FORMAL-PROOFS-ON-VERILOG; `docs/22` stage 3 |
| 17 | retrofit: a module in the BMC slot; two catches, can the slot drive the levers and what can undo them | Part 5, "What we are building, in plain terms"; `tools/github/experiments.json` WAVE-EXIT-REGISTER |
| 22 | one bad prompt among a billion: the five layers, missed / STOP not GO / host policy allows / NO / holds; words only, an action, the record and the levers | `hardware-and-silicon/blog/figures/fig_bad_prompt.png` and Part 5, "One bad prompt, start to finish" |
| 23 | inside the chip: the six inputs, burned in, measured boot, the ten questions in order, ledger, log, mailbox, the six outputs | `hardware-and-silicon/blog/figures/fig_chip_inside.png` and Part 5, "Inside the chip"; `docs/04` §5 and §6 |
| 24 | the ticket is one-time, bound to a hash of the exact fields; a changed amount breaks the hash; a second presentation is refused | blog post 01 (layers 0, 4 and 5); `tests/test_h17_use_cases.py` |
| 25 | `mailbox.bad_sequence`, `mailbox.bad_signature`, `model.not_evaluated`, `gate.constraint.target.in_denied_list`, `endpoint.target_protected`, `gate.witness_missing`, `gate.held_for_human`, `release.hazard_class_not_allowed`, `release.session_hazard_budget_exceeded`, `compute.budget_exceeded`, `ticket.missing`, `ticket.replay`, `ticket.bad_signature`, `ticket.wrong_endpoint`, `ep.no_capability`, `gate.output_unpresented` | `govsim/reasons.py`; `govsim/policy.py` composes the denied-list code; `docs/17` quotes it from the strike narration |
| 25 | `attestation_missing`, `hold_pending`, `sandbox_quarantined` as OpenShell sees them | `hardware-and-silicon/hardware_ref/oasp.py` `openshell_reason_code`, `HOLD_PENDING`; `hardware-and-silicon/tests/test_oasp.py` |
| 25 | CONTRACT-ATTESTATION-BINDS-PERMISSIONS, CONTRACT-EVERY-CROSSING-GOVERNED, CONTRACT-POLICY-QUORUM-NO-ROLLBACK, CONTRACT-COMPARATOR-SURVIVES-COMPROMISE, CONTRACT-OVERRIDE-SLOW-AND-LOGGED, CONTRACT-SHARED-BUDGET-NO-OVERSPEND, CONTRACT-NO-ACTION-WITHOUT-TICKET, CONTRACT-OVERSIGHT-SURVIVES-MODEL as the backing hypothesis sets | the test file names under `tests/` |
| 20, 21 | the six layers, their mechanisms, and the NVIDIA mapping (OpenShell policy prover, Sentry on BlueField-4 as the required witness, both witnesses for high-authority actions, DOCA application next, I/O-stage block eventually, GPU and DPU roots bound) | blog post 01, "The layer model" table; `hardware-and-silicon/docs/NVIDIA.md`, "Sentry's verdict is required" and the dual-witness rule |
| 30 | loop beacon in the heartbeat; loss of current declared after two sense periods; a jumpered governor caught within two heartbeats; FMEA | `docs/02` §loop rules; `docs/04` timing table; `test_jumpered_governor_is_caught_by_the_beacon_within_two_heartbeats` (CONTRACT-HALT-REACHES-EVERY-GPU); `docs/07` §5 |
| 29, 30 | reach: options A to D; the credential moved behind an adapter | `docs/18` §5 |
| 29, 30 | coverage and people: the two limits no theorem removes | `docs/23` §6; `docs/18` questions 1 and 14 |
| 30, 31 | open questions 15 and 16: supply chain and enclosure; a multilateral root | `docs/18` §8 rows 15 and 16, §8b |
| 32, 33 | the asks and what each settles; what would disprove it; the outside audit by models that wrote none of this | `docs/18` §8 and §9; `docs/21`; `audit/PROMPT.md`; Part 5, "What happens next" |
| 14 | abliteration removes refusal in an afternoon on a consumer GPU; a judge is a transformer too | blog post 01, "Why one layer is never enough"; Arditi and others 2024 in `docs/24` §7 |
| 19 | Sentry announced 28 September 2026 for BlueField-4; the Open Secure AI Alliance (July 2026, Linux Foundation since September) and its "trusted foundation" sentence | `docs/AUDIT-2026-10.md` REVIEW-SENTRY-SCOPE-MISSTATED; `hardware-and-silicon/docs/NVIDIA.md`; Part 5 |

## Pictures, and where each one comes from

| Slide | Picture | Source |
|---|---|---|
| 1 | the halt loop drawn as a ring with one open governor | `docs/02` |
| 3 | a judge model is a witness; it can keep a gate shut, it can never be the gate; only the silicon layer can be the lock | blog post 01 |
| 4 | a firewall for actions with a hand on the breaker; a chip that can only ask the GPU nicely is a classifier with a heatsink | `docs/18` §2; `docs/00` GOAL-OWN-GOVERNOR-PER-GPU |
| 5, 7, 8 | the staircase of six rungs, witnesses versus locks, the person on the only path; "prompts are advice, training is a habit, watchers are witnesses, the sandbox is a fence around the operator's own yard" | `docs/24` §6 |
| 9 | Menger's theorem with roads and guards (`fig_ks_menger.png`) | Part 6, "A hundred-year-old theorem about guards" |
| 9, 13 | a switch stops everything; a gate lets through what a signed rulebook allows | Part 6, "So where does the switch go?"; `docs/23` §7 |
| 10 | the five cuts chart (`fig_ks_cuts.png`) | Part 6, "Where could the switch go?"; the numbers from the proof script |
| 11 | why the smallest cut is at the smaller end (`fig_ks_smaller_end.png`) | Part 6, "The graph theory, in four pictures" |
| 12 | the percolation chart, redrawn natively from the script's table | Part 6, same section; `--percolation` |
| 13 | gates at both ends with the mesh between (`fig_ks_exits.png`) | Part 6, "So where does the switch go?" |
| 14 | the customs officer who cannot read the paperwork | `docs/17` §1 |
| 15 | two bridges | `docs/17` §1 |
| 16 | "reading is not checking. I knew that. I still had to be shown." | Part 5, "What proving found" |
| 17 | the referee with a whistle and a rulebook he did not write | `docs/18` §1 |
| 19 | "fine by me. That is the chip." | Part 5, "How it plugs into OpenShell" |
| 20 | biology separates the alarm from the muscle: the spinal reflex | blog post 01, layer 3 |
| 22 | the one-bad-prompt flow (the blog's `fig_bad_prompt.png`, redrawn as shapes); "scale is the point, not the problem" | Part 5 |
| 23 | inside the chip (the blog's `fig_chip_inside.png`, redrawn as shapes); "what it cannot know" | Part 5 |
| 24 | change the amount and the hash breaks; present it twice and the second is refused | blog post 01 |
| 27 | "the wave cost a few bucks and a quarter of an hour" | Part 5, "Promising, and not" |
| 28 | "if an experiment kills the chip as designed, that is the result" | Part 5, "What happens next"; `docs/22` stage 1 |
| 29 | the perimeter firewall decides whether the packet leaves, not what the far server does | `docs/18` §5 |
| 31 | "same mechanisms, because they are the right mechanisms" | `docs/18` §8b |
| 2, 32 | the same catalogue of attacks is the acceptance test for every stage; 1000 percent sure in the pre-hardware phase | blog post 01 roadmap; `docs/22`; your own rule for the program |
| 34 | "there is no kill switch. There are gates, at the ends." | `docs/23` §7 |

The five figure files under `figures/` (four of them used; the percolation chart is drawn natively in the deck) are copies of the blog's, generated by
`hardware-and-silicon/blog/tools/make_figures.py`; the deck crops their title band (the top
176 pixels of the 200 dpi render) so the slide's own title is the only title.

## Removed from earlier drafts of the deck

The first drafts had illustrations invented for the talk, not taken from the research, and they
are gone: the smoke alarm and the fire door, the bank with its teller and vault, the boarding
pass, the bridge before the steel is ordered, and a three-step timeline that replaced the post's
own roadmap. Two codes were shown as Python constant names rather than as the model prints
them (`OUTPUT_UNPRESENTED`, `COMPUTE_BUDGET`); the deck prints `gate.output_unpresented` and
`compute.budget_exceeded`. A "0.01 percent firmware share" was one run's figure; the deck states
the tested bound, under 0.1 percent. The four-phase roadmap of the first deck is replaced by the
five stages of `docs/22`, which is the program's plan of record now. The wave's dollar cost is
not printed, because the two reports disagree on what they count (the safety-governor report
says 0.69 dollars for its three experiments; Part 5 says about 3.30 dollars for the four across
both repositories); the strip says "a few bucks", which both support.

## Not in the research

The year 1972 for the reference-monitor idea (the Anderson report) and 1927 for Menger's theorem
are general knowledge, cited in `docs/23` and `docs/24` rather than figures from this program's
own work. The papers on slide 6 are the literature, cited in full in `docs/24` §7.
