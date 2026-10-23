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
> **Backed by:** `govsim/harness.py` (the sweep across tiers), `tests/test_h00_*.py` to
> `test_h16_*.py`, `rtl/tests/test_blocks.py`, `.github/workflows/ci.yml`; the current matrix
> is `results/report.md`.

## 1. Hypotheses and what would knock each one down

| Id | Claim | Falsified if | Level | Test |
|---|---|---|---|---|
| H0 | Within the boundary, no protected operation executes without a fresh authorization bound to that exact operation | Any forged, altered, expired, replayed or unauthorized ticket is accepted by an endpoint | sim, silicon | `tests/test_h00_contract.py` |
| H1 | Attestation binds permissions to firmware, model manifest and policy | A change in any of them leaves the fingerprint or the epoch unchanged, or a permission carries over | sim, silicon | `tests/test_h01_attestation.py` |
| H2 | Every enumerated boundary crossing passes a governed switch | Bytes reach a non-roster peer, or leave while the heartbeat is dead, or a path is found that the enumeration missed; descriptor-level leaks between roster members are the recorded residual | sim (rack tier; residual recorded), silicon | `tests/test_h02_enforcement_points.py` |
| H3 | Policy changes only with a quorum, and never backwards | An image with fewer than k signatures, or an older version, is accepted | sim, rtl (monotonic) | `tests/test_h03_quorum.py` |
| H4 | The broker cannot choose its rule or lane | A requester-supplied label changes a decision | sim | `tests/test_h04_lane.py` |
| H5 | Alarms are monotone | An alarm is cleared without a rule or key | sim, rtl (sticky alarm bits) | `tests/test_h05_alarms.py` |
| H6 | The comparator holds with every layer above it compromised | A release succeeds with host, broker and runtime under red-team control | sim, silicon | `tests/test_h06_comparator.py` |
| H7 | The assumptions register is complete for the deployment | A policy with a rule input that has no register row loads | sim | `tests/test_h07_register.py` |
| H8 | Human override is slow and fully logged | An override below the latency floor, below the quorum, or missing from the log | sim | `tests/test_h08_override.py` |
| H9 | Governor overhead is zero per token, one lookup per transfer, one signature per response | Operation counts grow with tokens, or the modelled cost exceeds one percent for the reference workload | sim (model), silicon (measurement) | `tests/test_h09_overhead.py`, `govsim/bench.py` |
| H10 | Permitted-channel leakage stays within the budget | Extraction through the output channel exceeds the query or byte budget without tripping a limit | sim | `tests/test_h10_leakage.py` |
| H11 | A halt propagates to every GPU in the domain within the bound, fail-safe | Any GPU keeps running after a halt or a loop break; any governor clears alone | sim, rtl (halt_loop), silicon | `tests/test_h11_halt_loop.py` |
| H12 | Only roster members speak on the fabric, and only once per message | A rogue or replayed message is acted on | sim | `tests/test_h12_fabric_auth.py` |
| H13 | Shared budgets cannot be overspent across governors | Concurrent reservations exceed the limit | sim | `tests/test_h13_shared_budget.py` |
| H14 | Partitions and epoch changes end in safe states, never in stale ones | A cut-off segment keeps running; an epoch applies unevenly | sim, rtl (heartbeat) | `tests/test_h14_partition.py` |
| H15 | Production silicon has no debug path | A debug access succeeds in the production lifecycle state | sim, rtl (lifecycle), silicon | `tests/test_h15_tamper.py` |
| H16 | The physical levers work without the GPU's cooperation | A GPU that ignores every software command keeps running after the governor asserts its levers | sim, silicon | `tests/test_h16_levers.py` |
| H17 | No governed action initiates without a ticket, and no governed response leaves the rack without a release ticket | A strike, payment, message or shipment executes with no ticket, or a response reaches the user with no release ticket, or a forged, replayed, wrong-session or wrong-hash ticket is honoured | sim | `tests/test_h17_use_cases.py` |
| H18 | Oversight survives the model: the observer is always invoked and cannot be impersonated, audit sampling is unpredictable, the evaluated model is the deployed model, compute and hazard budgets bind | A release passes with no observer verdict or with a verdict under the host's or the governor's own key; a sampled or hazard-class response leaves before the audit store's receipt; a model digest with no evaluation attestation gets its key; a budget is exceeded without a throttle or a license | sim | `tests/test_h18_oversight.py` |
| H19 | A signature authorizes exactly what was signed, and a policy cannot set its own quorum (added 22 October 2026 after testing found both broken) | An image with a threshold under the fused one, or of zero with no signatures, is staged; any signed frame the system produces (heartbeat, halt, clear, approval, commit, request, output, roster join, alarm clear) is accepted by a command it was not signed for; a HALT or CLEAR for another chip, past its expiry or signed with the heartbeat key is accepted | sim | `tests/test_h19_authorization.py` |
| H20 | The controls the rulebook names are enforced, not just stored (added 22 October 2026) | A revoked observer, approver or GPU still counts; a sandboxed governor grants a peer capability on request; a session spread over two governors gets two hazard budgets, or one whose owner is unreachable releases; a workload token minted under an old edition is accepted | sim | `tests/test_h20_closed_gaps.py` |

## 2. Tiers in the simulation

Every test runs against three configurations of the model:

| Tier | Enforcement points | Levers | Fabric |
|---|---|---|---|
| rack (plan of record) | NVSwitch ports, PCIe switch ports and ACS, DPU flow tables, all roster-bound; unchecked paths bricked | brake, reset, slot power | loop + messages |
| board (fallback) | none (the model records the gap) | brake, reset, slot power | loop + messages |
| integrated (future ask) | the rack tier plus descriptor-level checks at the copy engines and the peer MMU, and an inline output hash | as rack | as rack |

H2 has two parts. Link-level containment (no bytes to a non-roster peer, no bytes when the
heartbeat is dead) must hold at the rack tier. Descriptor-level containment between two
roster members is *expected to fail* at the rack and board tiers and is reported as the
known residual, not a surprise. At the integrated tier the descriptor checker is modelled but a buffer-class policy is not, so H2b is reported as a gap there too rather than as a pass earned by a test that closes the checker by hand. The report in `results/report.md` shows the matrix; it summarizes the sweep's probes, which are lighter than the test files they stand for.

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
| Governor loses power | Loop opens | Immediate | Domain halts; the dead governor's GPU is powered down by the slot's default-safe PWR_EN where the board has per-slot power control, and held in reset otherwise |
| Governor firmware hang | Heartbeat not consumed; no tickets | Watchdog | Watchdog resets the governor into HALTED_INITIAL; loop opens |
| Fuse read failure | Keys cannot derive | Boot | Boot refused; the sequencer never leaves HALTED_INITIAL |
| NVM corruption | Policy or ledger unreadable | Authentication tag | Refuse to RUN; request a fresh policy image; reservations are rebuilt from the roster |
| Loop sense comparator stuck "closed" | A real open is missed at one governor | The loop beacon: a member whose own signed report says its switch is open while the loop carries current is named and the rack halts (`02-safety-fabric.md`) | The other governors' switches still open the loop; the beacon names the odd one out |
| Fabric port failure | Partition | Heartbeat expiry | Safe mode for the cut-off segment |
| Clock glitch | Counter or FSM corruption | Glitch detector | Zeroize, SAFE |

## 6. What the proofs assume

Following seL4's practice, the control firmware's verification will state its assumptions
explicitly: the hardware model (the RTL properties above hold), no DMA into the governor's
SRAM (there is no DMA engine), the crypto engines compute what they claim, the fuse and NVM
macros are correct, and the compiler is trusted or the binary is verified. A verified
controller does not verify the GPU beside it. The claims table in the blog applies in full.
