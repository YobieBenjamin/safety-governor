"""The origin gate's cryptography: weights sealed to governed hardware (docs/18 question 20, issue W1).

A publisher encrypts the weights once, chunk by chunk, with a random data key (AES-256-GCM, each chunk bound
to the model digest and its index, so chunks cannot be swapped or reordered). The data key is sealed to the
governor's key-encryption key: X25519 to the governor's public half, HKDF, AES-GCM. Only the governor can
open it. The governor never hands the data key out in the clear: it re-seals it to the X25519 key of one GPU
whose confidential-computing report it has verified, and only while the signed rulebook lists the model.

These are the primitives, not the protocol; the protocol (KEY_RELEASE, KEY_RENEW, revocation) is in
``govsim/governor.py`` and the GPU's half in ``govsim/gpu.py``.
"""
from __future__ import annotations

import os

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from .crypto import hkdf, sha256

CHUNK = 1 << 20          # 1 MiB chunks: a GPU decrypts while it streams the weights in


def x25519_private(seed32: bytes) -> X25519PrivateKey:
    return X25519PrivateKey.from_private_bytes(seed32[:32])


def public_hex(priv: X25519PrivateKey) -> str:
    return priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def seal_to(pub_hex: str, plaintext: bytes, info: bytes) -> dict:
    """Seal ``plaintext`` so only the holder of the X25519 key behind ``pub_hex`` can open it (an HPKE-shaped box)."""
    eph = X25519PrivateKey.generate()
    eph_pub = eph.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    recipient = bytes.fromhex(pub_hex)
    shared = eph.exchange(X25519PublicKey.from_public_bytes(recipient))
    key = hkdf(shared, b"govsim-seal|" + info + eph_pub + recipient)
    nonce = os.urandom(12)
    return {"eph": eph_pub.hex(), "nonce": nonce.hex(), "ct": AESGCM(key).encrypt(nonce, plaintext, info).hex(), "to": pub_hex}


def open_sealed(priv: X25519PrivateKey, box: dict, info: bytes) -> bytes | None:
    """Open a box, or None if it was not sealed to this key, was altered, or names different context ``info``."""
    try:
        eph_pub = bytes.fromhex(box["eph"])
        recipient = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        shared = priv.exchange(X25519PublicKey.from_public_bytes(eph_pub))
        key = hkdf(shared, b"govsim-seal|" + info + eph_pub + recipient)
        return AESGCM(key).decrypt(bytes.fromhex(box["nonce"]), bytes.fromhex(box["ct"]), info)
    except Exception:            # wrong key, tampered box, malformed fields: all the same answer, no key
        return None


def _aad(model_digest: str, index: int) -> bytes:
    return model_digest.encode() + b"|" + index.to_bytes(8, "big")


def seal_weights(weights: bytes, model_digest: str, governor_kek_pub: str, chunk: int = CHUNK) -> dict:
    """The publisher's side: encrypt the weights under a fresh data key, seal that key to the governor."""
    dek = AESGCM.generate_key(bit_length=256)
    aes = AESGCM(dek)
    chunks = []
    for i in range(0, max(len(weights), 1), chunk):
        nonce = i.to_bytes(12, "big")                        # unique per chunk under a key used for one model only
        chunks.append(aes.encrypt(nonce, weights[i:i + chunk], _aad(model_digest, i // chunk)))
    return {"model_digest": model_digest, "chunk": chunk, "n": len(chunks), "chunks": chunks,
            "plain_sha256": sha256(weights), "wrapped_dek": seal_to(governor_kek_pub, dek, b"dek|" + model_digest.encode())}


def decrypt_weights(sealed: dict, dek: bytes) -> bytes | None:
    """The GPU's side: decrypt every chunk in order; None if any chunk was altered, swapped or reordered."""
    aes = AESGCM(dek)
    out = bytearray()
    try:
        for idx, ct in enumerate(sealed["chunks"]):
            out += aes.decrypt((idx * sealed["chunk"]).to_bytes(12, "big"), ct, _aad(sealed["model_digest"], idx))
    except Exception:
        return None
    return bytes(out) if sha256(bytes(out)) == sealed["plain_sha256"] else None
