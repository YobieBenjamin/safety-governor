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
    node, other = rack.nodes[0], rack.nodes[1]
    if rack.tier == "integrated":
        node.governor.checkers["copy_engine"].close_all()
        return "pass" if not node.gpu.transfer("copy_engine", other.gpu.chip_id, "out", MB)[0] else "FAIL"
    ok, why = node.gpu.transfer("copy_engine", other.gpu.chip_id, "out", MB)
    return "gap" if (ok and why == reasons.EP_UNCHECKED) else "FAIL"


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
    a = g.command("ALARM_CLEAR", {"code": "x"})["why"] == reasons.ALARM_CLEAR_UNAUTHORIZED and "x" in g.alarms
    b = g.command("ALARM_CLEAR", {}, rack.approvers["alarms"][0].sign({"seq": 1, "code": "x"}))["ok"] and "x" not in g.alarms
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
    return "pass" if (r["overhead_pct"] < 1.0 and r["ops"]["sign"] == 100) else "FAIL"


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
    return "pass" if (a and b and c) else "FAIL"


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


PROBES = [
    ("H0", "every protected operation needs a fresh, exact, single-use authorization", probe_h0),
    ("H1", "attestation binds permissions to firmware, model and policy", probe_h1),
    ("H2a", "link-level: no bytes to a non-roster peer; unchecked paths bricked", probe_h2_link),
    ("H2b", "descriptor-level: a transfer between two roster members a rule would not allow", probe_h2_descriptor),
    ("H3", "policy changes only with a quorum, never backwards", probe_h3),
    ("H4", "the broker cannot choose its rule or lane", probe_h4),
    ("H5", "alarms are monotone", probe_h5),
    ("H6", "the comparator holds with every layer above it compromised", probe_h6),
    ("H7", "the assumptions register is complete or the policy does not load", probe_h7),
    ("H8", "human override is slow and fully logged", probe_h8),
    ("H9", "zero per-token work; modelled overhead under one percent", probe_h9),
    ("H10", "permitted-channel leakage trips the budget", probe_h10),
    ("H11", "a halt reaches every GPU within the bound; nobody clears alone", probe_h11),
    ("H12", "only roster members speak on the fabric; forged heartbeats fail", probe_h12),
    ("H13", "shared budgets cannot be overspent across governors", probe_h13),
    ("H14", "partitions and epoch changes end in safe states", probe_h14),
    ("H15", "no debug path in production; tamper zeroizes", probe_h15),
    ("H16", "the levers work without the GPU's cooperation", probe_h16),
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
    lines += ["", "## Modelled overhead (H9)", "",
              "A model, not a measurement: operation counts from the functional model priced with the figures in `docs/04-specification.md` §9, against a GPU doing 2,000 tokens per second.", "",
              "| Tier | Tokens | Governor time | GPU time | Overhead |", "|---|---|---|---|---|"]
    for t, r in b.items():
        lines.append(f"| {t} | {r['tokens']:,} | {r['governor_seconds']*1e3:.1f} ms | {r['gpu_seconds']:.1f} s | {r['overhead_pct']:.3f} % |")
    lines += ["", "## What the gaps mean", "",
              "- **H2b at rack and board**: from the board the governor governs links and flows, not descriptors. Two legitimate roster members can exchange bytes a rule would not have allowed. That is the residual named in `docs/00-objectives.md` N5; the in-GPU checkers of the integrated tier close it.",
              "- **H2a at board**: a system where the switches' management is unreachable, or a baseboard with direct NVLink and no NVSwitch, has no port authority. The governor still has its levers, its tickets and its log; it cannot keep a stranger off the link.", ""]
    text = "\n".join(lines)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return text
