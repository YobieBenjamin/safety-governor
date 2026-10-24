# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The origin gate's cryptography: weights sealed to governed hardware (docs/18 question 20, issue W1).

The problem: a model's weights should run only on a GPU the governor has verified, and only while the
signed rulebook still lists the model.

How it works: the publisher encrypts the weights once, chunk by chunk, with a random data key
(AES-256-GCM). Each chunk is bound to the model digest and its index, so chunks cannot be swapped or
reordered. The data key is sealed to the governor's key-encryption key (X25519 to the governor's public
half, HKDF, AES-GCM), so only the governor can open it. The governor never hands the data key out in the
clear. It re-seals the key to the X25519 key of one GPU whose confidential-computing report it has
verified, and only while the rulebook lists the model.

What it guarantees: a package that decrypts correctly under the key is intact. The decrypted bytes must
also match the publisher's signed commitment (hash, length, chunk layout, format and config). A label
alone cannot attach a model name to different weights (F01).

What it deliberately does NOT do: AES-GCM does not prove the bytes were approved. That is the job of the
commitment, which the manifest signs. This file holds only the primitives. The protocol (KEY_RELEASE,
KEY_RENEW, revocation) is in ``govsim/governor.py``, and the GPU's half is in ``govsim/gpu.py``.
"""
from __future__ import annotations

import os

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from .crypto import digest, hkdf, sha256

CHUNK = 1 << 20          # 1 MiB chunks: a GPU decrypts while it streams the weights in


def x25519_private(seed32: bytes) -> X25519PrivateKey:
    """Make an X25519 private key from 32 seed bytes. Only the first 32 bytes are used."""
    return X25519PrivateKey.from_private_bytes(seed32[:32])


def public_hex(priv: X25519PrivateKey) -> str:
    """The public half of an X25519 key, as hex."""
    return priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def seal_to(pub_hex: str, plaintext: bytes, info: bytes) -> dict:
    """Seal ``plaintext`` so only the holder of the X25519 key behind ``pub_hex`` can open it (an HPKE-shaped box)."""
    eph = X25519PrivateKey.generate()
    eph_pub = eph.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    recipient = bytes.fromhex(pub_hex)
    shared = eph.exchange(X25519PublicKey.from_public_bytes(recipient))
    # the context and both public keys go into the derived key, so a box cannot be reused under another context or recipient
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
    """Associated data for one chunk: the model digest and the chunk index. The data is checked along with the
    ciphertext but not encrypted, so a chunk moved to another model or another position fails to decrypt."""
    return model_digest.encode() + b"|" + index.to_bytes(8, "big")


def weights_commitment(weights: bytes, *, chunk: int = CHUNK, fmt: str = "raw", config: dict | None = None) -> dict:
    """The publisher's binding commitment to the EXACT weight bytes and the way they are packaged: the plaintext
    hash, the total length, the chunk size and chunk count, the format, and the execution-relevant config. A label
    is not a measurement; this is. The publisher-signed manifest commits to this, the governor copies it into the
    key lease, and the GPU checks the decrypted content against it before it will run a single token (F01)."""
    data_len = len(weights)
    n = len(range(0, max(data_len, 1), chunk))
    return {"sha256": sha256(weights), "length": data_len, "chunk": int(chunk), "n": n,
            "format": str(fmt), "config": config or {}}


def commitment_matches(commitment: dict | None, plaintext: bytes, sealed: dict) -> bool:
    """True only if the decrypted ``plaintext`` and the package structure reproduce the authenticated
    ``commitment`` exactly: the bytes (hash and length), the chunk size and count, the format and the config.
    Byte substitution, truncation, chunk duplication, a format swap or a config swap each change at least one
    field, so each one is refused. A missing or malformed commitment is refused (fail closed)."""
    if not isinstance(commitment, dict):
        return False
    if int(sealed.get("n", -1)) != commitment.get("n") or len(sealed.get("chunks", [])) != commitment.get("n"):
        return False
    observed = weights_commitment(plaintext, chunk=int(sealed.get("chunk", CHUNK)),
                                  fmt=str(sealed.get("format", "raw")), config=sealed.get("config"))
    return digest(observed) == digest(commitment)


def seal_weights(weights: bytes, model_digest: str, governor_kek_pub: str, chunk: int = CHUNK, *,
                 fmt: str = "raw", config: dict | None = None) -> dict:
    """The publisher's side: encrypt the weights under a fresh data key, seal that key to the governor, and record
    the binding commitment the manifest will sign. AES-GCM proves the chosen package is intact under the chosen
    key; it does not prove the bytes were approved. The commitment is what ties the package to an approved model."""
    dek = AESGCM.generate_key(bit_length=256)
    aes = AESGCM(dek)
    chunks = []
    for i in range(0, max(len(weights), 1), chunk):
        nonce = i.to_bytes(12, "big")                        # unique per chunk under a key used for one model only
        chunks.append(aes.encrypt(nonce, weights[i:i + chunk], _aad(model_digest, i // chunk)))
    return {"model_digest": model_digest, "chunk": chunk, "n": len(chunks), "chunks": chunks,
            "format": str(fmt), "config": config or {},
            "weights": weights_commitment(weights, chunk=chunk, fmt=fmt, config=config),
            "plain_sha256": sha256(weights), "wrapped_dek": seal_to(governor_kek_pub, dek, b"dek|" + model_digest.encode())}


def decrypt_weights(sealed: dict, dek: bytes) -> bytes | None:
    """The GPU's side: decrypt every chunk in order; None if any chunk was altered, swapped or reordered. This
    proves package integrity under the key only. Whether the bytes were the approved bytes is a separate question,
    answered by ``commitment_matches`` against the publisher's commitment carried in the lease (F01)."""
    aes = AESGCM(dek)
    out = bytearray()
    try:
        for idx, ct in enumerate(sealed["chunks"]):
            # the nonce is the chunk's byte offset, the same value seal_weights used when it encrypted the chunk
            out += aes.decrypt((idx * sealed["chunk"]).to_bytes(12, "big"), ct, _aad(sealed["model_digest"], idx))
    except Exception:
        return None
    return bytes(out) if sha256(bytes(out)) == sealed["plain_sha256"] else None
