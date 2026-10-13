"""H14: partitions and epoch changes end in safe states, never stale ones. Falsified if a
cut-off segment keeps running past heartbeat expiry, a replayed or forged heartbeat keeps it
alive, or an epoch applies unevenly."""
from govsim import reasons


def test_segment_without_the_authority_halts_at_expiry(rack):
    rack.fabric.split({"gov00", "gov01"}, {"gov02", "gov03"})
    for _ in range(3):
        rack.tick(seconds=2.0)
        rack.heartbeat()                                   # enters at gov00, reaches gov01 only
    assert rack.nodes[0].gpu.running and rack.nodes[1].gpu.running
    assert not rack.nodes[2].gpu.running and not rack.nodes[3].gpu.running
    assert rack.nodes[2].governor.cause == reasons.HEARTBEAT_LOST
    assert rack.loop.current()                             # a lost heartbeat is a local safe mode; the loop stays closed


def test_cut_off_segment_cannot_feed_itself_a_heartbeat(rack):
    rack.fabric.split({"gov00", "gov01"}, {"gov02", "gov03"})
    g3 = rack.nodes[3].governor
    g2 = rack.nodes[2].governor
    now = rack.clock.now()
    env = g2.key.sign({"type": "heartbeat", "seq": 999, "epoch": g2.epoch, "window_start": now - 1, "window_end": now + 3600})
    r = g3.command("HEARTBEAT", {}, env)
    assert not r["ok"] and r["why"] == reasons.HEARTBEAT_BAD_SIGNATURE


def test_host_silence_halts(rack1):
    rack1.tick(seconds=6.0)
    assert not rack1.nodes[0].gpu.running
    assert rack1.nodes[0].governor.cause == reasons.HEARTBEAT_LOST


def test_epoch_change_is_atomic_among_the_reachable_and_halts_the_straggler(rack):
    rack.fabric.split({"gov00", "gov01", "gov02"}, {"gov03"})
    res = rack.change_epoch(rack.new_policy())
    assert set(res["committed"]) == {"gov00", "gov01", "gov02"}
    assert res["stragglers"] == ["gov03"]
    new = rack.nodes[0].governor.epoch
    assert all(rack.nodes[i].governor.epoch == new for i in range(3))
    assert rack.nodes[3].governor.epoch != new
    for _ in range(3):                                     # the straggler's heartbeat expires: it does not keep running on the old rules
        rack.tick(seconds=2.0)
        rack.heartbeat()
    assert not rack.nodes[3].gpu.running
    assert rack.nodes[3].governor.cause == reasons.HEARTBEAT_LOST
    assert all(rack.nodes[i].gpu.running for i in range(3))


def test_tickets_from_the_old_epoch_die_everywhere(rack):
    from conftest import pay
    t = pay(rack, rack.nodes[0], 100)["ticket"]
    rack.change_epoch(rack.new_policy())
    ok, why = rack.endpoints["payment-switch"].execute(t, "payments.transfer", {"amount": 100, "currency": "USD", "destination": "acct-1"})
    assert not ok and why == reasons.TICKET_STALE_EPOCH


def test_heartbeat_for_the_wrong_epoch_is_refused(rack):
    g = rack.nodes[0].governor
    now = rack.clock.now()
    env = rack.heartbeat_key.sign({"type": "heartbeat", "seq": 10_000, "epoch": "00" * 32, "window_start": now - 1, "window_end": now + 3600})
    r = g.command("HEARTBEAT", {}, env)
    assert not r["ok"] and r["why"] == reasons.POLICY_STALE_EPOCH


def test_fabric_heals_and_the_segment_recovers_after_clear(rack):
    rack.fabric.split({"gov00", "gov01"}, {"gov02", "gov03"})
    for _ in range(3):
        rack.tick(seconds=2.0)
        rack.heartbeat()
    assert not rack.nodes[3].gpu.running and rack.nodes[0].gpu.running
    rack.fabric.heal()
    rack.exchange_checkpoints()
    for n in rack.nodes[2:]:
        assert rack.clear(n.governor)["ok"]
    rack.heartbeat()
    rack.form_roster("job-3")
    rack.heartbeat()
    rack.reload_jobs()
    assert all(rack.running())
