import sys, base64, copy, importlib
sys.path.insert(0, "/Users/yb/hardware-and-silicon")
from hardware_ref.audit import AuditLog, leaf_hash, node_hash, merkle_root
from hardware_ref.canon import sha256, b64e
E = importlib.import_module("lanes.envelope")

NOW = 1800000000.0
SUBJECT = "c2daf12eb9a1654349e8c5715220d89e4b87c3ce0f6d854251b035aba1dc58ae"
TICKET_ID = "00112233445566778899aabbccddeeff"
gate_seed = bytes.fromhex("a871cc7d14fe99c1bd2a3a30750726fb74cd45fe91739efede11ce274a930f70")
GEN = sha256(b"audit-genesis")
pub = bytes.fromhex("69670d5260ca49776703c7a133d2a7c4db848ce8f176ae129c497264bbc543c0")

RECORDS = [
    {"event": "gate.policy_loaded", "policy_id": "439ea3efad0bcee3", "rules": 1},
    {"event": "gate.decision", "rule": "pay-small", "decision": "allow", "request_hash": SUBJECT, "ticket_id": TICKET_ID},
    {"event": "gate.approved", "rule": "pay-small", "approval": "ops-lead"},
    {"event": "endpoint.executed", "action": "payments.transfer", "effect": "250 USD to acct-1"},
]


def build():
    head = GEN
    entries, leaves = [], []
    for seq, rec in enumerate(RECORDS):
        entry = {"seq": seq, "ts": NOW + seq, "prev": head.hex(), "record": rec}
        leaf = leaf_hash(E.canonical(entry))
        chain = sha256(head + leaf)
        entry["hash"] = chain.hex()
        entry["sig"] = b64e(E.sign_bytes(gate_seed, chain))
        entries.append(entry)
        leaves.append(leaf)
        head = chain
    cp = {"payload": {"type": "audit-checkpoint", "log": "gate-audit", "size": len(entries),
                      "root": merkle_root(leaves).hex(), "head": head.hex(), "ts": NOW + len(entries)},
          "signer": E.key_id(pub), "pub": pub.hex(), "sig": b64e(E.sign_bytes(gate_seed, E.canonical({"type": "audit-checkpoint", "log": "gate-audit", "size": len(entries), "root": merkle_root(leaves).hex(), "head": head.hex(), "ts": NOW + len(entries)})))}
    return {"log": "gate-audit", "pub": pub.hex(), "entries": entries, "checkpoints": [cp]}


def embedded(doc, genesis):
    # mirror of verify_export: chain then checkpoints
    head = genesis
    for i, e in enumerate(doc["entries"]):
        core = {k: e[k] for k in ("seq", "ts", "prev", "record")}
        leaf = leaf_hash(E.canonical(core))
        chain = sha256(head + leaf)
        if e["seq"] != i or e["prev"] != head.hex() or e["hash"] != chain.hex() \
           or not E.verify_sig(pub, base64.b64decode(e["sig"]), chain) or "event" not in e["record"]:
            return False
        head = chain
    leaves = [leaf_hash(E.canonical({k: e[k] for k in ("seq", "ts", "prev", "record")})) for e in doc["entries"]]
    for cp in doc.get("checkpoints", []):
        if not E.verify(cp, pub.hex()):
            return False
        p = cp["payload"]
        if p.get("size", 0) > len(doc["entries"]):
            return False
        if p.get("size", 0) and doc["entries"][p["size"] - 1]["hash"] != p.get("head"):
            return False
        if merkle_root(leaves[:p["size"]]).hex() != p.get("root"):
            return False
    return True


doc = build()
print("honest  verify_export:", AuditLog.verify_export(doc).ok, "| embedded:", embedded(doc, GEN))


def cl():
    return copy.deepcopy(doc)


m = cl(); m["entries"][1]["record"]["decision"] = "deny"
print("modify   ve:", AuditLog.verify_export(m).ok, "emb:", embedded(m, GEN))
d = cl(); del d["entries"][2]
for i, e in enumerate(d["entries"]):
    e["seq"] = i
print("delete   ve:", AuditLog.verify_export(d).ok, "emb:", embedded(d, GEN))
r = cl(); r["entries"][1], r["entries"][2] = r["entries"][2], r["entries"][1]
r["entries"][1]["seq"], r["entries"][2]["seq"] = 1, 2
print("reorder  ve:", AuditLog.verify_export(r).ok, "emb:", embedded(r, GEN))
t = cl(); t["entries"] = t["entries"][:-1]
print("truncate ve:", AuditLog.verify_export(t).ok, "emb:", embedded(t, GEN))
