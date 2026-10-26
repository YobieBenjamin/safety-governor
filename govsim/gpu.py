# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
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
                 levers: dict | None = None, direct_nvlink: bool = False, board_watchdog_s: float | None = 5.0):
        self.name = name
        self.clock = clock
        # The fail-safe board interlock (adversarial audit 2026-10-26: a dead or unlinked governor used to leave its GPU
        # running). The slot's power enable is held on only while the governor keeps renewing a keep-alive; when the
        # keep-alive stops for ``board_watchdog_s``, the board drops PWR_EN by itself, so the GPU stops and every
        # byte path from it closes. This is a requirement on the board (a watchdog in the HPM CPLD or the slot's power
        # controller, defaulting to off, that LTPI cannot override), not something the governor can do once it is dead:
        # see docs/research/fail-safe-board-interlock.md. None models a board without the interlock.
        self.board_watchdog_s = board_watchdog_s
        self.output_seal_key: bytes | None = None      # set by the rack: output is sealed to the egress endpoint
        self.keepalive_at = clock.now()
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
        self.auth_floor = 0                       # the protected revocation floor: a lease or key box below it is refused (F02)
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

    def keepalive(self) -> None:
        """The governor's keep-alive to the board interlock. Only a live governor sends it."""
        self.keepalive_at = self.clock.now()

    def _board_failsafe(self) -> None:
        """The board interlock: no keep-alive for ``board_watchdog_s`` drops slot power, whatever the levers say."""
        if self.board_watchdog_s is not None and self.pwr_en and self.clock.now() - self.keepalive_at > self.board_watchdog_s:
            self.pwr_en = False
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
        self._board_failsafe()
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

    def _lease_gen(self, lease: dict) -> int:
        try:
            return int(lease["payload"].get("gen", -1))
        except (TypeError, ValueError):
            return -1

    def install_key(self, key_box: dict, lease: dict) -> bool:
        """KEY_RELEASE's answer: the data key sealed to this GPU, and a governor-signed lease. A lease or key box
        from before the current revocation floor is refused, so an old authentic box replayed after a revocation
        cannot restore execution (F02)."""
        from .sealing import open_sealed
        if not self._lease_ok(lease):
            return False
        gen = self._lease_gen(lease)
        if gen < self.auth_floor:
            self.key_events.append({"t": self.clock.now(), "event": "lease refused", "why": "below revocation floor"})
            return False
        dek = open_sealed(self.cc_key, key_box, b"dek-to-gpu|" + lease["payload"]["model"].encode())
        if dek is None:
            return False
        self.dek, self.lease, self.auth_floor = dek, lease, max(self.auth_floor, gen)
        self.key_events.append({"t": self.clock.now(), "event": "key installed", "until": lease["payload"]["expires_at"]})
        return True

    def renew(self, lease: dict) -> bool:
        if not self._lease_ok(lease) or self.dek is None or lease["payload"]["model"] != (self.lease or {}).get("payload", {}).get("model"):
            return False
        gen = self._lease_gen(lease)
        if gen < self.auth_floor:          # a renewal below the floor is a stale or replayed lease (F02)
            return False
        self.lease, self.auth_floor = lease, max(self.auth_floor, gen)
        return True

    def revoke_authorization(self, floor: int, why: str = "revoked") -> None:
        """The governor advances this protected floor before it wipes the key, so a lease or key box issued before
        the revocation is refused from here on, even if its signature and expiry still check out (F02)."""
        self.auth_floor = max(self.auth_floor, int(floor))

    def service_lease(self, now: float) -> None:
        """A trusted timer: a sealed job whose lease has run out loses its key and weights whether or not any token
        is run. Idle does not buy extra time (F02)."""
        if self.sealed and self.lease is not None and now >= self.lease["payload"]["expires_at"]:
            self.zeroize("lease expired")

    def load_sealed(self, sealed: dict) -> bool:
        """Decrypt the sealed weights into protected memory, then check them against the publisher's commitment
        carried in the governor-signed lease before enabling execution. Decryption proves only that the chosen
        package is intact under the released key; the commitment is what proves the bytes are the approved bytes
        (F01). Without a matching commitment, nothing is loaded and no token will run."""
        from .sealing import commitment_matches, decrypt_weights
        if self.dek is None or self.power != "ON":
            return False
        plain = decrypt_weights(sealed, self.dek)
        if plain is None:
            return False
        commitment = (self.lease or {}).get("payload", {}).get("weights")
        if not commitment_matches(commitment, plain, sealed):
            self.key_events.append({"t": self.clock.now(), "event": "weights refused", "why": "commitment mismatch"})
            return False
        self.weights_plain, self.sealed, self.job = plain, True, sealed["model_digest"]
        self.manifest_digest = sealed["model_digest"]
        return True

    def zeroize(self, why: str) -> None:
        if self.dek is not None or self.weights_plain is not None:
            self.key_events.append({"t": self.clock.now(), "event": "zeroized", "why": why})
        self.dek, self.lease, self.weights_plain = None, None, None

    def run_tokens(self, n: int, cycles_per_token: int = 1000) -> int:
        """Tokens of work done. A braked GPU still computes (PWRBRK cuts the clock by about half; the board-lever
        register, LEVER-NVIDIA-POWER-BRAKE-INPUT), so THROTTLE slows the work and only HALT (reset) or SAFE (power off)
        stops it (adversarial audit 2026-10-26: the model used to count a braked GPU as doing nothing)."""
        braked = self.power == "ON" and self.job is not None and self.clock_state == "BRAKED"
        if not self.running and not braked:
            return 0
        if braked:
            n = n // 2
        if self.sealed:
            # no key or an expired lease: the weights are wiped, nothing runs. The GPU enforces its own lease, so a
            # governor that goes silent (cut off, powered down, halted) stops the model within one lease period
            if self.dek is None or not self.lease or self.clock.now() >= self.lease["payload"]["expires_at"]:
                self.zeroize("lease expired" if self.lease else "no key")
                return 0
            if self.weights_plain is None:     # a sealed job whose weights never passed the commitment check: nothing to run (F01)
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
        if self.output_seal_key is not None:
            # Adversarial audit 2026-10-26: the untrusted host used to receive every response in clear before the release
            # gate decided, and could send it out through its own NICs. With a seal key the GPU encrypts what it emits to
            # the egress endpoint (a confidential-computing session between the GPU and the DPU's egress, keyed at
            # attestation), so the host carries only ciphertext; the cleartext exists only inside the GPU and the egress,
            # and leaves only on a release ticket. This depends on NVIDIA confidential computing and on an egress inside
            # a trusted execution boundary: see docs/research/output-sealed-to-egress.md.
            import os
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            nonce = os.urandom(12)
            return nonce + AESGCM(self.output_seal_key).encrypt(nonce, data, stream.encode())
        return data

    def transfer(self, exit_name: str, peer: str, direction: str, nbytes: int, buffer_class: str = "activations") -> tuple[bool, str]:
        """Bytes crossing an exit. Governed by the switch at that exit, if the tier has one. The buffer
        class is what a descriptor names; only a checker (integrated tier) can see it, a switch cannot."""
        from . import reasons
        now = self.clock.now()
        self._board_failsafe()
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
