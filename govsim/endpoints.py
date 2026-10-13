"""Enforcement points and action endpoints.

Rack tier: the enforcement points are the switches the GPU's traffic already passes
(NVSwitch ports, PCIe switch ports and ACS, DPU flow tables, the storage path). The governor
is their only writer; a port or flow is open exactly when a matching, unexpired capability
exists. Integrated tier (a future vendor ask): descriptor-level checkers inside the GPU.

Action endpoints are the comparators in the devices that act. They hold the governor's
public key, their own used-ticket store, the current epoch, a heartbeat timer and their own
sensors, and they re-check at the moment of action.
"""
from __future__ import annotations

from typing import Any, Callable

from . import reasons
from .crypto import VerifyKey, canonical, digest, hmac_sha256, verify_object
from .store import Store

RACK_POINTS = ("nvswitch", "pcie", "dpu", "storage")
INTEGRATED_POINTS = ("copy_engine", "peer_mmu")
BRICKED = ("display", "jtag", "debug")


class Switch:
    """A governed switch: NVSwitch, PCIe switch, DPU flow table or the storage path.

    ``program`` is the only way to open a port or flow, and it verifies the governor's MAC.
    ``host_write`` models the host, the BMC or Fabric Manager trying to change the switch;
    at the rack tier the governor is the only master on the management bus, so it fails.
    """

    def __init__(self, kind: str, owner_chip_id: str, cap_key: bytes, log: Callable[[str, dict], None]):
        self.kind = kind
        self.owner = owner_chip_id
        self._cap_key = cap_key
        self.table: dict[tuple[str, str], dict] = {}     # (peer, direction) -> capability
        self.log = log
        self.refusals: list[dict] = []
        self.epoch_tag = ""

    def mac(self, cap: dict) -> str:
        body = {k: v for k, v in cap.items() if k != "mac"}
        return hmac_sha256(self._cap_key, canonical(body))

    def program(self, cap: dict) -> bool:
        if cap.get("point") != self.kind or cap.get("mac") != self.mac(cap):
            self.refusals.append({"why": reasons.EP_NO_CAPABILITY, "cap": cap})
            return False
        self.table[(cap["peer"], cap["direction"])] = dict(cap)
        return True

    def close_all(self) -> None:
        self.table.clear()

    def set_epoch(self, epoch_tag: str) -> None:
        self.epoch_tag = epoch_tag

    def host_write(self, peer: str, direction: str) -> bool:
        """The host cannot program the switch. Logged as an attempt."""
        self.log("switch.host_write_refused", {"switch": self.kind, "peer": peer})
        return False

    def pass_traffic(self, peer: str, direction: str, nbytes: int, now: float) -> tuple[bool, str]:
        cap = self.table.get((peer, direction)) or self.table.get((peer, "both"))
        if cap is None:
            return self._refuse(peer, direction, nbytes, reasons.EP_NO_CAPABILITY)
        if cap["expiry"] <= now:
            self.table.pop((cap["peer"], cap["direction"]), None)
            return self._refuse(peer, direction, nbytes, reasons.EP_EXPIRED)
        if cap["epoch_tag"] != self.epoch_tag:
            return self._refuse(peer, direction, nbytes, reasons.EP_STALE_EPOCH)
        if cap["budget"] < nbytes:
            return self._refuse(peer, direction, nbytes, reasons.EP_BUDGET_EXHAUSTED)
        cap["budget"] -= nbytes
        return True, reasons.OK

    def _refuse(self, peer: str, direction: str, nbytes: int, why: str) -> tuple[bool, str]:
        self.refusals.append({"switch": self.kind, "peer": peer, "direction": direction, "bytes": nbytes, "why": why})
        self.log("switch.refused", {"switch": self.kind, "peer": peer, "bytes": nbytes, "why": why})
        return False, why


class DescriptorChecker(Switch):
    """Integrated tier only: the same table at a copy engine or the peer MMU, inside the GPU."""


class ActionEndpoint:
    """The comparator in the device that acts (requirement R10, R11; hypotheses H0, H6)."""

    def __init__(self, name: str, clock, governor_pub: VerifyKey, store: Store | None = None,
                 safe_transition: str = "no_action", lists: dict[str, Any] | None = None,
                 sensors: dict[str, Any] | None = None, heartbeat_expiry_s: float = 5.0):
        self.name = name
        self.clock = clock
        self.governor_pub = governor_pub
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
        if not verify_object(signed_epoch, self.governor_pub) or signed_epoch["payload"].get("type") != "policy-epoch":
            return False
        self.epoch = signed_epoch["payload"]["epoch"]
        return True

    def heartbeat(self, now: float) -> None:
        self.hb_expiry = now + self.heartbeat_expiry_s

    # --- the comparator ---------------------------------------------------------
    def admit(self, ticket: dict | None, action: str, params: dict, now: float) -> tuple[bool, str]:
        if ticket is None:
            return False, reasons.TICKET_MISSING
        if not verify_object(ticket, self.governor_pub) or ticket["payload"].get("type") != "ticket":
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
