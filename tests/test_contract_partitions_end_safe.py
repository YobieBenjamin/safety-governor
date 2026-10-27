# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""CONTRACT-PARTITIONS-END-SAFE: partitions and epoch changes end in safe states, never stale ones. Falsified if a
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
    env = rack.sign_heartbeat({"type": "heartbeat", "seq": 10_000, "epoch": "00" * 32, "window_start": now - 1, "window_end": now + 3600})
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


def test_reachable_straggler_is_expelled_by_the_epoch_bound_heartbeat(rack):
    """The fabric is intact, but gov03's host never delivers the proposal. The authority commits
    to the three that acknowledged. Heartbeats now carry the new epoch; gov03, still on the old
    one, refuses them and halts at the first one (adversarial audit 3: it used to keep minting until its heartbeat
    expiry), with the straggler cause on record. Nobody keeps running on the old rules."""
    res = rack.change_epoch(rack.new_policy(), silent=["gov03"])
    assert set(res["committed"]) == {"gov00", "gov01", "gov02"} and res["stragglers"] == ["gov03"]
    g3 = rack.nodes[3].governor
    assert g3.epoch != rack.epoch
    r = rack.heartbeat()
    assert g3.log.has("deny.heartbeat", why=reasons.POLICY_STALE_EPOCH)
    assert not rack.nodes[3].gpu.running and g3.cause == reasons.EPOCH_STRAGGLER      # at once, not at expiry
    for _ in range(3):
        rack.tick(seconds=2.0)
        rack.heartbeat()
    assert not rack.nodes[3].gpu.running
    assert all(rack.nodes[i].gpu.running for i in range(3))


def test_staged_but_uncommitted_governor_is_expelled_at_the_deadline(rack):
    """gov03 acknowledged the proposal but its POLICY_COMMIT never arrived. It accepts new-epoch
    heartbeats only until the policy's epoch deadline, then halts as an epoch straggler; it cannot
    mint under the old rules and its ports to the new-epoch peers are closed."""
    from govsim.policy import policy_epoch
    image = rack.new_policy()
    new = policy_epoch(image)
    for n in rack.nodes:
        assert n.governor.command("POLICY_PROPOSE", {"image": image})["ok"]
    for n in rack.nodes[:3]:
        assert n.governor.command("POLICY_COMMIT", {"epoch": new})["ok"]
    rack.policy, rack.epoch = image, new
    g3 = rack.nodes[3].governor
    deadline = g3.policy["fabric"]["epoch_deadline_s"]
    rack.tick(seconds=deadline / 2)
    rack.heartbeat()
    assert g3.state == "RUN"                                                   # inside the deadline: the staged epoch is good
    for _ in range(8):
        rack.tick(seconds=2.0)
        rack.heartbeat()
    assert g3.epoch != new and g3.staged is not None
    assert g3.state != "RUN" and g3.cause == reasons.EPOCH_STRAGGLER and not rack.nodes[3].gpu.running
    assert g3.state == g3.policy["safe_mode"]["causes"][reasons.EPOCH_STRAGGLER]
    from conftest import pay
    assert pay(rack, rack.nodes[3], 1, governor=g3)["why"] == reasons.MBOX_NOT_RUNNING
    assert g3.switches["nvswitch"].table == {}
    assert all(rack.nodes[i].gpu.running for i in range(3))


def test_a_long_heartbeat_window_is_clamped_to_the_policy_expiry(rack1):
    node = rack1.nodes[0]
    g = node.governor
    assert rack1.heartbeat(window_s=365 * 86400)["ok"]
    assert g.hb_expiry - rack1.clock.now() <= g.policy["fabric"]["heartbeat_expiry_s"]
    rack1.tick(seconds=6.0)
    assert not node.gpu.running and g.cause == reasons.HEARTBEAT_LOST


def test_an_old_heartbeat_after_a_restart_is_dropped(rack1):
    node = rack1.nodes[0]
    g = node.governor
    now = rack1.clock.now()
    old = rack1.sign_heartbeat({"type": "heartbeat", "seq": 1, "epoch": rack1.epoch, "window_start": now - 1, "window_end": now + 3600})
    assert g.command("HEARTBEAT", {}, old)["why"] == reasons.HEARTBEAT_REPLAY
    g.restart()
    r = g.command("HEARTBEAT", {}, old)
    assert not r["ok"] and r["why"] == reasons.HEARTBEAT_REPLAY
    assert g.state == "HALTED_INITIAL" and g.hb_expiry < now


def test_heartbeat_outside_its_window_is_refused(rack1):
    g = rack1.nodes[0].governor
    now = rack1.clock.now()
    expiry_before = g.hb_expiry
    for start, end in ((now - 10, now - 1), (now + 10, now + 20)):               # already over, or not yet valid
        rack1.hb_seq += 1
        env = rack1.sign_heartbeat({"type": "heartbeat", "seq": rack1.hb_seq, "epoch": rack1.epoch, "window_start": start, "window_end": end})
        r = g.command("HEARTBEAT", {}, env)
        assert not r["ok"] and r["why"] == reasons.HEARTBEAT_EXPIRED
    assert g.hb_expiry == expiry_before
