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
from .crypto import SigningKey, VerifyKey, canonical, digest, hmac_sha256, sha256, verify_any, verify_object
from .store import Store

# F29: the ticket-binding check. True in every real run. The red-team self-test sets it to False, for the length
# of one run, to show that the battery reports a leak when the binding is missing. Nothing else changes it.
ENFORCE_TICKET_BINDING = True

RACK_POINTS = ("nvswitch", "pcie", "dpu", "storage")
USED_TICKET_CAPACITY = 1 << 20      # the endpoint's used-ticket store (docs/04: 2**20 entries)
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
                 recovery_hashes: list[str] | None = None, recovery_threshold: int = 0):
        """Create one endpoint. ``governor_keys`` maps each governor's key id to its public key, for every governor
        that may mint a ticket for this device. ``safe_transition`` is what the endpoint does when it refuses
        (the rack's endpoints use ``no_release``, ``decline`` or ``hold``). ``sensors`` are the device's own inputs at
        the moment of action. The used-ticket record loads from the store, so it survives a restart."""
        self.name = name
        self.clock = clock
        self.keys = dict(governor_keys)      # key id -> VerifyKey of every governor that may mint for this device
        self.store = store or Store()
        self.consumed = self.store.get("consumed", {})     # ticket_id -> t
        # F33: a second, separate record of burned tickets, written in the same save as ``consumed``. The single-use
        # check reads both. Clearing one record does not reopen a ticket; clearing both still does (see the tests).
        self.burned = self.store.get("burned", {})        # ticket_id -> t
        # ticket_id -> the ticket's own expiry. Once a ticket has expired, admit() refuses it anyway, so its used
        # record can be dropped: the store is bounded by the tickets live at once, not by all tickets ever seen.
        self.used_expiry = self.store.get("used_expiry", {})
        # Concurrency contract: a single endpoint may be driven by several threads at once (concurrent
        # dispatch). Admission plus durable consumption is an atomic compare-and-set under this lock, so
        # for any one ticket exactly one caller becomes the owner and crosses the effect boundary (F11).
        self._lock = threading.Lock()
        self.epoch = ""
        self.policy_expires_at = None       # F30: the edition's expiry, checked against this endpoint's clock on every admit
        self.safe_transition = safe_transition
        self.lists = lists or {}            # list id -> {"entries": [...], "stale": bool}
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
        self.epoch_version = version
        self.epoch = signed_epoch["payload"]["epoch"]
        self.policy_expires_at = signed_epoch["payload"].get("expires_at")     # F30: None when the edition names no expiry
        return True

    def _prune_used(self, now: float) -> None:
        """Drop the used records of tickets that have expired (admit refuses an expired ticket on its own)."""
        for tid in [tid for tid, exp in self.used_expiry.items() if exp < now]:
            self.consumed.pop(tid, None)
            self.burned.pop(tid, None)
            self.used_expiry.pop(tid, None)

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
        self.edition = image
        self.trusted = {"keys": list(image["governance_keys"]), "threshold": int(image["threshold"])}
        self.revoked = set(image.get("revocations", []))
        self._edition_epoch = policy_epoch(image)
        # The governance-signed edition is itself the announcement of the epoch: the endpoint moves to it now, and no
        # governor-signed statement of an older version can move it back (see set_epoch).
        if getattr(self, "epoch_version", None) is None or int(image["version"]) >= self.epoch_version:
            self.epoch_version = int(image["version"])
            self.epoch = self._edition_epoch
        return True

    def _check_against_edition(self, ticket: dict, t: dict, action: str, params: dict) -> tuple[bool, str]:
        """The ticket's governor is not revoked, and the rule it names exists in the edition in force and allows this
        action, at this endpoint, for this workload, with these fields (typed limits; list checks stay at the
        governor, which holds the signed lists)."""
        if self.edition is None:
            return False, reasons.TICKET_NO_EDITION
        if ticket.get("signer") in self.revoked or t.get("governor") in self.revoked:
            return False, reasons.TICKET_REVOKED_GOVERNOR
        if t.get("policy_epoch") != self._edition_epoch:
            return False, reasons.TICKET_STALE_EPOCH
        rule = next((r for r in self.edition.get("rules", []) if r.get("id") == t.get("rule")), None)
        if rule is None:
            return False, reasons.TICKET_NO_RULE
        if rule.get("action") != action or (rule.get("endpoint") and rule["endpoint"] != self.name) \
                or rule.get("measurement") not in ("*", t.get("measurement")) \
                or (rule.get("requirement") or {}).get("mode") == "deny":
            return False, reasons.TICKET_RULE_MISMATCH
        from .policy import check_constraints
        typed = {**rule, "constraints": {k: c for k, c in (rule.get("constraints") or {}).items()
                                         if "in_list" not in c and "not_in_list" not in c}}
        ok, why = check_constraints(typed, params, {})
        if not ok:
            return False, reasons.TICKET_RULE_MISMATCH + "." + why
        if rule.get("budget") and not (t.get("reservation") and t.get("budget_owner")):
            return False, reasons.TICKET_RULE_MISMATCH + ".no_reservation"
        return True, reasons.OK

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
        if t["action"] != action:
            return False, reasons.TICKET_ACTION_MISMATCH
        if t["params_digest"] != digest(params):
            return False, reasons.TICKET_PARAMS_MISMATCH
        # F29: every ticket names exactly one endpoint. An unbound ticket is refused, and so is a ticket
        # that names another endpoint. The check does not depend on the ticket carrying a truthy field.
        if ENFORCE_TICKET_BINDING:
            if not t.get("endpoint"):
                return False, reasons.TICKET_UNBOUND
            if t["endpoint"] != self.name:
                return False, reasons.TICKET_WRONG_ENDPOINT
        if self.policy_expires_at is not None and now >= self.policy_expires_at:
            return False, reasons.POLICY_EXPIRED     # F30: the edition has expired, whatever the governor's tick has or has not done
        if t["policy_epoch"] != self.epoch:
            return False, reasons.TICKET_STALE_EPOCH
        if self.governance_hashes is not None:
            ok, why = self._check_against_edition(ticket, t, action, params)
            if not ok:
                return False, why
        if now < t.get("valid_from", 0.0):
            return False, reasons.TICKET_NOT_YET_VALID
        if now >= t["expires_at"]:
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
            self.used_expiry[t["ticket_id"]] = float(t.get("expires_at", now))
            self.consumed[t["ticket_id"]] = now
            self.burned[t["ticket_id"]] = now  # F33: the second record, saved with the first
            self.store.save()                  # burned before anything else happens
        try:
            committed = self.commit(ticket) if self.commit else False
        except ConnectionError:
            return self._refuse(reasons.COMMIT_UNREACHABLE)
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
        self.state = "ARMED"


RELEASE_ACTION = "response.release"


class EgressEndpoint(ActionEndpoint):
    """The DPU's egress to the user: bytes are held until a release ticket for exactly that response
    is admitted. Without a valid ticket the bytes never leave."""

    def __init__(self, name: str, clock, governor_keys: dict[str, VerifyKey], store: Store | None = None, safe_transition: str = "hold",
                 governance_hashes: list[str] | None = None, governance_floor: int | None = None,
                 recovery_hashes: list[str] | None = None, recovery_threshold: int = 0):
        """The egress for one node. It holds responses until a release ticket covers them. Its safe transition is ``hold``.
        It holds the governance anchors too, so it learns each new edition from the governance signatures themselves
        and not only from its own governor (adversarial audit 3: a straggling governor kept its egress on old rules)."""
        super().__init__(name, clock, governor_keys, store, safe_transition=safe_transition,
                         governance_hashes=governance_hashes, governance_floor=governance_floor,
                         recovery_hashes=recovery_hashes, recovery_threshold=recovery_threshold)
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

    def __init__(self, name: str, clock, governor_keys: dict[str, VerifyKey], key: SigningKey, store: Store | None = None):
        """The escrow endpoint. ``key`` is its own signing key, used for escrow receipts. Its safe transition is ``hold``."""
        super().__init__(name, clock, governor_keys, store, safe_transition="hold")
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
