"""The policy image: rules, keys, reference values, the assumptions register, k-of-n
signatures and the epoch. ``docs/04-specification.md`` §4.

A rule's constraints may reference *inputs* (a list id, a registry, a sensor source). The
image carries an assumptions register with one row per input; ``check_register`` returns the
inputs that have no row, and a governor refuses to load an image where that set is not empty
(requirement H7).
"""
from __future__ import annotations

import copy
from typing import Any, Iterable

from . import reasons
from .crypto import SigningKey, VerifyKey, digest, verify_object


def make_rule(rule_id: str, action: str, *, measurement: str = "*", constraints: dict | None = None,
              mode: str = "auto", observers: list[str] | None = None, max_risk: float = 1.0,
              approvers_quorum: int = 0, rate: dict | None = None, budget: dict | None = None,
              endpoint: str | None = None, delay_s: float = 0.0, inputs: list[str] | None = None,
              output_budget: dict | None = None) -> dict:
    return {
        "id": rule_id, "measurement": measurement, "action": action,
        "constraints": constraints or {},
        "requirement": {"mode": mode, "observers": observers or [], "max_risk": max_risk, "approvers_quorum": approvers_quorum},
        "rate": rate, "budget": budget, "endpoint": endpoint, "delay_s": delay_s,
        "inputs": inputs or [],              # the register rows this rule relies on
        "output_budget": output_budget,      # {"queries": n, "bytes": n, "window_s": s}
    }


def make_register_row(input_name: str, authority: str, freshness: str, on_conflict: str, independence: str, unchecked: str) -> dict:
    return {"input": input_name, "authority": authority, "freshness": freshness,
            "on_conflict": on_conflict, "independence": independence, "unchecked": unchecked}


def make_policy(*, version: int, issued_at: float, expires_at: float, governance_keys: list[VerifyKey],
                threshold: int, approver_keys: dict[str, list[VerifyKey]], heartbeat_key: VerifyKey,
                publisher_keys: list[VerifyKey], reference_values: list[dict], endpoints: list[dict],
                budget_owners: dict[str, str], rules: list[dict], assumptions: list[dict],
                safe_mode: dict | None = None, fabric: dict | None = None, observer_keys: list[VerifyKey] | None = None,
                revocations: list[str] | None = None, override_floor_s: float = 60.0) -> dict:
    return {
        "version": version, "issued_at": issued_at, "expires_at": expires_at,
        "governance_keys": [k.hex for k in governance_keys], "threshold": threshold,
        "approver_keys": {rid: [k.hex for k in ks] for rid, ks in approver_keys.items()},
        "heartbeat_key": heartbeat_key.hex,
        "publisher_keys": [k.hex for k in publisher_keys],
        "observer_keys": [k.hex for k in (observer_keys or [])],
        "reference_values": reference_values,      # [{device_class, firmware_digest, valid_until, vendor_key}]
        "revocations": revocations or [],
        "endpoints": endpoints,                    # [{name, pubkey, safe_transition}]
        "budget_owners": budget_owners,            # budget key -> governor chip id
        "rules": rules,
        "assumptions": assumptions,
        "override_floor_s": override_floor_s,
        "safe_mode": safe_mode or {"default_rung": "THROTTLE", "T_throttle_s": 30.0, "T_halt_s": 300.0,
                                   "causes": {reasons.LOOP_OPEN: "HALT", reasons.LOOP_BROKEN: "HALT",
                                              reasons.TAMPER: "SAFE", reasons.HEARTBEAT_LOST: "THROTTLE",
                                              reasons.EPOCH_STRAGGLER: "HALT", reasons.HALT_COMMANDED: "HALT"}},
        "fabric": fabric or {"heartbeat_period_s": 1.0, "heartbeat_expiry_s": 5.0, "max_hops": 16,
                             "epoch_deadline_s": 10.0, "loop_bound_s": 0.001},
    }


def policy_epoch(image: dict) -> str:
    body = {k: v for k, v in image.items() if k != "signatures"}
    return digest(body)


def sign_policy(image: dict, keys: Iterable[SigningKey]) -> dict:
    image = copy.deepcopy(image)
    body = {k: v for k, v in image.items() if k != "signatures"}
    image["signatures"] = [k.sign({"type": "policy", "epoch": digest(body)}) for k in keys]
    return image


def verify_policy(image: dict, governance_hashes: list[str] | None = None) -> tuple[bool, str]:
    """k-of-n check. Governance keys are taken from the image but must match the fused hashes."""
    try:
        keys = [VerifyKey.from_hex(h) for h in image["governance_keys"]]
        threshold = int(image["threshold"])
        if governance_hashes is not None:
            for k in keys:
                if digest(k.hex) not in governance_hashes:
                    return False, reasons.POLICY_QUORUM
        body = {k: v for k, v in image.items() if k != "signatures"}
        epoch = digest(body)
        good: set[str] = set()
        for sig in image.get("signatures", []):
            for k in keys:
                if sig.get("signer") == k.key_id and verify_object(sig, k) and sig["payload"].get("epoch") == epoch:
                    good.add(k.key_id)
        if len(good) < threshold:
            return False, reasons.POLICY_QUORUM
        return True, reasons.OK
    except (KeyError, TypeError, ValueError):
        return False, reasons.POLICY_QUORUM


def check_register(image: dict) -> list[str]:
    """Inputs named by rules that have no assumptions-register row."""
    rows = {r["input"] for r in image.get("assumptions", [])}
    missing: list[str] = []
    for rule in image.get("rules", []):
        for inp in rule.get("inputs", []):
            if inp not in rows and inp not in missing:
                missing.append(inp)
    # endpoints rely on inputs too
    for ep in image.get("endpoints", []):
        for inp in ep.get("inputs", []):
            if inp not in rows and inp not in missing:
                missing.append(inp)
    return missing


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
        if "min" in c and v < c["min"]:
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.below_min"
        if "max" in c and v > c["max"]:
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.above_max"
        if "in" in c and v not in c["in"]:
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.not_allowed"
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
