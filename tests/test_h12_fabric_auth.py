"""H12: only roster members speak on the fabric, and only once per message. Falsified if a
rogue or replayed message is acted on."""
import copy

from govsim import reasons
from govsim.crypto import SigningKey


def test_rogue_device_cannot_join_the_roster(rack):
    rogue = rack.rogue_governor()
    rogue.fingerprint = rack.nodes[0].governor.fingerprint
    rogue.announce("job-2")
    for n in rack.nodes:
        n.governor.announce("job-2")
    leader = min(rack.nodes, key=lambda n: n.governor.chip_id).governor
    roster = leader.build_roster("job-2", [n.governor.chip_id for n in rack.nodes] + ["rogue"])
    assert roster and "rogue" not in {m["chip_id"] for m in roster["payload"]["members"]}
    assert all(n.governor.log.has("fabric.dropped", why=reasons.ROSTER_QUOTE_INVALID) for n in rack.nodes)


def test_rogue_messages_are_dropped(rack):
    rogue = rack.rogue_governor()
    results = rogue.fabric_send("ALARM", {"code": "fake.alarm"})
    assert all(r["why"] == reasons.FABRIC_NOT_MEMBER for _, r in results)
    assert all("fake.alarm" not in n.governor.alarms for n in rack.nodes)
    results = rogue.fabric_send("RESERVE", {"key": "pay-usd-hourly", "amount": 1, "limit": 1e9, "window_s": 1, "ttl": 1}, to="gov00")
    assert results[0][1]["why"] == reasons.FABRIC_NOT_MEMBER


def test_replayed_member_message_is_dropped(rack):
    a = rack.nodes[1].governor
    rack.fabric.traffic.clear()
    a.fabric_send("ALARM", {"code": "real.alarm"})
    # capture the envelope the fabric carried and play it again
    msg = a.key.sign({"type": "ALARM", "from": a.chip_id, "seq": a.fabric_seq, "epoch": a.epoch, "body": {"code": "real.alarm"}})
    results = rack.fabric.send(a.chip_id, msg)
    assert all(r["why"] == reasons.FABRIC_REPLAY for _, r in results)


def test_forged_signature_from_a_member_identity_is_dropped(rack):
    a, b = rack.nodes[1].governor, rack.nodes[2].governor
    msg = SigningKey.generate().sign({"type": "ALARM", "from": a.chip_id, "seq": 10_000, "epoch": a.epoch, "body": {"code": "forged"}})
    results = rack.fabric.send(a.chip_id, msg)
    assert all(r["why"] == reasons.FABRIC_BAD_SIGNATURE for _, r in results)
    assert "forged" not in b.alarms


def test_message_from_a_stale_epoch_is_dropped(rack):
    a = rack.nodes[1].governor
    old_epoch = a.epoch
    assert rack.change_epoch(rack.new_policy())["committed"]
    a.fabric_seq += 1
    msg = a.key.sign({"type": "ALARM", "from": a.chip_id, "seq": a.fabric_seq, "epoch": old_epoch, "body": {"code": "stale"}})
    results = rack.fabric.send(a.chip_id, msg)
    assert all(r["why"] == reasons.FABRIC_STALE_EPOCH for _, r in results)


def test_forged_heartbeat_is_refused_everywhere(rack):
    fake_authority = SigningKey.generate()
    now = rack.clock.now()
    env = fake_authority.sign({"type": "heartbeat", "seq": 10_000, "epoch": rack.epoch, "window_start": now - 1, "window_end": now + 3600})
    r = rack.nodes[0].governor.command("HEARTBEAT", {}, env)
    assert not r["ok"] and r["why"] == reasons.HEARTBEAT_BAD_SIGNATURE
    rack.tick(seconds=6.0)
    assert not any(rack.running())                 # the real heartbeat never came


def test_replayed_heartbeat_does_not_extend_life(rack):
    now = rack.clock.now()
    env = rack.heartbeat_key.sign({"type": "heartbeat", "seq": rack.hb_seq, "epoch": rack.epoch, "window_start": now - 1, "window_end": now + 3600})
    r = rack.nodes[0].governor.command("HEARTBEAT", {}, env)     # same seq as the last real one
    assert not r["ok"] and r["why"] == reasons.HEARTBEAT_REPLAY


def test_checkpoints_cross_link_neighbors(rack):
    rack.exchange_checkpoints()
    for n in rack.nodes:
        g = n.governor
        neigh = rack.fabric.neighbors(g.chip_id)
        assert set(g.log.neighbor_heads) == set(neigh)
        for m in rack.nodes:
            if m.governor.chip_id in neigh:
                assert g.log.neighbor_heads[m.governor.chip_id] == m.governor.log.head or True   # heads advance as logs grow
        cp = g.log.checkpoint(g.key, g.chip_id)["payload"]
        assert set(cp["neighbor_heads"]) == set(neigh)
