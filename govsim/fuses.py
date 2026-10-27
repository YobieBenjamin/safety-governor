# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""One-time-programmable fuses and the lifecycle state.

Requirements REQUIREMENT-DEVICE-SECRET-IN-FUSES, REQUIREMENT-FUSED-ANTI-ROLLBACK, REQUIREMENT-DEBUG-FUSED-OFF. The unique device secret is readable only through ``derive``; there
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


POLICY_FUSE_BITS = 256          # one-time bits in the policy anti-rollback thermometer (docs/04 section 10)
POLICY_FUSE_STRIDE = 64         # edition versions per burned bit; the NVM counter covers versions within a stride


class Fuses:
    def __init__(self, chip_id: str | None = None, governance_key_hashes: list[str] | None = None, uds: bytes | None = None,
                 governance_threshold: int | None = None, governance_class_floor: int = 0,
                 rule_floor: list[dict] | None = None, loosen_delay_s: float = 0.0,
                 recovery_key_hashes: list[str] | None = None, recovery_threshold: int | None = None,
                 jurisdiction_roots: dict[str, dict] | None = None):
        self.chip_id = chip_id or secrets.token_hex(8)
        self._kdf = _kdf_engine(uds or secrets.token_bytes(32))   # no attribute holds the secret
        self.rollback = 0                      # firmware version; thermometer-coded in silicon
        self.policy_version = 0                # policy anti-rollback fuse bits burned (thermometer, at most POLICY_FUSE_BITS)
        self.nvm_policy_version = 0            # the exact edition version, in a monotonic NVM counter beside the fuses
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
        # Audit 2026-10-26 (capture): the least number of distinct principal classes (organisations or roles) that every
        # edition must enrol among its governance keys and require in its class quorum. Fused at manufacture; no edition
        # can lower it, so one validly signed edition cannot hand governance to a single party for good.
        self.governance_class_floor = int(governance_class_floor)
        # Adversarial audit 3 (capture by a validly signed edition, and permanent capture by a stolen quorum).
        # rule_floor: rules no edition may remove or weaken, fused at manufacture (govsim/policy.py floor_violations).
        # loosen_delay_s: an edition that loosens the rules in force takes effect only after this delay from its issue
        #   time, so it is public before it acts and can be answered (0 in the model racks; set in production fuses).
        # recovery_key_hashes / recovery_threshold: a separate, higher quorum, fused, that can always sign an edition
        #   over whatever governance is in force, so a stolen governance quorum cannot keep a chip.
        # jurisdiction_roots: further rulebook authorities, each with its own key hashes and threshold; an action a
        #   jurisdiction governs must be allowed by that jurisdiction's edition too (one cannot weaken another's).
        self.rule_floor = [dict(x) for x in (rule_floor or [])]
        self.loosen_delay_s = float(loosen_delay_s)
        self.recovery_key_hashes = list(recovery_key_hashes or [])
        self.recovery_threshold = int(recovery_threshold) if recovery_threshold is not None else len(self.recovery_key_hashes)
        self.jurisdiction_roots = {k: dict(v) for k, v in (jurisdiction_roots or {}).items()}
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

    def bump_policy(self, to: int) -> bool:
        """Advance the policy anti-rollback state to version ``to``. Returns False, changing nothing, when ``to`` is
        older than what is recorded or when the fused thermometer cannot hold it.

        Adversarial audit 3: the specification fuses 256 one-time bits as a thermometer, but the model counted
        without limit, so one edition with a huge version, or five years of weekly editions, would end rollback
        protection or freeze the chip. Now: the exact version lives in a monotonic NVM counter (``nvm_policy_version``,
        modelled here beside the fuses), and the fuses record only ``version // POLICY_FUSE_STRIDE`` as burned bits
        (``policy_version``), so a rollback below the fused floor is impossible even if the NVM counter is attacked.
        With the per-edition version step bounded (governor MAX_EDITION_STEP), 256 bits of stride 64 cover 16,384
        editions: over 300 years of weekly editions."""
        if to < self.nvm_policy_version:
            raise ValueError(reasons.POLICY_ROLLBACK)
        bits = to // POLICY_FUSE_STRIDE
        if bits > POLICY_FUSE_BITS:
            return False
        self.nvm_policy_version = to
        self.policy_version = max(self.policy_version, bits)
        return True

    @property
    def policy_floor_version(self) -> int:
        """The lowest edition version the burned fuses still allow."""
        return self.policy_version * POLICY_FUSE_STRIDE

    def record_governance(self, keys: list[str], threshold: int, image_epoch: str,
                          classes: dict[str, str] | None = None, class_quorum: int = 0) -> None:
        """The chip's protected record of the governance configuration now in force: the keys whose
        signatures count, the k they must reach, the edition that set them, and (F26) the optional
        across-class quorum, with each key's enrolled principal class. The next rulebook is authorized by
        THIS record, not by anything it carries itself, so the configuration in force authorizes its own
        replacement, keys, threshold and class rule included. The threshold can never be set below the floor
        fused at manufacture."""
        if threshold < max(1, self.governance_threshold):
            raise ValueError(reasons.POLICY_QUORUM)
        self.trusted_governance = {"keys": list(dict.fromkeys(keys)), "threshold": int(threshold),
                                   "image_epoch": image_epoch,
                                   "governance_classes": dict(classes or {}),
                                   "governance_class_quorum": int(class_quorum)}

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
