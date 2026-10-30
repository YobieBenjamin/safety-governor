# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The policy image: the signed rulebook that a governor enforces. ``docs/04-specification.md`` section 4.

What a policy image holds: the governance keys and the threshold k (how many of them must sign a change);
the keys that may sign each role (authority, heartbeat, publisher, observer, approver, eval, license); the
reference values (the firmware digests and vendor keys a chip must match); the rules (for each action, a
mode, the typed limits, a budget, an endpoint); the assumptions register (one row for each input the rules
rely on); the endpoints; the budget owners; and the safe-mode and fabric timers.

What this file does: it builds images (``make_rule``, ``make_register_row``, ``make_policy``), signs them
(``sign_policy``), gives each one an epoch (``policy_epoch``, a digest of its body), checks signatures and
quorum (``verify_policy``), and picks the rule for a request (``select_rule``, ``find_rule``,
``check_constraints``).

Rules and the register: a rule relies on inputs. They are the lists its constraints name, the observer
verdict its lane needs, and the budget key it spends from, plus anything it declares. ``check_register``
returns the inputs that have no register row. ``check_budget_owners`` returns the budget keys that have no
owner. A governor refuses an image where either list is not empty (CONTRACT-ASSUMPTIONS-REGISTER-COMPLETE, REQUIREMENT-ONE-LEDGER-OWNS-BUDGET; tests/test_contract_assumptions_register_complete.py).

What it guarantees: a governor accepts an image only when at least k distinct valid signatures from the keys
in force cover the image's epoch, the threshold is in range, and the register and budget owners are
complete. Rule selection uses only the verified measurement, the action and the typed fields. Requester
labels never reach it (CONTRACT-BROKER-CANNOT-PICK-RULE).

What it deliberately does NOT do: it does not judge whether a rule is wise. It does not choose the signers,
because the governance root does that. It does not reach the network. The default buffer policy and audit
settings are starting values, and an image may replace them.
"""
from __future__ import annotations

import copy
from typing import Any, Iterable

from . import reasons
from . import definitions as D
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
    """Build one rule. ``action`` is the action it covers. ``measurement`` is the workload it applies to, where ``*``
    means any workload. ``constraints`` are the typed limits a request must meet. ``mode`` sets how a passing request
    is handled: ``auto`` issues a ticket at once; ``observer`` needs an observer verdict whose risk is at or below
    ``max_risk``; ``human`` parks the request until ``approvers_quorum`` approvers sign. The other fields set the rate
    limit, the budget, the endpoint, the release checks, and the payer and beneficiary checks. Output: a dict."""
    return {
        "id": rule_id, "measurement": measurement, "action": action,
        "constraints": constraints or {},
        "requirement": {"mode": mode, "observers": observers or [], "max_risk": max_risk, "approvers_quorum": approvers_quorum,
                        # response.release only: which verdict classes may leave, the legibility floor, and
                        # whether a failing verdict is refused or parked for the human lane
                        "allowed_hazard_classes": list(allowed_hazard_classes if allowed_hazard_classes is not None else ["none"]),
                        "min_legibility": min_legibility, "on_hazard": on_hazard, "on_illegible": on_illegible},
        "rate": rate, "budget": budget, "endpoint": endpoint, "delay_s": delay_s,
        "payer_confirm": payer_confirm,   # EXPERIMENT-CUSTOMER-CONFIRMATION: {"registry": <list id>, "account_param": <param naming the paying account>}
        "beneficiary": beneficiary,       # F04: {"registry": <list id>, "param": <param naming the payee>}; a payee not on the current signed registry is a hold
        "inputs": inputs or [],              # the register rows this rule relies on
        "output_budget": output_budget,      # {"queries": n, "bytes": n, "window_s": s}
        "hazard_budget": hazard_budget,      # response.release only: {"max": n, "window_s": s} hazard verdicts per session
        "streams_required": streams_required,   # response.release only; None: the image's streams_required
    }


def make_register_row(input_name: str, authority: str, freshness: str, on_conflict: str, independence: str, unchecked: str) -> dict:
    """Build one row of the assumptions register: the input, who vouches for it (``authority``), how fresh it must
    be, what a conflict does (``on_conflict``), why it is independent of what it checks, and what is not checked.
    The row is a written reason. The governor checks that every input a rule uses has one."""
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
                governance_classes: dict[str, str] | None = None, governance_class_quorum: int = 0,
                heartbeat_cosigners: list[VerifyKey] | None = None, heartbeat_threshold: int = 1,
                authority_threshold: int = 1, list_threshold: int = 1, site: str | None = None,
                fleet_ledger: dict | None = None) -> dict:
    """Assemble an unsigned policy image from its parts. The keyword arguments set the defaults for the timers, the
    buffer policy, the audit sampling and the escrow classes. The result is a dict with a version, an expiry, the keys,
    the rules and the register. It is not in force until it is signed with ``sign_policy`` and a governor accepts it
    through ``verify_policy``."""
    return {
        "version": version, "issued_at": issued_at, "expires_at": expires_at,
        # The data center this edition governs (GOAL.md: the chip guards its server, its rack and the governed
        # servers of its data center, and is not a global kill switch). Heartbeats and authority commands name the
        # site; a governor accepts only its own site's, so one site's heartbeat signers going silent, or being
        # captured, stops or reaches only that site (adversarial audit 3). None: a single-site model.
        "site": site,
        # The fleet ledger's replica keys and how many must sign each answer (govsim/fleet.py). None: no fleet budget.
        "fleet_ledger": dict(fleet_ledger) if fleet_ledger else None,
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
        # Audit 2026-10-26: one heartbeat key and one authority key were single points of failure and of capture (one
        # key's silence stopped every rack that trusted it; one key could halt any rack). A heartbeat now counts only with
        # ``heartbeat_threshold`` distinct signers among the heartbeat key and its cosigners, and a HALT, CLEAR or EXCLUDE
        # only with ``authority_threshold`` distinct authority signers. With 2 of 3, one signer going silent stops
        # nothing, and one stolen key can neither halt a rack nor keep a stale rack alive.
        "heartbeat_cosigners": [k.hex for k in (heartbeat_cosigners or [])],
        "heartbeat_threshold": int(heartbeat_threshold),
        "authority_threshold": int(authority_threshold),
        "list_threshold": int(list_threshold),     # distinct governance signers a rule-input list needs
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
        "safe_mode": safe_mode or {"default_rung": "THROTTLE", "T_throttle_s": 30.0, "T_halt_s": 300.0,   # default rung for an unlisted cause; a THROTTLE escalates to HALT after T_throttle_s, a HALT to SAFE after T_halt_s
                                   "causes": {reasons.LOOP_OPEN: "HALT", reasons.LOOP_BROKEN: "HALT", reasons.LOOP_JUMPERED: "HALT",
                                              reasons.TAMPER: "SAFE", reasons.HEARTBEAT_LOST: "HALT",   # audit 3: a brake alone leaves the GPU computing at half clock
                                              reasons.EPOCH_STRAGGLER: "HALT", reasons.HALT_COMMANDED: "HALT"}},
        "fabric": fabric or {"heartbeat_expiry_s": 5.0, "max_hops": 16, "epoch_deadline_s": 10.0, "loop_bound_s": 0.001},   # heartbeat trust (s), relay hops, staged-epoch deadline (s), loop bound (s)
    }


# Actions the governor performs itself, with no device acting on a ticket: the only rules allowed to name no endpoint.
GOVERNOR_ACTIONS = {"model.output", "model.export", "compute.extend", "weights.write"}
# Actions whose effect leaves the governed system (money, messages, goods, strikes, bytes to a user) and so must be
# bounded by a budget or a rate at the device that acts, whatever the governor does.
OUTWARD_ACTIONS = {"payments.transfer", "message.send", "shipment.order", "strike", "response.release"}


def shape_problems(image: dict) -> list[str]:
    """The rulebook shapes that no governor or endpoint can make safe, named so the edition is refused at signing
    time rather than found by an auditor (fresh audit 30 October 2026, where five of fourteen findings were editions
    that enforced nothing). Returns a list of problems, empty when the edition's shape is sound. Each line names the
    rule and the shape:
      - a rule for an action a device performs that names no endpoint (every device would accept it, or none)
      - a rule whose action leaves the system with neither a budget nor a rate, unless a human must approve each one
      - an observer-mode rule whose risk ceiling is 1.0 (every verdict passes) or that names no observer key
      - a human-mode rule with a quorum below one or no approver keys in the edition
      - a money budget (a budget whose rule moves payments) not owned by the fleet when a fleet ledger is named
      - an audit store named by the edition that is not among its endpoints"""
    problems: list[str] = []
    rules = image.get("rules", []) or []
    owners = image.get("budget_owners", {}) or {}
    approver_keys = image.get("approver_keys", {}) or {}
    has_fleet_ledger = bool((image.get("fleet_ledger") or {}).get("keys"))
    endpoint_names = {e.get("name") for e in image.get("endpoints", []) or []}
    for r in rules:
        rid, action = r.get("id", "?"), r.get("action")
        req = r.get("requirement") or {}
        mode = req.get("mode", "auto")
        if mode == "deny":
            continue
        if not r.get("endpoint") and action not in GOVERNOR_ACTIONS:
            problems.append(f"{rid}: names no endpoint for an action a device performs")
        if action in OUTWARD_ACTIONS and not r.get("budget") and not r.get("rate") and mode != "human" and action != "response.release":
            problems.append(f"{rid}: an outward action with neither a budget nor a rate")
        if action == "response.release" and not r.get("output_budget") and not any(x.get("action") == "model.output" and x.get("output_budget") for x in rules):
            problems.append(f"{rid}: a release rule with no output budget anywhere in the edition")
        if mode == "observer":
            if float(req.get("max_risk", 1.0)) >= 1.0:
                problems.append(f"{rid}: an observer-mode rule whose risk ceiling is 1.0 (every verdict passes)")
            if not image.get("observer_keys"):
                problems.append(f"{rid}: an observer-mode rule in an edition with no observer keys")
        if mode == "human":
            if int(req.get("approvers_quorum", 0) or 0) < 1:
                problems.append(f"{rid}: a human-mode rule with a quorum below one")
            if not approver_keys.get(rid):
                problems.append(f"{rid}: a human-mode rule with no approver keys in the edition")
        if r.get("budget") and action == "payments.transfer" and has_fleet_ledger and owners.get(r["budget"].get("key")) != "fleet":
            problems.append(f"{rid}: a money budget not owned by the fleet though a fleet ledger is named")
    store = (image.get("audit") or {}).get("store")
    if store and endpoint_names and store not in endpoint_names:
        problems.append(f"audit store {store} is not among the edition's endpoints")
    return problems


def policy_epoch(image: dict) -> str:
    """The epoch of an image: a digest of its body, with the signatures left out. Two images that differ in any field
    get different epochs, so a command made under one edition cannot be replayed under another."""
    body = {k: v for k, v in image.items() if k != "signatures"}
    return digest(body)


def sign_policy(image: dict, keys: Iterable[SigningKey]) -> dict:
    """Return a copy of the image with one signature from each signing key. Each signature covers the image's epoch, so a
    signature on one edition is not valid for another. The original image is not changed."""
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
    def named(spec) -> bool:
        if isinstance(spec, dict):                  # a quorum of owners: at least one, and 1 <= threshold <= owners
            o = spec.get("owners") or []
            t = spec.get("threshold", len(o))
            return bool(o) and isinstance(t, int) and 1 <= t <= len(o)
        return bool(spec)
    return [k for k in dict.fromkeys(keys) if not named(owners.get(k))]


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
    labels never reach this function (CONTRACT-BROKER-CANNOT-PICK-RULE)."""
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


# A denylist entry is matched by meaning, not by bytes (audits 2 and 3, 2026-10-26: a protected site written as a
# tuple, one micro-degree off, with an altitude, as text or as a mapping was not "in" the list). The definitions engine
# (govsim/definitions.py) reduces the value and every entry to one canonical meaning first. A value that cannot be
# reduced to the kind of thing the list holds counts as a hit: it is refused, never guessed at.
DENYLIST_TOLERANCE = 1e-3          # degrees of great circle for places: about 111 m


def denylist_hit(v: Any, entries: Any, tolerance: float = DENYLIST_TOLERANCE, kind: str | None = None) -> bool:
    """True when ``v`` means the same thing as any entry of a denylist, or when ``v`` cannot be understood as the
    kind of thing the list holds. Places match within ``tolerance`` degrees of great-circle distance, whatever
    their spelling; text matches after Unicode and case canonicalization; anything else must be equal and of the
    same type (so True is not 1)."""
    kind = kind or D.list_kind(entries)
    if kind == D.GEO:
        here = D.canonical_geo(v)
        if here is None:
            return True                                            # not understood as a place: fail closed
        limit_m = tolerance * D.METRES_PER_DEGREE
        return any((p := D.canonical_geo(e)) is not None and D.distance_m(here, p) <= limit_m for e in entries)
    if kind == D.TEXT:
        word = D.canonical_text(v)
        if word is None:
            return True                                            # not understood as text: fail closed
        return any(D.canonical_text(e) == word for e in entries)
    return any(type(v) is type(e) and v == e for e in entries)


def _same_value(v: Any, allowed: Iterable[Any]) -> bool:
    """Membership with types respected: an allow-list of [1] does not admit True, and "1" is not 1."""
    return any(type(v) is type(a) and v == a for a in allowed)


def check_constraints(rule: dict, params: dict, lists: dict[str, Any]) -> tuple[bool, str]:
    """Typed limits. ``lists`` are the signed lists the governor holds (by list id)."""
    for name, c in rule["constraints"].items():
        if name not in params:
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.missing"
        v = params[name]
        if "type" in c:
            # The rule names the definition this field must satisfy; the field must mean something under it.
            if D.canonical(c["type"], v) is None:
                return False, f"{reasons.GATE_CONSTRAINT}.{name}.not_understood"
        if ("min" in c or "max" in c) and not finite_number(v):   # NaN/inf/bool pass every < / > test otherwise (F03)
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.not_a_finite_number"
        if "min" in c and v < c["min"]:
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.below_min"
        if "max" in c and v > c["max"]:
            return False, f"{reasons.GATE_CONSTRAINT}.{name}.above_max"
        if "in" in c and not _same_value(v, c["in"]):
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
            if denylist_hit(v, lst["entries"], c.get("tolerance", DENYLIST_TOLERANCE), c.get("type")):
                return False, f"{reasons.GATE_CONSTRAINT}.{name}.in_denied_list"
        if "in_list" in c:
            lst = lists.get(c["in_list"])
            if lst is None or lst.get("stale"):
                return False, f"{reasons.GATE_CONSTRAINT}.{name}.list_unavailable"
            if not _same_value(v, lst["entries"]):
                return False, f"{reasons.GATE_CONSTRAINT}.{name}.not_in_allowed_list"
    return True, reasons.OK


# ---------------------------------------------------------------- the fused rule floor and loosening (audit 3)
# Adversarial audit 3: the chip accepted ANY edition a governance quorum signed, including one that dropped the
# protected-site constraint and made strikes automatic. A persistent AI that captures or deceives the signers would
# need nothing more. Two defences, both checked by the governor itself:
#   1. A rule floor fused at manufacture: for the actions it names, every rule must keep the listed constraints and
#      may not use the listed modes. No signature, however many, changes fuses.
#   2. A loosening delay: an edition that loosens the rules in force takes effect only once its own `effective_at`
#      has arrived, and `effective_at` must be at least the fused delay after its `issued_at`. The edition is public
#      (and answerable by the recovery quorum) before it can act.
MODE_STRICTNESS = {"auto": 0, "observer": 1, "human": 2}


def floor_violations(image: dict, floor: list[dict]) -> list[str]:
    """Where an edition falls below the fused rule floor. Each floor entry is
    {"action": a, "constraints": {param: {key: value}}, "forbidden_modes": [..]}: every rule for action a must carry
    those constraint keys with those values, and must not use a forbidden mode."""
    out = []
    for entry in floor:
        for rule in image.get("rules", []):
            if rule.get("action") != entry.get("action"):
                continue
            for param, need in (entry.get("constraints") or {}).items():
                have = (rule.get("constraints") or {}).get(param) or {}
                for k, v in need.items():
                    if have.get(k) != v:
                        out.append(f"{rule.get('id')}.{param}.{k}")
            if (rule.get("requirement") or {}).get("mode") in set(entry.get("forbidden_modes") or []):
                out.append(f"{rule.get('id')}.mode")
    return out


def loosenings(old: dict | None, new: dict) -> list[str]:
    """What an edition makes less strict than the one in force. Covered: new rules, weaker modes, fewer approvers,
    a higher risk ceiling, removed or widened constraints, larger budgets and rates, a different governance key set or
    a lower threshold, and revocations withdrawn. Not covered (stated in docs/28): reference values, endpoints,
    buffer policy and timers, which are compared by the governance process, not by the chip."""
    if not old:
        return []
    out: list[str] = []
    old_rules = {r["id"]: r for r in old.get("rules", [])}
    for r in new.get("rules", []):
        o = old_rules.get(r["id"])
        if o is None:
            out.append(f"rule.{r['id']}.added")
            continue
        rq, oq = r.get("requirement") or {}, o.get("requirement") or {}
        if MODE_STRICTNESS.get(rq.get("mode"), 0) < MODE_STRICTNESS.get(oq.get("mode"), 0):
            out.append(f"rule.{r['id']}.mode")
        if int(rq.get("approvers_quorum") or 0) < int(oq.get("approvers_quorum") or 0):
            out.append(f"rule.{r['id']}.approvers")
        if float(rq.get("max_risk", 1.0)) > float(oq.get("max_risk", 1.0)):
            out.append(f"rule.{r['id']}.max_risk")
        oc, nc = o.get("constraints") or {}, r.get("constraints") or {}
        for param, c in oc.items():
            n = nc.get(param)
            if n is None:
                out.append(f"rule.{r['id']}.{param}.removed")
                continue
            for k, v in c.items():
                if k not in n:
                    out.append(f"rule.{r['id']}.{param}.{k}.removed")
                elif k == "max" and finite_number(n[k]) and finite_number(v) and n[k] > v:
                    out.append(f"rule.{r['id']}.{param}.max")
                elif k == "min" and finite_number(n[k]) and finite_number(v) and n[k] < v:
                    out.append(f"rule.{r['id']}.{param}.min")
                elif k == "in" and not set(map(repr, n[k])) <= set(map(repr, v)):
                    out.append(f"rule.{r['id']}.{param}.in")
                elif k in ("not_in_list", "in_list", "type") and n[k] != v:
                    out.append(f"rule.{r['id']}.{param}.{k}")
        ob, nb = o.get("budget") or {}, r.get("budget") or {}
        if ob and (not nb or float(nb.get("limit", 0)) > float(ob.get("limit", 0))):
            out.append(f"rule.{r['id']}.budget")
        orate, nrate = o.get("rate") or {}, r.get("rate") or {}
        if orate and (not nrate or int(nrate.get("max", 0)) > int(orate.get("max", 0))):
            out.append(f"rule.{r['id']}.rate")
    if sorted(new.get("governance_keys", [])) != sorted(old.get("governance_keys", [])) \
            or int(new.get("threshold", 0)) < int(old.get("threshold", 0)):
        out.append("governance")
    if not set(old.get("revocations", [])) <= set(new.get("revocations", [])):
        out.append("revocations.withdrawn")
    return out


def verify_recovery(image: dict, recovery_hashes: list[str], threshold: int) -> bool:
    """Is this edition signed by the fused recovery quorum? The image carries the recovery public keys
    (``recovery_keys``); only those whose digest is fused count, each once, and ``threshold`` of them must have signed
    the image body. Used when a stolen governance quorum has rotated the chip to the thief's keys (audit 3)."""
    if not recovery_hashes or threshold < 1:
        return False
    try:
        keys = {VerifyKey.from_hex(h).key_id: VerifyKey.from_hex(h) for h in image.get("recovery_keys", [])
                if digest(h) in recovery_hashes}
        epoch = digest({k: v for k, v in image.items() if k != "signatures"})
        good = {sig["signer"] for sig in image.get("signatures", [])
                if sig.get("signer") in keys and verify_object(sig, keys[sig["signer"]]) and sig["payload"].get("epoch") == epoch}
        threshold_ok = 1 <= int(image["threshold"]) <= len(set(image["governance_keys"]))
        return threshold_ok and len(good) >= threshold
    except (KeyError, TypeError, ValueError):
        return False


def make_jurisdiction_edition(*, jurisdiction: str, version: int, issued_at: float, expires_at: float,
                              keys: list[VerifyKey], threshold: int, governs: list[str], rules: list[dict]) -> dict:
    """An unsigned edition for one jurisdiction (adversarial audit 3: several rulebook authorities per chip). It names
    the actions it ``governs``; for those, a request must satisfy one of its ``rules`` as well as the main edition,
    and its strictest requirement applies. Signed with ``sign_policy`` by that jurisdiction's own keys."""
    return {"jurisdiction": jurisdiction, "version": version, "issued_at": issued_at, "expires_at": expires_at,
            "governance_keys": [k.hex for k in keys], "threshold": threshold, "governs": list(governs), "rules": rules}
