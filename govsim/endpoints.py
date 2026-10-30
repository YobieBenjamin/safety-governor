# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Enforcement points and action endpoints.

What this file holds:
- Switches (the enforcement points at rack tier): the switches that the GPU's traffic already passes,
  namely NVSwitch ports, PCIe switch ports, DPU flow tables and the storage path. A port or flow is
  open only while a matching, unexpired capability exists. The governor is the only writer.
- Descriptor checkers (integrated tier only, a future vendor request): the same idea inside the GPU,
  at the copy engine and the peer MMU (memory management unit).
- Action endpoints: the devices that carry out an action, such as a payment switch, a messaging
  service, the DPU egress to the user, and the audit store. An endpoint holds the public keys of the
  governors, its own record of used tickets, the current epoch, a heartbeat timer and its own sensors.
  It re-checks a ticket at the moment it acts.

What it guarantees, as written: an endpoint acts only on a ticket that names the same action and
parameters, the current epoch and this endpoint, and that has not expired or been used already. The
used-ticket record is written under a lock before the action happens, so one ticket is used at most
once at this endpoint. An endpoint whose heartbeat timer has run out refuses to act. A capability's
MAC (a keyed hash that proves who made the entry) is checked when the governor programs the entry.

What it deliberately does NOT do: it does not decide whether an action is allowed. The governor decides
that, and the endpoint only checks the ticket it was given. It does not re-check the MAC on each lookup.
The device checks in ``strike_checks`` are the checks for one device, not a full list of what a device
must check.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

from . import reasons
from .crypto import SigningKey, VerifyKey, canonical, digest, finite_number, hmac_sha256, sha256, verify_any, verify_object
from .store import Store

def number_or_none(v):
    """The value as a float when it is a real, finite number (bool excluded), else None."""
    return float(v) if finite_number(v) else None


MAX_CLOCK_SKEW_S = 60.0             # how far ahead of this device's clock a receipt, approval or commit statement may be dated
REVOCATION_PEERS = 2                # other governors of the rack whose signed statements revoke a governor here
REQUIRED_TICKET_FIELDS = ("type", "ticket_id", "request_id", "request_hash", "action", "params_digest", "measurement", "rule",
                          "policy_epoch", "endpoint", "governor", "valid_from", "expires_at")
TICKET_TTL_S = 300.0                # the governor's ticket TTL (govsim.governor.TICKET_TTL_S); repeated here so the endpoint
                                    # does not import the governor

# F29: the ticket-binding check. True in every real run. The red-team self-test sets it to False, for the length
# of one run, to show that the battery reports a leak when the binding is missing. Nothing else changes it.
ENFORCE_TICKET_BINDING = True

RACK_POINTS = ("nvswitch", "pcie", "dpu", "storage")
USED_TICKET_CAPACITY = 1 << 20      # the endpoint's used-ticket store (docs/04: 2**20 entries)
MAX_TICKET_LIFE_S = 3600.0          # no ticket is good for longer than an hour, whatever its payload says: a far-future ticket
                                    # would never leave the used-ticket store (audit 30 October 2026)
INTEGRATED_POINTS = ("copy_engine", "peer_mmu")
BRICKED = ("display", "jtag", "debug")


class Switch:
    """A governed switch: NVSwitch, PCIe switch, DPU flow table or the storage path.

    ``program`` is the governor's write path, and it verifies the governor's MAC. On a bare-metal HGX host today root
    can also reprogram NVSwitch routing and PCIe switch ports in band (docs/research/nvswitch-management.md). Since
    adversarial audit 3 the model has that path too: ``host_write`` opens an entry with no MAC, and works whenever
    the switch's in-band management is not locked down (``locked`` False). Locking it (out-of-band-only management,
    PCIe switch configuration lockdown) is a board and switch-firmware requirement; the governor reads the lock state
    and the switch firmware measurement over its own sideband (``lock_report``) and refuses RUN on a switch that is
    not locked (docs/research/switch-management-lockdown.md).
    """

    def __init__(self, kind: str, owner_chip_id: str, cap_key: bytes, log: Callable[[str, dict], None]):
        """Create one switch of ``kind`` (one of ``RACK_POINTS``). ``owner_chip_id`` names the governor that
        programs it, and ``cap_key`` is the key its capability MACs are made with. ``log`` is the governor's
        logging function. A new switch has no open entries."""
        self.kind = kind
        self.owner = owner_chip_id
        self._cap_key = cap_key
        self.table: dict[tuple[str, str], dict] = {}     # (peer, direction) -> capability
        self.bytes_by_direction: dict[tuple[str, str], int] = {}   # (peer, direction) -> bytes admitted
        self.log = log
        self.refusals: list[dict] = []
        self.epoch_tag = ""
        self.bytes_passed: dict[str, int] = {}           # peer -> bytes that crossed this switch
        self.locked = True                               # in-band (host) management disabled; False on today's bare metal
        self.firmware_digest = "switch-fw-reference"     # measured by the governor over its sideband

    def lock_report(self) -> dict:
        """What the governor reads over its sideband: whether in-band management is locked, and the firmware digest."""
        return {"locked": bool(self.locked), "firmware": self.firmware_digest}

    def host_write(self, peer: str, direction: str, budget: int = 1 << 40) -> bool:
        """The host writing a port or flow in band, with no governor capability. Possible only on an unlocked switch."""
        if self.locked:
            return False
        self.table[(peer, direction)] = {"point": self.kind, "peer": peer, "direction": direction, "budget": budget,
                                         "expiry": float("inf"), "epoch_tag": self.epoch_tag, "buffer_class": None}
        return True

    def mac(self, cap: dict) -> str:
        """The MAC over a capability's contents, leaving out the MAC field itself. Two capabilities with the
        same contents have the same MAC, and a changed field makes the MAC wrong."""
        body = {k: v for k, v in cap.items() if k != "mac"}
        return hmac_sha256(self._cap_key, canonical(body))

    def _key(self, cap: dict) -> tuple:
        """The table key. A switch sees peer and direction and nothing finer (buffer classes are not on the wire)."""
        return (cap["peer"], cap["direction"])

    def program(self, cap: dict) -> bool:
        """Open one port or flow from a capability the governor made. Output: True when it is stored. A capability
        for another switch kind, or with a wrong MAC, is refused and logged. This is the only write path."""
        if cap.get("point") != self.kind or cap.get("mac") != self.mac(cap):
            self.refusals.append({"why": reasons.EP_NO_CAPABILITY, "cap": cap})
            return False
        self.table[self._key(cap)] = dict(cap)
        return True

    def close_all(self) -> None:
        """Close every port and flow on this switch."""
        self.table.clear()

    def close_peer(self, peer: str) -> None:
        """Close every port and flow to one peer."""
        for k in [k for k in self.table if k[0] == peer]:
            self.table.pop(k)

    def set_epoch(self, epoch_tag: str) -> None:
        """Record the epoch tag. A capability with a different tag is refused (see ``_admit``)."""
        self.epoch_tag = epoch_tag

    def pass_traffic(self, peer: str, direction: str, nbytes: int, now: float) -> tuple[bool, str]:
        """Check one transfer against the table. An entry for this peer and direction is used, or an entry marked
        ``both``, which covers either direction. With no entry the transfer is refused. Output: (ok, reason)."""
        cap = self.table.get((peer, direction)) or self.table.get((peer, "both"))
        if cap is None:
            return self._refuse(peer, direction, nbytes, reasons.EP_NO_CAPABILITY)
        return self._admit(cap, peer, direction, nbytes, now)

    def _admit(self, cap: dict, peer: str, direction: str, nbytes: int, now: float, **extra) -> tuple[bool, str]:
        """The checks on a matching entry: expiry, epoch tag, byte budget. One lookup, one decrement."""
        if cap["expiry"] <= now:
            self.table.pop(self._key(cap), None)      # an expired entry is removed, so it cannot be used again
            return self._refuse(peer, direction, nbytes, reasons.EP_EXPIRED, **extra)
        if cap["epoch_tag"] != self.epoch_tag:
            return self._refuse(peer, direction, nbytes, reasons.EP_STALE_EPOCH, **extra)
        if cap["budget"] < nbytes:
            return self._refuse(peer, direction, nbytes, reasons.EP_BUDGET_EXHAUSTED, **extra)
        if cap.get("single_use") and nbytes != cap["budget"]:
            # F31: a single-use grant covers exactly the bytes it names, in one transfer
            return self._refuse(peer, direction, nbytes, reasons.EP_BUDGET_EXHAUSTED, **extra)
        cap["budget"] -= nbytes
        self.bytes_passed[peer] = self.bytes_passed.get(peer, 0) + nbytes
        self.bytes_by_direction[(peer, direction)] = self.bytes_by_direction.get((peer, direction), 0) + nbytes
        if cap.get("single_use") and cap["budget"] == 0:
            self.table.pop(self._key(cap), None)     # F31: the grant is spent and cannot be used again
        return True, reasons.OK

    def _refuse(self, peer: str, direction: str, nbytes: int, why: str, **extra) -> tuple[bool, str]:
        """Record one refused transfer in the refusal list and in the log, then return (False, reason)."""
        self.refusals.append({"switch": self.kind, "peer": peer, "direction": direction, "bytes": nbytes, "why": why, **extra})
        self.log("switch.refused", {"switch": self.kind, "peer": peer, "bytes": nbytes, "why": why, **extra})
        return False, why


class DescriptorChecker(Switch):
    """Integrated tier only: the same table at a copy engine or the peer MMU, inside the GPU, keyed on
    (peer, direction, buffer class). A class with no entry for that peer is refused: EP_BUFFER_CLASS."""

    def _key(self, cap: dict) -> tuple:
        """The table key for a checker: peer, direction and buffer class. Each buffer class has its own entry."""
        return (cap["peer"], cap["direction"], cap.get("buffer_class"))

    def pass_traffic(self, peer: str, direction: str, nbytes: int, now: float, buffer_class: str = "activations") -> tuple[bool, str]:
        """Check one transfer at a checker, as ``Switch.pass_traffic`` does, but the buffer class must also have an
        entry for that peer. When the peer has entries for other classes, the reason is EP_BUFFER_CLASS. Output: (ok, reason)."""
        cap = self.table.get((peer, direction, buffer_class)) or self.table.get((peer, "both", buffer_class))
        if cap is None:
            why = reasons.EP_BUFFER_CLASS if any(k[0] == peer for k in self.table) else reasons.EP_NO_CAPABILITY
            return self._refuse(peer, direction, nbytes, why, buffer_class=buffer_class)
        return self._admit(cap, peer, direction, nbytes, now, buffer_class=buffer_class)


class ActionEndpoint:
    """The comparator in the device that acts (requirement REQUIREMENT-RULEBOOK-SELECTS-RULE-AND-LANE, REQUIREMENT-AUTHORIZATION-IS-DURABLE-TRANSACTION; hypotheses CONTRACT-FRESH-AUTHORIZATION-PER-OPERATION, CONTRACT-COMPARATOR-SURVIVES-COMPROMISE)."""

    def __init__(self, name: str, clock, governor_keys: dict[str, VerifyKey], store: Store | None = None,
                 safe_transition: str = "no_action", lists: dict[str, Any] | None = None,
                 sensors: dict[str, Any] | None = None, heartbeat_expiry_s: float = 5.0,
                 governance_hashes: list[str] | None = None, governance_floor: int | None = None,
                 recovery_hashes: list[str] | None = None, recovery_threshold: int = 0,
                 governor_ids: dict[str, str] | None = None, device_key: SigningKey | None = None):
        """Create one endpoint. ``governor_keys`` maps each governor's key id to its public key, for every governor
        that may mint a ticket for this device. ``device_key`` is this device's own key; the edition lists the public
        key of every device under its role name, and a device whose key the edition does not list installs no edition
        and so acts on nothing (fresh audit 30 October 2026: a second device with a listed role name allowed the full
        cap again). ``safe_transition`` is what the endpoint does when it refuses
        (the rack's endpoints use ``no_release``, ``decline`` or ``hold``). ``sensors`` are the device's own inputs at
        the moment of action. The used-ticket record loads from the store, so it survives a restart."""
        self.name = name
        self.clock = clock
        self.device_key = device_key
        self.keys = dict(governor_keys)      # key id -> VerifyKey of every governor that may mint for this device
        self.governor_ids = dict(governor_ids or {})   # key id -> chip id, when known: a ticket's governor field must match its signer
        self.store = store or Store()
        self.consumed = self.store.get("consumed", {})     # ticket_id -> t
        # F33: a second, separate record of burned tickets, written in the same save as ``consumed``. The single-use
        # check reads both. Clearing one record does not reopen a ticket; clearing both still does (see the tests).
        self.burned = self.store.get("burned", {})        # ticket_id -> t
        # ticket_id -> the ticket's own expiry. Once a ticket has expired, admit() refuses it anyway, so its used
        # record can be dropped: the store is bounded by the tickets live at once, not by all tickets ever seen.
        self.used_expiry = self.store.get("used_expiry", {})
        # Fleet reservations already spent at this endpoint: "replica key id:reservation id" -> [ticket_id, expiry].
        # One ledger reservation authorizes one ticket here; a second ticket carrying the same receipts is refused, so
        # a governor whose key was extracted cannot reuse one real reservation for many payments (29 October 2026).
        self.used_reservations = self.store.get("used_reservations", {})
        # Request hashes already acted on here: request_hash -> [ticket_id, expiry]. One authorization (approvals,
        # verdicts, receipts all name the request hash) buys one effect at this endpoint; a second ticket for the same
        # request is refused, whoever signed it (review panel 30 October 2026).
        self.used_requests = self.store.get("used_requests", {})
        # What this endpoint itself has let through under each budget key: budget_key -> [[time, amount], ...]. The
        # endpoint is a second counter for every budgeted rule, so a governor whose key was extracted, on a host that
        # forges commits, is still bounded by the edition's limit at this device even where no fleet ledger counts
        # (review panel 30 October 2026: the default rack's money budget had no bound outside the governor).
        self.spent = self.store.get("spent", {})
        # Actions this endpoint has let through under each rate-bearing rule: rule id -> [time, ...]. The endpoint
        # counts the rule's rate as it counts its budget (fresh audit 30 October 2026: rates were counted nowhere here).
        self.acted = self.store.get("acted", {})
        # Governors revoked at this device by a signed revocation statement (a governor's last act before its tamper
        # response wipes its key), kept in the store so a restart does not forget (fresh audit 30 October 2026).
        self.revoked_by_statement = set(self.store.get("revoked_by_statement", []))
        self.revocation_votes = self.store.get("revocation_votes", {})   # revoked key id -> [peer key ids that signed]
        self.list_floor = self.store.get("list_floor", {})  # list_id -> highest version ever installed here
        self.unchecked_list_constraints = 0   # list constraints this endpoint refused because it held no fresh copy of the list   # list constraints this endpoint could not re-check because it holds no such list
        # Concurrency contract: a single endpoint may be driven by several threads at once (concurrent
        # dispatch). Admission plus durable consumption is an atomic compare-and-set under this lock, so
        # for any one ticket exactly one caller becomes the owner and crosses the effect boundary (F11).
        self._lock = threading.Lock()
        self.epoch = ""
        self.policy_expires_at = None       # F30: the edition's expiry, checked against this endpoint's clock on every admit
        self.safe_transition = safe_transition
        self.lists = {**(lists or {}), **self.store.get("lists", {})}   # list id -> {"entries": [...], "stale": bool}; held signed lists come back from the store
        self.sensors = sensors or {}        # the device's own inputs at the moment of action
        self.hb_expiry = 0.0
        self.heartbeat_expiry_s = heartbeat_expiry_s
        self.commit: Callable[[dict], bool] | None = None   # set by the cluster: the governor's COMMIT path
        self.executed: list[dict] = []
        self.refused: list[tuple[str, str]] = []
        self.state = "ARMED"
        self.checks: list[Callable[[dict, dict], tuple[bool, str]]] = []   # device-specific re-checks
        # The edition in force, verified by the endpoint itself against the governance keys fused into the device at
        # manufacture (audit 2026-10-26: a ticket signed by any one governor key used to be enough). With an edition the
        # endpoint re-checks every ticket against the rulebook, so one governor key, extracted or lying, can authorize
        # only what some rule of the current edition allows, and nothing once the edition revokes that governor.
        self.governance_hashes = governance_hashes
        self.governance_floor = governance_floor
        self.recovery_hashes, self.recovery_threshold = list(recovery_hashes or []), int(recovery_threshold or 0)
        self.trusted: dict | None = None      # the governance keys and k of the edition in force (they authorize the next)
        self.edition: dict | None = None
        self.revoked: set[str] = set()

    # --- inputs from the governor ---------------------------------------------
    def set_epoch(self, signed_epoch: dict) -> bool:
        """Accept the governor's signed statement of the current epoch. A statement that does not verify is ignored,
        and the function returns False. Tickets for any other epoch are refused later, in ``admit``."""
        if verify_any(signed_epoch, self.keys) is None or signed_epoch["payload"].get("type") != "policy-epoch":
            return False
        # Never backwards: a statement for an older edition, or a different epoch at the same version, is refused,
        # so a replayed statement cannot roll this endpoint back (adversarial audit 3).
        version = signed_epoch["payload"].get("version")
        if not isinstance(version, int) or isinstance(version, bool):
            return False
        held = getattr(self, "epoch_version", None)
        if held is not None and (version < held or (version == held and signed_epoch["payload"]["epoch"] != self.epoch)):
            return False
        if self.edition is not None and signed_epoch["payload"]["epoch"] != self._edition_epoch:
            return False   # a governor's statement cannot move this device to an epoch its governance-signed edition does not name
        self.epoch_version = version
        self.epoch = signed_epoch["payload"]["epoch"]
        if self.edition is None:
            # No edition installed (a device without governance anchors): the statement is the only source. With an
            # edition, the expiry is the edition's own and a governor's statement cannot change it (fresh audit
            # 30 October 2026: a statement with expires_at None erased the expiry at every endpoint).
            self.policy_expires_at = signed_epoch["payload"].get("expires_at")
        return True

    def revoke_governor(self, statement: dict) -> bool:
        """A signed statement that a governor is revoked. Two sources count: the governor itself (its last act before
        the tamper response wipes its key, which a host between it and this device can swallow), and the other
        governors of the rack, who learn of the tamper over the governor fabric and each sign a statement; this device
        revokes on the governor's own word or on REVOCATION_PEERS distinct peers' words. The extracted key can forge only its own governor's revocation, or one peer's vote, which is the
        fail-closed direction. The record survives a restart (fresh audits of 30 October 2026)."""
        if not isinstance(statement, dict) or not isinstance(statement.get("payload"), dict):
            return False
        signer = verify_any(statement, self.keys)
        p = statement["payload"]
        target = p.get("key")
        if signer is None or p.get("type") != "governor-revoked" or not isinstance(target, str) or target not in self.keys:
            return False
        if statement.get("signer") == target:
            self.revoked_by_statement.add(target)
        else:
            votes = set(self.revocation_votes.get(target, []))
            votes.add(statement["signer"])
            self.revocation_votes[target] = sorted(votes)
            # Exactly REVOCATION_PEERS distinct peers, never fewer: in a rack with one peer, one extracted key could
            # otherwise revoke the other governor (a denial), so there the governor's own statement is the only path
            # and the host-swallow residual stands, stated in docs/29.
            if len(votes) >= REVOCATION_PEERS:
                self.revoked_by_statement.add(target)
        self.store.data["revoked_by_statement"] = sorted(self.revoked_by_statement)
        self.store.save()
        return target in self.revoked_by_statement

    def _prune_used(self, now: float) -> None:
        """Drop the used records of tickets that have expired (admit refuses an expired ticket on its own)."""
        for tid in [tid for tid, exp in self.used_expiry.items() if exp < now]:
            self.consumed.pop(tid, None)
            self.burned.pop(tid, None)
            self.used_expiry.pop(tid, None)
        for key in [k for k, (_, exp) in self.used_reservations.items() if exp < now]:
            self.used_reservations.pop(key, None)
        for key in [k for k, (_, exp) in self.used_requests.items() if exp < now]:
            self.used_requests.pop(key, None)

    def _authentic(self, ticket: dict) -> bool:
        """Signed by a governor this endpoint trusts, or, at an egress holding the MAC key it shares with its own
        governor, a release ticket MACed under that key (adversarial audit 3: per-response signatures overloaded the
        signing engine)."""
        if not isinstance(ticket, dict) or not isinstance(ticket.get("payload"), dict):
            return False
        if "mac" in ticket:
            key = getattr(self, "mac_key", None)
            if key is None or ticket["payload"].get("action") != "response.release" or ticket.get("signer") not in self.keys:
                return False
            import hmac as _hmac
            return _hmac.compare_digest(str(ticket["mac"]), hmac_sha256(key, canonical(ticket["payload"])))
        return verify_any(ticket, self.keys) is not None

    def install_edition(self, image: dict) -> bool:
        """Install a governance-signed edition after checking it here: its signatures against the governance keys in
        force (the fused key hashes for the first one), and no rollback of the version. Returns True when installed."""
        if self.governance_hashes is None:
            return False
        from .policy import policy_epoch, verify_policy, verify_recovery
        ok, _ = verify_policy(image, self.governance_hashes, self.governance_floor, trusted=self.trusted)
        ok = ok or verify_recovery(image, self.recovery_hashes, self.recovery_threshold)   # the fused recovery quorum
        if not ok or (self.edition is not None and image["version"] < self.edition["version"]):
            return False
        from .policy import shape_problems
        if shape_problems(image):
            return False   # the device will not enforce an edition whose shape enforces nothing (fresh audits 30 October 2026)
        listed = [e for e in image.get("endpoints", []) or [] if e.get("name") == self.name and e.get("pubkey")]
        if listed and (self.device_key is None or self.device_key.public.hex not in {e["pubkey"] for e in listed}):
            # The edition names the devices of this role by key. A device that is not one of them is not a device the
            # rulebook addressed, so it takes no edition and acts on nothing.
            return False
        self.edition = image
        self.trusted = {"keys": list(image["governance_keys"]), "threshold": int(image["threshold"])}
        self.revoked = set(image.get("revocations", []))
        self._edition_epoch = policy_epoch(image)
        self.policy_expires_at = number_or_none(image.get("expires_at"))   # F30: the edition's own expiry, from the edition alone
        # The governance-signed edition is itself the announcement of the epoch: the endpoint moves to it now, and no
        # governor-signed statement of an older version can move it back (see set_epoch).
        if getattr(self, "epoch_version", None) is None or int(image["version"]) >= self.epoch_version:
            self.epoch_version = int(image["version"])
            self.epoch = self._edition_epoch
        return True

    def _check_against_edition(self, ticket: dict, t: dict, action: str, params: dict, now: float) -> tuple[bool, str]:
        """The ticket's governor is not revoked, and the rule it names exists in the edition in force and allows this
        action, at this endpoint, for this workload, with these fields (typed limits; list checks stay at the
        governor, which holds the signed lists)."""
        if self.edition is None:
            return False, reasons.TICKET_NO_EDITION
        if ticket.get("signer") in self.revoked or t.get("governor") in self.revoked or ticket.get("signer") in self.revoked_by_statement:
            return False, reasons.TICKET_REVOKED_GOVERNOR
        if t.get("policy_epoch") != self._edition_epoch:
            return False, reasons.TICKET_STALE_EPOCH
        rule = next((r for r in self.edition.get("rules", []) if r.get("id") == t.get("rule")), None)
        if rule is None:
            return False, reasons.TICKET_NO_RULE
        # A rule that names no endpoint addresses no device, so no device acts on it (fresh audit 30 October 2026:
        # such a rule was accepted everywhere).
        if rule.get("action") != action or rule.get("endpoint") != self.name \
                or rule.get("measurement") not in ("*", t.get("measurement")) \
                or (rule.get("requirement") or {}).get("mode") == "deny":
            return False, reasons.TICKET_RULE_MISMATCH
        from .policy import check_constraints
        # Typed limits are re-checked here in full. A list constraint (a protected-site denylist, a recipient
        # registry) is re-checked when this endpoint holds that signed list (``install_list``); a list it does not
        # hold stays the governor's check alone, and is counted, so an operator can see what one governor key could
        # still authorize at this device (29 October 2026; before, every list check stayed at the governor).
        # A list constraint is checked against the fresh signed copy this device holds. A list it does not hold, or
        # holds but expired, is a refusal, as the register row says ("stale is a denial"); it was counted and let
        # through before the fresh audits of 30 October 2026, which under the extracted key made messaging an open
        # exit the day the list aged.
        held = {lid: meta for lid, meta in self._live_lists().items() if not meta.get("stale")}
        for name, c in (rule.get("constraints") or {}).items():
            lid = c.get("not_in_list") or c.get("in_list")
            if lid is not None and lid not in held:
                self.unchecked_list_constraints += 1
                return False, reasons.TICKET_RULE_MISMATCH + f".{name}.list_unavailable"
        ok, why = check_constraints(rule, params, held)
        if not ok:
            return False, reasons.TICKET_RULE_MISMATCH + "." + why
        ben = rule.get("beneficiary") or {}
        if ben.get("registry"):
            # The beneficiary registry (F04): the payee must be on the fresh signed registry this device holds.
            reg = held.get(ben["registry"])
            if reg is None:
                self.unchecked_list_constraints += 1
                return False, reasons.TICKET_RULE_MISMATCH + ".beneficiary.list_unavailable"
            if params.get(ben.get("param", "destination")) not in reg.get("entries", []):
                return False, reasons.TICKET_RULE_MISMATCH + ".beneficiary.not_in_registry"
        ok, why = self._mode_ok(t, rule, params, now)
        if not ok:
            return False, why
        # The budget the ticket names must be the rule's budget, as the edition has it. Every budget check below keys
        # off the rule, never off a field the ticket's signer chose (review panel 30 October 2026: a ticket re-signed
        # with budget_key set to None skipped the fleet-commit check and refilled the cap).
        budget = rule.get("budget")
        if budget:
            if t.get("budget_key") != budget.get("key") or not (t.get("reservation") and t.get("budget_owner")):
                return False, reasons.TICKET_RULE_MISMATCH + ".no_reservation"
            owner = (self.edition.get("budget_owners") or {}).get(budget["key"])
            if owner == "fleet":
                if t.get("budget_owner") != "fleet":
                    return False, reasons.TICKET_RULE_MISMATCH + ".budget_owner_mismatch"
                ok, why = self._fleet_receipts_ok(t, rule, params, now)
                if not ok:
                    return False, why
        elif t.get("budget_key") or t.get("reservation"):
            return False, reasons.TICKET_RULE_MISMATCH + ".unexpected_reservation"
        return True, reasons.OK

    def _rule_of(self, t: dict) -> dict | None:
        if self.edition is None:
            return None
        return next((r for r in self.edition.get("rules", []) if r.get("id") == t.get("rule")), None)

    def _max_ticket_life(self) -> float:
        """A ticket lives at most its TTL plus the longest delay any rule in the edition in force can add; with no
        edition the fixed ceiling applies (review panel 30 October 2026)."""
        if self.edition is None:
            return MAX_TICKET_LIFE_S
        delays = [float(r.get("delay_s", 0.0) or 0.0) for r in self.edition.get("rules", []) if finite_number(r.get("delay_s", 0.0) or 0.0)]
        return min(MAX_TICKET_LIFE_S, TICKET_TTL_S + (max(delays) if delays else 0.0))

    def _record_grace(self) -> float:
        """How long past the longest ticket life a used record is kept: the longest rule delay in the edition plus
        the clock skew allowed to credentials. Records are dated from this device's clock at the burn, never from a
        field of the ticket, so an attacker-written expiry cannot shorten them (fresh audits 30 October 2026); after a
        life plus this grace, no credential naming the record can still be accepted."""
        return max(0.0, self._max_ticket_life() - TICKET_TTL_S) + MAX_CLOCK_SKEW_S

    def _budget_room(self, t: dict, rule: dict, params: dict, now: float) -> tuple[bool, str]:
        """This endpoint's own count under the rule's budget: the amounts it has let through inside the rule's window
        plus this one must fit the rule's limit. It is a bound this device enforces from what it has done, so it does
        not depend on any governor's ledger. For a fleet-owned budget it is only a per-device bound, which is never
        looser than the fleet cap."""
        budget = rule.get("budget") or {}
        amount = number_or_none(params.get(budget.get("param")))
        limit, window = number_or_none(budget.get("limit")), number_or_none(budget.get("window_s", 3600.0))
        if amount is None or limit is None or window is None or amount < 0:
            return False, reasons.TICKET_RULE_MISMATCH + ".amount_malformed"
        # The edition may list several devices under this role; each device may let through its share of the limit,
        # so the devices together never exceed it (the share is the limit divided by the number of listed devices).
        share = max(1, len([e for e in (self.edition or {}).get("endpoints", []) or [] if e.get("name") == self.name]))
        rows = [[at, a] for at, a in self.spent.get(budget["key"], []) if at > now - window]
        if sum(a for _, a in rows) + amount > limit / share:
            return False, reasons.TICKET_RULE_MISMATCH + ".endpoint_budget_exceeded"
        self.spent[budget["key"]] = rows
        return True, reasons.OK

    def _mode_ok(self, t: dict, rule: dict, params: dict, now: float) -> tuple[bool, str]:
        """The rule's mode is enforced here, not only at the governor (audit 30 October 2026: a captured governor key
        could mint a ticket for a human-mode rule with no approver). A human-mode rule needs the edition's quorum of
        distinct approvers for that rule, each a signed approval naming this ticket's request hash. An observer-mode
        rule needs at least one observer's signed verdict naming the request hash."""
        mode = (rule.get("requirement") or {}).get("mode", "auto")
        if mode == "human":
            hexes = (self.edition.get("approver_keys") or {}).get(rule.get("id"), [])
            keys = {vk.key_id: vk for vk in (VerifyKey.from_hex(h) for h in hexes)}
            quorum = max(1, int((rule.get("requirement") or {}).get("approvers_quorum", 1) or 1))
            if not keys:
                return False, reasons.TICKET_RULE_MISMATCH + ".no_approver_keys"
            signers: set[str] = set()
            for env in t.get("approvals") or []:
                if not isinstance(env, dict) or verify_any(env, keys) is None:
                    continue
                p = env.get("payload") or {}
                # The approval names this request's hash (which the endpoint has recomputed from the parameters it
                # holds) and the epoch the ticket was minted under; an approval from an older rulebook is no approval.
                at = number_or_none(p.get("at"))
                if at is None or at < now - self._max_ticket_life() or at > now + MAX_CLOCK_SKEW_S:
                    continue   # an approval with no time, older than any ticket can live, or from the future, is a captured approval
                if p.get("type") == "approve" and p.get("request_hash") == t.get("request_hash") and p.get("epoch") == t.get("policy_epoch"):
                    signers.add(env["signer"])
            if len(signers) < quorum:
                return False, reasons.TICKET_RULE_MISMATCH + ".approvals_short"
        elif mode == "observer":
            keys = {vk.key_id: vk for vk in (VerifyKey.from_hex(h) for h in self.edition.get("observer_keys") or [])}
            # A verdict is bound to this ticket either by the request hash (a witnessed action) or by the response
            # hash the ticket names (a release ticket, where the observer judged the model's response, not the request).
            # Only a release ticket is bound to a verdict by the response hash (the observer judged the response, not
            # the request); every other observer-mode rule binds by the request hash alone (fresh audit 30 October
            # 2026: a captured verdict on a clean chat reply fired a strike through a response_hash parameter).
            release = rule.get("action") == RELEASE_ACTION
            max_risk = number_or_none((rule.get("requirement") or {}).get("max_risk", 1.0))
            good = 0
            for env in t.get("witnesses") or []:
                if isinstance(env, dict) and verify_any(env, keys) is not None:
                    p = env.get("payload") or {}
                    if p.get("type") != "observer-verdict":
                        continue
                    if release:
                        if p.get("response_hash") is None or p.get("response_hash") != (params or {}).get("response_hash"):
                            continue
                    elif p.get("request_hash") != t.get("request_hash"):
                        continue
                    # Checked as the governor checks it (review panel 30 October 2026: an expired verdict with risk
                    # 0.99 fired a strike because the endpoint matched the hash and nothing else).
                    exp, risk = number_or_none(p.get("expires_at")), number_or_none(p.get("risk", 1.0))
                    if exp is None or exp <= now or risk is None or (max_risk is not None and risk > max_risk):
                        continue
                    if release and not self._release_verdict_ok(p, rule, params, t):
                        continue
                    good += 1
            if good < 1:
                return False, reasons.TICKET_RULE_MISMATCH + ".no_observer_verdict"
        return True, reasons.OK

    def _release_verdict_ok(self, p: dict, rule: dict, params: dict, t: dict) -> bool:
        """The release checks the governor makes, made again here: the hazard class is one the rule allows, the
        legibility meets the rule's floor, and a response in an escrowed class carries the audit store's escrow
        receipt among the ticket's witnesses (fresh audit 30 October 2026: the egress checked expiry and risk only,
        and the release rule's risk ceiling was 1.0, so a response the observer called hazardous was released on a
        forged commit). The session hazard budget is a count across responses and stays the governor's."""
        req = rule.get("requirement") or {}
        hazard = str(p.get("hazard_class", "hazard"))
        if hazard not in (req.get("allowed_hazard_classes") or ["none"]):
            return False
        legibility = number_or_none(p.get("legibility", 0.0))
        if legibility is None or legibility < float(req.get("min_legibility", 0.0) or 0.0):
            return False
        audit = (self.edition or {}).get("audit") or {}
        if hazard in (audit.get("escrow_classes") or []):
            store_keys = {VerifyKey.from_hex(e["pubkey"]).key_id: VerifyKey.from_hex(e["pubkey"])
                          for e in (self.edition or {}).get("endpoints", []) if e.get("name") == audit.get("store") and e.get("pubkey")}
            if not any(isinstance(w, dict) and verify_any(w, store_keys) is not None and (w.get("payload") or {}).get("type") == "escrow"
                       and (w.get("payload") or {}).get("response_hash") == (params or {}).get("response_hash")
                       for w in t.get("escrow") or []):
                return False
        return True

    def _rate_room(self, rule: dict, now: float) -> tuple[bool, str]:
        """This endpoint's own count of actions under a rate-bearing rule inside the rule's window."""
        rate = rule.get("rate") or {}
        limit, window = number_or_none(rate.get("max")), number_or_none(rate.get("window_s"))
        if limit is None or window is None:
            return False, reasons.TICKET_RULE_MISMATCH + ".rate_malformed"
        share = max(1, len([e for e in (self.edition or {}).get("endpoints", []) or [] if e.get("name") == self.name]))
        times = [at for at in self.acted.get(rule["id"], []) if at > now - window]
        if len(times) + 1 > limit / share:
            return False, reasons.TICKET_RULE_MISMATCH + ".endpoint_rate_exceeded"
        times.append(now)
        self.acted[rule["id"]] = times
        return True, reasons.OK

    def _fleet_receipts_ok(self, t: dict, rule: dict, params: dict, now: float) -> tuple[bool, str]:
        """A ticket under a fleet-owned budget must carry the fleet ledger's receipts for its reservation: the
        edition's threshold of distinct replicas, each a signed receipt over this budget key, this amount, this
        governor, and the reservation id the ticket names for that replica. The endpoint verifies them against the
        replica keys the edition names, so the fleet cap is enforced by the ledger and checked by the endpoint, and a
        governor's extracted key alone buys nothing past the cap (29 October 2026)."""
        spec = self.edition.get("fleet_ledger") or {}
        keys = {vk.key_id: vk for vk in (VerifyKey.from_hex(h) for h in spec.get("keys", []))}
        k = int(spec.get("threshold", 0) or 0)
        if not keys or k < 1:
            return False, reasons.TICKET_RULE_MISMATCH + ".fleet_ledger_unknown"
        receipts = t.get("fleet_receipts")
        rids = t.get("reservation")
        if not isinstance(receipts, list) or not isinstance(rids, dict):
            return False, reasons.TICKET_RULE_MISMATCH + ".fleet_receipts_missing"
        amount = params.get(rule["budget"]["param"])
        seen: set[str] = set()
        for env in receipts:
            if not isinstance(env, dict) or verify_any(env, keys) is None:
                continue
            p = env["payload"]
            if p.get("type") != "fleet-reserve" or p.get("key") != rule["budget"]["key"] or p.get("reserver") != t.get("governor"):
                continue
            if not finite_number(p.get("amount")) or not finite_number(amount) or p["amount"] != amount:
                continue
            if rids.get(env["signer"]) != p.get("rid"):
                continue
            b = p.get("binding") or {}
            if b.get("request_hash") != t.get("request_hash") or b.get("endpoint") != self.name or b.get("ticket_id") != t.get("ticket_id"):
                continue   # a receipt made for another request, another ticket or another device buys nothing here
            at = number_or_none(p.get("at"))
            if at is None or at < now - self._max_ticket_life() or at > now + MAX_CLOCK_SKEW_S:
                continue   # a receipt older than any ticket can live, or dated ahead of this device's clock, is a captured receipt
            seen.add(env["signer"])
        if len(seen) < k:
            return False, reasons.TICKET_RULE_MISMATCH + ".fleet_receipts_short"
        return True, reasons.OK

    def install_list(self, list_id: str, signed_list: dict) -> bool:
        """Hold a signed list this device's rules compare against, checked the way the governor checks it: signed by
        the edition's list quorum of distinct, unrevoked governance signers, naming this list id. The list is read at
        use time through ``_live_lists``, where expiry and issuer revocation make it stale (F06)."""
        if self.edition is None:
            return False
        keys = {}
        for h in self.edition.get("governance_keys", []):
            vk = VerifyKey.from_hex(h)
            if vk.key_id not in self.revoked:
                keys[vk.key_id] = vk
        signer = verify_any(signed_list, keys)
        if signer is None or signed_list["payload"].get("list_id") != list_id:
            return False
        signers = {signer.key_id}
        for c in signed_list.get("cosignatures", []) or []:
            if isinstance(c, dict) and c.get("payload") == signed_list.get("payload"):
                vk = verify_any(c, keys)
                if vk is not None:
                    signers.add(vk.key_id)
        if len(signers) < int(self.edition.get("list_threshold", 1) or 1):
            return False
        p = signed_list["payload"]
        expires_at, version = number_or_none(p.get("expires_at", 0)), p.get("version", 0)
        if expires_at is None or not isinstance(version, int) or isinstance(version, bool) or not isinstance(p.get("entries"), list):
            return False   # a malformed list is refused, not raised on
        if expires_at <= self.clock.now():
            return False   # an expired list is never installed, so a replayed old list cannot be used to refuse honest traffic
        held = self.lists.get(list_id)
        floor = int(self.list_floor.get(list_id, 0))
        if int(version) < max(floor, int(held.get("version", 0)) if held else floor):
            return False
        self.lists[list_id] = {"entries": p["entries"], "expires_at": p["expires_at"], "version": int(p.get("version", 0)),
                               "issuer": signer.key_id, "list_id": list_id}
        self.store.data["lists"] = {lid: m for lid, m in self.lists.items() if "expires_at" in m}   # held lists survive a restart
        # The version floor lives in the store, so an older list cannot be reinstalled after a power cycle
        # (audit 30 October 2026: the floor was in memory only).
        self.list_floor[list_id] = int(p.get("version", 0))
        self.store.save()
        return True

    def _live_lists(self) -> dict[str, dict]:
        """The lists this endpoint holds, as the rules see them now: stale once expired or once the edition revokes
        the issuer. A list handed in at construction (``lists=``) with its own ``stale`` flag is passed through."""
        now = self.clock.now()
        view: dict[str, dict] = {}
        for lid, meta in self.lists.items():
            if "expires_at" in meta:
                stale = float(meta["expires_at"]) <= now or meta.get("issuer") in self.revoked
            else:
                stale = bool(meta.get("stale"))
            view[lid] = {**meta, "stale": stale}
        return view

    def _commit_verified(self, ticket: dict, committed, now: float) -> bool:
        """A commit is good only as a statement from the governor that minted the ticket (signed, or MACed for a MACed
        release ticket), naming this ticket, this request, this endpoint, the ticket's budget key and reservation, and,
        when the edition owns the rule's budget as fleet, carrying the edition's threshold of distinct replicas'
        fleet-commit receipts, each closing the reservation this ticket names for that replica and bound to this
        request and this device. Anything else, a bare True included, is no commit. Every check keys off the edition's
        rule, not off a field of the ticket (review panel 30 October 2026)."""
        if not isinstance(committed, dict) or not isinstance(committed.get("payload"), dict) or committed.get("signer") != ticket.get("signer"):
            return False
        if ticket.get("signer") in self.revoked_by_statement:
            return False
        if ("mac" in committed) != ("mac" in ticket):
            return False   # the statement is authenticated the way the ticket was: MAC for MAC, signature for signature
        if "mac" in committed:
            key = getattr(self, "mac_key", None)
            if key is None:
                return False
            import hmac as _hmac
            if not _hmac.compare_digest(str(committed["mac"]), hmac_sha256(key, canonical(committed["payload"]))):
                return False
        elif verify_any(committed, self.keys) is None:
            return False
        t, c = ticket["payload"], committed["payload"]
        if c.get("type") != "commit" or c.get("ticket_id") != t.get("ticket_id") or c.get("request_hash") != t.get("request_hash") \
                or c.get("endpoint") != self.name or c.get("budget_key") != t.get("budget_key") or c.get("reservation") != t.get("reservation"):
            return False
        at = number_or_none(c.get("at"))
        if at is None or at > now + MAX_CLOCK_SKEW_S or at < now - self._max_ticket_life():
            return False
        rule = self._rule_of(t)
        if self.edition is not None and rule is None:
            return False
        budget = (rule or {}).get("budget")
        if budget and (self.edition.get("budget_owners") or {}).get(budget["key"]) == "fleet":
            spec = self.edition.get("fleet_ledger") or {}
            keys = {vk.key_id: vk for vk in (VerifyKey.from_hex(h) for h in spec.get("keys", []))}
            k = int(spec.get("threshold", 0) or 0)
            rids = t.get("reservation") if isinstance(t.get("reservation"), dict) else {}
            closed: set[str] = set()
            for env in c.get("fleet_receipts") or []:
                if not isinstance(env, dict) or verify_any(env, keys) is None:
                    continue
                p = env.get("payload") or {}
                b = p.get("binding") or {}
                if p.get("type") == "fleet-commit" and p.get("key") == budget["key"] and p.get("reserver") == t.get("governor") \
                        and rids.get(env["signer"]) == p.get("rid") and b.get("request_hash") == t.get("request_hash") \
                        and b.get("endpoint") == self.name and b.get("ticket_id") == t.get("ticket_id"):
                    closed.add(env["signer"])
            if not keys or k < 1 or len(closed) < k:
                return False
        return True

    def heartbeat(self, now: float) -> None:
        """Renew the heartbeat timer. ``execute`` refuses to act once the timer has run out."""
        self.hb_expiry = now + self.heartbeat_expiry_s

    # --- the comparator ---------------------------------------------------------
    def admit(self, ticket: dict | None, action: str, params: dict, now: float) -> tuple[bool, str]:
        """The comparator. Checks a ticket against the action and parameters the caller presents. The checks run in
        this order: the ticket is present, its signature verifies, it is a ticket, its action and parameters match,
        its epoch is the current one, it names this endpoint (if it names one), it is inside its validity window,
        and it has not been used. Output: (ok, reason). It does not burn the ticket; ``execute`` does that."""
        if ticket is None:
            return False, reasons.TICKET_MISSING
        if not self._authentic(ticket) or ticket["payload"].get("type") != "ticket":
            return False, reasons.TICKET_BAD_SIGNATURE
        t = ticket["payload"]
        if any(f not in t for f in REQUIRED_TICKET_FIELDS):
            return False, reasons.TICKET_BAD_SIGNATURE + ".malformed"   # a ticket missing a field is refused, not raised on
        if t["action"] != action:
            return False, reasons.TICKET_ACTION_MISMATCH
        # A ticket's life is bounded by the device, not only by its payload (audit 30 October 2026). Both window edges
        # must be finite numbers; a string or an infinity in either is refused, not raised (review panel 30 October 2026).
        valid_from, expires_at = number_or_none(t.get("valid_from", 0.0)), number_or_none(t.get("expires_at"))
        if valid_from is None or expires_at is None:
            return False, reasons.TICKET_RULE_MISMATCH + ".validity_malformed"
        life = self._max_ticket_life()
        if expires_at - valid_from > life or expires_at > now + life:
            return False, reasons.TICKET_RULE_MISMATCH + ".validity_too_long"
        if self.governor_ids and self.governor_ids.get(ticket.get("signer")) not in (None, t.get("governor")):
            return False, reasons.TICKET_RULE_MISMATCH + ".governor_mismatch"
        if t["params_digest"] != digest(params):
            return False, reasons.TICKET_PARAMS_MISMATCH
        # The request hash is recomputed here from the request id and measurement the ticket carries and the action
        # and parameters presented, the way the governor built it. Every approval, verdict and receipt names that hash,
        # so this is what ties them to these parameters (review panel 30 October 2026).
        if t.get("request_hash") != digest([t.get("request_id"), t.get("measurement"), action, params]):
            return False, reasons.TICKET_RULE_MISMATCH + ".request_hash_mismatch"
        spent = self.used_requests.get(t.get("request_hash"))
        if spent and spent[0] != t["ticket_id"]:
            return False, reasons.TICKET_REPLAY + ".request_spent"
        # F29: every ticket names exactly one endpoint. An unbound ticket is refused, and so is a ticket
        # that names another endpoint. The check does not depend on the ticket carrying a truthy field.
        if ENFORCE_TICKET_BINDING:
            if not t.get("endpoint"):
                return False, reasons.TICKET_UNBOUND
            if t["endpoint"] != self.name:
                return False, reasons.TICKET_WRONG_ENDPOINT
        if getattr(self, "mac_key", None) is not None and t.get("action") == RELEASE_ACTION and "mac" not in ticket:
            # This egress shares a MAC key with its governor, so a release ticket here is MACed; a signed one did not
            # come through that path (fresh audit 30 October 2026: a signed release ticket bypassed the MAC entirely).
            return False, reasons.TICKET_BAD_SIGNATURE + ".release_not_maced"
        if self.policy_expires_at is not None and now >= self.policy_expires_at:
            return False, reasons.POLICY_EXPIRED     # F30: the edition has expired, whatever the governor's tick has or has not done
        if t["policy_epoch"] != self.epoch:
            return False, reasons.TICKET_STALE_EPOCH
        if self.governance_hashes is not None:
            ok, why = self._check_against_edition(ticket, t, action, params, now)
            if not ok:
                return False, why
        if now < valid_from:
            return False, reasons.TICKET_NOT_YET_VALID
        if now >= expires_at:
            return False, reasons.TICKET_EXPIRED
        if t["ticket_id"] in self.consumed:
            return False, reasons.TICKET_REPLAY
        return True, reasons.OK

    def execute(self, ticket: dict | None, action: str, params: dict) -> tuple[bool, str]:
        """Admit, burn, commit at the governor, re-check with own inputs, act."""
        now = self.clock.now()
        if now > self.hb_expiry:
            return self._refuse(reasons.ENDPOINT_HEARTBEAT_EXPIRED)
        ok, why = self.admit(ticket, action, params, now)
        if not ok:
            return self._refuse(why)
        t = ticket["payload"]
        # The replay check inside admit() above is advisory; the authoritative single-use check is this
        # compare-and-set, which re-reads the consumed set under the lock and burns the ticket in the same
        # critical section. Two callers that both cleared admit cannot both burn: the loser sees the burn
        # the winner just wrote and is refused here, before it can commit or dispatch an effect (F11).
        with self._lock:
            if t["ticket_id"] in self.consumed or t["ticket_id"] in self.burned:
                return self._refuse(reasons.TICKET_REPLAY)
            if len(self.consumed) >= USED_TICKET_CAPACITY:
                self._prune_used(now)
                if len(self.consumed) >= USED_TICKET_CAPACITY:
                    # Adversarial audit 3: the design did not say what happens when the used-ticket store fills. It
                    # refuses: a ticket that cannot be recorded as used is never executed.
                    return self._refuse(reasons.ENDPOINT_TICKET_STORE_FULL)
            if isinstance(t.get("fleet_receipts"), list) and isinstance(t.get("reservation"), dict):
                # One fleet reservation, one ticket at this endpoint: a second ticket that carries receipts for a
                # reservation already spent here is refused before it can act, whoever signed it.
                pairs = [f"{signer}:{rid}" for signer, rid in t["reservation"].items()]
                # Once spent here, a reservation buys nothing again, the same ticket included (a second presentation of
                # the same ticket is a replay whatever the other records say).
                if any(self.used_reservations.get(pair) is not None for pair in pairs):
                    return self._refuse(reasons.TICKET_REPLAY + ".reservation_spent")
                for pair in pairs:
                    self.used_reservations[pair] = [t["ticket_id"], now + self._max_ticket_life() + self._record_grace()]
            spent = self.used_requests.get(t.get("request_hash"))
            if spent is not None:
                return self._refuse(reasons.TICKET_REPLAY + ".request_spent")
            # Records are kept for as long as any receipt or approval that names them can still be presented. A
            # credential is accepted while it is younger than the longest ticket life, and it was issued no later
            # than the ticket's expiry minus the TTL, so the ticket's expiry plus the longest rule delay covers it
            # (fresh audit 30 October 2026: records pruned at the ticket's expiry let a cycled store reopen them).
            keep_until = now + self._max_ticket_life() + self._record_grace()
            self.used_requests[t.get("request_hash")] = [t["ticket_id"], keep_until]
            rule = self._rule_of(t)
            if rule is not None and rule.get("rate"):
                ok, why = self._rate_room(rule, now)
                if not ok:
                    return self._refuse(why)
            if rule is not None and rule.get("budget"):
                ok, why = self._budget_room(t, rule, params, now)
                if not ok:
                    return self._refuse(why)
                # Counted at the burn, inside the lock, so two tickets admitted together cannot both fit the last of
                # the limit; a ticket whose commit then fails stays counted (fail closed, the window clears it).
                key, param = rule["budget"]["key"], rule["budget"].get("param")
                self.spent.setdefault(key, []).append([now, number_or_none(params.get(param)) or 0.0])
            self.used_expiry[t["ticket_id"]] = now + self._max_ticket_life() + self._record_grace()
            self.consumed[t["ticket_id"]] = now
            self.burned[t["ticket_id"]] = now  # F33: the second record, saved with the first
            self.store.save()                  # burned before anything else happens
        try:
            committed = self.commit(ticket) if self.commit else False
        except ConnectionError:
            return self._refuse(reasons.COMMIT_UNREACHABLE)
        if committed and not self._commit_verified(ticket, committed, now):
            # The host answered for the governor, or the fleet ledger did not close the reservation: no effect
            # (audit 30 October 2026: a bare 'yes' from the host used to be enough).
            committed = False
        if not committed:
            return self._refuse(reasons.COMMIT_REJECTED)
        # The device's own checks run after the commit, so a ticket that fails one of them is already burned and
        # committed. The ticket cannot be used again. See the report for this ordering.
        for check in self.checks:              # the device's own sensors and lists
            ok, why = check(params, self.sensors)
            if not ok:
                return self._refuse(why)
        self.executed.append({"action": action, "params": params, "ticket": t["ticket_id"], "t": now})
        return True, reasons.OK

    def _refuse(self, why: str) -> tuple[bool, str]:
        """Record a refusal and move the endpoint to its safe transition (for example no release, decline or hold).
        Returns (False, reason)."""
        self.refused.append((why, self.safe_transition))
        self.state = self.safe_transition
        return False, why

    def restart(self) -> None:
        """Power loss and return: the used-ticket set comes back from the store."""
        self.store.power_loss()
        self.store.check_epoch_marks()       # F34: refuses to start when the two epoch-mark copies disagree
        self.consumed = self.store.get("consumed", {})
        self.burned = self.store.get("burned", {})
        self.used_expiry = self.store.get("used_expiry", {})
        self.used_reservations = self.store.get("used_reservations", {})
        self.used_requests = self.store.get("used_requests", {})
        self.spent = self.store.get("spent", {})
        self.acted = self.store.get("acted", {})
        self.revoked_by_statement = set(self.store.get("revoked_by_statement", []))
        self.revocation_votes = self.store.get("revocation_votes", {})
        self.list_floor = self.store.get("list_floor", {})
        self.lists = {**self.lists, **self.store.get("lists", {})}   # the signed lists this device held before the power cycle
        self.state = "ARMED"


RELEASE_ACTION = "response.release"


class EgressEndpoint(ActionEndpoint):
    """The DPU's egress to the user: bytes are held until a release ticket for exactly that response
    is admitted. Without a valid ticket the bytes never leave."""

    def __init__(self, name: str, clock, governor_keys: dict[str, VerifyKey], store: Store | None = None, safe_transition: str = "hold",
                 governance_hashes: list[str] | None = None, governance_floor: int | None = None,
                 recovery_hashes: list[str] | None = None, recovery_threshold: int = 0,
                 governor_ids: dict[str, str] | None = None, device_key: SigningKey | None = None):
        """The egress for one node. It holds responses until a release ticket covers them. Its safe transition is ``hold``.
        It holds the governance anchors too, so it learns each new edition from the governance signatures themselves
        and not only from its own governor (adversarial audit 3: a straggling governor kept its egress on old rules)."""
        super().__init__(name, clock, governor_keys, store, safe_transition=safe_transition,
                         governance_hashes=governance_hashes, governance_floor=governance_floor,
                         recovery_hashes=recovery_hashes, recovery_threshold=recovery_threshold, governor_ids=governor_ids,
                         device_key=device_key)
        self.held: dict[tuple[str, str], dict] = {}        # (session, response_id) -> {"bytes", "response_hash", "stream_hashes"}
        self.delivered: dict[str, list[bytes]] = {}        # session -> responses that left
        self.bytes_held = 0
        self.bytes_delivered = 0

    def hold(self, session: str, response_id: str, data: bytes, stream_hashes: dict[str, str] | None = None) -> str:
        """Buffer a response; returns its hash, which the governor's ticket must name."""
        h = sha256(data)
        self.held[(session, response_id)] = {"bytes": data, "response_hash": h, "stream_hashes": dict(stream_hashes or {"response": h})}
        self.bytes_held += len(data)
        return h

    def release(self, ticket: dict | None) -> tuple[bool, str]:
        """Admit a ``response.release`` ticket: its params digest must cover one held (session, response_id,
        response_hash); only then do the bytes move to ``delivered``."""
        if ticket is None:
            return self._refuse(reasons.TICKET_MISSING)
        want = (ticket.get("payload") or {}).get("params_digest")
        for (session, response_id), item in list(self.held.items()):
            params = {"session": session, "response_id": response_id, "response_hash": item["response_hash"], "stream_hashes": item["stream_hashes"]}
            if digest(params) != want:
                continue
            # F32: the bytes held here must still hash to the committed hash the ticket names. A write to the
            # held buffer that changes the bytes is refused before the ticket is spent or anything leaves.
            if sha256(item["bytes"]) != item["response_hash"]:
                return self._refuse(reasons.RELEASE_HASH_MISMATCH)
            ok, why = self.execute(ticket, RELEASE_ACTION, params)
            if ok:
                self.held.pop((session, response_id))
                self.delivered.setdefault(session, []).append(item["bytes"])
                self.bytes_held -= len(item["bytes"])
                self.bytes_delivered += len(item["bytes"])
            return ok, why
        return self._refuse(reasons.TICKET_PARAMS_MISMATCH)


class AuditStore(EgressEndpoint):
    """The audit store: an egress of its own (the sandbox's only one) that also signs escrow receipts."""

    def __init__(self, name: str, clock, governor_keys: dict[str, VerifyKey], key: SigningKey, store: Store | None = None, **anchors):
        """The escrow endpoint. ``key`` is its own signing key, used for escrow receipts. Its safe transition is ``hold``.
        ``anchors`` are the governance anchors every endpoint takes (governance_hashes and so on)."""
        super().__init__(name, clock, governor_keys, store, safe_transition="hold", device_key=key, **anchors)
        self.key = key
        self.receipts: list[str] = []

    def receipt(self, response_hash: str) -> dict:
        """The signed acknowledgement that a response is in escrow: the witness a release request carries."""
        self.receipts.append(response_hash)
        return self.key.sign({"type": "escrow", "store": self.name, "response_hash": response_hash, "time": self.clock.now()})


# ----------------------------------------------------------------------------- device checks
def strike_checks(protected_list_id: str = "protected-sites") -> list[Callable]:
    """A guidance chip: two independent navigation sources must agree; the target must not
    be on the signed protected-site list the device holds; a stale list is a denial."""

    def nav_agree(params: dict, sensors: dict) -> tuple[bool, str]:
        """The satellite and inertial positions must agree: each coordinate differs by at most 0.01 degrees.
        A missing reading counts as a conflict."""
        from .definitions import canonical_geo
        a, b = canonical_geo(sensors.get("nav_gnss")), canonical_geo(sensors.get("nav_inertial"))
        if a is None or b is None or abs(a[0] - b[0]) > 0.01 or abs(a[1] - b[1]) > 0.01:
            return False, reasons.ENDPOINT_SENSOR_CONFLICT
        return True, reasons.OK

    def not_protected(params: dict, sensors: dict) -> tuple[bool, str]:
        """Neither the requested target nor the position the device's own satellite reading gives may be on the
        protected-site list. A missing or stale list is a denial. Positions match within the denylist tolerance
        (about 100 m), whatever their container type (audit 2026-10-26: this check used to read only a fixed sensor
        and compared exact rounded tuples, so the requested target was never checked here)."""
        from .policy import denylist_hit
        lst = sensors.get("lists", {}).get(protected_list_id)
        if lst is None or lst.get("stale"):
            return False, reasons.ENDPOINT_LIST_STALE
        # Both positions are required; a missing one, or one that is not understood as a place, is refused
        # (denylist_hit fails closed on anything the definitions engine cannot read as a place).
        for pos in (params.get("target"), sensors.get("nav_gnss")):
            if pos is None or denylist_hit(pos, lst["entries"], kind="geo"):
                return False, reasons.ENDPOINT_TARGET_PROTECTED
        return True, reasons.OK

    return [nav_agree, not_protected]
