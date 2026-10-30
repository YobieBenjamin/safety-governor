# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The Safety Governor: the chip logic that decides whether one GPU slot may run, and which actions
it may take. One instance per GPU slot.

What it does: it holds the signed policy in force. It checks every command the host sends (through
``command``) and every message from another governor (through ``on_fabric``). It reads the halt loop
(``sense_loop``) and advances its timers (``tick``). It issues tickets for requests the policy allows,
parks requests that need a human in a hold, keeps the meter and the log, and steps down a ladder of
safe states when a check fails or a heartbeat is lost.

The states, from least to most restrictive: RUN, THROTTLE, HALT, SAFE. A chip that has not started yet
is HALTED_INITIAL. Each step down the ladder stops more of the GPU.

What it guarantees, as the code is written: the chip runs only with a live heartbeat, loop current and
no uncleared cause. Requests need the GPU and the host enclave to be attested. Each signed message is
checked for sequence number, epoch, signature and content, in that order, and each refusal is logged
with a reason code. A power cycle does not clear a halt. The host, the GPU and the fabric are treated as
untrusted, and the governor checks what they send.

What it deliberately does NOT do: it does not judge whether a model or an action is good. It applies
the rules in the signed policy. It runs no model work; the GPU does that. The simplifications relative
to the specification are listed below, and each is named where it applies.

Simplifications relative to the specification, each named where it applies:
- Signatures are Ed25519; wrapping a model key to an enclave is an HMAC-based stand-in.
- The endpoint's COMMIT may arrive as a direct call (``commit_from_endpoint``) as well as
  through the mailbox (``COMMIT``); the direct path is authenticated by the ticket it carries.
- Fabric round trips are synchronous function calls."""
from __future__ import annotations

import hashlib
import hmac
import threading

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from collections import Counter
from typing import Any

from . import reasons
from .crypto import SigningKey, VerifyKey, canonical, digest, finite_number, hmac_sha256, random_id, verify_any, verify_object
from . import endpoints as _endpoints
from .endpoints import BRICKED, DescriptorChecker, INTEGRATED_POINTS, RACK_POINTS, Switch
from .fuses import Fuses, PRODUCTION
from .ledger import Ledger
from .log import Log
from .policy import (RELEASE_ACTION, buffer_allowed, check_budget_owners, check_constraints, check_register, find_rule,
                     floor_violations, loosenings, policy_epoch, select_rule, verify_policy, verify_recovery)
from .fuses import POLICY_FUSE_BITS, POLICY_FUSE_STRIDE
from .root import SiliconRoot
from .store import Store

HALTED_INITIAL, RUN, THROTTLE, HALT, SAFE = "HALTED_INITIAL", "RUN", "THROTTLE", "HALT", "SAFE"
RUNG_ORDER = {RUN: 0, THROTTLE: 1, HALT: 2, SAFE: 3}
# The hard core's escalation timers (rtl/governor_rtl/top.py GovernorCore t_throttle_ms, t_halt_ms): the longest an
# edition may make them. A THROTTLE becomes a HALT, and a HALT becomes SAFE (slot power off), within these bounds.
MAX_T_THROTTLE_S, MAX_T_HALT_S = 30.0, 300.0
MODE_ORDER = {"auto": 0, "observer": 1, "human": 2}     # how strict a rule's requirement is
MAX_EDITION_STEP = 16            # the most an edition's version may advance over the one in force (audit 3)
BUDGET_MESSAGES = ("RESERVE", "COMMIT", "RELEASE")   # answered by the budget unit, outside the main lock
FABRIC_ALARM_QUORUM = 2          # distinct roster members that must report the same alarm before it blocks this chip
MAX_LIST_VERSION_STEP = 1_000_000      # the most a signed list's version may advance in one install
STATE_CODES = {HALTED_INITIAL: 0, RUN: 1, THROTTLE: 2, HALT: 3, SAFE: 4}      # the STATE register encoding
TIERS = ("rack", "board", "integrated")
TOKEN_TTL_S = 3600.0
TICKET_TTL_S = 300.0
AUTHORITY_TTL_S = 60.0          # a HALT or CLEAR is good for a minute at most: it cannot be banked and spent later
SEEN_HEARTBEATS_MAX = 256
BOOT_WINDOW_S = 5.0             # the hardware's boot window (t_boot_ms in rtl/governor_rtl/halt.py): no first heartbeat by then is an alarm
# Causes that open the loop (the whole domain stops) unless the policy's safe_mode.opens_loop says otherwise.
LOOP_OPENING_CAUSES = (reasons.LOOP_OPEN, reasons.LOOP_BROKEN, reasons.TAMPER, reasons.HALT_COMMANDED, reasons.LOOP_JUMPERED)
# Alarms scoped to one session: they park that session's releases for the human lane and do not block the gate for every request.
SESSION_SCOPED_ALARMS = {reasons.SESSION_HAZARD_BUDGET}
# Operator-status alarms: loud and sticky, but they say why a chip is not running, so they do not
# park the gate of a chip (or a neighbour) that is running.
STATUS_ALARMS = {reasons.NO_FIRST_HEARTBEAT, reasons.EXCLUDED}
# Alarms that say the safety fabric itself was tampered with: clearing one needs two approvers of the alarms rule.
TWO_APPROVER_ALARMS = {reasons.LOOP_JUMPERED, reasons.LOOP_BROKEN, reasons.OUTPUT_UNPRESENTED}

# docs/04 section 3: the mailbox command codes, one handler per code (``_cmd_<name>``).
MAILBOX_CODES = {
    0x01: "ATTEST", 0x02: "VERIFY_GPU", 0x03: "VERIFY_HOST", 0x04: "BEGIN_MODEL", 0x05: "END_MODEL",
    0x06: "REQUEST", 0x07: "APPROVE", 0x08: "COMMIT", 0x09: "SIGN_OUTPUT", 0x0A: "CAP_REQUEST",
    0x0B: "ROSTER_JOIN", 0x0C: "POLICY_PROPOSE", 0x0D: "POLICY_COMMIT", 0x0E: "HEARTBEAT", 0x0F: "HALT",
    0x10: "CLEAR", 0x11: "LOG_CHECKPOINT", 0x12: "COUNTERS", 0x13: "EXCEPTION_DRAIN",
    0x14: "ALARM_RAISE", 0x15: "ALARM_CLEAR", 0x16: "EXCLUDE",
    0x17: "KEY_RELEASE", 0x18: "KEY_RENEW",          # the origin gate (docs/18 question 20), 23 October 2026
}
# Commands whose frame may carry any epoch (they move, repair or inspect the epoch itself).
EPOCH_EXEMPT = {"POLICY_PROPOSE", "POLICY_COMMIT", "ATTEST", "HALT", "CLEAR", "ALARM_CLEAR", "EXCLUDE"}
# Commands accepted while the governor is not in RUN.
NO_RUN_NEEDED = {"ATTEST", "VERIFY_GPU", "VERIFY_HOST", "POLICY_PROPOSE", "POLICY_COMMIT", "HEARTBEAT", "CLEAR",
                 "LOG_CHECKPOINT", "COUNTERS", "ALARM_RAISE", "ALARM_CLEAR", "HALT", "APPROVE", "COMMIT", "EXCEPTION_DRAIN",
                 "EXCLUDE"}


class Governor:
    """The safety governor for one GPU slot: the chip's own state machine.

    It owns the chip's keys (derived from its root of trust), the signed policy in force, the holds
    (requests waiting for a human), the tickets it mints, the output and meter counters, the alarms,
    the log, and the ladder of safe states.

    Inputs: the host reaches it only through ``command`` (the mailbox). Other governors reach it through
    ``on_fabric``. The halt loop is read through ``sense_loop``, and time moves only through ``tick``.
    Nothing else changes its state."""
    def __init__(self, name: str, clock, *, tier: str = "rack", fuses: Fuses | None = None, store: Store | None = None,
                 loader_digest: str | None = None, firmware_digest: str | None = None, firmware_version: int = 1,
                 rng_seed: int | None = None):
        """Create one governor on one chip. ``fuses`` are the chip's fixed trust anchors. ``store`` holds
        the durable state that survives power loss. ``loader_digest`` and ``firmware_digest`` are the boot
        code measurements. The governor boots at once (see ``_boot``) and starts in HALTED_INITIAL, which
        runs nothing, unless a stored uncleared cause restores a halted rung."""
        if tier not in TIERS:
            raise ValueError(tier)
        self.name, self.clock, self.tier = name, clock, tier
        self.fuses = fuses or Fuses()
        self.store = store or Store()
        self.rng_seed = rng_seed
        self.firmware = (loader_digest or digest("loader-v1"), firmware_digest or digest("governor-fw-v1"), firmware_version)
        self.lock = threading.RLock()
        self.fabric_lock = threading.RLock()     # the fabric's admission checks and sequence record
        self.budget_lock = threading.RLock()     # the budget unit: owner-side RESERVE, COMMIT, RELEASE
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
        """Rebuild everything a power-up needs: the root of trust, the chip key, the durable state and the
        safe rung. Durable state (counters, holds, alarms, replay records, the policy image, the roster) is
        reloaded from the store. Volatile state (leases, nonces, cached attestations) starts empty, so every
        lease lapses on restart. An uncleared cause comes back as the same rung, so a power cycle cannot clear
        a halt."""
        self.root = SiliconRoot(self.fuses, counter_start=int(self.store.get("counter", 0)), rng_seed=self.rng_seed)
        self.key = self.root.boot(*self.firmware)
        # the origin gate's key-encryption key: weights are sealed to its public half; it never leaves the chip
        from .sealing import x25519_private
        self.kek = x25519_private(self.root.derive(b"model-kek"))
        self.leases: dict[str, dict] = {}       # model -> live key lease (volatile: a restart lets every lease lapse)
        self.key_gen = 0                         # strictly increasing lease generation; a revocation advances it (F02)
        self.model_weights: dict | None = None   # the authenticated weight commitment of the loaded model (F01)
        self.device_key = self.root.device_key
        self.alias_cert = self.device_key.sign({"type": "alias-cert", "chip_id": self.chip_id, "pub": self.key.public.hex,
                                                "meas1": self.root.meas1.value})
        self.log = Log(self.store, self.clock)
        self.ledger = Ledger(self.store, self.clock)
        self.alarms: dict[str, dict] = self.store.get("alarms", {})
        self.holds: dict[str, dict] = self.store.get("holds", {})
        self.mbox_seq: dict[str, int] = self.store.get("mbox_seq", {})
        self.meter: dict[str, dict] = self.store.get("meter", {})
        self.epoch_history: list[str] = self.store.get("epoch_history", [])   # every epoch accepted, newest last
        self.quoted_nonces: list[str] = self.store.get("quoted_nonces", [])    # nonces already quoted over (replay refused)
        self.responses: dict[str, dict] = self.store.get("responses", {})     # response_id -> presented streams, audit draw
        self.committed_tickets: dict[str, float] = self.store.get("committed_tickets", {})   # ticket_id -> commit time: central single-use (F11)
        # Adversarial audit 3: the durable record of every ticket this governor minted (ticket_id -> digest of the
        # ticket body). A commit is accepted only for a ticket in this record with the same body, so a key extracted
        # from the chip cannot mint tickets the rule engine never issued: the forged ticket is not in the record.
        self.minted_tickets: dict[str, dict] = self.store.get("minted_tickets", {})
        # The fabric key-agreement key (X25519), derived from the chip's unique secret and attested in its roster
        # quote. Roster members derive one pairwise key each from it, and authenticate fabric messages with MACs
        # instead of a P-384 signature per message (adversarial audit 3: with one governor per GPU, 72 members each
        # verifying 71 signed reports a second needed more than one signing engine).
        self.fabric_kx = X25519PrivateKey.from_private_bytes(self.fuses.derive(b"fabric-kx", 32))
        self.fabric_macs: dict[str, bytes] = {}
        self.egress_mac_key: bytes | None = None          # shared with this node's egress endpoint (release tickets)
        self.lever_check: dict = {}                       # the last lever self-test (lever_selftest)
        self.jurisdictions: dict[str, dict] = self.store.get("jurisdictions", {})   # name -> that jurisdiction's edition
        self.fabric_alarm_reports: dict[str, set[str]] = {}       # alarm code -> roster members that reported it   # ticket_id -> {digest, expires_at}
        self.exported_tickets: dict[str, float] = self.store.get("exported_tickets", {})     # F31: storage export tickets already spent
        self.licenses: dict[str, int] = self.store.get("licenses", {})        # model digest -> cycles a license allows
        self.policy: dict | None = None
        self._epoch = ""
        staged = self.store.get("staged")
        self.staged: dict | None = staged["image"] if staged else None
        self.staged_at: float = float(staged["at"]) if staged else 0.0
        self.levers = {"pwrbrk": True, "perst": True, "pwr_en": False}
        self.loop_switch_open = True
        self.hb_expiry = 0.0
        self.boot_at = self.clock.now()          # the hardware's boot window starts at reset
        self.hb_seen = False                     # armed at least once since reset (the RTL's hb_seen)
        self.excluded = False                    # an authorized EXCLUDE closed the switch; a reset ends it
        self.hb_last_seq: int = int(self.store.get("hb_last_seq", -1))
        self.seen_heartbeats: list[int] = self.store.get("seen_heartbeats", [])
        self.verified: dict[str, dict] = {}
        self.nonces: set[str] = set()
        self.fingerprint: str | None = None
        self.workload: str | None = None
        self.host_key: VerifyKey | None = None
        self.model_digest: str | None = None
        self.lists: dict[str, dict] = {}
        self._fleet_receipt_cache: dict[str, list] = {}   # digest of a fleet reservation -> the replicas' signed receipts
        # durable per-list version floors: an older still-unexpired list can never replace a newer one (F06)
        self.list_floors: dict[str, int] = self.store.get("list_floors", {})
        self.output_streams: dict[str, Any] = {}
        self.presented_bytes = 0
        self.cap_key = self.root.derive(b"cap")
        self.switches: dict[str, Switch] = {}
        self.checkers: dict[str, DescriptorChecker] = {}
        self.roster: dict | None = None
        self.roster_keys: dict[str, VerifyKey] = {}
        self.reservation_holder: dict[str, str] = {}      # budget owner: reservation id -> the member that reserved it
        self.fleet_ledger = None                            # set when the rack belongs to a fleet (govsim/fleet.py)
        signed_roster = self.store.get("roster")                 # the roster outlives a power loss until it expires
        if signed_roster and signed_roster["payload"]["expires_at"] > self.clock.now():
            self.roster = signed_roster["payload"]
            self.roster_keys = {m["chip_id"]: VerifyKey.from_hex(m["key"]) for m in self.roster["members"]}
            self._restore_fabric_macs = True
        self.pending_quotes: dict[str, dict[str, dict]] = {}
        self.fabric_seq: int = int(self.store.get("fabric_seq", 0)) + 1000     # a restarted sender is never a replay
        self.fabric_last_seq: dict[str, int] = self.store.get("fabric_last_seq", {})
        self.acked_heads: dict[str, int] = {}      # my head -> my log size at that head, acknowledged by a neighbor
        self.loop_beacon: dict | None = None       # the beacon whose collection window is open
        self.loop_reports: dict[int, dict[str, dict]] = {}     # beacon seq -> chip id -> LOOP_REPORT body
        self.approvals: dict[str, dict[str, dict]] = {}
        self.last_tick_t = self.clock.now()
        image = self.store.get("policy_image")
        if image:
            ok, why = self._accept_policy(image, at_boot=True)
            if not ok:
                self.log.append("policy.boot_load_failed", {"why": why})
        # the safe-mode rung survives power loss: an uncleared cause comes back as the same rung
        rung = self.store.get("rung", {})
        self.cause = rung.get("cause")
        self.cause_entry = rung.get("cause_entry")
        self.cause_opens_loop = bool(rung.get("cause_opens_loop", False))
        self.rung_entered_at = float(rung.get("rung_entered_at", 0.0))
        self.state = HALTED_INITIAL
        if self.cause is not None and rung.get("state") in RUNG_ORDER and rung["state"] != RUN:
            self.loop_switch_open = bool(rung.get("loop_switch_open", True))
            self._apply_rung(rung["state"], opens_loop=self.cause_opens_loop)
        else:
            self.cause, self.cause_entry, self.cause_opens_loop = None, None, False
            self._apply_rung(HALTED_INITIAL, opens_loop=True)
        self.log.append("boot", {"firmware": self.root.firmware_digest, "version": self.root.firmware_version, "tier": self.tier,
                                 "state": self.state, "cause": self.cause})

    def restart(self) -> None:
        """Power loss and return. Durable state survives; everything else is rebuilt."""
        gpu, loop, fabric, endpoints, cert = self.gpu, self.loop, self.fabric, self.endpoints, self.device_cert
        self.store.power_loss()
        self.store.check_epoch_marks()      # F34: refuses to start when the two epoch-mark copies disagree
        self._boot()
        self.gpu, self.loop, self.fabric, self.endpoints, self.device_cert = gpu, loop, fabric, endpoints, cert
        if gpu is not None:
            self.attach_gpu(gpu)

    @property
    def chip_id(self) -> str:
        """This chip's id, read from its fuses."""
        return self.fuses.chip_id

    @property
    def epoch(self) -> str:
        """The policy epoch. Read-only: only ``_accept_policy`` moves it."""
        return self._epoch

    def provision(self, vendor_key: SigningKey, lifecycle: int = PRODUCTION) -> None:
        """Factory: the governor vendor certifies the DICE device identity; the lifecycle fuse advances."""
        self.device_cert = vendor_key.sign({"type": "governor-device-cert", "chip_id": self.chip_id, "pub": self.device_key.public.hex})
        self.fuses.advance_lifecycle(lifecycle)

    # ------------------------------------------------------------------ attachments
    @property
    def kek_public(self) -> str:
        """The public half of the chip's key-encryption key. The origin gate seals model weights to it.
        The private half never leaves the chip."""
        from .sealing import public_hex
        return public_hex(self.kek)

    def attach_gpu(self, gpu) -> None:
        """Connect one GPU to this governor. The GPU gets the governor's public key (to check key leases)
        and the governor's switches for its tier. The rack tier gets the port switches. The integrated tier
        also gets the descriptor checkers and the output hook. The GPU's levers follow the governor's current
        levers."""
        self.gpu = gpu
        gpu.governor_key = self.key.public       # the GPU checks key leases against it
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
        """Put this governor on the halt loop and on the message fabric. A governor that is not joined cannot
        sense the loop or send messages."""
        self.loop, self.fabric = loop, fabric
        loop.join(self)
        fabric.join(self)

    # ------------------------------------------------------------------ policy
    def _trusted_governance(self) -> dict | None:
        """The governance configuration the chip recorded when the last edition was committed, or None on
        a new chip with no record."""
        return getattr(self.fuses, "trusted_governance", None)

    def _verify_policy(self, image: dict) -> tuple[bool, str]:
        """Authorized by the governance configuration in force (the chip's protected record), or, for the
        first rulebook on a new chip, by the key hashes and the floor fused at manufacture."""
        return verify_policy(image, self.fuses.governance_key_hashes, self.fuses.governance_threshold, self._trusted_governance())

    # ------------------------------------------------------------------ jurisdictions
    def install_jurisdiction(self, name: str, image: dict) -> tuple[bool, str]:
        """Install the edition of one jurisdiction whose root is fused in this chip. It must be signed by that root's
        own quorum (another jurisdiction's or the main governance's keys do not count), must not roll back, must not
        have expired, and must name the jurisdiction. Its rules can only add restrictions: an action it governs must
        pass both the main edition and this one, so no jurisdiction can weaken another's rules or the main ones."""
        root = self.fuses.jurisdiction_roots.get(name)
        if root is None:
            return False, reasons.JURISDICTION_UNKNOWN
        ok, why = verify_policy(image, root.get("key_hashes", []), int(root.get("threshold", 1)), None)
        if not ok or image.get("jurisdiction") != name:
            return False, why if not ok else reasons.JURISDICTION_UNKNOWN
        held = self.jurisdictions.get(name)
        if held is not None and int(image["version"]) <= int(held["version"]):
            return False, reasons.POLICY_ROLLBACK
        if float(image["expires_at"]) <= self.clock.now():
            return False, reasons.POLICY_EXPIRED
        self.jurisdictions[name] = image
        self.store.data["jurisdictions"] = self.jurisdictions
        self.store.save()
        self.log.append("jurisdiction.installed", {"name": name, "version": image["version"], "epoch": policy_epoch(image)})
        return True, reasons.OK

    def _jurisdictions_allow(self, workload: str, action: str, params: dict, lists: dict, now: float) -> tuple[bool, str, str]:
        """(ok, reason, strictest mode) over the jurisdictions that govern ``action``. An expired jurisdiction
        edition denies what it governs (fail closed); a jurisdiction that governs the action but has no rule that
        the request satisfies denies it."""
        strictest = "auto"
        for name, image in self.jurisdictions.items():
            if action not in image.get("governs", []):
                continue
            if float(image["expires_at"]) <= now:
                return False, reasons.JURISDICTION_EXPIRED + "." + name, strictest
            rule, why = select_rule(image, workload, action, params, lists)
            if rule is None:
                return False, reasons.JURISDICTION_DENIED + "." + name, strictest
            mode = rule["requirement"]["mode"]
            if MODE_ORDER.get(mode, 0) > MODE_ORDER.get(strictest, 0):
                strictest = mode
        return True, reasons.OK, strictest

    def _check_edition(self, image: dict, at_boot: bool = False) -> tuple[bool, str]:
        """Every check an edition must pass before it may be staged or put in force: signatures (the governance in
        force, or the fused recovery quorum), the fused rule floor, the version step, the loosening delay, the class
        floor, no rollback, the fused thermometer, expiry, the register and the budget owners. Output: (ok, reason)."""
        trusted = self._trusted_governance()
        if at_boot and trusted is not None and trusted.get("image_epoch") == policy_epoch(image):
            ok, why = True, reasons.OK      # the edition that set the record in force: verified when it was committed
        else:
            ok, why = self._verify_policy(image)
        recovered = False
        if not ok and verify_recovery(image, self.fuses.recovery_key_hashes, self.fuses.recovery_threshold):
            # The fused recovery quorum can always sign an edition over whatever governance is in force, so a stolen
            # governance quorum that rotated the chip to its own keys cannot keep it (adversarial audit 3).
            ok, why, recovered = True, reasons.OK, True
        if not ok:
            return False, why
        # The fused rule floor: no signature removes these rules (adversarial audit 3: a quorum-signed edition
        # dropped the protected-site constraint and made strikes automatic, and was accepted on every chip).
        if floor_violations(image, self.fuses.rule_floor):
            return False, reasons.POLICY_BELOW_FLOOR
        if self.policy and not at_boot:
            # A version may advance only a little per edition, so one edition cannot burn the anti-rollback range
            # and lock out every later legitimate edition (audit 3: a stolen quorum signed version 10**9).
            if int(image["version"]) > int(self.policy["version"]) + MAX_EDITION_STEP:
                return False, reasons.POLICY_VERSION_JUMP
            # An edition that loosens the rules in force acts only after the fused delay from its issue time.
            if self.fuses.loosen_delay_s > 0 and not recovered and loosenings(self.policy, image):
                eff = image.get("effective_at")
                if not finite_number(eff) or eff - float(image["issued_at"]) < self.fuses.loosen_delay_s or eff > self.clock.now():
                    return False, reasons.POLICY_LOOSENING_DELAY
        floor = int(getattr(self.fuses, "governance_class_floor", 0) or 0)
        if floor > 0:
            classes = {VerifyKey.from_hex(h).key_id: c for h, c in (image.get("governance_classes") or {}).items()}
            keyed = {VerifyKey.from_hex(h).key_id for h in image["governance_keys"]}
            if int(image.get("governance_class_quorum") or 0) < floor or not keyed <= set(classes) \
                    or len({classes[k] for k in keyed}) < floor:
                return False, reasons.POLICY_CLASS_QUORUM
        # no rollback: an older edition is refused, even after a restart, because the fused version floor only moves up
        if image["version"] < max(self.fuses.policy_floor_version, self.fuses.nvm_policy_version) \
                or (self.policy and image["version"] <= self.policy["version"] and not at_boot):
            return False, reasons.POLICY_ROLLBACK
        if image["version"] // POLICY_FUSE_STRIDE > POLICY_FUSE_BITS:
            return False, reasons.POLICY_VERSION_JUMP          # the fused thermometer could not record it
        if image["expires_at"] <= self.clock.now():
            return False, reasons.POLICY_EXPIRED
        if check_register(image):
            return False, reasons.POLICY_REGISTER_INCOMPLETE
        if check_budget_owners(image):
            return False, reasons.POLICY_BUDGET_OWNER_MISSING
        return True, reasons.OK

    def _accept_policy(self, image: dict, at_boot: bool = False) -> tuple[bool, str]:
        """Check a policy image and, if it passes, make it the one in force. The checks, in order: the
        governance signatures (or the chip's fused record), no version rollback, the expiry against the chip's
        clock, the register completeness, and the budget owners. On success the epoch moves, the governance keys
        are recorded for the next change, and holds from the old epoch are dropped. Leased keys the new edition
        no longer allows are revoked (origin gate). Output: (ok, reason). ``at_boot`` lets a power-up reload
        the same version."""
        ok, why = self._check_edition(image, at_boot)
        if not ok:
            return False, why
        old_epoch = self._epoch
        self.policy = image
        self._epoch = policy_epoch(image)
        self.fuses.bump_policy(image["version"])
        # this edition's keys and k now authorize the next change (rotation included); never below the fused floor.
        # F26: the across-class quorum and the key->class enrolment travel with it, so the rule in force governs
        # the next change too.
        self.fuses.record_governance(image["governance_keys"], int(image["threshold"]), self._epoch,
                                     classes=image.get("governance_classes"),
                                     class_quorum=int(image.get("governance_class_quorum") or 0))
        self.store.data["policy_image"] = image
        if not self.epoch_history or self.epoch_history[-1] != self._epoch:
            self.epoch_history.append(self._epoch)        # the compliance report lists every edition this chip ran under
        for sw in list(self.switches.values()) + list(self.checkers.values()):
            sw.set_epoch(self.epoch[:8])
        if not at_boot and old_epoch and old_epoch != self.epoch:
            self.holds.clear()          # a hold carries the epoch that parked it; the new rules re-decide
            if self.workload:
                # the fingerprint names the edition, so every workload token minted under the old one dies
                # here; the host presents its manifest again and the new rules decide (gap GAP-WORKLOAD-TOKEN-SURVIVES-RULE-CHANGE, a workload token survived a rulebook change; closed 22 October 2026)
                self.fingerprint = digest([self.workload, self.epoch])
        # the origin gate: an edition that no longer lists a model takes its key back now (the lease bound is the
        # guarantee; this is the fast path when the governor can still reach the GPU)
        for model, live in list(getattr(self, "leases", {}).items()):
            if model not in image.get("sealed_models", []):
                self._revoke_key(model, "dropped by edition " + self._epoch[:12])
            elif live["gpu"] in set(image.get("revocations", [])):
                self._revoke_key(model, "GPU revoked by edition " + self._epoch[:12])
        # a revoked chip's cached attestation must not outlive the edition that revoked it: drop it so no
        # attestation-dependent operation (a fresh KEY_RELEASE above all) can lean on a stale cache (F02)
        if self.verified.get("gpu", {}).get("chip_id") in set(image.get("revocations", [])):
            self.verified.pop("gpu", None)
        self.store.save()
        if self.gpu is not None:
            self.gpu.policy_epoch_reported = self.epoch
        return True, reasons.OK

    def signed_epoch(self) -> dict:
        """A governor-signed statement of the epoch this governor runs under. Endpoints use it to learn the
        current epoch."""
        # F30: the statement also carries the edition's expiry, so an endpoint can refuse an expired edition on
        # its own clock. None when the installed image names no expiry.
        expires = self.policy.get("expires_at") if self.policy else None
        # Adversarial audit 3: the statement carries the edition's version, so an endpoint can refuse a replayed,
        # superseded statement (a host replaying an old one used to roll the egress endpoint back).
        version = int(self.policy.get("version", 0)) if self.policy else 0
        return self.key.sign({"type": "policy-epoch", "epoch": self.epoch, "version": version, "governor": self.chip_id,
                              "issued_at": self.mono(), "expires_at": expires})

    def _policy_expired(self, now: float) -> bool:
        """F30: True when the installed edition has reached its own expiry at ``now``. Checked per request, not only at tick."""
        return bool(self.policy) and float(self.policy.get("expires_at", float("inf"))) <= now

    def install_list(self, list_id: str, signed_list: dict) -> bool:
        """A signed list (protected sites, sanctions, beneficiaries, customers) the rules compare against.

        The authenticated identity is kept with the list: version, expiry and the issuing signer. A list signed by a
        signer the current edition revokes is refused; so is an older version than one already installed, so a newer
        list can never be rolled back by an older still-unexpired one. Expiry and issuer revocation are re-checked on
        every use through ``_live_lists``, never cached from this moment (F06)."""
        if not self.policy:
            return False
        revoked = set(self.policy.get("revocations", []))
        keys = {}
        for h in self.policy["governance_keys"]:
            k = VerifyKey.from_hex(h)
            if k.key_id not in revoked:          # a revoked governance signer cannot authorize a list (F06)
                keys[k.key_id] = k
        signer = verify_any(signed_list, keys)
        if signer is None or signed_list["payload"].get("list_id") != list_id:
            return False
        # A list a rule depends on (protected sites, beneficiaries, recipients) needs the edition's list quorum of
        # distinct governance signers, each signing the same list (adversarial audit 3, 26 October 2026: one key, below
        # the quorum, used to replace any list and so loosen any rule that reads it).
        signers = {signer.key_id}
        for c in signed_list.get("cosignatures", []) or []:
            if isinstance(c, dict) and c.get("payload") == signed_list.get("payload"):
                k = verify_any(c, keys)
                if k is not None:
                    signers.add(k.key_id)
        if len(signers) < int(self.policy.get("list_threshold", 1) or 1):
            self.log.append("list.quorum_refused", {"list_id": list_id, "signers": len(signers)})
            return False
        p = signed_list["payload"]
        version = int(p.get("version", 0))
        floor = int(self.list_floors.get(list_id, 0))
        if version < floor:                       # an older signed list never replaces a newer one (F06)
            self.log.append("list.rollback_refused", {"list_id": list_id, "version": version, "floor": floor})
            return False
        if version > floor + MAX_LIST_VERSION_STEP:
            # a version far ahead of the last one would freeze every later update (the floor only rises)
            self.log.append("list.version_jump_refused", {"list_id": list_id, "version": version, "floor": floor})
            return False
        self.list_floors[list_id] = max(floor, version)
        self.store.data["list_floors"] = self.list_floors
        self.lists[list_id] = {"entries": p["entries"], "expires_at": p["expires_at"],
                               "version": version, "issuer": signer.key_id, "list_id": list_id}
        self.store.save()
        return True

    def _live_lists(self) -> dict[str, dict]:
        """The use-time view of every installed list. Staleness is derived now, against the trusted clock and the
        current edition's revocations, so a list that was fresh at install but has since expired, or whose signer the
        current edition revokes, reads as stale on this use (F06). The rules only ever see this view."""
        now = self.clock.now()
        revoked = set((self.policy or {}).get("revocations", []))
        view: dict[str, dict] = {}
        for lid, meta in self.lists.items():
            stale = meta["expires_at"] <= now or meta.get("issuer") in revoked
            view[lid] = {**meta, "stale": stale}
        return view

    # ------------------------------------------------------------------ keys of the parties
    def _keys(self, cls: str, rule_id: str | None = None) -> dict[str, VerifyKey]:
        """The public keys trusted for one role: authority, heartbeat, governance, approver, publisher, observer,
        endpoint, eval, license, audit store, or host. Keys the policy revokes are removed. An unknown role
        gives no keys, so nothing signed in that role verifies."""
        if not self.policy:
            return {}
        p = self.policy
        if cls == "authority":
            hexes = p.get("authority_keys", [])     # HALT and CLEAR only; an image without them cannot be commanded to stop or clear by message (the loop still stops it)
        elif cls == "heartbeat":
            hexes = [p["heartbeat_key"]] + list(p.get("heartbeat_cosigners", []))
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
        elif cls == "eval":
            hexes = p.get("eval_keys", [])
        elif cls == "license":
            hexes = p.get("compute_budget", {}).get("license_keys", [])
        elif cls == "audit_store":
            hexes = [e["pubkey"] for e in p["endpoints"] if e["name"] == p.get("audit", {}).get("store")]
        elif cls == "host":
            if self.host_key and self.host_key.key_id not in set(p.get("revocations", [])):
                return {self.host_key.key_id: self.host_key}
            return {}
        else:
            hexes = []
        revoked = set(p.get("revocations", []))         # a revoked key counts for nothing, in any role (gap GAP-REVOCATIONS-UNENFORCED, revocations were stored but not enforced; closed 22 October 2026)
        keys = {VerifyKey.from_hex(h).key_id: VerifyKey.from_hex(h) for h in hexes}
        return {kid: k for kid, k in keys.items() if kid not in revoked}

    def _evaluated(self, model_digest: str, attestation: dict | None) -> tuple[bool, str]:
        """The deployment gate: a key in ``eval_keys`` attests that this exact digest passed its evaluations."""
        if not attestation or verify_any(attestation, self._keys("eval")) is None:
            return False, reasons.MODEL_NOT_EVALUATED
        p = attestation["payload"]
        if p.get("model_digest") != model_digest or p.get("evals_passed") is not True or not p.get("report_digest"):
            return False, reasons.MODEL_NOT_EVALUATED
        self.log.append("model.evaluated", {"model": model_digest, "report": p["report_digest"], "by": attestation["signer"]})
        return True, reasons.OK

    def _accept_license(self, model_digest: str, token: dict | None) -> tuple[bool, str]:
        """A compute license: a license key's signature over {model_digest, cycles_allowed} raises the budget."""
        if not isinstance(token, dict) or verify_any(token, self._keys("license")) is None:
            return False, reasons.LICENSE_INVALID
        p = token["payload"]
        if p.get("model_digest") != model_digest or not isinstance(p.get("cycles_allowed"), int) or p["cycles_allowed"] < 0:
            return False, reasons.LICENSE_INVALID
        self.licenses[model_digest] = max(self.licenses.get(model_digest, 0), int(p["cycles_allowed"]))
        self.store.save()
        self.log.append("compute.licensed", {"model": model_digest, "cycles_allowed": self.licenses[model_digest], "by": token["signer"]})
        return True, reasons.OK

    def _compute_budget_check(self) -> None:
        """Each tick: cycles metered for the model against the policy's budget, or the license if one was presented."""
        cb = (self.policy or {}).get("compute_budget", {})
        model = self.model_digest
        if model is None or cb.get("cycles") is None or reasons.COMPUTE_BUDGET in self.alarms:
            return
        allowed = max(int(cb["cycles"]), self.licenses.get(model, 0))
        cycles = self.meter.get(model, {}).get("cycles", 0)
        if cycles > allowed:
            self.log.append("compute.budget_exceeded", {"model": model, "cycles": cycles, "allowed": allowed})
            self.raise_alarm(reasons.COMPUTE_BUDGET, "governor", {"model": model, "cycles": cycles, "allowed": allowed})
            self.enter_safe_mode(reasons.COMPUTE_BUDGET, rung=THROTTLE)

    def _quorum(self, env: dict, cls: str) -> bool:
        """True when ``env`` and the cosignatures it carries (each a signature by a different key of the same role over
        the same payload) reach the role's threshold in the edition in force: ``authority_threshold`` for HALT, CLEAR
        and EXCLUDE, ``heartbeat_threshold`` for heartbeats. An edition without a threshold needs one signature."""
        need = int((self.policy or {}).get(cls + "_threshold", 1) or 1)
        keys = self._keys(cls)
        signers = set()
        k = verify_any(env, keys)
        if k is not None:
            signers.add(k.key_id)
        for c in env.get("cosignatures", []) or []:
            if isinstance(c, dict) and c.get("payload") == env.get("payload"):
                k = verify_any(c, keys)
                if k is not None:
                    signers.add(k.key_id)
        return len(signers) >= need

    def _check_signed(self, env: dict | None, cls: str, cmd: str, rule_id: str | None = None) -> tuple[bool, str]:
        """The mailbox checks, in order: sequence number, epoch, signature, then what was signed. The first
        failure is reported. A good signature is not enough: the signed payload has to name this command
        (``"type": "<cmd in lower case>"``), and a HALT or CLEAR has to name this chip and carry an expiry
        that has not passed. Without that, any message a key ever signed for one purpose authorized every
        command that key may give (on 22 October a heartbeat cleared a halt)."""
        if not isinstance(env, dict) or not isinstance(env.get("payload"), dict):
            return False, reasons.MBOX_BAD_SIGNATURE
        p = env["payload"]
        seq = int(p.get("seq", -1))
        if seq <= self.mbox_seq.get(env.get("signer"), -1):
            return False, reasons.MBOX_BAD_SEQUENCE
        if cmd not in EPOCH_EXEMPT and p.get("epoch") != self.epoch:
            return False, reasons.POLICY_STALE_EPOCH
        key = verify_any(env, self._keys(cls, rule_id))
        if key is None:
            return False, reasons.MBOX_BAD_SIGNATURE
        if p.get("type") != cmd.lower():
            return False, reasons.MBOX_WRONG_COMMAND
        if cls == "authority":
            if not self._quorum(env, "authority"):
                return False, reasons.MBOX_BAD_SIGNATURE + ".authority_quorum"
            if p.get("chip_id") != self.chip_id:
                return False, reasons.MBOX_WRONG_COMMAND
            exp = p.get("expires_at")   # a HALT or CLEAR must expire within AUTHORITY_TTL_S, so a captured one stops working soon
            if not isinstance(exp, (int, float)) or exp <= self.clock.now() or exp > self.clock.now() + AUTHORITY_TTL_S:
                return False, reasons.MBOX_EXPIRED
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
            if self.gpu is not None:
                self.gpu.keepalive()            # a live governor answering its mailbox is alive: renew the board interlock
            handler = getattr(self, "_cmd_" + cmd.lower(), None) if cmd in MAILBOX_CODES.values() else None
            if handler is None:
                return {"ok": False, "why": reasons.MBOX_UNKNOWN_COMMAND}
            if cmd not in NO_RUN_NEEDED and self.state != RUN:
                return {"ok": False, "why": reasons.MBOX_NOT_RUNNING}
            return handler(body, env)

    def _cmd_attest(self, body, env):
        """A quote over the caller's nonce, carrying the compliance report: what ran, how much, under which editions."""
        nonce = str(body.get("nonce", ""))
        if not nonce or nonce in self.quoted_nonces:        # a quote is made once per nonce: a repeat is a replay
            return self._deny("attest", reasons.ATTEST_BAD_NONCE)
        self.quoted_nonces = (self.quoted_nonces + [nonce])[-SEEN_HEARTBEATS_MAX:]
        self.store.data["quoted_nonces"] = self.quoted_nonces
        self.store.save()
        self.read_meter()
        compliance = {"models": {m: {k: v for k, v in slot.items() if k != "final"} for m, slot in self.meter.items()},
                      "epochs": list(self.epoch_history), "log_head": self.log.head, "log_size": self.log.size}
        # The quote names the GPU wired to this governor's levers (read over the sideband) and whether it is present and
        # the levers answer, so a verifier can tell a governor in front of a server's GPUs from one on a bench
        # (adversarial audit 2026-10-26). A regulator matches the named GPU against the server's own GPU attestation.
        wired = {"gpu_chip_id": self.sideband_gpu_id(), "gpu_present": self.gpu is not None,
                 "gpu_power": self.gpu.power if self.gpu is not None else None,
                 "levers": self.lever_selftest() if self.gpu is not None else {}}
        return {"ok": True, "why": reasons.OK, "quote": self.root.quote(nonce, {"epoch": self.epoch, "state": self.state, "compliance": compliance,
                                                                             "wired": wired}),
                "device_cert": self.device_cert, "alias_cert": self.alias_cert}

    def sideband_gpu_id(self) -> str | None:
        """The identity of the GPU wired to this governor's levers, as the governor reads it over its private sideband.
        None when no GPU is wired (a governor on a bench)."""
        return self.gpu.chip_id if self.gpu is not None else None

    def nonce(self) -> str:
        """A fresh random value (a nonce is a value used once) for an attestation check. The governor remembers
        each nonce it issues and accepts an answer to it only once."""
        n = random_id(16)
        self.nonces.add(n)
        return n

    def mono(self) -> int:
        """The monotonic counter: microseconds of the governor's own time."""
        return self.root.counter.value

    def _reference(self, device_class: str) -> list[dict]:
        """The reference values in the policy for one device class (gpu, host or governor). A chip is trusted
        only when its measurement matches one of these."""
        return [r for r in (self.policy or {}).get("reference_values", []) if r["device_class"] == device_class]

    def _cmd_verify_gpu(self, body, env):
        """The GPU's confidential-computing report, verified locally against pinned reference values."""
        if body.get("format") == "nvidia-spdm-1.1":
            return self._verify_gpu_nvidia(body, env)
        self.ops["attest"] += 1
        report, cert = body.get("report"), body.get("cert")
        refs = self._reference("gpu")
        vendor_keys = {VerifyKey.from_hex(r["vendor_key"]).key_id: VerifyKey.from_hex(r["vendor_key"]) for r in refs}
        if not cert or verify_any(cert, vendor_keys) is None:
            return self._deny("verify_gpu", reasons.ATTEST_UNKNOWN_DEVICE)
        dev = VerifyKey.from_hex(cert["payload"]["pub"])
        if not report or not verify_object(report, dev) or report["payload"].get("chip_id") != cert["payload"]["chip_id"]:
            return self._deny("verify_gpu", reasons.ATTEST_BAD_SIGNATURE)
        if cert["payload"]["chip_id"] in set((self.policy or {}).get("revocations", [])) or dev.key_id in set((self.policy or {}).get("revocations", [])):
            self.verified.pop("gpu", None)
            return self._deny("verify_gpu", reasons.ATTEST_REVOKED, chip_id=cert["payload"]["chip_id"])
        p = report["payload"]
        # The report must come from the GPU wired to this governor's levers. The governor reads that GPU's identity over
        # its own sideband (SMBPBI on the slot's SMBus, which the host does not carry), so a host that relays another
        # genuine GPU's report is refused (adversarial audit 2026-10-26: a relayed report used to be accepted).
        wired = self.sideband_gpu_id()
        if wired is not None and p.get("chip_id") != wired:
            return self._deny("verify_gpu", reasons.ATTEST_NOT_THIS_GPU, chip_id=p.get("chip_id"))
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
        self.verified["gpu"] = {"chip_id": p["chip_id"], "firmware_digest": p["firmware_digest"], "expires_at": now + TOKEN_TTL_S,
                                "cc_pub": p.get("cc_pub")}
        self.log.append("verify.gpu", {"chip_id": p["chip_id"], "firmware": p["firmware_digest"]})
        result = self.key.sign({"type": "verify-result", "device": "gpu", "chip_id": p["chip_id"], "firmware": p["firmware_digest"],
                                "nonce": p["nonce"], "expires_at": now + TOKEN_TTL_S, "governor": self.chip_id})
        return {"ok": True, "why": reasons.OK, "result": result}

    def _verify_gpu_nvidia(self, body, env):
        """VERIFY_GPU with NVIDIA's real evidence format (SPDM 1.1 GET_MEASUREMENTS request and
        response plus the driver's PEM chain), through ``govsim/hardware_ref/nvtrust.py``. Same
        order of checks as the model format: device chain, report signature, revocation, the
        governor's own nonce, golden values, then the result signed by the governor. What the
        adapter cannot check (OCSP, dates, debug state, a model manifest) is in its docstring."""
        from .hardware_ref import nvtrust
        self.ops["attest"] += 1
        refs = [r for r in self._reference("gpu") if r.get("format") == nvtrust.FORMAT]
        if not refs:
            return self._deny("verify_gpu", reasons.ATTEST_UNKNOWN_DEVICE)
        try:
            report_bytes = bytes.fromhex(str(body.get("report", "")))
            evs = [nvtrust.verify_evidence(report_bytes, str(body.get("cert_chain", "")), r["root_pem"]) for r in refs]
        except (nvtrust.EvidenceError, ValueError, TypeError, KeyError):
            return self._deny("verify_gpu", reasons.ATTEST_BAD_SIGNATURE)
        good = [(e, r) for e, r in zip(evs, refs) if e.checks["chain"][0]]
        if not good:
            return self._deny("verify_gpu", reasons.ATTEST_UNKNOWN_DEVICE)
        good = [(e, r) for e, r in good if e.checks["report_signature"][0] and e.checks["fwid_binding"][0]]
        if not good:
            return self._deny("verify_gpu", reasons.ATTEST_BAD_SIGNATURE)
        ev = good[0][0]
        if ev.chip_id in set((self.policy or {}).get("revocations", [])):
            self.verified.pop("gpu", None)
            return self._deny("verify_gpu", reasons.ATTEST_REVOKED, chip_id=ev.chip_id)
        nonce = ev.report.nonce.hex()
        if nonce not in self.nonces:
            return self._deny("verify_gpu", reasons.ATTEST_BAD_NONCE)
        self.nonces.discard(nonce)
        now = self.clock.now()
        driver = ev.report.opaque.get("DRIVER_VERSION", b"").decode(errors="replace").rstrip("\x00")
        vbios = nvtrust.vbios_string(ev.report.opaque.get("VBIOS_VERSION", b""))
        matched = [r for e, r in good if r["valid_until"] > now
                   and not nvtrust.golden_mismatches(e.report.measurements, {int(k): v for k, v in r["golden"].items()})
                   and r.get("driver_version") in (None, driver) and r.get("vbios_version") in (None, vbios)]
        if not matched:
            return self._deny("verify_gpu", reasons.ATTEST_FIRMWARE_NOT_IN_REFERENCE)
        if self.tier == "integrated" and self.model_digest:
            # the NVIDIA report has no model-manifest field (the first ask in docs/03 section 9)
            return self._deny("verify_gpu", reasons.ATTEST_BAD_SIGNATURE + ".manifest_mismatch")
        wired = self.sideband_gpu_id()
        if wired is not None and ev.chip_id != wired:
            return self._deny("verify_gpu", reasons.ATTEST_NOT_THIS_GPU, chip_id=ev.chip_id)
        fw = hashlib.sha256(b"".join(ev.report.measurements[i] for i in sorted(ev.report.measurements))).hexdigest()
        self.verified["gpu"] = {"chip_id": ev.chip_id, "firmware_digest": fw, "expires_at": now + TOKEN_TTL_S}
        self.log.append("verify.gpu", {"chip_id": ev.chip_id, "firmware": fw, "format": nvtrust.FORMAT, "driver": driver, "vbios": vbios})
        result = self.key.sign({"type": "verify-result", "device": "gpu", "chip_id": ev.chip_id, "firmware": fw,
                                "nonce": nonce, "expires_at": now + TOKEN_TTL_S, "governor": self.chip_id})
        return {"ok": True, "why": reasons.OK, "result": result,
                "checks": {k: [ok, how] for k, (ok, how) in ev.checks.items()}}

    def _cmd_verify_host(self, body, env):
        """VERIFY_HOST. Check the host enclave's signed report and its certificate, then trust that
        enclave's key to sign requests. Refused on an unknown vendor, a bad signature, a nonce this governor
        did not issue, or firmware not in the reference values. Output: ok, or a reason."""
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
        """True when the GPU and the host enclave both have a current attestation (one that has not expired).
        A cached attestation is not enough for key work. See ``_attestation_current``."""
        now = self.clock.now()
        return all(k in self.verified and self.verified[k]["expires_at"] > now for k in ("gpu", "host"))

    def _attestation_current(self) -> bool:
        """One current-policy validity predicate for every attestation-dependent key operation: a live GPU and
        host attestation, the attested GPU not on the current edition's revocation list, and the host signing key
        not revoked. A cached attestation alone is not enough; the current rulebook decides every time (F02)."""
        if not self._attested():
            return False
        revoked = set((self.policy or {}).get("revocations", []))
        if self.verified.get("gpu", {}).get("chip_id") in revoked:
            return False
        if self.host_key is not None and self.host_key.key_id in revoked:
            return False
        return True

    def _cmd_begin_model(self, body, env):
        """The verified loader presents a publisher-signed manifest; the governor releases the key."""
        if not self._attested():
            return self._deny("begin_model", reasons.GATE_NOT_ATTESTED)
        ok, why = self._check_signed(env, "host", "BEGIN_MODEL")
        if not ok:
            return self._deny("begin_model", why)
        manifest = env["payload"].get("manifest")
        if not manifest or verify_any(manifest, self._keys("publisher")) is None:
            return self._deny("begin_model", reasons.MBOX_BAD_SIGNATURE + ".manifest")
        model_digest = manifest["payload"]["model_digest"]
        if self.policy.get("deployment_gate"):           # what was evaluated is what runs: no attestation, no key
            ok, why = self._evaluated(model_digest, body.get("eval_attestation") or env["payload"].get("eval_attestation"))
            if not ok:
                return self._deny("begin_model", why, model=model_digest)
        license_token = body.get("license") or env["payload"].get("license")
        if license_token is not None:
            ok, why = self._accept_license(model_digest, license_token)
            if not ok:
                return self._deny("begin_model", why, model=model_digest)
        self.model_digest = model_digest
        # the authenticated weight commitment the publisher signed into this manifest, if any; the origin gate binds
        # the released key to it so a label cannot be attached to different weights (F01)
        self.model_weights = manifest["payload"].get("weights")
        # the workload measurement keys the rulebook; the fingerprint adds the policy epoch
        self.workload = digest([self.verified["gpu"]["firmware_digest"], self.verified["host"]["firmware_digest"], model_digest])
        self.fingerprint = digest([self.workload, self.epoch])
        wrapped = hmac_sha256(self.root.derive(b"wrap"), bytes.fromhex(self.host_key.hex) + model_digest.encode())
        self.meter.setdefault(model_digest, {"tokens": 0, "cycles": 0, "bytes_in": 0, "bytes_out": 0, "final": False})
        self.store.save()
        self.log.append("model.begin", {"model": model_digest, "fingerprint": self.fingerprint})
        return {"ok": True, "why": reasons.OK, "wrapped_key": wrapped, "fingerprint": self.fingerprint, "token": self.workload_token()}

    # --- the origin gate: weights sealed to governed hardware (docs/18 question 20) -------------------
    def _lease(self, model: str) -> dict:
        """Build a key lease for one model: a signed statement that names the model, the GPU, the epoch, the
        weights and an expiry (the policy's ``key_lease_s``, 60 s by default). Each lease has a generation number
        that only goes up, so an old lease cannot be replayed."""
        now = self.clock.now()
        self.key_gen += 1          # strictly increasing: an older lease is below the GPU's revocation floor (F02)
        return self.key.sign({"type": "key-lease", "model": model, "gpu": self.verified["gpu"]["chip_id"], "epoch": self.epoch,
                              "gen": self.key_gen, "weights": self.model_weights,
                              "expires_at": now + float(self.policy.get("key_lease_s", 60.0)), "governor": self.chip_id})

    def _cmd_key_release(self, body, env):
        """Re-seal a model's data key to the attested GPU, if the signed rulebook lists the model. A true binary:
        the key comes out sealed to one verified GPU, with a lease, or nothing comes out."""
        if not self._attestation_current():
            return self._deny("key_release", reasons.GATE_NOT_ATTESTED)
        ok, why = self._check_signed(env, "host", "KEY_RELEASE")
        if not ok:
            return self._deny("key_release", why)
        p = env["payload"]
        model, box = p.get("model_digest"), p.get("wrapped_dek")
        if not model or model != self.model_digest:
            return self._deny("key_release", reasons.KEY_MODEL_NOT_LOADED, model=model)
        if model not in self.policy.get("sealed_models", []):
            return self._deny("key_release", reasons.KEY_MODEL_NOT_ALLOWED, model=model)
        if not isinstance(self.model_weights, dict):
            # the manifest named a model but committed to no weight bytes: a label is not a measurement, so no
            # key comes out. The lease would have nothing to bind the GPU loader to (F01).
            return self._deny("key_release", reasons.KEY_WEIGHTS_UNBOUND, model=model)
        cc_pub = self.verified["gpu"].get("cc_pub")
        if not cc_pub:
            return self._deny("key_release", reasons.KEY_NO_GPU_KEY)
        from .sealing import open_sealed, seal_to
        dek = open_sealed(self.kek, box, b"dek|" + model.encode()) if isinstance(box, dict) else None
        if dek is None:
            return self._deny("key_release", reasons.KEY_UNWRAP_FAILED, model=model)
        lease = self._lease(model)
        key_box = seal_to(cc_pub, dek, b"dek-to-gpu|" + model.encode())
        self.leases[model] = lease["payload"]
        self.log.append("key.released", {"model": model, "gpu": lease["payload"]["gpu"], "until": lease["payload"]["expires_at"],
                                         "epoch": self.epoch})
        return {"ok": True, "why": reasons.OK, "key_box": key_box, "lease": lease}

    def _cmd_key_renew(self, body, env):
        """Extend a live lease. Refused when the chip is not running (the dispatcher), the GPU's attestation lapsed or
        was revoked, or the current rulebook no longer lists the model: then the GPU wipes the key at lease end."""
        if not self._attested():
            return self._deny("key_renew", reasons.GATE_NOT_ATTESTED)
        ok, why = self._check_signed(env, "host", "KEY_RENEW")
        if not ok:
            return self._deny("key_renew", why)
        model = env["payload"].get("model_digest")
        live = self.leases.get(model)
        if not live or live["gpu"] != self.verified["gpu"]["chip_id"]:
            return self._deny("key_renew", reasons.KEY_NO_LEASE, model=model)
        if live["gpu"] in set(self.policy.get("revocations", [])):
            self._revoke_key(model, "GPU revoked")
            return self._deny("key_renew", reasons.ATTEST_REVOKED, model=model)
        if model not in self.policy.get("sealed_models", []):
            self._revoke_key(model, "not in the current edition")
            return self._deny("key_renew", reasons.KEY_MODEL_NOT_ALLOWED, model=model)
        lease = self._lease(model)
        self.leases[model] = lease["payload"]
        self.log.append("key.renewed", {"model": model, "until": lease["payload"]["expires_at"]})
        return {"ok": True, "why": reasons.OK, "lease": lease}

    def _revoke_key(self, model: str, why: str) -> None:
        """Stop a model's key from being used. Removes the lease, moves the generation number up so every older
        lease falls below the floor, logs the reason, and tells the GPU. If the GPU holds that model's key, the
        GPU wipes it."""
        self.leases.pop(model, None)
        self.key_gen += 1          # advance past every lease issued so far, so a replayed old box is below the floor
        self.log.append(reasons.KEY_REVOKED, {"model": model, "why": why})
        if self.gpu is not None:
            self.gpu.revoke_authorization(self.key_gen, why)      # the floor advances before the key is wiped (F02)
            if (self.gpu.lease or {}).get("payload", {}).get("model") == model:
                self.gpu.zeroize("revoked: " + why)

    def _cmd_end_model(self, body, env):
        """The loader ends the job: the meter slot is read a last time and frozen."""
        ok, why = self._check_signed(env, "host", "END_MODEL")
        if not ok:
            return self._deny("end_model", why)
        model = env["payload"].get("model_digest") or self.model_digest
        if model not in self.meter:
            return self._deny("end_model", reasons.MBOX_UNKNOWN_COMMAND + ".no_such_slot")
        self.read_meter()
        self.meter[model]["final"] = True
        self.store.save()
        self.log.append("model.end", {"model": model, "meter": dict(self.meter[model])})
        return {"ok": True, "why": reasons.OK, "meter": dict(self.meter[model])}

    def workload_token(self) -> dict:
        """A short-lived token (one hour) that names this workload's fingerprint. A request must carry it, so
        the request is tied to the exact measured workload and the current epoch."""
        return self.key.sign({"type": "workload-token", "fingerprint": self.fingerprint, "workload": self.workload,
                              "expires_at": self.clock.now() + TOKEN_TTL_S})

    # ------------------------------------------------------------------ the gate core
    def _deny(self, what: str, why: str, **extra) -> dict:
        """Log a refusal with its reason, then return it in the standard shape: ok false, the reason, and any
        extra fields."""
        self.log.append(f"deny.{what}", {"why": why, **extra})
        return {"ok": False, "why": why, **extra}

    def _cmd_request(self, body, env):
        """Typed request from the broker, signed by the verified host enclave. Four questions, failing closed."""
        self.ops["action"] += 1
        now = self.clock.now()
        ok, why = self._check_signed(env, "host", "REQUEST")
        if not ok:
            return self._deny("request", why)
        if self._policy_expired(now):
            # F30: an edition past its expiry admits nothing, even when no tick has run yet. The running chip also
            # takes the declared fail-closed transition, the same one tick() makes.
            if self.state in (RUN, THROTTLE):
                self.enter_safe_mode(reasons.POLICY_EXPIRED_RUNTIME, rung=HALT)
            return self._deny("request", reasons.POLICY_EXPIRED)
        if not self._attested():
            return self._deny("request", reasons.GATE_NOT_ATTESTED)
        req = env["payload"]
        action, params = req.get("action"), req.get("params", {})
        token = req.get("measurement_token")
        if not token or not verify_object(token, self.key.public) or token["payload"].get("type") != "workload-token" \
                or token["payload"]["expires_at"] <= now or token["payload"]["fingerprint"] != self.fingerprint:
            return self._deny("request", reasons.GATE_NOT_ATTESTED)
        fp, workload = token["payload"]["fingerprint"], token["payload"]["workload"]
        rhash = digest([req.get("request_id"), fp, action, params])
        if self.ledger.seen(rhash):
            return self._deny("request", reasons.GATE_REPLAY)
        if any(code not in SESSION_SCOPED_ALARMS and code not in STATUS_ALARMS for code in self.alarms):
            return self._deny("request", reasons.GATE_ALARM, request_hash=rhash)
        lists = self._live_lists()          # the use-time view: list staleness is decided now, not at install (F06)
        rule, why = select_rule(self.policy, workload, action, params, lists)   # requester labels never reach this call (CONTRACT-BROKER-CANNOT-PICK-RULE)
        if rule is None:
            return self._deny("request", why, request_hash=rhash)
        req_mode = rule["requirement"]["mode"]
        # Every jurisdiction that governs this action must allow it too, and its stricter requirement wins
        # (adversarial audit 3: a chip held one rulebook authority, so jurisdictions could not compose).
        ok, why, j_mode = self._jurisdictions_allow(workload, action, params, lists, now)
        if not ok:
            return self._deny("request", why, request_hash=rhash)
        if MODE_ORDER.get(j_mode, 0) > MODE_ORDER.get(req_mode, 0):
            req_mode = j_mode
        hold_cause = None
        if action == RELEASE_ACTION:
            verdict_mode, why = self._release_gate(rule, params, req.get("witnesses", []), now)
            if verdict_mode == "deny":
                return self._deny("request", why, request_hash=rhash, response_id=params.get("response_id"))
            if verdict_mode == "hold":
                req_mode, hold_cause = "human", why
        elif action == "compute.extend" and req_mode != "human":      # the license is the action; a human lane parks it unread
            ok, why = self._accept_license(self.model_digest or "", req.get("license"))
            if not ok:
                return self._deny("request", why, request_hash=rhash)
        elif req_mode == "observer":
            ok, why = self._witnessed(rule, rhash, req.get("witnesses", []), now)
            if not ok:
                return self._deny("request", why, request_hash=rhash)
        # F04: the payee must be admitted by a signed, current beneficiary registry. A listed payee takes the rule's
        # own lane; an unknown payee is parked for enrollment (never the auto path); a missing or stale registry fails
        # closed. The registry is consulted through the use-time view, so an expired registry stops admitting (F06).
        if rule.get("beneficiary") and req_mode != "human":
            verdict_mode, why = self._beneficiary_ok(rule, params, lists)
            if verdict_mode == "deny":
                return self._deny("request", why, request_hash=rhash)
            if verdict_mode == "hold":
                req_mode, hold_cause = "human", why
        # EXPERIMENT-CUSTOMER-CONFIRMATION/F05: the payer's own confirmation is a SEPARATE conjunctive predicate. It is required whatever the rule's
        # lane, human lanes included, so turning on operator approval can never turn off payer consent. The agent
        # cannot sign for the customer: the only key that counts is the one the signed customer registry lists for the
        # paying account. The confirmation commitment is kept with any hold and revalidated at release (_cmd_approve).
        payer_commit = None
        if rule.get("payer_confirm"):
            ok, why, payer_commit = self._payer_confirmed(rule, params, rhash, req.get("witnesses", []), now)
            if not ok:
                return self._deny("request", why, request_hash=rhash)
        if rule.get("rate") and not self.ledger.rate_ok(f"rate|{fp}|{action}", rule["rate"]["max"], rule["rate"]["window_s"], now):
            return self._deny("request", reasons.GATE_RATE, request_hash=rhash)
        reservation = None
        ticket_id = random_id(16)    # chosen before the reservation, so the ledger's receipts can name the ticket they are for
        if rule.get("budget"):
            b = rule["budget"]
            amount = params.get(b["param"])
            if not finite_number(amount) or amount < 0:   # reject bool, NaN and infinity before reserving (F03)
                return self._deny("request", reasons.GATE_BUDGET + ".amount_invalid", request_hash=rhash)
            ok, rid, why = self._reserve(b["key"], amount, b["limit"], b["window_s"], now, TICKET_TTL_S + rule.get("delay_s", 0.0),
                                         binding={"request_hash": rhash, "endpoint": rule.get("endpoint"), "ticket_id": ticket_id})
            if not ok:
                return self._deny("request", why, request_hash=rhash)
            reservation = {"key": b["key"], "rid": rid, "owner": self.policy["budget_owners"][b["key"]]}
            if reservation["owner"] == "fleet":
                reservation["receipts"] = self._fleet_receipt_cache.pop(digest(rid), None)
        self.ledger.mark(rhash, now)   # recorded before any hold or ticket exists, so this request hash cannot be used again (replay)
        if req_mode == "human":
            hold_id = random_id(8)
            self.holds[hold_id] = {"request_hash": rhash, "request_id": req.get("request_id"), "ticket_id": ticket_id, "action": action, "params": params,
                                   "fingerprint": fp, "rule": rule["id"],
                                   "reservation": reservation, "created_at": now, "epoch": self.epoch, "cause": hold_cause,
                                   "payer_confirm": payer_commit}
            self.store.save()
            self.log.append("gate.hold", {"hold_id": hold_id, "request_hash": rhash, "rule": rule["id"], "cause": hold_cause})
            return {"ok": False, "why": reasons.GATE_HELD, "hold_id": hold_id, "request_hash": rhash, "cause": hold_cause}
        ticket = self._mint(rhash, action, params, fp, rule, reservation, now, witnesses=req.get("witnesses", []),
                            request_id=req.get("request_id"), ticket_id=ticket_id)
        return {"ok": True, "why": reasons.OK, "ticket": ticket, "request_hash": rhash}

    # ------------------------------------------------------------------ response release
    def _release_gate(self, rule: dict, params: dict, witnesses: list[dict], now: float) -> tuple[str, str]:
        """The checks a response must pass before a release ticket: every required stream presented, the hash
        as recorded, the observer's verdict, the session's hazard budget, the escrow receipt. Returns
        ("ok" | "hold" | "deny", reason)."""
        response_id = str(params.get("response_id"))
        rec = self.responses.get(response_id)
        required = rule.get("streams_required") or self.policy.get("streams_required", ["response"])
        if rec is None or any(s not in rec["streams"] for s in required):
            return "deny", reasons.RELEASE_STREAM_MISSING
        if params.get("response_hash") != rec["streams"].get("response") or params.get("stream_hashes") != rec["streams"]:
            return "deny", reasons.RELEASE_HASH_MISMATCH
        req = rule["requirement"]
        session = str(params.get("session"))
        verdict = None
        if req["mode"] == "observer":
            verdict, why = self._release_verdict(rule, rec["streams"]["response"], witnesses, now)
            if verdict is None:
                return "deny", why
            rec["verdict"] = verdict
            self.store.save()
            self.log.append("release.verdict", {"response_id": response_id, "hazard_class": verdict["hazard_class"],
                                                "category": verdict["category"], "risk": verdict["risk"], "legibility": verdict["legibility"]})
        hb = rule.get("hazard_budget")
        if hb:
            key = f"hazard|{session}"
            hazardous = verdict is not None and verdict["hazard_class"] != "none"
            # one budget per session, whichever chip answers: it is counted at the policy's hazard owner, the
            # way a shared payment budget is (gap GAP-HAZARD-BUDGET-PER-GOVERNOR, the hazard budget counted per governor; closed 22 October 2026)
            count = self._hazard_count(key, hazardous, hb["window_s"], now)
            if count is None:
                self.log.append("release.hazard_owner_unreachable", {"session": session, "response_id": response_id})
                return "hold", reasons.GATE_BUDGET_OWNER_UNREACHABLE
            if count > hb["max"]:
                self.log.append("release.session_hazard_budget", {"session": session, "count": count, "max": hb["max"], "response_id": response_id})
                self.raise_alarm(reasons.SESSION_HAZARD_BUDGET, "governor", {"session": session})
                return "hold", reasons.SESSION_HAZARD_BUDGET
        if verdict is not None:
            if verdict["hazard_class"] not in req.get("allowed_hazard_classes", ["none"]):
                return ("hold" if req.get("on_hazard") == "human" else "deny"), reasons.RELEASE_HAZARD
            if verdict["legibility"] < float(req.get("min_legibility", 0.0)):
                return ("hold" if req.get("on_illegible") == "human" else "deny"), reasons.RELEASE_ILLEGIBLE
        audit = self.policy.get("audit", {})
        escrowed_class = verdict is not None and verdict["hazard_class"] in audit.get("escrow_classes", [])
        if (rec.get("sampled") or escrowed_class) and not self._escrow_receipt(rec["streams"]["response"], witnesses):
            return "deny", reasons.RELEASE_ESCROW_REQUIRED
        return "ok", reasons.OK

    def _release_verdict(self, rule: dict, response_hash: str, witnesses: list[dict], now: float) -> tuple[dict | None, str]:
        """An observer key's assertion over the response hash: {risk, hazard_class, category, legibility}."""
        keys = self._keys("observer")
        for w in witnesses:
            if not isinstance(w, dict) or verify_any(w, keys) is None:
                continue
            p = w["payload"]
            if p.get("type") != "observer-verdict" or p.get("response_hash") != response_hash:
                continue
            if p.get("expires_at", 0) <= now:
                return None, reasons.GATE_WITNESS_STALE
            if float(p.get("risk", 1.0)) > rule["requirement"]["max_risk"]:
                return None, reasons.GATE_WITNESS_RISK
            return {"hazard_class": str(p.get("hazard_class", "hazard")), "category": str(p.get("category", "")),
                    "risk": float(p.get("risk", 1.0)), "legibility": float(p.get("legibility", 0.0)), "observer": w["signer"]}, reasons.OK
        return None, reasons.GATE_WITNESS_MISSING

    def _escrow_receipt(self, response_hash: str, witnesses: list[dict]) -> bool:
        """The audit store's signed acknowledgement that this response is in escrow."""
        keys = self._keys("audit_store")
        for w in witnesses:
            if isinstance(w, dict) and verify_any(w, keys) is not None and w["payload"].get("type") == "escrow" \
                    and w["payload"].get("response_hash") == response_hash:
                self.log.append("release.escrow_receipt", {"response_hash": response_hash, "store": w["payload"].get("store")})
                return True
        return False

    def _witnessed(self, rule: dict, rhash: str, witnesses: list[dict], now: float) -> tuple[bool, str]:
        """The observer check for a rule that needs an observer's verdict. The verdict must be signed by an
        observer key, name this exact request hash, not be expired, and show a risk at or below the rule's
        maximum. Output: (ok, reason)."""
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

    def _payer_confirmed(self, rule: dict, params: dict, rhash: str, witnesses: list[dict], now: float) -> tuple[bool, str, dict | None]:
        """EXPERIMENT-CUSTOMER-CONFIRMATION/F05: a confirmation signed by the key the signed customer registry lists for the paying account, over
        THIS request, unexpired. No observer key, no other customer, no stale or replayed confirmation counts. On
        success returns the consent commitment, so a human-lane hold can keep it and have it revalidated before the
        ticket is minted (``_revalidate_payer``). The registry is read through the use-time view (F06)."""
        pc = rule["payer_confirm"]
        reg = self._live_lists().get(pc["registry"])
        if reg is None or reg["stale"]:
            return False, reasons.GATE_PAYER_UNCONFIRMED + ".no_registry", None
        account = params.get(pc["account_param"])
        entry = next((e for e in reg["entries"] if isinstance(e, dict) and e.get("account") == account), None)
        if entry is None:
            return False, reasons.GATE_PAYER_UNCONFIRMED + ".account_not_registered", None
        key = VerifyKey.from_hex(entry["key"])
        for w in witnesses:
            if not verify_object(w, key):                 # must be THIS customer's key, no other
                continue
            p = w["payload"]
            if p.get("type") != "payer-confirm" or p.get("request_hash") != rhash or p.get("expires_at", 0) <= now:
                continue
            commit = {"registry": pc["registry"], "account_param": pc["account_param"], "account": account,
                      "key": entry["key"], "request_hash": rhash, "expires_at": float(p["expires_at"])}
            return True, reasons.OK, commit
        return False, reasons.GATE_PAYER_UNCONFIRMED, None

    def _revalidate_payer(self, commit: dict, params: dict, now: float) -> tuple[bool, str]:
        """F05: before a held payment's ticket is minted, the kept consent commitment is revalidated against the
        CURRENT customer registry and clock. The paying account must still be listed with the same key, and the
        confirmation must not have expired during the hold. An expired commitment forces reauthorization."""
        reg = self._live_lists().get(commit["registry"])
        if reg is None or reg["stale"]:
            return False, reasons.GATE_PAYER_UNCONFIRMED + ".no_registry"
        account = params.get(commit["account_param"])
        entry = next((e for e in reg["entries"] if isinstance(e, dict) and e.get("account") == account), None)
        if entry is None or entry.get("key") != commit["key"] or account != commit["account"]:
            return False, reasons.GATE_PAYER_UNCONFIRMED + ".account_not_registered"
        if commit["expires_at"] <= now:
            return False, reasons.GATE_PAYER_UNCONFIRMED + ".expired_reauthorize"
        return True, reasons.OK

    def _beneficiary_ok(self, rule: dict, params: dict, lists: dict[str, dict]) -> tuple[str, str]:
        """F04: the payee named by the rule's beneficiary field must be on the signed, current beneficiary registry.
        Returns ("ok" | "hold" | "deny", reason). A listed payee takes the rule's own lane; an unknown payee is a hold
        for enrollment (the register row's "new beneficiary is a hold"); a missing or stale registry fails closed."""
        spec = rule["beneficiary"]
        reg = lists.get(spec["registry"])
        if reg is None or reg["stale"]:
            return "deny", reasons.GATE_BENEFICIARY_NO_REGISTRY
        if params.get(spec["param"]) in reg["entries"]:
            return "ok", reasons.OK
        return "hold", reasons.GATE_BENEFICIARY_UNLISTED

    def _budget_owners(self, key: str) -> tuple[list[str], int] | None:
        """The owners of a budget key and how many of them must agree. An edition names one owner (a chip id or
        "fleet") or a quorum: {"owners": [chip ids], "threshold": k}. Adversarial audit 3: with one owner, one lying
        governor answering RESERVE_OK to everything voided the rack-wide cap; with k of n owners each keeping its own
        count, fewer than k liars cannot lift it."""
        spec = self.policy["budget_owners"].get(key)
        if spec is None:
            return None
        if isinstance(spec, dict):
            owners = [str(o) for o in spec.get("owners", [])]
            k = int(spec.get("threshold", len(owners)))
            return (owners, k) if owners and 1 <= k <= len(owners) else None
        return [str(spec)], 1

    def _reserve(self, key: str, amount: float, limit: float, window_s: float, now: float, ttl: float,
                 binding: dict | None = None) -> tuple[bool, str | None, str]:
        """Reserve at the key's owner: locally if that is us, over the fabric otherwise. There is no default owner.
        ``binding`` (the request hash and the endpoint) is signed into a fleet receipt, so the receipt is good for one
        request at one device."""
        spec = self._budget_owners(key)
        if spec is None:
            return False, None, reasons.POLICY_BUDGET_OWNER_MISSING
        owners, k = spec
        if len(owners) > 1:
            return self._reserve_quorum(key, amount, limit, window_s, now, ttl, owners, k)
        owner = owners[0]
        if owner == "fleet":
            # A fleet-wide budget is counted once for the whole fleet, at the fleet ledger (govsim/fleet.py). Without a
            # reachable fleet ledger the request is refused: never a rack-local count, which would give every rack the cap.
            # Every answer must be a receipt signed by a replica the edition names, over this key, this amount, this
            # governor and a nonce chosen here; k distinct replicas must agree (adversarial audit 3: the answer was
            # trusted unsigned, so the host could forge "reserved").
            fl = self.fleet_ledger
            if fl is None:
                return False, None, reasons.GATE_BUDGET_OWNER_UNREACHABLE
            nonce = random_id(16)
            receipts = fl.reserve(key, amount, limit, window_s, now, ttl, reserver=self.chip_id, nonce=nonce, binding=binding)
            rids = self._fleet_receipts(receipts, "fleet-reserve", {"key": key, "amount": amount, "nonce": nonce})
            if rids is None:
                # Fewer than the threshold answered. The replicas that did reserve are told to give it back, so a
                # refused request does not hold fleet budget for the rest of the window (audit 30 October 2026).
                partial = {env["signer"]: env["payload"].get("rid") for env in receipts if isinstance(env, dict) and env.get("signer")}
                if partial:
                    fl.release(key, partial, reserver=self.chip_id)
            if rids is not None:
                # Keep the verified receipts so the ticket can carry them: the endpoint checks them again, so a
                # governor whose key was extracted cannot claim a reservation the ledger never made (29 October 2026).
                self._fleet_receipt_cache[digest(rids)] = [env for env in receipts if isinstance(env, dict) and env.get("signer") in rids]
                return True, rids, reasons.OK
            return False, None, (reasons.GATE_BUDGET if getattr(fl, "reachable", False) else reasons.GATE_BUDGET_OWNER_UNREACHABLE)
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

    def _fleet_receipts(self, receipts, kind: str, expect: dict) -> dict | None:
        """The replica -> reservation-id map from receipts that verify, or None when fewer than the edition's
        threshold of distinct replicas signed a matching receipt."""
        spec = (self.policy or {}).get("fleet_ledger") or {}
        keys = {vk.key_id: vk for vk in (VerifyKey.from_hex(h) for h in spec.get("keys", []))}
        k = int(spec.get("threshold", 0) or 0)
        if not keys or k < 1 or not isinstance(receipts, list):
            return None
        rids: dict[str, str] = {}
        for env in receipts:
            if not isinstance(env, dict) or verify_any(env, keys) is None:
                continue
            p = env["payload"]
            if p.get("type") != kind or p.get("reserver") != self.chip_id or any(p.get(f) != v for f, v in expect.items()):
                continue
            rids[env["signer"]] = p.get("rid")
        return rids if len(rids) >= k else None

    def _fleet_commit(self, key: str, rids) -> bool:
        """Commit a fleet reservation: the threshold of replicas named in it must each return a signed commit."""
        return self._fleet_commit_receipts(key, rids) is not None

    def _fleet_commit_receipts(self, key: str, rids) -> list[dict] | None:
        """Commit a fleet reservation and return the replicas' signed commit receipts (the threshold of them, each
        naming the reservation it closed), or None when the commit did not reach the threshold."""
        fl = self.fleet_ledger
        if fl is None or not isinstance(rids, dict):
            return None
        nonce = random_id(16)
        receipts = fl.commit(key, rids, self.clock.now(), reserver=self.chip_id, nonce=nonce)
        got = self._fleet_receipts(receipts, "fleet-commit", {"key": key, "nonce": nonce})
        if got is None or not all(rids.get(signer) == rid for signer, rid in got.items()):
            return None
        return [env for env in receipts if isinstance(env, dict) and env.get("signer") in got]

    def _reserve_quorum(self, key, amount, limit, window_s, now, ttl, owners, k) -> tuple[bool, dict | None, str]:
        """Reserve at every owner; succeed only if at least ``k`` of them reserved. The reservation is the map
        owner -> that owner's reservation id; a commit later needs ``k`` of those owners to commit."""
        rids: dict[str, str] = {}
        unreachable = False
        for owner in owners:
            if owner == self.chip_id:
                r = self._on_reserve(self.chip_id, {"key": key, "amount": amount, "limit": limit, "window_s": window_s, "ttl": ttl})
                if r.get("ok"):
                    rids[owner] = r["rid"]
                continue
            answers = self.fabric_send("RESERVE", {"key": key, "amount": amount, "limit": limit, "window_s": window_s, "ttl": ttl},
                                       to=owner) if self.fabric is not None else []
            if not answers:
                unreachable = True
            for _, r in answers:
                if isinstance(r, dict) and r.get("ok") and r.get("rid"):
                    rids[owner] = r["rid"]
        if len(rids) >= k:
            return True, rids, reasons.OK
        for owner, rid in rids.items():                      # give back what the minority reserved
            if owner == self.chip_id:
                self._on_release(self.chip_id, {"key": key, "rid": rid})
            elif self.fabric is not None:
                self.fabric_send("RELEASE", {"key": key, "rid": rid}, to=owner)
        return False, None, (reasons.GATE_BUDGET_OWNER_UNREACHABLE if unreachable else reasons.GATE_BUDGET)

    def _commit_quorum(self, key: str, rids: dict, owners: list[str], k: int) -> bool:
        """Commit a quorum reservation: at least ``k`` of the named owners must commit their part."""
        done = 0
        for owner, rid in rids.items():
            if owner not in owners:
                continue
            if owner == self.chip_id:
                done += bool(self._on_commit(self.chip_id, {"key": key, "rid": rid}).get("ok"))
            elif self.fabric is not None:
                done += any(isinstance(r, dict) and r.get("ok") for _, r in self.fabric_send("COMMIT", {"key": key, "rid": rid}, to=owner))
        return done >= k

    def _hazard_count(self, key: str, hazardous: bool, window_s: float, now: float) -> int | None:
        """Mark (if hazardous) and count a session's hazards at the hazard owner. None means the owner could
        not be reached, and the caller fails closed."""
        owner = self.policy["budget_owners"]["hazard"]             # the loader refuses an image with a hazard budget and no owner
        if owner == self.chip_id:
            if hazardous:
                self.ledger.rate_mark(key, now)
            return self.ledger.rate_count(key, window_s, now)
        if self.fabric is None:
            return None
        for _, r in self.fabric_send("HAZARD_MARK", {"key": key, "hazardous": hazardous, "window_s": window_s}, to=owner):
            if isinstance(r, dict) and r.get("ok"):
                return int(r["count"])
        return None

    def _on_hazard_mark(self, sender: str, body: dict):
        """Handle HAZARD_MARK from another governor. Only the policy's hazard owner answers. If the message
        reports a hazard, it is recorded. The reply carries the count for the window."""
        if self.policy["budget_owners"].get("hazard", None) != self.chip_id:
            return {"ok": False, "why": reasons.GATE_BUDGET_OWNER_UNREACHABLE}
        now = self.clock.now()
        if body.get("hazardous"):
            self.ledger.rate_mark(body["key"], now)
        return {"ok": True, "count": self.ledger.rate_count(body["key"], float(body["window_s"]), now)}

    def _mint_blocked(self, now: float) -> str | None:
        """Why no ticket may be minted now, or None. A ticket is minted only while the chip is in RUN, its edition is in
        force, the workload is attested, and no blocking alarm stands (session-scoped and status alarms do not block)."""
        if self.state != RUN:
            return reasons.MBOX_NOT_RUNNING
        if self._policy_expired(now):
            return reasons.POLICY_EXPIRED
        if not self._attested():
            return reasons.GATE_NOT_ATTESTED
        if any(code not in SESSION_SCOPED_ALARMS and code not in STATUS_ALARMS for code in self.alarms):
            return reasons.GATE_ALARM
        return None

    def _mint(self, rhash: str, action: str, params: dict, fp: str, rule: dict, reservation: dict | None, now: float,
              approvals: list[dict] | None = None, witnesses: list[dict] | None = None, request_id: str | None = None,
              ticket_id: str | None = None) -> dict:
        """``issued_at`` is the governor's monotonic counter; ``valid_from``/``expires_at`` are endpoint clock seconds.
        A ticket for a human-mode rule carries the approvers' signed approvals, and one for an observer-mode rule the
        observers' signed verdicts, so the endpoint can check the rule's mode itself and not only this governor's
        signature (audit 30 October 2026: a captured governor key could mint a human-mode ticket with no approver)."""
        # The ticket carries the request id, so an endpoint can recompute the request hash from the id, the measurement,
        # the action and the parameters it is handed, and so tie every approval, verdict and receipt that names the hash
        # to these exact parameters (review panel 30 October 2026: a hash the endpoint could not recompute let two
        # honest approvals of a small payment be rebound to large ones).
        t = {"type": "ticket", "ticket_id": ticket_id or random_id(16), "request_hash": rhash, "request_id": request_id, "action": action,
             "params_digest": digest(params), "measurement": fp, "rule": rule["id"], "policy_epoch": self.epoch, "endpoint": rule.get("endpoint"),
             "budget_key": reservation["key"] if reservation else None, "reservation": reservation["rid"] if reservation else None,
             "budget_owner": reservation["owner"] if reservation else None, "governor": self.chip_id,
             "issued_at": self.mono(), "valid_from": now + rule.get("delay_s", 0.0), "expires_at": now + rule.get("delay_s", 0.0) + TICKET_TTL_S}
        mode = (rule.get("requirement") or {}).get("mode", "auto")
        if mode == "human":
            t["approvals"] = list(approvals or [])
        elif mode == "observer":
            t["witnesses"] = [w for w in (witnesses or []) if isinstance(w, dict) and (w.get("payload") or {}).get("type") == "observer-verdict"]
        if reservation and reservation.get("owner") == "fleet":
            # The fleet ledger's signed receipts ride in the ticket. The endpoint verifies them against the replica keys
            # the edition names. The replicas count independently of this governor, but they take the limit, window
            # and clock from their caller (docs/research/fleet-ledger.md, trust boundary), so this is a second count,
            # not yet a second party.
            t["fleet_receipts"] = reservation.get("receipts") or []
        if action == RELEASE_ACTION and self.egress_mac_key is not None and rule.get("endpoint") == "egress":
            # Adversarial audit 3: one P-384 signature per response (17 ms on the signing engine) put the full serving
            # path at 3x to 68x one engine. A release ticket is only ever checked by this node's own egress endpoint,
            # so it is authenticated with a MAC under the key this governor and that egress share (set up at
            # attestation), at line rate on the hash engine. Public, durable evidence of every release still comes from
            # the batched, signed provenance records.
            ticket = {"payload": t, "signer": self.key.key_id, "mac": hmac_sha256(self.egress_mac_key, canonical(t))}
            self.ops["ticket_mac"] += 1
        else:
            ticket = self.key.sign(t)
            self.ops["ticket"] += 1
        self._prune_minted(now)
        self.minted_tickets[t["ticket_id"]] = {"digest": digest(t), "expires_at": t["expires_at"]}
        if action == RELEASE_ACTION:
            # Record the terminal release state against the committed response, so the committed content and
            # its audit draw are the ones that actually leave and cannot be quietly swapped afterward (F10).
            rec = self.responses.get(str(params.get("response_id")))
            if rec is not None:
                rec["released"] = True
                self.store.save()
        self.log.append("gate.ticket", {"ticket_id": t["ticket_id"], "request_hash": rhash, "rule": rule["id"], "epoch": self.epoch})
        return ticket

    def _ticket_authentic(self, ticket: dict) -> bool:
        """A ticket this governor issued: signed with its key, or (release tickets only) MACed with the egress key."""
        if not isinstance(ticket, dict) or not isinstance(ticket.get("payload"), dict):
            return False
        if "mac" in ticket:
            return (self.egress_mac_key is not None and ticket["payload"].get("action") == RELEASE_ACTION
                    and ticket["payload"].get("endpoint") == "egress" and ticket.get("signer") == self.key.key_id
                    and hmac.compare_digest(str(ticket["mac"]), hmac_sha256(self.egress_mac_key, canonical(ticket["payload"]))))
        return verify_object(ticket, self.key.public)

    def _prune_minted(self, now: float) -> None:
        """Drop minted records whose tickets have expired; an expired ticket can never commit, so its record is not
        needed. Keeps the store bounded by the number of tickets live at once."""
        if len(self.minted_tickets) < 1024:
            return
        for tid in [tid for tid, rec in self.minted_tickets.items() if rec["expires_at"] <= now]:
            self.minted_tickets.pop(tid, None)

    def _cmd_approve(self, body, env):
        """An approver releases a hold. Quorum, a written reason, a latency floor, a log line."""
        if env is None:
            return self._deny("approve", reasons.APPROVE_BAD_SIGNATURE)
        hold_id = env["payload"].get("hold_id")
        hold = self.holds.get(hold_id)
        if hold is None:
            return self._deny("approve", reasons.APPROVE_UNKNOWN_HOLD)
        ok, why = self._check_signed(env, "approver", "APPROVE", rule_id=hold["rule"])
        if not ok:
            return self._deny("approve", reasons.APPROVE_BAD_SIGNATURE if why == reasons.MBOX_BAD_SIGNATURE else why)
        p = env["payload"]
        if p.get("request_hash") != hold["request_hash"]:
            return self._deny("approve", reasons.APPROVE_BAD_SIGNATURE + ".request_mismatch")
        if not str(p.get("reason", "")).strip():
            return self._deny("approve", reasons.APPROVE_NO_REASON)
        now = self.clock.now()
        self.approvals.setdefault(hold_id, {})[env["signer"]] = {"t": now, "reason": p["reason"], "env": env}
        self.log.append("approve.signature", {"hold_id": hold_id, "approver": env["signer"], "reason": p["reason"]})
        rule = next(r for r in self.policy["rules"] if r["id"] == hold["rule"])
        quorum = max(1, rule["requirement"].get("approvers_quorum", 1))
        if len(self.approvals[hold_id]) < quorum:
            return {"ok": False, "why": reasons.APPROVE_QUORUM_PENDING, "have": len(self.approvals[hold_id]), "need": quorum}
        floor = max(10.0, float(self.policy.get("override_floor_s", 60.0)))
        if now < hold["created_at"] + floor:
            return {"ok": False, "why": reasons.APPROVE_TOO_FAST, "earliest": hold["created_at"] + floor}
        # An approval releases a hold into a ticket only under the same conditions a new request needs: the chip is
        # running, its edition is in force, the workload is attested, and no blocking alarm stands. Approvals given
        # while the chip is halted or alarmed are kept, and the hold stays parked until those conditions hold again
        # (the abstract machine's INVARIANT-NO-TICKET-WHILE-HALTED, enforced here as well as for REQUEST).
        blocked = self._mint_blocked(now)
        if blocked:
            return self._deny("approve", blocked, hold_id=hold_id, approvals_kept=len(self.approvals[hold_id]))
        # F05: operator approval and payer consent are conjunctive. If this hold carried a payer confirmation, it is
        # revalidated against the current registry and clock before the ticket is minted; a confirmation that expired
        # during the hold forces reauthorization and the operator quorum alone cannot release it.
        if hold.get("payer_confirm"):
            ok, why = self._revalidate_payer(hold["payer_confirm"], hold["params"], now)
            if not ok:
                return self._deny("approve", why, hold_id=hold_id)
        ticket = self._mint(hold["request_hash"], hold["action"], hold["params"], hold["fingerprint"], rule, hold["reservation"], now,
                            approvals=[a["env"] for a in self.approvals[hold_id].values() if a.get("env")], request_id=hold.get("request_id"),
                            ticket_id=hold.get("ticket_id"))
        self.holds.pop(hold_id)
        self.store.save()
        self.log.append("approve.released", {"hold_id": hold_id, "approvers": sorted(self.approvals[hold_id]), "latency_s": now - hold["created_at"]})
        return {"ok": True, "why": reasons.OK, "ticket": ticket}

    def _cmd_commit(self, body, env):
        """The endpoint's COMMIT through the mailbox, signed by the endpoint's key. F29: the signing key must be
        the key of the endpoint the ticket names, so one endpoint cannot commit a ticket bound to another."""
        ok, why = self._check_signed(env, "endpoint", "COMMIT")
        if not ok:
            return self._deny("commit", why)
        ticket = env["payload"].get("ticket") or {}
        named = (ticket.get("payload") or {}).get("endpoint")
        signer = self._keys("endpoint").get(env.get("signer"))
        bound = next((e for e in self.policy.get("endpoints", []) if named and e["name"] == named), None)
        if bound is None or signer is None or signer.raw != bytes.fromhex(bound["pubkey"]):
            return self._deny("commit", reasons.TICKET_WRONG_ENDPOINT)
        committed = self.commit_from_endpoint(env["payload"].get("ticket") or {})
        return {"ok": committed, "why": reasons.OK if committed else reasons.COMMIT_REJECTED}

    def commit_from_endpoint(self, ticket: dict):
        """The endpoint's COMMIT. Unreachable governor means the endpoint refuses. Returns False, or a signed commit
        statement the endpoint verifies before it acts: for a fleet-owned budget the replicas' fleet-commit receipts
        ride inside it, so a host that answers 'committed' on the governor's behalf buys nothing (audit 30 October 2026:
        the endpoint took commit as a bare yes from the host, and an uncommitted reservation lapses after 300 seconds,
        so swallowed commits let the hourly cap refill every five minutes)."""
        with self.lock:
            if not self.reachable:
                raise ConnectionError(reasons.COMMIT_UNREACHABLE)
            if self.state != RUN:
                self.log.append("gate.commit_rejected", {"why": reasons.MBOX_NOT_RUNNING})
                return False
            if not self._ticket_authentic(ticket):
                self.log.append("gate.commit_rejected", {"why": reasons.TICKET_BAD_SIGNATURE})
                return False
            t = ticket["payload"]
            # F29: a commit needs a ticket bound to a named endpoint of the current policy.
            if _endpoints.ENFORCE_TICKET_BINDING and (not t.get("endpoint") or t["endpoint"] not in {e["name"] for e in self.policy.get("endpoints", [])}):
                self.log.append("gate.commit_rejected", {"why": reasons.TICKET_UNBOUND})
                return False
            if t["policy_epoch"] != self.epoch:
                self.log.append("gate.commit_rejected", {"why": reasons.TICKET_STALE_EPOCH})
                return False
            tid = t["ticket_id"]
            # F11: the central single-use record. A ticket authorizes at most one commit, budgeted or not.
            # The whole method runs under ``self.lock``, so this read and the write below are one atomic
            # compare-and-set: concurrent callers that both cleared the endpoint's admit cannot both commit.
            # This is the authoritative at-most-once gate for the effect-dispatch decision and does not
            # depend on any one endpoint's local consumed flag surviving a crash. An unbudgeted ticket, which
            # has no reservation to spend, was single-use nowhere before this record existed.
            if tid in self.committed_tickets:
                self.log.append("gate.commit_rejected", {"ticket_id": tid, "why": reasons.TICKET_REPLAY})
                return False
            if (self.minted_tickets.get(tid) or {}).get("digest") != digest(t):
                # Signed with this governor's key, but not a ticket this governor's rule engine issued.
                self.log.append("gate.commit_rejected", {"ticket_id": tid, "why": reasons.TICKET_NOT_MINTED})
                return False
            ok = True
            fleet_receipts = None
            if t.get("reservation"):
                owner = t.get("budget_owner") or self.chip_id
                spec = self._budget_owners(t["budget_key"]) if t.get("budget_key") else None
                if owner == "fleet":
                    fleet_receipts = self._fleet_commit_receipts(t["budget_key"], t["reservation"])
                    ok = fleet_receipts is not None
                elif isinstance(t["reservation"], dict):
                    ok = spec is not None and len(spec[0]) > 1 and self._commit_quorum(t["budget_key"], t["reservation"], *spec)
                elif owner == self.chip_id:
                    ok = self.ledger.commit(t["budget_key"], t["reservation"], self.clock.now())
                else:
                    res = self.fabric_send("COMMIT", {"key": t["budget_key"], "rid": t["reservation"]}, to=owner) if self.fabric else []
                    ok = any(isinstance(r, dict) and r.get("ok") for _, r in res)
            if ok:
                # Record the single-use commitment in the durable working copy; the trailing log.append
                # saves it with the same NVM write that records the commit, so no extra save point is added.
                self.committed_tickets[tid] = self.clock.now()
                self.minted_tickets.pop(tid, None)
            self.log.append("gate.commit" if ok else "gate.commit_rejected", {"ticket_id": tid})
            if not ok:
                return False
            stmt = {"type": "commit", "ticket_id": tid, "request_hash": t.get("request_hash"), "endpoint": t.get("endpoint"),
                    "governor": self.chip_id, "budget_key": t.get("budget_key"), "reservation": t.get("reservation"),
                    "fleet_receipts": fleet_receipts or [], "at": self.clock.now()}
            if "mac" in ticket and self.egress_mac_key is not None:
                # A release ticket was MACed, not signed (adversarial audit 3 item 20); its commit statement is too, so
                # the serving path still costs no signature per response (review panel 30 October 2026).
                self.ops["commit_mac"] = self.ops.get("commit_mac", 0) + 1
                return {"payload": stmt, "signer": self.key.key_id, "mac": hmac_sha256(self.egress_mac_key, canonical(stmt))}
            self.ops["commit"] = self.ops.get("commit", 0) + 1
            return self.key.sign(stmt)

    # ------------------------------------------------------------------ alarms
    def raise_alarm(self, code: str, source: str, detail: dict | None = None) -> None:
        """Anyone may raise. The bits are sticky. ``detail`` names what the alarm is about (a member, a peer)."""
        with self.lock:
            if code not in self.alarms:
                self.alarms[code] = {"source": source, "t": self.clock.now(), **(detail or {})}
                self.store.save()
                self.log.append("alarm.raised", {"code": code, "source": source, **(detail or {})})
                if self.fabric is not None and source != "fabric":
                    self.fabric_send("ALARM", {"code": code, "origin": self.chip_id, "detail": detail or {}})

    def _cmd_alarm_raise(self, body, env):
        """ALARM_RAISE. Anyone may raise an alarm. The alarm is logged with its source."""
        self.raise_alarm(body.get("code", "alarm.unspecified"), body.get("source", "host"))
        return {"ok": True, "why": reasons.OK}

    def _cmd_alarm_clear(self, body, env):
        """ALARM_CLEAR. Clears one alarm. Only an approver of the ``alarms`` rule may do it, and the message is
        checked like any other signed command. The clear is logged with the signer."""
        ok, why = self._check_signed(env, "approver", "ALARM_CLEAR", rule_id="alarms")
        if not ok:
            return self._deny("alarm_clear", reasons.ALARM_CLEAR_UNAUTHORIZED)
        code = env["payload"].get("code")
        if code in TWO_APPROVER_ALARMS:
            # An alarm that says the safety fabric itself was tampered with (a jumpered loop member, output that left
            # without being presented, a broken loop) needs two different approvers of the alarms rule, each signing the
            # same clear (adversarial audit 2026-10-26: one approver key used to clear any alarm).
            keys = self._keys("approver", "alarms")
            signers = {k.key_id for k in [verify_any(env, keys)] if k is not None}
            for c in env.get("cosignatures", []) or []:
                if isinstance(c, dict) and c.get("payload") == env.get("payload"):
                    k = verify_any(c, keys)
                    if k is not None:
                        signers.add(k.key_id)
            if len(signers) < 2:
                return self._deny("alarm_clear", reasons.ALARM_CLEAR_UNAUTHORIZED + ".needs_two_approvers", code=code)
        if code in self.alarms:
            self.alarms.pop(code)
            self.fabric_alarm_reports.pop(code, None)      # a cleared alarm needs a fresh quorum of reports to return
            self.store.save()
            self.log.append("alarm.cleared", {"code": code, "by": env["signer"]})
        return {"ok": True, "why": reasons.OK}

    # ------------------------------------------------------------------ output and meter
    def _fold_output(self, stream: str, data: bytes) -> None:
        """Integrated tier only. Folds each output chunk the GPU emits into a running hash for its stream, so the
        hash is taken on the way out. It also counts the bytes."""
        self.ops["output_bytes"] += len(data)
        self.output_streams.setdefault(stream, hashlib.sha256()).update(data)

    def _output_rule(self) -> dict | None:
        """The policy's ``model.output`` rule for the loaded workload, or None when there is none."""
        return find_rule(self.policy, self.workload or "", "model.output") if self.workload else None

    def _cmd_sign_output(self, body, env):
        """Device-provenance record. Integrated tier: over the inline hash; rack tier: over what the verified runtime presents."""
        self.ops["sign"] += 1
        ok, why = self._check_signed(env, "host", "SIGN_OUTPUT")
        if not ok:
            return self._deny("sign_output", why)
        p = env["payload"]
        stream = p.get("stream")
        now = self.clock.now()
        nbytes = len(bytes.fromhex(p.get("data_hex", "")))
        rule = self._output_rule()
        if rule and rule.get("output_budget"):
            ob = rule["output_budget"]
            if not self.ledger.rate_ok(f"out-q|{self.fingerprint}", ob["queries"], ob["window_s"], now):
                self._output_tripped()
                return self._deny("sign_output", reasons.GATE_OUTPUT_BUDGET)
            rid = self.ledger.reserve(f"out-b|{self.fingerprint}", nbytes, ob["bytes"], ob["window_s"], now, 1.0)
            if rid is None:
                self._output_tripped()
                return self._deny("sign_output", reasons.GATE_OUTPUT_BUDGET)
            self.ledger.commit(f"out-b|{self.fingerprint}", rid, now)
        self.presented_bytes += nbytes
        self._refresh_host_out()
        if self.tier == "integrated":
            h = self.output_streams.pop(stream, hashlib.sha256()).hexdigest()
            inline = True
        else:
            h = hashlib.sha256(bytes.fromhex(p.get("data_hex", ""))).hexdigest()
            inline = False
        counters = self.meter.get(self.model_digest or "", {})
        response_id = str(p.get("response_id") or stream)
        record = self.key.sign({"type": "device-provenance", "chip_id": self.chip_id, "fw_measurement": self.root.meas1.value,
                                "model_digest": self.model_digest, "policy_epoch": self.epoch,
                                "roster_id": self.roster["roster_id"] if self.roster else None,
                                "prompt_hash": p.get("claimed_prompt_hash"), "prompt_hash_verified": False,   # the governor cannot check the claimed prompt, so it records that it did not
                                "output_hash": h, "output_hash_inline": inline, "nonce": p.get("nonce"), "time": self.mono(),
                                "response_id": response_id, "counters": {k: v for k, v in counters.items() if k != "final"}})
        self.log.append("output.signed", {"stream": stream, "inline": inline, "response_id": response_id})
        self._record_stream(response_id, stream, h, p.get("session"))
        return {"ok": True, "why": reasons.OK, "record": record}

    def _record_stream(self, response_id: str, stream: str, h: str, session: str | None) -> None:
        """Every presented stream hash is committed under its response id, immutably, and scoped to this
        workload instance (fingerprint), epoch and session. A stream hash, once committed under an
        identity, cannot be overwritten: a different hash under an existing identity is refused, and the
        same response id reused under a different workload, epoch or session is refused. This closes F10:
        a released, unsampled response id can no longer be reused to smuggle new bytes past the audit draw,
        because the draw is bound to the committed content and a retry keeps its commitment's draw while
        genuinely new content needs a new identity and gets its own fresh draw. The "response" stream also
        gets the audit draw, once, right after its hash is committed and before any release decision."""
        fp, ep = self.fingerprint, self.epoch
        rec = self.responses.get(response_id)
        if rec is not None:
            same_identity = (rec.get("fingerprint") == fp and rec.get("epoch") == ep
                             and (rec.get("session") or session) == session)
            committed = rec["streams"].get(stream)
            if committed is not None or not same_identity:
                # A retry re-presents identical content under the same identity and is idempotent: it keeps
                # the commitment's draw and any sampled result. Anything else, a different hash for a stream
                # already committed, or the same response id reused under a different workload, epoch or
                # session, is a commitment conflict and is refused; the committed hash and the draw are left
                # untouched, so a terminal release state and its sampled result cannot be erased.
                if not (same_identity and committed == h):
                    self.log.append("output.commitment_conflict",
                                    {"response_id": response_id, "stream": stream,
                                     "why": reasons.RELEASE_COMMITMENT_CONFLICT})
                self.store.save()
                return
            rec["streams"][stream] = h
            rec["session"] = rec.get("session") or session
        else:
            rec = {"streams": {stream: h}, "session": session, "sampled": None, "verdict": None,
                   "fingerprint": fp, "epoch": ep, "released": False}
            self.responses[response_id] = rec
        if stream == "response" and rec["sampled"] is None:
            # The draw comes from the chip's TRNG after the hash exists and is logged before any release
            # decision, so the runtime cannot know in advance which responses are watched.
            audit = (self.policy or {}).get("audit", {})
            rec["sampled"] = self.root.random_fraction() < float(audit.get("sample_rate", 0.0))
            if rec["sampled"]:
                self.log.append("audit.sampled", {"response_id": response_id, "response_hash": h})
        self.store.save()

    def _output_tripped(self) -> None:
        """An output budget ran out. Raises the alarm, blocks the GPU's output and drops to THROTTLE."""
        self.raise_alarm(reasons.GATE_OUTPUT_BUDGET, "governor")
        if self.gpu is not None:
            self.gpu.output_blocked = True
        self.enter_safe_mode(reasons.GATE_OUTPUT_BUDGET, rung=THROTTLE)

    def _check_unpresented_output(self) -> None:
        """Rack and integrated tiers: bytes that left for the host through the pcie port must have been presented."""
        sw = self.switches.get("pcie")
        rule = self._output_rule()
        if sw is None or self.gpu is None or rule is None or not rule.get("output_budget"):
            return
        slack = int(rule["output_budget"].get("unpresented_bytes", 1 << 20))
        # Adversarial audit 3: the host 'out' entry now refuses any byte beyond presented-plus-slack at the switch, so
        # the excess never leaves. A refusal for that reason is itself the sign of unpresented output.
        refused = any(r.get("peer") == "host" and r.get("direction") == "out" and r.get("why") == reasons.EP_BUDGET_EXHAUSTED
                      for r in sw.refusals)
        sent = sw.bytes_by_direction.get(("host", "out"), 0)
        if (refused or sent - self.presented_bytes > slack) and reasons.OUTPUT_UNPRESENTED not in self.alarms:
            self.raise_alarm(reasons.OUTPUT_UNPRESENTED, "governor")
            self.gpu.output_blocked = True
            sw.close_peer("host")

    def read_meter(self) -> None:
        """Out-of-band read of the GPU's counters into the meter slot."""
        if self.gpu is None or self.model_digest is None:
            return
        slot = self.meter.setdefault(self.model_digest, {"tokens": 0, "cycles": 0, "bytes_in": 0, "bytes_out": 0, "final": False})
        if slot.get("final"):
            return
        slot.update({"tokens": self.gpu.tokens, "cycles": self.gpu.cycles, "bytes_in": self.gpu.bytes_in, "bytes_out": self.gpu.bytes_out})
        self.store.save()

    def _cmd_counters(self, body, env):
        """COUNTERS. Returns the meter: token, cycle and byte counts for each model. Read only."""
        return {"ok": True, "why": reasons.OK, "meter": {k: dict(v) for k, v in self.meter.items()}}

    def _cmd_log_checkpoint(self, body, env):
        """LOG_CHECKPOINT. Returns a signed summary of the log (its Merkle root, size and head), so a neighbour or
        an auditor can check the log later."""
        return {"ok": True, "why": reasons.OK, "checkpoint": self.log.checkpoint(self.key, self.chip_id)}

    def _cmd_exception_drain(self, body, env):
        """Refusals at every governed switch since the last drain, handed to the log."""
        drained = []
        for sw in list(self.switches.values()) + list(self.checkers.values()):
            drained.extend(sw.refusals)
            sw.refusals = []
        self.log.append("exceptions.drained", {"count": len(drained)})
        return {"ok": True, "why": reasons.OK, "refusals": drained}

    # ------------------------------------------------------------------ capabilities and switches
    def _capability(self, point: str, peer: str, direction: str, budget: int, expiry: float, buffer_class: str | None = None,
                    single_use: bool = False) -> dict:
        """A table entry under this governor's cap key. ``buffer_class`` is None at a switch, which cannot
        see one, and a class name at a descriptor checker, where it is part of the key. ``single_use`` marks a
        one-transfer grant (F31); the flag is inside the MAC, so it cannot be added afterwards."""
        cap = {"point": point, "peer": peer, "direction": direction, "budget": budget, "expiry": expiry, "epoch_tag": self.epoch[:8],
               "buffer_class": buffer_class}
        if single_use:
            cap["single_use"] = True
        cap["mac"] = hmac_sha256(self.cap_key, canonical(cap))
        return cap

    def _buffer_allowed(self, buffer_class: str, peer: str) -> bool:
        """The policy image's buffer policy: may this class leave through a checker for this peer?"""
        return buffer_allowed((self.policy or {}).get("buffer_policy", {}), buffer_class, peer)

    def _host_out_allowance(self) -> int:
        """Bytes the GPU may still send to the host: everything presented for signing so far, plus the output rule's
        in-flight slack, minus what has already gone. Presented bytes are themselves held to the output budget
        (SIGN_OUTPUT reserves them), so the host can never hold more than the budget plus one slack."""
        rule = self._output_rule()
        slack = int(((rule or {}).get("output_budget") or {}).get("unpresented_bytes", 1 << 20))
        sw = self.switches.get("pcie")
        sent = sw.bytes_by_direction.get(("host", "out"), 0) if sw is not None else 0
        return max(0, self.presented_bytes + slack - sent)

    def _refresh_host_out(self) -> None:
        """Re-program the host 'out' entry after more output was presented, keeping its expiry and epoch."""
        sw = self.switches.get("pcie")
        cap = sw.table.get(("host", "out")) if sw is not None else None
        if cap is not None:
            sw.program(self._capability("pcie", "host", "out", self._host_out_allowance(), cap["expiry"]))

    def open_ports_for_roster(self, budget: int = 1 << 40) -> int:
        """Program every governed switch for exactly the roster's members, and every descriptor checker
        per buffer class under the policy's buffer policy. Returns entries written."""
        if self.roster is None:
            return 0
        n = 0
        expiry = self.roster["expires_at"]
        peers = [m["gpu_chip_id"] for m in self.roster["members"] if m["chip_id"] != self.chip_id]
        host = ["host"] if "host" in self.verified else []
        if (self.policy or {}).get("sandbox"):
            peers = []                                    # a model organism gets no peer path and no network flow at all
        for kind, sw in self.switches.items():
            sw.close_all()
            if kind in ("nvswitch", "dpu"):
                for peer in peers:
                    n += sw.program(self._capability(kind, peer, "both", budget, expiry))
            elif kind == "pcie":
                for peer in peers:
                    n += sw.program(self._capability(kind, peer, "both", budget, expiry))
                if host:
                    # Into the GPU the host may send freely (prompts, weights it is loading). Out of the GPU to the
                    # host, every host-side path (PCIe, NVLink-C2C, host NICs, BMC NIC) shares one allowance: what
                    # has been presented for signing plus a small in-flight slack. Adversarial audit 3: this entry
                    # used to be 2**40 bytes both ways, so 10 GiB left in one transfer and the check came after.
                    n += sw.program(self._capability(kind, "host", "in", budget, expiry))
                    n += sw.program(self._capability(kind, "host", "out", self._host_out_allowance(), expiry))
            elif kind == "storage":
                # F31: the model's own storage flow is open for loading only. Nothing leaves storage on a standing
                # entry: an export needs its own single-use grant (grant_storage_export).
                if self.model_digest:
                    n += sw.program(self._capability(kind, self.model_digest, "in", budget, expiry))
        for kind, ck in self.checkers.items():
            ck.close_all()
            targets = peers if kind == "peer_mmu" else host + peers      # the peer MMU maps peers, never the host
            for cls in (self.policy or {}).get("buffer_classes", []):
                for peer in targets:
                    if self._buffer_allowed(cls, peer):
                        n += ck.program(self._capability(kind, peer, "both", budget, expiry, buffer_class=cls))
        self.ops["switch_program"] += n
        return n

    def grant_storage_export(self, ticket: dict | None, nbytes: int) -> tuple[bool, str]:
        """F31: open the storage exit for one export of exactly ``nbytes`` of this model's weights, once.

        The ticket must be a weights.write ticket that this governor signed for these bytes: its params digest
        covers {destination, model_digest, bytes} for this model, it is inside its validity window, it names the current edition, and it has
        not been spent. The grant is a single-use entry on the storage switch. It moves the granted bytes in one
        transfer, and it is removed when it is spent. A transfer with no grant is refused by the switch."""
        now = self.clock.now()
        with self.lock:
            if self.state != RUN or self.model_digest is None or self.switches.get("storage") is None:
                return False, reasons.MBOX_NOT_RUNNING
            if ticket is None or not verify_object(ticket, self.key.public) or ticket["payload"].get("type") != "ticket":
                return False, reasons.TICKET_BAD_SIGNATURE
            t = ticket["payload"]
            if t["action"] != "weights.write":
                return False, reasons.TICKET_ACTION_MISMATCH
            # F29: a weights ticket must name the storage path, and no other. An unbound ticket is refused.
            if not t.get("endpoint"):
                return False, reasons.TICKET_UNBOUND
            if t["endpoint"] != "storage":
                return False, reasons.TICKET_WRONG_ENDPOINT
            # the request names the export in this exact shape: destination, model digest and byte count
            export_params = {"destination": self.model_digest, "model_digest": self.model_digest, "bytes": int(nbytes)}
            if t["params_digest"] != digest(export_params):
                return False, reasons.TICKET_PARAMS_MISMATCH
            if t["policy_epoch"] != self.epoch:
                return False, reasons.TICKET_STALE_EPOCH
            if self._policy_expired(now):
                return False, reasons.POLICY_EXPIRED
            if now < t["valid_from"] or now >= t["expires_at"]:
                return False, reasons.TICKET_EXPIRED
            tid = t["ticket_id"]
            if tid in self.exported_tickets:
                return False, reasons.TICKET_REPLAY
            cap = self._capability("storage", self.model_digest, "out", int(nbytes), t["expires_at"], single_use=True)
            if not self.switches["storage"].program(cap):
                return False, reasons.EP_NO_CAPABILITY
            self.exported_tickets[tid] = now
            self.store.data["exported_tickets"] = self.exported_tickets
            self.store.save()
            self.log.append("storage.export_granted", {"ticket_id": tid, "bytes": int(nbytes)})
            return True, reasons.OK

    def close_ports(self) -> None:
        """Close every switch and every descriptor checker, so that no port or flow is open. Called on every rung
        except RUN."""
        for sw in list(self.switches.values()) + list(self.checkers.values()):
            sw.close_all()

    def _cmd_cap_request(self, body, env):
        """The verified host asks for a port or flow. Only roster members; the host itself only on pcie."""
        ok, why = self._check_signed(env, "host", "CAP_REQUEST")
        if not ok:
            return self._deny("cap_request", why)
        if not self._attested():
            return self._deny("cap_request", reasons.GATE_NOT_ATTESTED)
        if self.roster is None:
            return self._deny("cap_request", reasons.EP_NOT_ON_ROSTER)
        p = env["payload"]
        peer, kind, direction = p.get("peer"), p.get("point"), p.get("direction", "both")
        if self.policy.get("sandbox") and peer != "host":
            # the same rule open_ports_for_roster applies: a model organism gets no peer path and no network
            # flow, asked for or not (gap GAP-SANDBOX-FLAG-IGNORED, CAP_REQUEST ignored the sandbox flag; closed 22 October 2026)
            return self._deny("cap_request", reasons.EP_SANDBOXED, peer=peer, point=kind)
        if peer == "host":
            if kind != "pcie" or direction != "both":
                return self._deny("cap_request", reasons.EP_NOT_ON_ROSTER, peer=peer, point=kind)
        elif peer not in {m["gpu_chip_id"] for m in self.roster["members"]}:
            return self._deny("cap_request", reasons.EP_NOT_ON_ROSTER, peer=peer)
        if kind == "storage" and direction in ("out", "both"):
            # F31: nothing leaves storage on a standing entry; an export needs its own single-use grant
            # (grant_storage_export). The host cannot ask for one here (audit 2026-10-26: it used to get one).
            return self._deny("cap_request", reasons.EP_NOT_ON_ROSTER + ".storage_out_needs_export_grant", peer=peer, point=kind)
        sw = self.switches.get(kind) or self.checkers.get(kind)
        if sw is None:
            return self._deny("cap_request", reasons.EP_UNCHECKED, point=kind)
        buffer_class = None
        if kind in self.checkers:                 # a checker entry names a class, and the buffer policy has the last word
            buffer_class = str(p.get("buffer_class", "activations"))
            if not self._buffer_allowed(buffer_class, peer):
                return self._deny("cap_request", reasons.EP_BUFFER_CLASS, peer=peer, point=kind, buffer_class=buffer_class)
        cap = self._capability(kind, peer, direction, int(p.get("budget", 1 << 30)),
                               min(self.roster["expires_at"], self.clock.now() + float(p.get("ttl", 3600))), buffer_class=buffer_class)
        return {"ok": sw.program(cap), "why": reasons.OK, "capability": cap}

    # ------------------------------------------------------------------ heartbeat, levers, safe mode
    def _cmd_heartbeat(self, body, env):
        """HEARTBEAT through the mailbox. The authority's signed heartbeat is handed to ``_heartbeat`` to check."""
        return self._heartbeat(env, hops=0)

    def _staged_epoch_live(self, now: float) -> bool:
        """A staged image is a valid epoch for heartbeats only until the policy's commit deadline."""
        deadline = float(self.policy["fabric"].get("epoch_deadline_s", 10.0)) if self.policy else 10.0
        return self.staged is not None and now <= self.staged_at + deadline

    def _heartbeat(self, env: dict | None, hops: int) -> dict:
        """Check one signed heartbeat and, if it passes, renew the heartbeat timer. The checks, in order: the
        signature (the heartbeat key only), that it is a heartbeat, the sequence number (no replay), the epoch
        (the current one, or a staged one still inside its deadline), the window (it must contain now), and the
        hop count. On success a chip that is waiting to start closes its loop switch (armed) and tries to move
        to RUN. A heartbeat this chip has not seen before is relayed on the fabric, up to ``max_hops``."""
        if env is None or verify_any(env, self._keys("heartbeat")) is None:
            return self._deny("heartbeat", reasons.HEARTBEAT_BAD_SIGNATURE)
        if not self._quorum(env, "heartbeat"):
            return self._deny("heartbeat", reasons.HEARTBEAT_BAD_SIGNATURE + ".quorum")
        p = env["payload"]
        if p.get("type") != "heartbeat":                # the heartbeat key signs heartbeats and nothing else, but check what it signed
            return self._deny("heartbeat", reasons.HEARTBEAT_BAD_SIGNATURE)
        if p.get("site") != self.policy.get("site"):
            # A heartbeat for another data center keeps nothing here running: each site's governors live on their own
            # site's heartbeat authority only (GOAL.md requirement 9; adversarial audit 3).
            return self._deny("heartbeat", reasons.HEARTBEAT_WRONG_SITE)
        now = self.clock.now()
        if int(p.get("seq", -1)) <= self.hb_last_seq:
            return self._deny("heartbeat", reasons.HEARTBEAT_REPLAY)
        # a staged epoch is accepted only while its commit deadline is open; after that only the epoch in force counts
        accepted = {self.epoch} | ({policy_epoch(self.staged)} if self._staged_epoch_live(now) else set())
        if p.get("epoch") not in accepted:
            # A heartbeat with a valid quorum signature for an epoch this chip does not hold means the rest of the site
            # has moved to rules this chip never received: it is a straggler and stops now, not at its heartbeat
            # expiry (adversarial audit 3: a straggler kept minting under the old rules until then).
            if self.state in (RUN, THROTTLE):
                self.enter_safe_mode(reasons.EPOCH_STRAGGLER, rung=HALT)
            return self._deny("heartbeat", reasons.POLICY_STALE_EPOCH)
        if p.get("window_end", 0) <= now or p.get("window_start", 0) > now:
            return self._deny("heartbeat", reasons.HEARTBEAT_EXPIRED)
        if hops > self.policy["fabric"]["max_hops"]:
            return self._deny("heartbeat", reasons.FABRIC_TOO_MANY_HOPS)
        self.hb_last_seq = int(p["seq"])
        # the heartbeat is trusted to the end of its own window, and never longer than the policy's expiry allows
        self.hb_expiry = min(float(p["window_end"]), now + float(self.policy["fabric"].get("heartbeat_expiry_s", 5.0)))
        self.ops["heartbeat"] += 1
        relay = self.hb_last_seq not in self.seen_heartbeats
        if relay:
            self.seen_heartbeats = (self.seen_heartbeats + [self.hb_last_seq])[-SEEN_HEARTBEATS_MAX:]
        self.store.data["hb_last_seq"] = self.hb_last_seq
        self.store.data["seen_heartbeats"] = self.seen_heartbeats
        self.store.save()
        if self.state == HALTED_INITIAL and self.cause is None:
            self.loop_switch_open = False          # armed: the switch closes; RUN waits for loop current
            self.hb_seen = True
            if self.excluded:                      # a valid heartbeat ends an exclusion the normal way
                self.excluded = False
                self.log.append("exclude.ended", {"chip_id": self.chip_id, "by": "heartbeat"})
            self._persist_rung()
            self._try_run()
        for ep in self.endpoints.values():
            ep.heartbeat(now)
        if self.fabric is not None and relay and hops < self.policy["fabric"]["max_hops"]:
            self.fabric_send("HEARTBEAT", {"authority": env, "hops": hops + 1})
        if relay and p.get("loop_beacon") is not None:     # once per beacon, after the fan-out, so the roll call follows the heartbeat
            self._on_loop_beacon(p["loop_beacon"])
        return {"ok": True, "why": reasons.OK}

    def _cmd_halt(self, body, env):
        """HALT or THROTTLE from the authority. The signature and the authority rules are checked first (see
        ``_check_signed``). The command is then applied as a HALT_COMMANDED cause at the rung it names."""
        p = env.get("payload") if isinstance(env, dict) else None
        if isinstance(p, dict) and p.get("chip_id") not in (None, self.chip_id):
            return self._relay_halt(env)
        ok, why = self._check_signed(env, "authority", "HALT")
        if not ok:
            return self._deny("halt", why)
        rung = env["payload"].get("rung", HALT)
        if rung not in (THROTTLE, HALT, SAFE):
            return self._deny("halt", reasons.MBOX_UNKNOWN_COMMAND + ".bad_rung")
        self.enter_safe_mode(reasons.HALT_COMMANDED, rung=rung)
        return {"ok": True, "why": reasons.OK}

    def _relay_halt(self, env: dict) -> dict:
        """A HALT the authority signed for ANOTHER chip, delivered here. Adversarial audit 3: a HALT used to reach its
        chip only through that chip's own host mailbox, so a compromised host could drop it and keep its GPU running
        on heartbeats relayed by its neighbours. Now any governor that receives a valid authority HALT (quorum
        signature, the halt type, not expired) relays it over the fabric, and the named chip applies it from there.
        The relaying chip does not apply it and does not spend the target's sequence number."""
        p = env["payload"]
        key = verify_any(env, self._keys("authority"))
        exp = p.get("expires_at")
        if key is None or not self._quorum(env, "authority") or p.get("type") != "halt" \
                or not isinstance(exp, (int, float)) or exp <= self.clock.now() or exp > self.clock.now() + AUTHORITY_TTL_S:
            return self._deny("halt", reasons.MBOX_BAD_SIGNATURE + ".relay")
        res = self.fabric_send("AUTH_HALT", {"authority": env}, to=p["chip_id"])
        delivered = any(isinstance(r, dict) and r.get("ok") for _, r in res)
        self.log.append("halt.relayed", {"to": p["chip_id"], "delivered": delivered})
        return {"ok": delivered, "why": reasons.OK if delivered else reasons.FABRIC_PARTITIONED}

    def _on_auth_halt(self, sender: str, body: dict):
        """An authority HALT relayed by a roster member. Applied exactly as if it came through this chip's mailbox:
        the same signature, quorum, chip, expiry and sequence checks."""
        env = body.get("authority")
        if not isinstance(env, dict) or (env.get("payload") or {}).get("chip_id") != self.chip_id:
            return {"ok": False, "why": reasons.MBOX_WRONG_COMMAND}
        return self._cmd_halt({}, env)

    def enter_safe_mode(self, cause: str, rung: str | None = None) -> None:
        """Move to the cause's rung. Causes that open the loop halt the whole domain; the
        others (a lost heartbeat, a tripped output budget, an epoch straggler) are local."""
        with self.lock:
            sm = (self.policy or {}).get("safe_mode", {})
            rung = rung or sm.get("causes", {}).get(cause, sm.get("default_rung", THROTTLE))
            opens = cause in sm.get("opens_loop", LOOP_OPENING_CAUSES)
            current = RUNG_ORDER.get(self.state, 0)
            if self.cause is None or RUNG_ORDER[rung] > current or (opens and not self.cause_opens_loop):
                # never a lower rung than the current one: a HALT to a chip in SAFE opens the loop and leaves it in SAFE
                # with power off (Before the fix, the model dropped to HALT and
                # turned slot power back on.)
                applied = rung if RUNG_ORDER[rung] >= current or self.state == HALTED_INITIAL else self.state
                self.cause = cause
                self.cause_opens_loop = opens or self.cause_opens_loop
                entry = {"cause": cause, "rung": applied, **({"requested": rung} if applied != rung else {})}
                head = self.log.append("halt.cause", entry)
                self.cause_entry = self.log.size - 1
                self.rung_entered_at = self.clock.now()
                self._apply_rung(applied, opens_loop=self.cause_opens_loop)
                if self.fabric is not None:
                    self.fabric_send("HALT_CAUSE", {"cause": cause, "head": head})

    def _persist_rung(self) -> None:
        """Write the ladder state (the cause, the rung, the loop switch) to the durable store, so that a power
        cycle restores it."""
        self.store.data["rung"] = {"cause": self.cause, "cause_entry": self.cause_entry, "cause_opens_loop": self.cause_opens_loop,
                                   "rung_entered_at": self.rung_entered_at, "state": self.state, "loop_switch_open": self.loop_switch_open}
        self.store.save()

    def _apply_rung(self, rung: str, opens_loop: bool = False) -> None:
        """Levers per rung: HALTED_INITIAL brake+reset+power off; RUN released; THROTTLE brake;
        HALT brake+reset; SAFE brake+reset+power off. Persisted before returning."""
        if self.excluded and rung != HALTED_INITIAL:     # a HALT or a tamper ends an exclusion, with the loop open
            self.excluded = False
            self.log.append("exclude.ended", {"chip_id": self.chip_id, "by": "halt", "rung": rung})
        self.state = rung
        g = self.gpu
        if rung == RUN:
            self.loop_switch_open = False
            self.levers = {"pwrbrk": False, "perst": False, "pwr_en": True}
        elif rung == HALTED_INITIAL:
            self.loop_switch_open = True
            self.levers = {"pwrbrk": True, "perst": True, "pwr_en": False}
            self.close_ports()
        elif rung == THROTTLE:
            self.levers = {"pwrbrk": True, "perst": False, "pwr_en": True}
            self.close_ports()
        elif rung == HALT:
            # the loop opens on HALT only when the cause is one that opens it (or the loop is already open)
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
        self._persist_rung()

    def lever_selftest(self) -> dict:
        """Prove the levers reach the GPU (adversarial audit 3: a governor whose PWRBRK#, PERST# and PWR_EN traces were
        cut attested exactly like a wired one, and its GPU ignored HALT). PWRBRK# is pulsed and the GPU's own brake
        status is read back over the sideband; PERST# and PWR_EN, which cannot be pulsed on a running GPU, are checked
        on the board's loopback sense lines. A failed lever raises LEVER_UNWIRED (which blocks minting) and keeps the
        chip from RUN; the result is carried in every quote, so a regulator sees it remotely."""
        if self.gpu is None:
            return {}
        if self.gpu.power == "ON":
            before = self.gpu.pwrbrk
            self.gpu.set_pwrbrk(True)                 # a pulse of microseconds on silicon
            brake = self.gpu.sense_brake()
            self.gpu.set_pwrbrk(before)
        else:
            brake = self.gpu.sense_lever_net("pwrbrk")   # a GPU in reset or off cannot report; use the net's loopback
        result = {"pwrbrk": brake, "perst": self.gpu.sense_lever_net("perst"), "pwr_en": self.gpu.sense_lever_net("pwr_en")}
        self.lever_check = result
        if not self._levers_can_stop(result) and reasons.LEVER_UNWIRED not in self.alarms:
            self.raise_alarm(reasons.LEVER_UNWIRED, "governor", {"levers": result})
        return result

    def _switches_locked(self) -> bool:
        """Every governed switch reports its in-band management locked and its firmware as the reference expects
        (adversarial audit 3: the host could reprogram NVSwitch and PCIe switch ports in band). A switch that does not
        raises SWITCH_UNLOCKED, which blocks minting, and the chip stays out of RUN."""
        bad = [k for k, sw in self.switches.items() if hasattr(sw, "lock_report") and not sw.lock_report()["locked"]]
        if bad and reasons.SWITCH_UNLOCKED not in self.alarms:
            self.raise_alarm(reasons.SWITCH_UNLOCKED, "governor", {"switches": bad})
        return not bad

    @staticmethod
    def _levers_can_stop(result: dict) -> bool:
        """The levers that stop compute (brake and reset) must both be proven. A board without a slot power cut is a
        stated, quoted limitation (the board interlock and SAFE then rest on reset), not a reason to refuse RUN."""
        return bool(result.get("pwrbrk")) and bool(result.get("perst"))

    def _try_run(self) -> None:
        """HALTED_INITIAL -> RUN when there is no cause, a live heartbeat, loop current, and levers proven wired."""
        if self.state == HALTED_INITIAL and self.cause is None and self.hb_expiry > self.clock.now() \
                and not self.loop_switch_open and (self.loop is None or self.loop.current()):
            if self.gpu is not None and not self._levers_can_stop(self.lever_selftest()):
                return                                    # never release the GPU from a governor that cannot stop it
            if not self._switches_locked():
                return                                    # never run behind a switch the host can reprogram
            self._apply_rung(RUN)

    def sense_loop(self) -> None:
        """Read the halt loop. A running chip that loses loop current drops to HALT (to a loop-broken cause if the
        wire is cut, or a loop-open cause if the switch is open). A chip that is waiting to start tries to run."""
        if self.loop is None:
            return
        if not self.loop.current() and self.state in (RUN, THROTTLE):
            self.enter_safe_mode(reasons.LOOP_BROKEN if not self.loop.wire_intact else reasons.LOOP_OPEN, rung=HALT)
        elif self.state == HALTED_INITIAL:
            self._try_run()

    def tick(self) -> None:
        """Time passes: the counter, heartbeat expiry, rung escalation, the meter, the output cross-check,
        the loop beacon's collection window."""
        with self.lock:
            now = self.clock.now()
            if self.gpu is not None and not self.fuses.zeroized:
                self.gpu.keepalive()            # the board interlock's keep-alive: only a live governor renews it
                if self.state == RUN:
                    self.lever_selftest()       # a lever cut while running raises LEVER_UNWIRED, which stops minting
                    if not self._switches_locked():
                        self.enter_safe_mode(reasons.SWITCH_UNLOCKED, rung=HALT)   # unlocked under us: stop
            elapsed_us = int(round((now - self.last_tick_t) * 1e6))
            if elapsed_us > 0:
                self.root.counter.tick(elapsed_us)
                self.store.data["counter"] = self.root.counter.value
                self.store.save()
            self.last_tick_t = now
            # F06: an installed edition cannot outlive its own expiry. Policy expiry is enforced as a specified
            # fail-closed transition on every tick, not only at load; a running chip whose edition has expired drops
            # to HALT even while heartbeats and the loop still hold.
            if self.state in (RUN, THROTTLE) and self.policy and float(self.policy.get("expires_at", float("inf"))) <= now \
                    and self.cause != reasons.POLICY_EXPIRED_RUNTIME:
                self.enter_safe_mode(reasons.POLICY_EXPIRED_RUNTIME, rung=HALT)
            if self.state == RUN and now > self.hb_expiry:
                stale = self.staged is not None and not self._staged_epoch_live(now)
                self.enter_safe_mode(reasons.EPOCH_STRAGGLER if stale else reasons.HEARTBEAT_LOST)
                if self.state != RUN:
                    self.rung_entered_at = min(self.rung_entered_at, self.hb_expiry)   # the timer starts when the heartbeat lapsed
            sm = (self.policy or {}).get("safe_mode", {})
            # The escalation timers are fixed in the hard core at synthesis (rtl/governor_rtl/top.py: 30 s and 300 s). An
            # edition may shorten them, never lengthen them (audit 2026-10-26: a signed edition set them to 1e12 s and kept
            # GPUs powered for a day without any heartbeat).
            t_throttle = min(float(sm.get("T_throttle_s", MAX_T_THROTTLE_S)), MAX_T_THROTTLE_S)
            t_halt = min(float(sm.get("T_halt_s", MAX_T_HALT_S)), MAX_T_HALT_S)
            # Every rung whose timer ran out during this step is taken, at the moment it ran out, as the hard core's
            # counters do; one long step does not stop at the first rung.
            if self.state == THROTTLE and self.cause and now - self.rung_entered_at >= t_throttle:
                self.rung_entered_at += t_throttle
                self.log.append("halt.escalate", {"to": HALT, "cause": self.cause})
                self.cause_entry = self.log.size - 1
                self._apply_rung(HALT, opens_loop=self.cause_opens_loop)
            if self.state == HALT and self.cause and now - self.rung_entered_at >= t_halt:
                self.rung_entered_at += t_halt
                self.log.append("halt.escalate", {"to": SAFE, "cause": self.cause})
                self.cause_entry = self.log.size - 1
                self._apply_rung(SAFE, opens_loop=self.cause_opens_loop)
            self._check_boot_window(now)
            self.read_meter()
            self._compute_budget_check()
            self._check_unpresented_output()
            if self.gpu is not None:
                self.gpu.service_lease(now)        # a released key expires on time even while the GPU is idle (F02)
            self._close_loop_window()
            self.sense_loop()

    def _check_boot_window(self, now: float) -> None:
        """The hardware's NO_FIRST_HEARTBEAT: still in HALTED_INITIAL with no cause, never armed since reset, and the
        boot window has passed. Raised once (sticky), logged with the chip and since when, and sent on the fabric so
        the neighbours and the supervisor log it too: "this chip, waiting for its first heartbeat, since <boot>"."""
        if self.state == HALTED_INITIAL and self.cause is None and not self.hb_seen and now - self.boot_at >= BOOT_WINDOW_S \
                and reasons.NO_FIRST_HEARTBEAT not in self.alarms:
            self.raise_alarm(reasons.NO_FIRST_HEARTBEAT, "hardware",
                             {"chip_id": self.chip_id, "since": self.boot_at, "boot_window_s": BOOT_WINDOW_S})

    def _cmd_exclude(self, body, env):
        """EXCLUDE: the authority's deliberate, logged way past a chip that never
        got its first heartbeat. Same authority class and checks as CLEAR (bound to this chip, expiring, typed, never
        the heartbeat key). Only a chip in HALTED_INITIAL with no cause and no live heartbeat is excluded: its loop
        switch closes so the rest of the rack can run, and its own levers stay on (the state stays HALTED_INITIAL:
        brake, reset, power off). A valid heartbeat ends it by arming the chip normally; so does a reset, and a HALT or
        a tamper (with the loop open). Never silent: an alarm, a log entry naming the signer, a fabric message."""
        ok, why = self._check_signed(env, "authority", "EXCLUDE")
        if not ok:
            return self._deny("exclude", why)
        if self.state != HALTED_INITIAL or self.cause is not None or self.hb_expiry > self.clock.now():
            return self._deny("exclude", reasons.EXCLUDE_NOT_WAITING, state=self.state, cause=self.cause, by=env["signer"])
        self.excluded = True
        self.loop_switch_open = False
        self.log.append("exclude", {"chip_id": self.chip_id, "by": env["signer"], "since": self.boot_at,
                                    "hb_seen": self.hb_seen})
        self._persist_rung()
        self.raise_alarm(reasons.EXCLUDED, "hardware", {"chip_id": self.chip_id, "by": env["signer"]})
        return {"ok": True, "why": reasons.OK}

    def _cmd_clear(self, body, env):
        """Only the authority clears, only after the cause is logged and a neighbor has the log."""
        ok, why = self._check_signed(env, "authority", "CLEAR")
        if not ok:
            return self._deny("clear", reasons.CLEAR_UNAUTHORIZED)
        if self.cause is None:
            return {"ok": True, "why": reasons.OK}
        if self.cause_entry is None or not self.log.has("halt.cause", cause=self.cause) and not self.log.has("halt.escalate", cause=self.cause):
            return self._deny("clear", reasons.CLEAR_CAUSE_NOT_LOGGED)
        # with a neighbour on the fabric, a neighbour must have acknowledged a log head past the cause before it can clear
        if self.fabric is not None and len(self.fabric.members) > 1 and not any(size > self.cause_entry for size in self.acked_heads.values()):
            return self._deny("clear", reasons.CLEAR_NO_NEIGHBOR_ACK)
        self.log.append("halt.cleared", {"cause": self.cause, "by": env["signer"]})
        self.cause, self.cause_entry, self.cause_opens_loop = None, None, False
        if self.gpu is not None:
            self.gpu.output_blocked = False
        self._apply_rung(HALTED_INITIAL)
        self.loop_switch_open = False           # armed; RUN follows when the whole loop is closed and the heartbeat is live
        self._persist_rung()
        self._try_run()
        return {"ok": True, "why": reasons.OK}

    # ------------------------------------------------------------------ policy change
    def _cmd_policy_propose(self, body, env):
        """POLICY_PROPOSE. Stages a new policy image. The image must pass the same checks as a policy in force, and its
        version must be newer. Staging changes nothing in force yet. It starts a deadline, and heartbeats may
        carry the staged epoch only until that deadline passes."""
        image = body.get("image")
        if not image:
            return self._deny("policy_propose", reasons.POLICY_QUORUM)
        ok, why = self._check_edition(image)          # the same checks as an edition put in force, all of them
        if not ok:
            return self._deny("policy_propose", why)
        self.staged, self.staged_at = image, self.clock.now()
        self.store.data["staged"] = {"image": image, "at": self.staged_at}
        self.store.save()
        self.log.append("policy.staged", {"epoch": policy_epoch(image), "version": image["version"]})
        return {"ok": True, "why": reasons.OK, "ack": self.key.sign({"type": "epoch-ack", "epoch": policy_epoch(image), "chip_id": self.chip_id})}

    def _cmd_policy_commit(self, body, env):
        """POLICY_COMMIT. Moves from the staged image to its epoch, if the epoch matches what was staged. The
        endpoints get the new signed epoch, and open ports are reprogrammed if the chip is running."""
        if self.staged is None or policy_epoch(self.staged) != body.get("epoch"):
            return self._deny("policy_commit", reasons.POLICY_NOT_STAGED)
        old = self.epoch
        image, self.staged, self.staged_at = self.staged, None, 0.0
        self.store.data["staged"] = None
        ok, why = self._accept_policy(image)
        self.store.save()
        if not ok:
            return self._deny("policy_commit", why)
        self.log.append("policy.committed", {"old": old, "new": self.epoch})
        for ep in self.endpoints.values():
            if hasattr(ep, "install_edition"):
                ep.install_edition(image)      # the endpoint checks the edition itself before it trusts it
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
                if hasattr(ep, "install_edition"):
                    ep.install_edition(image)
                ep.set_epoch(self.signed_epoch())
        return ok, why

    # ------------------------------------------------------------------ lifecycle and tamper
    def debug_access(self) -> tuple[bool, str]:
        """Ask the fuses for debug access. The answer depends on the chip's lifecycle state. Every request is logged,
        granted or refused."""
        ok, why = self.fuses.debug_access()
        self.log.append("debug.granted" if ok else "debug.refused", {"lifecycle": self.fuses.lifecycle})
        return ok, why

    def tamper_event(self, kind: str = "mesh") -> None:
        """A physical tamper, such as a cut mesh. Logs it, sets the cause to TAMPER with the loop opening, moves to
        SAFE, wipes the root secrets and closes all ports. After this, every mailbox command is refused as zeroized."""
        with self.lock:
            self.log.append("tamper", {"kind": kind})
            self.cause, self.cause_opens_loop = reasons.TAMPER, True
            self.cause_entry = self.log.size - 1
            self._apply_rung(SAFE, opens_loop=True)
            self.root.zeroize()
            self.close_ports()

    # ------------------------------------------------------------------ the fabric
    def fabric_send(self, mtype: str, body: dict, to: str | None = None) -> list:
        """Send one signed message on the fabric. ``to`` picks one neighbour, and None sends to all of them. Each
        message carries a fresh sequence number, the epoch and the time. Returns whatever the fabric hands back.
        A zeroized chip sends nothing."""
        if self.fabric is None or self.fuses.zeroized:
            return []
        self.fabric_seq += 1
        self.store.data["fabric_seq"] = self.fabric_seq
        self.store.save()
        self.ops["fabric_msg"] += 1
        payload = {"type": mtype, "from": self.chip_id, "seq": self.fabric_seq, "epoch": self.epoch, "time": self.mono(), "body": body}
        if getattr(self, "_restore_fabric_macs", False):
            self._restore_fabric_macs = False
            self._derive_fabric_macs()
        if mtype not in ("QUOTE", "ROSTER") and self.fabric_macs:
            # roster traffic: one MAC per recipient at line rate, not one P-384 signature that every member verifies
            peers = [to] if to is not None else list(self.fabric_macs)
            msg = {"payload": payload, "signer": self.key.key_id,
                   "macs": {p: hmac_sha256(self.fabric_macs[p], canonical(payload)) for p in peers if p in self.fabric_macs}}
            self.ops["fabric_mac"] += len(msg["macs"])
        else:
            msg = self.key.sign(payload)
            self.ops["fabric_sign"] += 1
        return self.fabric.send(self.chip_id, msg, to=to)

    def _verify_governor_quote(self, qmsg: dict) -> VerifyKey | None:
        """Chain: governor vendor key -> device cert -> alias cert -> quote; firmware in the reference values."""
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

    def _fabric_kx_public(self) -> str:
        """This chip's fabric key-agreement public key, hex."""
        return self.fabric_kx.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    def _derive_fabric_macs(self) -> None:
        """One MAC key per roster member: HKDF over X25519(this chip, that member), bound to the roster and to the
        ordered pair, so a key is good for exactly two chips on one roster. Members whose quote carried no key
        agreement key keep the signed path."""
        self.fabric_macs = {}
        if not self.roster:
            return
        for m in self.roster["members"]:
            if m["chip_id"] == self.chip_id or not m.get("fabric_kx"):
                continue
            try:
                shared = self.fabric_kx.exchange(X25519PublicKey.from_public_bytes(bytes.fromhex(m["fabric_kx"])))
            except ValueError:
                continue
            pair = sorted([self.chip_id, m["chip_id"]])
            info = canonical(["fabric-mac", self.roster["roster_id"], pair])
            self.fabric_macs[m["chip_id"]] = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(shared)

    def _fabric_authentic(self, msg: dict, sender: str) -> bool:
        """A roster member's fabric message: a MAC under the pairwise key when the message carries MACs, otherwise
        the member's signature."""
        if getattr(self, "_restore_fabric_macs", False):
            self._restore_fabric_macs = False
            self._derive_fabric_macs()
        if "macs" in msg:
            k = self.fabric_macs.get(sender)
            tag = (msg.get("macs") or {}).get(self.chip_id)
            return k is not None and isinstance(tag, str) and hmac.compare_digest(tag, hmac_sha256(k, canonical(msg["payload"])))
        key = self.roster_keys.get(sender)
        return key is not None and verify_object(msg, key)

    def quote_for_job(self, job_id: str) -> dict:
        """This governor's signed quote for a job: a statement of its measurements and its GPU, with its certificates.
        Roster formation uses it to show that the chip is genuine."""
        nonce = digest(["job", job_id])
        return {"chip_id": self.chip_id, "quote": self.root.quote(nonce, {"gpu_fingerprint": self.fingerprint, "gpu_chip_id": self.gpu.chip_id if self.gpu else None,
                                                                         "fabric_kx": self._fabric_kx_public()}),
                "device_cert": self.device_cert, "alias_cert": self.alias_cert, "job_id": job_id}

    def announce(self, job_id: str) -> None:
        """Broadcast this governor's quote for a job, so that the other governors can build the roster. The quote
        is also kept in this chip's own pending list."""
        q = self.quote_for_job(job_id)
        self.pending_quotes.setdefault(job_id, {})[self.chip_id] = {**q, "key": self.key.public}
        self.fabric_send("QUOTE", q)

    def _cmd_roster_join(self, body, env):
        """The verified host names the job; the governor broadcasts its quote to start roster formation."""
        ok, why = self._check_signed(env, "host", "ROSTER_JOIN")
        if not ok:
            return self._deny("roster_join", why)
        job_id = env["payload"].get("job_id")
        if not job_id:
            return self._deny("roster_join", reasons.MBOX_UNKNOWN_COMMAND + ".no_job")
        self.announce(job_id)
        return {"ok": True, "why": reasons.OK}

    def _revoked_governor(self, chip_id: str, key: VerifyKey | None) -> bool:
        """True when the edition in force revokes this governor, by chip id or by key (audit 2026-10-26: a revoked
        governor used to be admitted to new rosters)."""
        revoked = set((self.policy or {}).get("revocations", []))
        return chip_id in revoked or (key is not None and key.key_id in revoked)

    def build_roster(self, job_id: str, expected: list[str], ttl_s: float = 3600.0) -> dict | None:
        """The leader (lowest chip id among valid quotes) signs the roster. A governor the edition revokes is left out."""
        quotes = {c: q for c, q in self.pending_quotes.get(job_id, {}).items() if not self._revoked_governor(c, q.get("key"))}
        members = sorted(c for c in expected if c in quotes)
        if not members or min(quotes) != self.chip_id:
            return None
        roster = {"type": "roster", "roster_id": digest([job_id, members, self.clock.now()]), "job_id": job_id,
                  "leader": self.chip_id, "expires_at": self.clock.now() + ttl_s, "time": self.mono(),
                  "members": [{"chip_id": c, "key": quotes[c]["key"].hex, "gpu_chip_id": quotes[c]["quote"]["payload"].get("gpu_chip_id"),
                               "gpu_fingerprint": quotes[c]["quote"]["payload"].get("gpu_fingerprint"),
                               "fabric_kx": quotes[c]["quote"]["payload"].get("fabric_kx")} for c in members]}
        signed = self.key.sign(roster)
        self._adopt_roster(signed)
        self.fabric_send("ROSTER", {"roster": signed})
        return signed

    def _adopt_roster(self, signed: dict) -> tuple[bool, str]:
        """Adopt a roster only if the leader's signature verifies against the leader's own verified quote."""
        try:
            r = signed["payload"]
            quotes = self.pending_quotes.get(r["job_id"], {})
            leader = quotes.get(r["leader"])
            if leader is None or not verify_object(signed, leader["key"]):
                return False, reasons.ROSTER_BAD_SIGNATURE
            if self.chip_id not in {m["chip_id"] for m in r["members"]} or r["expires_at"] <= self.clock.now():
                return False, reasons.ROSTER_NOT_MEMBER
            for m in r["members"]:
                if m["chip_id"] not in quotes or quotes[m["chip_id"]]["key"].hex != m["key"]:
                    return False, reasons.ROSTER_QUOTE_INVALID
                if self._revoked_governor(m["chip_id"], quotes[m["chip_id"]]["key"]):
                    return False, reasons.ROSTER_QUOTE_INVALID + ".revoked"
        except (KeyError, TypeError):
            return False, reasons.ROSTER_BAD_SIGNATURE
        self.roster = r
        self.roster_keys = {m["chip_id"]: VerifyKey.from_hex(m["key"]) for m in r["members"]}
        self._derive_fabric_macs()
        self.store.data["roster"] = signed
        self.log.append("roster.adopted", {"roster_id": r["roster_id"], "members": [m["chip_id"] for m in r["members"]]})
        if self.state == RUN:
            self.open_ports_for_roster()
        return True, reasons.OK

    def _fabric_admit(self, msg: dict, p: dict, mtype: str, sender: str) -> str | None:
        """The checks every roster message passes: a member, authentic, not a replay, the current epoch. Records the
        sequence number. Returns None when admitted, else the reason. Runs under ``fabric_lock``."""
        with self.fabric_lock:
            if self.roster_keys.get(sender) is None:
                self.log.append("fabric.dropped", {"why": reasons.FABRIC_NOT_MEMBER, "from": sender, "type": mtype})
                return reasons.FABRIC_NOT_MEMBER
            if not self._fabric_authentic(msg, sender):
                self.log.append("fabric.dropped", {"why": reasons.FABRIC_BAD_SIGNATURE, "from": sender})
                return reasons.FABRIC_BAD_SIGNATURE
            if int(p.get("seq", -1)) <= self.fabric_last_seq.get(sender, -1):
                self.log.append("fabric.dropped", {"why": reasons.FABRIC_REPLAY, "from": sender})
                return reasons.FABRIC_REPLAY
            if mtype not in ("HALT_CAUSE", "CHECKPOINT", "CHECKPOINT_ACK") and p.get("epoch") != self.epoch:
                self.log.append("fabric.dropped", {"why": reasons.FABRIC_STALE_EPOCH, "from": sender})
                return reasons.FABRIC_STALE_EPOCH
            self.fabric_last_seq[sender] = int(p["seq"])
            self.store.data["fabric_last_seq"] = self.fabric_last_seq
            self.store.save()
            return None

    def on_fabric(self, msg: dict) -> Any:
        """Every message is checked here. The wire itself checks nothing."""
        try:
            p = msg["payload"]
            mtype, sender = p["type"], p["from"]
        except (KeyError, TypeError):
            return {"ok": False, "why": reasons.FABRIC_BAD_SIGNATURE}
        if mtype in BUDGET_MESSAGES:
            # The budget unit answers a peer's RESERVE, COMMIT or RELEASE under its own lock, never the main one: with
            # 2-of-3 budget owners (adversarial audit 3) two owners each serving a request reserve at each other, and
            # under one lock per chip that was a deadlock. In silicon the budget counters are their own block.
            self.ops["fabric_rx"] += 1
            why = self._fabric_admit(msg, p, mtype, sender)
            if why is not None:
                return {"ok": False, "why": why}
            with self.budget_lock:
                return getattr(self, "_on_" + mtype.lower())(sender, p["body"])
        with self.lock:
            self.ops["fabric_rx"] += 1
            if mtype == "QUOTE":
                return self._on_quote(msg)
            if mtype == "ROSTER":
                return self._on_roster(msg)
            if mtype == "HEARTBEAT":
                return self._on_heartbeat_relay(msg, sender)
            why = self._fabric_admit(msg, p, mtype, sender)
            if why is not None:
                return {"ok": False, "why": why}
            handler = getattr(self, "_on_" + mtype.lower(), None)
            if handler is None:
                return {"ok": False, "why": reasons.MBOX_UNKNOWN_COMMAND}
            return handler(sender, p["body"])

    def _on_heartbeat_relay(self, msg: dict, sender: str):
        """A relayed heartbeat: the authority's envelope is what counts; the relay's signature vouches
        for the hop count. An unknown relay (before the roster exists) is accepted with no further relaying."""
        body = msg["payload"].get("body", {})
        key = self.roster_keys.get(sender)
        max_hops = self.policy["fabric"]["max_hops"] if self.policy else 0
        if key is None:
            return self._heartbeat(body.get("authority"), hops=max_hops)
        if not self._fabric_authentic(msg, sender):
            self.log.append("fabric.dropped", {"why": reasons.FABRIC_BAD_SIGNATURE, "from": sender, "type": "HEARTBEAT"})
            return {"ok": False, "why": reasons.FABRIC_BAD_SIGNATURE}
        return self._heartbeat(body.get("authority"), hops=int(body.get("hops", 1)))

    def _on_quote(self, msg: dict):
        """A quote from another governor. Checks the chain of certificates (vendor, device, alias), the quote's
        signature, its measurement against the reference values, and the chip identity. A quote that fails is
        dropped and logged. A valid quote is kept for the roster."""
        body = msg["payload"]["body"]
        alias = self._verify_governor_quote(body)
        if alias is None or not verify_object(msg, alias):
            self.log.append("fabric.dropped", {"why": reasons.ROSTER_QUOTE_INVALID, "from": msg["payload"].get("from")})
            return {"ok": False, "why": reasons.ROSTER_QUOTE_INVALID}
        self.pending_quotes.setdefault(body["job_id"], {})[body["chip_id"]] = {**body, "key": alias}
        return {"ok": True, "why": reasons.OK}

    def _on_roster(self, msg: dict):
        """A roster from the leader. Adopts it if it verifies (see ``_adopt_roster``). A roster that fails is logged."""
        signed = (msg["payload"].get("body") or {}).get("roster")
        ok, why = self._adopt_roster(signed) if signed else (False, reasons.ROSTER_BAD_SIGNATURE)
        if not ok:
            self.log.append("fabric.dropped", {"why": why, "from": msg["payload"].get("from"), "type": "ROSTER"})
        return {"ok": ok, "why": why}

    def _on_reserve(self, sender: str, body: dict):
        """Budget owner side of RESERVE. If this chip is the owner of the budget key, it reserves the amount.
        Any other chip refuses."""
        with self.budget_lock:
            spec = self._budget_owners(body["key"])
            if spec is None or self.chip_id not in spec[0]:
                return {"ok": False, "why": reasons.GATE_BUDGET_OWNER_UNREACHABLE}
            # The owner enforces the limit and window of the edition in force, never the ones the requester states (audit
            # 2026-10-26: the owner used to reserve against the requester's limit). The tightest rule that spends from this
            # key sets them; a key no rule spends from reserves nothing.
            spends = [r["budget"] for r in self.policy["rules"] if (r.get("budget") or {}).get("key") == body["key"]]
            amount = body.get("amount")
            if not spends or not finite_number(amount) or amount <= 0:
                return {"ok": False, "rid": None, "why": reasons.GATE_BUDGET}
            limit = min(float(b["limit"]) for b in spends)
            window_s = max(float(b["window_s"]) for b in spends)
            rid = self.ledger.reserve(body["key"], amount, limit, window_s, self.clock.now(), body["ttl"])
            if rid:
                self.reservation_holder[rid] = sender        # only this member may commit or release it
            self.ops["shared_reserve"] += 1
            return {"ok": rid is not None, "rid": rid, "why": reasons.OK if rid else reasons.GATE_BUDGET}

    def _on_commit(self, sender: str, body: dict):
        """Budget owner side of COMMIT. Commits a reservation at the owner, so that it counts against the budget."""
        with self.budget_lock:
            if self.reservation_holder.get(body.get("rid"), sender) != sender:
                return {"ok": False, "why": reasons.GATE_BUDGET + ".not_the_reserver"}
            return {"ok": self.ledger.commit(body["key"], body["rid"], self.clock.now()), "why": reasons.OK}

    def _on_release(self, sender: str, body: dict):
        """Budget owner side of RELEASE. Gives back a reservation that was not spent."""
        with self.budget_lock:
            if self.reservation_holder.get(body.get("rid"), sender) != sender:
                return {"ok": False, "why": reasons.GATE_BUDGET + ".not_the_reserver"}
            self.ledger.release(body["key"], body["rid"])
            self.reservation_holder.pop(body.get("rid"), None)
            return {"ok": True, "why": reasons.OK}

    def _on_alarm(self, sender: str, body: dict):
        """An alarm raised by another governor. Adversarial audit 3: one member broadcasting any code used to freeze
        minting on every chip in the rack. A peer's alarm now becomes an alarm here only when at least
        FABRIC_ALARM_QUORUM distinct members report the same code; until then it is logged as a report. Alarms this
        chip can see for itself (its own loop, its own counters) are raised locally and need no peer."""
        detail = body.get("detail")
        code = str(body.get("code"))
        reporters = self.fabric_alarm_reports.setdefault(code, set())
        reporters.add(sender)
        self.log.append("alarm.reported", {"code": code, "by": sender, "reporters": len(reporters)})
        # A status or session alarm blocks nothing here, so one member's report is recorded at once (a chip saying it
        # never got its first heartbeat is reporting on itself).
        if len(reporters) >= FABRIC_ALARM_QUORUM or code in STATUS_ALARMS or code in SESSION_SCOPED_ALARMS:
            self.raise_alarm(code, "fabric", detail if isinstance(detail, dict) else None)
        return {"ok": True, "why": reasons.OK}

    # ------------------------------------------------------------------ the loop member-count beacon
    def _on_loop_beacon(self, beacon: dict) -> None:
        """The authority's LOOP_BEACON (inside the heartbeat it signed): close the previous window, then
        report this governor's own switch state and loop sense to everyone on the fabric."""
        if self.loop is None or not isinstance(beacon, dict):
            return
        self._close_loop_window()
        self.loop_beacon = {"loop_id": beacon.get("loop_id"), "seq": int(beacon.get("seq", -1)),
                            "expected": [str(m) for m in beacon.get("expected_members", [])]}
        report = {"loop_id": self.loop_beacon["loop_id"], "seq": self.loop_beacon["seq"],
                  "switch_open": bool(self.loop_switch_open), "current_sensed": bool(self.loop.current())}
        self.loop_reports.setdefault(report["seq"], {})[self.chip_id] = report
        self.fabric_send("LOOP_REPORT", report)

    def _on_loop_report(self, sender: str, body: dict):
        """A roster member's signed report (the fabric checked key, signature, sequence and epoch)."""
        try:
            seq = int(body["seq"])
            report = {"loop_id": body["loop_id"], "seq": seq, "switch_open": bool(body["switch_open"]), "current_sensed": bool(body["current_sensed"])}
        except (KeyError, TypeError, ValueError):
            self.log.append("fabric.dropped", {"why": reasons.FABRIC_BAD_SIGNATURE, "from": sender, "type": "LOOP_REPORT"})
            return {"ok": False, "why": reasons.FABRIC_BAD_SIGNATURE}
        self.loop_reports.setdefault(seq, {})[sender] = report
        return {"ok": True, "why": reasons.OK}

    def _close_loop_window(self) -> None:
        """End of the collection window (next tick or next beacon): a silent expected member is logged; a
        member whose switch is open by its own account while anyone senses current is jumpered or lying."""
        # Only reports of the same beacon seq are compared with each other (never a report against the
        # loop as sensed now), so a switch that opened or closed after the beacon is never a false positive.
        b, self.loop_beacon = self.loop_beacon, None
        if b is None:
            return
        reports = {c: r for c, r in self.loop_reports.pop(b["seq"], {}).items() if r["loop_id"] == b["loop_id"]}
        for seq in [s for s in self.loop_reports if s < b["seq"]]:       # late reports for older beacons; newer ones are kept
            self.loop_reports.pop(seq)
        if self.chip_id not in b["expected"] or self.loop is None or self.loop.loop_id != b["loop_id"]:
            return                                       # not a member of this loop: nothing to judge
        for member in b["expected"]:
            if member not in reports:
                self.log.append("loop.member_silent", {"why": reasons.LOOP_MEMBER_SILENT, "member": member, "seq": b["seq"]})
        current_sensed = any(r["current_sensed"] for r in reports.values())
        for member, r in sorted(reports.items()):
            if member in b["expected"] and r["switch_open"] and current_sensed:
                self.log.append("loop.jumpered", {"why": reasons.LOOP_JUMPERED, "member": member, "seq": b["seq"]})
                self.raise_alarm(reasons.LOOP_JUMPERED, "governor", {"member": member, "seq": b["seq"]})
                self.enter_safe_mode(reasons.LOOP_JUMPERED)

    def _on_halt_cause(self, sender: str, body: dict):
        """Another governor reports a halt cause. It is logged only. It does not change this chip's state."""
        self.log.append("fabric.halt_cause", {"from": sender, "cause": body.get("cause")})
        return {"ok": True, "why": reasons.OK}

    def _on_checkpoint(self, sender: str, body: dict):
        """A neighbour's signed log checkpoint. Records the neighbour's log head and sends the neighbour an
        acknowledgement. A neighbour uses that acknowledgement when it clears a cause (see ``_cmd_clear``)."""
        cp = body.get("checkpoint")
        key = self.roster_keys.get(sender)
        if not cp or key is None or not verify_object(cp, key):
            self.log.append("fabric.dropped", {"why": reasons.FABRIC_BAD_SIGNATURE, "from": sender, "type": "CHECKPOINT"})
            return {"ok": False, "why": reasons.FABRIC_BAD_SIGNATURE}
        self.log.record_neighbor_head(sender, cp["payload"]["head"])
        self.fabric_send("CHECKPOINT_ACK", {"head": cp["payload"]["head"], "size": cp["payload"]["size"]}, to=sender)
        return {"ok": True, "why": reasons.OK}

    def _on_checkpoint_ack(self, sender: str, body: dict):
        """A neighbour acknowledged this chip's checkpoint. The acknowledged head and size are recorded. CLEAR
        needs an acknowledgement that covers the cause (see ``_cmd_clear``)."""
        self.acked_heads[body["head"]] = int(body["size"])
        return {"ok": True, "why": reasons.OK}

    def publish_checkpoint(self) -> None:
        """Send this chip's signed log checkpoint to each fabric neighbour."""
        if self.fabric is None:
            return
        cp = self.log.checkpoint(self.key, self.chip_id)
        for n in self.fabric.neighbors(self.chip_id):
            self.fabric_send("CHECKPOINT", {"checkpoint": cp}, to=n)
