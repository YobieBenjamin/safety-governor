# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The 75-attack / 12-baseline catalogue of the reference stack (hardware-and-silicon, ``hardware_ref``), mapped to
the requirement ids each row exercises and to the layer of the governor design that would decide it.

Every row of that catalogue runs against the reference SOFTWARE stack (the reference gate, its verifier, its
endpoints, its log); none of it runs against the RTL. So "decided in the catalogue by" is always the reference
gate. The column that matters here is the governor-side owner:
  hard core        an RTL block decides it (the endpoint's used-ticket store, the epoch register's quorum strobe)
  firmware         the governor's firmware decides it; any RTL involvement is a strobe
  reference gate   the reference stack's own lane (provenance, OpenShell integration) with no governor counterpart
The runner cross-checks the row names against hardware-and-silicon/results/report.json when that clone is present.
A row name is a machine key that starts with the reference-stack layer it tests: L0 (Silicon Root), L2 (Provenance),
L3 (Observers), L4 (Control Plane) or L5 (Governance Root) (LABELS.md rule on reference-stack layers).
"""
from __future__ import annotations

HC, FWL, REF = "hard core", "firmware", "reference gate"

# name -> (governor-side owner, requirement ids)
CATALOGUE: dict[str, tuple[str, tuple[str, ...]]] = {
    # baselines
    "baseline.attest": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING", "REQUIREMENT-ATTESTATION-QUOTE-CONTENTS")),
    "baseline.pay_small": (FWL, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD", "REQUIREMENT-SYSTEM-TICKETED-ACTIONS", "REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES")),
    "baseline.pay_large_hold_approve": (FWL, ("REQUIREMENT-HOLD-RELEASED-BY-QUORUM", "REQUIREMENT-SYSTEM-OVERRIDE-SLOW-LOGGED")),
    "baseline.mail_with_provenance": (REF, ("REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION",)),
    "baseline.http_auto": (FWL, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD",)),
    "baseline.audit_verifies": (FWL, ("REQUIREMENT-SIGNED-LOG-CHECKPOINT",)),
    "baseline.openshell_supervised_action": (REF, ("REQUIREMENT-SYSTEM-TICKETED-ACTIONS", "REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION")),
    "baseline.openshell_policy_derived": (REF, ("REQUIREMENT-SYSTEM-CROSSINGS-GOVERNED",)),
    "baseline.dual_witness_allow": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "baseline.high_authority_dual_witness": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES", "REQUIREMENT-HOLD-RELEASED-BY-QUORUM")),
    "baseline.hold_survives_restart": (FWL, ("REQUIREMENT-HOLD-RELEASED-BY-QUORUM",)),
    "baseline.budget_recovers_after_ticket_expiry": (FWL, ("REQUIREMENT-SYSTEM-SHARED-BUDGETS",)),
    # layer 0: silicon root and attestation
    "L0.firmware_tamper": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING", "REQUIREMENT-FIRMWARE-CHANGE-ROTATES-KEYS")),
    "L0.lying_firmware": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING", "REQUIREMENT-FIRMWARE-CHANGE-ROTATES-KEYS")),
    "L0.rollback_fused": (FWL, ("REQUIREMENT-FIRMWARE-UPDATE-GATED",)),
    "L0.rollback_unfused": (FWL, ("REQUIREMENT-FIRMWARE-UPDATE-GATED", "REQUIREMENT-SYSTEM-ATTESTATION-BINDING")),
    "L0.cloned_device": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING",)),
    "L0.revoked_device": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING", "REQUIREMENT-SYSTEM-CONTROLS-ENFORCED")),
    "L0.nonce_replay": (FWL, ("REQUIREMENT-ATTESTATION-QUOTE-CONTENTS",)),
    "L0.nonce_expired": (FWL, ("REQUIREMENT-ATTESTATION-QUOTE-CONTENTS",)),
    "L0.nonce_foreign": (FWL, ("REQUIREMENT-ATTESTATION-QUOTE-CONTENTS",)),
    "L0.gpu_swap": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING",)),
    # layer 5: governance
    "L5.reference_values_forged": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING", "REQUIREMENT-SYSTEM-POLICY-QUORUM")),
    "L5.policy_forged": (FWL, ("REQUIREMENT-SYSTEM-POLICY-QUORUM", "REQUIREMENT-RACK-WIDE-EPOCH-SWITCH", "REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM")),
    "L5.policy_default_allow": (FWL, ("REQUIREMENT-SYSTEM-POLICY-QUORUM", "REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD")),
    # layer 4: the gate
    "L4.token_missing": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING", "REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION")),
    "L4.token_forged": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING", "REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION")),
    "L4.token_expired": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING", "REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION")),
    "L4.token_wrong_workload": (FWL, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING",)),
    "L4.no_capability": (FWL, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD", "REQUIREMENT-SYSTEM-BROKER-NO-CHOICE")),
    "L4.weights_exfiltration": (FWL, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD", "REQUIREMENT-SYSTEM-CROSSINGS-GOVERNED")),
    "L4.amount_over_limit": (FWL, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD",)),
    "L4.currency_not_allowed": (FWL, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD",)),
    "L4.destination_pattern": (FWL, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD",)),
    "L4.type_confusion": (FWL, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD",)),
    "L4.url_outside_allowlist": (FWL, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD",)),
    "L4.rate_limit_burst": (FWL, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD",)),
    "L4.request_replay": (FWL, ("REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION", "REQUIREMENT-REQUEST-HASH-DEFINITION")),
    "L4.hold_bypass": (FWL, ("REQUIREMENT-HOLD-RELEASED-BY-QUORUM", "REQUIREMENT-SYSTEM-TICKETED-ACTIONS")),
    "L4.approval_forged": (FWL, ("REQUIREMENT-HOLD-RELEASED-BY-QUORUM", "REQUIREMENT-SYSTEM-SIGNATURE-EXACT")),
    "L4.approval_wrong_request": (FWL, ("REQUIREMENT-HOLD-RELEASED-BY-QUORUM", "REQUIREMENT-REQUEST-HASH-DEFINITION", "REQUIREMENT-SYSTEM-SIGNATURE-EXACT")),
    "L4.approval_replay": (FWL, ("REQUIREMENT-HOLD-RELEASED-BY-QUORUM", "REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION")),
    "L4.approval_expired": (FWL, ("REQUIREMENT-HOLD-RELEASED-BY-QUORUM",)),
    # lanes 3 and 2: observer and provenance
    "L3.observer_missing": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "L3.observer_forged": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "L3.observer_stale": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "L3.observer_subject_swap": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES", "REQUIREMENT-REQUEST-HASH-DEFINITION")),
    "L3.observer_high_risk": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "L2.provenance_missing": (REF, ("REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION",)),
    "L2.provenance_tampered": (REF, ("REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION",)),
    "L2.provenance_content_swap": (REF, ("REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION",)),
    "L2.provenance_forged": (REF, ("REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION",)),
    # endpoints
    "EP.no_ticket": (FWL, ("REQUIREMENT-SYSTEM-TICKETED-ACTIONS", "REQUIREMENT-SYSTEM-COMPARATOR-HOLDS")),
    "EP.ticket_replay": (HC, ("REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED", "REQUIREMENT-BURN-BEFORE-ADMIT", "REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION")),
    "EP.ticket_param_swap": (FWL, ("REQUIREMENT-REQUEST-HASH-DEFINITION", "REQUIREMENT-SYSTEM-COMPARATOR-HOLDS")),
    "EP.ticket_action_swap": (FWL, ("REQUIREMENT-REQUEST-HASH-DEFINITION", "REQUIREMENT-SYSTEM-COMPARATOR-HOLDS")),
    "EP.ticket_forged": (FWL, ("REQUIREMENT-SYSTEM-COMPARATOR-HOLDS", "REQUIREMENT-CRYPTO-ENGINES-CORRECT")),
    "EP.ticket_expired": (FWL, ("REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION",)),
    # audit
    "AU.modify_record": (FWL, ("REQUIREMENT-SIGNED-LOG-CHECKPOINT",)),
    "AU.delete_middle": (FWL, ("REQUIREMENT-SIGNED-LOG-CHECKPOINT",)),
    "AU.truncate_tail": (FWL, ("REQUIREMENT-SIGNED-LOG-CHECKPOINT",)),
    "AU.reorder": (FWL, ("REQUIREMENT-SIGNED-LOG-CHECKPOINT",)),
    "AU.forge_checkpoint": (FWL, ("REQUIREMENT-SIGNED-LOG-CHECKPOINT", "REQUIREMENT-CRYPTO-ENGINES-CORRECT")),
    "AU.fork_after_checkpoint": (FWL, ("REQUIREMENT-SIGNED-LOG-CHECKPOINT",)),
    "AU.inclusion_forged_leaf": (FWL, ("REQUIREMENT-SIGNED-LOG-CHECKPOINT",)),
    # NVIDIA OpenShell integration
    "NV.unrouted_passthrough_no_ticket": (REF, ("REQUIREMENT-SYSTEM-TICKETED-ACTIONS", "REQUIREMENT-SYSTEM-CROSSINGS-GOVERNED")),
    "NV.unattested_sandbox": (REF, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING",)),
    "NV.stale_host_token": (REF, ("REQUIREMENT-SYSTEM-ATTESTATION-BINDING",)),
    "NV.sentry_drift_quarantine": (REF, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "NV.sentry_identity_unverified": (REF, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "NV.repeated_denials_quarantine": (REF, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "NV.ticket_replay_across_sandboxes": (HC, ("REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED", "REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION")),
    "NV.weights_export_via_supervisor": (REF, ("REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD", "REQUIREMENT-SYSTEM-CROSSINGS-GOVERNED")),
    "NV.dual_witness_sentry_high": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "NV.dual_witness_obs_main_high": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "NV.dual_witness_second_forged": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "NV.dual_witness_second_missing": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    "NV.high_authority_single_witness": (FWL, ("REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES",)),
    # transactions, budgets, epochs
    "TX.budget_exhausted": (FWL, ("REQUIREMENT-SYSTEM-SHARED-BUDGETS",)),
    "TX.concurrent_overspend": (FWL, ("REQUIREMENT-SYSTEM-SHARED-BUDGETS",)),
    "TX.ticket_after_policy_change": (FWL, ("REQUIREMENT-TICKET-REFUSED-STALE-OR-STOPPED", "REQUIREMENT-RACK-WIDE-EPOCH-SWITCH")),
    "TX.epoch_forged": (HC, ("REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM", "REQUIREMENT-RACK-WIDE-EPOCH-SWITCH", "REQUIREMENT-SYSTEM-POLICY-QUORUM")),
    "TX.ticket_replay_after_restart": (HC, ("REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED",)),
    "TX.request_replay_after_restart": (FWL, ("REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION",)),
    "TX.commit_unreachable": (FWL, ("REQUIREMENT-SYSTEM-SHARED-BUDGETS", "REQUIREMENT-TICKET-REFUSED-STALE-OR-STOPPED")),
    "TX.risk_label_ignored": (FWL, ("REQUIREMENT-SYSTEM-BROKER-NO-CHOICE",)),
    "TX.commit_forged_ticket": (FWL, ("REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION", "REQUIREMENT-CRYPTO-ENGINES-CORRECT")),
}
