"""A simulated NVIDIA GPU as the governor sees it.

The GPU is untrusted and unchanged. The model has: a vendor-issued device certificate and a
confidential-computing attestation report over a nonce; a running state that responds to the
physical levers whether or not its software cooperates; exits (the switches its traffic
passes, and the internal paths a future integrated tier would check); a token stream for the
meter; and an output buffer the runtime presents for signing.

Simplifications: kernels are ``run_tokens(n)``; transfers are ``transfer(exit, peer, bytes)``.
"""
from __future__ import annotations

from .crypto import SigningKey, digest

EXITS = {
    # name: (governed at rack tier?, checked only at integrated tier?)
    "nvswitch": True, "pcie": True, "dpu": True, "storage": True,
    "copy_engine": False, "peer_mmu": False,       # inside the GPU: integrated tier only
    "display": None, "jtag": None, "debug": None,  # bricked by policy
}


class GPU:
    def __init__(self, name: str, clock, vendor_key: SigningKey, firmware_digest: str,
                 levers: dict | None = None, direct_nvlink: bool = False):
        self.name = name
        self.clock = clock
        self.chip_id = "gpu-" + digest(name)[:12]
        self.firmware_digest = firmware_digest
        self.device_key = SigningKey.generate()
        # confidential-computing key: weights are released sealed to its public half, which the signed report carries
        from .sealing import public_hex
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        self.cc_key = X25519PrivateKey.generate()
        self.cc_pub = public_hex(self.cc_key)
        self.governor_key = None                  # the governor's signing key, set when it attaches (verifies leases)
        self.sealed = False                       # the loaded job's weights are sealed: no lease, no tokens
        self.dek = None                           # the model's data key, in protected memory only while a lease holds
        self.lease: dict | None = None
        self.weights_plain: bytes | None = None   # decrypted weights, in protected memory
        self.key_events: list[dict] = []         # what happened to the key, for the experiment's record
        self.device_cert = vendor_key.sign({"type": "gpu-device-cert", "chip_id": self.chip_id, "pub": self.device_key.public.hex})
        self.levers_available = levers or {"pwrbrk": True, "perst": True, "pwr_en": True}
        self.direct_nvlink = direct_nvlink        # a board with no NVSwitch: peer traffic bypasses every switch
        # physical inputs
        self.pwrbrk = False
        self.perst = False
        self.pwr_en = True
        # state
        self.power = "ON"
        self.clock_state = "FULL"
        self.job = None                           # the model digest of the loaded job
        self.manifest_digest = ""                 # set by the loader; reported only at the integrated tier
        self.policy_epoch_reported = ""
        self.ignore_software = False              # a GPU whose firmware ignores management commands
        self.open_paths: list[str] = []           # debug paths left open (reported in attestation)
        self.tokens = 0
        self.cycles = 0
        self.bytes_out = 0
        self.bytes_in = 0
        self.switches: dict[str, object] = {}     # exit -> Switch (the governor attaches these)
        self.checkers: dict[str, object] = {}     # exit -> DescriptorChecker (integrated tier)
        self.output_hook = None                   # integrated tier: inline hash callback
        self.output_blocked = False
        self.gap_log: list[dict] = []             # transfers that passed with no checker (the recorded residual)

    # --- attestation ------------------------------------------------------------
    def attestation_report(self, nonce: str, tier: str) -> dict:
        payload = {"type": "gpu-report", "chip_id": self.chip_id, "firmware_digest": self.firmware_digest,
                   "nonce": nonce, "open_paths": list(self.open_paths), "cc_pub": self.cc_pub}
        if tier == "integrated":
            payload["manifest_digest"] = self.manifest_digest
            payload["policy_epoch"] = self.policy_epoch_reported
        return {"report": self.device_key.sign(payload), "cert": self.device_cert}

    # --- levers: physics, not requests -------------------------------------------
    def set_pwrbrk(self, on: bool) -> None:
        if self.levers_available.get("pwrbrk"):
            self.pwrbrk = on
            self._apply()

    def set_perst(self, on: bool) -> None:
        if self.levers_available.get("perst"):
            self.perst = on
            self._apply()

    def set_pwr_en(self, on: bool) -> None:
        if self.levers_available.get("pwr_en"):
            self.pwr_en = on
            self._apply()

    def _apply(self) -> None:
        if not self.pwr_en:
            self.power, self.clock_state, self.job = "OFF", "OFF", None
            self.zeroize("power off")             # protected memory does not survive power loss
            return
        if self.perst:
            self.power, self.clock_state, self.job = "RESET", "OFF", None
            self.zeroize("reset")
            return
        self.power = "ON"
        self.clock_state = "BRAKED" if self.pwrbrk else "FULL"

    def software_power_limit(self, watts: int) -> bool:
        """A management-bus request. A GPU with hostile firmware ignores it."""
        if self.ignore_software:
            return False
        self.clock_state = "LIMITED" if watts < 300 else "FULL"
        return True

    @property
    def running(self) -> bool:
        return self.power == "ON" and self.job is not None and self.clock_state in ("FULL", "LIMITED")

    # --- work --------------------------------------------------------------------
    def load(self, model_digest: str) -> None:
        if self.power == "ON":
            self.job = model_digest
            self.manifest_digest = model_digest

    # --- sealed weights: the origin gate (docs/18 question 20) --------------------------------
    def _lease_ok(self, lease: dict | None) -> bool:
        from .crypto import verify_object
        return bool(lease and self.governor_key is not None and verify_object(lease, self.governor_key)
                    and lease["payload"].get("gpu") == self.chip_id and lease["payload"].get("type") == "key-lease")

    def install_key(self, key_box: dict, lease: dict) -> bool:
        """KEY_RELEASE's answer: the data key sealed to this GPU, and a governor-signed lease."""
        from .sealing import open_sealed
        if not self._lease_ok(lease):
            return False
        dek = open_sealed(self.cc_key, key_box, b"dek-to-gpu|" + lease["payload"]["model"].encode())
        if dek is None:
            return False
        self.dek, self.lease = dek, lease
        self.key_events.append({"t": self.clock.now(), "event": "key installed", "until": lease["payload"]["expires_at"]})
        return True

    def renew(self, lease: dict) -> bool:
        if not self._lease_ok(lease) or self.dek is None or lease["payload"]["model"] != (self.lease or {}).get("payload", {}).get("model"):
            return False
        self.lease = lease
        return True

    def load_sealed(self, sealed: dict) -> bool:
        """Decrypt the sealed weights into protected memory; needs the key."""
        from .sealing import decrypt_weights
        if self.dek is None or self.power != "ON":
            return False
        plain = decrypt_weights(sealed, self.dek)
        if plain is None:
            return False
        self.weights_plain, self.sealed, self.job = plain, True, sealed["model_digest"]
        self.manifest_digest = sealed["model_digest"]
        return True

    def zeroize(self, why: str) -> None:
        if self.dek is not None or self.weights_plain is not None:
            self.key_events.append({"t": self.clock.now(), "event": "zeroized", "why": why})
        self.dek, self.lease, self.weights_plain = None, None, None

    def run_tokens(self, n: int, cycles_per_token: int = 1000) -> int:
        if not self.running:
            return 0
        if self.sealed:
            # no key or an expired lease: the weights are wiped, nothing runs. The GPU enforces its own lease, so a
            # governor that goes silent (cut off, powered down, halted) stops the model within one lease period
            if self.dek is None or not self.lease or self.clock.now() >= self.lease["payload"]["expires_at"]:
                self.zeroize("lease expired" if self.lease else "no key")
                return 0
        self.tokens += n
        self.cycles += n * cycles_per_token
        return n

    def emit(self, stream: str, data: bytes) -> bytes | None:
        """Token bytes leaving the GPU for the host: they cross the governed pcie port where there is
        one. Integrated tier: also folded into the governor's hash inline."""
        if not self.running or self.output_blocked:
            return None
        switch = self.switches.get("pcie")
        if switch is not None and not switch.pass_traffic("host", "out", len(data), self.clock.now())[0]:
            return None
        self.bytes_out += len(data)
        if self.output_hook:
            self.output_hook(stream, data)
        return data

    def transfer(self, exit_name: str, peer: str, direction: str, nbytes: int, buffer_class: str = "activations") -> tuple[bool, str]:
        """Bytes crossing an exit. Governed by the switch at that exit, if the tier has one. The buffer
        class is what a descriptor names; only a checker (integrated tier) can see it, a switch cannot."""
        from . import reasons
        now = self.clock.now()
        if not self.running and direction == "out":
            return False, "gpu.not_running"
        if exit_name in ("display", "jtag", "debug"):
            if exit_name in self.open_paths:
                return True, reasons.EP_UNCHECKED
            return False, reasons.EP_BRICKED
        if exit_name == "nvswitch" and self.direct_nvlink:
            self.gap_log.append({"exit": exit_name, "peer": peer, "bytes": nbytes, "why": "direct NVLink, no switch"})
            return True, reasons.EP_UNCHECKED
        checker = self.checkers.get(exit_name)
        if checker is not None:
            ok, why = checker.pass_traffic(peer, direction, nbytes, now, buffer_class=buffer_class)
            if not ok:
                return False, why
        switch = self.switches.get(exit_name)
        if switch is None:
            if exit_name in ("copy_engine", "peer_mmu"):
                # internal path: checked by the descriptor checker where there is one (integrated tier);
                # at the rack tier it is governed only by the switch the bytes reach next
                return True, reasons.OK if checker is not None else reasons.EP_UNCHECKED
            self.gap_log.append({"exit": exit_name, "peer": peer, "bytes": nbytes, "why": "no governed switch"})
            return True, reasons.EP_UNCHECKED
        ok, why = switch.pass_traffic(peer, direction, nbytes, now)
        if ok:
            if direction == "out":
                self.bytes_out += nbytes
            else:
                self.bytes_in += nbytes
        return ok, why
