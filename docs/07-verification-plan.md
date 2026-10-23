# 07 · Verification plan

Three levels, one catalogue. The functional model proves the logic. The RTL simulation and
formal properties prove the hardware blocks keep their invariants. Silicon validation proves
the physical claims. The same hypothesis list runs at every level; a level is finished when
its artefact passes the hypotheses that level can test.

> **In plain words:** every claim is written down together with the observation that would
> prove it wrong, and each one has a test. The model is checked first, then the hardware
> blocks, then the chip itself after it comes back from the fab. The last section says what
> the proofs take on faith.
> **Plain-English version:** `10-plain-english-walkthrough.md` §12.
> **Backed by:** `govsim/harness.py` (the sweep across tiers), the contract test files
> `tests/test_contract_*.py`, `rtl/tests/test_blocks.py`, `.github/workflows/ci.yml`; the current matrix
> is `results/report.md`.

## 1. Hypotheses and what would knock each one down

| Id | Claim | Falsified if | Level | Test |
|---|---|---|---|---|
| CONTRACT-FRESH-AUTHORIZATION-PER-OPERATION | Within the boundary, no protected operation executes without a fresh authorization bound to that exact operation | Any forged, altered, expired, replayed or unauthorized ticket is accepted by an endpoint | sim, silicon | `tests/test_contract_fresh_authorization_per_operation.py` |
| CONTRACT-ATTESTATION-BINDS-PERMISSIONS | Attestation binds permissions to firmware, model manifest and policy | A change in any of them leaves the fingerprint or the epoch unchanged, or a permission carries over | sim, silicon | `tests/test_contract_attestation_binds_permissions.py` |
| CONTRACT-EVERY-CROSSING-GOVERNED | Every enumerated boundary crossing passes a governed switch | Bytes reach a non-roster peer, or leave while the heartbeat is dead, or a path is found that the enumeration missed; descriptor-level leaks between roster members are the recorded residual | sim (rack tier; residual recorded), silicon | `tests/test_contract_every_crossing_governed.py` |
| CONTRACT-POLICY-QUORUM-NO-ROLLBACK | Policy changes only with a quorum, and never backwards | An image with fewer than k signatures, or an older version, is accepted | sim, rtl (monotonic) | `tests/test_contract_policy_quorum_no_rollback.py` |
| CONTRACT-BROKER-CANNOT-PICK-RULE | The broker cannot choose its rule or lane | A requester-supplied label changes a decision | sim | `tests/test_contract_broker_cannot_pick_rule.py` |
| CONTRACT-ALARMS-ARE-MONOTONE | Alarms are monotone | An alarm is cleared without a rule or key | sim, rtl (sticky alarm bits) | `tests/test_contract_alarms_are_monotone.py` |
| CONTRACT-COMPARATOR-SURVIVES-COMPROMISE | The comparator holds with every layer above it compromised | A release succeeds with host, broker and runtime under red-team control | sim, silicon | `tests/test_contract_comparator_survives_compromise.py` |
| CONTRACT-ASSUMPTIONS-REGISTER-COMPLETE | The assumptions register is complete for the deployment | A policy with a rule input that has no register row loads | sim | `tests/test_contract_assumptions_register_complete.py` |
| CONTRACT-OVERRIDE-SLOW-AND-LOGGED | Human override is slow and fully logged | An override below the latency floor, below the quorum, or missing from the log | sim | `tests/test_contract_override_slow_and_logged.py` |
| CONTRACT-GOVERNOR-OVERHEAD-BOUNDED | Governor overhead is zero per token, one lookup per transfer, one signature per response | Operation counts grow with tokens, or the modelled cost exceeds one percent for the reference workload | sim (model), silicon (measurement) | `tests/test_contract_governor_overhead_bounded.py`, `govsim/bench.py` |
| CONTRACT-LEAKAGE-WITHIN-BUDGET | Permitted-channel leakage stays within the budget | Extraction through the output channel exceeds the query or byte budget without tripping a limit | sim | `tests/test_contract_leakage_within_budget.py` |
| CONTRACT-HALT-REACHES-EVERY-GPU | A halt propagates to every GPU in the domain within the bound, fail-safe | Any GPU keeps running after a halt or a loop break; any governor clears alone | sim, rtl (halt_loop), silicon | `tests/test_contract_halt_reaches_every_gpu.py` |
| CONTRACT-ONLY-ROSTER-SPEAKS-ONCE | Only roster members speak on the fabric, and only once per message | A rogue or replayed message is acted on | sim | `tests/test_contract_only_roster_speaks_once.py` |
| CONTRACT-SHARED-BUDGET-NO-OVERSPEND | Shared budgets cannot be overspent across governors | Concurrent reservations exceed the limit | sim | `tests/test_contract_shared_budget_no_overspend.py` |
| CONTRACT-PARTITIONS-END-SAFE | Partitions and epoch changes end in safe states, never in stale ones | A cut-off segment keeps running; an epoch applies unevenly | sim, rtl (heartbeat) | `tests/test_contract_partitions_end_safe.py` |
| CONTRACT-NO-DEBUG-IN-PRODUCTION | Production silicon has no debug path | A debug access succeeds in the production lifecycle state | sim, rtl (lifecycle), silicon | `tests/test_contract_no_debug_in_production.py` |
| CONTRACT-LEVERS-WITHOUT-GPU-COOPERATION | The physical levers work without the GPU's cooperation | A GPU that ignores every software command keeps running after the governor asserts its levers | sim, silicon | `tests/test_contract_levers_without_gpu_cooperation.py` |
| CONTRACT-NO-ACTION-WITHOUT-TICKET | No governed action initiates without a ticket, and no governed response leaves the rack without a release ticket | A strike, payment, message or shipment executes with no ticket, or a response reaches the user with no release ticket, or a forged, replayed, wrong-session or wrong-hash ticket is honoured | sim | `tests/test_contract_no_action_without_ticket.py` |
| CONTRACT-OVERSIGHT-SURVIVES-MODEL | Oversight survives the model: the observer is always invoked and cannot be impersonated, audit sampling is unpredictable, the evaluated model is the deployed model, compute and hazard budgets bind | A release passes with no observer verdict or with a verdict under the host's or the governor's own key; a sampled or hazard-class response leaves before the audit store's receipt; a model digest with no evaluation attestation gets its key; a budget is exceeded without a throttle or a license | sim | `tests/test_contract_oversight_survives_model.py` |
| CONTRACT-SIGNATURE-AUTHORIZES-EXACTLY | A signature authorizes exactly what was signed, and a policy cannot set its own quorum (added 22 October 2026 after testing found both broken) | An image with a threshold under the fused one, or of zero with no signatures, is staged; any signed frame the system produces (heartbeat, halt, clear, approval, commit, request, output, roster join, alarm clear) is accepted by a command it was not signed for; a HALT or CLEAR for another chip, past its expiry or signed with the heartbeat key is accepted | sim | `tests/test_contract_signature_authorizes_exactly.py` |
| CONTRACT-NAMED-CONTROLS-ENFORCED | The controls the rulebook names are enforced, not just stored (added 22 October 2026) | A revoked observer, approver or GPU still counts; a sandboxed governor grants a peer capability on request; a session spread over two governors gets two hazard budgets, or one whose owner is unreachable releases; a workload token minted under an old edition is accepted | sim | `tests/test_contract_named_controls_enforced.py` |

## 2. Tiers in the simulation

Every test runs against three configurations of the model:

| Tier | Enforcement points | Levers | Fabric |
|---|---|---|---|
| rack (plan of record) | NVSwitch ports, PCIe switch ports and ACS, DPU flow tables, all roster-bound; unchecked paths bricked | brake, reset, slot power | loop + messages |
| board (fallback) | none (the model records the gap) | brake, reset, slot power | loop + messages |
| integrated (future ask) | the rack tier plus descriptor-level checks at the copy engines and the peer MMU, and an inline output hash | as rack | as rack |

CONTRACT-EVERY-CROSSING-GOVERNED has two parts. Link-level containment (no bytes to a non-roster peer, no bytes when the
heartbeat is dead) must hold at the rack tier. Descriptor-level containment between two
roster members is *expected to fail* at the rack and board tiers and is reported as the
known residual, not a surprise. At the integrated tier the descriptor checker is modelled but a buffer-class policy is not, so CONTRACT-DESCRIPTOR-LEVEL-ROSTER-GAP is reported as a gap there too rather than as a pass earned by a test that closes the checker by hand. The report in `results/report.md` shows the matrix; it summarizes the sweep's probes, which are lighter than the test files they stand for.

## 3. RTL properties

For each block in `rtl/governor_rtl/`, a simulation test in `rtl/tests/` and, where the
property is small enough, a formal statement for a bounded model checker:

| Block | Invariant |
|---|---|
| `monotonic` | The counter value never decreases; a decrement request is refused |
| `measure_reg` | The register changes only through `extend`; no write path exists |
| `epoch_reg` | The register changes only on `policy_commit` with `quorum_ok`; the host port cannot write it |
| `lifecycle` | The state is monotone; in PRODUCTION, `debug_grant` is never asserted |
| `cap_table` | A lookup allows only an entry with matching key, budget > 0, not expired, matching epoch tag; budget never underflows |
| `ticket_store` | A burned id is never admitted again; `burn` before `admit` ordering |
| `heartbeat` | `expired` asserts within one millisecond tick of expiry; `remaining` reloads only on `hb_valid`, to the window given |
| `halt` | The rung (`state`) climbs on any of `loop_lost`, `hb_expired`, `tamper`, `cmd_halt`, `cmd_throttle`, `local_trip` and on the timers, never descends without `clear`; the levers `pwrbrk`, `perst`, `pwr_en` follow the rung exactly; `switch_open` starts set, clears only when armed (no cause, `hb_ok`), sets on `loop_lost`, `tamper` or `cmd_halt`, and `clear` does not reset it; `cause` bits 2:0 name the summary. Decided by Yobie, 23 October 2026: `cmd_halt` in any state ends with the loop switch open unless an authorized `clear` wins that cycle, and in SAFE the rung stays SAFE; `cmd_exclude` acts only in HALTED_INITIAL with no cause and no live heartbeat, closing the switch while every lever stays asserted, and an excluded chip never reaches RUN until a valid heartbeat arms it; `no_first_hb` is set when the boot window passes without a heartbeat and is never set once armed |
| `halt_loop` | `loop_out_open` follows `switch_open`; `loop_sense` low for two samples drives `loop_lost` (debounce) |
| `meter` | Counters are read-only from the host port (`host_wr` is refused and flagged) and only increment |
| `mailbox` | No command is dispatched unless `frame_seq` is above the key slot's last accepted sequence, then (`epoch_match` or `epoch_exempt`), then `sig_ok`, checked in that order with the first failure reported in `status` |
| `alarms` | Bits set by any source through `set_mask`; cleared only through `clear_mask` gated by `clear_authorized` |
| `top` (`GovernorCore`) | No CSR write port but the doorbell; the millisecond tick for the timers derives from the microsecond counter; the core boots on the HALTED_INITIAL rung with all three levers in the safe state and the loop switch open |

## 4. Silicon validation (after tape-out)

| Claim | Test |
|---|---|
| Halt bound 1 ms on a 72-governor loop | Oscilloscope on PWRBRK# across the domain; worst case over temperature and loop length |
| Levers stop a real GPU | A GPU running a benchmark ignores software; PWRBRK# throttles, PERST# resets, PWR_EN cuts; every governed switch port around it closes |
| Fuse lifecycle | JTAG refused in PRODUCTION; attempt logged |
| Tamper | Mesh cut, glitch injection, temperature excursion: keys zeroized, state SAFE |
| Overhead under one percent | Phase 2 measurement on a real node: tokens per second and action latency with the governor off, on, and on with full logging and revocation |
| Fabric under partition | Pull cables; verify the table in `02-safety-fabric.md` §3 row by row |

## 5. Failure modes and effects (FMEA, abbreviated)

| Failure | Effect | Detection | Mitigation |
|---|---|---|---|
| Governor loses power | Loop opens | Immediate | Domain halts. The dead governor's own GPU stops only on a board with the fail-safe interlock: a watchdog that drops the slot's PWR_EN when the governor's keep-alive stops, which LTPI cannot override (docs/research/fail-safe-board-interlock.md; an OEM requirement, open). Without it, LTPI holds a dead governor's levers released and its GPU keeps running (docs/interfaces/01-dcscm-dcsci-ltpi.md) |
| Governor firmware hang | Heartbeat not consumed; no tickets | Watchdog | Watchdog resets the governor into HALTED_INITIAL; loop opens |
| Fuse read failure | Keys cannot derive | Boot | Boot refused; the sequencer never leaves HALTED_INITIAL |
| NVM corruption | Policy or ledger unreadable | Authentication tag | Refuse to RUN; request a fresh policy image; reservations are rebuilt from the roster |
| Loop sense comparator stuck "closed" | A real open is missed at one governor | The loop beacon: a member whose own signed report says its switch is open while the loop carries current is named and the rack halts (`02-safety-fabric.md`) | The other governors' switches still open the loop; the beacon names the odd one out |
| Fabric port failure | Partition | Heartbeat expiry | Safe mode for the cut-off segment |
| Clock glitch | Counter or FSM corruption | Glitch detector | Zeroize, SAFE |

### 5.1 Expected false halts per rack-year (N2)

A false halt is a halt with no hazard behind it. The model is `govsim/false_halt.py`; `tests/test_false_halt_model.py` reproduces the arithmetic by hand and injects each mode into `govsim` to confirm the effect. A rack is 72 governors on one loop. Rates are in FIT (failures per 10^9 device-hours).

**Sources, stated plainly.** The rates are planning values chosen to the order of magnitude of the IEC 61508-6 data annex, IEC 62380, SN 29500 and MIL-HDBK-217F (connector class), and of public datasheet classes for regulators, comparators and PHYs. They were not read out of those tables in this run, and none is a measurement of this design. Rows marked "assumed" have no public rate at all. Check each against the cited table before the number is relied on; N3 (FPGA beside a real GPU) measures the transient rows.

| Mode (FMEA row) | Rate per governor | Scope | Debounce or window | Per rack-year |
|---|---|---|---|---|
| Governor loses power | 200 FIT | rack (loop opens) | none | 0.126 |
| Firmware hang, watchdog reset | 500 FIT (assumed) | rack | none | 0.316 |
| Loop wire or connector opens | 40 FIT | rack | none | 0.025 |
| Sense comparator stuck open | 50 FIT (assumed) | rack | none | 0.032 |
| Glitch detector false trip | 100 FIT (assumed) | rack | none | 0.063 |
| Switch readback stuck open, named by the beacon | 50 FIT (assumed) | rack | judged when the next heartbeat closes the window | 0.032 |
| Sense transient, 1e-4 per hour, mean 20 us | not a hard fault | rack | two samples at 100 us: 0.00134 survive | 0.084 |
| Beacon readback transient | same process | rack | live at the report instant: 5.6e-13 per window | 0.001 |
| Fabric port failure | 100 FIT | one slot | heartbeat expiry | 0.063 |
| Authority outage longer than the expiry, 1e-5 per hour | not per governor | every slot, loop closed | 5 s expiry | 0.088 |
| Heartbeat loss, 1e-3 per frame, dual ring | not a hard fault | one slot | 5 beats lost on both paths | 2e-21 |
| Fuse read failure, NVM corruption | 20, 100 FIT | none at runtime | boot refused | 0 |

**Result.** Rack-wide false halts 0.679, single-slot false halts 0.151, together **0.830 per rack-year**. The two-sample debounce is what holds the sense transients to 0.084: with a single sample the same glitches would give 12.5 rack halts per rack-year, more than the whole baseline of GPU interruptions. The transient inputs (rate and mean duration) are the least known numbers in the table. Firmware hang is the largest hard-fault row at 0.316; halving it matters more than any hardware row.

**Disproof threshold.** Operators would switch the governor off if it adds visibly to lost work. The reference is the interruption rate of a large training cluster: Meta's Llama 3 report counts 419 unexpected interruptions in 54 days on 16384 GPUs, which scales to 12.4 per 72-GPU rack-year (quoted from memory; confirm against the paper). The threshold here is one tenth of that, **1.24 false halts per rack-year**. The tenth is a judgement, not a measurement from any operator. The model's 0.830 is 67 percent of it, so the margin is real but not large, and the claim fails if N3 measures sense transients above about 6e-4 per hour at 20 us mean duration (six times the assumed rate) or firmware watchdog trips above about 1100 FIT.

**Beacon window.** As built the odd report must appear in one beacon's reports and is judged when the next heartbeat closes the window (two heartbeats of latency, `test_jumpered_governor_is_caught_by_the_beacon_within_two_heartbeats`). Requiring it in two consecutive beacons would remove the transient row (0.001) but not the stuck row, and would cost another heartbeat of latency; the model supports it (`confirm=2`).

**Not modelled.** `govsim` senses the loop with one sample; the two-sample debounce exists in the doc and in this model, not yet in the simulator or the RTL claim. Hazard-driven halts, operator halts and planned maintenance are not false halts and are excluded.

## 6. What the proofs assume

Following seL4's practice, the control firmware's verification will state its assumptions
explicitly: the hardware model (the RTL properties above hold), no DMA into the governor's
SRAM (there is no DMA engine), the crypto engines compute what they claim, the fuse and NVM
macros are correct, and the compiler is trusted or the binary is verified. A verified
controller does not verify the GPU beside it. The claims table in the blog applies in full.
