# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Hashing, signing and key derivation for the model.

What it provides: one fixed encoding of data (``canonical``, sorted JSON), SHA-256 hashes, keyed hashes
(HMAC), Ed25519 signatures, HKDF key derivation, and one envelope format that every party uses.

Ed25519 everywhere, the same choice as the reference stack. Production silicon uses ECDSA
P-384 (the curve the NVIDIA GPU attestation chain and AMD SEV-SNP use) and P-256 for
TPM-class endpoints; the curve changes nothing about the architecture.

A *signed object* is one envelope format used by every party::

    {"payload": {...}, "signer": <key id>, "sig": <hex>}

The signature is over ``canonical(payload)``. Verification always takes the public key the
caller expects; the envelope never carries a key the verifier would trust on its own.

What it guarantees: a verifier checks a signature only against the key it expects, and the
envelope cannot supply that key. A non-finite number (NaN or infinity) cannot be encoded, so it
cannot be signed or hashed (F03, tests/test_f03_nan_budget.py).

What it deliberately does NOT do: it does not store keys. Keys live in memory in this model.
It is not a hardware security module, and Ed25519 is not the production curve (see above).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import secrets
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class SignatureError(Exception):
    """An envelope failed verification."""


def canonical(obj: Any) -> bytes:
    """The one fixed byte encoding of a value: JSON with sorted keys, no spaces, and non-ASCII kept as is.
    Signatures, ``digest`` and the MACs over capabilities are all taken over these bytes, so two equal values
    always encode the same way. Raises ValueError for NaN or infinity."""
    # allow_nan=False: NaN and +/-Infinity are not valid JSON and must never be signed or hashed.
    # A payload carrying a non-finite number raises here, so it cannot be turned into a signed
    # object; the governor re-canonicalizes on verification, so such a request fails to verify (F03).
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def finite_number(v: Any) -> bool:
    """True only for a real, finite int or float. Rejects bool (a bool is an int in Python), NaN and
    the infinities, which otherwise slip past ordinary ``<`` / ``>`` budget and constraint checks (F03)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def sha256(data: bytes) -> str:
    """SHA-256 of ``data``, as hex."""
    return hashlib.sha256(data).hexdigest()


def digest(obj: Any) -> str:
    """SHA-256 of the canonical encoding, as hex."""
    return sha256(canonical(obj))


def hkdf(ikm: bytes, info: bytes, length: int = 32, salt: bytes = b"") -> bytes:
    """HKDF-SHA256: the key-derivation engine fed by the fused secret."""
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def hmac_sha256(key: bytes, data: bytes) -> str:
    """HMAC-SHA256 of ``data`` under ``key``, as hex. A keyed hash: only a holder of the key can make or check
    the value, so it proves who made it."""
    return hmac.new(key, data, "sha256").hexdigest()


def random_id(nbytes: int = 16) -> str:
    """A random hex string made of ``nbytes`` random bytes (twice as many hex characters). Used for ids and nonces,
    and drawn from the operating system's secure random source."""
    return secrets.token_hex(nbytes)


class VerifyKey:
    """An Ed25519 public key (32 bytes). It checks signatures and cannot make them."""

    def __init__(self, raw: bytes):
        """Wrap 32 raw bytes as a public key. Raises ValueError when the length is not 32."""
        if len(raw) != 32:
            raise ValueError("Ed25519 public keys are 32 bytes")
        self.raw = raw
        self._key = Ed25519PublicKey.from_public_bytes(raw)

    @classmethod
    def from_hex(cls, text: str) -> "VerifyKey":
        """Read a public key from its hex text."""
        return cls(bytes.fromhex(text))

    @property
    def hex(self) -> str:
        """The key as hex text."""
        return self.raw.hex()

    @property
    def key_id(self) -> str:
        """A short id for the key: the first 16 hex characters of the SHA-256 of the raw key. An envelope names
        its signer by this id, and the verifier looks up the key by it."""
        return sha256(self.raw)[:16]

    def verify(self, sig: bytes, data: bytes) -> bool:
        """True when ``sig`` is a valid signature of ``data`` by this key. A signature that does not match returns False."""
        try:
            self._key.verify(sig, data)
            return True
        except InvalidSignature:
            return False

    def __eq__(self, other: object) -> bool:
        """Two verify keys are equal when their raw bytes are equal."""
        return isinstance(other, VerifyKey) and other.raw == self.raw

    def __hash__(self) -> int:
        """Hash on the raw bytes, so a key can be used in a set or as a dict key."""
        return hash(self.raw)


class SigningKey:
    """An Ed25519 private key and its public half. Only its owner should hold it: anyone with the key can sign
    as that owner."""

    def __init__(self, private: Ed25519PrivateKey):
        """Wrap a private key and derive its public half, kept in ``public``."""
        self._key = private
        self.public = VerifyKey(private.public_key().public_bytes_raw())

    @classmethod
    def generate(cls) -> "SigningKey":
        """A new random signing key."""
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_seed(cls, seed: bytes) -> "SigningKey":
        """A signing key from a seed. The same seed always gives the same key. Only the first 32 bytes are used."""
        return cls(Ed25519PrivateKey.from_private_bytes(seed[:32]))

    @property
    def key_id(self) -> str:
        """The key id of this key's public half."""
        return self.public.key_id

    def sign_bytes(self, data: bytes) -> bytes:
        """Sign raw bytes. Returns the 64-byte signature."""
        return self._key.sign(data)

    def sign(self, payload: Mapping[str, Any]) -> dict:
        """Sign a payload and return the envelope: a copy of the payload, the signer's key id, and the hex signature
        over the canonical encoding of the payload."""
        payload = dict(payload)
        return {"payload": payload, "signer": self.key_id, "sig": self.sign_bytes(canonical(payload)).hex()}


def verify_object(obj: Mapping[str, Any], expected: VerifyKey) -> bool:
    """True iff ``obj`` is a well-formed envelope signed by ``expected``."""
    try:
        if obj["signer"] != expected.key_id:
            return False
        return expected.verify(bytes.fromhex(obj["sig"]), canonical(obj["payload"]))
    except (KeyError, TypeError, ValueError):
        return False


def verify_any(obj: Mapping[str, Any], keys: Mapping[str, VerifyKey]) -> VerifyKey | None:
    """Return the key from ``keys`` (by key id) that signed ``obj``, or None."""
    try:
        key = keys.get(obj["signer"])
    except (KeyError, TypeError):
        return None
    if key is None:
        return None
    return key if verify_object(obj, key) else None
