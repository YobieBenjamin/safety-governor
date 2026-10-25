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
    ("REQUIREMENT-MONOTONIC-MICROSECOND-COUNTER", "S", "1", "Time is the governor's monotonic counter (64-bit, 1 µs ticks, never decremented", "monotonic, top", RTL),
    ("REQUIREMENT-COUNTER-REFUSES-DECREMENT", "V", "3", "The counter value never decreases; a decrement request is refused", "monotonic", RTL),
    ("REQUIREMENT-COUNTER-FUSE-HIGH-WATER-MARK", "S", "1", "persisted across power loss with a fuse-backed high-water mark", "monotonic", RTL),
    # ---------------------------------------------------------------- measurement registers
    ("REQUIREMENT-MEASUREMENT-EXTEND-ONLY", "V", "3", "The register changes only through extend; no write path exists", "measure_reg", RTL),
    ("REQUIREMENT-LOADER-MEASUREMENT-REGISTER", "S", "2", "Measurement register 0 (loader); extend-only", "top (MEAS0)", RTL),
    ("REQUIREMENT-FIRMWARE-MEASUREMENT-REGISTER", "S", "2", "Measurement register 1 (firmware); extend-only", "top (MEAS1)", RTL),
    # ---------------------------------------------------------------- epoch
    ("REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM", "V", "3", "The register changes only on policy_commit with quorum_ok; the host port cannot write it", "epoch_reg", RTL),
    ("REQUIREMENT-EPOCH-IS-POLICY-DIGEST", "S", "2", "Policy epoch (digest of the accepted policy image)", "top (EPOCH)", RTL),
    ("REQUIREMENT-EPOCH-TAG-LOW-BITS", "S", "5", "epoch_tag: u16 // low bits of the epoch", "epoch_reg, cap_table", RTL),
    # ---------------------------------------------------------------- lifecycle
    ("REQUIREMENT-LIFECYCLE-MONOTONE-NO-DEBUG", "V", "3", "The state is monotone; in PRODUCTION, debug_grant is never asserted", "lifecycle", RTL),
    ("REQUIREMENT-PRODUCTION-HAS-NO-DEBUG", "V", "1", "Production silicon has no debug path", "lifecycle", RTL),
    ("REQUIREMENT-LIFECYCLE-REGISTER-ENCODING", "S", "2", "0 test, 1 provisioned, 2 production, 3 decommissioned (fuse-backed, monotone)", "top (LIFECYCLE)", RTL),
    ("REQUIREMENT-JTAG-REFUSED-AND-LOGGED", "V", "4", "JTAG refused in PRODUCTION; attempt logged", "lifecycle (flag); firmware (log)", RTL),
    # ---------------------------------------------------------------- capability table
    ("REQUIREMENT-CAPABILITY-TABLE-KEYED-MATCH", "S", "5", "The capability table is a content-addressable memory keyed on (point, peer, dir)", "cap_table", RTL),
    ("REQUIREMENT-LOOKUP-DECREMENTS-BUDGET", "S", "5", "a lookup decrements budget", "cap_table", RTL),
    ("REQUIREMENT-CAPABILITY-REFUSES-AT-ZERO", "S", "5", "refuses at zero, on expiry, or on an epoch-tag mismatch", "cap_table (zero)", RTL),
    ("REQUIREMENT-CAPABILITY-REFUSES-ON-EXPIRY", "S", "5", "refuses at zero, on expiry, or on an epoch-tag mismatch", "cap_table (expiry)", RTL),
    ("REQUIREMENT-CAPABILITY-REFUSES-STALE-TAG", "S", "5", "refuses at zero, on expiry, or on an epoch-tag mismatch", "cap_table (epoch tag)", RTL),
    ("REQUIREMENT-MAC-CHECKED-AT-INSERTION", "S", "5", "The MAC is checked at insertion, not per lookup", "cap_table", RTL),
    ("REQUIREMENT-BUDGET-NEVER-UNDERFLOWS", "V", "3", "budget never underflows", "cap_table", RTL),
    ("REQUIREMENT-CAPABILITY-DIRECTION-FIELD", "S", "5", "dir: u2 // in, out, both", "cap_table", RTL),
    ("REQUIREMENT-TABLE-SIZES-ARE-PARAMETERS", "S", "5", "The sizes are parameters of GovernorCore", "top", RTL),
    ("REQUIREMENT-PROTOTYPE-DEFAULT-SIZES", "S", "5", "instantiates the Amaranth defaults (8 entries per point, 16-bit peer, 24-bit budget, 32-bit ticket id, 8-bit command, 4 meter slots of 48 bits)", "top", RTL),
    ("REQUIREMENT-PORT-OPEN-ONLY-WITH-ENTRY", "S", "5", "a port or flow is open in the switch exactly when a matching, unexpired entry exists", "top, cap_table", RTL),
    ("REQUIREMENT-LOOKUP-IN-ONE-CYCLE", "S", "9", "1 cycle at the checker clock", "cap_table", RTL),
    ("REQUIREMENT-ENFORCEMENT-POINT-NUMBERING", "S", "5", "0 NVSwitch port, 1 PCIe switch port, 2 DPU flow, 3 storage path", "top", RTL),
    # ---------------------------------------------------------------- used-ticket store
    ("REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED", "V", "3", "A burned id is never admitted again", "ticket_store", RTL),
    ("REQUIREMENT-BURN-BEFORE-ADMIT", "V", "3", "burn before admit ordering", "ticket_store", RTL),
    # ---------------------------------------------------------------- heartbeat
    ("REQUIREMENT-HEARTBEAT-EXPIRES-ON-TIME", "V", "3", "expired asserts within one millisecond tick of expiry", "heartbeat", RTL),
    ("REQUIREMENT-HEARTBEAT-RELOADS-ONLY-ON-VALID", "V", "3", "remaining reloads only on hb_valid, to the window given", "heartbeat", RTL),
    ("REQUIREMENT-HEARTBEAT-REMAINING-REGISTER", "S", "2", "Heartbeat time remaining, milliseconds", "top (HB_REMAIN)", RTL),
    ("REQUIREMENT-MILLISECOND-TICK-FROM-COUNTER", "S", "9", "the RTL sequencer and heartbeat timers run on a millisecond tick derived from the microsecond counter", "top", RTL),
    ("REQUIREMENT-HEARTBEAT-WINDOW-CLAMPED", "S", "9", "the governor clamps any signed window to it", "heartbeat (window input)", FW),
    # ---------------------------------------------------------------- safe-mode sequencer
    ("REQUIREMENT-RUNG-CLIMBS-ON-CAUSES", "V", "3", "The rung (state) climbs on any of loop_lost, hb_expired, tamper, cmd_halt, cmd_throttle, local_trip and on the timers", "halt", RTL),
    ("REQUIREMENT-RUNG-NEVER-DESCENDS-UNCLEARED", "V", "3", "never descends without clear", "halt", RTL),
    ("REQUIREMENT-LEVERS-FOLLOW-RUNG", "V", "3", "the levers pwrbrk, perst, pwr_en follow the rung exactly", "halt", RTL),
    ("REQUIREMENT-SWITCH-CLOSES-ONLY-WHEN-ARMED", "V", "3", "switch_open starts set, clears only when armed (no cause, hb_ok)", "halt", RTL),
    ("REQUIREMENT-SWITCH-OPENS-ON-LOOP-CAUSE", "V", "3", "sets on loop_lost, tamper or cmd_halt", "halt", RTL),
    ("REQUIREMENT-CLEAR-KEEPS-SWITCH-OPEN", "V", "3", "and clear does not reset it", "halt", RTL),
    ("REQUIREMENT-CAUSE-BITS-NAME-SUMMARY", "V", "3", "cause bits 2:0 name the summary", "halt", RTL),
    ("REQUIREMENT-THROTTLE-AND-HALT-TIMERS", "S", "9", "30 s / 300 s", "halt, top", RTL),
    ("REQUIREMENT-TAMPER-ZEROIZES-TO-SAFE", "V", "4", "Mesh cut, glitch injection, temperature excursion: keys zeroized, state SAFE", "halt (tamper)", RTL),
    ("REQUIREMENT-STATE-REGISTER-CODES", "S", "2", "0 HALTED_INITIAL, 1 RUN, 2 THROTTLE, 3 HALT, 4 SAFE", "top (STATE)", RTL),
    ("REQUIREMENT-LEVERS-REGISTER-BITS", "S", "2", "bit 0 power brake asserted, bit 1 PERST# asserted, bit 2 PWR_EN low", "top (LEVERS)", RTL),
    ("REQUIREMENT-CORE-BOOTS-HALTED-SAFE", "V", "3", "the core boots on the HALTED_INITIAL rung with all three levers in the safe state and the loop switch open", "top", RTL),
    ("REQUIREMENT-WATCHDOG-RESETS-TO-HALTED", "V", "5", "Watchdog resets the governor into HALTED_INITIAL; loop opens", "top (reset)", RTL),
    ("REQUIREMENT-CLEAR-CLOSES-IF-NO-CAUSE", "S", "3", "close the loop switch if no cause remains", "halt (clear strobe)", RTL),
    # Yobie's two design calls, 23 October 2026 (docs/04 sections 2 and 3, docs/07 section 3)
    ("REQUIREMENT-HALT-OPENS-LOOP-EVERY-RUNG", "S", "3", "A HALT opens the loop switch on every rung, SAFE included", "halt", RTL),
    ("REQUIREMENT-HALT-IN-SAFE-STAYS-SAFE", "S", "3", "a HALT to a chip already in SAFE leaves it in SAFE with power off", "halt; model enter_safe_mode", RTL),
    ("REQUIREMENT-NO-FIRST-HEARTBEAT-ALARM", "S", "2", "ALARMS bit 31 is NO_FIRST_HEARTBEAT, set by the hardware when the chip has sat in HALTED_INITIAL with no cause and no valid heartbeat for longer than the boot window", "halt, top (ALARMS, CAUSE, BOOT_WAIT)", RTL),
    ("REQUIREMENT-ARMED-CHIP-NEVER-WAITING", "S", "2", "It is never set once the chip has been armed since reset", "halt, top", RTL),
    ("REQUIREMENT-HARDWARE-ALARMS-SEQUENCER-ONLY", "S", "2", "only the sequencer raises them and firmware cannot raise them", "top, alarms (hw_mask)", RTL),
    ("REQUIREMENT-EXCLUDE-ONLY-WHILE-WAITING", "S", "3", "EXCLUDE has no effect in any state but HALTED_INITIAL with no cause", "halt", RTL),
    ("REQUIREMENT-EXCLUDED-CHIP-CLOSES-LOOP", "S", "3", "the excluded chip closes its own loop switch so the rest of the rack can run, while its own levers stay asserted", "halt, top", RTL),
    ("REQUIREMENT-EXCLUSION-ENDS-ON-EVENTS", "S", "3", "It leaves exclusion when a valid heartbeat arms it normally, on a reset, or when a HALT or a tamper moves it to a halted rung with its loop open", "halt", RTL),
    ("REQUIREMENT-EXCLUDE-LOGGED-WITH-SIGNER", "S", "3", "every EXCLUDE is logged with who signed it", "model (_cmd_exclude); firmware", FW),
    # ---------------------------------------------------------------- loop
    ("REQUIREMENT-LOOP-PAD-FOLLOWS-SWITCH", "V", "3", "loop_out_open follows switch_open", "halt_loop", RTL),
    ("REQUIREMENT-LOOP-LOSS-DEBOUNCE", "V", "3", "loop_sense low for two samples drives loop_lost (debounce)", "halt_loop", RTL),
    ("REQUIREMENT-LOOP-REGISTER-BITS", "S", "2", "bit 0 loop current sensed, bit 1 own switch open", "top (LOOP)", RTL),
    # ---------------------------------------------------------------- meter
    ("REQUIREMENT-METER-HOST-WRITE-REFUSED", "V", "3", "Counters are read-only from the host port (host_wr is refused and flagged)", "meter", RTL),
    ("REQUIREMENT-METER-ONLY-INCREMENTS", "V", "3", "and only increment", "meter", RTL),
    ("REQUIREMENT-METER-SLOT-LAYOUT", "S", "2", "tokens, kernel cycles, bytes in, bytes out, per model digest slot", "top (METER_SLOT)", RTL),
    # ---------------------------------------------------------------- mailbox
    ("REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED", "S", "3", "sequence number greater than the last accepted one for that signer key", "mailbox", RTL),
    ("REQUIREMENT-FRAME-EPOCH-MUST-MATCH", "S", "3", "epoch equal to EPOCH (except the epoch-exempt commands", "mailbox", RTL),
    ("REQUIREMENT-FRAME-SIGNATURE-CHECKED", "S", "3", "which move, repair or inspect the epoch itself and must work when it is stale), then the signature", "mailbox", RTL),
    ("REQUIREMENT-SIGNED-PAYLOAD-NAMES-COMMAND", "S", "3", "then what was signed: the signed payload names the command it is for", "mailbox", RTL),
    ("REQUIREMENT-FIRST-FAILURE-IS-REASON", "S", "3", "The first failing check is the reason reported; the model (_check_signed) and the RTL (mailbox.py) check in the same order", "mailbox vs govsim", RTL),
    ("REQUIREMENT-DISPATCH-AFTER-ALL-CHECKS", "S", "3", "Only then is the command dispatched.", "mailbox", RTL),
    ("REQUIREMENT-SEQUENCE-REGISTER-PER-KEY", "S", "2", "Last accepted inbound sequence number (key slot 0; one counter per signer key)", "top (MBOX_SEQ), mailbox", RTL),
    ("REQUIREMENT-MAILBOX-STATUS-CODES", "S", "2", "0 idle, 1 busy, 2 ok, 3 bad signature, 4 bad sequence, 5 bad epoch, 6 refused", "mailbox, top (MBOX_STATUS)", RTL),
    ("REQUIREMENT-NO-DISPATCH-WITHOUT-FRESH-SEQUENCE", "V", "3", "No command is dispatched unless frame_seq is above the key slot's last accepted sequence", "mailbox", RTL),
    ("REQUIREMENT-WRONG-COMMAND-STATUS", "S", "3", "(mailbox.wrong_command, mailbox.expired; RTL status 7)", "mailbox", RTL),
    # ---------------------------------------------------------------- top
    ("REQUIREMENT-ONLY-DOORBELL-WRITABLE", "S", "2", "There is no writable register other than the doorbell.", "top", RTL),
    ("REQUIREMENT-NO-CSR-WRITE-PORT", "V", "3", "No CSR write port but the doorbell", "top", RTL),
    ("REQUIREMENT-SILICON-ID-REGISTER", "S", "2", "Silicon id and revision", "top (ID)", RTL),
    ("REQUIREMENT-CAUSE-REGISTER-LAYOUT", "S", "2", "Bits 2:0 the sequencer's own summary (0 none, 1 loop, 2 local, 3 tamper, 4 command); bit 3 waiting for the first heartbeat, boot window passed; bit 4 excluded; bits 15:8 the firmware's reason code", "top (CAUSE)", RTL),
    ("REQUIREMENT-LOG-WINDOW-FIRMWARE-MAPPED", "S", "2", "firmware-mapped: the log engine is firmware over NVM, so the RTL core does not decode it", "top (LOG_HEAD)", FW_ONLY),
    # ---------------------------------------------------------------- alarms
    ("REQUIREMENT-ALARM-SET-BY-ANY-SOURCE", "V", "3", "Bits set by any source through set_mask", "alarms", RTL),
    ("REQUIREMENT-ALARM-CLEAR-NEEDS-AUTHORIZATION", "V", "3", "cleared only through clear_mask gated by clear_authorized", "alarms", RTL),
    ("REQUIREMENT-STICKY-ALARM-REGISTER", "S", "2", "Sticky alarm bits (monotone; cleared only through the clear path)", "top (ALARMS)", RTL),
    ("REQUIREMENT-ALARMS-MONOTONE", "V", "1", "Alarms are monotone", "alarms", RTL),
    # ---------------------------------------------------------------- FMEA rows the hard core carries
    ("REQUIREMENT-BOOT-REFUSED-STAYS-HALTED", "V", "5", "Boot refused; the sequencer never leaves HALTED_INITIAL", "halt (hb_ok gate); firmware (boot)", RTL),
    ("REQUIREMENT-FIRMWARE-TAMPER-ZEROIZE", "V", "5", "Zeroize, SAFE", "halt (tamper strobe); key manager (zeroize)", FW),
    # ---------------------------------------------------------------- firmware-owned, with an RTL strobe
    ("REQUIREMENT-EPOCH-EXEMPT-COMMANDS", "S", "3", "POLICY_PROPOSE, POLICY_COMMIT, ATTEST, HALT, CLEAR, ALARM_CLEAR and EXCLUDE", "mailbox (epoch_exempt input)", FW),
    ("REQUIREMENT-HALT-CLEAR-NAME-CHIP-EXPIRY", "S", "3", "a HALT or CLEAR also names the chip it is for and carries an expiry no more than 60 s ahead that has not passed", "mailbox (signed_cmd input)", FW),
    ("REQUIREMENT-SELF-AUTHENTICATING-COMMANDS", "S", "3", "Commands that carry their own authentication in the body (an attestation report, a k-of-n signed policy image) are accepted without a frame signature", "mailbox (sig_ok input)", FW),
    ("REQUIREMENT-HEARTBEAT-RELOADS-TIMER", "S", "3", "Reloads the heartbeat timer", "heartbeat (hb_valid strobe)", FW),
    ("REQUIREMENT-HEARTBEAT-KEY-SIGNS-ONLY-HEARTBEATS", "S", "4", "heartbeat_key: key, // signs heartbeats and nothing else", "heartbeat (hb_valid strobe)", FW),
    ("REQUIREMENT-AUTHORITY-KEY-SIGNS-HALT", "S", "3", "an authority key (never the heartbeat key)", "halt (cmd_halt, cmd_throttle strobes)", FW),
    ("REQUIREMENT-CLEAR-NEEDS-LOGGED-CHECKPOINT", "S", "3", "Clear the cause if it is in the log and a fabric neighbor has acknowledged the checkpoint that contains it", "halt (clear strobe)", FW),
    ("REQUIREMENT-RACK-WIDE-EPOCH-SWITCH", "S", "3", "Switch the epoch (the rack-wide rule in 02)", "epoch_reg (commit, quorum_ok)", FW),
    ("REQUIREMENT-ANY-PARTY-RAISES-ALARM", "S", "3", "Raises a sticky alarm (any party may)", "alarms (set_mask)", FW),
    ("REQUIREMENT-ALARM-APPROVER-KEY-CLEARS", "S", "3", "the policy's alarm approver key", "alarms (clear_authorized)", FW),
    ("REQUIREMENT-HOST-PEER-ONLY-ON-PCIE", "S", "3", "The peer host is accepted only on the PCIe point, never on NVSwitch, DPU or storage", "cap_table (ins, mac_ok)", FW),
    ("REQUIREMENT-METER-SLOT-FREEZE", "S", "3", "Freezes the meter slot for that model", "meter (strobe)", FW),
    ("REQUIREMENT-TICKET-REFUSED-STALE-OR-STOPPED", "S", "3", "the governor refuses a stale-epoch ticket and refuses while not in RUN", "mailbox (needs_run); firmware (ticket)", FW),
    ("REQUIREMENT-SWITCH-RECONFIGURED-AFTER-EVENTS", "S", "5", "the governor re-derives the switch configuration from the table after any epoch, roster or heartbeat event", "cap_table (clear_all, ins)", FW),
    ("REQUIREMENT-FINGERPRINT-EXTENDED-BY-MANIFEST", "S", "3", "extends the fingerprint with the manifest digest", "firmware (the fingerprint has no RTL register)", FW_ONLY),
    # ---------------------------------------------------------------- firmware or system only (model-owned)
    ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD", "S", "3", "Gate core; returns a ticket, a hold id, or a refusal", "gate (firmware)", FW_ONLY),
    ("REQUIREMENT-HOLD-RELEASED-BY-QUORUM", "S", "3", "Releases a hold if the policy quorum for that rule is met", "gate (firmware)", FW_ONLY),
    ("REQUIREMENT-POLICY-VERSION-INCREASING", "S", "4", "version: u32, // strictly increasing; the anti-rollback counter tracks it", "policy loader, fuses", FW_ONLY),
    ("REQUIREMENT-THRESHOLD-NOT-BELOW-FUSE", "S", "4", "never below the fused threshold", "policy loader, fuses", FW_ONLY),
    ("REQUIREMENT-IMAGE-NEEDS-ASSUMPTION-ROWS", "S", "4", "refuses an image in which any of them lacks a row in assumptions", "policy loader", FW_ONLY),
    ("REQUIREMENT-REQUEST-HASH-DEFINITION", "S", "5", "request_hash = SHA-256(canonical(request_id, fingerprint, action, params))", "gate, endpoint", FW_ONLY),
    ("REQUIREMENT-FIRMWARE-CHANGE-ROTATES-KEYS", "S", "7", "A firmware change changes CDI_1 and every key under it.", "key manager (IP)", FW_ONLY),
    ("REQUIREMENT-APPROVAL-WINDOW-FLOOR", "S", "9", "policy, never below 10 s", "approvals (firmware)", FW_ONLY),
    ("REQUIREMENT-STRAGGLER-HALTS-WITHOUT-COMMIT", "S", "9", "a governor that staged an image and saw no commit stops accepting heartbeats under the staged epoch and halts as a straggler", "policy, heartbeat (firmware)", FW_ONLY),
    ("REQUIREMENT-PROMPT-HASH-UNVERIFIED-FLAG", "S", "6", "prompt_hash_verified: false", "provenance record (firmware)", FW_ONLY),
    ("REQUIREMENT-DEVICE-PROVENANCE-SIGNATURE", "S", "9", "Device-provenance signature", "crypto engine, firmware batching", FW_ONLY),
    ("REQUIREMENT-FIRMWARE-UPDATE-GATED", "S", "8", "Update: signed by the governance root, measured at boot, gated by the anti-rollback counter.", "boot ROM, fuses", FW_ONLY),
    ("REQUIREMENT-ATTESTATION-QUOTE-CONTENTS", "S", "3", "Returns the governor's quote: measurements, epoch, lifecycle, counters, over the nonce", "attestation (firmware)", FW_ONLY),
    ("REQUIREMENT-SIGNED-LOG-CHECKPOINT", "S", "3", "Signed Merkle root, size, head, neighbor heads", "log engine (firmware)", FW_ONLY),
    # ---------------------------------------------------------------- the hypotheses of docs/07 section 1 (system level)
    ("REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION", "V", "1", "Within the boundary, no protected operation executes without a fresh authorization bound to that exact operation", "system (CONTRACT-FRESH-AUTHORIZATION-PER-OPERATION)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING", "V", "1", "Attestation binds permissions to firmware, model manifest and policy", "system (CONTRACT-ATTESTATION-BINDS-PERMISSIONS)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-CROSSINGS-GOVERNED", "V", "1", "Every enumerated boundary crossing passes a governed switch", "system (CONTRACT-EVERY-CROSSING-GOVERNED)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-POLICY-QUORUM", "V", "1", "Policy changes only with a quorum, and never backwards", "system (CONTRACT-POLICY-QUORUM-NO-ROLLBACK); RTL monotonic", FW_ONLY),
    ("REQUIREMENT-SYSTEM-BROKER-NO-CHOICE", "V", "1", "The broker cannot choose its rule or lane", "system (CONTRACT-BROKER-CANNOT-PICK-RULE)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-COMPARATOR-HOLDS", "V", "1", "The comparator holds with every layer above it compromised", "system (CONTRACT-COMPARATOR-SURVIVES-COMPROMISE)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-ASSUMPTIONS-COMPLETE", "V", "1", "The assumptions register is complete for the deployment", "system (CONTRACT-ASSUMPTIONS-REGISTER-COMPLETE)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-OVERRIDE-SLOW-LOGGED", "V", "1", "Human override is slow and fully logged", "system (CONTRACT-OVERRIDE-SLOW-AND-LOGGED)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-LEAKAGE-BUDGET", "V", "1", "Permitted-channel leakage stays within the budget", "system (CONTRACT-LEAKAGE-WITHIN-BUDGET)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-HALT-PROPAGATES", "V", "1", "A halt propagates to every GPU in the domain within the bound, fail-safe", "system (CONTRACT-HALT-REACHES-EVERY-GPU); RTL halt_loop", FW_ONLY),
    ("REQUIREMENT-SYSTEM-ROSTER-SPEAKS-ONCE", "V", "1", "Only roster members speak on the fabric, and only once per message", "system (CONTRACT-ONLY-ROSTER-SPEAKS-ONCE)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-SHARED-BUDGETS", "V", "1", "Shared budgets cannot be overspent across governors", "system (CONTRACT-SHARED-BUDGET-NO-OVERSPEND)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-PARTITIONS-SAFE", "V", "1", "Partitions and epoch changes end in safe states, never in stale ones", "system (CONTRACT-PARTITIONS-END-SAFE); RTL heartbeat", FW_ONLY),
    ("REQUIREMENT-SYSTEM-TICKETED-ACTIONS", "V", "1", "No governed action initiates without a ticket, and no governed response leaves the rack without a release ticket", "system (CONTRACT-NO-ACTION-WITHOUT-TICKET)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES", "V", "1", "Oversight survives the model", "system (CONTRACT-OVERSIGHT-SURVIVES-MODEL)", FW_ONLY),
    ("REQUIREMENT-SYSTEM-SIGNATURE-EXACT", "V", "1", "A signature authorizes exactly what was signed, and a policy cannot set its own quorum", "system (CONTRACT-SIGNATURE-AUTHORIZES-EXACTLY); RTL mailbox status 7", FW_ONLY),
    ("REQUIREMENT-SYSTEM-CONTROLS-ENFORCED", "V", "1", "The controls the rulebook names are enforced, not just stored", "system (CONTRACT-NAMED-CONTROLS-ENFORCED)", FW_ONLY),
    ("REQUIREMENT-CRYPTO-ENGINES-CORRECT", "V", "6", "the crypto engines compute what they claim", "crypto IP (assumption)", FW_ONLY),
    # ---------------------------------------------------------------- physical claims
    ("REQUIREMENT-HALT-BOUND-MEASURED-SILICON", "V", "4", "Oscilloscope on PWRBRK# across the domain; worst case over temperature and loop length", "silicon (halt bound)", SILICON),
    ("REQUIREMENT-LEVERS-WORK-ON-GPU", "V", "4", "PWRBRK# throttles, PERST# resets, PWR_EN cuts", "silicon (levers on a real GPU)", SILICON),
    ("REQUIREMENT-POWER-LOSS-OPENS-LOOP", "V", "5", "Governor loses power | Loop opens", "silicon (normally-open switch)", SILICON),
    ("REQUIREMENT-BOARD-LOSS-DEBOUNCE", "S", "9", "Loss of current is declared after two sense periods (debounce)", "board (sense period); RTL debounce", SILICON),
]

REQ = {r[0]: r for r in REQUIREMENTS}


def normalize(text: str) -> str:
    return " ".join(text.replace("`", "").replace("\\|", "|").split())
