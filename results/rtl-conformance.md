# RTL spec conformance

`python -m rtl.conformance` on Python 3.12.15. **Result: PASS** (PASS means the suite does what it says: every conforming test passes, every recorded disagreement reproduces by assertion, every mutant is caught). Disagreements with the spec are findings, listed below; they do not fail the run.

- Requirements: 134 (from docs/04 and docs/07, quotes checked verbatim)
- Conformance tests: 173; 159 conform, 14 reproduce a disagreement
- Catalogue: 87 rows mapped; hardware-and-silicon clone not found (set HARDWARE_AND_SILICON); name cross-check skipped
- Catalogue rows + conformance tests: 260 (target 150)
- Mutation sample: 30/30 one-line mutants caught by assertion, over 30 requirements
- Mailbox differential: 4000 random frames, classes {'agree': 3690, 'CONFORMANCE-FIRST-SEQUENCE-NUMBER-ZERO': 3, 'CONFORMANCE-RUN-STATE-CHECK-ORDER': 253, 'CONFORMANCE-HEARTBEAT-SIGNATURE-CHECKED-FIRST': 54}
- Capability table differential: {'lookups': 1280, 'allowed': 269, 'inserts': 99}

## Disagreements (findings)

| Finding | Reproducer | What the RTL or model did |
|---|---|---|
| CONFORMANCE-RUN-STATE-CHECK-ORDER | `test_diff_finding_replayed_request_while_not_running` | assert: REQUEST seq=2 (last 2) [replayed/low seq, not running]: RTL status 4 (bad sequence), model mailbox.governor_not_running (tests_differential.py:277) |
| CONFORMANCE-RUN-STATE-CHECK-ORDER | `test_diff_finding_stale_request_while_not_running` | assert: REQUEST seq=1 (last 0) [stale epoch, not running]: RTL status 5 (bad epoch), model mailbox.governor_not_running (tests_differential.py:277) |
| CONFORMANCE-FIRST-SEQUENCE-NUMBER-ZERO | `test_diff_finding_first_sequence_number_zero` | assert: HALT seq=0 (last 0) [replayed/low seq]: RTL status 4 (bad sequence), model ok (tests_differential.py:277) |
| CONFORMANCE-HEARTBEAT-SIGNATURE-CHECKED-FIRST | `test_diff_finding_replayed_forged_heartbeat` | assert: HEARTBEAT seq=4 (last 4) [replayed/low seq, bad signature]: RTL status 4 (bad sequence), model heartbeat.bad_signature (tests_differential.py:277) |
| CONFORMANCE-HEARTBEAT-SIGNATURE-CHECKED-FIRST | `test_diff_finding_heartbeat_signed_as_something_else` | assert: HEARTBEAT seq=1 (last 0) [signed for another command]: RTL status 7 (wrong command), model heartbeat.bad_signature (tests_differential.py:277) |
| CONFORMANCE-CLEAR-REPORTS-ONE-REASON | `test_model_finding_clear_collapses_reasons` | assert: clear.unauthorized (tests_differential.py:451) |
| CONFORMANCE-DEBUG-BEFORE-FUSE-LOAD | `test_finding_core_reports_test_lifecycle_before_fuse_load` | assert: LIFECYCLE reads 0 and debug_grant is 0 (tests_findings.py:143) |
| CONFORMANCE-MILLISECOND-TICK-TOO-LONG | `test_finding_heartbeat_expires_on_time` | assert: heartbeat still live after 2,001 us; HB_REMAIN = 1 (tests_findings.py:279) |
| CONFORMANCE-ZERO-BYTE-LOOKUP-PASSES | `test_finding_cap_refuses_at_zero_budget` | assert: zero budget, zero-byte lookup allowed (reason 0) (tests_findings.py:319) |
| CONFORMANCE-DUPLICATE-CAPABILITY-ENTRIES | `test_finding_cap_reprogramming_a_key_replaces_it` | assert: a 500-byte lookup passed after the capability was reprogrammed to 10 bytes (tests_findings.py:342) |
| CONFORMANCE-DUPLICATE-CAPABILITY-ENTRIES | `test_finding_cap_rederived_after_epoch_switch_is_usable` | assert: re-derived capability refused (reason 3): the stale entry shadows it (tests_findings.py:587) |
| CONFORMANCE-FRAME-NOT-LATCHED | `test_finding_mailbox_sequence_never_moves_backwards` | assert: last accepted sequence moved back to 3 (tests_findings.py:483) |
| CONFORMANCE-STATUS-TABLE-MISSING-ROW | `test_finding_spec_status_table_lists_status_7` | assert: register map row: / 0x104 / `MBOX_STATUS` / RO / 8 / 0 idle, 1 busy, 2 ok, 3 bad signature, 4 bad sequence, 5 bad epoch, 6 refused / (tests_findings.py:496) |
| CONFORMANCE-SWITCH-OPEN-RUN-ONLY | `test_finding_loop_lost_in_halt_sets_switch_open` | assert: loop_lost in HALT did not set switch_open (tests_findings.py:255) |

First example of each mailbox disagreement class in the random run:

- CONFORMANCE-RUN-STATE-CHECK-ORDER: CAP_REQUEST seq=0 (last 1) [replayed/low seq, not running]: RTL status 4 (bad sequence), model mailbox.governor_not_running
- CONFORMANCE-FIRST-SEQUENCE-NUMBER-ZERO: HALT seq=0 (last 0) [replayed/low seq, signed for another command, not running]: RTL status 4 (bad sequence), model mailbox.wrong_command
- CONFORMANCE-HEARTBEAT-SIGNATURE-CHECKED-FIRST: HEARTBEAT seq=1 (last 1) [replayed/low seq, stale epoch, signed for another command, not running]: RTL status 4 (bad sequence), model heartbeat.bad_signature

## Coverage by requirement

| Id | Owner | Block | Conforming tests | Catalogue rows | Verdict |
|---|---|---|---|---|---|
| REQUIREMENT-MONOTONIC-MICROSECOND-COUNTER | RTL | monotonic, top | 3 | 0 | conforms |
| REQUIREMENT-COUNTER-REFUSES-DECREMENT | RTL | monotonic | 3 | 0 | conforms |
| REQUIREMENT-COUNTER-FUSE-HIGH-WATER-MARK | RTL | monotonic | 3 | 0 | conforms |
| REQUIREMENT-MEASUREMENT-EXTEND-ONLY | RTL | measure_reg | 3 | 0 | conforms |
| REQUIREMENT-LOADER-MEASUREMENT-REGISTER | RTL | top (MEAS0) | 1 | 0 | conforms |
| REQUIREMENT-FIRMWARE-MEASUREMENT-REGISTER | RTL | top (MEAS1) | 1 | 0 | conforms |
| REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM | RTL | epoch_reg | 4 | 2 | conforms |
| REQUIREMENT-EPOCH-IS-POLICY-DIGEST | RTL | top (EPOCH) | 1 | 0 | conforms |
| REQUIREMENT-EPOCH-TAG-LOW-BITS | RTL | epoch_reg, cap_table | 2 | 0 | conforms |
| REQUIREMENT-LIFECYCLE-MONOTONE-NO-DEBUG | RTL | lifecycle | 4 | 0 | conforms |
| REQUIREMENT-PRODUCTION-HAS-NO-DEBUG | RTL | lifecycle | 4 | 0 | DISAGREES CONFORMANCE-DEBUG-BEFORE-FUSE-LOAD |
| REQUIREMENT-LIFECYCLE-REGISTER-ENCODING | RTL | top (LIFECYCLE) | 1 | 0 | DISAGREES CONFORMANCE-DEBUG-BEFORE-FUSE-LOAD |
| REQUIREMENT-JTAG-REFUSED-AND-LOGGED | RTL | lifecycle (flag); firmware (log) | 1 | 0 | conforms |
| REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH | RTL | cap_table | 6 | 0 | DISAGREES CONFORMANCE-DUPLICATE-CAPABILITY-ENTRIES |
| REQUIREMENT-LOOKUP-DECREMENTS-BUDGET | RTL | cap_table | 3 | 0 | DISAGREES CONFORMANCE-DUPLICATE-CAPABILITY-ENTRIES |
| REQUIREMENT-CAPABILITY-REFUSES-AT-ZERO | RTL | cap_table (zero) | 2 | 0 | DISAGREES CONFORMANCE-ZERO-BYTE-LOOKUP-PASSES |
| REQUIREMENT-CAPABILITY-REFUSES-ON-EXPIRY | RTL | cap_table (expiry) | 2 | 0 | conforms |
| REQUIREMENT-CAPABILITY-REFUSES-STALE-TAG | RTL | cap_table (epoch tag) | 2 | 0 | conforms |
| REQUIREMENT-MAC-CHECKED-AT-INSERTION | RTL | cap_table | 2 | 0 | conforms |
| REQUIREMENT-BUDGET-NEVER-UNDERFLOWS | RTL | cap_table | 3 | 0 | conforms |
| REQUIREMENT-CAPABILITY-DIRECTION-FIELD | RTL | cap_table | 3 | 0 | conforms |
| REQUIREMENT-TABLE-SIZES-ARE-PARAMETERS | RTL | top | 1 | 0 | conforms |
| REQUIREMENT-PROTOTYPE-DEFAULT-SIZES | RTL | top | 1 | 0 | conforms |
| REQUIREMENT-PORT-OPEN-ONLY-WITH-ENTRY | RTL | top, cap_table | 2 | 0 | conforms |
| REQUIREMENT-LOOKUP-IN-ONE-CYCLE | RTL | cap_table | 1 | 0 | conforms |
| REQUIREMENT-ENFORCEMENT-POINT-NUMBERING | RTL | top | 1 | 0 | conforms |
| REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED | RTL | ticket_store | 4 | 3 | conforms |
| REQUIREMENT-BURN-BEFORE-ADMIT | RTL | ticket_store | 1 | 1 | conforms |
| REQUIREMENT-HEARTBEAT-EXPIRES-ON-TIME | RTL | heartbeat | 2 | 0 | DISAGREES CONFORMANCE-MILLISECOND-TICK-TOO-LONG |
| REQUIREMENT-HEARTBEAT-RELOADS-ONLY-ON-VALID | RTL | heartbeat | 2 | 0 | conforms |
| REQUIREMENT-HEARTBEAT-REMAINING-REGISTER | RTL | top (HB_REMAIN) | 1 | 0 | DISAGREES CONFORMANCE-MILLISECOND-TICK-TOO-LONG |
| REQUIREMENT-MILLISECOND-TICK-FROM-COUNTER | RTL | top | 2 | 0 | DISAGREES CONFORMANCE-MILLISECOND-TICK-TOO-LONG |
| REQUIREMENT-HEARTBEAT-WINDOW-CLAMPED | FW | heartbeat (window input) | 1 | 0 | conforms |
| REQUIREMENT-RUNG-CLIMBS-ON-CAUSES | RTL | halt | 11 | 0 | conforms |
| REQUIREMENT-RUNG-NEVER-DESCENDS-UNCLEARED | RTL | halt | 6 | 0 | conforms |
| REQUIREMENT-LEVERS-FOLLOW-RUNG | RTL | halt | 4 | 0 | conforms |
| REQUIREMENT-SWITCH-CLOSES-ONLY-WHEN-ARMED | RTL | halt | 5 | 0 | conforms |
| REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE | RTL | halt | 8 | 0 | DISAGREES CONFORMANCE-SWITCH-OPEN-RUN-ONLY |
| REQUIREMENT-CLEAR-KEEPS-SWITCH-OPEN | RTL | halt | 2 | 0 | conforms |
| REQUIREMENT-CAUSE-BITS-NAME-SUMMARY | RTL | halt | 2 | 0 | conforms |
| REQUIREMENT-THROTTLE-AND-HALT-TIMERS | RTL | halt, top | 3 | 0 | conforms |
| REQUIREMENT-TAMPER-ZEROIZES-TO-SAFE | RTL | halt (tamper) | 6 | 0 | conforms |
| REQUIREMENT-STATE-REGISTER-CODES | RTL | top (STATE) | 2 | 0 | conforms |
| REQUIREMENT-LEVERS-REGISTER-BITS | RTL | top (LEVERS) | 1 | 0 | conforms |
| REQUIREMENT-CORE-BOOTS-HALTED-SAFE | RTL | top | 1 | 0 | conforms |
| REQUIREMENT-WATCHDOG-RESETS-TO-HALTED | RTL | top (reset) | 1 | 0 | conforms |
| REQUIREMENT-CLEAR-CLOSES-IF-NO-CAUSE | RTL | halt (clear strobe) | 2 | 0 | conforms |
| REQUIREMENT-HALT-OPENS-LOOP-EVERY-RUNG | RTL | halt | 3 | 0 | conforms |
| REQUIREMENT-HALT-IN-SAFE-STAYS-SAFE | RTL | halt; model enter_safe_mode | 3 | 0 | conforms |
| REQUIREMENT-NO-FIRST-HEARTBEAT-ALARM | RTL | halt, top (ALARMS, CAUSE, BOOT_WAIT) | 1 | 0 | conforms |
| REQUIREMENT-ARMED-CHIP-NEVER-WAITING | RTL | halt, top | 1 | 0 | conforms |
| REQUIREMENT-HARDWARE-ALARMS-SEQUENCER-ONLY | RTL | top, alarms (hw_mask) | 1 | 0 | conforms |
| REQUIREMENT-EXCLUDE-ONLY-WHILE-WAITING | RTL | halt | 1 | 0 | conforms |
| REQUIREMENT-EXCLUDED-CHIP-CLOSES-LOOP | RTL | halt, top | 1 | 0 | conforms |
| REQUIREMENT-EXCLUSION-ENDS-ON-EVENTS | RTL | halt | 1 | 0 | conforms |
| REQUIREMENT-EXCLUDE-LOGGED-WITH-SIGNER | FW | model (_cmd_exclude); firmware | 1 | 0 | conforms |
| REQUIREMENT-LOOP-PAD-FOLLOWS-SWITCH | RTL | halt_loop | 1 | 0 | conforms |
| REQUIREMENT-LOOP-LOSS-DEBOUNCE | RTL | halt_loop | 3 | 0 | conforms |
| REQUIREMENT-LOOP-REGISTER-BITS | RTL | top (LOOP) | 1 | 0 | conforms |
| REQUIREMENT-METER-HOST-WRITE-REFUSED | RTL | meter | 1 | 0 | conforms |
| REQUIREMENT-METER-ONLY-INCREMENTS | RTL | meter | 4 | 0 | conforms |
| REQUIREMENT-METER-SLOT-LAYOUT | RTL | top (METER_SLOT) | 1 | 0 | conforms |
| REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED | RTL | mailbox | 7 | 0 | DISAGREES CONFORMANCE-FIRST-SEQUENCE-NUMBER-ZERO, CONFORMANCE-FRAME-NOT-LATCHED |
| REQUIREMENT-FRAME-EPOCH-MUST-MATCH | RTL | mailbox | 5 | 0 | conforms |
| REQUIREMENT-FRAME-SIGNATURE-CHECKED | RTL | mailbox | 5 | 0 | conforms |
| REQUIREMENT-SIGNED-PAYLOAD-NAMES-COMMAND | RTL | mailbox | 3 | 0 | DISAGREES CONFORMANCE-HEARTBEAT-SIGNATURE-CHECKED-FIRST |
| REQUIREMENT-FIRST-FAILURE-IS-REASON | RTL | mailbox vs govsim | 16 | 0 | DISAGREES CONFORMANCE-RUN-STATE-CHECK-ORDER, CONFORMANCE-FIRST-SEQUENCE-NUMBER-ZERO, CONFORMANCE-HEARTBEAT-SIGNATURE-CHECKED-FIRST, CONFORMANCE-CLEAR-REPORTS-ONE-REASON |
| REQUIREMENT-DISPATCH-AFTER-ALL-CHECKS | RTL | mailbox | 3 | 0 | conforms |
| REQUIREMENT-SEQUENCE-REGISTER-PER-KEY | RTL | top (MBOX_SEQ), mailbox | 2 | 0 | conforms |
| REQUIREMENT-MAILBOX-STATUS-CODES | RTL | mailbox, top (MBOX_STATUS) | 6 | 0 | DISAGREES CONFORMANCE-RUN-STATE-CHECK-ORDER, CONFORMANCE-STATUS-TABLE-MISSING-ROW |
| REQUIREMENT-NO-DISPATCH-WITHOUT-FRESH-SEQUENCE | RTL | mailbox | 2 | 0 | DISAGREES CONFORMANCE-FRAME-NOT-LATCHED |
| REQUIREMENT-WRONG-COMMAND-STATUS | RTL | mailbox | 5 | 0 | DISAGREES CONFORMANCE-STATUS-TABLE-MISSING-ROW |
| REQUIREMENT-ONLY-DOORBELL-WRITABLE | RTL | top | 2 | 0 | conforms |
| REQUIREMENT-NO-CSR-WRITE-PORT | RTL | top | 2 | 0 | conforms |
| REQUIREMENT-SILICON-ID-REGISTER | RTL | top (ID) | 1 | 0 | conforms |
| REQUIREMENT-CAUSE-REGISTER-LAYOUT | RTL | top (CAUSE) | 1 | 0 | conforms |
| REQUIREMENT-LOG-WINDOW-FIRMWARE-MAPPED | FW-ONLY | top (LOG_HEAD) | 1 | 0 | conforms |
| REQUIREMENT-ALARM-SET-BY-ANY-SOURCE | RTL | alarms | 1 | 0 | conforms |
| REQUIREMENT-ALARM-CLEAR-NEEDS-AUTHORIZATION | RTL | alarms | 2 | 0 | conforms |
| REQUIREMENT-STICKY-ALARM-REGISTER | RTL | top (ALARMS) | 1 | 0 | conforms |
| REQUIREMENT-ALARMS-MONOTONE | RTL | alarms | 3 | 0 | conforms |
| REQUIREMENT-BOOT-REFUSED-STAYS-HALTED | RTL | halt (hb_ok gate); firmware (boot) | 2 | 0 | conforms |
| REQUIREMENT-FIRMWARE-TAMPER-ZEROIZE | FW | halt (tamper strobe); key manager (zeroize) | 1 | 0 | conforms |
| REQUIREMENT-EPOCH-EXEMPT-COMMANDS | FW | mailbox (epoch_exempt input) | 2 | 0 | conforms |
| REQUIREMENT-HALT-CLEAR-NAME-CHIP-EXPIRY | FW | mailbox (signed_cmd input) | 3 | 0 | conforms |
| REQUIREMENT-SELF-AUTHENTICATING-COMMANDS | FW | mailbox (sig_ok input) | 1 | 0 | conforms |
| REQUIREMENT-HEARTBEAT-RELOADS-TIMER | FW | heartbeat (hb_valid strobe) | 2 | 0 | conforms |
| REQUIREMENT-HEARTBEAT-KEY-SIGNS-ONLY-HEARTBEATS | FW | heartbeat (hb_valid strobe) | 1 | 0 | conforms |
| REQUIREMENT-AUTHORITY-KEY-SIGNS-HALT | FW | halt (cmd_halt, cmd_throttle strobes) | 1 | 0 | conforms |
| REQUIREMENT-CLEAR-NEEDS-LOGGED-CHECKPOINT | FW | halt (clear strobe) | 1 | 0 | DISAGREES CONFORMANCE-CLEAR-REPORTS-ONE-REASON |
| REQUIREMENT-RACK-WIDE-EPOCH-SWITCH | FW | epoch_reg (commit, quorum_ok) | 1 | 3 | conforms |
| REQUIREMENT-ANY-PARTY-RAISES-ALARM | FW | alarms (set_mask) | 1 | 0 | conforms |
| REQUIREMENT-ALARM-APPROVER-KEY-CLEARS | FW | alarms (clear_authorized) | 1 | 0 | conforms |
| REQUIREMENT-HOST-PEER-ONLY-ON-PCIE | FW | cap_table (ins, mac_ok) | 1 | 0 | conforms |
| REQUIREMENT-METER-SLOT-FREEZE | FW | meter (strobe) | 1 | 0 | conforms |
| REQUIREMENT-TICKET-REFUSED-STALE-OR-STOPPED | FW | mailbox (needs_run); firmware (ticket) | 1 | 2 | conforms |
| REQUIREMENT-SWITCH-RECONFIGURED-AFTER-EVENTS | FW | cap_table (clear_all, ins) | 2 | 0 | DISAGREES CONFORMANCE-DUPLICATE-CAPABILITY-ENTRIES |
| REQUIREMENT-FINGERPRINT-EXTENDED-BY-MANIFEST | FW-ONLY | firmware (the fingerprint has no RTL register) | 0 | 0 | not covered |
| REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD | FW-ONLY | gate (firmware) | 0 | 12 | catalogue only |
| REQUIREMENT-HOLD-RELEASED-BY-QUORUM | FW-ONLY | gate (firmware) | 0 | 8 | catalogue only |
| REQUIREMENT-POLICY-VERSION-INCREASING | FW-ONLY | policy loader, fuses | 0 | 0 | not covered |
| REQUIREMENT-THRESHOLD-NOT-BELOW-FUSE | FW-ONLY | policy loader, fuses | 0 | 0 | not covered |
| REQUIREMENT-IMAGE-NEEDS-ASSUMPTION-ROWS | FW-ONLY | policy loader | 0 | 0 | not covered |
| REQUIREMENT-REQUEST-HASH-DEFINITION | FW-ONLY | gate, endpoint | 0 | 5 | catalogue only |
| REQUIREMENT-FIRMWARE-CHANGE-ROTATES-KEYS | FW-ONLY | key manager (IP) | 0 | 2 | catalogue only |
| REQUIREMENT-APPROVAL-WINDOW-FLOOR | FW-ONLY | approvals (firmware) | 0 | 0 | not covered |
| REQUIREMENT-STRAGGLER-HALTS-WITHOUT-COMMIT | FW-ONLY | policy, heartbeat (firmware) | 0 | 0 | not covered |
| REQUIREMENT-PROMPT-HASH-UNVERIFIED-FLAG | FW-ONLY | provenance record (firmware) | 0 | 0 | not covered |
| REQUIREMENT-DEVICE-PROVENANCE-SIGNATURE | FW-ONLY | crypto engine, firmware batching | 0 | 0 | not covered |
| REQUIREMENT-FIRMWARE-UPDATE-GATED | FW-ONLY | boot ROM, fuses | 0 | 2 | catalogue only |
| REQUIREMENT-ATTESTATION-QUOTE-CONTENTS | FW-ONLY | attestation (firmware) | 0 | 4 | catalogue only |
| REQUIREMENT-SIGNED-LOG-CHECKPOINT | FW-ONLY | log engine (firmware) | 0 | 8 | catalogue only |
| REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION | FW-ONLY | system (CONTRACT-FRESH-AUTHORIZATION-PER-OPERATION) | 0 | 16 | catalogue only |
| REQUIREMENT-SYSTEM-ATTESTATION-BINDING | FW-ONLY | system (CONTRACT-ATTESTATION-BINDS-PERMISSIONS) | 0 | 14 | catalogue only |
| REQUIREMENT-SYSTEM-CROSSINGS-GOVERNED | FW-ONLY | system (CONTRACT-EVERY-CROSSING-GOVERNED) | 0 | 4 | catalogue only |
| REQUIREMENT-SYSTEM-POLICY-QUORUM | FW-ONLY | system (CONTRACT-POLICY-QUORUM-NO-ROLLBACK); RTL monotonic | 0 | 4 | catalogue only |
| REQUIREMENT-SYSTEM-BROKER-NO-CHOICE | FW-ONLY | system (CONTRACT-BROKER-CANNOT-PICK-RULE) | 0 | 2 | catalogue only |
| REQUIREMENT-SYSTEM-COMPARATOR-HOLDS | FW-ONLY | system (CONTRACT-COMPARATOR-SURVIVES-COMPROMISE) | 0 | 4 | catalogue only |
| REQUIREMENT-SYSTEM-ASSUMPTIONS-COMPLETE | FW-ONLY | system (CONTRACT-ASSUMPTIONS-REGISTER-COMPLETE) | 0 | 0 | not covered |
| REQUIREMENT-SYSTEM-OVERRIDE-SLOW-LOGGED | FW-ONLY | system (CONTRACT-OVERRIDE-SLOW-AND-LOGGED) | 0 | 1 | catalogue only |
| REQUIREMENT-SYSTEM-LEAKAGE-BUDGET | FW-ONLY | system (CONTRACT-LEAKAGE-WITHIN-BUDGET) | 0 | 0 | not covered |
| REQUIREMENT-SYSTEM-HALT-PROPAGATES | FW-ONLY | system (CONTRACT-HALT-REACHES-EVERY-GPU); RTL halt_loop | 0 | 0 | not covered |
| REQUIREMENT-SYSTEM-ROSTER-SPEAKS-ONCE | FW-ONLY | system (CONTRACT-ONLY-ROSTER-SPEAKS-ONCE) | 0 | 0 | not covered |
| REQUIREMENT-SYSTEM-SHARED-BUDGETS | FW-ONLY | system (CONTRACT-SHARED-BUDGET-NO-OVERSPEND) | 0 | 4 | catalogue only |
| REQUIREMENT-SYSTEM-PARTITIONS-SAFE | FW-ONLY | system (CONTRACT-PARTITIONS-END-SAFE); RTL heartbeat | 0 | 0 | not covered |
| REQUIREMENT-SYSTEM-TICKETED-ACTIONS | FW-ONLY | system (CONTRACT-NO-ACTION-WITHOUT-TICKET) | 0 | 5 | catalogue only |
| REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES | FW-ONLY | system (CONTRACT-OVERSIGHT-SURVIVES-MODEL) | 0 | 16 | catalogue only |
| REQUIREMENT-SYSTEM-SIGNATURE-EXACT | FW-ONLY | system (CONTRACT-SIGNATURE-AUTHORIZES-EXACTLY); RTL mailbox status 7 | 0 | 2 | catalogue only |
| REQUIREMENT-SYSTEM-CONTROLS-ENFORCED | FW-ONLY | system (CONTRACT-NAMED-CONTROLS-ENFORCED) | 0 | 1 | catalogue only |
| REQUIREMENT-CRYPTO-ENGINES-CORRECT | FW-ONLY | crypto IP (assumption) | 0 | 3 | catalogue only |
| REQUIREMENT-HALT-BOUND-MEASURED-SILICON | SILICON | silicon (halt bound) | 0 | 0 | not covered |
| REQUIREMENT-LEVERS-WORK-ON-GPU | SILICON | silicon (levers on a real GPU) | 0 | 0 | not covered |
| REQUIREMENT-POWER-LOSS-OPENS-LOOP | SILICON | silicon (normally-open switch) | 0 | 0 | not covered |
| REQUIREMENT-BOARD-LOSS-DEBOUNCE | SILICON | board (sense period); RTL debounce | 2 | 0 | conforms |

## Mutation sample

| # | Requirement | File | Mutant | Test | Outcome |
|---|---|---|---|---|---|
| 1 | REQUIREMENT-COUNTER-REFUSES-DECREMENT | monotonic.py | `self.refused.eq(self.dec_req)` to `self.refused.eq(0)` | `test_mono_decrement_request_refused_and_value_kept` | caught by assertion |
| 2 | REQUIREMENT-COUNTER-FUSE-HIGH-WATER-MARK | monotonic.py | `with m.If(self.hwm > self.value):` to `with m.If(self.hwm != self.value):` | `test_mono_lower_high_water_mark_cannot_pull_back` | caught by assertion |
| 3 | REQUIREMENT-MEASUREMENT-EXTEND-ONLY | measure_reg.py | `with m.If(self.extend):` to `with m.If(self.extend \| self.hash_done):` | `test_meas_engine_output_without_request_ignored` | caught by assertion |
| 4 | REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM | epoch_reg.py | `with m.If(self.commit & self.quorum_ok):` to `with m.If(self.commit):` | `test_epoch_commit_without_quorum_ignored` | caught by assertion |
| 5 | REQUIREMENT-LIFECYCLE-MONOTONE-NO-DEBUG | lifecycle.py | `with m.If(self.advance_to > self.state):` to `with m.If(self.advance_to != self.state):` | `test_lifecycle_never_moves_down_by_advance` | caught by assertion |
| 6 | REQUIREMENT-PRODUCTION-HAS-NO-DEBUG | lifecycle.py | `self.debug_grant.eq(self.debug_req & self.loaded & (self.state < PRODUCTION)),` to `self.debug_grant.eq(self.debug_req & self.loaded & (self.state <= PRODUCTION)),` | `test_lifecycle_debug_refused_in_production_and_later` | caught by assertion |
| 7 | REQUIREMENT-CAPABILITY-REFUSES-ON-EXPIRY | cap_table.py | `with m.Elif(self.expiry[hit] <= self.now):` to `with m.Elif(self.expiry[hit] < self.now):` | `test_cap_refuses_at_expiry_and_drops_entry` | caught by assertion |
| 8 | REQUIREMENT-CAPABILITY-REFUSES-STALE-TAG | cap_table.py | `with m.Elif(self.etag[hit] != self.epoch_tag):` to `with m.Elif(0):` | `test_cap_refuses_on_epoch_tag_mismatch` | caught by assertion |
| 9 | REQUIREMENT-MAC-CHECKED-AT-INSERTION | cap_table.py | `with m.Elif(self.ins & self.mac_ok & found):` to `with m.Elif(self.ins & found):` | `test_cap_insert_needs_mac` | caught by assertion |
| 10 | REQUIREMENT-BUDGET-NEVER-UNDERFLOWS | cap_table.py | `with m.Elif(self.budget[hit] < self.lk_bytes):` to `with m.Elif(0):` | `test_cap_refuses_more_than_remaining_budget` | caught by assertion |
| 11 | REQUIREMENT-PORT-OPEN-ONLY-WITH-ENTRY | top.py | `c.clear_all.eq(self.halt.ports_closed)` to `c.clear_all.eq(0)` | `test_core_tables_empty_whenever_not_running` | caught by assertion |
| 12 | REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED | ticket_store.py | `m.d.comb += self.seen.eq(match)` to `m.d.comb += self.seen.eq(0)` | `test_ticket_seen_after_burn` | caught by assertion |
| 13 | REQUIREMENT-HEARTBEAT-EXPIRES-ON-TIME | heartbeat.py | `m.d.sync += self.remaining.eq(self.remaining - 1)` to `m.d.sync += self.remaining.eq(self.remaining - 0)` | `test_hb_expires_on_the_window_th_tick` | caught by assertion |
| 14 | REQUIREMENT-HEARTBEAT-RELOADS-ONLY-ON-VALID | heartbeat.py | `with m.If(self.hb_valid):` to `with m.If(self.hb_valid \| (self.window != 0)):` | `test_hb_reload_only_on_valid` | caught by assertion |
| 15 | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES | halt.py | `with m.Elif((self.hb_expired \| self.local_trip \| self.cmd_throttle) & (self.state == RUN)):` to `with m.Elif((self.hb_expired \| self.cmd_throttle) & (self.state == RUN)):` | `test_halt_local_trip_throttles` | caught by assertion |
| 16 | REQUIREMENT-LEVERS-FOLLOW-RUNG | halt.py | `self.perst.eq((self.state == HALTED_INITIAL) \| (self.state == HALT) \| (self.state == SAFE)),` to `self.perst.eq((self.state == HALTED_INITIAL) \| (self.state == HALT)),` | `test_halt_levers_follow_every_rung` | caught by assertion |
| 17 | REQUIREMENT-SWITCH-CLOSES-ONLY-WHEN-ARMED | halt.py | `with m.Elif((self.state == HALTED_INITIAL) & (self.cause == C_NONE) & self.hb_ok):` to `with m.Elif((self.state == HALTED_INITIAL) & (self.cause == C_NONE)):` | `test_halt_no_arming_without_heartbeat` | caught by assertion |
| 18 | REQUIREMENT-CLEAR-KEEPS-SWITCH-OPEN | halt.py | `m.d.sync += [self.state.eq(HALTED_INITIAL), self.cause.eq(C_NONE), self.timer.eq(0)]` to `m.d.sync += [self.state.eq(HALTED_INITIAL), self.cause.eq(C_NONE), self.timer.eq(0), self.switch_open.eq(0)]` | `test_halt_clear_does_not_close_the_switch_until_armed` | caught by assertion |
| 19 | REQUIREMENT-CORE-BOOTS-HALTED-SAFE | halt.py | `self.switch_open = Signal(init=1)` to `self.switch_open = Signal(init=0)` | `test_core_boot_state_levers_and_switch` | caught by assertion |
| 20 | REQUIREMENT-LOOP-LOSS-DEBOUNCE | halt_loop.py | `self.loop_lost.eq(self.count >= self.debounce)` to `self.loop_lost.eq(self.count >= 1)` | `test_loop_one_noisy_sample_is_not_a_loss` | caught by assertion |
| 21 | REQUIREMENT-METER-HOST-WRITE-REFUSED | meter.py | `self.host_wr_refused.eq(self.host_wr)]` to `self.host_wr_refused.eq(0)]` | `test_meter_host_write_refused_and_flagged` | caught by assertion |
| 22 | REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED | mailbox.py | `m.d.comb += seq_ok.eq(self.frame_seq > self.last_seq[self.key_slot])` to `m.d.comb += seq_ok.eq(self.frame_seq >= self.last_seq[self.key_slot])` | `test_mbox_good_frame_dispatches_once` | caught by assertion |
| 23 | REQUIREMENT-FRAME-EPOCH-MUST-MATCH | mailbox.py | `with m.Elif(~(self.epoch_match \| self.epoch_exempt)):` to `with m.Elif(~self.epoch_match):` | `test_mbox_stale_epoch_refused_unless_exempt` | caught by assertion |
| 24 | REQUIREMENT-SIGNED-PAYLOAD-NAMES-COMMAND | mailbox.py | `with m.If(self.sig_ok & (self.signed_cmd == self.cmd)):` to `with m.If(self.sig_ok):` | `test_mbox_signed_for_another_command_is_status_7` | caught by assertion |
| 25 | REQUIREMENT-SEQUENCE-REGISTER-PER-KEY | top.py | `self.csr_rdata.eq(self.mbox.last_seq[0])` to `self.csr_rdata.eq(self.mbox.last_seq[1])` | `test_core_mbox_status_and_seq_csrs` | caught by assertion |
| 26 | REQUIREMENT-MAILBOX-STATUS-CODES | mailbox.py | `with m.Elif(self.needs_run & ~self.running):` to `with m.Elif(0):` | `test_mbox_refused_when_not_running` | caught by assertion |
| 27 | REQUIREMENT-ALARM-CLEAR-NEEDS-AUTHORIZATION | alarms.py | `m.d.comb += cleared.eq(self.alarms & ~(self.clear_mask & self.clear_authorized.replicate(len(self.alarms))))` to `m.d.comb += cleared.eq(self.alarms & ~self.clear_mask)` | `test_alarm_clear_needs_authorization` | caught by assertion |
| 28 | REQUIREMENT-HALT-OPENS-LOOP-EVERY-RUNG | halt.py | `            m.d.sync += self.switch_open.eq(1)
        with m.Elif(self.cmd_halt):` to `            pass
        with m.Elif(self.cmd_halt):` | `test_calls_halt_opens_loop_from_every_rung` | caught by assertion |
| 29 | REQUIREMENT-EXCLUDE-ONLY-WHILE-WAITING | halt.py | `with m.Elif(self.cmd_exclude & (self.state == HALTED_INITIAL) & (self.cause == C_NONE)):` to `with m.Elif(self.cmd_exclude):` | `test_calls_exclude_does_nothing_outside_waiting_for_first_heartbeat` | caught by assertion |
| 30 | REQUIREMENT-HARDWARE-ALARMS-SEQUENCER-ONLY | top.py | `HW_ALARMS = (1 << ALARM_NO_FIRST_HEARTBEAT) \| (1 << ALARM_EXCLUDED)` to `HW_ALARMS = (1 << ALARM_EXCLUDED)` | `test_calls_firmware_cannot_raise_the_hardware_alarm_bits` | caught by assertion |

## Every test

| Test | Requirements | Outcome | Seconds |
|---|---|---|---|
| `test_mono_counter_is_64_bits` | REQUIREMENT-MONOTONIC-MICROSECOND-COUNTER | pass | 0.0 |
| `test_mono_advances_once_per_tick` | REQUIREMENT-MONOTONIC-MICROSECOND-COUNTER | pass | 0.0 |
| `test_mono_decrement_request_refused_and_value_kept` | REQUIREMENT-COUNTER-REFUSES-DECREMENT | pass | 0.0 |
| `test_mono_never_decreases_under_random_inputs` | REQUIREMENT-COUNTER-REFUSES-DECREMENT | pass | 0.0 |
| `test_mono_high_water_mark_raises_the_counter` | REQUIREMENT-COUNTER-FUSE-HIGH-WATER-MARK | pass | 0.0 |
| `test_mono_lower_high_water_mark_cannot_pull_back` | REQUIREMENT-COUNTER-FUSE-HIGH-WATER-MARK | pass | 0.0 |
| `test_meas_engine_output_without_request_ignored` | REQUIREMENT-MEASUREMENT-EXTEND-ONLY | pass | 0.0 |
| `test_meas_extend_latches_engine_result` | REQUIREMENT-MEASUREMENT-EXTEND-ONLY | pass | 0.0 |
| `test_meas_has_no_write_port` | REQUIREMENT-MEASUREMENT-EXTEND-ONLY | pass | 0.0 |
| `test_core_meas_csr_windows_read_both_registers` | REQUIREMENT-LOADER-MEASUREMENT-REGISTER, REQUIREMENT-FIRMWARE-MEASUREMENT-REGISTER | pass | 0.0 |
| `test_epoch_commit_without_quorum_ignored` | REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM | pass | 0.0 |
| `test_epoch_quorum_without_commit_ignored` | REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM | pass | 0.0 |
| `test_epoch_host_write_has_no_effect` | REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM | pass | 0.0 |
| `test_epoch_commit_with_quorum_switches` | REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM | pass | 0.0 |
| `test_epoch_tag_is_low_16_bits` | REQUIREMENT-EPOCH-TAG-LOW-BITS | pass | 0.0 |
| `test_core_epoch_csr_reads_256_bits` | REQUIREMENT-EPOCH-IS-POLICY-DIGEST | pass | 0.0 |
| `test_lifecycle_never_moves_down_by_advance` | REQUIREMENT-LIFECYCLE-MONOTONE-NO-DEBUG | pass | 0.0 |
| `test_lifecycle_lower_fuse_load_cannot_move_down` | REQUIREMENT-LIFECYCLE-MONOTONE-NO-DEBUG | pass | 0.0 |
| `test_lifecycle_monotone_under_random_inputs` | REQUIREMENT-LIFECYCLE-MONOTONE-NO-DEBUG | pass | 0.0 |
| `test_lifecycle_debug_refused_in_production_and_later` | REQUIREMENT-PRODUCTION-HAS-NO-DEBUG, REQUIREMENT-JTAG-REFUSED-AND-LOGGED | pass | 0.0 |
| `test_lifecycle_debug_granted_before_production` | REQUIREMENT-PRODUCTION-HAS-NO-DEBUG | pass | 0.0 |
| `test_core_lifecycle_csr_encoding` | REQUIREMENT-LIFECYCLE-REGISTER-ENCODING | pass | 0.0 |
| `test_cap_match_requires_point` | REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH | pass | 0.0 |
| `test_cap_match_requires_peer` | REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH | pass | 0.0 |
| `test_cap_match_requires_direction` | REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH, REQUIREMENT-CAPABILITY-DIRECTION-FIELD | pass | 0.0 |
| `test_cap_both_admits_in_and_out` | REQUIREMENT-CAPABILITY-DIRECTION-FIELD | pass | 0.0 |
| `test_cap_lookup_decrements_by_bytes` | REQUIREMENT-LOOKUP-DECREMENTS-BUDGET | pass | 0.0 |
| `test_cap_refuses_more_than_remaining_budget` | REQUIREMENT-CAPABILITY-REFUSES-AT-ZERO, REQUIREMENT-BUDGET-NEVER-UNDERFLOWS | pass | 0.0 |
| `test_cap_budget_never_underflows_random` | REQUIREMENT-BUDGET-NEVER-UNDERFLOWS | pass | 0.0 |
| `test_cap_refuses_at_expiry_and_drops_entry` | REQUIREMENT-CAPABILITY-REFUSES-ON-EXPIRY | pass | 0.0 |
| `test_cap_refuses_on_epoch_tag_mismatch` | REQUIREMENT-CAPABILITY-REFUSES-STALE-TAG, REQUIREMENT-SWITCH-RECONFIGURED-AFTER-EVENTS | pass | 0.0 |
| `test_cap_insert_needs_mac` | REQUIREMENT-MAC-CHECKED-AT-INSERTION | pass | 0.0 |
| `test_cap_lookup_does_not_consult_mac` | REQUIREMENT-MAC-CHECKED-AT-INSERTION | pass | 0.0 |
| `test_cap_full_table_refuses_insert` | REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH | pass | 0.0 |
| `test_cap_lookup_answers_in_the_same_cycle` | REQUIREMENT-LOOKUP-IN-ONE-CYCLE | pass | 0.0 |
| `test_core_has_one_table_per_point_sized_by_parameter` | REQUIREMENT-TABLE-SIZES-ARE-PARAMETERS, REQUIREMENT-ENFORCEMENT-POINT-NUMBERING | pass | 0.0 |
| `test_core_default_sizes_are_the_spec_prototype` | REQUIREMENT-PROTOTYPE-DEFAULT-SIZES | pass | 0.0 |
| `test_core_tables_empty_whenever_not_running` | REQUIREMENT-PORT-OPEN-ONLY-WITH-ENTRY | pass | 0.0 |
| `test_ticket_seen_after_burn` | REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED, REQUIREMENT-BURN-BEFORE-ADMIT | pass | 0.0 |
| `test_ticket_second_burn_of_same_id_refused` | REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED | pass | 0.0 |
| `test_ticket_full_store_refuses_burn_and_flags` | REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED | pass | 0.0 |
| `test_ticket_never_admitted_twice_random` | REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED | pass | 0.0 |
| `test_hb_expired_at_reset` | REQUIREMENT-HEARTBEAT-EXPIRES-ON-TIME | pass | 0.0 |
| `test_hb_expires_on_the_window_th_tick` | REQUIREMENT-HEARTBEAT-EXPIRES-ON-TIME | pass | 0.0 |
| `test_hb_reload_only_on_valid` | REQUIREMENT-HEARTBEAT-RELOADS-ONLY-ON-VALID | pass | 0.0 |
| `test_hb_valid_wins_over_tick` | REQUIREMENT-HEARTBEAT-RELOADS-ONLY-ON-VALID | pass | 0.0 |
| `test_core_hb_remain_csr` | REQUIREMENT-HEARTBEAT-REMAINING-REGISTER | pass | 0.0 |
| `test_core_timers_ignore_the_raw_microsecond_tick` | REQUIREMENT-MILLISECOND-TICK-FROM-COUNTER | pass | 0.0 |
| `test_halt_loop_lost_from_run` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES, REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE | pass | 0.0 |
| `test_halt_loop_lost_from_throttle` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES, REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE | pass | 0.0 |
| `test_halt_hb_expired_throttles` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES | pass | 0.0 |
| `test_halt_local_trip_throttles` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES | pass | 0.0 |
| `test_halt_cmd_throttle_throttles` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES | pass | 0.0 |
| `test_halt_cmd_halt_from_run` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES, REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE | pass | 0.0 |
| `test_halt_cmd_halt_from_throttle` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES, REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE | pass | 0.0 |
| `test_halt_tamper_from_run` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES, REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE, REQUIREMENT-TAMPER-ZEROIZES-TO-SAFE | pass | 0.0 |
| `test_halt_tamper_from_every_rung` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES, REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE, REQUIREMENT-TAMPER-ZEROIZES-TO-SAFE | pass | 0.0 |
| `test_halt_throttle_escalates_after_t_throttle_ticks` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES, REQUIREMENT-THROTTLE-AND-HALT-TIMERS | pass | 0.0 |
| `test_halt_halt_escalates_after_t_halt_ticks` | REQUIREMENT-RUNG-CLIMBS-ON-CAUSES, REQUIREMENT-THROTTLE-AND-HALT-TIMERS | pass | 0.0 |
| `test_core_default_timers_are_30s_and_300s` | REQUIREMENT-THROTTLE-AND-HALT-TIMERS | pass | 0.0 |
| `test_halt_never_descends_without_clear_random` | REQUIREMENT-RUNG-NEVER-DESCENDS-UNCLEARED | pass | 0.2 |
| `test_halt_safe_is_absorbing_without_clear` | REQUIREMENT-RUNG-NEVER-DESCENDS-UNCLEARED | pass | 0.0 |
| `test_halt_levers_follow_every_rung` | REQUIREMENT-LEVERS-FOLLOW-RUNG | pass | 0.0 |
| `test_halt_ports_closed_outside_run` | REQUIREMENT-LEVERS-FOLLOW-RUNG | pass | 0.0 |
| `test_halt_switch_open_at_reset` | REQUIREMENT-SWITCH-CLOSES-ONLY-WHEN-ARMED | pass | 0.0 |
| `test_halt_no_arming_without_heartbeat` | REQUIREMENT-SWITCH-CLOSES-ONLY-WHEN-ARMED, REQUIREMENT-BOOT-REFUSED-STAYS-HALTED | pass | 0.0 |
| `test_halt_arms_before_loop_current` | REQUIREMENT-SWITCH-CLOSES-ONLY-WHEN-ARMED | pass | 0.0 |
| `test_halt_heartbeat_alone_never_recloses_after_a_loop_cause` | REQUIREMENT-SWITCH-CLOSES-ONLY-WHEN-ARMED, REQUIREMENT-CLEAR-KEEPS-SWITCH-OPEN | pass | 0.0 |
| `test_halt_clear_does_not_close_the_switch_until_armed` | REQUIREMENT-CLEAR-KEEPS-SWITCH-OPEN, REQUIREMENT-CLEAR-CLOSES-IF-NO-CAUSE | pass | 0.0 |
| `test_halt_clear_in_boot_rung_is_a_no_op` | REQUIREMENT-CLEAR-CLOSES-IF-NO-CAUSE | pass | 0.0 |
| `test_halt_cause_codes_match_the_spec` | REQUIREMENT-CAUSE-BITS-NAME-SUMMARY | pass | 0.0 |
| `test_halt_escalation_keeps_the_cause` | REQUIREMENT-CAUSE-BITS-NAME-SUMMARY | pass | 0.0 |
| `test_halt_state_codes_match_the_spec` | REQUIREMENT-STATE-REGISTER-CODES | pass | 0.0 |
| `test_core_state_and_cause_csrs` | REQUIREMENT-STATE-REGISTER-CODES, REQUIREMENT-CAUSE-REGISTER-LAYOUT | pass | 0.0 |
| `test_core_levers_csr_bits` | REQUIREMENT-LEVERS-REGISTER-BITS | pass | 0.0 |
| `test_core_boot_state_levers_and_switch` | REQUIREMENT-CORE-BOOTS-HALTED-SAFE | pass | 0.0 |
| `test_core_reset_from_run_returns_to_boot_rung` | REQUIREMENT-WATCHDOG-RESETS-TO-HALTED | pass | 0.0 |
| `test_loop_pad_follows_switch_request` | REQUIREMENT-LOOP-PAD-FOLLOWS-SWITCH | pass | 0.0 |
| `test_loop_one_noisy_sample_is_not_a_loss` | REQUIREMENT-LOOP-LOSS-DEBOUNCE, REQUIREMENT-BOARD-LOSS-DEBOUNCE | pass | 0.0 |
| `test_loop_two_low_samples_declare_loss` | REQUIREMENT-LOOP-LOSS-DEBOUNCE, REQUIREMENT-BOARD-LOSS-DEBOUNCE | pass | 0.0 |
| `test_loop_counts_only_on_sample_strobes` | REQUIREMENT-LOOP-LOSS-DEBOUNCE | pass | 0.0 |
| `test_core_loop_csr_bits` | REQUIREMENT-LOOP-REGISTER-BITS | pass | 0.0 |
| `test_meter_host_write_refused_and_flagged` | REQUIREMENT-METER-HOST-WRITE-REFUSED | pass | 0.0 |
| `test_meter_counters_only_increase_random` | REQUIREMENT-METER-ONLY-INCREMENTS | pass | 0.0 |
| `test_meter_slots_are_independent` | REQUIREMENT-METER-ONLY-INCREMENTS | pass | 0.0 |
| `test_core_meter_csr_layout` | REQUIREMENT-METER-SLOT-LAYOUT | pass | 0.0 |
| `test_mbox_good_frame_dispatches_once` | REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED, REQUIREMENT-DISPATCH-AFTER-ALL-CHECKS | pass | 0.0 |
| `test_mbox_sequence_must_strictly_increase` | REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED | pass | 0.0 |
| `test_mbox_sequence_is_per_key_slot` | REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED, REQUIREMENT-SEQUENCE-REGISTER-PER-KEY | pass | 0.0 |
| `test_mbox_stale_epoch_refused_unless_exempt` | REQUIREMENT-FRAME-EPOCH-MUST-MATCH | pass | 0.0 |
| `test_mbox_bad_signature_refused` | REQUIREMENT-FRAME-SIGNATURE-CHECKED | pass | 0.0 |
| `test_mbox_no_dispatch_before_signature` | REQUIREMENT-FRAME-SIGNATURE-CHECKED, REQUIREMENT-DISPATCH-AFTER-ALL-CHECKS | pass | 0.0 |
| `test_mbox_signed_for_another_command_is_status_7` | REQUIREMENT-SIGNED-PAYLOAD-NAMES-COMMAND, REQUIREMENT-WRONG-COMMAND-STATUS | pass | 0.0 |
| `test_mbox_refused_when_not_running` | REQUIREMENT-MAILBOX-STATUS-CODES | pass | 0.0 |
| `test_mbox_status_codes_match_the_register_map` | REQUIREMENT-MAILBOX-STATUS-CODES | pass | 0.0 |
| `test_mbox_failed_frames_do_not_consume_sequence` | REQUIREMENT-NO-DISPATCH-WITHOUT-FRESH-SEQUENCE, REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED | pass | 0.0 |
| `test_mbox_no_dispatch_without_all_checks_random` | REQUIREMENT-NO-DISPATCH-WITHOUT-FRESH-SEQUENCE | pass | 0.1 |
| `test_core_mbox_status_and_seq_csrs` | REQUIREMENT-SEQUENCE-REGISTER-PER-KEY, REQUIREMENT-MAILBOX-STATUS-CODES | pass | 0.0 |
| `test_core_has_no_csr_write_port` | REQUIREMENT-ONLY-DOORBELL-WRITABLE, REQUIREMENT-NO-CSR-WRITE-PORT | pass | 0.0 |
| `test_core_csr_reads_have_no_side_effects` | REQUIREMENT-ONLY-DOORBELL-WRITABLE, REQUIREMENT-NO-CSR-WRITE-PORT | pass | 0.0 |
| `test_core_id_register` | REQUIREMENT-SILICON-ID-REGISTER | pass | 0.0 |
| `test_core_log_window_is_not_decoded` | REQUIREMENT-LOG-WINDOW-FIRMWARE-MAPPED | pass | 0.0 |
| `test_core_mono_csr_low_and_high_words` | REQUIREMENT-MONOTONIC-MICROSECOND-COUNTER | pass | 0.0 |
| `test_alarm_any_source_sets` | REQUIREMENT-ALARM-SET-BY-ANY-SOURCE, REQUIREMENT-ALARMS-MONOTONE, REQUIREMENT-ANY-PARTY-RAISES-ALARM | pass | 0.0 |
| `test_alarm_clear_needs_authorization` | REQUIREMENT-ALARM-CLEAR-NEEDS-AUTHORIZATION, REQUIREMENT-ALARM-APPROVER-KEY-CLEARS | pass | 0.0 |
| `test_alarm_set_beats_clear_in_the_same_cycle` | REQUIREMENT-ALARM-CLEAR-NEEDS-AUTHORIZATION, REQUIREMENT-ALARMS-MONOTONE | pass | 0.0 |
| `test_alarm_monotone_without_authorization_random` | REQUIREMENT-ALARMS-MONOTONE | pass | 0.0 |
| `test_core_alarms_csr` | REQUIREMENT-STICKY-ALARM-REGISTER | pass | 0.0 |
| `test_meter_frozen_slot_stays_put_without_strobes` | REQUIREMENT-METER-SLOT-FREEZE, REQUIREMENT-METER-ONLY-INCREMENTS | pass | 0.0 |
| `test_core_epoch_switch_kills_every_old_capability` | REQUIREMENT-SWITCH-RECONFIGURED-AFTER-EVENTS, REQUIREMENT-EPOCH-TAG-LOW-BITS, REQUIREMENT-RACK-WIDE-EPOCH-SWITCH | pass | 0.0 |
| `test_mbox_self_authenticating_command_rides_on_the_firmware_verdict` | REQUIREMENT-SELF-AUTHENTICATING-COMMANDS, REQUIREMENT-FRAME-EPOCH-MUST-MATCH | pass | 0.0 |
| `test_diff_mailbox_random_frames_only_known_disagreements` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED, REQUIREMENT-FRAME-EPOCH-MUST-MATCH, REQUIREMENT-FRAME-SIGNATURE-CHECKED, REQUIREMENT-SIGNED-PAYLOAD-NAMES-COMMAND, REQUIREMENT-MAILBOX-STATUS-CODES, REQUIREMENT-WRONG-COMMAND-STATUS | pass | 0.5 |
| `test_diff_spec_good_halt` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-DISPATCH-AFTER-ALL-CHECKS | pass | 0.0 |
| `test_diff_spec_replayed_halt` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED | pass | 0.0 |
| `test_diff_spec_halt_with_stale_epoch_is_exempt` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-FRAME-EPOCH-MUST-MATCH, REQUIREMENT-EPOCH-EXEMPT-COMMANDS | pass | 0.0 |
| `test_diff_spec_heartbeat_presented_as_clear` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-SIGNED-PAYLOAD-NAMES-COMMAND, REQUIREMENT-WRONG-COMMAND-STATUS | pass | 0.0 |
| `test_diff_spec_stale_epoch_request` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-FRAME-EPOCH-MUST-MATCH | pass | 0.0 |
| `test_diff_spec_forged_request` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-FRAME-SIGNATURE-CHECKED | pass | 0.0 |
| `test_diff_spec_request_while_not_running` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-MAILBOX-STATUS-CODES, REQUIREMENT-TICKET-REFUSED-STALE-OR-STOPPED | pass | 0.0 |
| `test_diff_spec_replayed_and_forged` | REQUIREMENT-FIRST-FAILURE-IS-REASON | pass | 0.0 |
| `test_diff_spec_stale_and_forged` | REQUIREMENT-FIRST-FAILURE-IS-REASON | pass | 0.0 |
| `test_diff_spec_not_running_and_forged` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-MAILBOX-STATUS-CODES | pass | 0.0 |
| `test_diff_spec_clear_for_another_chip` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-HALT-CLEAR-NAME-CHIP-EXPIRY, REQUIREMENT-WRONG-COMMAND-STATUS | pass | 0.0 |
| `test_diff_spec_expired_clear` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-HALT-CLEAR-NAME-CHIP-EXPIRY, REQUIREMENT-WRONG-COMMAND-STATUS | pass | 0.0 |
| `test_diff_spec_per_key_sequence` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED | pass | 0.0 |
| `test_diff_spec_good_heartbeat` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-FRAME-SIGNATURE-CHECKED, REQUIREMENT-HEARTBEAT-RELOADS-TIMER | pass | 0.0 |
| `test_diff_finding_replayed_request_while_not_running` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-MAILBOX-STATUS-CODES | reproduces CONFORMANCE-RUN-STATE-CHECK-ORDER | 0.0 |
| `test_diff_finding_stale_request_while_not_running` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-MAILBOX-STATUS-CODES | reproduces CONFORMANCE-RUN-STATE-CHECK-ORDER | 0.0 |
| `test_diff_finding_first_sequence_number_zero` | REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED, REQUIREMENT-FIRST-FAILURE-IS-REASON | reproduces CONFORMANCE-FIRST-SEQUENCE-NUMBER-ZERO | 0.0 |
| `test_diff_finding_replayed_forged_heartbeat` | REQUIREMENT-FIRST-FAILURE-IS-REASON | reproduces CONFORMANCE-HEARTBEAT-SIGNATURE-CHECKED-FIRST | 0.0 |
| `test_diff_finding_heartbeat_signed_as_something_else` | REQUIREMENT-SIGNED-PAYLOAD-NAMES-COMMAND, REQUIREMENT-FIRST-FAILURE-IS-REASON | reproduces CONFORMANCE-HEARTBEAT-SIGNATURE-CHECKED-FIRST | 0.0 |
| `test_model_clear_handler_reports_the_mailbox_reason` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-CLEAR-NEEDS-LOGGED-CHECKPOINT | pass | 0.0 |
| `test_model_finding_clear_collapses_reasons` | REQUIREMENT-FIRST-FAILURE-IS-REASON, REQUIREMENT-CLEAR-NEEDS-LOGGED-CHECKPOINT | reproduces CONFORMANCE-CLEAR-REPORTS-ONE-REASON | 0.0 |
| `test_fw_epoch_exempt_list_matches_spec` | REQUIREMENT-EPOCH-EXEMPT-COMMANDS | pass | 0.0 |
| `test_fw_authority_expiry_ceiling_is_60s` | REQUIREMENT-HALT-CLEAR-NAME-CHIP-EXPIRY | pass | 0.0 |
| `test_fw_heartbeat_key_cannot_sign_a_halt` | REQUIREMENT-HEARTBEAT-KEY-SIGNS-ONLY-HEARTBEATS, REQUIREMENT-AUTHORITY-KEY-SIGNS-HALT | pass | 0.0 |
| `test_fw_heartbeat_window_is_clamped_to_policy_expiry` | REQUIREMENT-HEARTBEAT-WINDOW-CLAMPED, REQUIREMENT-HEARTBEAT-RELOADS-TIMER | pass | 0.0 |
| `test_fw_host_peer_only_on_pcie` | REQUIREMENT-HOST-PEER-ONLY-ON-PCIE | pass | 0.0 |
| `test_finding_clear_and_tamper_pulse_same_cycle_ends_safe` | REQUIREMENT-TAMPER-ZEROIZES-TO-SAFE, REQUIREMENT-RUNG-NEVER-DESCENDS-UNCLEARED | pass | 0.0 |
| `test_finding_clear_and_tamper_same_cycle_never_leaves_safe_rung` | REQUIREMENT-TAMPER-ZEROIZES-TO-SAFE, REQUIREMENT-RUNG-NEVER-DESCENDS-UNCLEARED | pass | 0.0 |
| `test_level_tamper_with_clear_settles_in_safe` | REQUIREMENT-TAMPER-ZEROIZES-TO-SAFE | pass | 0.0 |
| `test_model_tamper_is_safe_and_unclearable` | REQUIREMENT-FIRMWARE-TAMPER-ZEROIZE, REQUIREMENT-TAMPER-ZEROIZES-TO-SAFE | pass | 0.0 |
| `test_finding_lifecycle_debug_before_fuse_load` | REQUIREMENT-LIFECYCLE-MONOTONE-NO-DEBUG, REQUIREMENT-PRODUCTION-HAS-NO-DEBUG | pass | 0.0 |
| `test_finding_core_reports_test_lifecycle_before_fuse_load` | REQUIREMENT-LIFECYCLE-REGISTER-ENCODING, REQUIREMENT-PRODUCTION-HAS-NO-DEBUG | reproduces CONFORMANCE-DEBUG-BEFORE-FUSE-LOAD | 0.0 |
| `test_lifecycle_after_load_debug_is_dead` | REQUIREMENT-PRODUCTION-HAS-NO-DEBUG | pass | 0.0 |
| `test_finding_cmd_halt_in_safe_opens_the_loop` | REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE, REQUIREMENT-HALT-OPENS-LOOP-EVERY-RUNG | pass | 0.0 |
| `test_model_finding_halt_in_safe_does_not_descend` | REQUIREMENT-RUNG-NEVER-DESCENDS-UNCLEARED, REQUIREMENT-LEVERS-FOLLOW-RUNG, REQUIREMENT-HALT-IN-SAFE-STAYS-SAFE | pass | 0.0 |
| `test_cmd_halt_in_throttle_from_local_cause_opens_loop` | REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE | pass | 0.0 |
| `test_finding_loop_lost_in_halt_sets_switch_open` | REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE | reproduces CONFORMANCE-SWITCH-OPEN-RUN-ONLY | 0.0 |
| `test_finding_heartbeat_expires_on_time` | REQUIREMENT-MILLISECOND-TICK-FROM-COUNTER, REQUIREMENT-HEARTBEAT-EXPIRES-ON-TIME, REQUIREMENT-HEARTBEAT-REMAINING-REGISTER | reproduces CONFORMANCE-MILLISECOND-TICK-TOO-LONG | 0.1 |
| `test_core_ms_strobe_is_derived_from_the_counter` | REQUIREMENT-MILLISECOND-TICK-FROM-COUNTER | pass | 0.1 |
| `test_finding_cap_refuses_at_zero_budget` | REQUIREMENT-CAPABILITY-REFUSES-AT-ZERO | reproduces CONFORMANCE-ZERO-BYTE-LOOKUP-PASSES | 0.0 |
| `test_finding_cap_reprogramming_a_key_replaces_it` | REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH, REQUIREMENT-LOOKUP-DECREMENTS-BUDGET | reproduces CONFORMANCE-DUPLICATE-CAPABILITY-ENTRIES | 0.0 |
| `test_model_switch_replaces_on_reprogram` | REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH, REQUIREMENT-LOOKUP-DECREMENTS-BUDGET | pass | 0.0 |
| `test_diff_cap_table_random_against_model_switch` | REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH, REQUIREMENT-LOOKUP-DECREMENTS-BUDGET, REQUIREMENT-CAPABILITY-REFUSES-AT-ZERO, REQUIREMENT-CAPABILITY-REFUSES-ON-EXPIRY, REQUIREMENT-CAPABILITY-REFUSES-STALE-TAG, REQUIREMENT-BUDGET-NEVER-UNDERFLOWS, REQUIREMENT-CAPABILITY-DIRECTION-FIELD | pass | 0.1 |
| `test_finding_meter_counter_wraps_at_48_bits` | REQUIREMENT-METER-ONLY-INCREMENTS | pass | 0.0 |
| `test_finding_mono_wraps_from_an_all_ones_high_water_mark` | REQUIREMENT-COUNTER-REFUSES-DECREMENT, REQUIREMENT-COUNTER-FUSE-HIGH-WATER-MARK | pass | 0.0 |
| `test_finding_mailbox_sequence_never_moves_backwards` | REQUIREMENT-NO-DISPATCH-WITHOUT-FRESH-SEQUENCE, REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED | reproduces CONFORMANCE-FRAME-NOT-LATCHED | 0.0 |
| `test_finding_spec_status_table_lists_status_7` | REQUIREMENT-MAILBOX-STATUS-CODES, REQUIREMENT-WRONG-COMMAND-STATUS | reproduces CONFORMANCE-STATUS-TABLE-MISSING-ROW | 0.0 |
| `test_diff_levers_per_rung_rtl_equals_model` | REQUIREMENT-LEVERS-FOLLOW-RUNG | pass | 0.0 |
| `test_diff_boot_rung_rtl_equals_model` | REQUIREMENT-SWITCH-CLOSES-ONLY-WHEN-ARMED, REQUIREMENT-BOOT-REFUSED-STAYS-HALTED | pass | 0.0 |
| `test_cap_expired_entry_closes_the_port_for_good` | REQUIREMENT-PORT-OPEN-ONLY-WITH-ENTRY | pass | 0.0 |
| `test_finding_cap_rederived_after_epoch_switch_is_usable` | REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH, REQUIREMENT-SWITCH-RECONFIGURED-AFTER-EVENTS | reproduces CONFORMANCE-DUPLICATE-CAPABILITY-ENTRIES | 0.0 |
| `test_calls_halt_in_safe_from_local_cause_opens_loop_keeps_safe` | REQUIREMENT-HALT-OPENS-LOOP-EVERY-RUNG, REQUIREMENT-HALT-IN-SAFE-STAYS-SAFE | pass | 0.0 |
| `test_calls_halt_opens_loop_from_every_rung` | REQUIREMENT-HALT-OPENS-LOOP-EVERY-RUNG | pass | 0.0 |
| `test_calls_model_halt_in_safe_stays_safe_and_opens_loop` | REQUIREMENT-HALT-IN-SAFE-STAYS-SAFE, REQUIREMENT-RUNG-NEVER-DESCENDS-UNCLEARED | pass | 0.0 |
| `test_calls_core_names_the_chip_waiting_for_its_first_heartbeat` | REQUIREMENT-NO-FIRST-HEARTBEAT-ALARM | pass | 0.0 |
| `test_calls_core_never_raises_no_first_heartbeat_once_armed` | REQUIREMENT-ARMED-CHIP-NEVER-WAITING | pass | 0.0 |
| `test_calls_firmware_cannot_raise_the_hardware_alarm_bits` | REQUIREMENT-HARDWARE-ALARMS-SEQUENCER-ONLY | pass | 0.0 |
| `test_calls_exclude_does_nothing_outside_waiting_for_first_heartbeat` | REQUIREMENT-EXCLUDE-ONLY-WHILE-WAITING | pass | 0.0 |
| `test_calls_exclude_closes_the_pad_and_keeps_every_lever` | REQUIREMENT-EXCLUDED-CHIP-CLOSES-LOOP | pass | 0.0 |
| `test_calls_exclusion_ends_by_heartbeat_halt_or_tamper_only` | REQUIREMENT-EXCLUSION-ENDS-ON-EVENTS | pass | 0.0 |
| `test_calls_model_logs_every_exclude_with_its_signer` | REQUIREMENT-EXCLUDE-LOGGED-WITH-SIGNER | pass | 0.0 |
