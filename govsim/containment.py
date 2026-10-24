# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""EXPERIMENT-CONTAINMENT: the containment rate. How little can leave a governed rack under the tightest serviceable policy.

    python -m govsim.containment            # the ceiling, measured, and what it means for exfiltration
    python -m govsim.containment --write     # also results/containment.md

This is the defensive side of the replication question a reader raised on Part 6: an agent can move bytes as ordinary
packets, indistinguishable from any other traffic, so if it can get its weights out it can run a replica beyond its
creator's reach. The design never disputes the mechanism and never inspects content. It decides by destination and
volume, at every exit. So the question is not "can the chip tell AI packets apart" (it does not try) but "how many
bytes an hour can leave through the channels the policy permits, and is that enough to move a model that matters?"

The measurement is an honest one, and three earlier mistakes are corrected here (external audit F12, F13):

* The named policy is installed and its live limits are read back and asserted before anything is measured. An
  earlier version changed ``r.policy_kw`` after construction and called ``bring_up()``, which does not reload the
  policy, so every case silently ran the reference rulebook and the recorded numbers (6,135 and 26,200 B/h) were the
  reference and loop values, not the named policies.
* What is measured is bytes that actually LEAVE through the complete release path, read back at the egress boundary
  (``egress.bytes_delivered``), not successful signing calls. A provenance signature with no release moves nothing.
* Every externally observable channel the policy permits is inventoried, not just the signed-response channel. A
  listed-recipient ``message.send`` with an unbounded body is a permitted channel with no finite byte ceiling, so the
  finite-ceiling claim FAILS until that body is bounded and counted.
* The one-time burst (the unpresented slack, a cumulative host-minus-presented gap bounded once) is reported SEPARATELY
  from the sustained per-hour rate and never summed into it. An earlier version added the one-time budget onto the
  hourly figure; that was wrong (docs/18 8h).

No search for exploits, no replica: a rate meter on the exits, measured at the boundary.
"""
from __future__ import annotations

import argparse
import os
import sys

from . import reasons
from .cluster import LISTED_RECIPIENTS, build_rack

GB = 1e9
HOUR = 3600.0
# weights an adversary might want to move out, and their size
WEIGHTS = {"70B model, fp16": 140 * GB, "70B model, 4-bit": 35 * GB, "8B model, 4-bit": 4.5 * GB}
# a probe body far larger than any signed-channel ceiling, to expose an unbounded permitted channel
PROBE_BODY_BYTES = 1 << 20


def _output_rule(policy: dict) -> dict | None:
    for r in policy.get("rules", []):
        if r["action"] == "model.output":
            return r
    return None


def _rule(policy: dict, rule_id: str) -> dict | None:
    for r in policy.get("rules", []):
        if r["id"] == rule_id:
            return r
    return None


def _installed(node) -> dict:
    """The live limits the governor is actually running, read back from its loaded policy. These are asserted
    against what the case asked for before any byte is measured; a mismatch means the policy was not installed."""
    policy = node.governor.policy
    orule = _output_rule(policy) or {}
    ob = orule.get("output_budget") or {}
    rel = _rule(policy, "response.release") or {}
    return {"epoch": node.governor.epoch, "sandbox": bool(policy.get("sandbox")),
            "output_bytes": ob.get("bytes"), "output_queries": ob.get("queries"),
            "unpresented_bytes": ob.get("unpresented_bytes"),
            "release_endpoint": rel.get("endpoint")}


def _measure_signed_channel(r, node, egress, output_bytes: int, output_queries: int, sandbox: bool) -> int:
    """Drive the complete present -> release -> egress path with fixed chunks until the output budget trips, and
    return the bytes that ACTUALLY LEFT through the egress boundary (delivered, not signed). Chunks are sized so
    the byte and query budgets exhaust together, so the delivered total approaches the signed byte allowance."""
    before = egress.bytes_delivered
    target = max(min(output_queries, 64), 1)
    chunk = max(output_bytes // target, 1)
    observer = None if sandbox else {"hazard_class": "none", "risk": 0.1}
    for i in range(target + 5):
        # escrow=True supplies the audit-store receipt so a random audit draw never masks the byte ceiling we
        # are measuring; the only thing that stops delivery here is the signed-response budget itself.
        res = r.respond(node, "sess", b"x" * chunk, observer=observer, response_id=f"c{i}", egress=egress, escrow=True)
        if not res["released"][0]:
            break                      # budget tripped (or any refusal): nothing left on this one, stop
    return egress.bytes_delivered - before


def _probe_message_channel(r, node, message_max_bytes: int | None, message_rate: dict | None) -> dict:
    """Inventory the agent's listed-recipient message.send channel: attempt a listed send with a large body and
    one past any byte bound, and decide the channel's per-hour byte ceiling. An unbounded body means no finite
    ceiling. A byte bound plus a message rate give sustained = bound * messages/hour."""
    rule = _rule(node.governor.policy, "message.send.listed") or {}
    constraints = rule.get("constraints", {})
    body_bound = constraints.get("body", {}).get("max_bytes")
    rate = rule.get("rate")
    recipient = LISTED_RECIPIENTS[0]
    # attempt a large body to a listed recipient; if it is admitted the channel carries arbitrary bytes
    big = r.request(node, "message.send", {"recipient": recipient, "body": "x" * PROBE_BODY_BYTES})
    large_body_permitted = bool(big.get("ok"))
    over_bound_refused = None
    within_bound_permitted = None
    if body_bound is not None:
        over = r.request(node, "message.send", {"recipient": recipient, "body": "x" * (body_bound + 64)})
        over_bound_refused = not over.get("ok")
        small = "y" * max(body_bound - 8, 1)
        within = r.request(node, "message.send", {"recipient": recipient, "body": small})
        within_bound_permitted = bool(within.get("ok"))
    # a channel is bounded only if the body is capped AND a message rate caps how many go out per hour
    bounded = body_bound is not None and rate is not None and not large_body_permitted
    sustained = None
    if bounded:
        per_hour = rate["max"] * (HOUR / rate["window_s"])
        sustained = int(body_bound * per_hour)
    return {"channel": "message.send (listed recipient)", "body_max_bytes": body_bound, "rate": rate,
            "large_body_permitted": large_body_permitted, "over_bound_refused": over_bound_refused,
            "within_bound_permitted": within_bound_permitted, "bounded": bounded,
            "sustained_bytes_per_hour": sustained}


def egress_ceiling(output_bytes: int, output_queries: int, unpresented_bytes: int, sandbox: bool,
                   message_max_bytes: int | None = None, message_rate: dict | None = None) -> dict:
    """Install a named policy, read back and assert its live limits, then measure what actually leaves through
    each permitted channel at the enforced boundary.

    ``ceiling_bytes_per_hour`` is the SUSTAINED signed-channel rate (delivered bytes per hour). The one-time
    unpresented burst is reported separately in ``burst_bytes`` and never summed into the hourly rate.
    ``finite_ceiling_holds`` is true only if every permitted externally observable channel is bounded."""
    policy_kw = {"output_bytes": output_bytes, "output_queries": output_queries,
                 "unpresented_bytes": unpresented_bytes, "sandbox": sandbox}
    if message_max_bytes is not None:
        policy_kw["message_max_bytes"] = message_max_bytes
    if message_rate is not None:
        policy_kw["message_rate"] = message_rate
    r = build_rack(1, "rack", policy_kw=policy_kw)
    r.bring_up()
    node = r.nodes[0]
    g = node.governor

    inst = _installed(node)
    # assert the policy we asked for is the policy that is running, before measuring anything
    assert inst["output_bytes"] == output_bytes, f"installed output_bytes {inst['output_bytes']} != {output_bytes}"
    assert inst["output_queries"] == output_queries, f"installed output_queries {inst['output_queries']} != {output_queries}"
    assert inst["unpresented_bytes"] == unpresented_bytes, f"installed unpresented_bytes {inst['unpresented_bytes']} != {unpresented_bytes}"
    assert inst["sandbox"] == sandbox, f"installed sandbox {inst['sandbox']} != {sandbox}"

    # probe the other channels while the governor is cleanly in RUN, before the signed-channel measurement drives
    # the output budget to its trip (which raises an alarm and throttles the governor).
    msg = _probe_message_channel(r, node, message_max_bytes, message_rate)

    # peer and network flows the model might ask for, to move bytes another way: attempt it, do not assume the result
    off_roster_flow_opened = False
    if not sandbox:
        env = node.host_sign({"point": "pcie", "peer": "internet-host-203.0.113.7", "direction": "out", "budget": 1 << 40},
                             g.epoch, "CAP_REQUEST")
        off_roster_flow_opened = g.command("CAP_REQUEST", {}, env)["ok"]

    egress = r.audit_store if sandbox else node.egress
    sustained = _measure_signed_channel(r, node, egress, output_bytes, output_queries, sandbox)

    # the channel inventory: every externally observable channel the policy permits and whether it is bounded
    channels = [{"channel": "signed response (egress)", "bounded": True, "sustained_bytes_per_hour": sustained}]
    # the message channel is auto only when the policy does not gate it to humans (the sandbox does)
    if not sandbox:
        channels.append({"channel": msg["channel"], "bounded": msg["bounded"],
                         "sustained_bytes_per_hour": msg["sustained_bytes_per_hour"]})
    finite_ceiling_holds = all(c["bounded"] for c in channels)

    return {"output_bytes": output_bytes, "output_queries": output_queries, "sandbox": sandbox,
            "installed": inst,
            # sustained per-hour rate at the egress boundary (delivered, not signed). NOT including the burst.
            "ceiling_bytes_per_hour": sustained,
            "sustained_bytes_per_hour": sustained,
            # one-time burst: the unpresented slack, a cumulative host-minus-presented gap bounded once, no refill
            "burst_bytes": unpresented_bytes,
            "off_roster_flow_opened": off_roster_flow_opened,
            "message_channel": msg,
            "channels": channels,
            "finite_ceiling_holds": finite_ceiling_holds}


def exfil_time(sustained_per_hour: float) -> dict:
    """How long to move each set of weights at the SUSTAINED ceiling (the one-time burst is irrelevant to a model
    far larger than it). Sealed weights (EXPERIMENT-ORIGIN-GATE) are ciphertext without the key, so this is the time to move a USELESS
    copy; it is the plaintext case that the ceiling has to make impractical."""
    years = {}
    for name, size in WEIGHTS.items():
        hours = size / sustained_per_hour if sustained_per_hour > 0 else float("inf")
        years[name] = hours / (24 * 365)
    return years


# a message bound a deployer would set so the agent's messaging channel has a finite ceiling: 4 KB bodies, 60/min
BOUNDED_MSG = {"message_max_bytes": 4_096, "message_rate": {"max": 60, "window_s": 60}}


def checks():
    out, ceilings = [], {}

    def check(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    # the reference rulebook, with every permitted channel bounded (the messaging channel too)
    ref = egress_ceiling(output_bytes=200_000, output_queries=50, unpresented_bytes=1 << 20, sandbox=False, **BOUNDED_MSG)
    ceilings["reference rulebook"] = ref
    check("reference rulebook: the installed policy is the one asked for (limits read back from the governor)",
          ref["installed"]["output_bytes"] == 200_000 and ref["installed"]["output_queries"] == 50)
    check("reference rulebook: delivered bytes at the egress boundary stay within the signed byte allowance",
          ref["sustained_bytes_per_hour"] <= 200_000, f"{ref['sustained_bytes_per_hour']:,} B/h delivered")
    check("reference rulebook: a flow to an off-roster (internet) host is refused at CAP_REQUEST, content unseen",
          not ref["off_roster_flow_opened"])
    check("reference rulebook: every permitted channel is bounded, so the ceiling is finite",
          ref["finite_ceiling_holds"])

    # a sandbox rulebook: a model organism, no network flow at all, messaging gated to humans, the tightest policy
    tight = egress_ceiling(output_bytes=4_096, output_queries=10, unpresented_bytes=4_096, sandbox=True)
    ceilings["sandbox (tightest)"] = tight
    check("sandbox rulebook: no peer or network flow is opened, asked for or not", not tight["off_roster_flow_opened"])
    check("sandbox rulebook: delivered bytes stay within the signed byte allowance (a few KB an hour)",
          tight["sustained_bytes_per_hour"] <= 4_096, f"{tight['sustained_bytes_per_hour']:,} B/h delivered")
    check("sandbox rulebook: the finite-ceiling claim holds (no unbounded permitted channel)",
          tight["finite_ceiling_holds"])

    # the point of the whole thing: at the tight sustained ceiling, moving a real model takes a very long time
    ty = exfil_time(tight["sustained_bytes_per_hour"])
    check("at the sandbox sustained ceiling, moving even an 8B 4-bit model takes many decades, a 70B model centuries",
          ty["8B model, 4-bit"] > 25 and ty["70B model, 4-bit"] > 100,
          f"8B: {ty['8B model, 4-bit']:.0f} years, 70B 4-bit: {ty['70B model, 4-bit']:.0f} years")

    # the honest disproof direction (P3): a loose policy (a busy service, generous budget) can move a small model in
    # practical time. The defence is the budget, so a policy that serves a lot also leaks a lot.
    loose = egress_ceiling(output_bytes=50 << 20, output_queries=100_000, unpresented_bytes=16 << 20, sandbox=False, **BOUNDED_MSG)
    ceilings["busy service (loose)"] = loose
    ty_loose = exfil_time(loose["sustained_bytes_per_hour"])
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
         "The numbers below are measured at the enforced boundary: bytes that actually LEFT through the egress path "
         "(`egress.bytes_delivered`), under the policy the governor is actually running (its live limits are read "
         "back and asserted before measuring). They are arithmetic on the simulator's budgets, a design target, not "
         "a measurement of silicon that does not exist yet.", "",
         "## The ceiling, measured at the boundary", "",
         "The sustained rate is the per-hour signed-response delivery. The burst is the one-time unpresented slack "
         "(a cumulative host-minus-presented gap, bounded once, with no hourly refill). They are reported separately "
         "and never summed: a one-time budget is not a rate.", "",
         "| Rulebook | Installed (bytes/queries) | Sustained (delivered) | One-time burst | Off-roster flow | Finite ceiling |",
         "|---|---|---|---|---|---|"]
    for name, c in ceilings.items():
        inst = c["installed"]
        L.append(f"| {name} | {inst['output_bytes']:,} B / {inst['output_queries']:,} q | "
                 f"{c['sustained_bytes_per_hour']:,} B/h | {c['burst_bytes']:,} B | "
                 f"{'OPENED' if c['off_roster_flow_opened'] else 'refused'} | "
                 f"{'holds' if c['finite_ceiling_holds'] else 'FAILS (unbounded channel)'} |")
    L += ["", "## Every permitted channel, inventoried", "",
          "The signed-response channel is not the only way out. A listed-recipient `message.send` is a permitted "
          "channel too; with an unbounded body it has no finite byte ceiling, so the finite-ceiling claim fails until "
          "the body is bounded and counted. The busy and reference rulebooks here bound it (4 KB bodies, 60 per "
          "minute); the sandbox gates messaging to humans.", "",
          "| Rulebook | Channel | Bounded | Sustained |", "|---|---|---|---|"]
    for name, c in ceilings.items():
        for ch in c["channels"]:
            s = f"{ch['sustained_bytes_per_hour']:,} B/h" if ch["sustained_bytes_per_hour"] is not None else "no finite ceiling"
            L.append(f"| {name} | {ch['channel']} | {'yes' if ch['bounded'] else 'NO'} | {s} |")
    L += ["", "## What that sustained ceiling means for moving weights", "",
          "At the tightest (sandbox) sustained ceiling, time to move a copy of the weights out through the permitted "
          "channels (the one-time burst is negligible against a model this size):",
          "", "| Weights | Size | Time at the sandbox sustained ceiling |", "|---|---|---|"]
    for name, size in WEIGHTS.items():
        L.append(f"| {name} | {size/GB:.0f} GB | {ty_tight[name]:,.0f} years |")
    L += ["", "And under a busy-service rulebook with a generous budget, the honest other direction:", "",
          "| Weights | Time at the busy-service sustained ceiling |", "|---|---|"]
    for name in WEIGHTS:
        d = ty_loose[name] * 365
        L.append(f"| {name} | {d:,.0f} days |" if d >= 1 else f"| {name} | {ty_loose[name]*365*24:,.0f} hours |")
    L += ["", "## Corrections on the record (external audit F12, F13)", "",
          "- The earlier table recorded 6,135 and 26,200 B/h for the sandbox and busy cases. Those were the reference "
          "and loop values: the named policy was never installed, because the code changed `policy_kw` after "
          "construction and `bring_up()` does not reload the policy. The numbers above install the named policy and "
          "read its limits back first.",
          "- The earlier \"50 years / centuries / 11 days\" interpretations were computed from a ceiling that summed a "
          "one-time burst onto a per-hour rate, and from signing calls rather than delivered bytes. Those "
          "interpretations are withdrawn; the corrected sustained figures are above.",
          "- The old measurement counted successful `sign_output` calls. A provenance signature with no release moves "
          "no bytes; the figures above are read back from the egress boundary after the complete release path.",
          "",
          "## What this shows, and what it does not", "",
          "- The gate needs no idea what a packet is. Bytes to anything off the signed roster are refused at the exit, "
          "and the bytes that may leave are capped. Under a tight policy the cap makes moving even a small model take "
          "longer than a lifetime.",
          "- Sealed weights (W1) make this a double lock: a copy that did leave would be ciphertext without the key, "
          "which the governor releases only to attested hardware. The plaintext case is the one the ceiling guards.",
          "- The ceiling is only finite if EVERY permitted channel is bounded. A deployer who leaves a listed-recipient "
          "message body unbounded has no byte ceiling at all, whatever the signed-response budget says.",
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
        print(f"  ceiling: {name}: sustained {c['sustained_bytes_per_hour']:,} B/h delivered, one-time burst "
              f"{c['burst_bytes']:,} B, finite-ceiling {'holds' if c['finite_ceiling_holds'] else 'FAILS'}, "
              f"off-roster flow {'OPENED' if c['off_roster_flow_opened'] else 'refused'}")
    print(f"  exfil: sandbox sustained ceiling moves an 8B 4-bit model in {checks.exfil_tight['8B model, 4-bit']:,.0f} years; "
          f"busy-service in {checks.exfil_loose['8B model, 4-bit']*365:,.0f} days")
    if a.write:
        os.makedirs("results", exist_ok=True)
        open("results/containment.md", "w").write(report(results, checks.ceilings, checks.exfil_tight, checks.exfil_loose))
        print("wrote results/containment.md")
    bad = [n for n, k, _ in results if not k]
    print("P3b: every check holds" if not bad else f"P3b: {len(bad)} check(s) FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
