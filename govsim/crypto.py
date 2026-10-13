"""Hashing, signing and key derivation for the model.

Ed25519 everywhere, the same choice as the reference stack. Production silicon uses ECDSA
P-384 (the curve the NVIDIA GPU attestation chain and AMD SEV-SNP use) and P-256 for
TPM-class endpoints; the curve changes nothing about the architecture.

A *signed object* is one envelope format used by every party::

    {"payload": {...}, "signer": <key id>, "sig": <hex>}

The signature is over ``canonical(payload)``. Verification always takes the public key the
caller expects; the envelope never carries a key the verifier would trust on its own.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class SignatureError(Exception):
    """An envelope failed verification."""


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(obj: Any) -> str:
    """SHA-256 of the canonical encoding, as hex."""
    return sha256(canonical(obj))


def hkdf(ikm: bytes, info: bytes, length: int = 32, salt: bytes = b"") -> bytes:
    """HKDF-SHA256: the key-derivation engine fed by the fused secret."""
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def hmac_sha256(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, "sha256").hexdigest()


def random_id(nbytes: int = 16) -> str:
    return secrets.token_hex(nbytes)


class VerifyKey:
    def __init__(self, raw: bytes):
        if len(raw) != 32:
            raise ValueError("Ed25519 public keys are 32 bytes")
        self.raw = raw
        self._key = Ed25519PublicKey.from_public_bytes(raw)

    @classmethod
    def from_hex(cls, text: str) -> "VerifyKey":
        return cls(bytes.fromhex(text))

    @property
    def hex(self) -> str:
        return self.raw.hex()

    @property
    def key_id(self) -> str:
        return sha256(self.raw)[:16]

    def verify(self, sig: bytes, data: bytes) -> bool:
        try:
            self._key.verify(sig, data)
            return True
        except InvalidSignature:
            return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, VerifyKey) and other.raw == self.raw

    def __hash__(self) -> int:
        return hash(self.raw)


class SigningKey:
    def __init__(self, private: Ed25519PrivateKey):
        self._key = private
        self.public = VerifyKey(private.public_key().public_bytes_raw())

    @classmethod
    def generate(cls) -> "SigningKey":
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_seed(cls, seed: bytes) -> "SigningKey":
        return cls(Ed25519PrivateKey.from_private_bytes(seed[:32]))

    @property
    def key_id(self) -> str:
        return self.public.key_id

    def sign_bytes(self, data: bytes) -> bytes:
        return self._key.sign(data)

    def sign(self, payload: Mapping[str, Any]) -> dict:
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
