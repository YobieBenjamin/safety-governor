# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Reason codes. Strings in the model; 16-bit codes in silicon (the table at the end)."""

# attestation and identity
ATTEST_BAD_SIGNATURE = "attest.bad_signature"
ATTEST_UNKNOWN_DEVICE = "attest.unknown_device"
ATTEST_FIRMWARE_NOT_IN_REFERENCE = "attest.firmware_not_in_reference"
ATTEST_BAD_NONCE = "attest.bad_nonce"
ATTEST_EXPIRED = "attest.expired"
ATTEST_PATH_OPEN = "attest.unchecked_path_open"

# policy
POLICY_QUORUM = "policy.quorum_not_met"
POLICY_CLASS_QUORUM = "policy.class_quorum_not_met"   # F26: signatures did not span enough distinct principal classes
POLICY_ROLLBACK = "policy.rollback"
POLICY_REGISTER_INCOMPLETE = "policy.register_incomplete"
POLICY_EXPIRED = "policy.expired"
POLICY_STALE_EPOCH = "policy.stale_epoch"
POLICY_NOT_STAGED = "policy.not_staged"
POLICY_BUDGET_OWNER_MISSING = "policy.budget_owner_missing"

# mailbox
MBOX_BAD_SEQUENCE = "mailbox.bad_sequence"
MBOX_BAD_SIGNATURE = "mailbox.bad_signature"
MBOX_NOT_RUNNING = "mailbox.governor_not_running"
MBOX_UNKNOWN_COMMAND = "mailbox.unknown_command"
MBOX_WRONG_COMMAND = "mailbox.wrong_command"        # a valid signature over a different command, or for another chip
MBOX_EXPIRED = "mailbox.expired"                    # an authority command past its expiry, or with none
ATTEST_REVOKED = "attest.revoked"                    # the device is on the rulebook's revocation list
EP_SANDBOXED = "ep.sandboxed"                       # a sandboxed workload gets no peer path and no network flow

# gate
GATE_REPLAY = "gate.replay"
GATE_NOT_ATTESTED = "gate.not_attested"
GATE_NO_RULE = "gate.no_rule"
GATE_CONSTRAINT = "gate.constraint"
GATE_WITNESS_MISSING = "gate.witness_missing"
GATE_WITNESS_STALE = "gate.witness_stale"
GATE_WITNESS_RISK = "gate.witness_risk_too_high"
GATE_RATE = "gate.rate_exceeded"
GATE_BUDGET = "gate.budget_exceeded"
GATE_BUDGET_OWNER_UNREACHABLE = "gate.budget_owner_unreachable"
GATE_HELD = "gate.held_for_human"
GATE_ALARM = "gate.alarm_active"
GATE_OUTPUT_BUDGET = "gate.output_budget_exceeded"
OUTPUT_UNPRESENTED = "gate.output_unpresented"

# response release (a response leaving the rack is a governed action)
RELEASE_HAZARD = "release.hazard_class_not_allowed"
RELEASE_ILLEGIBLE = "release.below_legibility_floor"
RELEASE_ESCROW_REQUIRED = "release.escrow_receipt_required"
RELEASE_STREAM_MISSING = "release.required_stream_missing"
RELEASE_HASH_MISMATCH = "release.response_hash_mismatch"
RELEASE_COMMITMENT_CONFLICT = "release.response_commitment_conflict"
SESSION_HAZARD_BUDGET = "release.session_hazard_budget_exceeded"

# deployment and training governance
MODEL_NOT_EVALUATED = "model.not_evaluated"
COMPUTE_BUDGET = "compute.budget_exceeded"
LICENSE_INVALID = "compute.license_invalid"

# approvals and overrides
APPROVE_UNKNOWN_HOLD = "approve.unknown_hold"
APPROVE_BAD_SIGNATURE = "approve.bad_signature"
APPROVE_QUORUM_PENDING = "approve.quorum_pending"
APPROVE_TOO_FAST = "approve.below_latency_floor"
APPROVE_NO_REASON = "approve.reason_missing"

# tickets at endpoints
TICKET_BAD_SIGNATURE = "ticket.bad_signature"
TICKET_PARAMS_MISMATCH = "ticket.params_mismatch"
TICKET_ACTION_MISMATCH = "ticket.action_mismatch"
TICKET_EXPIRED = "ticket.expired"
TICKET_NOT_YET_VALID = "ticket.not_yet_valid"
TICKET_REPLAY = "ticket.replay"
TICKET_STALE_EPOCH = "ticket.stale_epoch"
TICKET_WRONG_ENDPOINT = "ticket.wrong_endpoint"
TICKET_MISSING = "ticket.missing"
COMMIT_UNREACHABLE = "commit.unreachable"
COMMIT_REJECTED = "commit.rejected"
ENDPOINT_HEARTBEAT_EXPIRED = "endpoint.heartbeat_expired"
ENDPOINT_SENSOR_CONFLICT = "endpoint.sensor_conflict"
ENDPOINT_LIST_STALE = "endpoint.list_stale"
ENDPOINT_TARGET_PROTECTED = "endpoint.target_protected"

# alarms
ALARM_CLEAR_UNAUTHORIZED = "alarm.clear_unauthorized"

# enforcement points
EP_NO_CAPABILITY = "ep.no_capability"
EP_BUDGET_EXHAUSTED = "ep.budget_exhausted"
EP_EXPIRED = "ep.capability_expired"
EP_STALE_EPOCH = "ep.stale_epoch"
EP_BRICKED = "ep.path_bricked"
EP_NOT_ON_ROSTER = "ep.peer_not_on_roster"
EP_UNCHECKED = "ep.unchecked_path"   # the recorded gap at tiers without a checker
EP_BUFFER_CLASS = "ep.buffer_class_not_permitted"   # integrated tier: the class may not leave for that peer

# fabric
FABRIC_NOT_MEMBER = "fabric.sender_not_on_roster"
FABRIC_BAD_SIGNATURE = "fabric.bad_signature"
FABRIC_REPLAY = "fabric.replay"
FABRIC_STALE_EPOCH = "fabric.stale_epoch"
FABRIC_TOO_MANY_HOPS = "fabric.too_many_hops"
FABRIC_PARTITIONED = "fabric.partitioned"
HEARTBEAT_BAD_SIGNATURE = "heartbeat.bad_signature"
HEARTBEAT_REPLAY = "heartbeat.replay"
HEARTBEAT_EXPIRED = "heartbeat.expired"
ROSTER_QUOTE_INVALID = "roster.quote_invalid"
ROSTER_NOT_MEMBER = "roster.not_member"
ROSTER_BAD_SIGNATURE = "roster.bad_signature"
CLEAR_UNAUTHORIZED = "clear.unauthorized"
CLEAR_CAUSE_NOT_LOGGED = "clear.cause_not_logged"
CLEAR_NO_NEIGHBOR_ACK = "clear.no_neighbor_ack"

# lifecycle and tamper
DEBUG_REFUSED = "lifecycle.debug_refused"
TAMPER_ZEROIZED = "tamper.zeroized"
LIFECYCLE_BACKWARDS = "lifecycle.backwards"

# levers and loop
LOOP_OPEN = "loop.open"
LOOP_BROKEN = "loop.broken"
LOOP_JUMPERED = "loop.member_jumpered"       # a member reports its switch open while the loop carries current
LOOP_MEMBER_SILENT = "loop.member_silent"    # an expected member sent no report for the beacon (logged, not an alarm)
HALT_COMMANDED = "halt.commanded"
HEARTBEAT_LOST = "halt.heartbeat_lost"
EPOCH_STRAGGLER = "halt.epoch_straggler"
TAMPER = "halt.tamper"

# boot: the first heartbeat. A chip that never gets its first heartbeat keeps
# holding the rack, loudly: the hardware raises NO_FIRST_HEARTBEAT past the boot window (ALARMS bit 31, CAUSE bit 3 in
# silicon). An authorized EXCLUDE closes its loop switch while its own levers stay on (ALARMS bit 30, CAUSE bit 4).
NO_FIRST_HEARTBEAT = "boot.no_first_heartbeat"
EXCLUDED = "boot.excluded"
EXCLUDE_NOT_WAITING = "exclude.not_waiting_for_first_heartbeat"   # EXCLUDE outside HALTED_INITIAL with no cause and no live heartbeat

# the origin gate: weights sealed to governed hardware, the key released by the governor (docs/18 question 20)
KEY_MODEL_NOT_LOADED = "key.model_not_loaded"          # KEY_RELEASE for a model no BEGIN_MODEL presented (manifest, eval gate)
KEY_MODEL_NOT_ALLOWED = "key.model_not_in_rulebook"    # the signed rulebook's sealed_models does not list it (or no longer does)
KEY_NO_GPU_KEY = "key.no_attested_gpu_key"             # the verified GPU report carried no confidential-computing key
KEY_UNWRAP_FAILED = "key.unwrap_failed"                # the data key was not sealed to this governor, or was altered
KEY_NO_LEASE = "key.no_lease"                          # KEY_RENEW for a model with no live lease on this chip
KEY_REVOKED = "key.revoked"                            # logged when a new edition drops a model with a live lease
KEY_WEIGHTS_UNBOUND = "key.weights_not_committed"      # the manifest named a model but committed to no weight bytes (F01)

# the customer-confirmation payment rule (docs/18 question 22, issue I1): a wire needs the payer's own signature
GATE_PAYER_UNCONFIRMED = "gate.payer_unconfirmed"

# the beneficiary admission rule (external audit F04): a payee must be on a current, signed beneficiary registry
GATE_BENEFICIARY_UNLISTED = "gate.beneficiary_unlisted"       # an unknown payee: a hold for enrollment, never the auto path
GATE_BENEFICIARY_NO_REGISTRY = "gate.beneficiary_no_registry"  # the signed beneficiary registry is missing or stale: fail closed

# authority that is validated at use time, not only at install (external audit F06)
POLICY_EXPIRED_RUNTIME = "halt.policy_expired"                # a running edition passed its own expiry: the declared fail-closed transition

OK = "ok"

# The 16-bit encoding the RTL and the firmware share. Codes are stable once assigned: the codes first assigned (every
# name before ADDED) keep their sorted numbering, and names added later take the next numbers in the order added.
ADDED = [NO_FIRST_HEARTBEAT, EXCLUDED, EXCLUDE_NOT_WAITING,       # 23 October 2026
         KEY_MODEL_NOT_LOADED, KEY_MODEL_NOT_ALLOWED, KEY_NO_GPU_KEY, KEY_UNWRAP_FAILED, KEY_NO_LEASE, KEY_REVOKED,   # 23 October, origin gate
         GATE_PAYER_UNCONFIRMED,   # 23 October, I1
         KEY_WEIGHTS_UNBOUND,      # 23 October, origin-gate weight-commitment binding (F01)
         GATE_BENEFICIARY_UNLISTED, GATE_BENEFICIARY_NO_REGISTRY, POLICY_EXPIRED_RUNTIME]   # 23 October, external audit F04/F06
_FIRST = sorted(v for k, v in list(globals().items()) if k.isupper() and isinstance(v, str) and v not in ADDED)
CODES = {name: i for i, name in enumerate(_FIRST + ADDED, start=1)}
