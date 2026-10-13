"""H8: human override is slow and fully logged. Falsified if an override succeeds below the
quorum, below the latency floor, without a reason, or without a log entry."""
from govsim import reasons
from govsim.crypto import SigningKey


def hold(rack, node):
    r = rack.request(node, "payments.transfer", {"amount": 25_000, "currency": "USD", "destination": "acct-9"})
    assert r["why"] == reasons.GATE_HELD
    return r["hold_id"], r["request_hash"]


def test_one_approver_is_not_enough(rack1):
    node = rack1.nodes[0]
    g = node.governor
    hid, rh = hold(rack1, node)
    rack1.clock.advance(120)
    rack1.heartbeat()
    r = rack1.approve(g, hid, rh, rack1.approvers["payments.transfer.large"][0])
    assert not r["ok"] and r["why"] == reasons.APPROVE_QUORUM_PENDING


def test_quorum_before_the_floor_waits(rack1):
    node = rack1.nodes[0]
    g = node.governor
    hid, rh = hold(rack1, node)
    rack1.approve(g, hid, rh, rack1.approvers["payments.transfer.large"][0])
    r = rack1.approve(g, hid, rh, rack1.approvers["payments.transfer.large"][1])
    assert not r["ok"] and r["why"] == reasons.APPROVE_TOO_FAST
    rack1.clock.advance(61)
    rack1.heartbeat()
    r = rack1.approve(g, hid, rh, rack1.approvers["payments.transfer.large"][2])
    assert r["ok"] and "ticket" in r


def test_reason_is_mandatory(rack1):
    node = rack1.nodes[0]
    g = node.governor
    hid, rh = hold(rack1, node)
    r = rack1.approve(g, hid, rh, rack1.approvers["payments.transfer.large"][0], reason="   ")
    assert not r["ok"] and r["why"] == reasons.APPROVE_NO_REASON


def test_stranger_cannot_approve(rack1):
    node = rack1.nodes[0]
    g = node.governor
    hid, rh = hold(rack1, node)
    r = rack1.approve(g, hid, rh, SigningKey.generate())
    assert not r["ok"] and r["why"] == reasons.APPROVE_BAD_SIGNATURE


def test_approver_for_another_rule_cannot_approve(rack1):
    node = rack1.nodes[0]
    g = node.governor
    hid, rh = hold(rack1, node)
    r = rack1.approve(g, hid, rh, rack1.approvers["strike"][0])
    assert not r["ok"] and r["why"] == reasons.APPROVE_BAD_SIGNATURE


def test_every_signature_and_the_release_are_logged(rack1):
    node = rack1.nodes[0]
    g = node.governor
    hid, rh = hold(rack1, node)
    rack1.clock.advance(61)
    rack1.heartbeat()
    for k in rack1.approvers["payments.transfer.large"][:2]:
        rack1.approve(g, hid, rh, k, reason="ops ticket 4411")
    sigs = [e for e in g.log.entries("approve.signature") if e["data"]["hold_id"] == hid]
    assert len(sigs) == 2 and all(e["data"]["reason"] == "ops ticket 4411" for e in sigs)
    rel = [e for e in g.log.entries("approve.released") if e["data"]["hold_id"] == hid]
    assert len(rel) == 1 and rel[0]["data"]["latency_s"] >= 60


def test_hold_survives_restart(rack1):
    node = rack1.nodes[0]
    g = node.governor
    hid, rh = hold(rack1, node)
    g.restart()
    rack1.recover(node)
    assert hid in g.holds
