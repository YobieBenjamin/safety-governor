# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""H9: the governor's work is zero per token, one lookup per transfer, one signature per
response. This module counts operations in the functional model for a reference workload
and prices them with the figures in ``docs/04-specification.md`` §9. It is a model, not a
measurement; the Phase 2 measurement on real hardware replaces it.

Three numbers come out, because they answer three different questions:

* ``firmware_overhead_pct``: firmware time (mailbox, tickets, heartbeats, fabric) as a share
  of GPU time. This is the only governor work that sits on an action path.
* ``engine_utilization_pct``: how busy the hash-and-sign engine is. It runs beside the GPU,
  not in front of it, so it must keep up; it does not slow the GPU down. Signatures are priced
  at OpenTitan's published OTBN cycle count for a constant-time ECDSA P-384 sign, at Earl
  Grey's 100 MHz, and the engine is shared by every GPU slot the governor chip serves.
* ``record_latency_s``: the most a response waits if the runtime insists on its provenance
  record before release: one batch window plus one signature.
"""
from __future__ import annotations

from .cluster import build_rack

COST_S = {
    "mailbox": 20e-6,          # firmware path, auto rule
    "ticket": 20e-6,
    "switch_program": 1e-3,    # one management-bus write per port change
    "fabric_msg": 5e-6,
    "attest": 2e-3,
    "heartbeat": 5e-6,
    "shared_reserve": 10e-6,
    "output_bytes": 0.0,       # the hash runs at line rate; no governor time per byte
}
OTBN_P384_SIGN_CYCLES = 1_697_985          # opentitan.org, OTBN performance table, ECDSA-P384 sign, constant time
OTBN_CLOCK_HZ = 100e6                      # Earl Grey core clock
SIGN_S = OTBN_P384_SIGN_CYCLES / OTBN_CLOCK_HZ    # 17 ms
BATCH_WINDOW_S = 0.05                      # docs/04 §9: one signature per window over a Merkle root of the records
SLOTS_PER_CHIP = 8                         # an HGX baseboard: the engine serves eight GPUs
GPU_SECONDS_PER_TOKEN = 1 / 2000.0         # a modest 2,000 tokens per second per GPU


def run(tier: str = "rack", gpus: int = 4, requests: int = 1000, tokens_per_request: int = 500, actions: int = 50,
        slots_per_chip: int = SLOTS_PER_CHIP, batch_window_s: float = BATCH_WINDOW_S) -> dict:
    """Count the governor's operations for one GPU's workload and price them."""
    rack = build_rack(gpus, tier, policy_kw={"output_queries": 10 ** 9, "output_bytes": 10 ** 12})
    rack.bring_up()
    for n in rack.nodes:
        n.governor.ops.clear()
    node = rack.nodes[0]
    total_tokens = 0
    for i in range(requests):
        total_tokens += node.gpu.run_tokens(tokens_per_request)
        node.gpu.emit("s", b"x" * 64)
        rack.sign_output(node, "s", b"x" * 64)
        if i % 5 == 0:
            node.gpu.transfer("nvswitch", rack.nodes[1].gpu.chip_id, "out", 1 << 20)
        if i % 20 == 0:
            rack.heartbeat()
    for _ in range(actions):
        rack.request(node, "payments.transfer", {"amount": 1, "currency": "USD", "destination": "acct-1"})
    ops = dict(node.governor.ops)
    gpu_s = total_tokens * GPU_SECONDS_PER_TOKEN            # the GPU is busy throughout, so this is also wall time
    firmware_s = sum(COST_S.get(k, 0.0) * v for k, v in ops.items() if k != "sign")
    responses = ops.get("sign", 0)
    # the engine is shared: every slot on the chip produces the same stream of responses
    sig_unbatched = responses * slots_per_chip
    windows = gpu_s / batch_window_s if batch_window_s > 0 else float("inf")
    sig_batched = min(sig_unbatched, windows)
    util = lambda n: 100.0 * n * SIGN_S / gpu_s if gpu_s else 0.0
    return {"tier": tier, "tokens": total_tokens, "ops": ops, "responses": responses,
            "gpu_seconds": gpu_s, "firmware_seconds": firmware_s,
            "firmware_overhead_pct": 100.0 * firmware_s / gpu_s if gpu_s else 0.0,
            "signatures_unbatched": sig_unbatched, "signatures_batched": sig_batched,
            "engine_utilization_unbatched_pct": util(sig_unbatched), "engine_utilization_pct": util(sig_batched),
            "record_latency_s": batch_window_s + SIGN_S,
            "per_token_ops": (ops.get("mailbox", 0) + ops.get("ticket", 0) + ops.get("sign", 0)) / max(1, total_tokens)}


def run_full_path(tier: str = "rack", gpus: int = 2, responses: int = 100, tokens_per_response: int = 500,
                  actions: int = 0, slots_per_chip: int = SLOTS_PER_CHIP, batch_window_s: float = BATCH_WINDOW_S) -> dict:
    """F23: price the engine over the REAL request-to-effect path, not just the batched provenance records.

    ``run()`` above calls ``sign_output()`` and prices the batched record signatures, but it never follows the
    response-release path. On that path the verified runtime requests a release ticket for EVERY response, and the
    governor signs every ticket (counted in ``ops["ticket"]``, not ``ops["sign"]``). Those per-response release
    tickets are per-item capabilities: each independently authorizes one response to leave, so they cannot be
    collapsed under one Merkle root the way the records are. This function drives the full path and prices both the
    batched records AND the unbatched release-ticket signatures, so the engine load is the honest one.
    """
    rack = build_rack(gpus, tier, policy_kw={"output_queries": 10 ** 9, "output_bytes": 10 ** 12})
    rack.bring_up()
    for n in rack.nodes:
        n.governor.ops.clear()
    node = rack.nodes[0]
    total_tokens, delivered, verifications = 0, 0, 0
    for i in range(responses):
        total_tokens += node.gpu.run_tokens(tokens_per_response)
        res = rack.respond(node, "bench", b"x" * 64, observer={"hazard_class": "none", "risk": 0.1},
                           escrow=True, response_id=f"resp-{i}")
        if res["released"][0]:
            delivered += 1
        verifications += 1                       # the egress verified exactly one release ticket for this response
    for j in range(actions):
        rack.request(node, "payments.transfer", {"amount": 1, "currency": "USD", "destination": "acct-1"})
    ops = dict(node.governor.ops)
    gpu_s = total_tokens * GPU_SECONDS_PER_TOKEN
    firmware_s = sum(COST_S.get(k, 0.0) * v for k, v in ops.items() if k != "sign")
    record_sigs = ops.get("sign", 0)                 # one provenance record per response (rack tier)
    release_tickets = ops.get("ticket", 0) - actions  # the per-response release tickets (minted on response.release)
    action_tickets = actions

    # the engine serves every slot on the chip, each producing the same stream
    record_sigs_chip = record_sigs * slots_per_chip
    ticket_sigs_chip = ops.get("ticket", 0) * slots_per_chip      # release + action tickets, each a full signature
    windows = gpu_s / batch_window_s if batch_window_s > 0 else float("inf")
    records_batched = min(record_sigs_chip, windows)             # records collapse to one signature per window
    util = lambda n: 100.0 * n * SIGN_S / gpu_s if gpu_s else 0.0
    return {"tier": tier, "responses": responses, "actions": actions, "tokens": total_tokens, "gpu_seconds": gpu_s,
            "ops": ops, "firmware_seconds": firmware_s,
            "signatures": record_sigs, "tickets": ops.get("ticket", 0), "release_tickets": release_tickets,
            "action_tickets": action_tickets, "verifications": verifications, "releases": delivered,
            "slots_per_chip": slots_per_chip,
            "records_batched": records_batched, "release_ticket_signatures": ticket_sigs_chip,
            # the old (incomplete) figure: batched provenance records only
            "engine_utilization_records_only_pct": util(records_batched),
            # the honest figure: batched records PLUS every per-item release/action ticket signature
            "engine_utilization_full_path_pct": util(records_batched + ticket_sigs_chip)}


def main() -> None:
    print(f"signature: ECDSA P-384 on OTBN at 100 MHz = {OTBN_P384_SIGN_CYCLES:,} cycles = {SIGN_S*1e3:.1f} ms "
          f"(OpenTitan's published figure); batch window {BATCH_WINDOW_S*1e3:.0f} ms; {SLOTS_PER_CHIP} slots per governor chip")
    for tier in ("rack", "integrated"):
        r = run(tier)
        print(f"{tier:11s} tokens={r['tokens']:>9,}  firmware={r['firmware_seconds']*1e3:7.1f} ms of gpu={r['gpu_seconds']:6.1f} s "
              f"({r['firmware_overhead_pct']:.3f}%)  engine: {r['engine_utilization_unbatched_pct']:.0f}% unbatched -> "
              f"{r['engine_utilization_pct']:.0f}% batched  record latency <= {r['record_latency_s']*1e3:.0f} ms  ops={r['ops']}")
    short = run("rack", requests=1000, tokens_per_request=100)
    print(f"short responses (100 tokens): engine {short['engine_utilization_unbatched_pct']:.0f}% unbatched, which cannot keep up, "
          f"-> {short['engine_utilization_pct']:.0f}% batched (why the spec batches, docs/04 §9)")
    print("full request-to-effect path (F23): the real path requests and signs a release ticket per response; those "
          "per-item signatures are NOT batchable like the records, so they must be priced too:")
    for toks in (500, 100):
        f = run_full_path("rack", responses=100, tokens_per_response=toks, actions=0)
        over = "" if f["engine_utilization_full_path_pct"] <= 100 else "  OVER ONE ENGINE"
        print(f"  {toks:>3}-token responses: records-only {f['engine_utilization_records_only_pct']:.0f}% -> "
              f"full path (incl. release tickets) {f['engine_utilization_full_path_pct']:.0f}%{over}  "
              f"(signs={f['signatures']}, tickets={f['tickets']}, releases={f['releases']})")


if __name__ == "__main__":
    main()
