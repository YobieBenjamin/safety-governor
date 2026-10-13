"""Enforcement points and action endpoints.

Rack tier: the enforcement points are the switches the GPU's traffic already passes
(NVSwitch ports, PCIe switch ports and ACS, DPU flow tables, the storage path). The governor
is their only writer; a port or flow is open exactly when a matching, unexpired capability
exists. Integrated tier (a future vendor ask): descriptor-level checkers inside the GPU.

Action endpoints are the comparators in the devices that act. They hold the public keys of
the rack's governors, their own used-ticket store (the model's used-ticket set lives here, not
in the governor), the current epoch, a heartbeat timer and their own sensors, and they re-check
at the moment of action.
"""
from __future__ import annotations

from typing import Any, Callable

from . import reasons
from .crypto import SigningKey, VerifyKey, canonical, digest, hmac_sha256, sha256, verify_any, verify_object
from .store import Store

RACK_POINTS = ("nvswitch", "pcie", "dpu", "storage")
INTEGRATED_POINTS = ("copy_engine", "peer_mmu")
BRICKED = ("display", "jtag", "debug")


class Switch:
    """A governed switch: NVSwitch, PCIe switch, DPU flow table or the storage path.

    ``program`` is the only way to open a port or flow, and it verifies the governor's MAC.
    There is no host write path: the governor is the only master on the management bus.
    """

    def __init__(self, kind: str, owner_chip_id: str, cap_key: bytes, log: Callable[[str, dict], None]):
        self.kind = kind
        self.owner = owner_chip_id
        self._cap_key = cap_key
        self.table: dict[tuple[str, str], dict] = {}     # (peer, direction) -> capability
        self.log = log
        self.refusals: list[dict] = []
        self.epoch_tag = ""
        self.bytes_passed: dict[str, int] = {}           # peer -> bytes that crossed this switch

    def mac(self, cap: dict) -> str:
        body = {k: v for k, v in cap.items() if k != "mac"}
        return hmac_sha256(self._cap_key, canonical(body))

    def _key(self, cap: dict) -> tuple:
        """The table key. A switch sees peer and direction and nothing finer (buffer classes are not on the wire)."""
        return (cap["peer"], cap["direction"])

    def program(self, cap: dict) -> bool:
        if cap.get("point") != self.kind or cap.get("mac") != self.mac(cap):
            self.refusals.append({"why": reasons.EP_NO_CAPABILITY, "cap": cap})
            return False
        self.table[self._key(cap)] = dict(cap)
        return True

    def close_all(self) -> None:
        self.table.clear()

    def close_peer(self, peer: str) -> None:
        for k in [k for k in self.table if k[0] == peer]:
            self.table.pop(k)

    def set_epoch(self, epoch_tag: str) -> None:
        self.epoch_tag = epoch_tag

    def pass_traffic(self, peer: str, direction: str, nbytes: int, now: float) -> tuple[bool, str]:
        cap = self.table.get((peer, direction)) or self.table.get((peer, "both"))
        if cap is None:
            return self._refuse(peer, direction, nbytes, reasons.EP_NO_CAPABILITY)
        return self._admit(cap, peer, direction, nbytes, now)

    def _admit(self, cap: dict, peer: str, direction: str, nbytes: int, now: float, **extra) -> tuple[bool, str]:
        """The checks on a matching entry: expiry, epoch tag, byte budget. One lookup, one decrement."""
        if cap["expiry"] <= now:
            self.table.pop(self._key(cap), None)
            return self._refuse(peer, direction, nbytes, reasons.EP_EXPIRED, **extra)
        if cap["epoch_tag"] != self.epoch_tag:
            return self._refuse(peer, direction, nbytes, reasons.EP_STALE_EPOCH, **extra)
        if cap["budget"] < nbytes:
            return self._refuse(peer, direction, nbytes, reasons.EP_BUDGET_EXHAUSTED, **extra)
        cap["budget"] -= nbytes
        self.bytes_passed[peer] = self.bytes_passed.get(peer, 0) + nbytes
        return True, reasons.OK

    def _refuse(self, peer: str, direction: str, nbytes: int, why: str, **extra) -> tuple[bool, str]:
        self.refusals.append({"switch": self.kind, "peer": peer, "direction": direction, "bytes": nbytes, "why": why, **extra})
        self.log("switch.refused", {"switch": self.kind, "peer": peer, "bytes": nbytes, "why": why, **extra})
        return False, why


class DescriptorChecker(Switch):
    """Integrated tier only: the same table at a copy engine or the peer MMU, inside the GPU, keyed on
    (peer, direction, buffer class). A class with no entry for that peer is refused: EP_BUFFER_CLASS."""

    def _key(self, cap: dict) -> tuple:
        return (cap["peer"], cap["direction"], cap.get("buffer_class"))

    def pass_traffic(self, peer: str, direction: str, nbytes: int, now: float, buffer_class: str = "activations") -> tuple[bool, str]:
        cap = self.table.get((peer, direction, buffer_class)) or self.table.get((peer, "both", buffer_class))
        if cap is None:
            why = reasons.EP_BUFFER_CLASS if any(k[0] == peer for k in self.table) else reasons.EP_NO_CAPABILITY
            return self._refuse(peer, direction, nbytes, why, buffer_class=buffer_class)
        return self._admit(cap, peer, direction, nbytes, now, buffer_class=buffer_class)


class ActionEndpoint:
    """The comparator in the device that acts (requirement R10, R11; hypotheses H0, H6)."""

    def __init__(self, name: str, clock, governor_keys: dict[str, VerifyKey], store: Store | None = None,
                 safe_transition: str = "no_action", lists: dict[str, Any] | None = None,
                 sensors: dict[str, Any] | None = None, heartbeat_expiry_s: float = 5.0):
        self.name = name
        self.clock = clock
        self.keys = dict(governor_keys)      # key id -> VerifyKey of every governor that may mint for this device
        self.store = store or Store()
        self.consumed = self.store.get("consumed", {})     # ticket_id -> t
        self.epoch = ""
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

    # --- inputs from the governor ---------------------------------------------
    def set_epoch(self, signed_epoch: dict) -> bool:
        if verify_any(signed_epoch, self.keys) is None or signed_epoch["payload"].get("type") != "policy-epoch":
            return False
        self.epoch = signed_epoch["payload"]["epoch"]
        return True

    def heartbeat(self, now: float) -> None:
        self.hb_expiry = now + self.heartbeat_expiry_s

    # --- the comparator ---------------------------------------------------------
    def admit(self, ticket: dict | None, action: str, params: dict, now: float) -> tuple[bool, str]:
        if ticket is None:
            return False, reasons.TICKET_MISSING
        if verify_any(ticket, self.keys) is None or ticket["payload"].get("type") != "ticket":
            return False, reasons.TICKET_BAD_SIGNATURE
        t = ticket["payload"]
        if t["action"] != action:
            return False, reasons.TICKET_ACTION_MISMATCH
        if t["params_digest"] != digest(params):
            return False, reasons.TICKET_PARAMS_MISMATCH
        if t["policy_epoch"] != self.epoch:
            return False, reasons.TICKET_STALE_EPOCH
        if t.get("endpoint") and t["endpoint"] != self.name:
            return False, reasons.TICKET_WRONG_ENDPOINT
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
        self.consumed[t["ticket_id"]] = now
        self.store.save()                      # burned before anything else happens
        try:
            committed = self.commit(ticket) if self.commit else False
        except ConnectionError:
            return self._refuse(reasons.COMMIT_UNREACHABLE)
        if not committed:
            return self._refuse(reasons.COMMIT_REJECTED)
        for check in self.checks:              # the device's own sensors and lists
            ok, why = check(params, self.sensors)
            if not ok:
                return self._refuse(why)
        self.executed.append({"action": action, "params": params, "ticket": t["ticket_id"], "t": now})
        return True, reasons.OK

    def _refuse(self, why: str) -> tuple[bool, str]:
        self.refused.append((why, self.safe_transition))
        self.state = self.safe_transition
        return False, why

    def restart(self) -> None:
        """Power loss and return: the used-ticket set comes back from the store."""
        self.store.power_loss()
        self.consumed = self.store.get("consumed", {})
        self.state = "ARMED"


RELEASE_ACTION = "response.release"


class EgressEndpoint(ActionEndpoint):
    """The DPU's egress to the user: bytes are held until a release ticket for exactly that response
    is admitted. Without a valid ticket the bytes never leave."""

    def __init__(self, name: str, clock, governor_keys: dict[str, VerifyKey], store: Store | None = None, safe_transition: str = "hold"):
        super().__init__(name, clock, governor_keys, store, safe_transition=safe_transition)
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
        a, b = sensors.get("nav_gnss"), sensors.get("nav_inertial")
        if a is None or b is None or abs(a[0] - b[0]) > 0.01 or abs(a[1] - b[1]) > 0.01:
            return False, reasons.ENDPOINT_SENSOR_CONFLICT
        return True, reasons.OK

    def not_protected(params: dict, sensors: dict) -> tuple[bool, str]:
        lst = sensors.get("lists", {}).get(protected_list_id)
        if lst is None or lst.get("stale"):
            return False, reasons.ENDPOINT_LIST_STALE
        target = (round(sensors["nav_gnss"][0], 3), round(sensors["nav_gnss"][1], 3))
        if target in {tuple(e) for e in lst["entries"]}:
            return False, reasons.ENDPOINT_TARGET_PROTECTED
        return True, reasons.OK

    return [nav_agree, not_protected]
