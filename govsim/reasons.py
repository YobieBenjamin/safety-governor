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
POLICY_ROLLBACK = "policy.rollback"
POLICY_REGISTER_INCOMPLETE = "policy.register_incomplete"
POLICY_EXPIRED = "policy.expired"
POLICY_STALE_EPOCH = "policy.stale_epoch"
POLICY_NOT_STAGED = "policy.not_staged"

# mailbox
MBOX_BAD_SEQUENCE = "mailbox.bad_sequence"
MBOX_BAD_SIGNATURE = "mailbox.bad_signature"
MBOX_NOT_RUNNING = "mailbox.governor_not_running"
MBOX_UNKNOWN_COMMAND = "mailbox.unknown_command"

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
HALT_COMMANDED = "halt.commanded"
HEARTBEAT_LOST = "halt.heartbeat_lost"
EPOCH_STRAGGLER = "halt.epoch_straggler"
TAMPER = "halt.tamper"

OK = "ok"

# The 16-bit encoding the RTL and the firmware share. Codes are stable once assigned.
CODES = {name: i for i, name in enumerate(sorted(v for k, v in globals().items() if k.isupper() and isinstance(v, str)), start=1)}
