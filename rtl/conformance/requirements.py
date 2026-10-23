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
    ("R-001", "S", "1", "Time is the governor's monotonic counter (64-bit, 1 µs ticks, never decremented", "monotonic, top", RTL),
    ("R-002", "V", "3", "The counter value never decreases; a decrement request is refused", "monotonic", RTL),
    ("R-003", "S", "1", "persisted across power loss with a fuse-backed high-water mark", "monotonic", RTL),
    # ---------------------------------------------------------------- measurement registers
    ("R-004", "V", "3", "The register changes only through extend; no write path exists", "measure_reg", RTL),
    ("R-005", "S", "2", "Measurement register 0 (loader); extend-only", "top (MEAS0)", RTL),
    ("R-006", "S", "2", "Measurement register 1 (firmware); extend-only", "top (MEAS1)", RTL),
    # ---------------------------------------------------------------- epoch
    ("R-007", "V", "3", "The register changes only on policy_commit with quorum_ok; the host port cannot write it", "epoch_reg", RTL),
    ("R-008", "S", "2", "Policy epoch (digest of the accepted policy image)", "top (EPOCH)", RTL),
    ("R-009", "S", "5", "epoch_tag: u16 // low bits of the epoch", "epoch_reg, cap_table", RTL),
    # ---------------------------------------------------------------- lifecycle
    ("R-010", "V", "3", "The state is monotone; in PRODUCTION, debug_grant is never asserted", "lifecycle", RTL),
    ("R-011", "V", "1", "Production silicon has no debug path", "lifecycle", RTL),
    ("R-012", "S", "2", "0 test, 1 provisioned, 2 production, 3 decommissioned (fuse-backed, monotone)", "top (LIFECYCLE)", RTL),
    ("R-013", "V", "4", "JTAG refused in PRODUCTION; attempt logged", "lifecycle (flag); firmware (log)", RTL),
    # ---------------------------------------------------------------- capability table
    ("R-014", "S", "5", "The capability table is a content-addressable memory keyed on (point, peer, dir)", "cap_table", RTL),
    ("R-015", "S", "5", "a lookup decrements budget", "cap_table", RTL),
    ("R-016", "S", "5", "refuses at zero, on expiry, or on an epoch-tag mismatch", "cap_table (zero)", RTL),
    ("R-017", "S", "5", "refuses at zero, on expiry, or on an epoch-tag mismatch", "cap_table (expiry)", RTL),
    ("R-018", "S", "5", "refuses at zero, on expiry, or on an epoch-tag mismatch", "cap_table (epoch tag)", RTL),
    ("R-019", "S", "5", "The MAC is checked at insertion, not per lookup", "cap_table", RTL),
    ("R-020", "V", "3", "budget never underflows", "cap_table", RTL),
    ("R-021", "S", "5", "dir: u2 // in, out, both", "cap_table", RTL),
    ("R-022", "S", "5", "The sizes are parameters of GovernorCore", "top", RTL),
    ("R-023", "S", "5", "instantiates the Amaranth defaults (8 entries per point, 16-bit peer, 24-bit budget, 32-bit ticket id, 8-bit command, 4 meter slots of 48 bits)", "top", RTL),
    ("R-024", "S", "5", "a port or flow is open in the switch exactly when a matching, unexpired entry exists", "top, cap_table", RTL),
    ("R-025", "S", "9", "1 cycle at the checker clock", "cap_table", RTL),
    ("R-026", "S", "5", "0 NVSwitch port, 1 PCIe switch port, 2 DPU flow, 3 storage path", "top", RTL),
    # ---------------------------------------------------------------- used-ticket store
    ("R-027", "V", "3", "A burned id is never admitted again", "ticket_store", RTL),
    ("R-028", "V", "3", "burn before admit ordering", "ticket_store", RTL),
    # ---------------------------------------------------------------- heartbeat
    ("R-029", "V", "3", "expired asserts within one millisecond tick of expiry", "heartbeat", RTL),
    ("R-030", "V", "3", "remaining reloads only on hb_valid, to the window given", "heartbeat", RTL),
    ("R-031", "S", "2", "Heartbeat time remaining, milliseconds", "top (HB_REMAIN)", RTL),
    ("R-032", "S", "9", "the RTL sequencer and heartbeat timers run on a millisecond tick derived from the microsecond counter", "top", RTL),
    ("R-033", "S", "9", "the governor clamps any signed window to it", "heartbeat (window input)", FW),
    # ---------------------------------------------------------------- safe-mode sequencer
    ("R-034", "V", "3", "The rung (state) climbs on any of loop_lost, hb_expired, tamper, cmd_halt, cmd_throttle, local_trip and on the timers", "halt", RTL),
    ("R-035", "V", "3", "never descends without clear", "halt", RTL),
    ("R-036", "V", "3", "the levers pwrbrk, perst, pwr_en follow the rung exactly", "halt", RTL),
    ("R-037", "V", "3", "switch_open starts set, clears only when armed (no cause, hb_ok)", "halt", RTL),
    ("R-038", "V", "3", "sets on loop_lost, tamper or cmd_halt", "halt", RTL),
    ("R-039", "V", "3", "and clear does not reset it", "halt", RTL),
    ("R-040", "V", "3", "cause bits 2:0 name the summary", "halt", RTL),
    ("R-041", "S", "9", "30 s / 300 s", "halt, top", RTL),
    ("R-042", "V", "4", "Mesh cut, glitch injection, temperature excursion: keys zeroized, state SAFE", "halt (tamper)", RTL),
    ("R-043", "S", "2", "0 HALTED_INITIAL, 1 RUN, 2 THROTTLE, 3 HALT, 4 SAFE", "top (STATE)", RTL),
    ("R-044", "S", "2", "bit 0 power brake asserted, bit 1 PERST# asserted, bit 2 PWR_EN low", "top (LEVERS)", RTL),
    ("R-045", "V", "3", "the core boots on the HALTED_INITIAL rung with all three levers in the safe state and the loop switch open", "top", RTL),
    ("R-046", "V", "5", "Watchdog resets the governor into HALTED_INITIAL; loop opens", "top (reset)", RTL),
    ("R-047", "S", "3", "close the loop switch if no cause remains", "halt (clear strobe)", RTL),
    # Yobie's two design calls, 23 October 2026 (docs/04 sections 2 and 3, docs/07 section 3)
    ("R-144", "S", "3", "A HALT opens the loop switch on every rung, SAFE included", "halt", RTL),
    ("R-145", "S", "3", "a HALT to a chip already in SAFE leaves it in SAFE with power off", "halt; model enter_safe_mode", RTL),
    ("R-146", "S", "2", "ALARMS bit 31 is NO_FIRST_HEARTBEAT, set by the hardware when the chip has sat in HALTED_INITIAL with no cause and no valid heartbeat for longer than the boot window", "halt, top (ALARMS, CAUSE, BOOT_WAIT)", RTL),
    ("R-147", "S", "2", "It is never set once the chip has been armed since reset", "halt, top", RTL),
    ("R-148", "S", "2", "only the sequencer raises them and firmware cannot raise them", "top, alarms (hw_mask)", RTL),
    ("R-149", "S", "3", "EXCLUDE has no effect in any state but HALTED_INITIAL with no cause", "halt", RTL),
    ("R-150", "S", "3", "the excluded chip closes its own loop switch so the rest of the rack can run, while its own levers stay asserted", "halt, top", RTL),
    ("R-151", "S", "3", "It leaves exclusion when a valid heartbeat arms it normally, on a reset, or when a HALT or a tamper moves it to a halted rung with its loop open", "halt", RTL),
    ("R-152", "S", "3", "every EXCLUDE is logged with who signed it", "model (_cmd_exclude); firmware", FW),
    # ---------------------------------------------------------------- loop
    ("R-048", "V", "3", "loop_out_open follows switch_open", "halt_loop", RTL),
    ("R-049", "V", "3", "loop_sense low for two samples drives loop_lost (debounce)", "halt_loop", RTL),
    ("R-050", "S", "2", "bit 0 loop current sensed, bit 1 own switch open", "top (LOOP)", RTL),
    # ---------------------------------------------------------------- meter
    ("R-051", "V", "3", "Counters are read-only from the host port (host_wr is refused and flagged)", "meter", RTL),
    ("R-052", "V", "3", "and only increment", "meter", RTL),
    ("R-053", "S", "2", "tokens, kernel cycles, bytes in, bytes out, per model digest slot", "top (METER_SLOT)", RTL),
    # ---------------------------------------------------------------- mailbox
    ("R-054", "S", "3", "sequence number greater than the last accepted one for that signer key", "mailbox", RTL),
    ("R-055", "S", "3", "epoch equal to EPOCH (except the epoch-exempt commands", "mailbox", RTL),
    ("R-056", "S", "3", "which move, repair or inspect the epoch itself and must work when it is stale), then the signature", "mailbox", RTL),
    ("R-057", "S", "3", "then what was signed: the signed payload names the command it is for", "mailbox", RTL),
    ("R-058", "S", "3", "The first failing check is the reason reported; the model (_check_signed) and the RTL (mailbox.py) check in the same order", "mailbox vs govsim", RTL),
    ("R-059", "S", "3", "Only then is the command dispatched.", "mailbox", RTL),
    ("R-060", "S", "2", "Last accepted inbound sequence number (key slot 0; one counter per signer key)", "top (MBOX_SEQ), mailbox", RTL),
    ("R-061", "S", "2", "0 idle, 1 busy, 2 ok, 3 bad signature, 4 bad sequence, 5 bad epoch, 6 refused", "mailbox, top (MBOX_STATUS)", RTL),
    ("R-062", "V", "3", "No command is dispatched unless frame_seq is above the key slot's last accepted sequence", "mailbox", RTL),
    ("R-063", "S", "3", "(mailbox.wrong_command, mailbox.expired; RTL status 7)", "mailbox", RTL),
    # ---------------------------------------------------------------- top
    ("R-064", "S", "2", "There is no writable register other than the doorbell.", "top", RTL),
    ("R-065", "V", "3", "No CSR write port but the doorbell", "top", RTL),
    ("R-066", "S", "2", "Silicon id and revision", "top (ID)", RTL),
    ("R-067", "S", "2", "Bits 2:0 the sequencer's own summary (0 none, 1 loop, 2 local, 3 tamper, 4 command); bit 3 waiting for the first heartbeat, boot window passed; bit 4 excluded; bits 15:8 the firmware's reason code", "top (CAUSE)", RTL),
    ("R-068", "S", "2", "firmware-mapped: the log engine is firmware over NVM, so the RTL core does not decode it", "top (LOG_HEAD)", FW_ONLY),
    # ---------------------------------------------------------------- alarms
    ("R-069", "V", "3", "Bits set by any source through set_mask", "alarms", RTL),
    ("R-070", "V", "3", "cleared only through clear_mask gated by clear_authorized", "alarms", RTL),
    ("R-071", "S", "2", "Sticky alarm bits (monotone; cleared only through the clear path)", "top (ALARMS)", RTL),
    ("R-072", "V", "1", "Alarms are monotone", "alarms", RTL),
    # ---------------------------------------------------------------- FMEA rows the hard core carries
    ("R-073", "V", "5", "Boot refused; the sequencer never leaves HALTED_INITIAL", "halt (hb_ok gate); firmware (boot)", RTL),
    ("R-074", "V", "5", "Zeroize, SAFE", "halt (tamper strobe); key manager (zeroize)", FW),
    # ---------------------------------------------------------------- firmware-owned, with an RTL strobe
    ("R-080", "S", "3", "POLICY_PROPOSE, POLICY_COMMIT, ATTEST, HALT, CLEAR, ALARM_CLEAR and EXCLUDE", "mailbox (epoch_exempt input)", FW),
    ("R-081", "S", "3", "a HALT or CLEAR also names the chip it is for and carries an expiry no more than 60 s ahead that has not passed", "mailbox (signed_cmd input)", FW),
    ("R-082", "S", "3", "Commands that carry their own authentication in the body (an attestation report, a k-of-n signed policy image) are accepted without a frame signature", "mailbox (sig_ok input)", FW),
    ("R-083", "S", "3", "Reloads the heartbeat timer", "heartbeat (hb_valid strobe)", FW),
    ("R-084", "S", "4", "heartbeat_key: key, // signs heartbeats and nothing else", "heartbeat (hb_valid strobe)", FW),
    ("R-085", "S", "3", "an authority key (never the heartbeat key)", "halt (cmd_halt, cmd_throttle strobes)", FW),
    ("R-086", "S", "3", "Clear the cause if it is in the log and a fabric neighbor has acknowledged the checkpoint that contains it", "halt (clear strobe)", FW),
    ("R-087", "S", "3", "Switch the epoch (the rack-wide rule in 02)", "epoch_reg (commit, quorum_ok)", FW),
    ("R-088", "S", "3", "Raises a sticky alarm (any party may)", "alarms (set_mask)", FW),
    ("R-089", "S", "3", "the policy's alarm approver key", "alarms (clear_authorized)", FW),
    ("R-090", "S", "3", "The peer host is accepted only on the PCIe point, never on NVSwitch, DPU or storage", "cap_table (ins, mac_ok)", FW),
    ("R-091", "S", "3", "Freezes the meter slot for that model", "meter (strobe)", FW),
    ("R-092", "S", "3", "the governor refuses a stale-epoch ticket and refuses while not in RUN", "mailbox (needs_run); firmware (ticket)", FW),
    ("R-093", "S", "5", "the governor re-derives the switch configuration from the table after any epoch, roster or heartbeat event", "cap_table (clear_all, ins)", FW),
    ("R-094", "S", "3", "extends the fingerprint with the manifest digest", "firmware (the fingerprint has no RTL register)", FW_ONLY),
    # ---------------------------------------------------------------- firmware or system only (model-owned)
    ("R-100", "S", "3", "Gate core; returns a ticket, a hold id, or a refusal", "gate (firmware)", FW_ONLY),
    ("R-101", "S", "3", "Releases a hold if the policy quorum for that rule is met", "gate (firmware)", FW_ONLY),
    ("R-102", "S", "4", "version: u32, // strictly increasing; the anti-rollback counter tracks it", "policy loader, fuses", FW_ONLY),
    ("R-103", "S", "4", "never below the fused threshold", "policy loader, fuses", FW_ONLY),
    ("R-104", "S", "4", "refuses an image in which any of them lacks a row in assumptions", "policy loader", FW_ONLY),
    ("R-105", "S", "5", "request_hash = SHA-256(canonical(request_id, fingerprint, action, params))", "gate, endpoint", FW_ONLY),
    ("R-106", "S", "7", "A firmware change changes CDI_1 and every key under it.", "key manager (IP)", FW_ONLY),
    ("R-107", "S", "9", "policy, never below 10 s", "approvals (firmware)", FW_ONLY),
    ("R-108", "S", "9", "a governor that staged an image and saw no commit stops accepting heartbeats under the staged epoch and halts as a straggler", "policy, heartbeat (firmware)", FW_ONLY),
    ("R-109", "S", "6", "prompt_hash_verified: false", "provenance record (firmware)", FW_ONLY),
    ("R-110", "S", "9", "Device-provenance signature", "crypto engine, firmware batching", FW_ONLY),
    ("R-111", "S", "8", "Update: signed by the governance root, measured at boot, gated by the anti-rollback counter.", "boot ROM, fuses", FW_ONLY),
    ("R-112", "S", "3", "Returns the governor's quote: measurements, epoch, lifecycle, counters, over the nonce", "attestation (firmware)", FW_ONLY),
    ("R-113", "S", "3", "Signed Merkle root, size, head, neighbor heads", "log engine (firmware)", FW_ONLY),
    # ---------------------------------------------------------------- the hypotheses of docs/07 section 1 (system level)
    ("R-120", "V", "1", "Within the boundary, no protected operation executes without a fresh authorization bound to that exact operation", "system (H0)", FW_ONLY),
    ("R-121", "V", "1", "Attestation binds permissions to firmware, model manifest and policy", "system (H1)", FW_ONLY),
    ("R-122", "V", "1", "Every enumerated boundary crossing passes a governed switch", "system (H2)", FW_ONLY),
    ("R-123", "V", "1", "Policy changes only with a quorum, and never backwards", "system (H3); RTL monotonic", FW_ONLY),
    ("R-124", "V", "1", "The broker cannot choose its rule or lane", "system (H4)", FW_ONLY),
    ("R-125", "V", "1", "The comparator holds with every layer above it compromised", "system (H6)", FW_ONLY),
    ("R-126", "V", "1", "The assumptions register is complete for the deployment", "system (H7)", FW_ONLY),
    ("R-127", "V", "1", "Human override is slow and fully logged", "system (H8)", FW_ONLY),
    ("R-128", "V", "1", "Permitted-channel leakage stays within the budget", "system (H10)", FW_ONLY),
    ("R-129", "V", "1", "A halt propagates to every GPU in the domain within the bound, fail-safe", "system (H11); RTL halt_loop", FW_ONLY),
    ("R-130", "V", "1", "Only roster members speak on the fabric, and only once per message", "system (H12)", FW_ONLY),
    ("R-131", "V", "1", "Shared budgets cannot be overspent across governors", "system (H13)", FW_ONLY),
    ("R-132", "V", "1", "Partitions and epoch changes end in safe states, never in stale ones", "system (H14); RTL heartbeat", FW_ONLY),
    ("R-133", "V", "1", "No governed action initiates without a ticket, and no governed response leaves the rack without a release ticket", "system (H17)", FW_ONLY),
    ("R-134", "V", "1", "Oversight survives the model", "system (H18)", FW_ONLY),
    ("R-135", "V", "1", "A signature authorizes exactly what was signed, and a policy cannot set its own quorum", "system (H19); RTL mailbox status 7", FW_ONLY),
    ("R-136", "V", "1", "The controls the rulebook names are enforced, not just stored", "system (H20)", FW_ONLY),
    ("R-137", "V", "6", "the crypto engines compute what they claim", "crypto IP (assumption)", FW_ONLY),
    # ---------------------------------------------------------------- physical claims
    ("R-140", "V", "4", "Oscilloscope on PWRBRK# across the domain; worst case over temperature and loop length", "silicon (halt bound)", SILICON),
    ("R-141", "V", "4", "PWRBRK# throttles, PERST# resets, PWR_EN cuts", "silicon (levers on a real GPU)", SILICON),
    ("R-142", "V", "5", "Governor loses power | Loop opens", "silicon (normally-open switch)", SILICON),
    ("R-143", "S", "9", "Loss of current is declared after two sense periods (debounce)", "board (sense period); RTL debounce", SILICON),
]

REQ = {r[0]: r for r in REQUIREMENTS}


def normalize(text: str) -> str:
    return " ".join(text.replace("`", "").replace("\\|", "|").split())
