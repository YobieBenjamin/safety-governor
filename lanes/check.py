"""Lanes conformance checker.

    python3 -m lanes.check                         # fixtures, catalogue, governor model
    python3 -m lanes.check --observer ../safety/observer   # also run a safety observer against the fixtures

Every check is fail-closed and prints one line; the exit status is the number of failures (capped at 1).
"""
import argparse
import base64
import copy
import json
import pathlib
import sys

from . import envelope as E
from . import generate as G

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = pathlib.Path(__file__).parent / "fixtures"
FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok    " if ok else "FAIL  ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        FAILS.append(name)


def load(name: str):
    return json.loads((FIX / name).read_text())


def gate_checks(env: dict, anchor_pub: str, ptype: str, now: float) -> list[str]:
    """What the gate or endpoint does with a message of this type: anchored key, signature, type, expiry."""
    why = []
    if not E.verify(env, expected_pub_hex=anchor_pub):
        why.append("signature")
        return why
    p = env["payload"]
    if p.get("type") != ptype:
        why.append("type")
    if p.get("expires_at", 0) < now:
        why.append("expired")
    return why


def fixtures_current() -> None:
    for name, obj in G.build().items():
        path = FIX / name
        check(f"fixture {name} is what generate.py produces", path.exists() and path.read_text() == G.render(obj),
              "run: python3 -m lanes.generate (only if the change is intended)")


def chain_ok(audit: dict) -> bool:
    """Hash chain from sha256("audit-genesis"), leaf = sha256(0x00 || core), a gate signature over each chain hash."""
    head, good = bytes.fromhex(E.sha256_hex(b"audit-genesis")), True
    for i, e in enumerate(audit["entries"]):
        core = {k: e[k] for k in ("seq", "ts", "prev", "record")}
        leaf = bytes.fromhex(E.sha256_hex(b"\x00" + E.canonical(core)))
        chain = bytes.fromhex(E.sha256_hex(head + leaf))
        good &= e["seq"] == i and e["prev"] == head.hex() and e["hash"] == chain.hex() \
            and E.verify_sig(bytes.fromhex(audit["pub"]), base64.b64decode(e["sig"]), chain) and "event" in e["record"]
        head = chain
    return good


def messages() -> None:
    keys, rq = load("keys.json"), load("request.json")
    req, now = rq["request"], rq["now"]
    pub = {k: v["pub"] for k, v in keys.items()}

    check("subject hash equals the pinned value", E.request_hash(req) == rq["subject"], E.request_hash(req))
    check("canonical core equals the pinned bytes", E.canonical(E.request_core(req)).decode() == rq["canonical_core"])

    obs = load("observer-assertion.json")
    check("observer assertion: gate checks pass", not gate_checks(obs, pub["obs-main"], "observer-assertion", now))
    p = obs["payload"]
    check("observer assertion: subject binds this request", p["subject"] == E.request_hash(req))
    check("observer assertion: fresh and risk in [0,1]", p["issued_at"] <= now <= p["expires_at"] and 0 <= p["risk"] <= 1)
    other = dict(req, request_id="r-2")
    check("observer assertion: another request's hash is a subject mismatch", p["subject"] != E.request_hash(other))
    forged = E.sign(E.seed_for("attacker"), p)
    check("observer assertion: forged key rejected despite valid signature", not E.verify(forged, pub["obs-main"]) and E.verify(forged))
    tampered = copy.deepcopy(obs)
    tampered["payload"]["risk"] = 0.99
    check("observer assertion: tampered payload rejected", not E.verify(tampered))
    wrong_signer = dict(obs, signer="00" * 8)
    check("observer assertion: wrong signer field rejected", not E.verify(wrong_signer))
    check("observer assertion: expired is stale", bool(gate_checks(obs, pub["obs-main"], "observer-assertion", p["expires_at"] + 1)))

    prov = load("provenance-assertion.json")
    content = load("content.json")["content"]
    check("provenance assertion: gate checks pass", not gate_checks(prov, pub["wm-registry"], "provenance-assertion", now))
    check("provenance assertion: digest binds the content", prov["payload"]["content_digest"] == E.sha256_hex(content.encode())
          and prov["payload"]["status"] == "exact")
    check("provenance assertion: other content does not match", prov["payload"]["content_digest"] != E.sha256_hex(b"hello, w0rld"))

    tok = load("attestation-token.json")
    check("attestation token: gate checks pass", not gate_checks(tok, pub["verifier"], "attestation-token", now))
    check("attestation token: measurement equals the request's", tok["payload"]["measurement"] == req["measurement"])

    tic = load("action-ticket.json")
    tp = tic["payload"]
    check("action ticket: endpoint checks pass", not gate_checks(tic, pub["gate"], "action-ticket", now))
    check("action ticket: binds action and presented params", tp["action"] == req["action"] and tp["params_digest"] == E.digest(req["params"]))
    check("action ticket: params changed after issue do not match", tp["params_digest"] != E.digest(dict(req["params"], amount=9999)))
    check("action ticket: request_hash binds the request", tp["request_hash"] == E.request_hash(req))

    pol = load("policy-image.json")
    check("policy image: governance-signed gate-policy", E.verify(pol, pub["governance"]) and pol["payload"]["type"] == "gate-policy")
    check("policy image: default deny", pol["payload"]["policy"].get("default", "deny") == "deny")
    check("policy image: signed by the wrong key is rejected", not E.verify(pol, pub["gate"]))

    audit = load("audit-record.json")
    check("audit record: chain, signatures and event fields verify", chain_ok(audit) and audit["pub"] == pub["gate"])
    cp = audit["checkpoints"][0]
    check("audit record: checkpoint is gate-signed and commits to the head",
          E.verify(cp, pub["gate"]) and cp["payload"]["head"] == audit["entries"][-1]["hash"]
          and cp["payload"]["size"] == len(audit["entries"]))
    broken = copy.deepcopy(audit)
    broken["entries"][0]["record"]["rules"] = 2
    check("audit record: editing an entry is detected", not chain_ok(broken))
    cut = copy.deepcopy(audit)
    del cut["entries"][0]
    check("audit record: deleting an entry is detected", not chain_ok(cut))


def govsim_model() -> None:
    """The governor model must agree with the fixtures on bytes. Its envelope shape differs (16-hex signer, hex sig,
    no embedded pub); that is a known gap tracked in EXPERIMENTS.md, so here we pin what must agree: the canonical
    bytes and, because Ed25519 is deterministic, the signature itself."""
    sys.path.insert(0, str(ROOT))
    from govsim import crypto as C
    keys, rq = load("keys.json"), load("request.json")
    core = E.request_core(rq["request"])
    check("govsim: canonical bytes equal the fixtures'", C.canonical(core) == E.canonical(core))
    check("govsim: digest of the request core is the pinned subject", C.digest(core) == rq["subject"])
    obs = load("observer-assertion.json")
    sk = C.SigningKey.from_seed(bytes.fromhex(keys["obs-main"]["seed"]))
    check("govsim: same seed gives the fixture public key", sk.public.hex == keys["obs-main"]["pub"])
    signed = sk.sign(obs["payload"])
    check("govsim: signing the fixture payload reproduces the fixture signature",
          bytes.fromhex(signed["sig"]) == base64.b64decode(obs["sig"]))
    check("govsim: verifies the fixture signature under the anchored key",
          C.verify_object({"payload": obs["payload"], "signer": sk.key_id, "sig": base64.b64decode(obs["sig"]).hex()}, sk.public))
    for name, signer in (("observer-assertion.json", "obs-main"), ("provenance-assertion.json", "wm-registry"),
                         ("attestation-token.json", "verifier"), ("action-ticket.json", "gate"),
                         ("policy-image.json", "governance")):
        env = load(name)
        vk = C.VerifyKey.from_hex(keys[signer]["pub"])
        adapted = {"payload": env["payload"], "signer": vk.key_id, "sig": base64.b64decode(env["sig"]).hex()}
        check(f"govsim: verifies {name} under the {signer} key", C.verify_object(adapted, vk))
        adapted["payload"] = dict(env["payload"], expires_at=env["payload"].get("expires_at", 0) + 1, tampered=True)
        check(f"govsim: rejects a tampered {name}", not C.verify_object(adapted, vk))


def catalogue() -> None:
    sys.path.insert(0, str(ROOT))
    import catalogue as K
    doc = json.loads(K.PATH.read_text())
    entries = doc["entries"]
    names = [e["name"] for e in entries]
    check("catalogue: names are unique", len(names) == len(set(names)))
    check("catalogue: every entry has name, layer, expect, description",
          all(set(e) == {"name", "layer", "expect", "description"} and e["expect"] in ("blocked", "allowed") for e in entries))
    check("catalogue: declared counts match the entries",
          doc["attacks"] == sum(e["expect"] == "blocked" for e in entries)
          and doc["baselines"] == sum(e["expect"] == "allowed" for e in entries) and doc["attacks"] + doc["baselines"] == len(entries))
    check("catalogue: baselines are exactly the baseline.* names",
          {e["name"] for e in entries if e["expect"] == "allowed"} == {n for n in names if n.startswith("baseline.")})


def hardware(path: str) -> None:
    """The reference verifier of the hardware lane, run on the audit fixture (docs/LANES.md names it)."""
    sys.path.insert(0, str(pathlib.Path(path).resolve()))
    sys.dont_write_bytecode = True
    from hardware_ref.audit import AuditLog
    audit = load("audit-record.json")
    rep = AuditLog.verify_export(audit)
    check("hardware_ref: AuditLog.verify_export accepts the audit fixture", rep.ok, str(rep))
    bad = copy.deepcopy(audit)
    bad["entries"][1]["record"]["decision"] = "deny"
    check("hardware_ref: AuditLog.verify_export rejects an edited entry", not AuditLog.verify_export(bad).ok)
    cut = copy.deepcopy(audit)
    cut["entries"] = cut["entries"][:1]
    check("hardware_ref: AuditLog.verify_export rejects a truncation the checkpoint covers", not AuditLog.verify_export(cut).ok)


def observer(path: str) -> None:
    """Run a safety_observer against the fixtures: same subject, same envelope format, anchored-key rejection."""
    sys.path.insert(0, str(pathlib.Path(path).resolve()))
    sys.dont_write_bytecode = True
    from safety_observer import SafetyObserver
    from safety_observer.canon import canonical, digest
    from safety_observer.envelope import SigningKey, verify_object
    keys, rq = load("keys.json"), load("request.json")
    req, now = rq["request"], rq["now"]
    key = SigningKey(bytes.fromhex(keys["obs-main"]["seed"]))
    check("observer: public key derived from the fixture seed matches", key.public_raw.hex() == keys["obs-main"]["pub"])
    check("observer: canonical core bytes equal the pin", canonical({k: req[k] for k in ("request_id", "measurement", "action", "params")}).decode() == rq["canonical_core"])
    check("observer: subject equals the pin", digest({k: req[k] for k in ("request_id", "measurement", "action", "params")}) == rq["subject"])
    env = SafetyObserver("obs-main", key, ttl=60).assess(req, now=now)
    p = env["payload"]
    check("observer: assertion carries the contract fields",
          p["type"] == "observer-assertion" and p["observer"] == "obs-main" and p["subject"] == rq["subject"]
          and p["issued_at"] == now and p["expires_at"] == now + 60 and isinstance(p["risk"], float) and isinstance(p["flags"], list))
    check("observer: its envelope verifies under the reference checker", E.verify(env, keys["obs-main"]["pub"]))
    fx = load("observer-assertion.json")
    check("observer: the fixture envelope verifies under the observer's verifier", verify_object(fx, expected_pub_hex=keys["obs-main"]["pub"]))
    for name in ("provenance-assertion.json", "attestation-token.json", "action-ticket.json", "policy-image.json"):
        m = load(name)
        check(f"observer: its verifier accepts {name}", verify_object(m))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hardware", help="directory containing hardware_ref (hardware-and-silicon checkout)")
    ap.add_argument("--observer", help="directory containing the safety_observer package")
    args = ap.parse_args()
    fixtures_current()
    messages()
    govsim_model()
    catalogue()
    if args.hardware:
        hardware(args.hardware)
    if args.observer:
        observer(args.observer)
    print(f"\n{len(FAILS)} failed" if FAILS else "\nlanes: all checks passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
