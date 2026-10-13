"""H9: the governor's work is zero per token, one lookup per transfer, one signature per
response. This module counts operations in the functional model for a reference workload
and converts them to time with the cost figures in ``docs/04-specification.md`` §9. It is a
model, not a measurement; the Phase 2 measurement on real hardware replaces it.
"""
from __future__ import annotations

from .cluster import build_rack

COST_S = {
    "mailbox": 20e-6,          # firmware path, auto rule
    "ticket": 20e-6,
    "sign": 1e-3,              # one ECDSA signature per response, budgeted at 1 ms on an OTBN-class coprocessor (the spec batches records; this charges the worst case)
    "switch_program": 1e-3,    # one management-bus write per port change
    "fabric_msg": 5e-6,
    "attest": 2e-3,
    "heartbeat": 5e-6,
    "shared_reserve": 10e-6,
    "output_bytes": 0.0,       # the hash runs at line rate; no governor time per byte
}
GPU_SECONDS_PER_TOKEN = 1 / 2000.0      # a modest 2,000 tokens per second per GPU


def run(tier: str = "rack", gpus: int = 4, requests: int = 1000, tokens_per_request: int = 500, actions: int = 50,
        concurrent_sequences: int = 1) -> dict:
    """Count the governor's operations for a workload and price them.

    ``concurrent_sequences`` models the batching in ``docs/04-specification.md`` §9: an
    inference server that serves N sequences at once completes up to N responses inside one
    batch window, and the governor signs one Merkle root for all of them. The default of 1 is
    the worst case, one signature per response, which is what the functional model counts.
    """
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
        rack.request(node, "payments.transfer", {"amount": 1, "currency": "USD", "destination": "a"})
    ops = dict(node.governor.ops)
    priced = dict(ops)
    priced["sign"] = -(-ops.get("sign", 0) // max(1, concurrent_sequences))   # ceil: one signature per batch of responses
    governor_s = sum(COST_S.get(k, 0.0) * v for k, v in priced.items())
    gpu_s = total_tokens * GPU_SECONDS_PER_TOKEN
    return {"tier": tier, "tokens": total_tokens, "ops": ops, "signatures": priced["sign"],
            "governor_seconds": governor_s, "gpu_seconds": gpu_s,
            "overhead_pct": 100.0 * governor_s / gpu_s if gpu_s else 0.0,
            "per_token_ops": (ops.get("mailbox", 0) + ops.get("ticket", 0) + ops.get("sign", 0)) / max(1, total_tokens)}


def main() -> None:
    for tier in ("rack", "integrated"):
        r = run(tier)
        print(f"{tier:11s} tokens={r['tokens']:>9,}  governor={r['governor_seconds']*1e3:8.1f} ms  gpu={r['gpu_seconds']:8.1f} s  overhead={r['overhead_pct']:.3f}%  ops={r['ops']}")
    short = run("rack", requests=1000, tokens_per_request=100)
    batched = run("rack", requests=1000, tokens_per_request=100, concurrent_sequences=16)
    print(f"short responses (100 tokens), one signature each: overhead={short['overhead_pct']:.3f}%; "
          f"16 sequences batched per window: overhead={batched['overhead_pct']:.3f}%  (why the spec batches, docs/04 §9)")


if __name__ == "__main__":
    main()
