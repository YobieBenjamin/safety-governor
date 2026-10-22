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


def test_bytes_that_leave_for_the_host_but_are_never_presented_trip_an_alarm(rack1):
    """Rack tier: the GPU's output crosses the governed pcie port. The governor compares what
    crossed with what the runtime presented for signing; the excess beyond the policy's slack
    (1 MB) raises OUTPUT_UNPRESENTED and blocks the output path."""
    node = rack1.nodes[0]
    g = node.governor
    for _ in range(1000):
        assert node.gpu.emit("s", b"x" * 10_000) is not None               # 10 MB out, never presented
    assert reasons.OUTPUT_UNPRESENTED not in g.alarms                        # the check runs on the governor's tick
    rack1.tick()
    assert reasons.OUTPUT_UNPRESENTED in g.alarms
    assert node.gpu.emit("s", b"x") is None and node.gpu.output_blocked
    assert not node.gpu.transfer("pcie", "host", "out", 1)[0]                 # the host port is closed
    assert not rack1.request(node, "payments.transfer", {"amount": 1, "currency": "USD", "destination": "a"})["ok"]   # alarms block the gate


def test_presented_output_within_the_slack_raises_nothing(rack1):
    node = rack1.nodes[0]
    g = node.governor
    for i in range(20):
        data = b"y" * 5_000
        assert node.gpu.emit(f"s{i}", data) is not None
        assert rack1.sign_output(node, f"s{i}", data)["ok"]
    rack1.tick()
    assert reasons.OUTPUT_UNPRESENTED not in g.alarms


def test_meter_counts_tokens_and_the_host_cannot_write_it(rack1):
    from govsim.governor import MAILBOX_CODES
    node = rack1.nodes[0]
    g = node.governor
    node.gpu.run_tokens(1234)
    rack1.tick()
    before = g.command("COUNTERS", {})["meter"][node.model_digest]
    assert before["tokens"] == 1234 and before["cycles"] == 1234 * 1000
    junk = {"meter": {node.model_digest: {"tokens": 0}}, "tokens": 0, "model_digest": node.model_digest, "slot": 0}
    for code, name in sorted(MAILBOX_CODES.items()):
        if name == "END_MODEL":
            continue                                                         # finalizes the slot; tested below
        g.command(name, junk, node.host_sign(junk, g.epoch))
        assert g.command("COUNTERS", {})["meter"][node.model_digest]["tokens"] == 1234, name
    node.gpu.run_tokens(1)
    assert rack1.end_model(node)["meter"]["tokens"] == 1235
    node.gpu.run_tokens(1)
    rack1.tick()
    assert g.command("COUNTERS", {})["meter"][node.model_digest]["tokens"] == 1235   # the slot is final


def test_the_budget_the_covert_model_reads_is_the_one_enforced_here(rack1):
    """tests/test_covert_budget.py bounds covert leakage from the output budget in the policy image; this
    pins that it is the same 50 queries and 200 KB per hour the tests above trip (docs/05-threat-model.md)."""
    ob = rack1.nodes[0].governor._output_rule()["output_budget"]
    assert (ob["queries"], ob["bytes"], ob["window_s"]) == (50, 200_000, 3600)
