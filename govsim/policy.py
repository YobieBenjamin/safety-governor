# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The policy image: rules, keys, reference values, the assumptions register, k-of-n
signatures and the epoch. ``docs/04-specification.md`` section 4.

A rule relies on *inputs*: the lists its constraints name, the observer verdict its lane needs,
the budget key it spends from, and anything it declares. ``check_register`` derives that set and
returns the inputs with no assumptions-register row; ``check_budget_owners`` returns budget keys
with no owner. A governor refuses an image where either set is not empty (H7, R12).
"""
from __future__ import annotations

import copy
from typing import Any, Iterable

from . import reasons
from .crypto import SigningKey, VerifyKey, canonical, digest, finite_number, verify_object

# Buffer classes at the integrated tier, and where each class may go through the copy engines
# and the peer MMU. Scopes: "none" (never leaves the GPU), "roster" (roster peers only), "host"
# (the verified host only), "any-roster-or-host". A class with no entry, or an unknown scope,
# gets no capability at all: fail closed.
BUFFER_CLASSES = ["weights", "kv_cache", "activations", "outputs"]
BUFFER_POLICY = {"weights": "none", "kv_cache": "roster", "activations": "roster", "outputs": "host"}
BUFFER_SCOPES = ("none", "roster", "host", "any-roster-or-host")

# Audit: the share of responses the chip's TRNG picks for review, the verdict classes that are
# always escrowed, and the endpoint whose signed receipt releases an escrowed response.
AUDIT = {"sample_rate": 0.05, "escrow_classes": ["hazard"], "store": "audit-store"}
RELEASE_ACTION = "response.release"


def buffer_allowed(buffer_policy: dict, buffer_class: str, peer: str) -> bool:
    """May ``buffer_class`` leave for ``peer`` ("host" or a roster peer) under this buffer policy?"""
    scope = buffer_policy.get(buffer_class, "none")
    if peer == "host":
        return scope in ("host", "any-roster-or-host")
    return scope in ("roster", "any-roster-or-host")


def make_rule(rule_id: str, action: str, *, measurement: str = "*", constraints: dict | None = None,
              mode: str = "auto", observers: list[str] | None = None, max_risk: float = 1.0,
              approvers_quorum: int = 0, rate: dict | None = None, budget: dict | None = None,
              endpoint: str | None = None, delay_s: float = 0.0, inputs: list[str] | None = None,
              output_budget: dict | None = None, allowed_hazard_classes: list[str] | None = None,
              min_legibility: float = 0.0, on_hazard: str = "refuse", on_illegible: str = "refuse",
              hazard_budget: dict | None = None, streams_required: list[str] | None = None,
              payer_confirm: dict | None = None, beneficiary: dict | None = None) -> dict:
    return {
        "id": rule_id, "measurement": measurement, "action": action,
        "constraints": constraints or {},
        "requirement": {"mode": mode, "observers": observers or [], "max_risk": max_risk, "approvers_quorum": approvers_quorum,
                        # response.release only: which verdict classes may leave, the legibility floor, and
                        # whether a failing verdict is refused or parked for the human lane
                        "allowed_hazard_classes": list(allowed_hazard_classes if allowed_hazard_classes is not None else ["none"]),
                        "min_legibility": min_legibility, "on_hazard": on_hazard, "on_illegible": on_illegible},
        "rate": rate, "budget": budget, "endpoint": endpoint, "delay_s": delay_s,
        "payer_confirm": payer_confirm,   # I1: {"registry": <list id>, "account_param": <param naming the paying account>}
        "beneficiary": beneficiary,       # F04: {"registry": <list id>, "param": <param naming the payee>}; a payee not on the current signed registry is a hold
        "inputs": inputs or [],              # the register rows this rule relies on
        "output_budget": output_budget,      # {"queries": n, "bytes": n, "window_s": s}
        "hazard_budget": hazard_budget,      # response.release only: {"max": n, "window_s": s} hazard verdicts per session
        "streams_required": streams_required,   # response.release only; None: the image's streams_required
    }


def make_register_row(input_name: str, authority: str, freshness: str, on_conflict: str, independence: str, unchecked: str) -> dict:
    return {"input": input_name, "authority": authority, "freshness": freshness,
            "on_conflict": on_conflict, "independence": independence, "unchecked": unchecked}


def make_policy(*, version: int, issued_at: float, expires_at: float, governance_keys: list[VerifyKey],
                threshold: int, approver_keys: dict[str, list[VerifyKey]], heartbeat_key: VerifyKey,
                publisher_keys: list[VerifyKey], reference_values: list[dict], endpoints: list[dict],
                budget_owners: dict[str, str], rules: list[dict], assumptions: list[dict],
                safe_mode: dict | None = None, fabric: dict | None = None, observer_keys: list[VerifyKey] | None = None,
                revocations: list[str] | None = None, override_floor_s: float = 60.0,
                buffer_classes: list[str] | None = None, buffer_policy: dict[str, str] | None = None,
                audit: dict | None = None, streams_required: list[str] | None = None,
                eval_keys: list[VerifyKey] | None = None, deployment_gate: bool = False,
                compute_budget: dict | None = None, sandbox: bool = False, authority_keys: list[VerifyKey] | None = None,
                sealed_models: list[str] | None = None, key_lease_s: float = 60.0,
                governance_classes: dict[str, str] | None = None, governance_class_quorum: int = 0) -> dict:
    return {
        "version": version, "issued_at": issued_at, "expires_at": expires_at,
        "governance_keys": [k.hex for k in governance_keys], "threshold": threshold,
        # F26: optional quorum across enrolled principal CLASSES. governance_classes maps a governance key's
        # hex to the class (the organisation or role) that holds it; governance_class_quorum is how many
        # DISTINCT classes the signers of a change must span. 0 means the check is off and behaviour is the
        # bare key count as before. When on, several keys of ONE class no longer suffice: counting keys is not
        # independence.
        "governance_classes": dict(governance_classes or {}),
        "governance_class_quorum": int(governance_class_quorum),
        "approver_keys": {rid: [k.hex for k in ks] for rid, ks in approver_keys.items()},
        "heartbeat_key": heartbeat_key.hex,
        "authority_keys": [k.hex for k in (authority_keys or [])],          # HALT and CLEAR; a different key from the heartbeat's, so a key that only says "alive" can never say "stop" or "go"
        "publisher_keys": [k.hex for k in publisher_keys],
        "observer_keys": [k.hex for k in (observer_keys or [])],
        "reference_values": reference_values,      # [{device_class, firmware_digest, valid_until, vendor_key}]
        "revocations": revocations or [],
        "endpoints": endpoints,                    # [{name, pubkey, safe_transition}]
        "budget_owners": budget_owners,            # budget key -> governor chip id
        "rules": rules,
        "assumptions": assumptions,
        "override_floor_s": override_floor_s,
        "buffer_classes": list(buffer_classes if buffer_classes is not None else BUFFER_CLASSES),
        "buffer_policy": dict(buffer_policy if buffer_policy is not None else BUFFER_POLICY),   # the default for every workload without a rule of its own
        "audit": dict(audit if audit is not None else AUDIT),              # unpredictable sampling and escrow before release
        "streams_required": list(streams_required if streams_required is not None else ["response"]),   # per workload default
        "eval_keys": [k.hex for k in (eval_keys or [])],                   # who may attest that a model was evaluated
        "deployment_gate": bool(deployment_gate),                          # BEGIN_MODEL needs an eval attestation
        "compute_budget": dict(compute_budget if compute_budget is not None else {"cycles": None, "license_keys": []}),
        "sandbox": bool(sandbox),                                          # model organisms: no network flows
        "sealed_models": list(sealed_models or []),                        # the origin gate: models whose key this chip may release
        "key_lease_s": float(key_lease_s),                                 # a released key lives this long unless renewed
        "safe_mode": safe_mode or {"default_rung": "THROTTLE", "T_throttle_s": 30.0, "T_halt_s": 300.0,
                                   "causes": {reasons.LOOP_OPEN: "HALT", reasons.LOOP_BROKEN: "HALT", reasons.LOOP_JUMPERED: "HALT",
                                              reasons.TAMPER: "SAFE", reasons.HEARTBEAT_LOST: "THROTTLE",
                                              reasons.EPOCH_STRAGGLER: "HALT", reasons.HALT_COMMANDED: "HALT"}},
        "fabric": fabric or {"heartbeat_expiry_s": 5.0, "max_hops": 16, "epoch_deadline_s": 10.0, "loop_bound_s": 0.001},
    }


def policy_epoch(image: dict) -> str:
    body = {k: v for k, v in image.items() if k != "signatures"}
    return digest(body)


def sign_policy(image: dict, keys: Iterable[SigningKey]) -> dict:
    image = copy.deepcopy(image)
    body = {k: v for k, v in image.items() if k != "signatures"}
    image["signatures"] = [k.sign({"type": "policy", "epoch": digest(body)}) for k in keys]
    return image


def verify_policy(image: dict, governance_hashes: list[str] | None = None, min_threshold: int | None = None,
                  trusted: dict | None = None) -> tuple[bool, str]:
    """Is this rulebook authorized? The answer comes from trusted state, never from the image.

    ``trusted`` is the governance configuration in force (the keys whose signatures count and the k
    they must reach, from the chip's protected record). When it is set, the image needs k distinct
    valid signatures from THOSE keys over its body, whatever keys and threshold the image itself
    names: the configuration in force authorizes its replacement, so the same quorum can rotate keys
    and change k. When it is not set (the very first rulebook on a new chip), the image's keys must
    match the key hashes fused at manufacture and k is the larger of the image's and the fused floor.

    Either way the image's own threshold must be at least one, at most the number of its distinct
    keys, and not below ``min_threshold`` (the manufacture floor), because it becomes the k that
    authorizes the NEXT change. Each key counts once however often it signed or is listed.
    (Until 22 October 2026 k was read from the image being checked, so threshold 0 with no
    signatures passed; an external audit reproduced it.)"""
    try:
        own_keys = list({h: VerifyKey.from_hex(h) for h in image["governance_keys"]}.values())
        threshold = int(image["threshold"])
        floor = int(min_threshold) if min_threshold is not None else 1
        if threshold < max(1, floor) or threshold > len(own_keys):
            return False, reasons.POLICY_QUORUM
        if trusted is not None:
            signers = list({h: VerifyKey.from_hex(h) for h in trusted["keys"]}.values())
            required = int(trusted["threshold"])
        else:
            if governance_hashes is not None and any(digest(k.hex) not in governance_hashes for k in own_keys):
                return False, reasons.POLICY_QUORUM
            signers, required = own_keys, max(threshold, floor)
        if required < max(1, floor):
            return False, reasons.POLICY_QUORUM
        body = {k: v for k, v in image.items() if k != "signatures"}
        epoch = digest(body)
        good: set[str] = set()
        for sig in image.get("signatures", []):
            for k in signers:
                if sig.get("signer") == k.key_id and verify_object(sig, k) and sig["payload"].get("epoch") == epoch:
                    good.add(k.key_id)
        if len(good) < required:
            return False, reasons.POLICY_QUORUM
        # F26: optional quorum across enrolled principal classes. The requirement in force governs this change,
        # so it comes from the trusted record when there is one (the image cannot relax its own class rule, the
        # same discipline as the threshold), and from the image only on the first rulebook. When on, the valid
        # signers must span at least that many DISTINCT classes: several keys of one class are one class, so an
        # org holding three of five keys cannot sign a change alone. Off by default (quorum 0): behaviour is the
        # bare key count as before.
        src = trusted if trusted is not None else image
        class_quorum = int(src.get("governance_class_quorum") or 0)
        if class_quorum > 0:
            class_of = {VerifyKey.from_hex(h).key_id: cls for h, cls in (src.get("governance_classes") or {}).items()}
            classes_present = {class_of[kid] for kid in good if kid in class_of}
            if len(classes_present) < class_quorum:
                return False, reasons.POLICY_CLASS_QUORUM
        return True, reasons.OK
    except (KeyError, TypeError, ValueError):
        return False, reasons.POLICY_QUORUM


LIST_CONSTRAINTS = ("not_in_list", "in_list", "digest_of")
OBSERVER_INPUT = "observer-verdict"


def rule_inputs(rule: dict) -> list[str]:
    """Every input a rule relies on, derived from what it does, plus anything it declares."""
    inputs = list(rule.get("inputs", []))
    for c in rule.get("constraints", {}).values():
        for k in LIST_CONSTRAINTS:
            if k in c:
                inputs.append(c[k])
    req = rule.get("requirement", {})
    if req.get("observers") or req.get("mode") == "observer":
        inputs.append(OBSERVER_INPUT)
    if rule.get("budget"):
        inputs.append(rule["budget"]["key"])
    return list(dict.fromkeys(inputs))


def check_register(image: dict) -> list[str]:
    """Inputs the rules or endpoints rely on that have no assumptions-register row."""
    rows = {r["input"] for r in image.get("assumptions", [])}
    needed: list[str] = []
    for rule in image.get("rules", []):
        needed += rule_inputs(rule)
    for ep in image.get("endpoints", []):
        needed += ep.get("inputs", [])
    return [inp for inp in dict.fromkeys(needed) if inp not in rows]


def check_budget_owners(image: dict) -> list[str]:
    """Budget keys the rules use that no governor owns. There is no default owner."""
    owners = image.get("budget_owners", {})
    keys = [r["budget"]["key"] for r in image.get("rules", []) if r.get("budget")]
    if any(r.get("hazard_budget") for r in image.get("rules", [])):
        keys.append("hazard")       # a session's hazard budget is one budget, counted at one owner, like any other shared budget
    return [k for k in dict.fromkeys(keys) if k not in owners]


def find_rule(image: dict, measurement: str, action: str) -> dict | None:
    """The first rule for this measurement and action (exact measurement before wildcard)."""
    exact = [r for r in image["rules"] if r["action"] == action and r["measurement"] == measurement]
    if exact:
        return exact[0]
    anyv = [r for r in image["rules"] if r["action"] == action and r["measurement"] == "*"]
    return anyv[0] if anyv else None


def select_rule(image: dict, measurement: str, action: str, params: dict, lists: dict[str, Any]) -> tuple[dict | None, str]:
    """The rulebook selects the rule from the verified measurement, the action and the typed
    fields, and from nothing else. Several rules may share an action (a small-payment rule
    and a large-payment rule); the first whose constraints the fields satisfy wins. Requester
    labels never reach this function (H4)."""
    candidates = [r for r in image["rules"] if r["action"] == action and r["measurement"] == measurement]
    candidates += [r for r in image["rules"] if r["action"] == action and r["measurement"] == "*"]
    if not candidates:
        return None, reasons.GATE_NO_RULE
    last = reasons.GATE_NO_RULE
    for rule in candidates:
        ok, why = check_constraints(rule, params, lists)
        if ok:
            return rule, reasons.OK
        last = why
    return None, last


def check_constraints(rule: dict, params: dict, lists: dict[str, Any]) -> tuple[bool, str]:
    """Typed limits. ``lists`` are the signed lists the governor holds (by list id)."""
    for name, c in rule["constraints"].items():
        if name not in params:
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.missing"
        v = params[name]
        if ("min" in c or "max" in c) and not finite_number(v):   # NaN/inf/bool pass every < / > test otherwise (F03)
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.not_a_finite_number"
        if "min" in c and v < c["min"]:
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.below_min"
        if "max" in c and v > c["max"]:
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.above_max"
        if "in" in c and v not in c["in"]:
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.not_allowed"
        if "max_bytes" in c:
            # F12: a byte ceiling on a free-form parameter (a message body, a payload). The externally
            # observable size is the canonical serialization, the same bytes that would be signed and
            # that leave through the channel. Without this a listed-recipient message.send carries an
            # arbitrary body, so the permitted channel has no finite byte ceiling.
            try:
                n = len(canonical(v))
            except (TypeError, ValueError):
                return False, f"{reasons.GATE_CONSTRAINT}.{name}.not_serializable"
            if n > c["max_bytes"]:
                return False, f"{reasons.GATE_CONSTRAINT}.{name}.above_max_bytes"
        if "not_in_list" in c:
            lst = lists.get(c["not_in_list"])
            if lst is None or lst.get("stale"):
                return False, f"{reasons.GATE_CONSTRAINT}.{name}.list_unavailable"
            if v in lst["entries"]:
                return False, f"{reasons.GATE_CONSTRAINT}.{name}.in_denied_list"
        if "in_list" in c:
            lst = lists.get(c["in_list"])
            if lst is None or lst.get("stale"):
                return False, f"{reasons.GATE_CONSTRAINT}.{name}.list_unavailable"
            if v not in lst["entries"]:
                return False, f"{reasons.GATE_CONSTRAINT}.{name}.not_in_allowed_list"
    return True, reasons.OK
