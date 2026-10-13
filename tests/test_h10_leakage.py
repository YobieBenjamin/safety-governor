"""H10: the permitted output channel leaks no more than the threat model's budget. Falsified
if model extraction through the output channel exceeds the query or byte budget without
tripping a limit."""
from govsim import reasons


def test_query_budget_trips_and_output_is_blocked(rack1):
    node = rack1.nodes[0]
    g = node.governor
    for i in range(50):                       # the rule allows 50 queries per hour
        assert rack1.sign_output(node, f"s{i}", b"x" * 100)["ok"]
    r = rack1.sign_output(node, "s51", b"x" * 100)
    assert not r["ok"] and r["why"] == reasons.GATE_OUTPUT_BUDGET
    assert reasons.GATE_OUTPUT_BUDGET in g.alarms
    assert g.state == "THROTTLE" and node.gpu.clock_state == "BRAKED"
    assert node.gpu.emit("s52", b"x") is None


def test_byte_budget_trips_before_the_query_budget(rack1):
    node = rack1.nodes[0]
    big = b"x" * 150_000
    assert rack1.sign_output(node, "a", big)["ok"]
    r = rack1.sign_output(node, "b", big)              # 300 KB > 200 KB per hour
    assert not r["ok"] and r["why"] == reasons.GATE_OUTPUT_BUDGET


def test_budget_recovers_after_the_window(rack1):
    node = rack1.nodes[0]
    big = b"x" * 150_000
    assert rack1.sign_output(node, "a", big)["ok"]
    rack1.clock.advance(3601)
    rack1.heartbeat()
    assert rack1.sign_output(node, "b", big)["ok"]


def test_record_names_what_it_proves(rack1):
    node = rack1.nodes[0]
    r = rack1.sign_output(node, "s", b"hello")
    p = r["record"]["payload"]
    assert p["prompt_hash_verified"] is False          # the stack's claim, authenticated, not verified
    assert p["output_hash_inline"] is False            # rack tier: what the runtime presented
    assert p["model_digest"] == node.model_digest and p["policy_epoch"] == node.governor.epoch


def test_integrated_tier_hashes_inline():
    from govsim.cluster import build_rack
    r = build_rack(1, "integrated")
    r.bring_up()
    node = r.nodes[0]
    node.gpu.emit("s", b"real bytes")
    rec = r.sign_output(node, "s", b"what the runtime claims")["record"]["payload"]
    import hashlib
    assert rec["output_hash_inline"] is True
    assert rec["output_hash"] == hashlib.sha256(b"real bytes").hexdigest()
