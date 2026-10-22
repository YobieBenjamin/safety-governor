# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""CONTRACT-GOVERNOR-OVERHEAD-BOUNDED: the governor's work is zero per token, one lookup per transfer, one signature per
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
    "ticket_mac": 20e-6,       # a release ticket: same firmware path as a ticket; its MAC runs on the hash engine
    "fabric_mac": 2e-6,        # one pairwise MAC per recipient (hash engine; firmware only queues it)
}
OTBN_P384_SIGN_CYCLES = 1_697_985          # opentitan.org, OTBN performance table, ECDSA-P384 sign, constant time
OTBN_CLOCK_HZ = 100e6                      # Earl Grey core clock
SIGN_S = OTBN_P384_SIGN_CYCLES / OTBN_CLOCK_HZ    # 17 ms
BATCH_WINDOW_S = 0.05                      # docs/04 §9: one signature per window over a Merkle root of the records
SLOTS_PER_CHIP = 8                         # an HGX baseboard: the engine serves eight GPUs
# Post-quantum path (C3). ML-DSA is not in Earl Grey silicon and no OTBN-specific measured cycle count is in the
# repo (docs/04 §7, docs/08, docs/18 §9: a future OpenTitan release or a software implementation, cost measured in
# Phase 2). The stand-in is the pqm4 project's ML-DSA-65 (Dilithium3) sign on a Cortex-M4, about 10 million
# cycles on average.
#
# UNVERIFIED PLACEHOLDER: the 10,000,000 figure has NO checked source at revision 1 (no web access). It is from
# memory of the pqm4 tables and MUST be re-checked against the current pqm4 release, with the M4->OTBN scaling,
# before the result is relied on. Every hybrid verdict below is conditional on it.
# Scaling assumption (UNVERIFIED, 1.0x): the M4 count is assumed equal on the OTBN-class engine. This is an
# assumption, not a measurement, and is to be measured in Phase 2; a software SHAKE on OTBN could make it
# optimistic. Signing is rejection sampling, so the figure is a mean; its tail is covered by HYBRID_PESSIMISM in
# the tests (a 2x factor standing in for it -- an assumption, not a measurement), not by this constant.
MLDSA65_SIGN_CYCLES = 10_000_000           # UNVERIFIED placeholder: Cortex-M4 pqm4 ML-DSA-65 sign, mean; no checked source
MLDSA65_COST_SOURCED = False               # no checked source at revision 1; re-check pqm4 + M4->OTBN scaling before relying
MLDSA65_SIGN_S = MLDSA65_SIGN_CYCLES / OTBN_CLOCK_HZ    # 100 ms
HYBRID_SIGN_S = SIGN_S + MLDSA65_SIGN_S    # both signatures per batch, one engine: 117 ms
HYBRID_BATCH_WINDOW_S = 0.25               # window, under 1 s, that keeps the single engine under 100 percent; must exceed HYBRID_SIGN_S
GPU_SECONDS_PER_TOKEN = 1 / 2000.0         # a modest 2,000 tokens per second per GPU
# ASSUMPTION (stated, not measured): an HMAC-SHA256 over a short message on the hash engine takes about 2 microseconds,
# and a P-384 verify costs about what a sign does (17 ms on OTBN). Phase 2 measurement replaces both.
MAC_S = 2e-6
VERIFY_S = SIGN_S


def run(tier: str = "rack", gpus: int = 4, requests: int = 1000, tokens_per_request: int = 500, actions: int = 50,
        slots_per_chip: int = SLOTS_PER_CHIP, batch_window_s: float = BATCH_WINDOW_S,
        hybrid_window_s: float = HYBRID_BATCH_WINDOW_S, hybrid_sign_s: float = HYBRID_SIGN_S) -> dict:
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
    hybrid_windows = gpu_s / hybrid_window_s if hybrid_window_s > 0 else float("inf")
    hybrid_batched = min(sig_unbatched, hybrid_windows)
    util = lambda n: 100.0 * n * SIGN_S / gpu_s if gpu_s else 0.0
    return {"tier": tier, "tokens": total_tokens, "ops": ops, "responses": responses,
            "gpu_seconds": gpu_s, "firmware_seconds": firmware_s,
            "firmware_overhead_pct": 100.0 * firmware_s / gpu_s if gpu_s else 0.0,
            "signatures_unbatched": sig_unbatched, "signatures_batched": sig_batched,
            "engine_utilization_unbatched_pct": util(sig_unbatched), "engine_utilization_pct": util(sig_batched),
            "record_latency_s": batch_window_s + SIGN_S,
            "hybrid_signatures_batched": hybrid_batched,
            "hybrid_engine_utilization_pct": 100.0 * hybrid_batched * hybrid_sign_s / gpu_s if gpu_s else 0.0,
            "hybrid_engine_utilization_at_base_window_pct": 100.0 * sig_batched * hybrid_sign_s / gpu_s if gpu_s else 0.0,
            "hybrid_record_latency_s": hybrid_window_s + hybrid_sign_s,
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
        verifications += 1                       # the egress checked exactly one release ticket for this response
    for j in range(actions):
        rack.request(node, "payments.transfer", {"amount": 1, "currency": "USD", "destination": "acct-1"})
    ops = dict(node.governor.ops)
    gpu_s = total_tokens * GPU_SECONDS_PER_TOKEN
    firmware_s = sum(COST_S.get(k, 0.0) * v for k, v in ops.items() if k != "sign")
    record_sigs = ops.get("sign", 0)                 # one provenance record per response (rack tier)
    # Adversarial audit 3: release tickets are MACed under the key the governor shares with its own egress (one per
    # response, on the hash engine); only action tickets are P-384 signatures on the signing engine.
    release_tickets = ops.get("ticket_mac", 0)
    action_tickets = ops.get("ticket", 0)

    # the engine serves every slot on the chip, each producing the same stream
    record_sigs_chip = record_sigs * slots_per_chip
    action_sigs_chip = action_tickets * slots_per_chip
    release_macs_chip = release_tickets * slots_per_chip
    windows = gpu_s / batch_window_s if batch_window_s > 0 else float("inf")
    records_batched = min(record_sigs_chip, windows)             # records collapse to one signature per window
    util = lambda n: 100.0 * n * SIGN_S / gpu_s if gpu_s else 0.0
    mac_util = 100.0 * release_macs_chip * MAC_S / gpu_s if gpu_s else 0.0
    return {"tier": tier, "responses": responses, "actions": actions, "tokens": total_tokens, "gpu_seconds": gpu_s,
            "ops": ops, "firmware_seconds": firmware_s,
            "signatures": record_sigs, "tickets": release_tickets + action_tickets, "release_tickets": release_tickets,
            "action_tickets": action_tickets, "verifications": verifications, "releases": delivered,
            "slots_per_chip": slots_per_chip,
            "records_batched": records_batched, "release_ticket_signatures": 0, "release_ticket_macs": release_macs_chip,
            "engine_utilization_records_only_pct": util(records_batched),
            # the full path as built: batched records, signed action tickets, MACed release tickets (hash engine)
            "engine_utilization_full_path_pct": util(records_batched + action_sigs_chip) + mac_util,
            # the design audit 3 measured, kept for comparison: every release ticket a P-384 signature
            "engine_utilization_signed_release_pct": util(records_batched + action_sigs_chip + release_macs_chip)}


def roll_call_load(members: int, beacons_per_s: float = 1.0, fabric_auth: str = "mac") -> dict:
    """The loop roll call (adversarial audit 3, catalog row 19): each beacon, every member sends one LOOP_REPORT to
    every other member and checks the reports of all the others, and every member checks the heartbeat's two
    authority signatures. ``fabric_auth`` is "sign" (one P-384 signature per report, verified by every receiver: the
    design audit 3 priced) or "mac" (pairwise HMAC keys from an attested X25519 exchange at roster formation, as
    govsim now does). Output: the share of one signing engine per member chip."""
    hb_verifies = 2 * beacons_per_s * VERIFY_S                      # the heartbeat's 2-of-3 quorum, every member
    if fabric_auth == "sign":
        per_s = beacons_per_s * (SIGN_S + (members - 1) * VERIFY_S) + hb_verifies
        hash_s = 0.0
    else:
        per_s = hb_verifies
        hash_s = beacons_per_s * 2 * (members - 1) * MAC_S          # MAC every outgoing copy, check every incoming one
    return {"members": members, "fabric_auth": fabric_auth, "engine_pct": 100.0 * per_s,
            "hash_engine_pct": 100.0 * hash_s}


def measured_fabric_auth(members: int = 4) -> dict:
    """Run one beacon round in the model and count how the roster's fabric messages were authenticated."""
    rack = build_rack(members, "rack")
    rack.bring_up()
    for n in rack.nodes:
        n.governor.ops.clear()
    rack.heartbeat()
    ops = [dict(n.governor.ops) for n in rack.nodes]
    return {"fabric_sign": sum(o.get("fabric_sign", 0) for o in ops), "fabric_mac": sum(o.get("fabric_mac", 0) for o in ops)}


def main() -> None:
    print(f"signature: ECDSA P-384 on OTBN at 100 MHz = {OTBN_P384_SIGN_CYCLES:,} cycles = {SIGN_S*1e3:.1f} ms "
          f"(OpenTitan's published figure); batch window {BATCH_WINDOW_S*1e3:.0f} ms; {SLOTS_PER_CHIP} slots per governor chip")
    for tier in ("rack", "integrated"):
        r = run(tier)
        print(f"{tier:11s} tokens={r['tokens']:>9,}  firmware={r['firmware_seconds']*1e3:7.1f} ms of gpu={r['gpu_seconds']:6.1f} s "
              f"({r['firmware_overhead_pct']:.3f}%)  engine: {r['engine_utilization_unbatched_pct']:.0f}% unbatched -> "
              f"{r['engine_utilization_pct']:.0f}% batched  record latency <= {r['record_latency_s']*1e3:.0f} ms  ops={r['ops']}")
    h = run("rack")
    print(f"hybrid (P-384 + ML-DSA-65, both per batch): {HYBRID_SIGN_S*1e3:.0f} ms per batch (ML-DSA-65 {MLDSA65_SIGN_CYCLES:,} cycles, "
          f"Cortex-M4 pqm4 figure, {'UNVERIFIED placeholder -- no checked source at revision 1' if not MLDSA65_COST_SOURCED else 'sourced'} -- re-check before relying; "
          f"OTBN 1.0x assumed); engine {h['hybrid_engine_utilization_at_base_window_pct']:.0f}% at the "
          f"{BATCH_WINDOW_S*1e3:.0f} ms window (cannot keep up) -> {h['hybrid_engine_utilization_pct']:.0f}% at a {HYBRID_BATCH_WINDOW_S*1e3:.0f} ms window (under 1 s); "
          f"record latency <= {h['hybrid_record_latency_s']*1e3:.0f} ms. "
          f"Counted is signing only (tickets are a 20 us firmware path; verification and session setup are not on the engine), "
          f"so 'no second engine' holds for the signing workload, not the chip as a whole. "
          f"Disproof did not hold -- a window under 1 s keeps the one engine under 100 percent -- but ONLY conditional on the unverified ML-DSA figure.")
    short = run("rack", requests=1000, tokens_per_request=100)
    print(f"short responses (100 tokens): engine {short['engine_utilization_unbatched_pct']:.0f}% unbatched, which cannot keep up, "
          f"-> {short['engine_utilization_pct']:.0f}% batched (why the spec batches, docs/04 §9)")
    print("full request-to-effect path (F23, adversarial audit 3): every response gets a release ticket; it is now MACed "
          "for the node's own egress instead of signed, and priced here with the records and action tickets:")
    for toks in (500, 100):
        f = run_full_path("rack", responses=100, tokens_per_response=toks, actions=0)
        over = "" if f["engine_utilization_full_path_pct"] <= 100 else "  OVER ONE ENGINE"
        print(f"  {toks:>3}-token responses: full path {f['engine_utilization_full_path_pct']:.0f}%{over} with MACed release "
              f"tickets (was {f['engine_utilization_signed_release_pct']:.0f}% with a signature per release ticket)  "
              f"(signs={f['signatures']}, release MACs={f['release_tickets']}, releases={f['releases']})")
    head = 50.0 - run_full_path("rack", responses=100, tokens_per_response=100, actions=0)["engine_utilization_full_path_pct"]
    cap = head / 100.0 / SIGN_S
    print(f"  signed action tickets that fit under half an engine beside 100-token serving: about {cap:.0f} per second per "
          f"governor chip ({cap / SLOTS_PER_CHIP:.1f} per GPU at {SLOTS_PER_CHIP} GPUs per chip)")
    print("loop roll call per member chip (one beacon a second; P-384 verify priced as a sign):")
    for n in (9, 72):
        a, b = roll_call_load(n, fabric_auth="sign"), roll_call_load(n, fabric_auth="mac")
        print(f"  {n:>2} members: signed fabric {a['engine_pct']:.0f}% of one engine -> pairwise MACs {b['engine_pct']:.0f}% "
              f"(+{b['hash_engine_pct']:.2f}% of the hash engine)")


if __name__ == "__main__":
    main()
