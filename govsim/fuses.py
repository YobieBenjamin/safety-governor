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


def _kdf_engine(uds: bytes):
    """The key-derivation engine: the only thing that ever sees the secret, held in its closure."""
    def derive(info: bytes, length: int) -> bytes:
        return hkdf(uds, info, length)
    return derive


class Fuses:
    def __init__(self, chip_id: str | None = None, governance_key_hashes: list[str] | None = None, uds: bytes | None = None,
                 governance_threshold: int | None = None):
        self.chip_id = chip_id or secrets.token_hex(8)
        self._kdf = _kdf_engine(uds or secrets.token_bytes(32))   # no attribute holds the secret
        self.rollback = 0                      # firmware version; thermometer-coded in silicon
        self.policy_version = 0                # policy image version; a second thermometer
        self.lifecycle = TEST
        self.governance_key_hashes = list(governance_key_hashes or [])
        # the k of k-of-n, fused at provisioning beside the key hashes. A policy image may raise it and
        # never lower it: the threshold an image carries is the image's own claim, and an image cannot
        # be allowed to decide how many signatures it needs (that was the defect found on 22 October:
        # threshold 0 and no signatures passed). Unset, it is a majority of the fused keys, at least one.
        n = len(set(self.governance_key_hashes))
        self.governance_threshold = int(governance_threshold) if governance_threshold is not None else max(1, n // 2 + 1)
        if self.governance_threshold < 1:
            raise ValueError(reasons.POLICY_QUORUM)
        self.trusted_governance: dict | None = None   # set by the first rulebook the fused key hashes admit; see record_governance
        self.zeroized = False

    # --- secret -------------------------------------------------------------
    def derive(self, info: bytes, length: int = 32) -> bytes:
        """The only way out of the fuse block: a derived key, never the secret itself."""
        if self.zeroized:
            raise RuntimeError(reasons.TAMPER_ZEROIZED)
        return self._kdf(info, length)

    @property
    def uds_fingerprint(self) -> str:
        """A public, non-reversible identifier of the secret, for the chip certificate."""
        return sha256(self.derive(b"fingerprint"))

    # --- monotone state -----------------------------------------------------
    def bump_rollback(self, to: int) -> None:
        if to < self.rollback:
            raise ValueError(reasons.POLICY_ROLLBACK)
        self.rollback = to

    def bump_policy(self, to: int) -> None:
        if to < self.policy_version:
            raise ValueError(reasons.POLICY_ROLLBACK)
        self.policy_version = to

    def record_governance(self, keys: list[str], threshold: int, image_epoch: str) -> None:
        """The chip's protected record of the governance configuration now in force: the keys whose
        signatures count, the k they must reach, and the edition that set them. The next rulebook is
        authorized by THIS record, not by anything it carries itself, so the configuration in force
        authorizes its own replacement, keys and threshold included. The threshold can never be set
        below the floor fused at manufacture."""
        if threshold < max(1, self.governance_threshold):
            raise ValueError(reasons.POLICY_QUORUM)
        self.trusted_governance = {"keys": list(dict.fromkeys(keys)), "threshold": int(threshold), "image_epoch": image_epoch}

    def bump_governance_threshold(self, to: int) -> None:
        """The manufacture floor. Thermometer-coded like the version counters: it only goes up, and only at
        provisioning; a rulebook never moves it (the current configuration's own k is in trusted_governance)."""
        if to < self.governance_threshold:
            raise ValueError(reasons.POLICY_QUORUM)
        self.governance_threshold = to

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
        self._kdf = _kdf_engine(b"\x00" * 32)
        self.zeroized = True
