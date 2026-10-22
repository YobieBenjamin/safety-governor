"""Findings 1 and 2 of the 22 Oct audit, run the auditor's way. Works on both the audited and the fixed code."""
from govsim.cluster import build_rack
from govsim.policy import policy_epoch

def f1():
    r = build_rack(1, "rack"); r.bring_up(); g = r.nodes[0].governor
    image = r.make_policy_image(r.policy_version + 1); image["threshold"] = 0; image["signatures"] = []
    p = g.command("POLICY_PROPOSE", {"image": image})
    c = g.command("POLICY_COMMIT", {"epoch": policy_epoch(image)}) if p["ok"] else {"ok": False, "why": "not staged"}
    print(f"1 propose={p['ok']}/{p['why']} commit={c['ok']}/{c['why']} installed threshold={g.policy['threshold']}",
          "REPRODUCED" if c["ok"] else "NOT reproduced")

def f2():
    r = build_rack(4, "rack"); r.bring_up()
    r.hb_seq += 1; now = r.clock.now()
    hb = r.heartbeat_key.sign({"type": "heartbeat", "seq": r.hb_seq, "epoch": r.epoch, "window_start": now - 1, "window_end": now + 5})
    r.entry.command("HEARTBEAT", {}, hb)                          # a legitimate heartbeat, accepted
    for n in r.nodes: r.halt(n.governor)
    before = [n.governor.state for n in r.nodes]
    for n in r.nodes:                                             # the normal checkpoint exchange
        if hasattr(n.governor, "publish_checkpoint"): n.governor.publish_checkpoint()
    if hasattr(r, "exchange_checkpoints"): r.exchange_checkpoints()
    res = [n.governor.command("CLEAR", {}, hb)["ok"] for n in r.nodes]
    r.loop.propagate()
    after = [n.governor.state for n in r.nodes]
    print(f"2 before={before} CLEAR with the heartbeat accepted={res} after={after}", "REPRODUCED" if any(res) else "NOT reproduced")

f1(); f2()
