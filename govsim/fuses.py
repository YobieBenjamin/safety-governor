"""One-time-programmable fuses and the lifecycle state.

Requirements R1, R3, R4. The unique device secret is readable only through ``derive``; there
is no accessor that returns it. The anti-rollback counter and the lifecycle state are
monotone. Debug access is refused in PRODUCTION and the attempt is reported to the caller so
the governor can log it.
"""
from __future__ import annotations

import secrets

from . import reasons
from .crypto import hkdf, sha256

TEST, PROVISIONED, PRODUCTION, DECOMMISSIONED = 0, 1, 2, 3
LIFECYCLE_NAMES = {TEST: "TEST", PROVISIONED: "PROVISIONED", PRODUCTION: "PRODUCTION", DECOMMISSIONED: "DECOMMISSIONED"}


class Fuses:
    def __init__(self, chip_id: str | None = None, governance_key_hashes: list[str] | None = None, uds: bytes | None = None):
        self.chip_id = chip_id or secrets.token_hex(8)
        self._uds = uds or secrets.token_bytes(32)
        self.rollback = 0                      # firmware version; thermometer-coded in silicon
        self.policy_version = 0                # policy image version; a second thermometer
        self.lifecycle = TEST
        self.governance_key_hashes = list(governance_key_hashes or [])
        self.zeroized = False

    # --- secret -------------------------------------------------------------
    def derive(self, info: bytes, length: int = 32) -> bytes:
        """The only way out of the fuse block: a derived key, never the secret itself."""
        if self.zeroized:
            raise RuntimeError(reasons.TAMPER_ZEROIZED)
        return hkdf(self._uds, info, length)

    @property
    def uds_fingerprint(self) -> str:
        """A public, non-reversible identifier of the secret, for the chip certificate."""
        return sha256(hkdf(self._uds, b"fingerprint"))

    # --- monotone state -----------------------------------------------------
    def bump_rollback(self, to: int) -> None:
        if to < self.rollback:
            raise ValueError(reasons.POLICY_ROLLBACK)
        self.rollback = to

    def bump_policy(self, to: int) -> None:
        if to < self.policy_version:
            raise ValueError(reasons.POLICY_ROLLBACK)
        self.policy_version = to

    def advance_lifecycle(self, to: int) -> None:
        if to < self.lifecycle:
            raise ValueError(reasons.LIFECYCLE_BACKWARDS)
        self.lifecycle = to

    def debug_access(self) -> tuple[bool, str]:
        """JTAG / scan request. Granted only before PRODUCTION."""
        if self.lifecycle >= PRODUCTION:
            return False, reasons.DEBUG_REFUSED
        return True, reasons.OK

    def zeroize(self) -> None:
        """Tamper response: the secret is gone and so is every key derived from it."""
        self._uds = b"\x00" * 32
        self.zeroized = True
