# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The silicon root of trust: measured boot, extend-only registers, DICE key derivation, the
quote engine and the monotonic counter. Requirement REQUIREMENT-MEASURED-BOOT-DERIVES-KEY.

Simplification: the boot ROM and loader are represented by their digests; "booting" a
firmware image is ``boot(loader_digest, firmware_digest)``.
"""
from __future__ import annotations

import random

from . import reasons
from .crypto import SigningKey, sha256, canonical
from .fuses import Fuses


class MeasurementRegister:
    """Can be extended, never written. The silicon version is ``rtl/governor_rtl/measure_reg.py``."""

    def __init__(self):
        self.value = "0" * 64

    def extend(self, digest_hex: str) -> str:
        self.value = sha256(bytes.fromhex(self.value) + bytes.fromhex(digest_hex))
        return self.value


class MonotonicCounter:
    """Never decreases. Persisted through the store so a restart continues upward."""

    def __init__(self, start: int = 0):
        self.value = int(start)

    def tick(self, by: int = 1) -> int:
        if by < 0:
            raise ValueError("monotonic counters do not decrement")
        self.value += by
        return self.value


class SiliconRoot:
    def __init__(self, fuses: Fuses, counter_start: int = 0, rng_seed: int | None = None):
        self.fuses = fuses
        self.meas0 = MeasurementRegister()
        self.meas1 = MeasurementRegister()
        self.counter = MonotonicCounter(counter_start)
        # The TRNG. Silicon draws from a physical noise source; the model draws from the OS unless a
        # seed is given, which makes a test's sample set reproducible without making it predictable to
        # the runtime (the seed never leaves the chip).
        self._rng = random.Random(rng_seed) if rng_seed is not None else random.SystemRandom()
        self.booted = False
        self.loader_digest = ""
        self.firmware_digest = ""
        self.firmware_version = 0
        self._key: SigningKey | None = None
        self.device_key: SigningKey | None = None

    def boot(self, loader_digest: str, firmware_digest: str, firmware_version: int) -> SigningKey:
        """Measure, check rollback, derive the DICE identity. Returns the signing key."""
        if firmware_version < self.fuses.rollback:
            raise ValueError(reasons.POLICY_ROLLBACK)
        self.fuses.bump_rollback(firmware_version)
        self.meas0 = MeasurementRegister()
        self.meas1 = MeasurementRegister()
        self.meas0.extend(loader_digest)
        self.meas1.extend(firmware_digest)
        cdi0 = self.fuses.derive(b"cdi0:" + bytes.fromhex(self.meas0.value))
        cdi1 = self.fuses.derive(b"cdi1:" + cdi0 + bytes.fromhex(self.meas1.value))
        # DICE: the DeviceID key is derived from CDI_0 (the secret and the first mutable code, the
        # loader); the alias key from CDI_1 (plus the firmware). A loader change changes the device
        # identity; a firmware change changes only the alias key.
        self.device_key = SigningKey.from_seed(self.fuses.derive(b"deviceid:" + cdi0))
        self._key = SigningKey.from_seed(self.fuses.derive(b"sign:" + cdi1))
        self.loader_digest, self.firmware_digest, self.firmware_version = loader_digest, firmware_digest, firmware_version
        self.booted = True
        return self._key

    @property
    def key(self) -> SigningKey:
        if not self.booted or self._key is None:
            raise RuntimeError("root not booted")
        return self._key

    def derive(self, label: bytes) -> bytes:
        """A key under CDI_1 for NVM, capability MACs, wrapping."""
        return self.fuses.derive(b"cdi1-derived:" + bytes.fromhex(self.meas1.value) + b":" + label)

    def random_fraction(self) -> float:
        """One draw from the chip's TRNG in [0, 1): what audit sampling uses."""
        return self._rng.random()

    def quote(self, nonce: str, extra: dict | None = None) -> dict:
        """Signed evidence of what booted, over a nonce."""
        payload = {
            "type": "quote",
            "chip_id": self.fuses.chip_id,
            "meas0": self.meas0.value,
            "meas1": self.meas1.value,
            "firmware_version": self.firmware_version,
            "lifecycle": self.fuses.lifecycle,
            "counter": self.counter.value,
            "nonce": nonce,
        }
        if extra:
            payload.update(extra)
        return self.key.sign(payload)

    def zeroize(self) -> None:
        self.fuses.zeroize()
        self._key = None
        self.device_key = None
        self.booted = False
