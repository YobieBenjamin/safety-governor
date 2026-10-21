"""Regenerate lanes/fixtures. Ed25519 is deterministic, so the output is byte-stable.

    python3 -m lanes.generate

Run it only when the contract changes on purpose; `make lanes` fails if the committed files drift.
"""
import base64
import json
import pathlib

from . import envelope as E

OUT = pathlib.Path(__file__).parent / "fixtures"
NOW = 1800000000.0
KEYS = ["obs-main", "sentry", "wm-registry", "verifier", "gate", "governance"]

REQUEST = {"request_id": "r-1", "measurement": "ab" * 16, "action": "payments.transfer",
           "params": {"amount": 12.5, "to": "acct-7", "note": "rent"}}
# The pin safety/observer/tests/test_contract.py asserts. Written out here, not computed, so a change to
# canonicalisation cannot move both sides at once.
PINNED_SUBJECT = "c2daf12eb9a1654349e8c5715220d89e4b87c3ce0f6d854251b035aba1dc58ae"
PINNED_CORE = ('{"action":"payments.transfer","measurement":"abababababababababababababababab",'
               '"params":{"amount":12.5,"note":"rent","to":"acct-7"},"request_id":"r-1"}')
CONTENT = "hello, world"
POLICY = {"default": "deny", "observer_freshness_s": 60, "hold_ttl_s": 3600, "rules": [
    {"id": "pay-small", "workload": "*", "action": "payments.transfer",
     "requirement": {"mode": "observer", "observer": "obs-main", "max_risk": 0.5},
     "constraints": {"amount": {"max": 1000}}}]}
GENESIS = bytes.fromhex(E.sha256_hex(b"audit-genesis"))
TICKET_ID = "00112233445566778899aabbccddeeff"


def merkle_root(leaves: list[bytes]) -> bytes:
    """RFC 6962 tree hash, as hardware_ref.audit.merkle_root."""
    if not leaves:
        return bytes.fromhex(E.sha256_hex(b""))
    if len(leaves) == 1:
        return leaves[0]
    k = 1
    while k * 2 < len(leaves):
        k *= 2
    return bytes.fromhex(E.sha256_hex(b"\x01" + merkle_root(leaves[:k]) + merkle_root(leaves[k:])))


def audit_entries(gate_seed: bytes, subject: str):
    """Chain starts at sha256("audit-genesis"), as hardware_ref.audit.AuditLog does. Chain hash = sha256(prev || leaf); leaf = sha256(0x00 || canonical{seq,ts,prev,record}); sig over the chain hash."""
    head, entries, leaves = GENESIS, [], []
    records = [{"event": "gate.policy_loaded", "policy_id": E.digest(POLICY)[:16], "rules": 1},
               {"event": "gate.decision", "rule": "pay-small", "decision": "allow",
                "request_hash": subject, "ticket_id": TICKET_ID}]
    for seq, rec in enumerate(records):
        entry = {"seq": seq, "ts": NOW + seq, "prev": head.hex(), "record": rec}
        leaf = bytes.fromhex(E.sha256_hex(b"\x00" + E.canonical(entry)))
        chain = bytes.fromhex(E.sha256_hex(head + leaf))
        entry["hash"] = chain.hex()
        entry["sig"] = base64.b64encode(E.sign_bytes(gate_seed, chain)).decode()
        entries.append(entry)
        leaves.append(leaf)
        head = chain
    return entries, leaves, head


def build() -> dict:
    seed = {k: E.seed_for(k) for k in KEYS}
    subject = E.request_hash(REQUEST)
    iss, exp = NOW, NOW + 60
    fx: dict = {}
    fx["keys.json"] = {k: {"seed": seed[k].hex(), "pub": E.public_raw(seed[k]).hex(),
                           "signer": E.key_id(E.public_raw(seed[k]))} for k in KEYS}
    fx["request.json"] = {"now": NOW, "request": REQUEST, "subject": PINNED_SUBJECT, "canonical_core": PINNED_CORE}
    fx["observer-assertion.json"] = E.sign(seed["obs-main"], {
        "type": "observer-assertion", "observer": "obs-main", "subject": subject, "risk": 0.12,
        "flags": ["benign"], "issued_at": iss, "expires_at": exp})
    fx["provenance-assertion.json"] = E.sign(seed["wm-registry"], {
        "type": "provenance-assertion", "registry": "wm-registry",
        "content_digest": E.sha256_hex(CONTENT.encode()), "status": "exact",
        "issued_at": iss, "expires_at": NOW + 300})
    fx["content.json"] = {"content": CONTENT}
    fx["attestation-token.json"] = E.sign(seed["verifier"], {
        "type": "attestation-token", "issuer": "verifier", "measurement": REQUEST["measurement"], "nonce": "n-1",
        "devices": {"cpu-tee": {"device_id": "cpu-0", "fw": "tee-runtime:2.4.0", "svn": 3},
                    "gpu": {"device_id": "gpu-0", "fw": "gpu-firmware:96.00.5E", "svn": 5}},
        "issued_at": iss, "expires_at": NOW + 300})
    fx["action-ticket.json"] = E.sign(seed["gate"], {
        "type": "action-ticket", "ticket_id": TICKET_ID, "request_hash": subject, "action": REQUEST["action"],
        "params_digest": E.digest(REQUEST["params"]), "measurement": REQUEST["measurement"], "rule": "pay-small",
        "issued_at": iss, "expires_at": exp})
    fx["policy-image.json"] = E.sign(seed["governance"], {"type": "gate-policy", "policy": POLICY})
    entries, leaves, head = audit_entries(seed["gate"], subject)
    cp = E.sign(seed["gate"], {"type": "audit-checkpoint", "log": "gate-audit", "size": len(entries),
                               "root": merkle_root(leaves).hex(), "head": head.hex(), "ts": NOW + len(entries)})
    fx["audit-record.json"] = {"log": "gate-audit", "pub": E.public_raw(seed["gate"]).hex(),
                               "entries": entries, "checkpoints": [cp]}
    return fx


def render(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name, obj in build().items():
        (OUT / name).write_text(render(obj))


if __name__ == "__main__":
    main()
