# Fact-check of the generated documents, 22 October 2026

Everything in this program that reads well was written fast, some of it by me at two in the
morning and a lot of it with an AI at the keyboard. That is how you get a document that
says the chip "signs its tickets in batches" when the code batches something else, or a
proof that leans on an assumption it never stated. So on 22 October three independent
readers, none of which had seen the documents being written, went through the lot with the
code, the tests, the proofs and the primary sources open, and wrote down every place where a
sentence and the evidence disagree. This is the record: what was checked, what was wrong,
what changed, and what the program still owes.

The rule for the fix was the smallest true sentence. Where the code was right and the
document was wrong, the document changed. Where the document described something the model
does not do, the document now says so, and the gap is in the list at the end for the
program to close. No code changed to make a document true, with one exception, a check
added to a proof script, noted below.

## 1. What was checked and how

| Document | Reader's method | Findings |
|---|---|---|
| `25-the-rulebook-and-the-board.md` | Every file, function, test, constant, reason code, number and cross-reference checked against `govsim/`, `tests/`, `proofs/`, `rtl/`, `docs/`, `hw/` and the sibling repository; behaviour claims the tests do not cover were probed by running the model | 35 (10 wrong, 6 unsupported, 14 imprecise, 5 cosmetic) |
| `docs/brief/build_deck.js` (the 34-slide brief) | Each slide's claims against the same sources plus `audit/wave-1/`; the bench and the proofs run | 29 (6 wrong, 3 unsupported, 18 imprecise, 2 cosmetic) |
| Blog Parts 5, 6 and 7 (`hardware-and-silicon/blog/06`, `07`, `08`) | All 220 tests, `make proof`, `make loop`, the bench and the reference stack's 56 tests run; standards and the NVIDIA and OpenAI facts checked on the web | 32 (5 wrong, 9 unsupported, 13 imprecise, 5 cosmetic) |
| `24-the-ladder.md` and `23-there-is-no-kill-switch.md` | Every paper's id, authors, year and attributed result confirmed from the arXiv record; every repository reference opened; the kill-switch script run and its claims recomputed by hand | 20 (5 wrong, 4 unsupported, 7 imprecise, 4 cosmetic) |

Severity, as the readers used it: **wrong** is contradicted by the evidence; **unsupported**
has nothing behind it; **imprecise** is the right idea with the wrong number or word;
**cosmetic** is a label or a reference. Every finding was applied unless this record says
otherwise. The three reports are summarised below; the full tables live in the session
that produced them and the substance is here.

## 2. docs/25, the rulebook and the board

The document was written from the design and then checked against the model. The model won
every argument, which is the correct outcome and also the embarrassing one.

What was wrong and is fixed:

- An expired rulebook is refused at **commit** and at boot, not at stage, and not on every
  request afterwards. `_cmd_policy_propose` checks quorum, rollback, register and budget
  owners; `policy.expired` lives in `_accept_policy` only, which `test_h03_quorum` pins.
  The per-request expiry claim is gone; the figure `fig-no-order` was renumbered to match.
- The hazard budget is a **local rate window on each governor's own ledger**
  (`hazard|session`), not a shared budget with one owner over the fabric. Only the payment
  budget is owned over the fabric (H13). The scenario text, the figure note and §7 now say so.
- `approvers_quorum` only means anything when the rule's mode is **human**. The strike rule
  in the model runs as observer mode with a risk ceiling; a passing witness mints a ticket,
  no hold. The strike row and §3 changed.
- There is no separate "is the form well formed" step: the typed-field check runs inside
  `select_rule`, after attestation, the token, replay and alarms. Row 1 was deleted and
  `.missing` moved into the rule row.
- The release gate checks the **hazard budget before the class**, and that order is
  load-bearing (`test_h17` gets `session_hazard_budget_exceeded` on the third hazard only
  because of it). Three places and the figure reordered.
- The mailbox order (sequence, edition, signature) is pinned by
  `tests/test_h03_quorum.py::test_mailbox_reports_the_first_failing_check` and
  `rtl/tests/test_blocks.py`, not by `test_h00_contract.py`.
- `revocations` is in the schema and **never read** by the model. Said plainly now; in the
  gap list.
- `02-safety-fabric.md` references: the straggler is §2, shared budgets are §2; there is no §6.

What was unsupported and is now qualified: `sandbox` is honoured by `open_ports_for_roster`
only, not by `CAP_REQUEST` (a sandboxed roster peer can still be granted a flow); `digest_of`
is a register-derivation constraint, not a typed limit the gate evaluates; a verdict is
accepted from **any** key in the image's `observer_keys`, the rule's own list only drives the
register check; `COMMIT` is accepted from any endpoint key in the image, the binding to the
ticket's endpoint is enforced by the device; tokens in the model come from the GPU's counter,
not from the presented streams; OpenShell's network policy is derived from the hardware_ref
gate policy's `egress` block, which the govsim image does not have.

Imprecise, fixed: OpenShell has no 202, a hold is a deny that says `hold_pending`; the
reworded second hazard is parked as a hold with a session-scoped sticky alarm, released by
the rule's approvers; rollback is refused strictly below the fused counter or not above the
running edition; RTL status 6 is "governor not running"; six attestation checks, five pinned
by H1; freshness is H2, witness staleness H17, impersonation H18; the buffer policy is the
integrated tier's; `hazard_budget` defaults to none and the narration sets max 1; the meter's
alarm is about cycles; the PCIe port is programmed for host and roster peers; the heartbeat
is checked in `tick` and shows up as `governor_not_running`; a reused token from a legitimate
`BEGIN_MODEL` passes the fingerprint check (only the manifest-in-report ask closes it); docs/18
§8 rows 15 and 16, not §8b; `04-specification.md` §4 extended with the fields the model has
(`eval_keys`, `deployment_gate`, `buffer_classes`, `buffer_policy`, `audit`,
`streams_required`, `compute_budget`, `sandbox`, the rule's `in` and release fields,
`hazard_budget`).

## 3. The brief (the deck)

Fixed in `build_deck.js` and the deck rebuilt: L5's numbers are 20 of 87 compared, 17 agree,
five disagreements pinned; the envelope signer fields are identical across repositories
(`sha256[:8]` as 16 hex characters both sides), the real gap is hex versus base64 and the
missing embedded key, and it is a recorded gap, not a failing test; the L4 replayer
re-encodes the guards and does not drive the Z3 machine, 199 of 200 traces plus one expected
refusal, and its heartbeat check cannot fail because the sink emits `heartbeat_lost` right
before it; the column is "What was found", not "What the gate found"; the tests run racks of
up to five GPUs, the 72 is the loop simulation; the HGX per-slot levers are grouped on
today's board and the per-module signals sit behind NDA; the seven firmware asks are all
NSM, HMC and Fabric Manager items, the copy-engine and peer-MMU checkers are a silicon ask
for a future generation; eleven of the twenty-one mailbox commands are signed, the rest
authenticate their payload or are open by design; the ten gate questions now match
`_cmd_request` (form check inside the rule step; a dead heartbeat or an expired rulebook
stops the chip before any handler runs); P3 and P4 worded as proven; 17 ms at 100 MHz is
34 ms at the sky130 prototype's 50 MHz, where the batched engine would be 68 percent busy;
the codes-to-tests rows corrected (session hazard budget is H17, compute budget H18,
unpresented output H10); k per pair, not per machine; the board tier in docs/01's words;
"P2 register pending"; twenty-three experiments; N2 models and N3 measures; NSM port disable
applies from the next reset today, apply-now is ask 1; the sub-millisecond answer is the
model's and unmeasured; `gate.not_attested` beside `model.not_evaluated`; one chip per
baseboard, one instance per slot. `docs/brief/SOURCES.md`: five figure files, the bench call
needs `actions=0` to give 0.044 percent, the contract tests are named in `tests/test_oasp.py`,
L5 carries no waiting marker.

## 4. The blog, Parts 5, 6 and 7

**Part 7.** The chip batches **provenance records**, not tickets; one P-384 signature per
50 ms window keeps the signing engine under 34 percent busy, and the firmware share under
0.1 percent is a separate number that batching does not produce. On an NFPA 72 supervised
circuit a cut wire is a **trouble** signal, not an alarm; the halt loop goes further than a
fire loop, a cut halts. Loss of current is declared after two missed samples and the halt
output follows within about three sense periods, 311 µs on the digital path (the same
loose phrase was in `02-safety-fabric.md` §1 and is fixed there). The tests run racks of up
to four GPUs; 72 is the ngspice loop. A jumpered governor is caught the moment its own
switch opens, and is invisible and harmless until then (by design, `test_h11`). Rebuilding
rosters during a partition is in the design's partition table, not in a test. Per-port
switch control is a firmware ask (docs/03 §9), so "opens only" became "is designed to open
only" with the ask named. ANSI/ISA-50.00.01 and IEC 60381-1. 100BASE-T1 on the harness.
The rack figure now says it draws 72 governors as nine trays of eight.

**Part 6.** The percolation chart counts copy-to-device **pairs** still connected, not roads;
its axis and callouts changed. "Edge cut" meant a cut at the network's edge, not a graph
theorist's edge cut; reworded everywhere, the country figure included. The deep-network
row (K1a) is thin in the model: 57 of the 60 core nodes sit one hop from some machine, so
the check runs on three nodes; the post, docs/23 and the script's own output now say so,
and a larger core is in the gap list. Claim 2 is **k dots per pair**, not per machine; the
model's 43 dots for 22 machines is under two per machine, and the script asserts only
"at least k and larger than either end". Claim 3 needs the network to carry
min(|S|, |T|) disjoint paths between the two whole sides, which pairwise k-connectivity does
not give (a 2-connected core with a two-node waist is the counterexample); the one code
change of this review adds **K4c** to `proofs/no_global_kill_switch.py`, which lets the cut
fall anywhere except on the bystanders and checks that the smallest separator in the whole
graph is still 11, the device end's count. It holds. The reference-monitor sentence now
claims only what `core_invariants.py` proves: the always-invoked half, on the abstract
machine. The six irreversible devices are the model's labelling (every second one plus the
motor). "Hundreds of thousands" of private machines is now "uncounted".

**Part 5.** 20 of 87 catalogue entries compared and 17 agree (the agent's first write-up said
21 and all agreeing; its second pass corrected it, and the post said so nowhere). The wave's
own report puts the three chip-repository experiments at 69 cents; the fourteen minutes and
the three percent of the subscription window are my reading of the tool's meter and the
post now says that. All four experiments came back "revise". The packet holds the latest
review of each branch, not every review. The reviewer's actual words on the replayer
("re-encodes the guards as copies and does not drive the machine") replace a phrase that
was not in the packet. The uncommitted-work episode belonged to L5's first revision, not to
H1. The first-pass path blocks are in the pull requests' history, not in the packet, and the
post says which pass it describes. The local reader timed out on two of three. The gate
beats OpenShell's half-second timeout by roughly a thousand times in the Python model,
unmeasured on hardware. The watermark numbers now match Part 1 (a half rewrite beats the
watermark four times in five; an unmarked paraphrase every time). Twenty-three experiments,
twenty issues. The five contract tests are among fourteen. The September source for the
alliance's move to the Linux Foundation is cited.

## 5. docs/24 and docs/23

docs/24: the quorum of observers is docs/18 question 2 (and YB-0053, YB-0054), not 12; the
hold and approval tests are `test_h08_override.py` and `test_h04_lane.py`, H18 is the
witnesses; the human lane is docs/04 §4 (the rule's requirement mode) and §3 (the hold and
APPROVE), not §5; of the four ways the framework could be wrong, two have experiments (N2;
YB-0052 to 0054) and two (device-maker coverage, persuasion) are docs/18 questions with no
experiment, which the text now says instead of claiming four; Wallace et al. rank system
over user over model and tool output, the developer tier came later in OpenAI's model spec;
OpenShell 0.1.0 was released on 28 September 2026 and first shown at GTC in March, and
Sentry is a reference system design, not open source and not a product; the Open Secure AI
Alliance has no published charter, the trusted-foundation wording is its description of its
stack; three figures are borrowed from the blog, not two; YB-0052's review found the
baseline overlap, it did not measure correlated failures; docs/23 argues and checks on a
model, it does not prove the Internet; "a billion a day" and "by the thousand" are gone, they
had no source; BlueField-4 is a DPU; Sentry's verdict can also be a rung-2 witness (docs/25
§0.1), so the two documents agree on where it sits.

docs/23: Claim 2 and Claim 3 reworded as above, with K4c in the table; K1a's row carries the
thin-check note; the core is "expander-like" (the script checks simple and connected, not
expansion); docs/19 proves claim L with the reference-monitor argument and the Z3 proofs,
not with cuts, and the header says so; Menger is nearly a century old; the reference-monitor
sentence in §5 claims the always-invoked half only. docs/25's "the kill switch on the path
to the model" is now "the local switch", since docs/23's whole point is that the other kind
does not exist.

## 6. What the readers could not check

- The `safety` repository (YB-0052's set, scorer, baselines and pull request 7) and the
  `Watermark` repository are not on the machine the readers ran on; their numbers are
  inherited from the posts that first stated them.
- GitHub itself (the pull-request comments, NVIDIA/OpenShell at `837fdfd`, the
  supervisor-middleware contract) and a few vendor pages (NIST's copy of the Anderson
  report, the DC-SCM project page, the full text of NVIDIA's in-silicon monitoring post)
  were behind a proxy or a permission nobody was awake to grant. Where a claim rests on one
  of these it is inherited from `hardware-and-silicon/docs/NVIDIA.md` or docs/03, which were
  written with the page open.
- "The weights at rest are ciphertext under the governor's key" and "the GPU runs nothing
  without `BEGIN_MODEL`" are design claims; the model's wrapped key is an HMAC stand-in and
  `GPU.load` takes a digest.

## 7. What the program owes

These are places where a document described the design and the model does something
simpler. Each is a gap to close or a row for the experiment table, not a thing to paper
over again.

| # | Gap | Where it shows | What closes it |
|---|---|---|---|
| G1 | `revocations` is stored and never read: a revoked observer key or chip id is still honoured | `policy.py:85`; docs/25 §2 | A check in `_keys` and `_witnessed`; a test that revokes a key mid-session and expects `gate.witness_revoked` |
| G2 | `CAP_REQUEST` ignores `sandbox`: a sandboxed roster peer can still be granted a flow | `governor.py` `_cmd_cap_request`; docs/25 §2 | The sandbox check in `_cmd_cap_request`; a test beside `test_h17::test_sandbox_organism` |
| G3 | The hazard budget is per governor, so a session spread across two chips gets two budgets | `governor.py` `_release_gate`; docs/25 §0.1 | Either own it over the fabric like the payment budget (H13's `_reserve`) or state per-governor as the design |
| G4 | Tokens are read from the GPU's counter, not from the streams presented for signing | `read_meter`; docs/25 §7.1 | Derive the meter's tokens from `_cmd_sign_output`, or keep the counter and say so in docs/04 |
| G5 | A workload token's fingerprint survives an edition change, so an old token is accepted under the new edition | `governor.py` `_cmd_begin_model`, `_cmd_request`; docs/25 §2.1 | Refresh the fingerprint on commit, or require `BEGIN_MODEL` again; `test_h01::test_fingerprint_names_policy_epoch` extended |
| G6 | The L4 replayer re-encodes the guards and does not drive the Z3 machine; its heartbeat check cannot fail | `audit/wave-1/review/L4`; experiment L4 | The revision L4 is in: install z3 in the agent's environment and drive `core_invariants.py` for real |
| G7 | K1a is near-vacuous on a 60-node core (three deep nodes) | `proofs/no_global_kill_switch.py`; docs/23 §4; Part 6 | Rebuild with a core large enough that "deep" means something (a few hundred nodes), rerun, and restate the numbers everywhere they appear |
| G8 | Claim 3 needs set-to-set connectivity; K4c checks it on the instance, the prose assumption is strengthened | docs/23 §3a; Part 6 | Done in the documents; the stronger assumption belongs in the proof script's docstring too (it is) |
| G9 | The gate's latency inside OpenShell's window is unmeasured | docs/NVIDIA.md; Part 5; deck slide 19 | YB-0056 is that experiment; a timing test in `tests/test_oasp.py` would pin the model's half millisecond |
| G10 | The sky130 prototype at 50 MHz puts a P-384 signature at 34 ms and the batched engine at 68 percent, above the spec's 50 percent bound | docs/04 §9 and §11 | Either a wider batch window at the prototype clock or the product clock stated as the bound's basis |
| G11 | Roster formation during a partition is in the design's table and in no test | docs/02 §3; Part 7 | A case in `test_h14_partition.py` that forms a roster in the surviving half before `heal()` |
| G12 | The wall time and cost of a wave are not in the packet in a form anyone can check (`0 min` per row) | `audit/wave-1/REPORT.md` | `run_wave.sh` records wall time per attempt and the CLI's own cost line into the report |

## 8. How to check this record

```
cd safety-governor
python3 -m pytest -q tests rtl/tests          # 220 tests
make proof                                    # P0 to P9, the commit point, K0 to K5 with K4c
python3 proofs/no_global_kill_switch.py       # the K rows, with the thin-check note on K1a
python3 -m govsim.bench                       # the engine and firmware numbers
make loop                                     # the 39 ngspice runs behind 317 us
python3 docs/tools/build_doc_docx.py docs/25-the-rulebook-and-the-board.md
```

The documents changed by this review: `02`, `04`, `22`, `23`, `24`, `25`, `START-HERE.md`,
`docs/brief/build_deck.js` and `SOURCES.md`, the figures under `docs/figures/`, and in the
sibling repository blog Parts 5, 6 and 7 with their figures. The commits that carry them name
this file.

Yobie Benjamin · yobie AT ieee DOT org · linkedin.com/in/yobie
