# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
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
    heads_at_publish = {n.governor.chip_id: n.governor.log.head for n in rack.nodes}
    rack.exchange_checkpoints()
    for n in rack.nodes:
        g = n.governor
        neigh = rack.fabric.neighbors(g.chip_id)
        assert set(g.log.neighbor_heads) == set(neigh)
        for chip in neigh:
            assert g.log.neighbor_heads[chip] == heads_at_publish[chip]      # the neighbor's head as it published it
        cp = g.log.checkpoint(g.key, g.chip_id)["payload"]
        assert cp["neighbor_heads"] == {chip: heads_at_publish[chip] for chip in neigh}


def test_forged_checkpoint_is_dropped_and_logged(rack):
    a, b = rack.nodes[1].governor, rack.nodes[2].governor
    before = dict(b.log.neighbor_heads)
    fake = SigningKey.generate().sign({"type": "checkpoint", "chip_id": a.chip_id, "head": "ab" * 32, "size": 999, "neighbor_heads": {}, "time": 0})
    res = a.fabric_send("CHECKPOINT", {"checkpoint": fake}, to=b.chip_id)
    assert res[0][1]["why"] == reasons.FABRIC_BAD_SIGNATURE
    assert b.log.neighbor_heads == before
    assert b.log.has("fabric.dropped", why=reasons.FABRIC_BAD_SIGNATURE, type="CHECKPOINT")


def test_forged_roster_is_dropped_and_logged(rack):
    leader = rack.nodes[0].governor
    others = [n.governor for n in rack.nodes[1:]]
    before = [g.roster["roster_id"] for g in others]
    fake_roster = SigningKey.generate().sign({**leader.roster, "roster_id": "ff" * 32, "expires_at": rack.clock.now() + 3600})
    msg = SigningKey.generate().sign({"type": "ROSTER", "from": leader.chip_id, "seq": 10_000, "epoch": leader.epoch, "time": 0,
                                       "body": {"roster": fake_roster}})
    results = rack.fabric.send(leader.chip_id, msg)
    assert all(r["why"] == reasons.ROSTER_BAD_SIGNATURE for _, r in results)
    assert [g.roster["roster_id"] for g in others] == before
    assert all(g.log.has("fabric.dropped", why=reasons.ROSTER_BAD_SIGNATURE, type="ROSTER") for g in others)


def test_heartbeat_relay_signature_and_hop_limit(rack):
    """A relayed heartbeat carries the authority's envelope inside a member's envelope. A forged
    relay is dropped; a genuine relay past the hop limit is refused."""
    a, b = rack.nodes[1].governor, rack.nodes[2].governor
    now = rack.clock.now()
    rack.hb_seq += 1
    env = rack.heartbeat_key.sign({"type": "heartbeat", "seq": rack.hb_seq, "epoch": rack.epoch, "window_start": now - 1, "window_end": now + 5})
    forged = SigningKey.generate().sign({"type": "HEARTBEAT", "from": a.chip_id, "seq": a.fabric_seq + 1, "epoch": a.epoch, "time": 0,
                                         "body": {"authority": env, "hops": 1}})
    res = rack.fabric.send(a.chip_id, forged, to=b.chip_id)
    assert res[0][1]["why"] == reasons.FABRIC_BAD_SIGNATURE and b.hb_last_seq < rack.hb_seq
    too_far = rack.policy["fabric"]["max_hops"] + 1
    res = a.fabric_send("HEARTBEAT", {"authority": env, "hops": too_far}, to=b.chip_id)
    assert res[0][1]["why"] == reasons.FABRIC_TOO_MANY_HOPS and b.hb_last_seq < rack.hb_seq
    res = a.fabric_send("HEARTBEAT", {"authority": env, "hops": 1}, to=b.chip_id)
    assert res[0][1]["ok"] and b.hb_last_seq == rack.hb_seq


def test_replayed_fabric_message_after_a_restart_is_dropped(rack):
    """The receiver's last-seen sequence numbers survive its own power loss."""
    a, b = rack.nodes[1].governor, rack.nodes[2].governor
    a.fabric_send("ALARM", {"code": "real.alarm"})
    msg = a.key.sign({"type": "ALARM", "from": a.chip_id, "seq": a.fabric_seq, "epoch": a.epoch, "time": 0, "body": {"code": "real.alarm"}})
    b.restart()
    rack.recover(rack.nodes[2])
    rack.form_roster("job-again")                                             # b is a member again, with a's key
    assert a.chip_id in b.roster_keys
    b.alarms.clear()
    r = b.on_fabric(msg)
    assert r["why"] == reasons.FABRIC_REPLAY and "real.alarm" not in b.alarms


def test_a_restarted_sender_is_not_a_replay(rack):
    a, b = rack.nodes[1].governor, rack.nodes[2].governor
    a.fabric_send("ALARM", {"code": "before"})
    a.restart()
    rack.recover(rack.nodes[1])
    rack.form_roster("job-again")
    res = a.fabric_send("ALARM", {"code": "after"}, to=b.chip_id)
    assert res[0][1]["ok"] and "after" in b.alarms


def test_genuine_chip_with_unapproved_firmware_cannot_join(rack):
    """A real governor chip with a valid vendor certificate, running firmware whose measurement
    is not in the governance root's reference values. Its device identity is genuine; its quote
    is refused all the same."""
    bad = rack.rogue_governor_with_bad_firmware()
    bad.fingerprint = rack.nodes[0].governor.fingerprint
    bad.announce("job-4")
    for n in rack.nodes:
        n.governor.announce("job-4")
    leader = min(rack.nodes, key=lambda n: n.governor.chip_id).governor
    roster = leader.build_roster("job-4", [n.governor.chip_id for n in rack.nodes] + ["gov-badfw"])
    assert roster and "gov-badfw" not in {m["chip_id"] for m in roster["payload"]["members"]}
    assert all(n.governor.log.has("fabric.dropped", why=reasons.ROSTER_QUOTE_INVALID, **{"from": "gov-badfw"}) for n in rack.nodes)
