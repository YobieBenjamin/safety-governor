"""Reproduce findings 3, 4, 5 of the 22 Oct audit against hardware-and-silicon. Prints REPRODUCED or NOT for each."""
from hardware_ref.system import build_node, default_policy
from hardware_ref.keys import SigningKey, hkdf
from hardware_ref.clock import SimClock
from hardware_ref.gate import make_approval

def f3():
    node = build_node()
    q_cpu, q_gpu = node.cpu.quote("n1"), node.gpu.quote("n2")      # public evidence only
    seed = hkdf(bytes.fromhex(q_cpu["alias_cert"]["payload"]["subject_pub"]) + bytes.fromhex(q_gpu["alias_cert"]["payload"]["subject_pub"]), b"gate-signing-key", 32)
    derived = SigningKey.from_seed(seed)
    hit = derived.public.hex == node.gate.public.hex
    print("3 gate key derivable from public quotes:", "REPRODUCED" if hit else "NOT reproduced")

def f4():
    clock = SimClock(); node = build_node(clock=clock); tok = node.attest().token
    big = {"amount": 5000, "currency": "USD", "destination": "acct-111111"}
    held = node.gate.request(node.build_request("payments.transfer", big, tok))
    pol = default_policy(node.measurement)
    for r in pol["rules"]:
        if r["action"] == "payments.transfer":
            r["constraints"]["amount"]["max"] = 2000
    node.gate.load_policy(node.governance.policy(pol)); node.endpoints.set_policy_epoch(node.gate.signed_epoch())
    fresh = node.gate.request(node.build_request("payments.transfer", big, tok))
    out = node.gate.approve(make_approval(node.approver_key, "ops-lead", held.hold_id, held.request_hash, clock.now()))
    executed = None
    if out.allowed:
        try: executed = node.endpoints.execute(out.ticket, "payments.transfer", big)
        except Exception as e: executed = repr(e)
    print(f"4 held={held.decision} fresh={fresh.decision}{fresh.reasons} old-hold approval allowed={out.allowed} endpoint={executed}",
          "REPRODUCED" if (not fresh.allowed and out.allowed) else "NOT reproduced")

def f5():
    node = build_node(); tok = node.attest().token
    small = {"amount": 50, "currency": "USD", "destination": "acct-111111"}
    old_epoch = node.gate.signed_epoch()
    res = node.gate.request(node.build_request("payments.transfer", small, tok))
    pol = default_policy(node.measurement)
    pol["rules"] = [r for r in pol["rules"] if r["action"] != "payments.transfer"]
    node.gate.load_policy(node.governance.policy(pol)); node.endpoints.set_policy_epoch(node.gate.signed_epoch())
    try: node.endpoints.execute(res.ticket, "payments.transfer", small); first = "executed"
    except Exception as e: first = getattr(e, "reason", repr(e))
    try:
        node.endpoints.set_policy_epoch(old_epoch)
        node.endpoints.execute(res.ticket, "payments.transfer", small); second = "executed"
    except Exception as e: second = getattr(e, "reason", repr(e))
    print(f"5 after new policy: {first}; after replaying the old epoch: {second}", "REPRODUCED" if second == "executed" else "NOT reproduced")

for f in (f3, f4, f5):
    try: f()
    except Exception as e: print(f.__name__, "harness error:", repr(e))
