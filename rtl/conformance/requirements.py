# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Every testable "must" in docs/04-specification.md (S) and docs/07-verification-plan.md (V).

Each row: id, source (doc and section), the spec's own words (checked verbatim against the doc by the runner,
backticks and line breaks ignored), the block, and who owns the rule.

Owners:
  RTL       the hard core (rtl/governor_rtl, GovernorCore in top.py) decides it
  FW        firmware-owned; RTL only enforces the strobe (the firmware decides, the hard core acts on its strobe)
  FW-ONLY   firmware or system-owned with no RTL strobe at all (the functional model is the only executable form)
  SILICON   a physical claim; not testable in simulation
"""
from __future__ import annotations

RTL, FW, FW_ONLY, SILICON = "RTL", "FW", "FW-ONLY", "SILICON"
OWNER_TEXT = {
    RTL: "hard core (RTL)",
    FW: "firmware-owned; RTL only enforces the strobe",
    FW_ONLY: "firmware/system-owned; no RTL strobe (model only)",
    SILICON: "silicon; not testable in simulation",
}
DOCS = {"S": "docs/04-specification.md", "V": "docs/07-verification-plan.md"}

# (id, doc, section, quote, block, owner)
REQUIREMENTS: list[tuple[str, str, str, str, str, str]] = [
    # ---------------------------------------------------------------- monotonic counter
    # Registered name: REQUIREMENT-MONOTONIC-MICROSECOND-COUNTER (old ID R-001 is kept because code matches on it)
    ("R-001", "S", "1", "Time is the governor's monotonic counter (64-bit, 1 µs ticks, never decremented", "monotonic, top", RTL),
    # Registered name: REQUIREMENT-COUNTER-REFUSES-DECREMENT (old ID R-002 is kept because code matches on it)
    ("R-002", "V", "3", "The counter value never decreases; a decrement request is refused", "monotonic", RTL),
    # Registered name: REQUIREMENT-COUNTER-FUSE-HIGH-WATER-MARK (old ID R-003 is kept because code matches on it)
    ("R-003", "S", "1", "persisted across power loss with a fuse-backed high-water mark", "monotonic", RTL),
    # ---------------------------------------------------------------- measurement registers
    # Registered name: REQUIREMENT-MEASUREMENT-EXTEND-ONLY (old ID R-004 is kept because code matches on it)
    ("R-004", "V", "3", "The register changes only through extend; no write path exists", "measure_reg", RTL),
    # Registered name: REQUIREMENT-LOADER-MEASUREMENT-REGISTER (old ID R-005 is kept because code matches on it)
    ("R-005", "S", "2", "Measurement register 0 (loader); extend-only", "top (MEAS0)", RTL),
    # Registered name: REQUIREMENT-FIRMWARE-MEASUREMENT-REGISTER (old ID R-006 is kept because code matches on it)
    ("R-006", "S", "2", "Measurement register 1 (firmware); extend-only", "top (MEAS1)", RTL),
    # ---------------------------------------------------------------- epoch
    # Registered name: REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM (old ID R-007 is kept because code matches on it)
    ("R-007", "V", "3", "The register changes only on policy_commit with quorum_ok; the host port cannot write it", "epoch_reg", RTL),
    # Registered name: REQUIREMENT-EPOCH-IS-POLICY-DIGEST (old ID R-008 is kept because code matches on it)
    ("R-008", "S", "2", "Policy epoch (digest of the accepted policy image)", "top (EPOCH)", RTL),
    # Registered name: REQUIREMENT-EPOCH-TAG-LOW-BITS (old ID R-009 is kept because code matches on it)
    ("R-009", "S", "5", "epoch_tag: u16 // low bits of the epoch", "epoch_reg, cap_table", RTL),
    # ---------------------------------------------------------------- lifecycle
    # Registered name: REQUIREMENT-LIFECYCLE-MONOTONE-NO-DEBUG (old ID R-010 is kept because code matches on it)
    ("R-010", "V", "3", "The state is monotone; in PRODUCTION, debug_grant is never asserted", "lifecycle", RTL),
    # Registered name: REQUIREMENT-PRODUCTION-HAS-NO-DEBUG (old ID R-011 is kept because code matches on it)
    ("R-011", "V", "1", "Production silicon has no debug path", "lifecycle", RTL),
    # Registered name: REQUIREMENT-LIFECYCLE-REGISTER-ENCODING (old ID R-012 is kept because code matches on it)
    ("R-012", "S", "2", "0 test, 1 provisioned, 2 production, 3 decommissioned (fuse-backed, monotone)", "top (LIFECYCLE)", RTL),
    # Registered name: REQUIREMENT-JTAG-REFUSED-AND-LOGGED (old ID R-013 is kept because code matches on it)
    ("R-013", "V", "4", "JTAG refused in PRODUCTION; attempt logged", "lifecycle (flag); firmware (log)", RTL),
    # ---------------------------------------------------------------- capability table
    # Registered name: REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH (old ID R-014 is kept because code matches on it)
    ("R-014", "S", "5", "The capability table is a content-addressable memory keyed on (point, peer, dir)", "cap_table", RTL),
    # Registered name: REQUIREMENT-LOOKUP-DECREMENTS-BUDGET (old ID R-015 is kept because code matches on it)
    ("R-015", "S", "5", "a lookup decrements budget", "cap_table", RTL),
    # Registered name: REQUIREMENT-CAPABILITY-REFUSES-AT-ZERO (old ID R-016 is kept because code matches on it)
    ("R-016", "S", "5", "refuses at zero, on expiry, or on an epoch-tag mismatch", "cap_table (zero)", RTL),
    # Registered name: REQUIREMENT-CAPABILITY-REFUSES-ON-EXPIRY (old ID R-017 is kept because code matches on it)
    ("R-017", "S", "5", "refuses at zero, on expiry, or on an epoch-tag mismatch", "cap_table (expiry)", RTL),
    # Registered name: REQUIREMENT-CAPABILITY-REFUSES-STALE-TAG (old ID R-018 is kept because code matches on it)
    ("R-018", "S", "5", "refuses at zero, on expiry, or on an epoch-tag mismatch", "cap_table (epoch tag)", RTL),
    # Registered name: REQUIREMENT-MAC-CHECKED-AT-INSERTION (old ID R-019 is kept because code matches on it)
    ("R-019", "S", "5", "The MAC is checked at insertion, not per lookup", "cap_table", RTL),
    # Registered name: REQUIREMENT-BUDGET-NEVER-UNDERFLOWS (old ID R-020 is kept because code matches on it)
    ("R-020", "V", "3", "budget never underflows", "cap_table", RTL),
    # Registered name: REQUIREMENT-CAPABILITY-DIRECTION-FIELD (old ID R-021 is kept because code matches on it)
    ("R-021", "S", "5", "dir: u2 // in, out, both", "cap_table", RTL),
    # Registered name: REQUIREMENT-TABLE-SIZES-ARE-PARAMETERS (old ID R-022 is kept because code matches on it)
    ("R-022", "S", "5", "The sizes are parameters of GovernorCore", "top", RTL),
    # Registered name: REQUIREMENT-PROTOTYPE-DEFAULT-SIZES (old ID R-023 is kept because code matches on it)
    ("R-023", "S", "5", "instantiates the Amaranth defaults (8 entries per point, 16-bit peer, 24-bit budget, 32-bit ticket id, 8-bit command, 4 meter slots of 48 bits)", "top", RTL),
    # Registered name: REQUIREMENT-PORT-OPEN-ONLY-WITH-ENTRY (old ID R-024 is kept because code matches on it)
    ("R-024", "S", "5", "a port or flow is open in the switch exactly when a matching, unexpired entry exists", "top, cap_table", RTL),
    # Registered name: REQUIREMENT-LOOKUP-IN-ONE-CYCLE (old ID R-025 is kept because code matches on it)
    ("R-025", "S", "9", "1 cycle at the checker clock", "cap_table", RTL),
    # Registered name: REQUIREMENT-ENFORCEMENT-POINT-NUMBERING (old ID R-026 is kept because code matches on it)
    ("R-026", "S", "5", "0 NVSwitch port, 1 PCIe switch port, 2 DPU flow, 3 storage path", "top", RTL),
    # ---------------------------------------------------------------- used-ticket store
    # Registered name: REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED (old ID R-027 is kept because code matches on it)
    ("R-027", "V", "3", "A burned id is never admitted again", "ticket_store", RTL),
    # Registered name: REQUIREMENT-BURN-BEFORE-ADMIT (old ID R-028 is kept because code matches on it)
    ("R-028", "V", "3", "burn before admit ordering", "ticket_store", RTL),
    # ---------------------------------------------------------------- heartbeat
    # Registered name: REQUIREMENT-HEARTBEAT-EXPIRES-ON-TIME (old ID R-029 is kept because code matches on it)
    ("R-029", "V", "3", "expired asserts within one millisecond tick of expiry", "heartbeat", RTL),
    # Registered name: REQUIREMENT-HEARTBEAT-RELOADS-ONLY-ON-VALID (old ID R-030 is kept because code matches on it)
    ("R-030", "V", "3", "remaining reloads only on hb_valid, to the window given", "heartbeat", RTL),
    # Registered name: REQUIREMENT-HEARTBEAT-REMAINING-REGISTER (old ID R-031 is kept because code matches on it)
    ("R-031", "S", "2", "Heartbeat time remaining, milliseconds", "top (HB_REMAIN)", RTL),
    # Registered name: REQUIREMENT-MILLISECOND-TICK-FROM-COUNTER (old ID R-032 is kept because code matches on it)
    ("R-032", "S", "9", "the RTL sequencer and heartbeat timers run on a millisecond tick derived from the microsecond counter", "top", RTL),
    # Registered name: REQUIREMENT-HEARTBEAT-WINDOW-CLAMPED (old ID R-033 is kept because code matches on it)
    ("R-033", "S", "9", "the governor clamps any signed window to it", "heartbeat (window input)", FW),
    # ---------------------------------------------------------------- safe-mode sequencer
    # Registered name: REQUIREMENT-RUNG-CLIMBS-ON-CAUSES (old ID R-034 is kept because code matches on it)
    ("R-034", "V", "3", "The rung (state) climbs on any of loop_lost, hb_expired, tamper, cmd_halt, cmd_throttle, local_trip and on the timers", "halt", RTL),
    # Registered name: REQUIREMENT-RUNG-NEVER-DESCENDS-UNCLEARED (old ID R-035 is kept because code matches on it)
    ("R-035", "V", "3", "never descends without clear", "halt", RTL),
    # Registered name: REQUIREMENT-LEVERS-FOLLOW-RUNG (old ID R-036 is kept because code matches on it)
    ("R-036", "V", "3", "the levers pwrbrk, perst, pwr_en follow the rung exactly", "halt", RTL),
    # Registered name: REQUIREMENT-SWITCH-CLOSES-ONLY-WHEN-ARMED (old ID R-037 is kept because code matches on it)
    ("R-037", "V", "3", "switch_open starts set, clears only when armed (no cause, hb_ok)", "halt", RTL),
    # Registered name: REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE (old ID R-038 is kept because code matches on it)
    ("R-038", "V", "3", "sets on loop_lost, tamper or cmd_halt", "halt", RTL),
    # Registered name: REQUIREMENT-CLEAR-KEEPS-SWITCH-OPEN (old ID R-039 is kept because code matches on it)
    ("R-039", "V", "3", "and clear does not reset it", "halt", RTL),
    # Registered name: REQUIREMENT-CAUSE-BITS-NAME-SUMMARY (old ID R-040 is kept because code matches on it)
    ("R-040", "V", "3", "cause bits 2:0 name the summary", "halt", RTL),
    # Registered name: REQUIREMENT-THROTTLE-AND-HALT-TIMERS (old ID R-041 is kept because code matches on it)
    ("R-041", "S", "9", "30 s / 300 s", "halt, top", RTL),
    # Registered name: REQUIREMENT-TAMPER-ZEROIZES-TO-SAFE (old ID R-042 is kept because code matches on it)
    ("R-042", "V", "4", "Mesh cut, glitch injection, temperature excursion: keys zeroized, state SAFE", "halt (tamper)", RTL),
    # Registered name: REQUIREMENT-STATE-REGISTER-CODES (old ID R-043 is kept because code matches on it)
    ("R-043", "S", "2", "0 HALTED_INITIAL, 1 RUN, 2 THROTTLE, 3 HALT, 4 SAFE", "top (STATE)", RTL),
    # Registered name: REQUIREMENT-LEVERS-REGISTER-BITS (old ID R-044 is kept because code matches on it)
    ("R-044", "S", "2", "bit 0 power brake asserted, bit 1 PERST# asserted, bit 2 PWR_EN low", "top (LEVERS)", RTL),
    # Registered name: REQUIREMENT-CORE-BOOTS-HALTED-SAFE (old ID R-045 is kept because code matches on it)
    ("R-045", "V", "3", "the core boots on the HALTED_INITIAL rung with all three levers in the safe state and the loop switch open", "top", RTL),
    # Registered name: REQUIREMENT-WATCHDOG-RESETS-TO-HALTED (old ID R-046 is kept because code matches on it)
    ("R-046", "V", "5", "Watchdog resets the governor into HALTED_INITIAL; loop opens", "top (reset)", RTL),
    # Registered name: REQUIREMENT-CLEAR-CLOSES-IF-NO-CAUSE (old ID R-047 is kept because code matches on it)
    ("R-047", "S", "3", "close the loop switch if no cause remains", "halt (clear strobe)", RTL),
    # Yobie's two design calls, 23 October 2026 (docs/04 sections 2 and 3, docs/07 section 3)
    # Registered name: REQUIREMENT-HALT-OPENS-LOOP-EVERY-RUNG (old ID R-144 is kept because code matches on it)
    ("R-144", "S", "3", "A HALT opens the loop switch on every rung, SAFE included", "halt", RTL),
    # Registered name: REQUIREMENT-HALT-IN-SAFE-STAYS-SAFE (old ID R-145 is kept because code matches on it)
    ("R-145", "S", "3", "a HALT to a chip already in SAFE leaves it in SAFE with power off", "halt; model enter_safe_mode", RTL),
    # Registered name: REQUIREMENT-NO-FIRST-HEARTBEAT-ALARM (old ID R-146 is kept because code matches on it)
    ("R-146", "S", "2", "ALARMS bit 31 is NO_FIRST_HEARTBEAT, set by the hardware when the chip has sat in HALTED_INITIAL with no cause and no valid heartbeat for longer than the boot window", "halt, top (ALARMS, CAUSE, BOOT_WAIT)", RTL),
    # Registered name: REQUIREMENT-ARMED-CHIP-NEVER-WAITING (old ID R-147 is kept because code matches on it)
    ("R-147", "S", "2", "It is never set once the chip has been armed since reset", "halt, top", RTL),
    # Registered name: REQUIREMENT-HARDWARE-ALARMS-SEQUENCER-ONLY (old ID R-148 is kept because code matches on it)
    ("R-148", "S", "2", "only the sequencer raises them and firmware cannot raise them", "top, alarms (hw_mask)", RTL),
    # Registered name: REQUIREMENT-EXCLUDE-ONLY-WHILE-WAITING (old ID R-149 is kept because code matches on it)
    ("R-149", "S", "3", "EXCLUDE has no effect in any state but HALTED_INITIAL with no cause", "halt", RTL),
    # Registered name: REQUIREMENT-EXCLUDED-CHIP-CLOSES-LOOP (old ID R-150 is kept because code matches on it)
    ("R-150", "S", "3", "the excluded chip closes its own loop switch so the rest of the rack can run, while its own levers stay asserted", "halt, top", RTL),
    # Registered name: REQUIREMENT-EXCLUSION-ENDS-ON-EVENTS (old ID R-151 is kept because code matches on it)
    ("R-151", "S", "3", "It leaves exclusion when a valid heartbeat arms it normally, on a reset, or when a HALT or a tamper moves it to a halted rung with its loop open", "halt", RTL),
    # Registered name: REQUIREMENT-EXCLUDE-LOGGED-WITH-SIGNER (old ID R-152 is kept because code matches on it)
    ("R-152", "S", "3", "every EXCLUDE is logged with who signed it", "model (_cmd_exclude); firmware", FW),
    # ---------------------------------------------------------------- loop
    # Registered name: REQUIREMENT-LOOP-PAD-FOLLOWS-SWITCH (old ID R-048 is kept because code matches on it)
    ("R-048", "V", "3", "loop_out_open follows switch_open", "halt_loop", RTL),
    # Registered name: REQUIREMENT-LOOP-LOSS-DEBOUNCE (old ID R-049 is kept because code matches on it)
    ("R-049", "V", "3", "loop_sense low for two samples drives loop_lost (debounce)", "halt_loop", RTL),
    # Registered name: REQUIREMENT-LOOP-REGISTER-BITS (old ID R-050 is kept because code matches on it)
    ("R-050", "S", "2", "bit 0 loop current sensed, bit 1 own switch open", "top (LOOP)", RTL),
    # ---------------------------------------------------------------- meter
    # Registered name: REQUIREMENT-METER-HOST-WRITE-REFUSED (old ID R-051 is kept because code matches on it)
    ("R-051", "V", "3", "Counters are read-only from the host port (host_wr is refused and flagged)", "meter", RTL),
    # Registered name: REQUIREMENT-METER-ONLY-INCREMENTS (old ID R-052 is kept because code matches on it)
    ("R-052", "V", "3", "and only increment", "meter", RTL),
    # Registered name: REQUIREMENT-METER-SLOT-LAYOUT (old ID R-053 is kept because code matches on it)
    ("R-053", "S", "2", "tokens, kernel cycles, bytes in, bytes out, per model digest slot", "top (METER_SLOT)", RTL),
    # ---------------------------------------------------------------- mailbox
    # Registered name: REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED (old ID R-054 is kept because code matches on it)
    ("R-054", "S", "3", "sequence number greater than the last accepted one for that signer key", "mailbox", RTL),
    # Registered name: REQUIREMENT-FRAME-EPOCH-MUST-MATCH (old ID R-055 is kept because code matches on it)
    ("R-055", "S", "3", "epoch equal to EPOCH (except the epoch-exempt commands", "mailbox", RTL),
    # Registered name: REQUIREMENT-FRAME-SIGNATURE-CHECKED (old ID R-056 is kept because code matches on it)
    ("R-056", "S", "3", "which move, repair or inspect the epoch itself and must work when it is stale), then the signature", "mailbox", RTL),
    # Registered name: REQUIREMENT-SIGNED-PAYLOAD-NAMES-COMMAND (old ID R-057 is kept because code matches on it)
    ("R-057", "S", "3", "then what was signed: the signed payload names the command it is for", "mailbox", RTL),
    # Registered name: REQUIREMENT-FIRST-FAILURE-IS-REASON (old ID R-058 is kept because code matches on it)
    ("R-058", "S", "3", "The first failing check is the reason reported; the model (_check_signed) and the RTL (mailbox.py) check in the same order", "mailbox vs govsim", RTL),
    # Registered name: REQUIREMENT-DISPATCH-AFTER-ALL-CHECKS (old ID R-059 is kept because code matches on it)
    ("R-059", "S", "3", "Only then is the command dispatched.", "mailbox", RTL),
    # Registered name: REQUIREMENT-SEQUENCE-REGISTER-PER-KEY (old ID R-060 is kept because code matches on it)
    ("R-060", "S", "2", "Last accepted inbound sequence number (key slot 0; one counter per signer key)", "top (MBOX_SEQ), mailbox", RTL),
    # Registered name: REQUIREMENT-MAILBOX-STATUS-CODES (old ID R-061 is kept because code matches on it)
    ("R-061", "S", "2", "0 idle, 1 busy, 2 ok, 3 bad signature, 4 bad sequence, 5 bad epoch, 6 refused", "mailbox, top (MBOX_STATUS)", RTL),
    # Registered name: REQUIREMENT-NO-DISPATCH-WITHOUT-FRESH-SEQUENCE (old ID R-062 is kept because code matches on it)
    ("R-062", "V", "3", "No command is dispatched unless frame_seq is above the key slot's last accepted sequence", "mailbox", RTL),
    # Registered name: REQUIREMENT-WRONG-COMMAND-STATUS (old ID R-063 is kept because code matches on it)
    ("R-063", "S", "3", "(mailbox.wrong_command, mailbox.expired; RTL status 7)", "mailbox", RTL),
    # ---------------------------------------------------------------- top
    # Registered name: REQUIREMENT-ONLY-DOORBELL-WRITABLE (old ID R-064 is kept because code matches on it)
    ("R-064", "S", "2", "There is no writable register other than the doorbell.", "top", RTL),
    # Registered name: REQUIREMENT-NO-CSR-WRITE-PORT (old ID R-065 is kept because code matches on it)
    ("R-065", "V", "3", "No CSR write port but the doorbell", "top", RTL),
    # Registered name: REQUIREMENT-SILICON-ID-REGISTER (old ID R-066 is kept because code matches on it)
    ("R-066", "S", "2", "Silicon id and revision", "top (ID)", RTL),
    # Registered name: REQUIREMENT-CAUSE-REGISTER-LAYOUT (old ID R-067 is kept because code matches on it)
    ("R-067", "S", "2", "Bits 2:0 the sequencer's own summary (0 none, 1 loop, 2 local, 3 tamper, 4 command); bit 3 waiting for the first heartbeat, boot window passed; bit 4 excluded; bits 15:8 the firmware's reason code", "top (CAUSE)", RTL),
    # Registered name: REQUIREMENT-LOG-WINDOW-FIRMWARE-MAPPED (old ID R-068 is kept because code matches on it)
    ("R-068", "S", "2", "firmware-mapped: the log engine is firmware over NVM, so the RTL core does not decode it", "top (LOG_HEAD)", FW_ONLY),
    # ---------------------------------------------------------------- alarms
    # Registered name: REQUIREMENT-ALARM-SET-BY-ANY-SOURCE (old ID R-069 is kept because code matches on it)
    ("R-069", "V", "3", "Bits set by any source through set_mask", "alarms", RTL),
    # Registered name: REQUIREMENT-ALARM-CLEAR-NEEDS-AUTHORIZATION (old ID R-070 is kept because code matches on it)
    ("R-070", "V", "3", "cleared only through clear_mask gated by clear_authorized", "alarms", RTL),
    # Registered name: REQUIREMENT-STICKY-ALARM-REGISTER (old ID R-071 is kept because code matches on it)
    ("R-071", "S", "2", "Sticky alarm bits (monotone; cleared only through the clear path)", "top (ALARMS)", RTL),
    # Registered name: REQUIREMENT-ALARMS-MONOTONE (old ID R-072 is kept because code matches on it)
    ("R-072", "V", "1", "Alarms are monotone", "alarms", RTL),
    # ---------------------------------------------------------------- FMEA rows the hard core carries
    # Registered name: REQUIREMENT-BOOT-REFUSED-STAYS-HALTED (old ID R-073 is kept because code matches on it)
    ("R-073", "V", "5", "Boot refused; the sequencer never leaves HALTED_INITIAL", "halt (hb_ok gate); firmware (boot)", RTL),
    # Registered name: REQUIREMENT-FIRMWARE-TAMPER-ZEROIZE (old ID R-074 is kept because code matches on it)
    ("R-074", "V", "5", "Zeroize, SAFE", "halt (tamper strobe); key manager (zeroize)", FW),
    # ---------------------------------------------------------------- firmware-owned, with an RTL strobe
    # Registered name: REQUIREMENT-EPOCH-EXEMPT-COMMANDS (old ID R-080 is kept because code matches on it)
    ("R-080", "S", "3", "POLICY_PROPOSE, POLICY_COMMIT, ATTEST, HALT, CLEAR, ALARM_CLEAR and EXCLUDE", "mailbox (epoch_exempt input)", FW),
    # Registered name: REQUIREMENT-HALT-CLEAR-NAME-CHIP-EXPIRY (old ID R-081 is kept because code matches on it)
    ("R-081", "S", "3", "a HALT or CLEAR also names the chip it is for and carries an expiry no more than 60 s ahead that has not passed", "mailbox (signed_cmd input)", FW),
    # Registered name: REQUIREMENT-SELF-AUTHENTICATING-COMMANDS (old ID R-082 is kept because code matches on it)
    ("R-082", "S", "3", "Commands that carry their own authentication in the body (an attestation report, a k-of-n signed policy image) are accepted without a frame signature", "mailbox (sig_ok input)", FW),
    # Registered name: REQUIREMENT-HEARTBEAT-RELOADS-TIMER (old ID R-083 is kept because code matches on it)
    ("R-083", "S", "3", "Reloads the heartbeat timer", "heartbeat (hb_valid strobe)", FW),
    # Registered name: REQUIREMENT-HEARTBEAT-KEY-SIGNS-ONLY-HEARTBEATS (old ID R-084 is kept because code matches on it)
    ("R-084", "S", "4", "heartbeat_key: key, // signs heartbeats and nothing else", "heartbeat (hb_valid strobe)", FW),
    # Registered name: REQUIREMENT-AUTHORITY-KEY-SIGNS-HALT (old ID R-085 is kept because code matches on it)
    ("R-085", "S", "3", "an authority key (never the heartbeat key)", "halt (cmd_halt, cmd_throttle strobes)", FW),
    # Registered name: REQUIREMENT-CLEAR-NEEDS-LOGGED-CHECKPOINT (old ID R-086 is kept because code matches on it)
    ("R-086", "S", "3", "Clear the cause if it is in the log and a fabric neighbor has acknowledged the checkpoint that contains it", "halt (clear strobe)", FW),
    # Registered name: REQUIREMENT-RACK-WIDE-EPOCH-SWITCH (old ID R-087 is kept because code matches on it)
    ("R-087", "S", "3", "Switch the epoch (the rack-wide rule in 02)", "epoch_reg (commit, quorum_ok)", FW),
    # Registered name: REQUIREMENT-ANY-PARTY-RAISES-ALARM (old ID R-088 is kept because code matches on it)
    ("R-088", "S", "3", "Raises a sticky alarm (any party may)", "alarms (set_mask)", FW),
    # Registered name: REQUIREMENT-ALARM-APPROVER-KEY-CLEARS (old ID R-089 is kept because code matches on it)
    ("R-089", "S", "3", "the policy's alarm approver key", "alarms (clear_authorized)", FW),
    # Registered name: REQUIREMENT-HOST-PEER-ONLY-ON-PCIE (old ID R-090 is kept because code matches on it)
    ("R-090", "S", "3", "The peer host is accepted only on the PCIe point, never on NVSwitch, DPU or storage", "cap_table (ins, mac_ok)", FW),
    # Registered name: REQUIREMENT-METER-SLOT-FREEZE (old ID R-091 is kept because code matches on it)
    ("R-091", "S", "3", "Freezes the meter slot for that model", "meter (strobe)", FW),
    # Registered name: REQUIREMENT-TICKET-REFUSED-STALE-OR-STOPPED (old ID R-092 is kept because code matches on it)
    ("R-092", "S", "3", "the governor refuses a stale-epoch ticket and refuses while not in RUN", "mailbox (needs_run); firmware (ticket)", FW),
    # Registered name: REQUIREMENT-SWITCH-RECONFIGURED-AFTER-EVENTS (old ID R-093 is kept because code matches on it)
    ("R-093", "S", "5", "the governor re-derives the switch configuration from the table after any epoch, roster or heartbeat event", "cap_table (clear_all, ins)", FW),
    # Registered name: REQUIREMENT-FINGERPRINT-EXTENDED-BY-MANIFEST (old ID R-094 is kept because code matches on it)
    ("R-094", "S", "3", "extends the fingerprint with the manifest digest", "firmware (the fingerprint has no RTL register)", FW_ONLY),
    # ---------------------------------------------------------------- firmware or system only (model-owned)
    # Registered name: REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD (old ID R-100 is kept because code matches on it)
    ("R-100", "S", "3", "Gate core; returns a ticket, a hold id, or a refusal", "gate (firmware)", FW_ONLY),
    # Registered name: REQUIREMENT-HOLD-RELEASED-BY-QUORUM (old ID R-101 is kept because code matches on it)
    ("R-101", "S", "3", "Releases a hold if the policy quorum for that rule is met", "gate (firmware)", FW_ONLY),
    # Registered name: REQUIREMENT-POLICY-VERSION-INCREASING (old ID R-102 is kept because code matches on it)
    ("R-102", "S", "4", "version: u32, // strictly increasing; the anti-rollback counter tracks it", "policy loader, fuses", FW_ONLY),
    # Registered name: REQUIREMENT-THRESHOLD-NOT-BELOW-FUSE (old ID R-103 is kept because code matches on it)
    ("R-103", "S", "4", "never below the fused threshold", "policy loader, fuses", FW_ONLY),
    # Registered name: REQUIREMENT-IMAGE-NEEDS-ASSUMPTION-ROWS (old ID R-104 is kept because code matches on it)
    ("R-104", "S", "4", "refuses an image in which any of them lacks a row in assumptions", "policy loader", FW_ONLY),
    # Registered name: REQUIREMENT-REQUEST-HASH-DEFINITION (old ID R-105 is kept because code matches on it)
    ("R-105", "S", "5", "request_hash = SHA-256(canonical(request_id, fingerprint, action, params))", "gate, endpoint", FW_ONLY),
    # Registered name: REQUIREMENT-FIRMWARE-CHANGE-ROTATES-KEYS (old ID R-106 is kept because code matches on it)
    ("R-106", "S", "7", "A firmware change changes CDI_1 and every key under it.", "key manager (IP)", FW_ONLY),
    # Registered name: REQUIREMENT-APPROVAL-WINDOW-FLOOR (old ID R-107 is kept because code matches on it)
    ("R-107", "S", "9", "policy, never below 10 s", "approvals (firmware)", FW_ONLY),
    # Registered name: REQUIREMENT-STRAGGLER-HALTS-WITHOUT-COMMIT (old ID R-108 is kept because code matches on it)
    ("R-108", "S", "9", "a governor that staged an image and saw no commit stops accepting heartbeats under the staged epoch and halts as a straggler", "policy, heartbeat (firmware)", FW_ONLY),
    # Registered name: REQUIREMENT-PROMPT-HASH-UNVERIFIED-FLAG (old ID R-109 is kept because code matches on it)
    ("R-109", "S", "6", "prompt_hash_verified: false", "provenance record (firmware)", FW_ONLY),
    # Registered name: REQUIREMENT-DEVICE-PROVENANCE-SIGNATURE (old ID R-110 is kept because code matches on it)
    ("R-110", "S", "9", "Device-provenance signature", "crypto engine, firmware batching", FW_ONLY),
    # Registered name: REQUIREMENT-FIRMWARE-UPDATE-GATED (old ID R-111 is kept because code matches on it)
    ("R-111", "S", "8", "Update: signed by the governance root, measured at boot, gated by the anti-rollback counter.", "boot ROM, fuses", FW_ONLY),
    # Registered name: REQUIREMENT-ATTESTATION-QUOTE-CONTENTS (old ID R-112 is kept because code matches on it)
    ("R-112", "S", "3", "Returns the governor's quote: measurements, epoch, lifecycle, counters, over the nonce", "attestation (firmware)", FW_ONLY),
    # Registered name: REQUIREMENT-SIGNED-LOG-CHECKPOINT (old ID R-113 is kept because code matches on it)
    ("R-113", "S", "3", "Signed Merkle root, size, head, neighbor heads", "log engine (firmware)", FW_ONLY),
    # ---------------------------------------------------------------- the hypotheses of docs/07 section 1 (system level)
    # Registered name: REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION (old ID R-120 is kept because code matches on it)
    ("R-120", "V", "1", "Within the boundary, no protected operation executes without a fresh authorization bound to that exact operation", "system (CONTRACT-FRESH-AUTHORIZATION-PER-OPERATION)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-ATTESTATION-BINDING (old ID R-121 is kept because code matches on it)
    ("R-121", "V", "1", "Attestation binds permissions to firmware, model manifest and policy", "system (CONTRACT-ATTESTATION-BINDS-PERMISSIONS)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-CROSSINGS-GOVERNED (old ID R-122 is kept because code matches on it)
    ("R-122", "V", "1", "Every enumerated boundary crossing passes a governed switch", "system (CONTRACT-EVERY-CROSSING-GOVERNED)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-POLICY-QUORUM (old ID R-123 is kept because code matches on it)
    ("R-123", "V", "1", "Policy changes only with a quorum, and never backwards", "system (CONTRACT-POLICY-QUORUM-NO-ROLLBACK); RTL monotonic", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-BROKER-NO-CHOICE (old ID R-124 is kept because code matches on it)
    ("R-124", "V", "1", "The broker cannot choose its rule or lane", "system (CONTRACT-BROKER-CANNOT-PICK-RULE)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-COMPARATOR-HOLDS (old ID R-125 is kept because code matches on it)
    ("R-125", "V", "1", "The comparator holds with every layer above it compromised", "system (CONTRACT-COMPARATOR-SURVIVES-COMPROMISE)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-ASSUMPTIONS-COMPLETE (old ID R-126 is kept because code matches on it)
    ("R-126", "V", "1", "The assumptions register is complete for the deployment", "system (CONTRACT-ASSUMPTIONS-REGISTER-COMPLETE)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-OVERRIDE-SLOW-LOGGED (old ID R-127 is kept because code matches on it)
    ("R-127", "V", "1", "Human override is slow and fully logged", "system (CONTRACT-OVERRIDE-SLOW-AND-LOGGED)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-LEAKAGE-BUDGET (old ID R-128 is kept because code matches on it)
    ("R-128", "V", "1", "Permitted-channel leakage stays within the budget", "system (CONTRACT-LEAKAGE-WITHIN-BUDGET)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-HALT-PROPAGATES (old ID R-129 is kept because code matches on it)
    ("R-129", "V", "1", "A halt propagates to every GPU in the domain within the bound, fail-safe", "system (CONTRACT-HALT-REACHES-EVERY-GPU); RTL halt_loop", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-ROSTER-SPEAKS-ONCE (old ID R-130 is kept because code matches on it)
    ("R-130", "V", "1", "Only roster members speak on the fabric, and only once per message", "system (CONTRACT-ONLY-ROSTER-SPEAKS-ONCE)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-SHARED-BUDGETS (old ID R-131 is kept because code matches on it)
    ("R-131", "V", "1", "Shared budgets cannot be overspent across governors", "system (CONTRACT-SHARED-BUDGET-NO-OVERSPEND)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-PARTITIONS-SAFE (old ID R-132 is kept because code matches on it)
    ("R-132", "V", "1", "Partitions and epoch changes end in safe states, never in stale ones", "system (CONTRACT-PARTITIONS-END-SAFE); RTL heartbeat", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-TICKETED-ACTIONS (old ID R-133 is kept because code matches on it)
    ("R-133", "V", "1", "No governed action initiates without a ticket, and no governed response leaves the rack without a release ticket", "system (CONTRACT-NO-ACTION-WITHOUT-TICKET)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES (old ID R-134 is kept because code matches on it)
    ("R-134", "V", "1", "Oversight survives the model", "system (CONTRACT-OVERSIGHT-SURVIVES-MODEL)", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-SIGNATURE-EXACT (old ID R-135 is kept because code matches on it)
    ("R-135", "V", "1", "A signature authorizes exactly what was signed, and a policy cannot set its own quorum", "system (CONTRACT-SIGNATURE-AUTHORIZES-EXACTLY); RTL mailbox status 7", FW_ONLY),
    # Registered name: REQUIREMENT-SYSTEM-CONTROLS-ENFORCED (old ID R-136 is kept because code matches on it)
    ("R-136", "V", "1", "The controls the rulebook names are enforced, not just stored", "system (CONTRACT-NAMED-CONTROLS-ENFORCED)", FW_ONLY),
    # Registered name: REQUIREMENT-CRYPTO-ENGINES-CORRECT (old ID R-137 is kept because code matches on it)
    ("R-137", "V", "6", "the crypto engines compute what they claim", "crypto IP (assumption)", FW_ONLY),
    # ---------------------------------------------------------------- physical claims
    # Registered name: REQUIREMENT-HALT-BOUND-MEASURED-SILICON (old ID R-140 is kept because code matches on it)
    ("R-140", "V", "4", "Oscilloscope on PWRBRK# across the domain; worst case over temperature and loop length", "silicon (halt bound)", SILICON),
    # Registered name: REQUIREMENT-LEVERS-WORK-ON-GPU (old ID R-141 is kept because code matches on it)
    ("R-141", "V", "4", "PWRBRK# throttles, PERST# resets, PWR_EN cuts", "silicon (levers on a real GPU)", SILICON),
    # Registered name: REQUIREMENT-POWER-LOSS-OPENS-LOOP (old ID R-142 is kept because code matches on it)
    ("R-142", "V", "5", "Governor loses power | Loop opens", "silicon (normally-open switch)", SILICON),
    # Registered name: REQUIREMENT-BOARD-LOSS-DEBOUNCE (old ID R-143 is kept because code matches on it)
    ("R-143", "S", "9", "Loss of current is declared after two sense periods (debounce)", "board (sense period); RTL debounce", SILICON),
]

REQ = {r[0]: r for r in REQUIREMENTS}


def normalize(text: str) -> str:
    return " ".join(text.replace("`", "").replace("\\|", "|").split())
