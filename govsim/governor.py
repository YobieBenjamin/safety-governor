"""The Safety Governor: one instance per GPU slot.

Everything in ``docs/01-architecture.md`` "Blocks" is here or in a module this one owns.
The mailbox is the only input from the host (``command``); the fabric is the only input from
other governors (``on_fabric``); the loop is sensed (``sense_loop``); time passes through
``tick``. Nothing else can change the governor's state.

Simplifications relative to the specification, each named where it applies:
- Signatures are Ed25519; wrapping a model key to an enclave is an HMAC-based stand-in.
- The COMMIT from an endpoint is authenticated by the ticket it carries rather than by an
  endpoint signature.
- Fabric round trips are synchronous function calls.
"""
from __future__ import annotations

import hashlib
import secrets
import threading
from collections import Counter
from typing import Any

from . import reasons
from .crypto import SigningKey, VerifyKey, canonical, digest, hmac_sha256, random_id, verify_any, verify_object
from .endpoints import BRICKED, DescriptorChecker, INTEGRATED_POINTS, RACK_POINTS, Switch
from .fuses import Fuses, PRODUCTION
from .ledger import Ledger
from .log import Log
from .policy import check_constraints, check_register, find_rule, policy_epoch, select_rule, verify_policy
from .root import SiliconRoot
from .store import Store

BOOT, HALTED_INITIAL, RUN, THROTTLE, HALT, SAFE = "BOOT", "HALTED_INITIAL", "RUN", "THROTTLE", "HALT", "SAFE"
RUNG_ORDER = {RUN: 0, THROTTLE: 1, HALT: 2, SAFE: 3}
TIERS = ("rack", "board", "integrated")
EPOCH_EXEMPT = {"ATTEST", "VERIFY_GPU", "VERIFY_HOST", "POLICY_PROPOSE", "POLICY_COMMIT", "HEARTBEAT", "CLEAR", "LOG_CHECKPOINT", "COUNTERS", "ALARM_RAISE", "HALT"}
TOKEN_TTL_S = 3600.0
TICKET_TTL_S = 300.0


class Governor:
    def __init__(self, name: str, clock, *, tier: str = "rack", fuses: Fuses | None = None, store: Store | None = None,
                 loader_digest: str | None = None, firmware_digest: str | None = None, firmware_version: int = 1):
        if tier not in TIERS:
            raise ValueError(tier)
        self.name, self.clock, self.tier = name, clock, tier
        self.fuses = fuses or Fuses()
        self.store = store or Store()
        self.firmware = (loader_digest or digest("loader-v1"), firmware_digest or digest("governor-fw-v1"), firmware_version)
        self.lock = threading.RLock()
        self.ops: Counter = Counter()
        self.gpu = None
        self.loop = None
        self.fabric = None
        self.endpoints: dict[str, Any] = {}
        self.reachable = True
        self.device_cert: dict | None = None
        self._boot()

    # ------------------------------------------------------------------ boot and restart
    def _boot(self) -> None:
        self.state = BOOT
        self.root = SiliconRoot(self.fuses, counter_start=int(self.store.get("counter", 0)))
        self.key = self.root.boot(*self.firmware)
        self.device_key = self.root.device_key
        self.alias_cert = self.device_key.sign({"type": "alias-cert", "chip_id": self.chip_id, "pub": self.key.public.hex,
                                                "meas1": self.root.meas1.value})
        self.log = Log(self.store, self.clock)
        self.ledger = Ledger(self.store, self.clock)
        self.alarms: dict[str, dict] = self.store.get("alarms", {})
        self.holds: dict[str, dict] = self.store.get("holds", {})
        self.mbox_seq: dict[str, int] = self.store.get("mbox_seq", {})
        self.meter: dict[str, dict] = self.store.get("meter", {})
        self.policy: dict | None = None
        self.epoch = ""
        self.staged: dict | None = None
        self.cause: str | None = None
        self.cause_entry: int | None = None
        self.rung_entered_at = 0.0
        self.levers = {"pwrbrk": False, "perst": False, "pwr_en": True}
        self.loop_switch_open = True
        self.hb_expiry = 0.0
        self.hb_last_seq = -1
        self.verified: dict[str, dict] = {}
        self.nonces: set[str] = set()
        self.fingerprint: str | None = None
        self.host_key: VerifyKey | None = None
        self.model_digest: str | None = None
        self.lists: dict[str, dict] = {}
        self.output_streams: dict[str, Any] = {}
        self.cap_key = self.root.derive(b"cap")
        self.switches: dict[str, Switch] = {}
        self.checkers: dict[str, DescriptorChecker] = {}
        self.roster: dict | None = None
        self.roster_keys: dict[str, VerifyKey] = {}
        self.pending_quotes: dict[str, dict[str, dict]] = {}
        self.fabric_seq = 0
        self.fabric_last_seq: dict[str, int] = {}
        self.seen_heartbeats: set[int] = set()
        self.acked_heads: dict[str, int] = {}      # my head -> my log size at that head, acknowledged by a neighbor
        self.approvals: dict[str, dict[str, dict]] = {}
        image = self.store.get("policy_image")
        if image:
            ok, why = self._accept_policy(image, at_boot=True)
            if not ok:
                self.log.append("policy.boot_load_failed", {"why": why})
        self.cause_opens_loop = False
        self._apply_rung(HALTED_INITIAL, opens_loop=True)
        self.log.append("boot", {"firmware": self.root.firmware_digest, "version": self.root.firmware_version, "tier": self.tier})

    def restart(self) -> None:
        """Power loss and return. Durable state survives; everything else is rebuilt."""
        gpu, loop, fabric, endpoints, cert = self.gpu, self.loop, self.fabric, self.endpoints, self.device_cert
        self.store.power_loss()
        self._boot()
        self.gpu, self.loop, self.fabric, self.endpoints, self.device_cert = gpu, loop, fabric, endpoints, cert
        if gpu is not None:
            self.attach_gpu(gpu)
        self._apply_rung(HALTED_INITIAL, opens_loop=True)

    @property
    def chip_id(self) -> str:
        return self.fuses.chip_id

    def provision(self, vendor_key: SigningKey, lifecycle: int = PRODUCTION) -> None:
        """Factory: the governor vendor certifies the DICE device identity; the lifecycle fuse advances."""
        self.device_cert = vendor_key.sign({"type": "governor-device-cert", "chip_id": self.chip_id, "pub": self.device_key.public.hex})
        self.fuses.advance_lifecycle(lifecycle)

    # ------------------------------------------------------------------ attachments
    def attach_gpu(self, gpu) -> None:
        self.gpu = gpu
        gpu.switches = {}
        gpu.checkers = {}
        gpu.output_hook = None
        if self.tier in ("rack", "integrated"):
            for kind in RACK_POINTS:
                sw = Switch(kind, self.chip_id, self.cap_key, self.log.append)
                sw.set_epoch(self.epoch[:8])
                self.switches[kind] = sw
                gpu.switches[kind] = sw
        if self.tier == "integrated":
            for kind in INTEGRATED_POINTS:
                ck = DescriptorChecker(kind, self.chip_id, self.cap_key, self.log.append)
                ck.set_epoch(self.epoch[:8])
                self.checkers[kind] = ck
                gpu.checkers[kind] = ck
            gpu.output_hook = self._fold_output
        gpu.policy_epoch_reported = self.epoch
        gpu.set_pwrbrk(self.levers["pwrbrk"])
        gpu.set_perst(self.levers["perst"])
        gpu.set_pwr_en(self.levers["pwr_en"])

    def join(self, loop, fabric) -> None:
        self.loop, self.fabric = loop, fabric
        loop.join(self)
        fabric.join(self)

    # ------------------------------------------------------------------ policy
    def _accept_policy(self, image: dict, at_boot: bool = False) -> tuple[bool, str]:
        ok, why = verify_policy(image, self.fuses.governance_key_hashes)
        if not ok:
            return False, why
        if image["version"] < self.fuses.policy_version or (self.policy and image["version"] <= self.policy["version"] and not at_boot):
            return False, reasons.POLICY_ROLLBACK
        if image["expires_at"] <= self.clock.now():
            return False, reasons.POLICY_EXPIRED
        missing = check_register(image)
        if missing:
            return False, reasons.POLICY_REGISTER_INCOMPLETE
        old_epoch = self.epoch
        self.policy = image
        self.epoch = policy_epoch(image)
        self.fuses.bump_policy(image["version"])
        self.store.data["policy_image"] = image
        for sw in list(self.switches.values()) + list(self.checkers.values()):
            sw.set_epoch(self.epoch[:8])
        if not at_boot and old_epoch and old_epoch != self.epoch:
            self.holds.clear()          # a hold carries the epoch that parked it; the new rules re-decide
        self.store.save()
        if self.gpu is not None:
            self.gpu.policy_epoch_reported = self.epoch
        return True, reasons.OK

    def signed_epoch(self) -> dict:
        return self.key.sign({"type": "policy-epoch", "epoch": self.epoch, "governor": self.chip_id, "issued_at": self.clock.now()})

    def install_list(self, list_id: str, signed_list: dict) -> bool:
        """A signed list (protected sites, sanctions) the rules compare against."""
        if not self.policy:
            return False
        keys = {VerifyKey.from_hex(h).key_id: VerifyKey.from_hex(h) for h in self.policy["governance_keys"]}
        if verify_any(signed_list, keys) is None or signed_list["payload"].get("list_id") != list_id:
            return False
        p = signed_list["payload"]
        self.lists[list_id] = {"entries": p["entries"], "stale": p["expires_at"] <= self.clock.now(), "expires_at": p["expires_at"]}
        return True

    # ------------------------------------------------------------------ keys of the parties
    def _keys(self, cls: str, rule_id: str | None = None) -> dict[str, VerifyKey]:
        if not self.policy:
            return {}
        p = self.policy
        if cls == "authority":
            hexes = [p["heartbeat_key"]]
        elif cls == "governance":
            hexes = p["governance_keys"]
        elif cls == "approver":
            hexes = p["approver_keys"].get(rule_id or "", [])
        elif cls == "publisher":
            hexes = p["publisher_keys"]
        elif cls == "observer":
            hexes = p["observer_keys"]
        elif cls == "endpoint":
            hexes = [e["pubkey"] for e in p["endpoints"]]
        elif cls == "host":
            return {self.host_key.key_id: self.host_key} if self.host_key else {}
        else:
            hexes = []
        return {VerifyKey.from_hex(h).key_id: VerifyKey.from_hex(h) for h in hexes}

    def _check_signed(self, env: dict, cls: str, rule_id: str | None = None, epoch_exempt: bool = False) -> tuple[bool, str]:
        key = verify_any(env, self._keys(cls, rule_id))
        if key is None:
            return False, reasons.MBOX_BAD_SIGNATURE
        p = env["payload"]
        seq = int(p.get("seq", -1))
        if seq <= self.mbox_seq.get(key.key_id, -1):
            return False, reasons.MBOX_BAD_SEQUENCE
        if not epoch_exempt and p.get("epoch") != self.epoch:
            return False, reasons.POLICY_STALE_EPOCH
        self.mbox_seq[key.key_id] = seq
        self.store.save()
        return True, reasons.OK

    # ------------------------------------------------------------------ the mailbox
    def command(self, cmd: str, body: dict | None = None, env: dict | None = None) -> dict:
        """The host's only way in. Returns ``{"ok": bool, "why": reason, ...}``."""
        with self.lock:
            body = body or {}
            self.ops["mailbox"] += 1
            if self.fuses.zeroized:
                return {"ok": False, "why": reasons.TAMPER_ZEROIZED}
            handler = getattr(self, "_cmd_" + cmd.lower(), None)
            if handler is None:
                return {"ok": False, "why": reasons.MBOX_UNKNOWN_COMMAND}
            if cmd not in EPOCH_EXEMPT and cmd not in ("APPROVE", "COMMIT", "ALARM_CLEAR") and self.state != RUN:
                return {"ok": False, "why": reasons.MBOX_NOT_RUNNING}
            return handler(body, env)

    def _cmd_attest(self, body, env):
        nonce = body.get("nonce", "")
        return {"ok": True, "why": reasons.OK, "quote": self.root.quote(nonce, {"epoch": self.epoch, "state": self.state}),
                "device_cert": self.device_cert, "alias_cert": self.alias_cert}

    def nonce(self) -> str:
        n = random_id(16)
        self.nonces.add(n)
        return n

    def _reference(self, device_class: str) -> list[dict]:
        return [r for r in (self.policy or {}).get("reference_values", []) if r["device_class"] == device_class]

    def _cmd_verify_gpu(self, body, env):
        """The GPU's confidential-computing report, verified locally against pinned reference values."""
        self.ops["attest"] += 1
        report, cert = body.get("report"), body.get("cert")
        refs = self._reference("gpu")
        vendor_keys = {VerifyKey.from_hex(r["vendor_key"]).key_id: VerifyKey.from_hex(r["vendor_key"]) for r in refs}
        if not cert or verify_any(cert, vendor_keys) is None:
            return self._deny("verify_gpu", reasons.ATTEST_UNKNOWN_DEVICE)
        dev = VerifyKey.from_hex(cert["payload"]["pub"])
        if not report or not verify_object(report, dev) or report["payload"].get("chip_id") != cert["payload"]["chip_id"]:
            return self._deny("verify_gpu", reasons.ATTEST_BAD_SIGNATURE)
        p = report["payload"]
        if p.get("nonce") not in self.nonces:
            return self._deny("verify_gpu", reasons.ATTEST_BAD_NONCE)
        self.nonces.discard(p["nonce"])
        now = self.clock.now()
        if not any(r["firmware_digest"] == p.get("firmware_digest") and r["valid_until"] > now for r in refs):
            return self._deny("verify_gpu", reasons.ATTEST_FIRMWARE_NOT_IN_REFERENCE)
        if p.get("open_paths"):
            return self._deny("verify_gpu", reasons.ATTEST_PATH_OPEN)
        if self.tier == "integrated" and self.model_digest and p.get("manifest_digest") != self.model_digest:
            return self._deny("verify_gpu", reasons.ATTEST_BAD_SIGNATURE + ".manifest_mismatch")
        self.verified["gpu"] = {"chip_id": p["chip_id"], "firmware_digest": p["firmware_digest"], "expires_at": now + TOKEN_TTL_S}
        self.log.append("verify.gpu", {"chip_id": p["chip_id"], "firmware": p["firmware_digest"]})
        return {"ok": True, "why": reasons.OK}

    def _cmd_verify_host(self, body, env):
        self.ops["attest"] += 1
        report, cert = body.get("report"), body.get("cert")
        refs = self._reference("host")
        vendor_keys = {VerifyKey.from_hex(r["vendor_key"]).key_id: VerifyKey.from_hex(r["vendor_key"]) for r in refs}
        if not cert or verify_any(cert, vendor_keys) is None:
            return self._deny("verify_host", reasons.ATTEST_UNKNOWN_DEVICE)
        enclave = VerifyKey.from_hex(cert["payload"]["pub"])
        if not report or not verify_object(report, enclave):
            return self._deny("verify_host", reasons.ATTEST_BAD_SIGNATURE)
        p = report["payload"]
        if p.get("nonce") not in self.nonces:
            return self._deny("verify_host", reasons.ATTEST_BAD_NONCE)
        self.nonces.discard(p["nonce"])
        now = self.clock.now()
        if not any(r["firmware_digest"] == p.get("firmware_digest") and r["valid_until"] > now for r in refs):
            return self._deny("verify_host", reasons.ATTEST_FIRMWARE_NOT_IN_REFERENCE)
        self.verified["host"] = {"firmware_digest": p["firmware_digest"], "expires_at": now + TOKEN_TTL_S}
        self.host_key = enclave
        self.log.append("verify.host", {"firmware": p["firmware_digest"]})
        return {"ok": True, "why": reasons.OK}

    def _attested(self) -> bool:
        now = self.clock.now()
        return all(k in self.verified and self.verified[k]["expires_at"] > now for k in ("gpu", "host"))

    def _cmd_begin_model(self, body, env):
        """The verified loader presents a publisher-signed manifest; the governor releases the key."""
        if not self._attested():
            return self._deny("begin_model", reasons.GATE_NOT_ATTESTED)
        ok, why = self._check_signed(env, "host")
        if not ok:
            return self._deny("begin_model", why)
        manifest = env["payload"].get("manifest")
        if not manifest or verify_any(manifest, self._keys("publisher")) is None:
            return self._deny("begin_model", reasons.MBOX_BAD_SIGNATURE + ".manifest")
        model_digest = manifest["payload"]["model_digest"]
        self.model_digest = model_digest
        self.fingerprint = digest([self.verified["gpu"]["firmware_digest"], self.verified["host"]["firmware_digest"], model_digest, self.epoch])
        wrapped = hmac_sha256(self.root.derive(b"wrap"), bytes.fromhex(self.host_key.hex) + model_digest.encode())
        self.meter.setdefault(model_digest, {"tokens": 0, "cycles": 0, "bytes_in": 0, "bytes_out": 0})
        self.store.save()
        self.log.append("model.begin", {"model": model_digest, "fingerprint": self.fingerprint})
        return {"ok": True, "why": reasons.OK, "wrapped_key": wrapped, "fingerprint": self.fingerprint, "token": self.workload_token()}

    def workload_token(self) -> dict:
        return self.key.sign({"type": "workload-token", "fingerprint": self.fingerprint, "expires_at": self.clock.now() + TOKEN_TTL_S})

    # ------------------------------------------------------------------ the gate core
    def _deny(self, what: str, why: str, **extra) -> dict:
        self.log.append(f"deny.{what}", {"why": why, **extra})
        return {"ok": False, "why": why, **extra}

    def _cmd_request(self, body, env):
        """Typed request from the broker. Four questions, in order, failing closed."""
        self.ops["action"] += 1
        now = self.clock.now()
        req = body
        action, params = req.get("action"), req.get("params", {})
        token = req.get("measurement_token")
        if not token or not verify_object(token, self.key.public) or token["payload"].get("type") != "workload-token" \
                or token["payload"]["expires_at"] <= now or token["payload"]["fingerprint"] != self.fingerprint:
            return self._deny("request", reasons.GATE_NOT_ATTESTED)
        fp = token["payload"]["fingerprint"]
        rhash = digest([req.get("request_id"), fp, action, params])
        if self.ledger.seen(rhash):
            return self._deny("request", reasons.GATE_REPLAY)
        if self.alarms:
            return self._deny("request", reasons.GATE_ALARM, request_hash=rhash)
        rule, why = select_rule(self.policy, fp, action, params, self.lists)   # requester labels never reach this call (H4)
        if rule is None:
            return self._deny("request", why, request_hash=rhash)
        req_mode = rule["requirement"]["mode"]
        if req_mode == "observer":
            ok, why = self._witnessed(rule, rhash, req.get("witnesses", []), now)
            if not ok:
                return self._deny("request", why, request_hash=rhash)
        if rule.get("rate") and not self.ledger.rate_ok(f"rate|{fp}|{action}", rule["rate"]["max"], rule["rate"]["window_s"], now):
            return self._deny("request", reasons.GATE_RATE, request_hash=rhash)
        reservation = None
        if rule.get("budget"):
            b = rule["budget"]
            amount = params.get(b["param"])
            if not isinstance(amount, (int, float)) or amount < 0:
                return self._deny("request", reasons.GATE_BUDGET + ".amount_invalid", request_hash=rhash)
            ok, rid, why = self._reserve(b["key"], amount, b["limit"], b["window_s"], now, TICKET_TTL_S + rule.get("delay_s", 0.0))
            if not ok:
                return self._deny("request", why, request_hash=rhash)
            reservation = {"key": b["key"], "rid": rid, "owner": self.policy["budget_owners"].get(b["key"], self.chip_id)}
        self.ledger.mark(rhash, now)
        if req_mode == "human":
            hold_id = random_id(8)
            self.holds[hold_id] = {"request_hash": rhash, "action": action, "params": params, "fingerprint": fp, "rule": rule["id"],
                                   "reservation": reservation, "created_at": now, "epoch": self.epoch}
            self.store.save()
            self.log.append("gate.hold", {"hold_id": hold_id, "request_hash": rhash, "rule": rule["id"]})
            return {"ok": False, "why": reasons.GATE_HELD, "hold_id": hold_id, "request_hash": rhash}
        ticket = self._mint(rhash, action, params, fp, rule, reservation, now)
        return {"ok": True, "why": reasons.OK, "ticket": ticket, "request_hash": rhash}

    def _witnessed(self, rule: dict, rhash: str, witnesses: list[dict], now: float) -> tuple[bool, str]:
        keys = self._keys("observer")
        for w in witnesses:
            key = verify_any(w, keys)
            if key is None:
                continue
            p = w["payload"]
            if p.get("request_hash") != rhash:
                continue
            if p.get("expires_at", 0) <= now:
                return False, reasons.GATE_WITNESS_STALE
            if p.get("risk", 1.0) > rule["requirement"]["max_risk"]:
                return False, reasons.GATE_WITNESS_RISK
            return True, reasons.OK
        return False, reasons.GATE_WITNESS_MISSING

    def _reserve(self, key: str, amount: float, limit: float, window_s: float, now: float, ttl: float) -> tuple[bool, str | None, str]:
        owner = self.policy["budget_owners"].get(key, self.chip_id)
        if owner == self.chip_id:
            rid = self.ledger.reserve(key, amount, limit, window_s, now, ttl)
            return (True, rid, reasons.OK) if rid else (False, None, reasons.GATE_BUDGET)
        if self.fabric is None:
            return False, None, reasons.GATE_BUDGET_OWNER_UNREACHABLE
        res = self.fabric_send("RESERVE", {"key": key, "amount": amount, "limit": limit, "window_s": window_s, "ttl": ttl}, to=owner)
        for _, r in res:
            if isinstance(r, dict) and r.get("ok"):
                return True, r["rid"], reasons.OK
            if isinstance(r, dict) and r.get("why") == reasons.GATE_BUDGET:
                return False, None, reasons.GATE_BUDGET
        return False, None, reasons.GATE_BUDGET_OWNER_UNREACHABLE

    def _mint(self, rhash: str, action: str, params: dict, fp: str, rule: dict, reservation: dict | None, now: float) -> dict:
        self.ops["ticket"] += 1
        t = {"type": "ticket", "ticket_id": random_id(16), "request_hash": rhash, "action": action, "params_digest": digest(params),
             "measurement": fp, "rule": rule["id"], "policy_epoch": self.epoch, "endpoint": rule.get("endpoint"),
             "budget_key": reservation["key"] if reservation else None, "reservation": reservation["rid"] if reservation else None,
             "budget_owner": reservation["owner"] if reservation else None,
             "issued_at": now, "valid_from": now + rule.get("delay_s", 0.0), "expires_at": now + rule.get("delay_s", 0.0) + TICKET_TTL_S}
        ticket = self.key.sign(t)
        self.log.append("gate.ticket", {"ticket_id": t["ticket_id"], "request_hash": rhash, "rule": rule["id"], "epoch": self.epoch})
        return ticket

    def _cmd_approve(self, body, env):
        """An approver releases a hold. Quorum, a written reason, a latency floor, a log line."""
        if env is None:
            return self._deny("approve", reasons.APPROVE_BAD_SIGNATURE)
        hold_id = env["payload"].get("hold_id")
        hold = self.holds.get(hold_id)
        if hold is None:
            return self._deny("approve", reasons.APPROVE_UNKNOWN_HOLD)
        ok, why = self._check_signed(env, "approver", rule_id=hold["rule"])
        if not ok:
            return self._deny("approve", reasons.APPROVE_BAD_SIGNATURE if why == reasons.MBOX_BAD_SIGNATURE else why)
        p = env["payload"]
        if p.get("request_hash") != hold["request_hash"]:
            return self._deny("approve", reasons.APPROVE_BAD_SIGNATURE + ".request_mismatch")
        if not str(p.get("reason", "")).strip():
            return self._deny("approve", reasons.APPROVE_NO_REASON)
        now = self.clock.now()
        self.approvals.setdefault(hold_id, {})[env["signer"]] = {"t": now, "reason": p["reason"]}
        self.log.append("approve.signature", {"hold_id": hold_id, "approver": env["signer"], "reason": p["reason"]})
        rule = next(r for r in self.policy["rules"] if r["id"] == hold["rule"])
        quorum = max(1, rule["requirement"].get("approvers_quorum", 1))
        if len(self.approvals[hold_id]) < quorum:
            return {"ok": False, "why": reasons.APPROVE_QUORUM_PENDING, "have": len(self.approvals[hold_id]), "need": quorum}
        floor = max(10.0, float(self.policy.get("override_floor_s", 60.0)))
        if now < hold["created_at"] + floor:
            return {"ok": False, "why": reasons.APPROVE_TOO_FAST, "earliest": hold["created_at"] + floor}
        ticket = self._mint(hold["request_hash"], hold["action"], hold["params"], hold["fingerprint"], rule, hold["reservation"], now)
        self.holds.pop(hold_id)
        self.store.save()
        self.log.append("approve.released", {"hold_id": hold_id, "approvers": sorted(self.approvals[hold_id]), "latency_s": now - hold["created_at"]})
        return {"ok": True, "why": reasons.OK, "ticket": ticket}

    def commit_from_endpoint(self, ticket: dict) -> bool:
        """The endpoint's COMMIT. Unreachable governor means the endpoint refuses."""
        with self.lock:
            if not self.reachable:
                raise ConnectionError(reasons.COMMIT_UNREACHABLE)
            if self.state != RUN:
                self.log.append("gate.commit_rejected", {"why": reasons.MBOX_NOT_RUNNING})
                return False
            if not verify_object(ticket, self.key.public):
                self.log.append("gate.commit_rejected", {"why": reasons.TICKET_BAD_SIGNATURE})
                return False
            t = ticket["payload"]
            if t["policy_epoch"] != self.epoch:
                self.log.append("gate.commit_rejected", {"why": reasons.TICKET_STALE_EPOCH})
                return False
            ok = True
            if t.get("reservation"):
                owner = t.get("budget_owner") or self.chip_id
                if owner == self.chip_id:
                    ok = self.ledger.commit(t["budget_key"], t["reservation"], self.clock.now())
                else:
                    res = self.fabric_send("COMMIT", {"key": t["budget_key"], "rid": t["reservation"]}, to=owner) if self.fabric else []
                    ok = any(isinstance(r, dict) and r.get("ok") for _, r in res)
            self.log.append("gate.commit" if ok else "gate.commit_rejected", {"ticket_id": t["ticket_id"]})
            return ok

    # ------------------------------------------------------------------ alarms
    def raise_alarm(self, code: str, source: str) -> None:
        """Anyone may raise. The bits are sticky."""
        with self.lock:
            if code not in self.alarms:
                self.alarms[code] = {"source": source, "t": self.clock.now()}
                self.store.save()
                self.log.append("alarm.raised", {"code": code, "source": source})
                if self.fabric is not None and source != "fabric":
                    self.fabric_send("ALARM", {"code": code, "origin": self.chip_id})

    def _cmd_alarm_raise(self, body, env):
        self.raise_alarm(body.get("code", "alarm.unspecified"), body.get("source", "host"))
        return {"ok": True, "why": reasons.OK}

    def _cmd_alarm_clear(self, body, env):
        if env is None:
            return self._deny("alarm_clear", reasons.ALARM_CLEAR_UNAUTHORIZED)
        ok, why = self._check_signed(env, "approver", rule_id="alarms", epoch_exempt=True)
        if not ok:
            return self._deny("alarm_clear", reasons.ALARM_CLEAR_UNAUTHORIZED)
        code = env["payload"].get("code")
        if code in self.alarms:
            self.alarms.pop(code)
            self.store.save()
            self.log.append("alarm.cleared", {"code": code, "by": env["signer"]})
        return {"ok": True, "why": reasons.OK}

    # ------------------------------------------------------------------ output and meter
    def _fold_output(self, stream: str, data: bytes) -> None:
        self.ops["output_bytes"] += len(data)
        self.output_streams.setdefault(stream, hashlib.sha256()).update(data)

    def _cmd_sign_output(self, body, env):
        """Device-provenance record. Integrated tier: over the inline hash; rack tier: over what the verified runtime presents."""
        self.ops["sign"] += 1
        ok, why = self._check_signed(env, "host")
        if not ok:
            return self._deny("sign_output", why)
        p = env["payload"]
        stream = p.get("stream")
        now = self.clock.now()
        rule = find_rule(self.policy, self.fingerprint or "", "model.output") if self.fingerprint else None
        if rule and rule.get("output_budget"):
            ob = rule["output_budget"]
            nbytes = len(bytes.fromhex(p.get("data_hex", "")))
            if not self.ledger.rate_ok(f"out-q|{self.fingerprint}", ob["queries"], ob["window_s"], now):
                self._output_tripped()
                return self._deny("sign_output", reasons.GATE_OUTPUT_BUDGET)
            rid = self.ledger.reserve(f"out-b|{self.fingerprint}", nbytes, ob["bytes"], ob["window_s"], now, 1.0)
            if rid is None:
                self._output_tripped()
                return self._deny("sign_output", reasons.GATE_OUTPUT_BUDGET)
            self.ledger.commit(f"out-b|{self.fingerprint}", rid, now)
        if self.tier == "integrated":
            h = self.output_streams.pop(stream, hashlib.sha256()).hexdigest()
            inline = True
        else:
            h = hashlib.sha256(bytes.fromhex(p.get("data_hex", ""))).hexdigest()
            inline = False
        counters = self.meter.get(self.model_digest or "", {})
        record = self.key.sign({"type": "device-provenance", "chip_id": self.chip_id, "fw_measurement": self.root.meas1.value,
                                "model_digest": self.model_digest, "policy_epoch": self.epoch,
                                "roster_id": self.roster["roster_id"] if self.roster else None,
                                "prompt_hash": p.get("claimed_prompt_hash"), "prompt_hash_verified": False,
                                "output_hash": h, "output_hash_inline": inline, "nonce": p.get("nonce"), "time": now,
                                "counters": dict(counters)})
        self.log.append("output.signed", {"stream": stream, "inline": inline})
        return {"ok": True, "why": reasons.OK, "record": record}

    def _output_tripped(self) -> None:
        self.raise_alarm(reasons.GATE_OUTPUT_BUDGET, "governor")
        if self.gpu is not None:
            self.gpu.output_blocked = True
        self.enter_safe_mode(reasons.GATE_OUTPUT_BUDGET, rung=THROTTLE)

    def read_meter(self) -> None:
        """Out-of-band read of the GPU's counters into the meter slot."""
        if self.gpu is None or self.model_digest is None:
            return
        slot = self.meter.setdefault(self.model_digest, {"tokens": 0, "cycles": 0, "bytes_in": 0, "bytes_out": 0})
        slot.update({"tokens": self.gpu.tokens, "cycles": self.gpu.cycles, "bytes_in": self.gpu.bytes_in, "bytes_out": self.gpu.bytes_out})
        self.store.save()

    def _cmd_counters(self, body, env):
        return {"ok": True, "why": reasons.OK, "meter": {k: dict(v) for k, v in self.meter.items()}}

    def _cmd_log_checkpoint(self, body, env):
        return {"ok": True, "why": reasons.OK, "checkpoint": self.log.checkpoint(self.key, self.chip_id)}

    # ------------------------------------------------------------------ capabilities and switches
    def _capability(self, point: str, peer: str, direction: str, budget: int, expiry: float) -> dict:
        cap = {"point": point, "peer": peer, "direction": direction, "budget": budget, "expiry": expiry, "epoch_tag": self.epoch[:8]}
        cap["mac"] = hmac_sha256(self.cap_key, canonical(cap))
        return cap

    def open_ports_for_roster(self, budget: int = 1 << 40) -> int:
        """Program every governed switch for exactly the roster's members. Returns entries written."""
        if self.roster is None:
            return 0
        n = 0
        expiry = self.roster["expires_at"]
        peers = [m["gpu_chip_id"] for m in self.roster["members"] if m["chip_id"] != self.chip_id]
        for kind, sw in list(self.switches.items()) + list(self.checkers.items()):
            sw.close_all()
            if kind in ("nvswitch", "dpu", "peer_mmu"):
                for peer in peers:
                    n += sw.program(self._capability(kind, peer, "both", budget, expiry))
            elif kind in ("pcie", "copy_engine"):
                if "host" in self.verified:
                    n += sw.program(self._capability(kind, "host", "both", budget, expiry))
                for peer in peers:
                    n += sw.program(self._capability(kind, peer, "both", budget, expiry))
            elif kind == "storage":
                if self.model_digest:
                    n += sw.program(self._capability(kind, self.model_digest, "in", budget, expiry))
        self.ops["switch_program"] += n
        return n

    def close_ports(self) -> None:
        for sw in list(self.switches.values()) + list(self.checkers.values()):
            sw.close_all()

    def _cmd_cap_request(self, body, env):
        """The driver asks for a port or flow to a peer. Only roster members, only under this epoch."""
        if self.roster is None:
            return self._deny("cap_request", reasons.EP_NOT_ON_ROSTER)
        peer = body.get("peer")
        if peer != "host" and peer not in {m["gpu_chip_id"] for m in self.roster["members"]}:
            return self._deny("cap_request", reasons.EP_NOT_ON_ROSTER, peer=peer)
        kind = body.get("point")
        sw = self.switches.get(kind) or self.checkers.get(kind)
        if sw is None:
            return self._deny("cap_request", reasons.EP_UNCHECKED, point=kind)
        cap = self._capability(kind, peer, body.get("direction", "both"), int(body.get("budget", 1 << 30)),
                               min(self.roster["expires_at"], self.clock.now() + float(body.get("ttl", 3600))))
        return {"ok": sw.program(cap), "why": reasons.OK, "capability": cap}

    # ------------------------------------------------------------------ heartbeat, levers, safe mode
    def _cmd_heartbeat(self, body, env):
        return self._heartbeat(env, hops=0)

    def _heartbeat(self, env: dict | None, hops: int) -> dict:
        if env is None or verify_any(env, self._keys("authority")) is None:
            return self._deny("heartbeat", reasons.HEARTBEAT_BAD_SIGNATURE)
        p = env["payload"]
        now = self.clock.now()
        if int(p.get("seq", -1)) <= self.hb_last_seq:
            return self._deny("heartbeat", reasons.HEARTBEAT_REPLAY)
        if p.get("epoch") not in (self.epoch, policy_epoch(self.staged) if self.staged else None):
            return self._deny("heartbeat", reasons.POLICY_STALE_EPOCH)
        if p.get("window_end", 0) <= now or p.get("window_start", 0) > now:
            return self._deny("heartbeat", reasons.HEARTBEAT_EXPIRED)
        if hops > self.policy["fabric"]["max_hops"]:
            return self._deny("heartbeat", reasons.FABRIC_TOO_MANY_HOPS)
        self.hb_last_seq = int(p["seq"])
        self.hb_expiry = float(p["window_end"])
        self.ops["heartbeat"] += 1
        if self.state == HALTED_INITIAL and self.cause is None:
            self.loop_switch_open = False          # armed: the switch closes; RUN waits for loop current
            self._try_run()
        for ep in self.endpoints.values():
            ep.heartbeat(now)
        if self.fabric is not None and self.hb_last_seq not in self.seen_heartbeats:
            self.seen_heartbeats.add(self.hb_last_seq)
            self.fabric_send("HEARTBEAT", {"authority": env, "hops": hops + 1})
        return {"ok": True, "why": reasons.OK}

    def _cmd_halt(self, body, env):
        ok, why = self._check_signed(env, "authority", epoch_exempt=True)
        if not ok:
            return self._deny("halt", why)
        rung = env["payload"].get("rung", HALT)
        self.enter_safe_mode(reasons.HALT_COMMANDED, rung=rung)
        return {"ok": True, "why": reasons.OK}

    def enter_safe_mode(self, cause: str, rung: str | None = None) -> None:
        """Move to the cause's rung. Causes that open the loop halt the whole domain; the
        others (a lost heartbeat, a tripped output budget, an epoch straggler) are local."""
        with self.lock:
            sm = (self.policy or {}).get("safe_mode", {})
            rung = rung or sm.get("causes", {}).get(cause, sm.get("default_rung", THROTTLE))
            opens = cause in sm.get("opens_loop", [reasons.LOOP_OPEN, reasons.LOOP_BROKEN, reasons.TAMPER, reasons.HALT_COMMANDED])
            current = RUNG_ORDER.get(self.state, 0)
            if self.cause is None or RUNG_ORDER[rung] > current or (opens and not self.cause_opens_loop):
                self.cause = cause
                self.cause_opens_loop = opens or self.cause_opens_loop
                head = self.log.append("halt.cause", {"cause": cause, "rung": rung})
                self.cause_entry = self.log.size - 1
                self.rung_entered_at = self.clock.now()
                self._apply_rung(rung, opens_loop=self.cause_opens_loop)
                if self.fabric is not None:
                    self.fabric_send("HALT_CAUSE", {"cause": cause, "head": head})

    def _apply_rung(self, rung: str, opens_loop: bool = False) -> None:
        self.state = rung
        g = self.gpu
        if rung == RUN:
            self.loop_switch_open = False
            self.levers = {"pwrbrk": False, "perst": False, "pwr_en": True}
        elif rung == HALTED_INITIAL:
            self.loop_switch_open = True
            self.levers = {"pwrbrk": True, "perst": False, "pwr_en": True}
            self.close_ports()
        elif rung == THROTTLE:
            self.levers = {"pwrbrk": True, "perst": False, "pwr_en": True}
            self.close_ports()
        elif rung == HALT:
            self.loop_switch_open = self.loop_switch_open or opens_loop
            self.levers = {"pwrbrk": True, "perst": True, "pwr_en": True}
            self.close_ports()
        elif rung == SAFE:
            self.loop_switch_open = self.loop_switch_open or opens_loop
            self.levers = {"pwrbrk": True, "perst": True, "pwr_en": False}
            self.close_ports()
        if g is not None:
            g.set_pwrbrk(self.levers["pwrbrk"])
            g.set_perst(self.levers["perst"])
            g.set_pwr_en(self.levers["pwr_en"])
        if rung == RUN and self.roster is not None:
            self.open_ports_for_roster()

    def _try_run(self) -> None:
        """HALTED_INITIAL -> RUN when there is no cause, a live heartbeat, and loop current."""
        if self.state == HALTED_INITIAL and self.cause is None and self.hb_expiry > self.clock.now() \
                and not self.loop_switch_open and (self.loop is None or self.loop.current()):
            self._apply_rung(RUN)

    def sense_loop(self) -> None:
        if self.loop is None:
            return
        if not self.loop.current() and self.state in (RUN, THROTTLE):
            self.enter_safe_mode(reasons.LOOP_BROKEN if not self.loop.wire_intact else reasons.LOOP_OPEN, rung=HALT)
        elif self.state == HALTED_INITIAL:
            self._try_run()

    def tick(self) -> None:
        """Time passes: heartbeat expiry, rung escalation, reservation expiry."""
        with self.lock:
            now = self.clock.now()
            if self.state == RUN and now > self.hb_expiry:
                self.enter_safe_mode(reasons.HEARTBEAT_LOST)
            sm = (self.policy or {}).get("safe_mode", {})
            if self.state == THROTTLE and self.cause and now - self.rung_entered_at >= sm.get("T_throttle_s", 30.0):
                self.rung_entered_at = now
                self.log.append("halt.escalate", {"to": HALT, "cause": self.cause})
                self.cause_entry = self.log.size - 1
                self._apply_rung(HALT, opens_loop=self.cause_opens_loop)
            elif self.state == HALT and self.cause and now - self.rung_entered_at >= sm.get("T_halt_s", 300.0):
                self.rung_entered_at = now
                self.log.append("halt.escalate", {"to": SAFE, "cause": self.cause})
                self.cause_entry = self.log.size - 1
                self._apply_rung(SAFE, opens_loop=self.cause_opens_loop)
            self.sense_loop()

    def _cmd_clear(self, body, env):
        """Only the authority clears, only after the cause is logged and a neighbor has the log."""
        ok, why = self._check_signed(env, "authority", epoch_exempt=True)
        if not ok:
            return self._deny("clear", reasons.CLEAR_UNAUTHORIZED)
        if self.cause is None:
            return {"ok": True, "why": reasons.OK}
        if self.cause_entry is None or not self.log.has("halt.cause", cause=self.cause) and not self.log.has("halt.escalate", cause=self.cause):
            return self._deny("clear", reasons.CLEAR_CAUSE_NOT_LOGGED)
        if self.fabric is not None and len(self.fabric.members) > 1 and not any(size > self.cause_entry for size in self.acked_heads.values()):
            return self._deny("clear", reasons.CLEAR_NO_NEIGHBOR_ACK)
        self.log.append("halt.cleared", {"cause": self.cause, "by": env["signer"]})
        self.cause, self.cause_entry, self.cause_opens_loop = None, None, False
        if self.gpu is not None:
            self.gpu.output_blocked = False
        self._apply_rung(HALTED_INITIAL)
        self.loop_switch_open = False           # armed; RUN follows when the whole loop is closed and the heartbeat is live
        self._try_run()
        return {"ok": True, "why": reasons.OK}

    # ------------------------------------------------------------------ policy change
    def _cmd_policy_propose(self, body, env):
        image = body.get("image")
        if not image:
            return self._deny("policy_propose", reasons.POLICY_QUORUM)
        ok, why = verify_policy(image, self.fuses.governance_key_hashes)
        if not ok:
            return self._deny("policy_propose", why)
        if self.policy and image["version"] <= self.policy["version"]:
            return self._deny("policy_propose", reasons.POLICY_ROLLBACK)
        if check_register(image):
            return self._deny("policy_propose", reasons.POLICY_REGISTER_INCOMPLETE)
        self.staged = image
        self.log.append("policy.staged", {"epoch": policy_epoch(image), "version": image["version"]})
        return {"ok": True, "why": reasons.OK, "ack": self.key.sign({"type": "epoch-ack", "epoch": policy_epoch(image), "chip_id": self.chip_id})}

    def _cmd_policy_commit(self, body, env):
        if self.staged is None or policy_epoch(self.staged) != body.get("epoch"):
            return self._deny("policy_commit", reasons.POLICY_NOT_STAGED)
        old = self.epoch
        ok, why = self._accept_policy(self.staged)
        self.staged = None
        if not ok:
            return self._deny("policy_commit", why)
        self.log.append("policy.committed", {"old": old, "new": self.epoch})
        for ep in self.endpoints.values():
            ep.set_epoch(self.signed_epoch())
        if self.roster is not None and self.state == RUN:
            self.open_ports_for_roster()
        return {"ok": True, "why": reasons.OK, "epoch": self.epoch}

    def load_policy(self, image: dict) -> tuple[bool, str]:
        """Provisioning-time load (no epoch change ceremony). Same checks."""
        ok, why = self._accept_policy(image, at_boot=True)
        if ok:
            self.log.append("policy.loaded", {"epoch": self.epoch, "version": image["version"]})
            for ep in self.endpoints.values():
                ep.set_epoch(self.signed_epoch())
        return ok, why

    # ------------------------------------------------------------------ lifecycle and tamper
    def debug_access(self) -> tuple[bool, str]:
        ok, why = self.fuses.debug_access()
        self.log.append("debug.granted" if ok else "debug.refused", {"lifecycle": self.fuses.lifecycle})
        return ok, why

    def tamper_event(self, kind: str = "mesh") -> None:
        with self.lock:
            self.log.append("tamper", {"kind": kind})
            self.cause, self.cause_opens_loop = reasons.TAMPER, True
            self._apply_rung(SAFE, opens_loop=True)
            self.root.zeroize()
            self.close_ports()

    # ------------------------------------------------------------------ the fabric
    def fabric_send(self, mtype: str, body: dict, to: str | None = None) -> list:
        if self.fabric is None or self.fuses.zeroized:
            return []
        self.fabric_seq += 1
        self.ops["fabric_msg"] += 1
        msg = self.key.sign({"type": mtype, "from": self.chip_id, "seq": self.fabric_seq, "epoch": self.epoch, "body": body})
        return self.fabric.send(self.chip_id, msg, to=to)

    def _verify_governor_quote(self, qmsg: dict) -> VerifyKey | None:
        """Chain: governor vendor key → device cert → alias cert → quote; firmware in the reference values."""
        refs = self._reference("governor")
        vendor_keys = {VerifyKey.from_hex(r["vendor_key"]).key_id: VerifyKey.from_hex(r["vendor_key"]) for r in refs}
        dc, ac, quote = qmsg.get("device_cert"), qmsg.get("alias_cert"), qmsg.get("quote")
        if not dc or verify_any(dc, vendor_keys) is None:
            return None
        dev = VerifyKey.from_hex(dc["payload"]["pub"])
        if not ac or not verify_object(ac, dev) or ac["payload"]["chip_id"] != dc["payload"]["chip_id"]:
            return None
        alias = VerifyKey.from_hex(ac["payload"]["pub"])
        if not quote or not verify_object(quote, alias):
            return None
        qp = quote["payload"]
        if qp["meas1"] != ac["payload"]["meas1"] or qp["chip_id"] != dc["payload"]["chip_id"]:
            return None
        now = self.clock.now()
        if not any(r["meas1"] == qp["meas1"] and r["valid_until"] > now for r in refs):
            return None
        return alias

    def quote_for_job(self, job_id: str) -> dict:
        nonce = digest(["job", job_id])
        return {"chip_id": self.chip_id, "quote": self.root.quote(nonce, {"gpu_fingerprint": self.fingerprint, "gpu_chip_id": self.gpu.chip_id if self.gpu else None}),
                "device_cert": self.device_cert, "alias_cert": self.alias_cert, "job_id": job_id}

    def announce(self, job_id: str) -> None:
        q = self.quote_for_job(job_id)
        self.pending_quotes.setdefault(job_id, {})[self.chip_id] = {**q, "key": self.key.public}
        self.fabric_send("QUOTE", q)

    def build_roster(self, job_id: str, expected: list[str], ttl_s: float = 3600.0) -> dict | None:
        """The leader (lowest chip id among valid quotes) signs the roster."""
        quotes = self.pending_quotes.get(job_id, {})
        members = sorted(c for c in expected if c in quotes)
        if not members or min(quotes) != self.chip_id:
            return None
        roster = {"type": "roster", "roster_id": digest([job_id, members, self.clock.now()]), "job_id": job_id,
                  "leader": self.chip_id, "expires_at": self.clock.now() + ttl_s,
                  "members": [{"chip_id": c, "key": quotes[c]["key"].hex, "gpu_chip_id": quotes[c]["quote"]["payload"].get("gpu_chip_id"),
                               "gpu_fingerprint": quotes[c]["quote"]["payload"].get("gpu_fingerprint")} for c in members]}
        signed = self.key.sign(roster)
        self._adopt_roster(signed)
        self.fabric_send("ROSTER", {"roster": signed})
        return signed

    def _adopt_roster(self, signed: dict) -> bool:
        r = signed["payload"]
        quotes = self.pending_quotes.get(r["job_id"], {})
        leader = quotes.get(r["leader"])
        if leader is None or not verify_object(signed, leader["key"]):
            return False
        if self.chip_id not in {m["chip_id"] for m in r["members"]} or r["expires_at"] <= self.clock.now():
            return False
        for m in r["members"]:
            if m["chip_id"] not in quotes or quotes[m["chip_id"]]["key"].hex != m["key"]:
                return False
        self.roster = r
        self.roster_keys = {m["chip_id"]: VerifyKey.from_hex(m["key"]) for m in r["members"]}
        self.log.append("roster.adopted", {"roster_id": r["roster_id"], "members": [m["chip_id"] for m in r["members"]]})
        if self.state == RUN:
            self.open_ports_for_roster()
        return True

    def on_fabric(self, msg: dict) -> Any:
        """Every message is checked here. The wire itself checks nothing."""
        with self.lock:
            self.ops["fabric_rx"] += 1
            try:
                p = msg["payload"]
                mtype, sender = p["type"], p["from"]
            except (KeyError, TypeError):
                return {"ok": False, "why": reasons.FABRIC_BAD_SIGNATURE}
            if mtype == "QUOTE":
                return self._on_quote(msg)
            if mtype == "ROSTER":
                return self._on_roster(msg)
            if mtype == "HEARTBEAT":
                body = p.get("body", {})
                return self._heartbeat(body.get("authority"), hops=int(body.get("hops", 1)))
            key = self.roster_keys.get(sender)
            if key is None:
                self.log.append("fabric.dropped", {"why": reasons.FABRIC_NOT_MEMBER, "from": sender, "type": mtype})
                return {"ok": False, "why": reasons.FABRIC_NOT_MEMBER}
            if not verify_object(msg, key):
                self.log.append("fabric.dropped", {"why": reasons.FABRIC_BAD_SIGNATURE, "from": sender})
                return {"ok": False, "why": reasons.FABRIC_BAD_SIGNATURE}
            if int(p.get("seq", -1)) <= self.fabric_last_seq.get(sender, -1):
                self.log.append("fabric.dropped", {"why": reasons.FABRIC_REPLAY, "from": sender})
                return {"ok": False, "why": reasons.FABRIC_REPLAY}
            if mtype not in ("HEARTBEAT", "HALT_CAUSE", "CHECKPOINT", "CHECKPOINT_ACK") and p.get("epoch") != self.epoch:
                self.log.append("fabric.dropped", {"why": reasons.FABRIC_STALE_EPOCH, "from": sender})
                return {"ok": False, "why": reasons.FABRIC_STALE_EPOCH}
            self.fabric_last_seq[sender] = int(p["seq"])
            handler = getattr(self, "_on_" + mtype.lower(), None)
            if handler is None:
                return {"ok": False, "why": reasons.MBOX_UNKNOWN_COMMAND}
            return handler(sender, p["body"])

    def _on_quote(self, msg: dict):
        body = msg["payload"]["body"]
        alias = self._verify_governor_quote(body)
        if alias is None or not verify_object(msg, alias):
            self.log.append("fabric.dropped", {"why": reasons.ROSTER_QUOTE_INVALID, "from": msg["payload"].get("from")})
            return {"ok": False, "why": reasons.ROSTER_QUOTE_INVALID}
        self.pending_quotes.setdefault(body["job_id"], {})[body["chip_id"]] = {**body, "key": alias}
        return {"ok": True, "why": reasons.OK}

    def _on_roster(self, msg: dict):
        signed = msg["payload"]["body"]["roster"]
        ok = self._adopt_roster(signed)
        return {"ok": ok, "why": reasons.OK if ok else reasons.ROSTER_NOT_MEMBER}

    def _on_heartbeat(self, sender: str, body: dict):
        return self._heartbeat(body.get("authority"), hops=int(body.get("hops", 1)))

    def _on_reserve(self, sender: str, body: dict):
        owner = self.policy["budget_owners"].get(body["key"], self.chip_id)
        if owner != self.chip_id:
            return {"ok": False, "why": reasons.GATE_BUDGET_OWNER_UNREACHABLE}
        rid = self.ledger.reserve(body["key"], body["amount"], body["limit"], body["window_s"], self.clock.now(), body["ttl"])
        self.ops["shared_reserve"] += 1
        return {"ok": rid is not None, "rid": rid, "why": reasons.OK if rid else reasons.GATE_BUDGET}

    def _on_commit(self, sender: str, body: dict):
        return {"ok": self.ledger.commit(body["key"], body["rid"], self.clock.now()), "why": reasons.OK}

    def _on_release(self, sender: str, body: dict):
        self.ledger.release(body["key"], body["rid"])
        return {"ok": True, "why": reasons.OK}

    def _on_alarm(self, sender: str, body: dict):
        self.raise_alarm(body["code"], "fabric")
        return {"ok": True, "why": reasons.OK}

    def _on_halt_cause(self, sender: str, body: dict):
        self.log.append("fabric.halt_cause", {"from": sender, "cause": body.get("cause")})
        return {"ok": True, "why": reasons.OK}

    def _on_checkpoint(self, sender: str, body: dict):
        cp = body.get("checkpoint")
        key = self.roster_keys.get(sender)
        if not cp or key is None or not verify_object(cp, key):
            return {"ok": False, "why": reasons.FABRIC_BAD_SIGNATURE}
        self.log.record_neighbor_head(sender, cp["payload"]["head"])
        self.fabric_send("CHECKPOINT_ACK", {"head": cp["payload"]["head"], "size": cp["payload"]["size"]}, to=sender)
        return {"ok": True, "why": reasons.OK}

    def _on_checkpoint_ack(self, sender: str, body: dict):
        self.acked_heads[body["head"]] = int(body["size"])
        return {"ok": True, "why": reasons.OK}

    def publish_checkpoint(self) -> None:
        if self.fabric is None:
            return
        cp = self.log.checkpoint(self.key, self.chip_id)
        for n in self.fabric.neighbors(self.chip_id):
            self.fabric_send("CHECKPOINT", {"checkpoint": cp}, to=n)
