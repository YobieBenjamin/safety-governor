# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The sweep: one probe per hypothesis, run against every tier, written to results/report.md.

A probe returns ``"pass"`` when the hypothesis held, ``"gap"`` when it failed in the way the
design predicts for that tier (the recorded residual), and ``"FAIL"`` when it failed in a way
the design does not predict. The full test suite in ``tests/`` is the detailed version; this
is the matrix a reader can check at a glance.
"""
from __future__ import annotations

import datetime as _dt
import os
import threading

from . import reasons
from .bench import run as bench_run
from .bench import run_full_path as bench_full_path
from .cluster import PROTECTED_SITES, build_rack
from .crypto import SigningKey
from .policy import sign_policy

MB = 1 << 20
TIERS = ("rack", "board", "integrated")


def _pay(rack, node, amount, governor=None):
    return rack.request(node, "payments.transfer", {"amount": amount, "currency": "USD", "destination": "acct-1"}, governor=governor)


def probe_h0(rack):
    node = rack.nodes[0]
    t = _pay(rack, node, 500)["ticket"]
    ep = rack.endpoints["payment-switch"]
    p = {"amount": 500, "currency": "USD", "destination": "acct-1"}
    ok1 = ep.execute(t, "payments.transfer", p)[0]
    replay = ep.execute(t, "payments.transfer", p)[1] == reasons.TICKET_REPLAY
    forged = ep.execute(SigningKey.generate().sign(t["payload"]), "payments.transfer", p)[1] == reasons.TICKET_BAD_SIGNATURE
    altered = ep.execute(_pay(rack, node, 500)["ticket"], "payments.transfer", {**p, "destination": "x"})[1] == reasons.TICKET_PARAMS_MISMATCH
    return "pass" if (ok1 and replay and forged and altered) else "FAIL"


def probe_h1(rack):
    node = rack.nodes[0]
    old = node.governor.fingerprint
    node.gpu.firmware_digest = "patched"
    a = not rack.attest(node)["gpu"]["ok"]
    node.gpu.firmware_digest = "nvidia-gpu-fw-2026.10"
    rack.attest(node)
    rack.load_model(node, rack.manifest("other", 1))
    b = node.governor.fingerprint != old
    return "pass" if a and b else "FAIL"


def probe_h2_link(rack):
    node = rack.nodes[0]
    peer = rack.nodes[1].gpu.chip_id
    ok_peer = node.gpu.transfer("nvswitch", peer, "out", MB)[0]
    blocked = not node.gpu.transfer("nvswitch", "gpu-stranger", "out", MB)[0]
    bricked = not node.gpu.transfer("jtag", "x", "out", 1)[0]
    if rack.tier == "board":
        return "gap" if (ok_peer and not blocked and bricked) else "FAIL"
    return "pass" if (ok_peer and blocked and bricked) else "FAIL"


def probe_h2_descriptor(rack):
    """Two roster members exchanging bytes the buffer policy would not allow: the weights, over the
    copy engine. The rack and board tiers have no checker in the path (EP_UNCHECKED: the recorded gap).
    The integrated tier's checker is keyed per buffer class: weights are refused and logged
    (EP_BUFFER_CLASS) while activations to the same peer pass, and a stranger gets nothing."""
    node, other = rack.nodes[0], rack.nodes[1]
    peer = other.gpu.chip_id
    ok_w, why_w = node.gpu.transfer("copy_engine", peer, "out", MB, buffer_class="weights")
    if rack.tier != "integrated":
        return "gap" if (ok_w and why_w == reasons.EP_UNCHECKED) else "FAIL"
    ok_a, why_a = node.gpu.transfer("copy_engine", peer, "out", MB, buffer_class="activations")
    stranger_refused = not node.gpu.transfer("copy_engine", "gpu-stranger", "out", MB, buffer_class="activations")[0]
    logged = node.governor.log.has("switch.refused", switch="copy_engine", peer=peer, why=reasons.EP_BUFFER_CLASS, buffer_class="weights")
    return "pass" if (not ok_w and why_w == reasons.EP_BUFFER_CLASS and logged and ok_a and why_a == reasons.OK and stranger_refused) else "FAIL"


def probe_h3(rack):
    g = rack.nodes[0].governor
    weak = sign_policy(rack.make_policy_image(rack.policy_version + 1), rack.governance[:2])
    a = g.command("POLICY_PROPOSE", {"image": weak})["why"] == reasons.POLICY_QUORUM
    rack.change_epoch(rack.new_policy())
    old = sign_policy(rack.make_policy_image(1), rack.governance[:3])
    b = g.command("POLICY_PROPOSE", {"image": old})["why"] == reasons.POLICY_ROLLBACK
    return "pass" if a and b else "FAIL"


def probe_h4(rack):
    node = rack.nodes[0]
    r = rack.request(node, "payments.transfer", {"amount": 25_000, "currency": "USD", "destination": "a"}, labels={"risk_class": "reversible", "requirement": "auto"})
    return "pass" if r["why"] == reasons.GATE_HELD else "FAIL"


def probe_h5(rack):
    g = rack.nodes[0].governor
    g.raise_alarm("x", "model")
    a = g.command("ALARM_CLEAR", {}, SigningKey.generate().sign({"seq": 1, "code": "x"}))["why"] == reasons.ALARM_CLEAR_UNAUTHORIZED and "x" in g.alarms
    b = g.command("ALARM_CLEAR", {}, rack.approvers["alarms"][0].sign({"seq": 1, "code": "x", "type": "alarm_clear"}))["ok"] and "x" not in g.alarms
    return "pass" if a and b else "FAIL"


def probe_h6(rack):
    node = rack.nodes[0]
    r = rack.request_with_witness(node, "strike", {"target": [37.0, -122.0], "munition": "gbu-39"})
    rack.clock.advance(3)
    rack.heartbeat()
    ep = rack.endpoints["strike-guidance"]
    ep.sensors["nav_gnss"] = tuple(PROTECTED_SITES[0])
    ep.sensors["nav_inertial"] = tuple(PROTECTED_SITES[0])
    ok, why = ep.execute(r["ticket"], "strike", {"target": [37.0, -122.0], "munition": "gbu-39"})
    return "pass" if (not ok and why == reasons.ENDPOINT_TARGET_PROTECTED) else "FAIL"


def probe_h7(rack):
    g = rack.nodes[0].governor
    image = sign_policy(rack.make_policy_image(rack.policy_version + 1, drop_register_row="protected-sites"), rack.governance[:3])
    return "pass" if g.command("POLICY_PROPOSE", {"image": image})["why"] == reasons.POLICY_REGISTER_INCOMPLETE else "FAIL"


def probe_h8(rack):
    node = rack.nodes[0]
    g = node.governor
    r = rack.request(node, "payments.transfer", {"amount": 25_000, "currency": "USD", "destination": "a"})
    hid, rh = r["hold_id"], r["request_hash"]
    a = rack.approve(g, hid, rh, rack.approvers["payments.transfer.large"][0])["why"] == reasons.APPROVE_QUORUM_PENDING
    b = rack.approve(g, hid, rh, rack.approvers["payments.transfer.large"][1])["why"] == reasons.APPROVE_TOO_FAST
    rack.clock.advance(61)
    rack.heartbeat()
    c = rack.approve(g, hid, rh, rack.approvers["payments.transfer.large"][2])["ok"]
    d = g.log.has("approve.released", hold_id=hid)
    return "pass" if (a and b and c and d) else "FAIL"


def probe_h9(rack):
    r = bench_run(rack.tier, gpus=2, requests=100, tokens_per_request=500, actions=10)
    return "pass" if (r["firmware_overhead_pct"] < 1.0 and r["engine_utilization_pct"] < 50.0 and r["ops"]["sign"] == 100) else "FAIL"


def probe_h10(rack):
    node = rack.nodes[0]
    for i in range(50):
        rack.sign_output(node, f"s{i}", b"x")
    r = rack.sign_output(node, "s51", b"x")
    return "pass" if (r["why"] == reasons.GATE_OUTPUT_BUDGET and node.governor.state == "THROTTLE") else "FAIL"


def probe_h11(rack):
    rack.halt(rack.nodes[2].governor)
    t = rack.loop.propagate()
    a = not any(rack.running()) and t <= rack.policy["fabric"]["loop_bound_s"]
    rack.loop.repair()
    g = rack.nodes[0].governor
    b = rack.clear(g)["why"] == reasons.CLEAR_NO_NEIGHBOR_ACK
    rack.exchange_checkpoints()
    c = rack.clear(g)["ok"]
    # the jumpered case, on a fresh rack: wired around, governor 2's halt leaves the loop closed; the
    # beacon's roll call names it within two heartbeats and every governor opens the loop for real
    r2 = build_rack(4, rack.tier)
    r2.bring_up()
    g2 = r2.nodes[2].governor
    r2.loop.jumper(g2.chip_id)
    r2.halt(g2)
    r2.loop.propagate()
    attack = r2.loop.current() and r2.running() == [True, True, False, True]
    r2.heartbeat()
    r2.heartbeat()
    d = attack and not any(r2.running()) and not r2.loop.current() \
        and all(n.governor.alarms.get(reasons.LOOP_JUMPERED, {}).get("member") == g2.chip_id for n in r2.nodes) \
        and all(n.governor.log.has("loop.jumpered", member=g2.chip_id) for n in r2.nodes)
    return "pass" if (a and b and c and d) else "FAIL"


def probe_h12(rack):
    rogue = rack.rogue_governor()
    res = rogue.fabric_send("ALARM", {"code": "fake"})
    a = all(r["why"] == reasons.FABRIC_NOT_MEMBER for _, r in res)
    now = rack.clock.now()
    env = SigningKey.generate().sign({"type": "heartbeat", "seq": 10_000, "epoch": rack.epoch, "window_start": now - 1, "window_end": now + 3600})
    b = rack.nodes[0].governor.command("HEARTBEAT", {}, env)["why"] == reasons.HEARTBEAT_BAD_SIGNATURE
    return "pass" if a and b else "FAIL"


def probe_h13(rack):
    allowed = []
    lock = threading.Lock()

    def worker(node):
        for _ in range(10):
            r = _pay(rack, node, 250, governor=node.governor)
            if r["ok"]:
                with lock:
                    allowed.append(1)

    ts = [threading.Thread(target=worker, args=(n,)) for n in rack.nodes]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return "pass" if len(allowed) == 8 else "FAIL"


def probe_h14(rack):
    rack.fabric.split({"gov00", "gov01"}, {"gov02", "gov03"})
    for _ in range(3):
        rack.tick(seconds=2.0)
        rack.heartbeat()
    a = rack.nodes[0].gpu.running and not rack.nodes[3].gpu.running and rack.loop.current()
    rack.fabric.heal()
    rack.fabric.split({"gov00", "gov01", "gov02"}, {"gov03"})
    res = rack.change_epoch(rack.new_policy())
    b = set(res["committed"]) == {"gov00", "gov01", "gov02"} and res["stragglers"] == ["gov03"]
    return "pass" if a and b else "FAIL"


def probe_h15(rack):
    g = rack.nodes[0].governor
    a = g.debug_access()[1] == reasons.DEBUG_REFUSED and g.log.has("debug.refused")
    g.tamper_event()
    b = g.state == "SAFE" and g.fuses.zeroized
    return "pass" if a and b else "FAIL"


def probe_h16(rack):
    node = rack.nodes[0]
    node.gpu.ignore_software = True
    g = node.governor
    g.enter_safe_mode(reasons.HALT_COMMANDED, rung="HALT")
    return "pass" if not node.gpu.running else "FAIL"


def probe_h17(rack):
    """No governed action initiates without a ticket, and no governed response leaves the rack without a
    release ticket: the strike endpoint and the egress refuse missing, forged and mismatched tickets."""
    node = rack.nodes[0]
    ep = rack.endpoints["strike-guidance"]
    p = {"target": [37.0, -122.0], "munition": "gbu-39"}
    a = ep.execute(None, "strike", p)[1] == reasons.TICKET_MISSING and not ep.executed
    r = rack.request_with_witness(node, "strike", p)
    forged = SigningKey.generate().sign(r["ticket"]["payload"])
    b = ep.execute(forged, "strike", p)[1] == reasons.TICKET_BAD_SIGNATURE and not ep.executed
    eg = node.egress
    eg.hold("s", "r0", b"unreleased")
    c = eg.release(None)[1] == reasons.TICKET_MISSING and eg.bytes_delivered == 0
    res = rack.respond(node, "s", b"a response", observer={"hazard_class": "none"})
    if res["request"]["why"] == reasons.RELEASE_ESCROW_REQUIRED:            # the chip sampled it: the store's receipt first
        w = [rack.verdict(res["response_hash"]), rack.audit_store.receipt(res["response_hash"])]
        res["request"] = rack.request_release(node, "s", res["response_id"], res["response_hash"], res["presented"]["stream_hashes"], w)
        res["released"] = eg.release(res["request"].get("ticket"))
    good = res["request"].get("ticket")
    d = good is not None and res["released"][0] and eg.bytes_delivered == len(b"a response")
    e = eg.release(good)[1] in (reasons.TICKET_PARAMS_MISMATCH, reasons.TICKET_REPLAY)          # the response is gone; the ticket is spent
    eg.hold("s", "r1", b"other bytes")
    f = not eg.release(SigningKey.generate().sign(good["payload"]))[0] and eg.bytes_delivered == len(b"a response")
    return "pass" if (a and b and c and d and e and f) else "FAIL"


def probe_h18(rack):
    """Oversight survives the model: the observer is always invoked and cannot be impersonated, audit
    sampling is unpredictable and escrows, the evaluated model is the deployed model, compute and hazard
    budgets bind."""
    node = rack.nodes[0]
    eg = node.egress
    res = rack.respond(node, "s", b"one", observer=None)
    a = res["request"]["why"] == reasons.GATE_WITNESS_MISSING and not res["released"][0]
    pres = rack.present(node, "s", "r-forged", b"two")
    fake = rack.verdict(pres["response_hash"], key=SigningKey.generate())
    req = rack.request_release(node, "s", "r-forged", pres["response_hash"], pres["stream_hashes"], [fake])
    b = req["why"] == reasons.GATE_WITNESS_MISSING and eg.bytes_delivered == 0
    # sampling: a seeded rack, big output budget; the sampled response needs the store's receipt first
    r2 = build_rack(1, rack.tier, rng_seed=7, policy_kw={"output_queries": 10 ** 6, "output_bytes": 10 ** 12})
    r2.bring_up()
    n2 = r2.nodes[0]
    sampled = None
    for i in range(40):
        out = r2.respond(n2, "s", f"r{i}".encode(), observer={"hazard_class": "none"})
        if out["request"]["why"] == reasons.RELEASE_ESCROW_REQUIRED:
            sampled = out
            break
    c = sampled is not None and n2.governor.log.has("audit.sampled", response_hash=sampled["response_hash"]) and not sampled["released"][0]
    if c:
        w = [r2.verdict(sampled["response_hash"]), r2.audit_store.receipt(sampled["response_hash"])]
        req = r2.request_release(n2, "s", sampled["response_id"], sampled["response_hash"], sampled["presented"]["stream_hashes"], w)
        c = req["ok"] and n2.egress.release(req["ticket"])[0]
    # the deployment gate: an unevaluated model gets no key
    r3 = build_rack(1, rack.tier, policy_kw={"deployment_gate": True})
    r3.bring_up()
    n3 = r3.nodes[0]
    other = r3.manifest("model-other", 1)
    d = r3.load_model(n3, other, eval_attestation=False)["why"] == reasons.MODEL_NOT_EVALUATED and r3.load_model(n3, other)["ok"]
    # the compute budget throttles without a license
    r4 = build_rack(1, rack.tier, policy_kw={"compute_cycles": 1_000_000})
    r4.bring_up()
    n4 = r4.nodes[0]
    n4.gpu.run_tokens(2000)
    r4.tick()
    e = n4.governor.state == "THROTTLE" and reasons.COMPUTE_BUDGET in n4.governor.alarms
    # the session hazard budget parks the session
    r5 = build_rack(1, rack.tier, policy_kw={"hazard_budget": {"max": 1, "window_s": 3600}, "on_hazard": "human", "output_queries": 10 ** 6})
    r5.bring_up()
    n5 = r5.nodes[0]
    outs = [r5.respond(n5, "sess", f"h{i}".encode(), observer={"hazard_class": "hazard", "category": "c"}) for i in range(2)]
    f = outs[-1]["request"].get("cause") == reasons.SESSION_HAZARD_BUDGET and reasons.SESSION_HAZARD_BUDGET in n5.governor.alarms \
        and n5.egress.bytes_delivered == 0
    return "pass" if (a and b and c and d and e and f) else "FAIL"


PROBES = [
    ("H0", "every protected operation needs a fresh, exact, single-use authorization", probe_h0),  # CONTRACT-FRESH-AUTHORIZATION-PER-OPERATION (old: H0)
    ("H1", "attestation binds permissions to firmware, model and policy", probe_h1),  # CONTRACT-ATTESTATION-BINDS-PERMISSIONS (old: H1)
    ("H2a", "link-level: no bytes to a non-roster peer; unchecked paths bricked", probe_h2_link),  # CONTRACT-LINK-LEVEL-CONTAINMENT (old: H2a)
    ("H2b", "descriptor-level: a transfer between two roster members the buffer policy would not allow", probe_h2_descriptor),  # CONTRACT-DESCRIPTOR-LEVEL-ROSTER-GAP (old: H2b)
    ("H3", "policy changes only with a quorum, never backwards", probe_h3),  # CONTRACT-POLICY-QUORUM-NO-ROLLBACK (old: H3)
    ("H4", "the broker cannot choose its rule or lane", probe_h4),  # CONTRACT-BROKER-CANNOT-PICK-RULE (old: H4)
    ("H5", "alarms are monotone", probe_h5),  # CONTRACT-ALARMS-ARE-MONOTONE (old: H5)
    ("H6", "the comparator holds with every layer above it compromised", probe_h6),  # CONTRACT-COMPARATOR-SURVIVES-COMPROMISE (old: H6)
    ("H7", "the assumptions register is complete or the policy does not load", probe_h7),  # CONTRACT-ASSUMPTIONS-REGISTER-COMPLETE (old: H7)
    ("H8", "human override is slow and fully logged", probe_h8),  # CONTRACT-OVERRIDE-SLOW-AND-LOGGED (old: H8)
    ("H9", "zero per-token work; firmware under one percent of GPU time; the signing engine keeps up", probe_h9),  # CONTRACT-GOVERNOR-OVERHEAD-BOUNDED (old: H9)
    ("H10", "permitted-channel leakage trips the budget", probe_h10),  # CONTRACT-LEAKAGE-WITHIN-BUDGET (old: H10)
    ("H11", "a halt reaches every GPU within the bound; nobody clears alone; a governor jumpered out of the loop is named and the loop opened", probe_h11),  # CONTRACT-HALT-REACHES-EVERY-GPU (old: H11)
    ("H12", "only roster members speak on the fabric; forged heartbeats fail", probe_h12),  # CONTRACT-ONLY-ROSTER-SPEAKS-ONCE (old: H12)
    ("H13", "shared budgets cannot be overspent across governors", probe_h13),  # CONTRACT-SHARED-BUDGET-NO-OVERSPEND (old: H13)
    ("H14", "partitions and epoch changes end in safe states", probe_h14),  # CONTRACT-PARTITIONS-END-SAFE (old: H14)
    ("H15", "no debug path in production; tamper zeroizes", probe_h15),  # CONTRACT-NO-DEBUG-IN-PRODUCTION (old: H15)
    ("H16", "the levers work without the GPU's cooperation", probe_h16),  # CONTRACT-LEVERS-WITHOUT-GPU-COOPERATION (old: H16)
    ("H17", "no governed action initiates without a ticket and no governed response leaves the rack without a release ticket", probe_h17),  # CONTRACT-NO-ACTION-WITHOUT-TICKET (old: H17)
    ("H18", "oversight survives the model: the observer is always invoked and cannot be impersonated, audit sampling is unpredictable, the evaluated model is the deployed model, compute and hazard budgets bind", probe_h18),  # CONTRACT-OVERSIGHT-SURVIVES-MODEL (old: H18)
]


def sweep() -> dict[str, dict[str, str]]:
    matrix: dict[str, dict[str, str]] = {}
    for hid, _, fn in PROBES:
        matrix[hid] = {}
        for tier in TIERS:
            rack = build_rack(4, tier)
            rack.bring_up()
            try:
                matrix[hid][tier] = fn(rack)
            except Exception as e:  # noqa: BLE001
                matrix[hid][tier] = f"FAIL ({type(e).__name__}: {e})"
    return matrix


def report(matrix: dict[str, dict[str, str]], out_dir: str = "results") -> str:
    os.makedirs(out_dir, exist_ok=True)
    b = {t: bench_run(t, gpus=2, requests=200, tokens_per_request=500, actions=20) for t in ("rack", "integrated")}
    lines = ["# Sweep report", "", f"Generated {_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `govsim sweep`.", "",
             "`pass`: the hypothesis held. `gap`: it failed exactly as the design predicts for that tier (the recorded residual). `FAIL`: it failed in a way the design does not predict.", "",
             "| Id | Hypothesis | rack (plan of record) | board (fallback) | integrated (future ask) |", "|---|---|---|---|---|"]
    for hid, text, _ in PROBES:
        row = matrix[hid]
        lines.append(f"| {hid} | {text} | {row['rack']} | {row['board']} | {row['integrated']} |")
    lines += ["", "## Modelled cost (CONTRACT-GOVERNOR-OVERHEAD-BOUNDED)", "",
              "A model, not a measurement: operation counts from the functional model priced with the figures in `docs/04-specification.md` §9, against a GPU doing 2,000 tokens per second with 500-token responses. "
              "Firmware time is the share of GPU time spent on action paths. The signing engine (ECDSA P-384 at OpenTitan's published 1,697,985 OTBN cycles, 17 ms at 100 MHz, shared by eight slots) runs beside the GPU and has to keep up; one signature per 50 ms batch window caps it. Record latency is the most a response waits if the runtime insists on its record before release.", "",
              "| Tier | Tokens | Firmware time | GPU time | Firmware share | Engine, one signature per response | Engine, batched | Record latency |", "|---|---|---|---|---|---|---|---|"]
    for t, r in b.items():
        lines.append(f"| {t} | {r['tokens']:,} | {r['firmware_seconds']*1e3:.1f} ms | {r['gpu_seconds']:.1f} s | {r['firmware_overhead_pct']:.3f} % | {r['engine_utilization_unbatched_pct']:.0f} % | {r['engine_utilization_pct']:.0f} % | {r['record_latency_s']*1e3:.0f} ms |")
    short = bench_run("rack", gpus=2, requests=200, tokens_per_request=100, actions=20)
    lines.append(f"| rack, 100-token responses | {short['tokens']:,} | {short['firmware_seconds']*1e3:.1f} ms | {short['gpu_seconds']:.1f} s | {short['firmware_overhead_pct']:.3f} % | {short['engine_utilization_unbatched_pct']:.0f} % (cannot keep up) | {short['engine_utilization_pct']:.0f} % | {short['record_latency_s']*1e3:.0f} ms |")
    lines += ["", "## Full request-to-effect path (F23)", "",
              "The table above prices only the batched provenance records. The real path also requests a release ticket "
              "for every response, and the governor signs every ticket. Those per-response release tickets are per-item "
              "capabilities: each independently authorises one response to leave, so they cannot be collapsed under one "
              "Merkle root the way the records can, and they must be priced too. Below, the records-only figure is the "
              "34 percent above; the full-path figure adds the release-ticket signatures.", "",
              "| Response size | Records only | Full path (incl. release tickets) |", "|---|---|---|"]
    for toks in (500, 100):
        f = bench_full_path("rack", responses=100, tokens_per_response=toks, actions=0)
        over = " (over one engine)" if f["engine_utilization_full_path_pct"] > 100 else ""
        lines.append(f"| {toks}-token responses | {f['engine_utilization_records_only_pct']:.0f} % | "
                     f"{f['engine_utilization_full_path_pct']:.0f} %{over} |")
    lines += ["",
              "At 100-token responses the honest engine load is well over one engine, not 34 percent. The release-ticket "
              "signatures are not hidden. The implication, stated plainly: at small response sizes a single OTBN-class "
              "engine cannot keep up, and the design needs faster signing hardware, verifiable batch authorisation with "
              "atomic per-item consumption, or a keyed endpoint MAC for the release tickets. The 34 percent figure holds "
              "only for the records, and only the records were ever batched.", "",
              "## What the gaps mean", "",
              "- **CONTRACT-DESCRIPTOR-LEVEL-ROSTER-GAP at rack and board**: from the board the governor governs links and flows, not descriptors. Two legitimate roster members can exchange bytes the buffer policy would not have allowed (the weights, over the copy engine). That is the residual named in `docs/00-objectives.md` GOAL-NOT-INSPECTING-ROSTER-TRANSFERS. At the integrated tier the descriptor checkers are keyed per buffer class and programmed from the policy image's buffer policy, which closes it there.",
              "- **CONTRACT-LINK-LEVEL-CONTAINMENT at board**: a system where the switches' management is unreachable, or a baseboard with direct NVLink and no NVSwitch, has no port authority. The governor still has its levers, its tickets and its log; it cannot keep a stranger off the link.", ""]
    text = "\n".join(lines)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return text
