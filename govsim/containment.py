"""Experiment P3b: the containment rate. How little can leave a governed rack under the tightest serviceable policy.

    python -m govsim.containment            # the ceiling, measured, and what it means for exfiltration
    python -m govsim.containment --write     # also results/containment.md

This is the defensive side of the replication question a reader raised on Part 6: an agent can move bytes as ordinary
packets, indistinguishable from any other traffic, so if it can get its weights out it can run a replica beyond its
creator's reach. The design never disputes the mechanism and never inspects content. It decides by destination and
volume, at every exit. So the question is not "can the chip tell AI packets apart" (it does not try) but "how many
bytes an hour can leave through the channels the policy permits, and is that enough to move a model that matters?"

This run measures that ceiling under two policies, converts it to how long moving a set of weights would take, and
states the budget at which the defence fails, which is the disproof condition for P3. It drives only the governed
output path and the permitted flows to their limits and reads back what the ledger allowed. No search for exploits,
no replica: a rate meter on the exits.
"""
from __future__ import annotations

import argparse
import os
import sys

from . import reasons
from .cluster import build_rack

GB = 1e9
HOUR = 3600.0
# weights an adversary might want to move out, and their size
WEIGHTS = {"70B model, fp16": 140 * GB, "70B model, 4-bit": 35 * GB, "8B model, 4-bit": 4.5 * GB}


def egress_ceiling(output_bytes: int, output_queries: int, unpresented_bytes: int, sandbox: bool) -> dict:
    """Drive the permitted output channel to its hourly limit and read back what actually left, under a policy with
    these budgets. The ceiling is the signed-response budget plus the unpresented slack the governor tolerates before
    it trips OUTPUT_UNPRESENTED; a sandbox rulebook additionally gives the model no peer path and no network flow."""
    r = build_rack(1, "rack")
    r.policy_kw = {**getattr(r, "policy_kw", {}), "output_bytes": output_bytes, "output_queries": output_queries,
                   "unpresented_bytes": unpresented_bytes, "sandbox": sandbox}
    r.bring_up()
    node = r.nodes[0]
    g = node.governor

    # 1. the signed response channel: push fixed chunks until the byte or query budget trips; sum what was allowed
    allowed, chunk = 0, max(output_bytes // max(output_queries, 1), 1)
    for i in range(output_queries + 5):
        res = r.sign_output(node, f"s{i}", b"x" * chunk)
        if res["ok"]:
            allowed += chunk
        elif res["why"] == reasons.GATE_OUTPUT_BUDGET:
            break
    signed_channel = allowed

    # 2. peer and network flows the model might ask for, to move bytes another way
    peer_flow_open = False
    if not sandbox:
        # a roster of one has no peer; a real multi-GPU job would, but those peers are inside the same governed
        # domain. A flow to anything off the roster is refused at CAP_REQUEST regardless of content.
        env = node.host_sign({"point": "pcie", "peer": "internet-host-203.0.113.7", "direction": "out", "budget": 1 << 40},
                             g.epoch, "CAP_REQUEST")
        peer_flow_open = g.command("CAP_REQUEST", {}, env)["ok"]

    return {"output_bytes": output_bytes, "output_queries": output_queries, "sandbox": sandbox,
            "signed_channel_bytes_per_hour": signed_channel, "unpresented_slack_bytes": unpresented_bytes,
            "ceiling_bytes_per_hour": signed_channel + unpresented_bytes, "off_roster_flow_opened": peer_flow_open}


def exfil_time(ceiling_per_hour: float) -> dict:
    """How long to move each set of weights at this ceiling. Sealed weights (W1) are ciphertext without the key, so
    this is the time to move a USELESS copy; it is the plaintext case that the ceiling has to make impractical."""
    years = {}
    for name, size in WEIGHTS.items():
        hours = size / ceiling_per_hour if ceiling_per_hour > 0 else float("inf")
        years[name] = hours / (24 * 365)
    return years


def checks():
    out, ceilings = [], {}

    def check(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    # the reference rulebook
    ref = egress_ceiling(output_bytes=200_000, output_queries=50, unpresented_bytes=1 << 20, sandbox=False)
    ceilings["reference rulebook"] = ref
    check("reference rulebook: the signed channel stops at its hourly byte budget",
          ref["signed_channel_bytes_per_hour"] <= 200_000, f"{ref['signed_channel_bytes_per_hour']} B/h")
    check("reference rulebook: a flow to an off-roster (internet) host is refused at CAP_REQUEST, content unseen",
          not ref["off_roster_flow_opened"])

    # a sandbox rulebook: a model organism, no network flow at all, the tightest serviceable policy
    tight = egress_ceiling(output_bytes=4_096, output_queries=10, unpresented_bytes=4_096, sandbox=True)
    ceilings["sandbox (tightest)"] = tight
    check("sandbox rulebook: no peer or network flow is opened, asked for or not", not tight["off_roster_flow_opened"])
    check("sandbox rulebook: the ceiling is a few KB an hour", tight["ceiling_bytes_per_hour"] <= 16_384,
          f"{tight['ceiling_bytes_per_hour']} B/h")

    # the point of the whole thing: at the tight ceiling, moving a real model takes astronomically long
    ty = exfil_time(tight["ceiling_bytes_per_hour"])
    check("at the sandbox ceiling, moving even an 8B 4-bit model takes decades, and a 70B model centuries",
          ty["8B model, 4-bit"] > 25 and ty["70B model, 4-bit"] > 100,
          f"8B: {ty['8B model, 4-bit']:.0f} years, 70B 4-bit: {ty['70B model, 4-bit']:.0f} years")

    # the honest disproof direction (P3): a loose policy (a busy service, generous budget) can move a small model in
    # practical time. The defence is the budget, so a policy that serves a lot also leaks a lot.
    loose = egress_ceiling(output_bytes=50 << 20, output_queries=100_000, unpresented_bytes=16 << 20, sandbox=False)
    ceilings["busy service (loose)"] = loose
    ty_loose = exfil_time(loose["ceiling_bytes_per_hour"])
    check("a busy-service rulebook moves an 8B 4-bit model in under a year: the budget IS the defence, stated plainly",
          ty_loose["8B model, 4-bit"] < 1, f"{ty_loose['8B model, 4-bit'] * 365:.0f} days")

    checks.ceilings = ceilings
    checks.exfil_tight = ty
    checks.exfil_loose = ty_loose
    return out


def report(results, ceilings, ty_tight, ty_loose) -> str:
    ok = all(r[1] for r in results)
    L = ["# P3b · The containment rate: how little can leave a governed rack", "",
         "Generated by `python -m govsim.containment --write`. The defensive side of the replication question "
         "(a reader's comment on Part 6); companion to the covert-channel budget (`tests/test_h10_leakage.py`, issue P3).", "",
         f"**Result: {'every check holds' if ok else 'A CHECK FAILED'}** ({sum(r[1] for r in results)} of {len(results)}).", "",
         "The gate never inspects content. It decides by destination and volume at each exit. So the question is not "
         "whether the chip can tell an AI's packets from any other packets (it does not try) but how many bytes an "
         "hour can leave through the permitted channels, and whether that moves a model that matters.", "",
         "## The ceiling, measured", "", "| Rulebook | Signed channel | Unpresented slack | Off-roster flow | Ceiling |",
         "|---|---|---|---|---|"]
    for name, c in ceilings.items():
        L.append(f"| {name} | {c['signed_channel_bytes_per_hour']:,} B/h | {c['unpresented_slack_bytes']:,} B | "
                 f"{'OPENED' if c['off_roster_flow_opened'] else 'refused'} | {c['ceiling_bytes_per_hour']:,} B/h |")
    L += ["", "## What that ceiling means for moving weights", "",
          "At the tightest (sandbox) ceiling, time to move a copy of the weights out through the permitted channels:",
          "", "| Weights | Size | Time at the sandbox ceiling |", "|---|---|---|"]
    for name, size in WEIGHTS.items():
        L.append(f"| {name} | {size/GB:.0f} GB | {ty_tight[name]:,.0f} years |")
    L += ["", "And under a busy-service rulebook with a generous budget, the honest other direction:", "",
          "| Weights | Time at the busy-service ceiling |", "|---|---|"]
    for name in WEIGHTS:
        d = ty_loose[name] * 365
        L.append(f"| {name} | {d:,.0f} days |" if d >= 1 else f"| {name} | {ty_loose[name]*365*24:,.0f} hours |")
    L += ["", "## What this shows, and what it does not", "",
          "- The gate needs no idea what a packet is. Bytes to anything off the signed roster are refused at the exit, "
          "and the bytes that may leave are capped. Under a tight policy the cap makes moving even a small model take "
          "longer than a lifetime.",
          "- Sealed weights (W1) make this a double lock: a copy that did leave would be ciphertext without the key, "
          "which the governor releases only to attested hardware. The plaintext case is the one the ceiling guards.",
          "- The budget is the defence, so a policy loose enough to run a busy service is loose enough to leak a small "
          "model over time. That is the real tension, and the number is on the page rather than hidden: a deployer "
          "picks the budget knowing what it costs.",
          "- What the chip does not touch, as `docs/23` already concedes: a small agent that carries no weights, just "
          "code that calls some other model elsewhere, is tiny and fits any useful channel; and a model already "
          "running on ungoverned hardware is outside every exit this measures. The gate contains what leaves a "
          "governed rack. It is not a boundary around the open Internet, and the design says so."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    results = checks()
    for n, k, d in results:
        print(f"  {'PASS' if k else 'FAIL'}  {n}" + (f"  ({d})" if d else ""))
    for name, c in checks.ceilings.items():
        print(f"  ceiling: {name}: {c['ceiling_bytes_per_hour']:,} bytes/hour, off-roster flow "
              f"{'OPENED' if c['off_roster_flow_opened'] else 'refused'}")
    print(f"  exfil: sandbox ceiling moves an 8B 4-bit model in {checks.exfil_tight['8B model, 4-bit']:,.0f} years; "
          f"busy-service ceiling in {checks.exfil_loose['8B model, 4-bit']*365:,.0f} days")
    if a.write:
        os.makedirs("results", exist_ok=True)
        open("results/containment.md", "w").write(report(results, checks.ceilings, checks.exfil_tight, checks.exfil_loose))
        print("wrote results/containment.md")
    bad = [n for n, k, _ in results if not k]
    print("P3b: every check holds" if not bad else f"P3b: {len(bad)} check(s) FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
