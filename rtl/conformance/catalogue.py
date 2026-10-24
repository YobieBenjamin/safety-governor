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
"""
from __future__ import annotations

HC, FWL, REF = "hard core", "firmware", "reference gate"

# name -> (governor-side owner, requirement ids)
CATALOGUE: dict[str, tuple[str, tuple[str, ...]]] = {
    # baselines
    # Registered name: REQUIREMENT-SYSTEM-ATTESTATION-BINDING (old ID R-121 is kept because code matches on it)
    # Registered name: REQUIREMENT-ATTESTATION-QUOTE-CONTENTS (old ID R-112 is kept because code matches on it)
    "baseline.attest": (FWL, ("R-121", "R-112")),
    # Registered name: REQUIREMENT-GATE-RETURNS-TICKET-OR-HOLD (old ID R-100 is kept because code matches on it)
    # Registered name: REQUIREMENT-SYSTEM-TICKETED-ACTIONS (old ID R-133 is kept because code matches on it)
    # Registered name: REQUIREMENT-SYSTEM-OVERSIGHT-SURVIVES (old ID R-134 is kept because code matches on it)
    "baseline.pay_small": (FWL, ("R-100", "R-133", "R-134")),
    # Registered name: REQUIREMENT-HOLD-RELEASED-BY-QUORUM (old ID R-101 is kept because code matches on it)
    # Registered name: REQUIREMENT-SYSTEM-OVERRIDE-SLOW-LOGGED (old ID R-127 is kept because code matches on it)
    "baseline.pay_large_hold_approve": (FWL, ("R-101", "R-127")),
    # Registered name: REQUIREMENT-SYSTEM-FRESH-AUTHORIZATION (old ID R-120 is kept because code matches on it)
    "baseline.mail_with_provenance": (REF, ("R-120",)),
    "baseline.http_auto": (FWL, ("R-100",)),
    # Registered name: REQUIREMENT-SIGNED-LOG-CHECKPOINT (old ID R-113 is kept because code matches on it)
    "baseline.audit_verifies": (FWL, ("R-113",)),
    "baseline.openshell_supervised_action": (REF, ("R-133", "R-120")),
    # Registered name: REQUIREMENT-SYSTEM-CROSSINGS-GOVERNED (old ID R-122 is kept because code matches on it)
    "baseline.openshell_policy_derived": (REF, ("R-122",)),
    "baseline.dual_witness_allow": (FWL, ("R-134",)),
    "baseline.high_authority_dual_witness": (FWL, ("R-134", "R-101")),
    "baseline.hold_survives_restart": (FWL, ("R-101",)),
    # Registered name: REQUIREMENT-SYSTEM-SHARED-BUDGETS (old ID R-131 is kept because code matches on it)
    "baseline.budget_recovers_after_ticket_expiry": (FWL, ("R-131",)),
    # layer 0: silicon root and attestation
    # Registered name: REQUIREMENT-FIRMWARE-CHANGE-ROTATES-KEYS (old ID R-106 is kept because code matches on it)
    "L0.firmware_tamper": (FWL, ("R-121", "R-106")),
    "L0.lying_firmware": (FWL, ("R-121", "R-106")),
    # Registered name: REQUIREMENT-FIRMWARE-UPDATE-GATED (old ID R-111 is kept because code matches on it)
    "L0.rollback_fused": (FWL, ("R-111",)),
    "L0.rollback_unfused": (FWL, ("R-111", "R-121")),
    "L0.cloned_device": (FWL, ("R-121",)),
    # Registered name: REQUIREMENT-SYSTEM-CONTROLS-ENFORCED (old ID R-136 is kept because code matches on it)
    "L0.revoked_device": (FWL, ("R-121", "R-136")),
    "L0.nonce_replay": (FWL, ("R-112",)),
    "L0.nonce_expired": (FWL, ("R-112",)),
    "L0.nonce_foreign": (FWL, ("R-112",)),
    "L0.gpu_swap": (FWL, ("R-121",)),
    # layer 5: governance
    # Registered name: REQUIREMENT-SYSTEM-POLICY-QUORUM (old ID R-123 is kept because code matches on it)
    "L5.reference_values_forged": (FWL, ("R-121", "R-123")),
    # Registered name: REQUIREMENT-RACK-WIDE-EPOCH-SWITCH (old ID R-087 is kept because code matches on it)
    # Registered name: REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM (old ID R-007 is kept because code matches on it)
    "L5.policy_forged": (FWL, ("R-123", "R-087", "R-007")),
    "L5.policy_default_allow": (FWL, ("R-123", "R-100")),
    # layer 4: the gate
    "L4.token_missing": (FWL, ("R-121", "R-120")),
    "L4.token_forged": (FWL, ("R-121", "R-120")),
    "L4.token_expired": (FWL, ("R-121", "R-120")),
    "L4.token_wrong_workload": (FWL, ("R-121",)),
    # Registered name: REQUIREMENT-SYSTEM-BROKER-NO-CHOICE (old ID R-124 is kept because code matches on it)
    "L4.no_capability": (FWL, ("R-100", "R-124")),
    "L4.weights_exfiltration": (FWL, ("R-100", "R-122")),
    "L4.amount_over_limit": (FWL, ("R-100",)),
    "L4.currency_not_allowed": (FWL, ("R-100",)),
    "L4.destination_pattern": (FWL, ("R-100",)),
    "L4.type_confusion": (FWL, ("R-100",)),
    "L4.url_outside_allowlist": (FWL, ("R-100",)),
    "L4.rate_limit_burst": (FWL, ("R-100",)),
    # Registered name: REQUIREMENT-REQUEST-HASH-DEFINITION (old ID R-105 is kept because code matches on it)
    "L4.request_replay": (FWL, ("R-120", "R-105")),
    "L4.hold_bypass": (FWL, ("R-101", "R-133")),
    # Registered name: REQUIREMENT-SYSTEM-SIGNATURE-EXACT (old ID R-135 is kept because code matches on it)
    "L4.approval_forged": (FWL, ("R-101", "R-135")),
    "L4.approval_wrong_request": (FWL, ("R-101", "R-105", "R-135")),
    "L4.approval_replay": (FWL, ("R-101", "R-120")),
    "L4.approval_expired": (FWL, ("R-101",)),
    # lanes 3 and 2: observer and provenance
    "L3.observer_missing": (FWL, ("R-134",)),
    "L3.observer_forged": (FWL, ("R-134",)),
    "L3.observer_stale": (FWL, ("R-134",)),
    "L3.observer_subject_swap": (FWL, ("R-134", "R-105")),
    "L3.observer_high_risk": (FWL, ("R-134",)),
    "L2.provenance_missing": (REF, ("R-120",)),
    "L2.provenance_tampered": (REF, ("R-120",)),
    "L2.provenance_content_swap": (REF, ("R-120",)),
    "L2.provenance_forged": (REF, ("R-120",)),
    # endpoints
    # Registered name: REQUIREMENT-SYSTEM-COMPARATOR-HOLDS (old ID R-125 is kept because code matches on it)
    "EP.no_ticket": (FWL, ("R-133", "R-125")),
    # Registered name: REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED (old ID R-027 is kept because code matches on it)
    # Registered name: REQUIREMENT-BURN-BEFORE-ADMIT (old ID R-028 is kept because code matches on it)
    "EP.ticket_replay": (HC, ("R-027", "R-028", "R-120")),
    "EP.ticket_param_swap": (FWL, ("R-105", "R-125")),
    "EP.ticket_action_swap": (FWL, ("R-105", "R-125")),
    # Registered name: REQUIREMENT-CRYPTO-ENGINES-CORRECT (old ID R-137 is kept because code matches on it)
    "EP.ticket_forged": (FWL, ("R-125", "R-137")),
    "EP.ticket_expired": (FWL, ("R-120",)),
    # audit
    "AU.modify_record": (FWL, ("R-113",)),
    "AU.delete_middle": (FWL, ("R-113",)),
    "AU.truncate_tail": (FWL, ("R-113",)),
    "AU.reorder": (FWL, ("R-113",)),
    "AU.forge_checkpoint": (FWL, ("R-113", "R-137")),
    "AU.fork_after_checkpoint": (FWL, ("R-113",)),
    "AU.inclusion_forged_leaf": (FWL, ("R-113",)),
    # NVIDIA OpenShell integration
    "NV.unrouted_passthrough_no_ticket": (REF, ("R-133", "R-122")),
    "NV.unattested_sandbox": (REF, ("R-121",)),
    "NV.stale_host_token": (REF, ("R-121",)),
    "NV.sentry_drift_quarantine": (REF, ("R-134",)),
    "NV.sentry_identity_unverified": (REF, ("R-134",)),
    "NV.repeated_denials_quarantine": (REF, ("R-134",)),
    "NV.ticket_replay_across_sandboxes": (HC, ("R-027", "R-120")),
    "NV.weights_export_via_supervisor": (REF, ("R-100", "R-122")),
    "NV.dual_witness_sentry_high": (FWL, ("R-134",)),
    "NV.dual_witness_obs_main_high": (FWL, ("R-134",)),
    "NV.dual_witness_second_forged": (FWL, ("R-134",)),
    "NV.dual_witness_second_missing": (FWL, ("R-134",)),
    "NV.high_authority_single_witness": (FWL, ("R-134",)),
    # transactions, budgets, epochs
    "TX.budget_exhausted": (FWL, ("R-131",)),
    "TX.concurrent_overspend": (FWL, ("R-131",)),
    # Registered name: REQUIREMENT-TICKET-REFUSED-STALE-OR-STOPPED (old ID R-092 is kept because code matches on it)
    "TX.ticket_after_policy_change": (FWL, ("R-092", "R-087")),
    "TX.epoch_forged": (HC, ("R-007", "R-087", "R-123")),
    "TX.ticket_replay_after_restart": (HC, ("R-027",)),
    "TX.request_replay_after_restart": (FWL, ("R-120",)),
    "TX.commit_unreachable": (FWL, ("R-131", "R-092")),
    "TX.risk_label_ignored": (FWL, ("R-124",)),
    "TX.commit_forged_ticket": (FWL, ("R-120", "R-137")),
}
