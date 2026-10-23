# RTL spec conformance

`python -m rtl.conformance` on Python 3.13.16. **Result: PASS** (PASS means the suite does what it says: every conforming test passes, every recorded disagreement reproduces by assertion, every mutant is caught). Disagreements with the spec are findings, listed below; they do not fail the run.

- Requirements: 134 (from docs/04 and docs/07, quotes checked verbatim)
- Conformance tests: 173; 159 conform, 14 reproduce a disagreement
- Catalogue: 87 rows mapped; matches hardware-and-silicon/results/report.json (75/75 attacks blocked, 12/12 baselines allowed, passed=True)
- Catalogue rows + conformance tests: 260 (target 150)
- Mutation sample: 30/30 one-line mutants caught by assertion, over 30 requirements
- Mailbox differential: 4000 random frames, classes {'agree': 3690, 'F-02': 3, 'F-01': 253, 'F-03': 54}
- Capability table differential: {'lookups': 1280, 'allowed': 269, 'inserts': 99}

## Disagreements (findings)

| Finding | Reproducer | What the RTL or model did |
|---|---|---|
| F-01 | `test_diff_finding_replayed_request_while_not_running` | assert: REQUEST seq=2 (last 2) [replayed/low seq, not running]: RTL status 4 (bad sequence), model mailbox.governor_not_running (tests_differential.py:265) |
| F-01 | `test_diff_finding_stale_request_while_not_running` | assert: REQUEST seq=1 (last 0) [stale epoch, not running]: RTL status 5 (bad epoch), model mailbox.governor_not_running (tests_differential.py:265) |
| F-02 | `test_diff_finding_first_sequence_number_zero` | assert: HALT seq=0 (last 0) [replayed/low seq]: RTL status 4 (bad sequence), model ok (tests_differential.py:265) |
| F-03 | `test_diff_finding_replayed_forged_heartbeat` | assert: HEARTBEAT seq=4 (last 4) [replayed/low seq, bad signature]: RTL status 4 (bad sequence), model heartbeat.bad_signature (tests_differential.py:265) |
| F-03 | `test_diff_finding_heartbeat_signed_as_something_else` | assert: HEARTBEAT seq=1 (last 0) [signed for another command]: RTL status 7 (wrong command), model heartbeat.bad_signature (tests_differential.py:265) |
| F-04 | `test_model_finding_clear_collapses_reasons` | assert: clear.unauthorized (tests_differential.py:432) |
| F-06 | `test_finding_core_reports_test_lifecycle_before_fuse_load` | assert: LIFECYCLE reads 0 and debug_grant is 0 (tests_findings.py:134) |
| F-08 | `test_finding_heartbeat_expires_on_time` | assert: heartbeat still live after 2,001 us; HB_REMAIN = 1 (tests_findings.py:261) |
| F-09 | `test_finding_cap_refuses_at_zero_budget` | assert: zero budget, zero-byte lookup allowed (reason 0) (tests_findings.py:299) |
| F-10 | `test_finding_cap_reprogramming_a_key_replaces_it` | assert: a 500-byte lookup passed after the capability was reprogrammed to 10 bytes (tests_findings.py:319) |
| F-10 | `test_finding_cap_rederived_after_epoch_switch_is_usable` | assert: re-derived capability refused (reason 3): the stale entry shadows it (tests_findings.py:547) |
| F-13 | `test_finding_mailbox_sequence_never_moves_backwards` | assert: last accepted sequence moved back to 3 (tests_findings.py:450) |
| F-14 | `test_finding_spec_status_table_lists_status_7` | assert: register map row: / 0x104 / `MBOX_STATUS` / RO / 8 / 0 idle, 1 busy, 2 ok, 3 bad signature, 4 bad sequence, 5 bad epoch, 6 refused / (tests_findings.py:460) |
| F-15 | `test_finding_loop_lost_in_halt_sets_switch_open` | assert: loop_lost in HALT did not set switch_open (tests_findings.py:241) |

First example of each mailbox disagreement class in the random run:

- F-01: CAP_REQUEST seq=0 (last 1) [replayed/low seq, not running]: RTL status 4 (bad sequence), model mailbox.governor_not_running
- F-02: HALT seq=0 (last 0) [replayed/low seq, signed for another command, not running]: RTL status 4 (bad sequence), model mailbox.wrong_command
- F-03: HEARTBEAT seq=1 (last 1) [replayed/low seq, stale epoch, signed for another command, not running]: RTL status 4 (bad sequence), model heartbeat.bad_signature

## Coverage by requirement

| Id | Owner | Block | Conforming tests | Catalogue rows | Verdict |
|---|---|---|---|---|---|
| R-001 | RTL | monotonic, top | 3 | 0 | conforms |
| R-002 | RTL | monotonic | 3 | 0 | conforms |
| R-003 | RTL | monotonic | 3 | 0 | conforms |
| R-004 | RTL | measure_reg | 3 | 0 | conforms |
| R-005 | RTL | top (MEAS0) | 1 | 0 | conforms |
| R-006 | RTL | top (MEAS1) | 1 | 0 | conforms |
| R-007 | RTL | epoch_reg | 4 | 2 | conforms |
| R-008 | RTL | top (EPOCH) | 1 | 0 | conforms |
| R-009 | RTL | epoch_reg, cap_table | 2 | 0 | conforms |
| R-010 | RTL | lifecycle | 4 | 0 | conforms |
| R-011 | RTL | lifecycle | 4 | 0 | DISAGREES F-06 |
| R-012 | RTL | top (LIFECYCLE) | 1 | 0 | DISAGREES F-06 |
| R-013 | RTL | lifecycle (flag); firmware (log) | 1 | 0 | conforms |
| R-014 | RTL | cap_table | 6 | 0 | DISAGREES F-10 |
| R-015 | RTL | cap_table | 3 | 0 | DISAGREES F-10 |
| R-016 | RTL | cap_table (zero) | 2 | 0 | DISAGREES F-09 |
| R-017 | RTL | cap_table (expiry) | 2 | 0 | conforms |
| R-018 | RTL | cap_table (epoch tag) | 2 | 0 | conforms |
| R-019 | RTL | cap_table | 2 | 0 | conforms |
| R-020 | RTL | cap_table | 3 | 0 | conforms |
| R-021 | RTL | cap_table | 3 | 0 | conforms |
| R-022 | RTL | top | 1 | 0 | conforms |
| R-023 | RTL | top | 1 | 0 | conforms |
| R-024 | RTL | top, cap_table | 2 | 0 | conforms |
| R-025 | RTL | cap_table | 1 | 0 | conforms |
| R-026 | RTL | top | 1 | 0 | conforms |
| R-027 | RTL | ticket_store | 4 | 3 | conforms |
| R-028 | RTL | ticket_store | 1 | 1 | conforms |
| R-029 | RTL | heartbeat | 2 | 0 | DISAGREES F-08 |
| R-030 | RTL | heartbeat | 2 | 0 | conforms |
| R-031 | RTL | top (HB_REMAIN) | 1 | 0 | DISAGREES F-08 |
| R-032 | RTL | top | 2 | 0 | DISAGREES F-08 |
| R-033 | FW | heartbeat (window input) | 1 | 0 | conforms |
| R-034 | RTL | halt | 11 | 0 | conforms |
| R-035 | RTL | halt | 6 | 0 | conforms |
| R-036 | RTL | halt | 4 | 0 | conforms |
| R-037 | RTL | halt | 5 | 0 | conforms |
| R-038 | RTL | halt | 8 | 0 | DISAGREES F-15 |
| R-039 | RTL | halt | 2 | 0 | conforms |
| R-040 | RTL | halt | 2 | 0 | conforms |
| R-041 | RTL | halt, top | 3 | 0 | conforms |
| R-042 | RTL | halt (tamper) | 6 | 0 | conforms |
| R-043 | RTL | top (STATE) | 2 | 0 | conforms |
| R-044 | RTL | top (LEVERS) | 1 | 0 | conforms |
| R-045 | RTL | top | 1 | 0 | conforms |
| R-046 | RTL | top (reset) | 1 | 0 | conforms |
| R-047 | RTL | halt (clear strobe) | 2 | 0 | conforms |
| R-144 | RTL | halt | 3 | 0 | conforms |
| R-145 | RTL | halt; model enter_safe_mode | 3 | 0 | conforms |
| R-146 | RTL | halt, top (ALARMS, CAUSE, BOOT_WAIT) | 1 | 0 | conforms |
| R-147 | RTL | halt, top | 1 | 0 | conforms |
| R-148 | RTL | top, alarms (hw_mask) | 1 | 0 | conforms |
| R-149 | RTL | halt | 1 | 0 | conforms |
| R-150 | RTL | halt, top | 1 | 0 | conforms |
| R-151 | RTL | halt | 1 | 0 | conforms |
| R-152 | FW | model (_cmd_exclude); firmware | 1 | 0 | conforms |
| R-048 | RTL | halt_loop | 1 | 0 | conforms |
| R-049 | RTL | halt_loop | 3 | 0 | conforms |
| R-050 | RTL | top (LOOP) | 1 | 0 | conforms |
| R-051 | RTL | meter | 1 | 0 | conforms |
| R-052 | RTL | meter | 4 | 0 | conforms |
| R-053 | RTL | top (METER_SLOT) | 1 | 0 | conforms |
| R-054 | RTL | mailbox | 7 | 0 | DISAGREES F-02,F-13 |
| R-055 | RTL | mailbox | 5 | 0 | conforms |
| R-056 | RTL | mailbox | 5 | 0 | conforms |
| R-057 | RTL | mailbox | 3 | 0 | DISAGREES F-03 |
| R-058 | RTL | mailbox vs govsim | 16 | 0 | DISAGREES F-01,F-02,F-03,F-04 |
| R-059 | RTL | mailbox | 3 | 0 | conforms |
| R-060 | RTL | top (MBOX_SEQ), mailbox | 2 | 0 | conforms |
| R-061 | RTL | mailbox, top (MBOX_STATUS) | 6 | 0 | DISAGREES F-01,F-14 |
| R-062 | RTL | mailbox | 2 | 0 | DISAGREES F-13 |
| R-063 | RTL | mailbox | 5 | 0 | DISAGREES F-14 |
| R-064 | RTL | top | 2 | 0 | conforms |
| R-065 | RTL | top | 2 | 0 | conforms |
| R-066 | RTL | top (ID) | 1 | 0 | conforms |
| R-067 | RTL | top (CAUSE) | 1 | 0 | conforms |
| R-068 | FW-ONLY | top (LOG_HEAD) | 1 | 0 | conforms |
| R-069 | RTL | alarms | 1 | 0 | conforms |
| R-070 | RTL | alarms | 2 | 0 | conforms |
| R-071 | RTL | top (ALARMS) | 1 | 0 | conforms |
| R-072 | RTL | alarms | 3 | 0 | conforms |
| R-073 | RTL | halt (hb_ok gate); firmware (boot) | 2 | 0 | conforms |
| R-074 | FW | halt (tamper strobe); key manager (zeroize) | 1 | 0 | conforms |
| R-080 | FW | mailbox (epoch_exempt input) | 2 | 0 | conforms |
| R-081 | FW | mailbox (signed_cmd input) | 3 | 0 | conforms |
| R-082 | FW | mailbox (sig_ok input) | 1 | 0 | conforms |
| R-083 | FW | heartbeat (hb_valid strobe) | 2 | 0 | conforms |
| R-084 | FW | heartbeat (hb_valid strobe) | 1 | 0 | conforms |
| R-085 | FW | halt (cmd_halt, cmd_throttle strobes) | 1 | 0 | conforms |
| R-086 | FW | halt (clear strobe) | 1 | 0 | DISAGREES F-04 |
| R-087 | FW | epoch_reg (commit, quorum_ok) | 1 | 3 | conforms |
| R-088 | FW | alarms (set_mask) | 1 | 0 | conforms |
| R-089 | FW | alarms (clear_authorized) | 1 | 0 | conforms |
| R-090 | FW | cap_table (ins, mac_ok) | 1 | 0 | conforms |
| R-091 | FW | meter (strobe) | 1 | 0 | conforms |
| R-092 | FW | mailbox (needs_run); firmware (ticket) | 1 | 2 | conforms |
| R-093 | FW | cap_table (clear_all, ins) | 2 | 0 | DISAGREES F-10 |
| R-094 | FW-ONLY | firmware (the fingerprint has no RTL register) | 0 | 0 | not covered |
| R-100 | FW-ONLY | gate (firmware) | 0 | 12 | catalogue only |
| R-101 | FW-ONLY | gate (firmware) | 0 | 8 | catalogue only |
| R-102 | FW-ONLY | policy loader, fuses | 0 | 0 | not covered |
| R-103 | FW-ONLY | policy loader, fuses | 0 | 0 | not covered |
| R-104 | FW-ONLY | policy loader | 0 | 0 | not covered |
| R-105 | FW-ONLY | gate, endpoint | 0 | 5 | catalogue only |
| R-106 | FW-ONLY | key manager (IP) | 0 | 2 | catalogue only |
| R-107 | FW-ONLY | approvals (firmware) | 0 | 0 | not covered |
| R-108 | FW-ONLY | policy, heartbeat (firmware) | 0 | 0 | not covered |
| R-109 | FW-ONLY | provenance record (firmware) | 0 | 0 | not covered |
| R-110 | FW-ONLY | crypto engine, firmware batching | 0 | 0 | not covered |
| R-111 | FW-ONLY | boot ROM, fuses | 0 | 2 | catalogue only |
| R-112 | FW-ONLY | attestation (firmware) | 0 | 4 | catalogue only |
| R-113 | FW-ONLY | log engine (firmware) | 0 | 8 | catalogue only |
| R-120 | FW-ONLY | system (H0) | 0 | 16 | catalogue only |
| R-121 | FW-ONLY | system (H1) | 0 | 14 | catalogue only |
| R-122 | FW-ONLY | system (H2) | 0 | 4 | catalogue only |
| R-123 | FW-ONLY | system (H3); RTL monotonic | 0 | 4 | catalogue only |
| R-124 | FW-ONLY | system (H4) | 0 | 2 | catalogue only |
| R-125 | FW-ONLY | system (H6) | 0 | 4 | catalogue only |
| R-126 | FW-ONLY | system (H7) | 0 | 0 | not covered |
| R-127 | FW-ONLY | system (H8) | 0 | 1 | catalogue only |
| R-128 | FW-ONLY | system (H10) | 0 | 0 | not covered |
| R-129 | FW-ONLY | system (H11); RTL halt_loop | 0 | 0 | not covered |
| R-130 | FW-ONLY | system (H12) | 0 | 0 | not covered |
| R-131 | FW-ONLY | system (H13) | 0 | 4 | catalogue only |
| R-132 | FW-ONLY | system (H14); RTL heartbeat | 0 | 0 | not covered |
| R-133 | FW-ONLY | system (H17) | 0 | 5 | catalogue only |
| R-134 | FW-ONLY | system (H18) | 0 | 16 | catalogue only |
| R-135 | FW-ONLY | system (H19); RTL mailbox status 7 | 0 | 2 | catalogue only |
| R-136 | FW-ONLY | system (H20) | 0 | 1 | catalogue only |
| R-137 | FW-ONLY | crypto IP (assumption) | 0 | 3 | catalogue only |
| R-140 | SILICON | silicon (halt bound) | 0 | 0 | not covered |
| R-141 | SILICON | silicon (levers on a real GPU) | 0 | 0 | not covered |
| R-142 | SILICON | silicon (normally-open switch) | 0 | 0 | not covered |
| R-143 | SILICON | board (sense period); RTL debounce | 2 | 0 | conforms |

## Mutation sample

| # | Requirement | File | Mutant | Test | Outcome |
|---|---|---|---|---|---|
| 1 | R-002 | monotonic.py | `self.refused.eq(self.dec_req)` to `self.refused.eq(0)` | `test_mono_decrement_request_refused_and_value_kept` | caught by assertion |
| 2 | R-003 | monotonic.py | `with m.If(self.hwm > self.value):` to `with m.If(self.hwm != self.value):` | `test_mono_lower_high_water_mark_cannot_pull_back` | caught by assertion |
| 3 | R-004 | measure_reg.py | `with m.If(self.extend):` to `with m.If(self.extend \| self.hash_done):` | `test_meas_engine_output_without_request_ignored` | caught by assertion |
| 4 | R-007 | epoch_reg.py | `with m.If(self.commit & self.quorum_ok):` to `with m.If(self.commit):` | `test_epoch_commit_without_quorum_ignored` | caught by assertion |
| 5 | R-010 | lifecycle.py | `with m.If(self.advance_to > self.state):` to `with m.If(self.advance_to != self.state):` | `test_lifecycle_never_moves_down_by_advance` | caught by assertion |
| 6 | R-011 | lifecycle.py | `self.debug_grant.eq(self.debug_req & self.loaded & (self.state < PRODUCTION)),` to `self.debug_grant.eq(self.debug_req & self.loaded & (self.state <= PRODUCTION)),` | `test_lifecycle_debug_refused_in_production_and_later` | caught by assertion |
| 7 | R-017 | cap_table.py | `with m.Elif(self.expiry[hit] <= self.now):` to `with m.Elif(self.expiry[hit] < self.now):` | `test_cap_refuses_at_expiry_and_drops_entry` | caught by assertion |
| 8 | R-018 | cap_table.py | `with m.Elif(self.etag[hit] != self.epoch_tag):` to `with m.Elif(0):` | `test_cap_refuses_on_epoch_tag_mismatch` | caught by assertion |
| 9 | R-019 | cap_table.py | `with m.Elif(self.ins & self.mac_ok & found):` to `with m.Elif(self.ins & found):` | `test_cap_insert_needs_mac` | caught by assertion |
| 10 | R-020 | cap_table.py | `with m.Elif(self.budget[hit] < self.lk_bytes):` to `with m.Elif(0):` | `test_cap_refuses_more_than_remaining_budget` | caught by assertion |
| 11 | R-024 | top.py | `c.clear_all.eq(self.halt.ports_closed)` to `c.clear_all.eq(0)` | `test_core_tables_empty_whenever_not_running` | caught by assertion |
| 12 | R-027 | ticket_store.py | `m.d.comb += self.seen.eq(match)` to `m.d.comb += self.seen.eq(0)` | `test_ticket_seen_after_burn` | caught by assertion |
| 13 | R-029 | heartbeat.py | `m.d.sync += self.remaining.eq(self.remaining - 1)` to `m.d.sync += self.remaining.eq(self.remaining - 0)` | `test_hb_expires_on_the_window_th_tick` | caught by assertion |
| 14 | R-030 | heartbeat.py | `with m.If(self.hb_valid):` to `with m.If(self.hb_valid \| (self.window != 0)):` | `test_hb_reload_only_on_valid` | caught by assertion |
| 15 | R-034 | halt.py | `with m.Elif((self.hb_expired \| self.local_trip \| self.cmd_throttle) & (self.state == RUN)):` to `with m.Elif((self.hb_expired \| self.cmd_throttle) & (self.state == RUN)):` | `test_halt_local_trip_throttles` | caught by assertion |
| 16 | R-036 | halt.py | `self.perst.eq((self.state == HALTED_INITIAL) \| (self.state == HALT) \| (self.state == SAFE)),` to `self.perst.eq((self.state == HALTED_INITIAL) \| (self.state == HALT)),` | `test_halt_levers_follow_every_rung` | caught by assertion |
| 17 | R-037 | halt.py | `with m.Elif((self.state == HALTED_INITIAL) & (self.cause == C_NONE) & self.hb_ok):` to `with m.Elif((self.state == HALTED_INITIAL) & (self.cause == C_NONE)):` | `test_halt_no_arming_without_heartbeat` | caught by assertion |
| 18 | R-039 | halt.py | `m.d.sync += [self.state.eq(HALTED_INITIAL), self.cause.eq(C_NONE), self.timer.eq(0)]` to `m.d.sync += [self.state.eq(HALTED_INITIAL), self.cause.eq(C_NONE), self.timer.eq(0), self.switch_open.eq(0)]` | `test_halt_clear_does_not_close_the_switch_until_armed` | caught by assertion |
| 19 | R-045 | halt.py | `self.switch_open = Signal(init=1)` to `self.switch_open = Signal(init=0)` | `test_core_boot_state_levers_and_switch` | caught by assertion |
| 20 | R-049 | halt_loop.py | `self.loop_lost.eq(self.count >= self.debounce)` to `self.loop_lost.eq(self.count >= 1)` | `test_loop_one_noisy_sample_is_not_a_loss` | caught by assertion |
| 21 | R-051 | meter.py | `self.host_wr_refused.eq(self.host_wr)]` to `self.host_wr_refused.eq(0)]` | `test_meter_host_write_refused_and_flagged` | caught by assertion |
| 22 | R-054 | mailbox.py | `m.d.comb += seq_ok.eq(self.frame_seq > self.last_seq[self.key_slot])` to `m.d.comb += seq_ok.eq(self.frame_seq >= self.last_seq[self.key_slot])` | `test_mbox_good_frame_dispatches_once` | caught by assertion |
| 23 | R-055 | mailbox.py | `with m.Elif(~(self.epoch_match \| self.epoch_exempt)):` to `with m.Elif(~self.epoch_match):` | `test_mbox_stale_epoch_refused_unless_exempt` | caught by assertion |
| 24 | R-057 | mailbox.py | `with m.If(self.sig_ok & (self.signed_cmd == self.cmd)):` to `with m.If(self.sig_ok):` | `test_mbox_signed_for_another_command_is_status_7` | caught by assertion |
| 25 | R-060 | top.py | `self.csr_rdata.eq(self.mbox.last_seq[0])` to `self.csr_rdata.eq(self.mbox.last_seq[1])` | `test_core_mbox_status_and_seq_csrs` | caught by assertion |
| 26 | R-061 | mailbox.py | `with m.Elif(self.needs_run & ~self.running):` to `with m.Elif(0):` | `test_mbox_refused_when_not_running` | caught by assertion |
| 27 | R-070 | alarms.py | `m.d.comb += cleared.eq(self.alarms & ~(self.clear_mask & self.clear_authorized.replicate(len(self.alarms))))` to `m.d.comb += cleared.eq(self.alarms & ~self.clear_mask)` | `test_alarm_clear_needs_authorization` | caught by assertion |
| 28 | R-144 | halt.py | `            m.d.sync += self.switch_open.eq(1)
        with m.Elif(self.cmd_halt):` to `            pass
        with m.Elif(self.cmd_halt):` | `test_calls_halt_opens_loop_from_every_rung` | caught by assertion |
| 29 | R-149 | halt.py | `with m.Elif(self.cmd_exclude & (self.state == HALTED_INITIAL) & (self.cause == C_NONE)):` to `with m.Elif(self.cmd_exclude):` | `test_calls_exclude_does_nothing_outside_waiting_for_first_heartbeat` | caught by assertion |
| 30 | R-148 | top.py | `HW_ALARMS = (1 << ALARM_NO_FIRST_HEARTBEAT) \| (1 << ALARM_EXCLUDED)` to `HW_ALARMS = (1 << ALARM_EXCLUDED)` | `test_calls_firmware_cannot_raise_the_hardware_alarm_bits` | caught by assertion |

## Every test

| Test | Requirements | Outcome | Seconds |
|---|---|---|---|
| `test_mono_counter_is_64_bits` | R-001 | pass | 0.0 |
| `test_mono_advances_once_per_tick` | R-001 | pass | 0.0 |
| `test_mono_decrement_request_refused_and_value_kept` | R-002 | pass | 0.0 |
| `test_mono_never_decreases_under_random_inputs` | R-002 | pass | 0.2 |
| `test_mono_high_water_mark_raises_the_counter` | R-003 | pass | 0.0 |
| `test_mono_lower_high_water_mark_cannot_pull_back` | R-003 | pass | 0.0 |
| `test_meas_engine_output_without_request_ignored` | R-004 | pass | 0.0 |
| `test_meas_extend_latches_engine_result` | R-004 | pass | 0.0 |
| `test_meas_has_no_write_port` | R-004 | pass | 0.0 |
| `test_core_meas_csr_windows_read_both_registers` | R-005, R-006 | pass | 0.1 |
| `test_epoch_commit_without_quorum_ignored` | R-007 | pass | 0.0 |
| `test_epoch_quorum_without_commit_ignored` | R-007 | pass | 0.0 |
| `test_epoch_host_write_has_no_effect` | R-007 | pass | 0.0 |
| `test_epoch_commit_with_quorum_switches` | R-007 | pass | 0.0 |
| `test_epoch_tag_is_low_16_bits` | R-009 | pass | 0.0 |
| `test_core_epoch_csr_reads_256_bits` | R-008 | pass | 0.1 |
| `test_lifecycle_never_moves_down_by_advance` | R-010 | pass | 0.0 |
| `test_lifecycle_lower_fuse_load_cannot_move_down` | R-010 | pass | 0.0 |
| `test_lifecycle_monotone_under_random_inputs` | R-010 | pass | 0.2 |
| `test_lifecycle_debug_refused_in_production_and_later` | R-011, R-013 | pass | 0.0 |
| `test_lifecycle_debug_granted_before_production` | R-011 | pass | 0.0 |
| `test_core_lifecycle_csr_encoding` | R-012 | pass | 0.1 |
| `test_cap_match_requires_point` | R-014 | pass | 0.0 |
| `test_cap_match_requires_peer` | R-014 | pass | 0.0 |
| `test_cap_match_requires_direction` | R-014, R-021 | pass | 0.0 |
| `test_cap_both_admits_in_and_out` | R-021 | pass | 0.0 |
| `test_cap_lookup_decrements_by_bytes` | R-015 | pass | 0.0 |
| `test_cap_refuses_more_than_remaining_budget` | R-016, R-020 | pass | 0.0 |
| `test_cap_budget_never_underflows_random` | R-020 | pass | 0.1 |
| `test_cap_refuses_at_expiry_and_drops_entry` | R-017 | pass | 0.0 |
| `test_cap_refuses_on_epoch_tag_mismatch` | R-018, R-093 | pass | 0.0 |
| `test_cap_insert_needs_mac` | R-019 | pass | 0.0 |
| `test_cap_lookup_does_not_consult_mac` | R-019 | pass | 0.0 |
| `test_cap_full_table_refuses_insert` | R-014 | pass | 0.0 |
| `test_cap_lookup_answers_in_the_same_cycle` | R-025 | pass | 0.0 |
| `test_core_has_one_table_per_point_sized_by_parameter` | R-022, R-026 | pass | 0.0 |
| `test_core_default_sizes_are_the_spec_prototype` | R-023 | pass | 0.0 |
| `test_core_tables_empty_whenever_not_running` | R-024 | pass | 0.1 |
| `test_ticket_seen_after_burn` | R-027, R-028 | pass | 0.0 |
| `test_ticket_second_burn_of_same_id_refused` | R-027 | pass | 0.0 |
| `test_ticket_full_store_refuses_burn_and_flags` | R-027 | pass | 0.0 |
| `test_ticket_never_admitted_twice_random` | R-027 | pass | 0.0 |
| `test_hb_expired_at_reset` | R-029 | pass | 0.0 |
| `test_hb_expires_on_the_window_th_tick` | R-029 | pass | 0.0 |
| `test_hb_reload_only_on_valid` | R-030 | pass | 0.0 |
| `test_hb_valid_wins_over_tick` | R-030 | pass | 0.0 |
| `test_core_hb_remain_csr` | R-031 | pass | 0.1 |
| `test_core_timers_ignore_the_raw_microsecond_tick` | R-032 | pass | 0.1 |
| `test_halt_loop_lost_from_run` | R-034, R-038 | pass | 0.0 |
| `test_halt_loop_lost_from_throttle` | R-034, R-038 | pass | 0.0 |
| `test_halt_hb_expired_throttles` | R-034 | pass | 0.0 |
| `test_halt_local_trip_throttles` | R-034 | pass | 0.0 |
| `test_halt_cmd_throttle_throttles` | R-034 | pass | 0.0 |
| `test_halt_cmd_halt_from_run` | R-034, R-038 | pass | 0.0 |
| `test_halt_cmd_halt_from_throttle` | R-034, R-038 | pass | 0.0 |
| `test_halt_tamper_from_run` | R-034, R-038, R-042 | pass | 0.0 |
| `test_halt_tamper_from_every_rung` | R-034, R-038, R-042 | pass | 0.0 |
| `test_halt_throttle_escalates_after_t_throttle_ticks` | R-034, R-041 | pass | 0.0 |
| `test_halt_halt_escalates_after_t_halt_ticks` | R-034, R-041 | pass | 0.0 |
| `test_core_default_timers_are_30s_and_300s` | R-041 | pass | 0.0 |
| `test_halt_never_descends_without_clear_random` | R-035 | pass | 0.6 |
| `test_halt_safe_is_absorbing_without_clear` | R-035 | pass | 0.0 |
| `test_halt_levers_follow_every_rung` | R-036 | pass | 0.0 |
| `test_halt_ports_closed_outside_run` | R-036 | pass | 0.0 |
| `test_halt_switch_open_at_reset` | R-037 | pass | 0.0 |
| `test_halt_no_arming_without_heartbeat` | R-037, R-073 | pass | 0.0 |
| `test_halt_arms_before_loop_current` | R-037 | pass | 0.0 |
| `test_halt_heartbeat_alone_never_recloses_after_a_loop_cause` | R-037, R-039 | pass | 0.0 |
| `test_halt_clear_does_not_close_the_switch_until_armed` | R-039, R-047 | pass | 0.0 |
| `test_halt_clear_in_boot_rung_is_a_no_op` | R-047 | pass | 0.0 |
| `test_halt_cause_codes_match_the_spec` | R-040 | pass | 0.0 |
| `test_halt_escalation_keeps_the_cause` | R-040 | pass | 0.0 |
| `test_halt_state_codes_match_the_spec` | R-043 | pass | 0.0 |
| `test_core_state_and_cause_csrs` | R-043, R-067 | pass | 0.1 |
| `test_core_levers_csr_bits` | R-044 | pass | 0.1 |
| `test_core_boot_state_levers_and_switch` | R-045 | pass | 0.1 |
| `test_core_reset_from_run_returns_to_boot_rung` | R-046 | pass | 0.1 |
| `test_loop_pad_follows_switch_request` | R-048 | pass | 0.0 |
| `test_loop_one_noisy_sample_is_not_a_loss` | R-049, R-143 | pass | 0.0 |
| `test_loop_two_low_samples_declare_loss` | R-049, R-143 | pass | 0.0 |
| `test_loop_counts_only_on_sample_strobes` | R-049 | pass | 0.0 |
| `test_core_loop_csr_bits` | R-050 | pass | 0.1 |
| `test_meter_host_write_refused_and_flagged` | R-051 | pass | 0.0 |
| `test_meter_counters_only_increase_random` | R-052 | pass | 0.1 |
| `test_meter_slots_are_independent` | R-052 | pass | 0.0 |
| `test_core_meter_csr_layout` | R-053 | pass | 0.1 |
| `test_mbox_good_frame_dispatches_once` | R-054, R-059 | pass | 0.0 |
| `test_mbox_sequence_must_strictly_increase` | R-054 | pass | 0.0 |
| `test_mbox_sequence_is_per_key_slot` | R-054, R-060 | pass | 0.0 |
| `test_mbox_stale_epoch_refused_unless_exempt` | R-055 | pass | 0.0 |
| `test_mbox_bad_signature_refused` | R-056 | pass | 0.0 |
| `test_mbox_no_dispatch_before_signature` | R-056, R-059 | pass | 0.0 |
| `test_mbox_signed_for_another_command_is_status_7` | R-057, R-063 | pass | 0.0 |
| `test_mbox_refused_when_not_running` | R-061 | pass | 0.0 |
| `test_mbox_status_codes_match_the_register_map` | R-061 | pass | 0.0 |
| `test_mbox_failed_frames_do_not_consume_sequence` | R-062, R-054 | pass | 0.0 |
| `test_mbox_no_dispatch_without_all_checks_random` | R-062 | pass | 0.6 |
| `test_core_mbox_status_and_seq_csrs` | R-060, R-061 | pass | 0.1 |
| `test_core_has_no_csr_write_port` | R-064, R-065 | pass | 0.0 |
| `test_core_csr_reads_have_no_side_effects` | R-064, R-065 | pass | 0.1 |
| `test_core_id_register` | R-066 | pass | 0.1 |
| `test_core_log_window_is_not_decoded` | R-068 | pass | 0.1 |
| `test_core_mono_csr_low_and_high_words` | R-001 | pass | 0.1 |
| `test_alarm_any_source_sets` | R-069, R-072, R-088 | pass | 0.0 |
| `test_alarm_clear_needs_authorization` | R-070, R-089 | pass | 0.0 |
| `test_alarm_set_beats_clear_in_the_same_cycle` | R-070, R-072 | pass | 0.0 |
| `test_alarm_monotone_without_authorization_random` | R-072 | pass | 0.1 |
| `test_core_alarms_csr` | R-071 | pass | 0.1 |
| `test_meter_frozen_slot_stays_put_without_strobes` | R-091, R-052 | pass | 0.0 |
| `test_core_epoch_switch_kills_every_old_capability` | R-093, R-009, R-087 | pass | 0.1 |
| `test_mbox_self_authenticating_command_rides_on_the_firmware_verdict` | R-082, R-055 | pass | 0.0 |
| `test_diff_mailbox_random_frames_only_known_disagreements` | R-058, R-054, R-055, R-056, R-057, R-061, R-063 | pass | 1.7 |
| `test_diff_spec_good_halt` | R-058, R-059 | pass | 0.0 |
| `test_diff_spec_replayed_halt` | R-058, R-054 | pass | 0.0 |
| `test_diff_spec_halt_with_stale_epoch_is_exempt` | R-058, R-055, R-080 | pass | 0.0 |
| `test_diff_spec_heartbeat_presented_as_clear` | R-058, R-057, R-063 | pass | 0.0 |
| `test_diff_spec_stale_epoch_request` | R-058, R-055 | pass | 0.0 |
| `test_diff_spec_forged_request` | R-058, R-056 | pass | 0.0 |
| `test_diff_spec_request_while_not_running` | R-058, R-061, R-092 | pass | 0.0 |
| `test_diff_spec_replayed_and_forged` | R-058 | pass | 0.0 |
| `test_diff_spec_stale_and_forged` | R-058 | pass | 0.0 |
| `test_diff_spec_not_running_and_forged` | R-058, R-061 | pass | 0.0 |
| `test_diff_spec_clear_for_another_chip` | R-058, R-081, R-063 | pass | 0.0 |
| `test_diff_spec_expired_clear` | R-058, R-081, R-063 | pass | 0.0 |
| `test_diff_spec_per_key_sequence` | R-058, R-054 | pass | 0.0 |
| `test_diff_spec_good_heartbeat` | R-058, R-056, R-083 | pass | 0.0 |
| `test_diff_finding_replayed_request_while_not_running` | R-058, R-061 | reproduces F-01 | 0.0 |
| `test_diff_finding_stale_request_while_not_running` | R-058, R-061 | reproduces F-01 | 0.0 |
| `test_diff_finding_first_sequence_number_zero` | R-054, R-058 | reproduces F-02 | 0.0 |
| `test_diff_finding_replayed_forged_heartbeat` | R-058 | reproduces F-03 | 0.0 |
| `test_diff_finding_heartbeat_signed_as_something_else` | R-057, R-058 | reproduces F-03 | 0.0 |
| `test_model_clear_handler_reports_the_mailbox_reason` | R-058, R-086 | pass | 0.0 |
| `test_model_finding_clear_collapses_reasons` | R-058, R-086 | reproduces F-04 | 0.0 |
| `test_fw_epoch_exempt_list_matches_spec` | R-080 | pass | 0.0 |
| `test_fw_authority_expiry_ceiling_is_60s` | R-081 | pass | 0.0 |
| `test_fw_heartbeat_key_cannot_sign_a_halt` | R-084, R-085 | pass | 0.0 |
| `test_fw_heartbeat_window_is_clamped_to_policy_expiry` | R-033, R-083 | pass | 0.0 |
| `test_fw_host_peer_only_on_pcie` | R-090 | pass | 0.0 |
| `test_finding_clear_and_tamper_pulse_same_cycle_ends_safe` | R-042, R-035 | pass | 0.0 |
| `test_finding_clear_and_tamper_same_cycle_never_leaves_safe_rung` | R-042, R-035 | pass | 0.0 |
| `test_level_tamper_with_clear_settles_in_safe` | R-042 | pass | 0.0 |
| `test_model_tamper_is_safe_and_unclearable` | R-074, R-042 | pass | 0.0 |
| `test_finding_lifecycle_debug_before_fuse_load` | R-010, R-011 | pass | 0.0 |
| `test_finding_core_reports_test_lifecycle_before_fuse_load` | R-012, R-011 | reproduces F-06 | 0.1 |
| `test_lifecycle_after_load_debug_is_dead` | R-011 | pass | 0.1 |
| `test_finding_cmd_halt_in_safe_opens_the_loop` | R-038, R-144 | pass | 0.0 |
| `test_model_finding_halt_in_safe_does_not_descend` | R-035, R-036, R-145 | pass | 0.0 |
| `test_cmd_halt_in_throttle_from_local_cause_opens_loop` | R-038 | pass | 0.0 |
| `test_finding_loop_lost_in_halt_sets_switch_open` | R-038 | reproduces F-15 | 0.0 |
| `test_finding_heartbeat_expires_on_time` | R-032, R-029, R-031 | reproduces F-08 | 0.3 |
| `test_core_ms_strobe_is_derived_from_the_counter` | R-032 | pass | 0.4 |
| `test_finding_cap_refuses_at_zero_budget` | R-016 | reproduces F-09 | 0.0 |
| `test_finding_cap_reprogramming_a_key_replaces_it` | R-014, R-015 | reproduces F-10 | 0.0 |
| `test_model_switch_replaces_on_reprogram` | R-014, R-015 | pass | 0.0 |
| `test_diff_cap_table_random_against_model_switch` | R-014, R-015, R-016, R-017, R-018, R-020, R-021 | pass | 0.4 |
| `test_finding_meter_counter_wraps_at_48_bits` | R-052 | pass | 0.0 |
| `test_finding_mono_wraps_from_an_all_ones_high_water_mark` | R-002, R-003 | pass | 0.1 |
| `test_finding_mailbox_sequence_never_moves_backwards` | R-062, R-054 | reproduces F-13 | 0.0 |
| `test_finding_spec_status_table_lists_status_7` | R-061, R-063 | reproduces F-14 | 0.0 |
| `test_diff_levers_per_rung_rtl_equals_model` | R-036 | pass | 0.0 |
| `test_diff_boot_rung_rtl_equals_model` | R-037, R-073 | pass | 0.0 |
| `test_cap_expired_entry_closes_the_port_for_good` | R-024 | pass | 0.0 |
| `test_finding_cap_rederived_after_epoch_switch_is_usable` | R-014, R-093 | reproduces F-10 | 0.0 |
| `test_calls_halt_in_safe_from_local_cause_opens_loop_keeps_safe` | R-144, R-145 | pass | 0.0 |
| `test_calls_halt_opens_loop_from_every_rung` | R-144 | pass | 0.0 |
| `test_calls_model_halt_in_safe_stays_safe_and_opens_loop` | R-145, R-035 | pass | 0.0 |
| `test_calls_core_names_the_chip_waiting_for_its_first_heartbeat` | R-146 | pass | 0.1 |
| `test_calls_core_never_raises_no_first_heartbeat_once_armed` | R-147 | pass | 0.1 |
| `test_calls_firmware_cannot_raise_the_hardware_alarm_bits` | R-148 | pass | 0.1 |
| `test_calls_exclude_does_nothing_outside_waiting_for_first_heartbeat` | R-149 | pass | 0.0 |
| `test_calls_exclude_closes_the_pad_and_keeps_every_lever` | R-150 | pass | 0.1 |
| `test_calls_exclusion_ends_by_heartbeat_halt_or_tamper_only` | R-151 | pass | 0.0 |
| `test_calls_model_logs_every_exclude_with_its_signer` | R-152 | pass | 0.0 |
