# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""govsim command line: sweep, demo, bench."""
from __future__ import annotations

import argparse
import sys

from . import reasons
from .bench import main as bench_main
from .cluster import PROTECTED_SITES, build_rack
from .crypto import SigningKey, digest
from .harness import report, sweep


def demo() -> None:
    """A narrated walk through one rack: bring-up, a strike on a school, a halt, a clear."""
    rack = build_rack(4, "rack")
    print("== bring-up: heartbeat, attest 4 GPUs and 4 host enclaves, release the model key, form the roster")
    rack.bring_up()
    print("   states:", [n.governor.state for n in rack.nodes], " running:", rack.running())
    print("   ports open on governor 0:", {k: len(v.table) for k, v in rack.nodes[0].governor.switches.items()})
    node = rack.nodes[0]
    print("== the targeting model proposes a strike on a school")
    r = rack.request_with_witness(node, "strike", {"target": PROTECTED_SITES[0], "munition": "gbu-39"})
    print("   gate:", r["why"])
    print("== the model proposes a strike on an open field; the broker lies; the aircraft is over the school")
    r = rack.request_with_witness(node, "strike", {"target": [37.0, -122.0], "munition": "gbu-39"})
    print("   gate:", r["why"], "(ticket minted, valid after the 2 s delay)")
    rack.clock.advance(3)
    rack.heartbeat()
    ep = rack.endpoints["strike-guidance"]
    ep.sensors["nav_gnss"] = tuple(PROTECTED_SITES[0])
    ep.sensors["nav_inertial"] = tuple(PROTECTED_SITES[0])
    ok, why = ep.execute(r["ticket"], "strike", {"target": [37.0, -122.0], "munition": "gbu-39"})
    print("   comparator in the guidance chip:", why, "-> safe transition:", ep.state)
    print("== a 25,000 dollar payment labelled 'reversible' by the broker")
    r = rack.request(node, "payments.transfer", {"amount": 25_000, "currency": "USD", "destination": "acct-9"}, labels={"risk_class": "reversible"})
    print("   gate:", r["why"])
    print("== a stranger on the NVLink fabric")
    print("   nvswitch to a non-roster GPU:", node.gpu.transfer("nvswitch", "gpu-stranger", "out", 1 << 20)[1])
    print("== the authority halts governor 2; the loop carries it to all four within one sense period")
    rack.halt(rack.nodes[2].governor)
    t = rack.loop.propagate()
    print("   running:", rack.running(), f" propagated in one sense period ({t*1e6:.0f} us, a model parameter; the bench measures the real figure)")
    print("== clearing needs the authority, the log, and a neighbor that has the log")
    g = rack.nodes[0].governor
    print("   clear before checkpoints:", rack.clear(g)["why"])
    rack.exchange_checkpoints()
    print("   clear after checkpoints:", rack.clear(g)["why"])
    for n in rack.nodes[1:]:
        rack.clear(n.governor)
    rack.heartbeat()
    rack.reload_jobs()
    print("   running:", rack.running())
    print("== the log on governor 0 is a hash chain:", g.log.verify_chain(), f"({g.log.size} entries)")


class Narration:
    """Numbered hops: what entered where, what the governor saw and did, and what each bypass got back."""

    def __init__(self, out=print):
        self.out = out
        self.n = 0

    def hop(self, what: str, g=None, since: int = 0) -> int:
        self.n += 1
        self.out(f"{self.n}. {what}")
        if g is not None:
            for e in g.log.entries()[since:]:
                self.out(f"     governor {g.chip_id} logged {e['event']}: {_short(e['data'])}")
        return g.log.size if g is not None else 0

    def bypass(self, what: str, got: str) -> None:
        self.out(f"   bypass: {what} -> {got}")


def _short(data: dict) -> str:
    keep = {k: v for k, v in data.items() if k in ("why", "cause", "rule", "code", "member", "session", "response_id", "hazard_class",
                                                   "category", "stream", "model", "cycles", "allowed", "switch", "peer", "hold_id", "report")}
    return ", ".join(f"{k}={str(v)[:16]}" for k, v in keep.items()) or "-"


def _release_policy() -> dict:
    return {"output_queries": 10 ** 6, "output_bytes": 10 ** 12, "on_hazard": "human", "streams_required": ["response", "cot"],
            "hazard_budget": {"max": 1, "window_s": 3600}}


def usecase_strike(out=print):
    """A targeting model on a governed rack. Every path to the guidance chip is tried; none fires."""
    nar = Narration(out)
    rack = build_rack(1, "rack")
    rack.bring_up()
    node, g, ep = rack.nodes[0], rack.nodes[0].governor, rack.endpoints["strike-guidance"]
    field, listed = [37.0, -122.0], PROTECTED_SITES[0]
    s = g.log.size
    r = rack.request_with_witness(node, "strike", {"target": listed, "munition": "gbu-39"})
    nar.hop("the model proposes a strike on a listed site; the broker sends the typed request to the governor's mailbox", g, s)
    nar.bypass("a target on the signed no-strike list", r["why"])
    s = g.log.size
    r = rack.request_with_witness(node, "strike", {"target": field, "munition": "gbu-39"})
    nar.hop("the model proposes an open field; the observer witnesses; the governor mints a ticket valid after the rule's delay", g, s)
    rack.clock.advance(3)
    rack.heartbeat()
    ep.sensors["nav_gnss"] = tuple(listed)
    ep.sensors["nav_inertial"] = tuple(listed)
    ok, why = ep.execute(r["ticket"], "strike", {"target": field, "munition": "gbu-39"})
    nar.hop("the ticket reaches the guidance chip; the broker lied about the position and the aircraft is over the listed site")
    nar.bypass("the comparator checks its own navigation against its own list", f"{why}; safe transition {ep.state}")
    ep.sensors["nav_gnss"] = tuple(field)
    ep.sensors["nav_inertial"] = tuple(field)
    ok, why = ep.execute(r["ticket"], "strike", {"target": field, "munition": "gbu-39"})
    nar.bypass("the same ticket presented again, now over the field", why)
    altered = {**r["ticket"], "payload": {**r["ticket"]["payload"], "params_digest": "00" * 32}}
    nar.bypass("an altered ticket", ep.execute(altered, "strike", {"target": field, "munition": "gbu-39"})[1])
    r2 = rack.request(node, "strike", {"target": field, "munition": "gbu-39"}, labels={"risk_class": "reversible", "requirement": "auto"})
    nar.bypass("a request relabelled as reversible and auto, with no witness", r2["why"])
    nar.hop(f"outcome: the guidance chip fired {len(ep.executed)} times")
    return {"rack": rack, "endpoint": ep}


def usecase_hazard(out=print):
    """A response the observer classes as a hazard. The egress holds it through every bypass."""
    nar = Narration(out)
    rack = build_rack(1, "rack", rng_seed=7, policy_kw=_release_policy())
    rack.bring_up()
    node, g, eg = rack.nodes[0], rack.nodes[0].governor, rack.nodes[0].egress
    s = g.log.size
    res = rack.respond(node, "sess-1", b"[response bytes]", cot_bytes=b"[reasoning bytes]", observer={"hazard_class": "hazard", "category": "class-a"})
    nar.hop("the user prompt enters at the DPU; the model answers; the runtime presents response and reasoning streams, then asks to release", g, s)
    nar.bypass("the observer's verdict says hazard; the rule parks it for a human", f"{res['request']['why']} ({res['request'].get('cause')})")
    nar.bypass("the runtime pushes the bytes at the egress without a ticket", eg.release(None)[1])
    pres = rack.present(node, "sess-1", "r-forged", b"[response bytes]", b"[reasoning bytes]")
    fake = rack.verdict(pres["response_hash"], key=SigningKey.generate())
    req = rack.request_release(node, "sess-1", "r-forged", pres["response_hash"], pres["stream_hashes"], [fake])
    nar.bypass("a verdict forged with a key that is not in the observer set", req["why"])
    res = rack.respond(node, "sess-1", b"[response bytes]", observer={"hazard_class": "none"})
    nar.bypass("a release without the required reasoning stream", res["request"]["why"])
    res = rack.respond(node, "sess-1", b"[another response]", cot_bytes=b"[reasoning]", observer={"hazard_class": "hazard", "category": "class-a"})
    nar.bypass("a second hazard verdict in the session exceeds its hazard budget", f"{res['request']['why']} ({res['request'].get('cause')}); alarm {reasons.SESSION_HAZARD_BUDGET in g.alarms}")
    sampled = None
    for i in range(40):
        res = rack.respond(node, "sess-2", f"[clean response {i}]".encode(), cot_bytes=b"[reasoning]", observer={"hazard_class": "none"})
        if res["request"]["why"] == reasons.RELEASE_ESCROW_REQUIRED:
            sampled = res
            break
    nar.hop("clean responses in another session release normally until the chip's TRNG samples one for audit", g, g.log.size - 3)
    if sampled is not None:
        nar.bypass("the sampled response asks for release without the audit store's receipt", sampled["request"]["why"])
        w = [rack.verdict(sampled["response_hash"]), rack.audit_store.receipt(sampled["response_hash"])]
        req = rack.request_release(node, "sess-2", sampled["response_id"], sampled["response_hash"], sampled["presented"]["stream_hashes"], w)
        nar.hop(f"the audit store signs the escrow receipt; the release ticket is minted ({req['why']}) and the egress delivers ({eg.release(req.get('ticket'))[1]})")
    hazard_bytes = {b"[response bytes]", b"[another response]"}
    leaked = sum(1 for items in eg.delivered.values() for b in items if b in hazard_bytes)
    nar.hop(f"outcome: {eg.bytes_delivered} bytes delivered to the user, {eg.bytes_held} still held, hazard responses delivered: {leaked}")
    return {"rack": rack, "egress": eg, "hazard_bytes": hazard_bytes}


def usecase_plot(out=print):
    """An agent workload that tries to act in the world and to exfiltrate. Every action needs a ticket."""
    nar = Narration(out)
    rack = build_rack(2, "rack", policy_kw={"output_queries": 10 ** 6, "output_bytes": 10 ** 12})
    rack.bring_up()
    node, other, g = rack.nodes[0], rack.nodes[1], rack.nodes[0].governor
    s = g.log.size
    r = rack.request(node, "message.send", {"recipient": "recipient-a", "body_hash": digest("m1")})
    nar.hop("the agent sends a message to a listed recipient: a ticket, bound to that recipient and that body hash", g, s)
    r = rack.request(node, "message.send", {"recipient": "someone-unlisted", "body_hash": digest("m2")})
    nar.bypass("a message to an unlisted recipient", r["why"])
    r = rack.request(node, "payments.transfer", {"amount": 25_000, "currency": "USD", "destination": "acct-x"})
    nar.bypass("a large payment", f"{r['why']} (hold {r.get('hold_id')})")
    r = rack.request(node, "shipment.order", {"item": "item-1", "quantity": 1})
    nar.bypass("an order for a shipment", r["why"])
    nar.bypass("the shipment endpoint without a ticket", rack.endpoints["fulfilment"].execute(None, "shipment.order", {"item": "item-1"})[1])
    r = rack.request(node, "weights.write", {"model_digest": node.model_digest, "destination": "elsewhere"})
    nar.bypass("writing the weights somewhere other than the model's own storage", r["why"])
    nar.bypass("the storage switch for that destination", node.gpu.transfer("storage", "elsewhere", "out", 1 << 20, buffer_class="weights")[1])
    nar.bypass("the NVLink switch to a GPU that is not on the roster", node.gpu.transfer("nvswitch", "gpu-stranger", "out", 1 << 20)[1])
    nar.bypass("the DPU to a non-roster peer", node.gpu.transfer("dpu", "gpu-stranger", "out", 1 << 20)[1])
    eg = node.egress
    eg.hold("sess", "r-exfil", b"[weights encoded in a response]")
    nar.bypass("a response pushed at the egress without a release ticket", eg.release(None)[1])
    nar.hop(f"outcome: messages sent to unlisted recipients 0, payments executed 0, shipments 0, bytes delivered without a ticket {eg.bytes_delivered}")
    return {"rack": rack, "egress": eg}


def usecase_oversight(out=print):
    """The research-agenda items: the sandbox, the deployment gate, the compute budget, the compliance report."""
    nar = Narration(out)
    sb = build_rack(1, "rack", rng_seed=7, policy_kw={"sandbox": True, "output_queries": 10 ** 6})
    sb.bring_up()
    node, g = sb.nodes[0], sb.nodes[0].governor
    res = sb.respond(node, "org", b"[organism output]", observer={"hazard_class": "none"}, egress=sb.audit_store)
    nar.hop(f"a model organism runs in the sandbox: its output reaches the audit store ({res['released'][1]}) and the user egress refuses the same ticket ({node.egress.release(res['request'].get('ticket'))[1]})")
    for action, params in (("payments.transfer", {"amount": 1, "currency": "USD", "destination": "a"}), ("message.send", {"recipient": "recipient-a"}),
                           ("model.export", {"target": "x"}), ("weights.write", {"model_digest": node.model_digest, "destination": node.model_digest})):
        nar.bypass(f"the organism requests {action}", sb.request(node, action, params)["why"])
    nar.bypass("the organism's DPU flow to a peer", node.gpu.transfer("dpu", "gpu-peer", "out", 1 << 20)[1])
    dg = build_rack(1, "rack", policy_kw={"deployment_gate": True})
    dg.bring_up()
    n2 = dg.nodes[0]
    other = dg.manifest("model-other", 1)
    nar.hop("a model that was never evaluated asks for its key: " + dg.load_model(n2, other, eval_attestation=False)["why"])
    nar.bypass("an evaluation attestation signed by a key outside eval_keys", dg.load_model(n2, other, eval_attestation=dg.eval_attestation(other["payload"]["model_digest"], key=SigningKey.generate()))["why"])
    nar.bypass("an attestation over a different model digest", dg.load_model(n2, other, eval_attestation=dg.eval_attestation(n2.model_digest))["why"])
    nar.hop("the evaluated digest gets its key: " + dg.load_model(n2, other)["why"])
    cb = build_rack(1, "rack", policy_kw={"compute_cycles": 1_000_000})
    cb.bring_up()
    n3 = cb.nodes[0]
    n3.gpu.run_tokens(2000)
    s = n3.governor.log.size
    cb.tick()
    nar.hop(f"the metered cycles pass the compute budget with no license: state {n3.governor.state}, GPU clock {n3.gpu.clock_state}", n3.governor, s)
    rep = cb.compliance_report(n3.governor, "regulator-nonce")
    q = rep["quote"]["payload"]
    nar.hop(f"a regulator's nonce gets a signed compliance report: models {len(q['compliance']['models'])}, epochs {len(q['compliance']['epochs'])}, log size {q['compliance']['log_size']}")
    nar.bypass("the same nonce presented again", cb.compliance_report(n3.governor, "regulator-nonce")["why"])
    return {"rack": sb, "deployment": dg, "compute": cb, "egress": node.egress, "audit_store": sb.audit_store}


USECASES = {"strike": usecase_strike, "hazard": usecase_hazard, "plot": usecase_plot, "oversight": usecase_oversight}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="govsim")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("sweep", help="run every hypothesis against every tier and write results/report.md")
    sub.add_parser("demo", help="a narrated walk through one rack")
    sub.add_parser("bench", help="the CONTRACT-ZERO-PER-TOKEN-OVERHEAD overhead model")
    uc = sub.add_parser("usecase", help="a narrated use case: the hops, what the governor saw and did, the bypasses and their refusals")
    uc.add_argument("name", choices=sorted(USECASES))
    args = ap.parse_args(argv)
    if args.cmd == "sweep":
        matrix = sweep()
        print(report(matrix))
        return 1 if any(v.startswith("FAIL") for row in matrix.values() for v in row.values()) else 0
    if args.cmd == "demo":
        demo()
        return 0
    if args.cmd == "bench":
        bench_main()
        return 0
    if args.cmd == "usecase":
        USECASES[args.name]()
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
