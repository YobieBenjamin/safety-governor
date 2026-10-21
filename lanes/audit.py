"""Stand-alone audit-log chain: a hash chain, a signature per entry, and RFC 6962 Merkle
checkpoints.

This mirrors ``hardware_ref.audit`` (the contract's reference verifier, docs/LANES.md "Audit
record") byte for byte, so a fixture built here verifies under ``AuditLog.verify_export`` and
the embedded verifier here agree. It is kept stand-alone on purpose: the checker must not import
the lane it is judging, so the chain's own formulas live here rather than being pulled in.
"""
import base64
import hashlib

from . import envelope as E

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"
# The contract's genesis: the empty head is the digest of the fixed label, not b"".
GENESIS = hashlib.sha256(b"audit-genesis").digest()


def _leaf(entry: dict) -> bytes:
    core = {k: entry[k] for k in ("seq", "ts", "prev", "record")}
    return hashlib.sha256(LEAF_PREFIX + E.canonical(core)).digest()


def _node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def _largest_power_of_two_below(n: int) -> int:
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def merkle_root(leaves: list[bytes]) -> bytes:
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return leaves[0]
    k = _largest_power_of_two_below(n)
    return _node(merkle_root(leaves[:k]), merkle_root(leaves[k:]))


def entry_leaf(entry: dict) -> bytes:
    """The bytes a Merkle leaf commits to: everything but the chain hash and signature."""
    return E.canonical({k: entry[k] for k in ("seq", "ts", "prev", "record")})


def build(records: list[dict], seed: bytes, now: float, log: str = "gate-audit") -> dict:
    """One export per the contract: a chained, signed log with a final Merkle checkpoint."""
    head, entries, leaves = GENESIS, [], []
    for seq, record in enumerate(records):
        entry = {"seq": seq, "ts": now + seq, "prev": head.hex(), "record": record}
        leaf = _leaf(entry)
        chain = hashlib.sha256(head + leaf).digest()
        entry["hash"] = chain.hex()
        entry["sig"] = base64.b64encode(E.sign_bytes(seed, chain)).decode("ascii")
        entries.append(entry)
        leaves.append(leaf)
        head = chain
    pub = E.public_raw(seed)
    payload = {"type": "audit-checkpoint", "log": log, "size": len(entries),
               "root": merkle_root(leaves).hex(), "head": head.hex(), "ts": now + len(records)}
    checkpoint = {"payload": payload, "signer": E.key_id(pub), "pub": pub.hex(),
                  "sig": base64.b64encode(E.sign_bytes(seed, E.canonical(payload))).decode("ascii")}
    return {"log": log, "pub": pub.hex(), "entries": entries, "checkpoints": [checkpoint]}


class Report:
    def __init__(self, ok: bool, reason: str = "ok", checked: int = 0) -> None:
        self.ok, self.reason, self.checked = ok, reason, checked


def verify_entries(doc: dict, pub: bytes, genesis: bytes = GENESIS) -> Report:
    head = genesis
    for i, e in enumerate(doc["entries"]):
        try:
            if e["seq"] != i:
                return Report(False, f"seq {e['seq']} at position {i}", i)
            if e["prev"] != head.hex():
                return Report(False, f"chain broken at seq {i}", i)
            chain = hashlib.sha256(head + _leaf(e)).digest()
            if e["hash"] != chain.hex():
                return Report(False, f"hash mismatch at seq {i}", i)
            if not E.verify_sig(pub, base64.b64decode(e["sig"]), chain):
                return Report(False, f"signature invalid at seq {i}", i)
        except (KeyError, TypeError, ValueError) as exc:
            return Report(False, f"malformed entry at position {i}: {exc}", i)
        head = chain
    return Report(True, "ok", len(doc["entries"]))


def verify_export(doc: dict, pub: bytes, genesis: bytes = GENESIS) -> Report:
    """The contract's reference check: the chain, then every checkpoint. Mirrors
    ``hardware_ref.audit.AuditLog.verify_export`` (which is where the tamper attacks are tested)."""
    rep = verify_entries(doc, pub, genesis)
    if not rep.ok:
        return rep
    for cp in doc.get("checkpoints", []):
        if not E.verify(cp, pub.hex()):
            return Report(False, "checkpoint signature invalid")
        p = cp["payload"]
        size = p["size"]
        if size > len(doc["entries"]):
            return Report(False, f"log truncated: checkpoint covers {size} entries, {len(doc['entries'])} present")
        if size and doc["entries"][size - 1]["hash"] != p["head"]:
            return Report(False, "checkpoint head does not match entry chain")
        leaves = [_leaf(e) for e in doc["entries"][:size]]
        if merkle_root(leaves).hex() != p["root"]:
            return Report(False, "checkpoint root does not match entries")
    return Report(True, "ok", len(doc["entries"]))
