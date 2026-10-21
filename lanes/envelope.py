"""Reference canonical JSON and signed envelope for the lanes contract (docs/LANES.md in hardware-and-silicon).

Stand-alone on purpose: the checker must not import code from the lane it is judging.
"""
import base64
import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(obj) -> str:
    return sha256_hex(canonical(obj))


def request_core(req: dict) -> dict:
    return {k: req[k] for k in ("request_id", "measurement", "action", "params")}


def request_hash(req: dict) -> str:
    return digest(request_core(req))


def key_id(pub_raw: bytes) -> str:
    return hashlib.sha256(pub_raw).digest()[:8].hex()


def seed_for(name: str) -> bytes:
    """Fixture keys are public test keys derived from their name. Never use them for anything else."""
    return hashlib.sha256(b"lanes-fixture-key/" + name.encode()).digest()


def public_raw(seed: bytes) -> bytes:
    return Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def sign_bytes(seed: bytes, data: bytes) -> bytes:
    return Ed25519PrivateKey.from_private_bytes(seed).sign(data)


def sign(seed: bytes, payload: dict) -> dict:
    pub = public_raw(seed)
    return {"payload": payload, "signer": key_id(pub), "pub": pub.hex(),
            "sig": base64.b64encode(sign_bytes(seed, canonical(payload))).decode("ascii")}


def verify_sig(pub: bytes, sig: bytes, data: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(pub).verify(sig, data)
    except (InvalidSignature, ValueError):
        return False
    return True


def verify(env, expected_pub_hex: str | None = None) -> bool:
    if not isinstance(env, dict):
        return False
    try:
        pub_hex = env["pub"]
        pub = bytes.fromhex(pub_hex)
        sig = base64.b64decode(env["sig"], validate=True)
        payload = env["payload"]
    except (KeyError, ValueError, TypeError):
        return False
    if expected_pub_hex is not None and pub_hex != expected_pub_hex:
        return False
    if env.get("signer") != key_id(pub):
        return False
    return verify_sig(pub, sig, canonical(payload))
