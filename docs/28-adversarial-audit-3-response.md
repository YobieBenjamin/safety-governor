# Adversarial function audit 3: the response

A fresh, independent team (team B), knowing nothing of earlier audits or fixes, audited the code after the first round
of fixes (safety-governor b335e06, hardware-and-silicon 0e088dc, Watermark afdbb2c) against GOAL.md and the audit
prompt. Verdict: **DOES NOT HOLD**, 40 rows: 8 catastrophic, 15 serious, 7 moderate, 10 claims. The report and the
catalog are kept unedited in the project (`design/adversarial-function-audit-3-report.md`,
`design/problem-catalog-audit-3.tsv`) and on the drive (`work/audits/adversarial-function/audit-3-team-b/`).

Every row below follows the pipeline in `PROBLEM-TO-SILICON-PIPELINE.md`: the attack became a failing test, then the
code fix, then the full suites. The regression tests are `tests/test_adversarial_audit_3.py` (safety-governor),
`rtl/tests/test_adversarial_audit_3_rtl.py` (the hard core) and `tests/test_adversarial_audit_3.py`
(hardware-and-silicon). Of the auditor's 33 tests, 29 now pass. The four that still fail ask for something no design
should do (act on a HALT nobody sends, keep GPUs running with every heartbeat signer silent, carry state into a brand-new
simulated chip, accept a lower sequence number with no new epoch); the faithful versions pass (rows 6, 9, 16, 28). This response is evidence for people to
check, not a verdict: GOAL.md says no AI is the final judge, and the next step is another fresh audit.

Status words: **fixed** (in code, with a test that failed before and passes now), **fixed in the model, depends on**
(the code enforces it; silicon needs a named party), **open** (not fixed; why and what next).

| # | Severity | Finding (short) | Status | Test | Silicon plan | Depends on |
|---|---|---|---|---|---|---|
| 1 | CATASTROPHIC | Protected site bypassed by an altitude, text or a mapping | fixed: the definitions engine (`govsim/definitions.py`) reduces every target to one canonical place; unreadable targets are refused | `test_a_protected_site_is_refused_however_it_is_written` (9 spellings), `test_a_target_the_definitions_engine_cannot_read_is_refused` | typed field decoder in the gate core and the endpoint comparator (`docs/research/definitions-engine.md`) | endpoint vendors adopt the definitions |
| 2 | CATASTROPHIC | One governance key replaces any signed list | fixed: lists need the list quorum (2 distinct governance signers) | `test_one_governance_key_cannot_replace_a_list`; red team `one governance key rewrites the beneficiary registry` | list verification uses the policy quorum engine | nothing |
| 3 | CATASTROPHIC | Exit register lacks NVLink-C2C, host NICs, BMC NIC | fixed in the model: host-side exits named, metered on one host allowance, sealed output only | `test_the_exit_register_names_the_host_side_exits`, `test_all_host_side_exits_share_one_allowance` | C2C governance point or CC session ending at the egress (`docs/research/host-side-exits.md`) | NVIDIA, OEM |
| 4 | CATASTROPHIC | 10 GiB to the host in one PCIe transfer | fixed: the host 'out' entry admits only presented bytes plus slack, checked per transfer | `test_one_transfer_to_the_host_is_bounded_by_the_output_allowance` (4 exits) | per-direction byte budget in the switch capability table | switch vendor |
| 5 | CATASTROPHIC | The host reprograms the switches in band | fixed in the model: in-band write path modelled; RUN refused and running chips halted unless every switch reports lockdown | `test_a_governor_will_not_run_behind_an_unlocked_switch`, `test_a_switch_unlocked_while_running_stops_the_gpu` | out-of-band-only NVSwitch management, PCIe switch lockdown, switch firmware measured (`docs/research/switch-management-lockdown.md`) | NVIDIA, switch vendor, OEM |
| 6 | CATASTROPHIC | Heartbeat signers are a fleet-wide off switch | fixed: heartbeat signers belong to one data center (`site`); a governor accepts only its own site's heartbeats. The auditor's test delivers no heartbeat to any rack (every authority silent), where stopping everything is the correct fail-closed result; it stays failing as written | `test_one_sites_silent_heartbeat_signers_stop_only_that_site`, `test_a_heartbeat_signed_for_another_site_is_refused` | site id bound into the hard-core heartbeat check (`docs/research/data-center-boundary.md`) | regulator, operator (who holds each site's signers) |
| 7 | CATASTROPHIC | A stolen quorum captures chips permanently | fixed: version step bound (16) and a fused recovery quorum that can always take a chip back | `test_a_version_jump_is_refused`, `test_the_recovery_quorum_takes_back_a_chip_whose_governance_was_stolen`, `test_the_recovery_keys_must_be_the_fused_ones` | recovery key hashes in OTP, step limit in the hard core (`docs/research/capture-defences.md`) | regulator, standards body |
| 8 | CATASTROPHIC | Fleet ledger answers are unauthenticated | fixed: replicas sign receipts over key, amount, reserver and a fresh nonce; every replica must answer at reserve and commit (independent counters), so a lying replica can only refuse | `test_forged_fleet_ledger_answers_are_refused`, `test_one_captured_fleet_ledger_replica_cannot_lift_the_fleet_cap` | replica keys in the edition, verification on the crypto engine (`docs/research/fleet-ledger.md`) | operator |
| 9 | SERIOUS | A targeted HALT depends on the target's host | fixed: any governor relays an authority HALT over the fabric. The auditor's test signs a HALT and never sends it; it stays failing as written | `test_a_halt_the_targets_host_drops_still_reaches_it_over_the_fabric`, `test_a_relayed_halt_must_carry_the_authority_quorum` | fabric HALT decoded in the hard core | nothing |
| 10 | SERIOUS | Stragglers keep minting on old rules | fixed: a quorum heartbeat for an unknown epoch halts the straggler at once; the authority installs the edition on every endpoint directly | `test_a_straggler_on_old_rules_cannot_release_after_the_commit`, `test_a_straggler_halts_at_the_first_heartbeat_of_the_new_epoch` | epoch announcement path to endpoints | endpoint vendors |
| 11 | SERIOUS | One lying budget owner voids the rack cap | fixed: rack budgets are counted by three owners and every one must reserve (a 2-of-3 rule with independent counters would let concurrent requests spend up to 1.5x the cap); a lying owner can only refuse | `test_one_lying_budget_owner_cannot_lift_the_rack_cap` | fabric protocol only | nothing |
| 12 | SERIOUS | An extracted key mints outside the rules | fixed: the governor commits only tickets in its durable minted record | `test_an_extracted_governor_key_cannot_mint_outside_the_rule_engine`; red team `ticket signed with the extracted governor key` | minted-ticket store beside the used-ticket store | nothing |
| 13 | SERIOUS | A bypassed governor attests like a wired one | fixed in the model: lever self-test (brake pulse read back, loopback sense on reset and power) in every quote; RUN needs brake and reset proven | `test_cut_levers_show_in_the_quote_and_stop_minting`, `test_a_governor_with_cut_levers_never_releases_its_gpu` | lever readback inputs (`docs/research/lever-loopback-sense.md`) | NVIDIA (SMBPBI brake status), OEM |
| 14 | SERIOUS | A quorum-signed harmful edition is accepted | fixed: fused rule floor; fused delay before a loosening edition acts (0 in model racks, set in production fuses) | `test_a_quorum_signed_edition_below_the_fused_floor_is_refused`, `test_an_automatic_strike_rule_is_below_the_floor_even_with_the_site_check`, `test_a_loosening_edition_waits_for_its_public_delay` | floor digest in OTP, delay timer; transparency-log inclusion proof is **open** | regulator, standards body |
| 15 | SERIOUS | RTL heartbeat window not clamped | fixed (RTL section below) | `test_adversarial_audit_3_rtl.py` | synthesis-time maximum window | nothing |
| 16 | SERIOUS | RTL forgets a halt across a power cycle | fixed (RTL section below) | `test_adversarial_audit_3_rtl.py` | NVM-backed rung record read at reset | nothing |
| 17 | SERIOUS | RTL CLEAR is a bare strobe | fixed (RTL section below) | `test_adversarial_audit_3_rtl.py` | clear bound to a dispatched, verified CLEAR | nothing |
| 18 | SERIOUS | 256 anti-rollback fuses cannot hold the versions | fixed: NVM monotonic counter plus one fuse bit per 64 versions, step bound 16; an unrecordable version is refused | `test_the_policy_fuses_hold_any_accepted_version` | NVM counter anchored by fuses | nothing |
| 19 | SERIOUS | The roll call needs more than one engine | fixed: roster fabric traffic is MACed with pairwise keys from an attested X25519 exchange (126% to 3% at 72 members) | `test_the_roll_call_at_72_members_fits_with_the_fabric_the_model_uses` | MAC-authenticated fabric (`docs/research/signing-engine-budget.md`) | nothing |
| 20 | SERIOUS | Release tickets overload the engine | fixed: release tickets are MACs for the node's own egress (306% to 34% at 100-token responses) | `test_at_100_tokens_the_full_path_now_fits_and_the_old_design_did_not`, `test_counts_reconcile_on_the_full_path` | HMAC tickets on the hash engine | nothing |
| 21 | SERIOUS | Jurisdictions cannot compose | fixed: fused jurisdiction roots; an action a jurisdiction governs must pass its edition too, strictest requirement wins | `test_a_jurisdiction_restricts_and_cannot_be_loosened_by_another`, `test_a_jurisdiction_edition_needs_its_own_roots_quorum` | several root key-hash sets in OTP (`docs/research/jurisdictions.md`) | regulator, standards body |
| 22 | SERIOUS | Nothing finds servers sold without a governor | **open**: outside the chip; registry and reconciliation protocol written down (`docs/research/ungoverned-servers.md`) | none possible in the model | none | regulator, vendors |
| 23 | SERIOUS | The observer is measured only on reasoning errors | **open**: WAVE-OBSERVER-EVALUATION-SET (harmful-action evaluation set, false-hold rate priced at fleet scale) not yet run | | none | nothing |
| 24 | MODERATE | A braked GPU keeps computing | fixed: a lost heartbeat goes straight to HALT (brake and reset) | `test_a_lost_heartbeat_stops_the_gpu_computing` | the RTL sequencer does the same (RTL section) | nothing |
| 25 | MODERATE | One member freezes the rack with an alarm | fixed: a peer's alarm blocks only when two distinct members report it | `test_one_governor_cannot_freeze_the_rack_with_an_alarm_but_two_can_raise_one` | none | nothing |
| 26 | MODERATE | One key freezes list updates with a huge version | fixed: list quorum and a version step bound | `test_a_list_version_cannot_jump_to_freeze_updates` | none | nothing |
| 27 | MODERATE | Endpoints accept a replayed older epoch | fixed: epoch statements carry the edition version; endpoints never go backwards; egress endpoints hold the edition | `test_an_endpoint_refuses_a_replayed_older_epoch` | version comparator in the endpoint epoch register | endpoint vendors |
| 28 | MODERATE | Mailbox sequence space ends | fixed (RTL section below) | `test_adversarial_audit_3_rtl.py` | wider, epoch-scoped sequence registers | nothing |
| 29 | MODERATE | The used-ticket store fills | fixed: records of expired tickets are pruned; a full store refuses | `test_a_full_used_ticket_store_refuses_and_expired_records_make_room` | sized store, refuse when full | nothing |
| 30 | MODERATE | Reference-stack tickets bind to no endpoint | fixed (hardware-and-silicon): every ticket names the rule's endpoint or the gate's default; an unbound ticket is valid nowhere | hardware-and-silicon `tests/test_adversarial_audit_3.py` | none | nothing |
| 31 | CLAIM | "a proof you cannot break" while attacks succeed | fixed: `govsim/prove.py` reworded (VERDICT 1 covers only checked attacks); audit attacks added to the red team | red team | none | nothing |
| 32 | CLAIM | Overhead hypothesis says pass at 306% | fixed: the hypothesis now checks the full path and the roll call | sweep | none | nothing |
| 33 | CLAIM | Leakage hypothesis says pass with a 10 GiB transfer | fixed by row 4 | sweep | none | nothing |
| 34 | CLAIM | "mints in 20 us, engine under 34%" | fixed in docs/04 section 9; the blog text is left for Yobie | | none | nothing |
| 35 | CLAIM | "no planet-wide switch of any kind" | the code now matches (row 6); the blog text (part 7) is left for Yobie | | none | nothing |
| 36 | CLAIM | "the host cannot stop the governor halting" | fixed in docs/03 (row 9) | | none | nothing |
| 37 | CLAIM | "no governor is left on the old rules" | fixed in docs/02 (row 10) | | none | nothing |
| 38 | CLAIM | "policy loosened by one operator: stopped" | fixed in docs/05 (rows 2, 14) | | none | nothing |
| 39 | CLAIM | "one per GPU" vs eight GPUs per chip in the pricing | fixed in the README; the blog text is left for Yobie | | none | nothing |
| 40 | CLAIM | "the chip can check a target against a list" | the code now matches (row 1); the blog text is left for Yobie | | none | nothing |

## The hard core (rows 15, 16, 17, 28, and row 24 in RTL)

All five changes are in `rtl/governor_rtl/`, with properties in `rtl/formal/`, new mutants that must fail, updated
conformance tests, regenerated Verilog in `rtl/gen/`, and regression tests in `rtl/tests/test_adversarial_audit_3_rtl.py`.

| # | Fix | Proof and test |
|---|---|---|
| 15 | The heartbeat loads min(window, 5000 ms); no signed window, however large, keeps the core alive past the policy expiry | `heartbeat.sv` (RTL-HEARTBEAT-NEVER-OUTLIVES-POLICY, reloads exactly the clamped window); two mutants; the auditor's test passes |
| 16 | A non-volatile rung record (reset-less registers standing for an NVM-backed register written by hardware) is set in HALT or SAFE and cleared only by an authorized clear. After any reset with the record set, the chip never arms: it returns to HALT (SAFE if the record says SAFE) with cause 5, the loop open | `halt_seq_persist.sv`, proven with reset free in every cycle; mutants. The auditor's test builds a brand-new simulator object, which cannot express non-volatile state; the faithful test (a real reset of the same chip) passes |
| 17 | CLEAR is bound in hardware: a clear takes effect only with `clear_authorized`, which the top level drives only when the mailbox dispatches a verified CLEAR command (code 0x10) in that cycle | `halt_seq.sv`, `governor_core.sv`; mutant that ignores the binding; the auditor's test passes |
| 28 | Mailbox sequence registers are 64 bits, and every key slot resets to zero when a quorum commits a new epoch; within an epoch the sequence still only rises | `mailbox.sv`; mutants. The auditor's test asks for a lower sequence number to be accepted with no new epoch, which would be a replay hole; the faithful test (a new epoch restores the slot; without one a lower number is still refused) passes. `MBOX_SEQ_HI` is at CSR 0x10C |
| 24 | A lost heartbeat in RUN or THROTTLE goes to HALT (brake and reset) with the local cause and the loop closed, matching the model | `halt_seq.sv`; conformance |

## Behaviour changes a reader should know about

- A lost heartbeat halts (brake and reset) at once instead of braking for 30 s.
- A straggler halts at the first heartbeat of the new epoch, with cause EPOCH_STRAGGLER.
- A single governor's alarm is a report to its neighbours; two reports raise it there. A chip's own alarm still stops
  its own minting at once, and causes that open the loop still stop the whole domain.
- Clearing every single-use record no longer reopens a ticket (F33's documented open part), because the minted record
  is retired at commit. Code inside the trust root that rewrites all four records is the remaining residual.
- `tests/test_f11_atomic_consume.py` builds its ticket by hand, so it now records it in the minted set as the mint does.

## What a fresh audit should look at next

The new mechanisms are new attack surface: the definitions engine's parsers, the recovery quorum, the loosening
classifier (`policy.loosenings`), jurisdiction composition, the fabric MAC keys, the release-ticket MAC key, the lever
self-test's sense lines, and the site binding.
