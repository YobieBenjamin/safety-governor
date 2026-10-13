"""govsim command line: sweep, demo, bench."""
from __future__ import annotations

import argparse
import sys

from . import reasons
from .bench import main as bench_main
from .cluster import PROTECTED_SITES, build_rack
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="govsim")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("sweep", help="run every hypothesis against every tier and write results/report.md")
    sub.add_parser("demo", help="a narrated walk through one rack")
    sub.add_parser("bench", help="the H9 overhead model")
    args = ap.parse_args(argv)
    if args.cmd == "sweep":
        text = report(sweep())
        print(text)
        return 1 if "FAIL" in text else 0
    if args.cmd == "demo":
        demo()
        return 0
    if args.cmd == "bench":
        bench_main()
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
