# Where every claim in the brief comes from

A check of the deck against the repositories, run on 16 October 2026. Each line names the
slide, the claim, the source in this program's own work, and how it was verified. Nothing on a
slide should be here as "my idea for the talk"; where an earlier draft of the deck had one,
the last section records what was removed.

## Numbers

| Slide | Claim | Source | Verified by |
|---|---|---|---|
| 4, 13 | 200 hypothesis tests pass (H0 to H18) | `tests/` | `python3 -m pytest -q tests`: 200 dots, 100 percent |
| 4, 13 | 20 RTL block tests pass | `rtl/tests/test_blocks.py` | `python3 -m pytest -q rtl/tests`: 20 dots |
| 13 | 317 µs worst case for the halt loop across 72 governors, 1 ms bound, 39 configurations | `hw/loop/results.md` | table row for N=72, last opener, 3 m hops: 6.15 µs electrical, 311 µs digital, 317.15 µs total, 682.85 µs margin; 39 configuration rows |
| 4, 13 | about 2 mm² of core logic, 1.4 by 1.4 mm, in a 10 mm² harness | `docs/04-specification.md` §11; `hw/librelane/governor_core/config.json`; `docs/AUDIT-2026-10.md` S9 | 1.4 × 1.4 mm = 1.96 mm² |
| 8, 14, 15 | P-384 signature 1,697,985 OTBN cycles, 17 ms at 100 MHz, one signature per 50 ms batch | `govsim/bench.py` constants; `tests/test_h09_overhead.py` | `OTBN_P384_SIGN_CYCLES = 1_697_985`, `SIGN_S ≈ 0.017`, `BATCH_WINDOW_S = 0.05` |
| 15 | engine 34 percent busy batched, 272 percent unbatched; firmware share under 0.1 percent | `govsim.bench.run("rack", gpus=2, requests=100, tokens_per_request=100)` | 33.96 percent, 271.7 percent, 0.044 percent; the test bound is 0.1 percent |
| 8 | mailbox of 21 signed commands, checked in order: sequence, edition, signature | `govsim/governor.py` `MAILBOX_CODES`, `_check_signed` | 21 codes; docstring and code order |
| 2, 13 | 75 attacks blocked, 12 baselines pass, 37 tests, in the reference stack | `hardware-and-silicon` `results/report.md` (the blog post 01 said 66 and 10; the catalogue grew with posts 3 and 4) | the report's own figures |
| 8 | HGX reset grouped: three PERST inputs for eight GPUs | `docs/research/board-lever-register.md` | register row, verified level |
| 8 | per-slot SMBus (SMBPBI), power brake, PERST#, PWR_EN, present and fault at the connector | `docs/figures/fig-rack.png`; `docs/03-interfaces.md`; the lever register | figure labels and register rows |
| 8, 17 | NSM port disable out of band; seven firmware asks | `docs/research/nvswitch-management.md` | `NSM_SET_PORT_DISABLE_FUTURE`; the asks section |
| 8 | AES-256-CTR with HMAC-SHA-256 for storage; no GCM on OpenTitan's AES | `docs/04-specification.md` crypto table; audit | table row |
| 8 | DC-SCM-class management module | `docs/01`, `docs/03`, `hw/pcb/rack-integration.md` | eight documents use the term |

## Mechanisms and reason codes

| Slide | Claim | Source |
|---|---|---|
| 4 | tamperproof, always invoked, verifiable: the three tests of a reference monitor | `docs/00-objectives.md` G5 ("the third test of a reference monitor"); `docs/18` §1 |
| 4 | fused secret, ROM boot, extend-only registers, anti-rollback counter, k-of-n signatures | blog post 01 layer 0; `docs/00` G8; `tests/test_h03_quorum.py` |
| 4 | the five crossings | `docs/17-use-cases.md` §1 (four) plus power, reset and clock in `docs/18` §1 |
| 6 | what is seen at a crossing; never seen; delegated with three guarantees; two bridges | `docs/17-use-cases.md` §1; `test_observer_is_always_invoked_and_cannot_be_impersonated` (H18) |
| 11 | the ticket is one-time, bound to a hash of the exact fields; a changed amount breaks the hash; a second presentation is refused | blog post 01 (layers 0, 4 and 5); `tests/test_h17_use_cases.py` |
| 12 | `mailbox.bad_sequence`, `mailbox.bad_signature`, `model.not_evaluated`, `gate.constraint.target.in_denied_list`, `endpoint.target_protected`, `gate.witness_missing`, `gate.held_for_human`, `release.hazard_class_not_allowed`, `release.session_hazard_budget_exceeded`, `compute.budget_exceeded`, `ticket.missing`, `ticket.replay`, `ticket.bad_signature`, `ticket.wrong_endpoint`, `ep.no_capability`, `gate.output_unpresented` | `govsim/reasons.py`; `govsim/policy.py` line 223 composes the denied-list code; `docs/17` quotes it from the strike narration |
| 12 | H1, H2, H3, H6, H8, H13, H17, H18 as the backing hypothesis sets | the test file names under `tests/` |
| 15 | loop beacon in the heartbeat; loss of current declared after two sense periods; a jumpered governor caught within two heartbeats; FMEA | `docs/02` §loop rules; `docs/04` timing table; `test_jumpered_governor_is_caught_by_the_beacon_within_two_heartbeats` (H11); `docs/07` §5 |
| 14, 15 | reach: options A to D; the credential moved behind an adapter | `docs/18-viability-and-open-questions.md` §5 |
| 15, 17 | observers' error rate open; quorum of observers; red team | `docs/18` §8, questions 2 and 12; `docs/17` proves/does-not table |
| 16, 17 | the asks and what each settles; what would disprove it | `docs/18` §8 and §9 |
| 9, 10 | the six layers, their mechanisms, and the NVIDIA mapping (OpenShell policy prover, Sentry on BlueField-4 as the required witness, DOCA application next, I/O-stage block eventually, GPU and DPU roots bound) | blog post 01, "The layer model" table |
| 5 | abliteration removes refusal in an afternoon on a consumer GPU; a judge is a transformer too | blog post 01, "Why one layer is never enough" |
| 4 | Sentry announced September 2026 for BlueField-4 | `docs/AUDIT-2026-10.md` S8 |

## Analogies, and where each one comes from

| Slide | Picture | Source |
|---|---|---|
| 3 | a judge model is a witness; it can keep a gate shut, it can never be the gate; only the silicon layer can be the lock | blog post 01 |
| 4 | a firewall for actions with a hand on the breaker; a chip that can only ask the GPU nicely is a classifier with a heatsink | `docs/18` §2 (the firewall remark was yours); `docs/00` G2 |
| 5 | the customs officer who cannot read the paperwork | `docs/17` §1 |
| 6 | two bridges | `docs/17` §1 |
| 7 | the referee with a whistle and a rulebook he did not write | `docs/18` §1 |
| 9 | biology separates the alarm from the muscle: the spinal reflex | blog post 01, layer 3 |
| 11 | change the amount and the hash breaks; present it twice and the second is refused | blog post 01 |
| 14 | the perimeter firewall decides whether the packet leaves, not what the far server does | `docs/18` §5 |
| 2, 16 | the same catalogue of attacks is the acceptance test for every phase; 1000 percent sure in the pre-hardware phase | blog post 01 roadmap; your own rule for the program |

## Removed from earlier drafts of the deck

These were illustrations invented for the talk, not taken from the research, and they are gone:
the smoke alarm and the fire door, the bank with its teller and vault, the boarding pass, the
bridge before the steel is ordered, and a three-step timeline that replaced the post's own
four-phase roadmap. Two codes were shown as Python constant names rather than as the model
prints them (`OUTPUT_UNPRESENTED`, `COMPUTE_BUDGET`); the deck now prints
`gate.output_unpresented` and `compute.budget_exceeded`. A "0.01 percent firmware share" was
one run's figure; the deck now states the tested bound, under 0.1 percent.

## Not in the research

The year 1972 for the reference-monitor idea (the Anderson report) is general knowledge, not a
figure from this program's documents, and the deck no longer prints it.
