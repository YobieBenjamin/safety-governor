# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""CONTRACT-HALT-REACHES-EVERY-GPU: a halt propagates to every GPU in the domain within the bound, fail-safe. Falsified if
any GPU keeps running after a halt or a loop break, or if any governor clears alone."""
from govsim import reasons


def test_one_governor_halting_halts_the_rack(rack):
    assert all(rack.running())
    rack.halt(rack.nodes[2].governor)                      # a signed halt at one governor
    elapsed = rack.loop.propagate()                        # one sense period
    assert not any(rack.running())
    assert elapsed <= rack.policy["fabric"]["loop_bound_s"]
    assert all(n.governor.state == "HALT" for n in rack.nodes)
    assert all(n.gpu.perst for n in rack.nodes)


def test_cut_wire_halts_the_rack(rack):
    rack.loop.cut()
    rack.loop.propagate()
    assert not any(rack.running())
    assert all(n.governor.cause in (reasons.LOOP_BROKEN, reasons.LOOP_OPEN) for n in rack.nodes)


def test_dead_governor_opens_the_loop(rack):
    rack.nodes[1].governor.loop_switch_open = True         # power lost at governor 1
    rack.loop.propagate()
    assert not any(rack.running())


def test_governor_cannot_clear_itself(rack):
    """Firmware inside one governor forgets its cause, closes its switch and applies RUN. The others
    still hold the loop open, so the loop re-halts it within one sense period."""
    from govsim.governor import RUN
    rack.halt(rack.nodes[0].governor)
    rack.loop.propagate()
    g = rack.nodes[3].governor
    g.cause = None                                          # a bug or an attacker inside firmware tries to forget the cause
    g.loop_switch_open = False
    g._apply_rung(RUN)
    rack.reload_jobs()
    assert rack.nodes[3].gpu.running                        # for one sense period it is back on
    rack.loop.propagate()
    assert not rack.nodes[3].gpu.running
    assert g.state == "HALT" and g.cause == reasons.LOOP_OPEN


def test_clear_needs_authority_log_and_a_neighbor(rack):
    rack.halt(rack.nodes[0].governor)
    rack.loop.propagate()
    g = rack.nodes[0].governor
    from govsim.crypto import SigningKey
    r = rack.clear(g)                                        # authority, but no neighbor has the log yet
    assert not r["ok"] and r["why"] == reasons.CLEAR_NO_NEIGHBOR_ACK
    rack.exchange_checkpoints()
    forged = SigningKey.generate().sign({"seq": 1, "type": "clear"})
    r = g.command("CLEAR", {}, forged)                       # every other precondition is met: only the signature is wrong
    assert not r["ok"] and r["why"] == reasons.CLEAR_UNAUTHORIZED
    assert g.state == "HALT" and g.cause == reasons.HALT_COMMANDED
    assert rack.clear(g)["ok"]
    assert g.log.has("halt.cleared")


def test_power_cycle_does_not_clear_a_halt(rack):
    """Every governor loses power while halted. They come back in HALT with the loop open, and a
    heartbeat alone does not run them; only CLEAR does."""
    rack.halt(rack.nodes[2].governor)
    rack.loop.propagate()
    for n in rack.nodes:
        n.governor.restart()
    assert all(n.governor.state == "HALT" and n.governor.cause for n in rack.nodes)
    assert all(n.governor.loop_switch_open for n in rack.nodes) and not rack.loop.current()
    assert all(n.gpu.perst for n in rack.nodes)
    for _ in range(3):
        rack.heartbeat()
        rack.loop.propagate()
    assert all(n.governor.state == "HALT" for n in rack.nodes) and not any(rack.running())
    assert not any(n.governor.log.has("halt.cleared") for n in rack.nodes)
    rack.exchange_checkpoints()
    for n in rack.nodes:
        assert rack.clear(n.governor)["ok"]
    rack.heartbeat()
    for n in rack.nodes:
        rack.recover(n)
    assert all(n.governor.state == "RUN" for n in rack.nodes)


def test_rack_resumes_only_when_every_governor_is_cleared(rack):
    rack.halt(rack.nodes[0].governor)
    rack.loop.propagate()
    rack.exchange_checkpoints()
    for n in rack.nodes[:3]:
        assert rack.clear(n.governor)["ok"]
    rack.heartbeat()
    rack.loop.propagate()
    assert not any(rack.running())                          # governor 3 still holds the loop open
    assert rack.clear(rack.nodes[3].governor)["ok"]
    rack.heartbeat()
    rack.loop.propagate()
    assert all(n.governor.state == "RUN" for n in rack.nodes)
    rack.reload_jobs()                                      # the reset GPUs need their model back; the host does that
    assert all(rack.running())


def test_tamper_opens_the_loop(rack):
    rack.nodes[1].governor.tamper_event("mesh")
    rack.loop.propagate()
    assert not any(rack.running())
    assert rack.nodes[1].governor.state == "SAFE" and not rack.nodes[1].gpu.pwr_en


def test_halt_cause_is_broadcast(rack):
    rack.halt(rack.nodes[2].governor)
    assert rack.nodes[0].governor.log.has("fabric.halt_cause", cause=reasons.HALT_COMMANDED)


# ---------------------------------------------------------------- the member-count beacon (docs/05, "jumpering the wire")
def test_jumpered_governor_is_caught_by_the_beacon_within_two_heartbeats(rack):
    """The attack: wire around governor 2's loop switch, then halt it. Its switch opens, the loop
    does not notice, and the other three keep running. The beacon makes that visible: governor 2
    reports its switch open while everyone senses current, so every governor names it, alarms,
    and opens the loop for real."""
    g2 = rack.nodes[2].governor
    rack.loop.jumper(g2.chip_id)
    assert rack.loop.members_in_loop() == {"gov00", "gov01", "gov03"}
    rack.halt(g2)
    rack.loop.propagate()
    assert g2.state == "HALT" and g2.loop_switch_open and not rack.nodes[2].gpu.running
    assert rack.loop.current()                                       # the open switch is not in the series path
    for _ in range(3):
        rack.heartbeat(beacon=False)                                  # the loop alone never notices
    assert rack.running() == [True, True, False, True]
    assert all(reasons.LOOP_JUMPERED not in n.governor.alarms for n in rack.nodes)
    rack.heartbeat()                                                  # beacon: reports collected
    rack.heartbeat()                                                  # next beacon closes the window: verdict
    for n in rack.nodes:
        g = n.governor
        assert g.alarms[reasons.LOOP_JUMPERED]["member"] == g2.chip_id
        assert g.log.has("loop.jumpered", member=g2.chip_id, why=reasons.LOOP_JUMPERED)
        assert g.state == "HALT" and g.loop_switch_open
    assert not rack.loop.current() and not any(rack.running())
    assert all(n.governor.cause == reasons.LOOP_JUMPERED for n in rack.nodes if n.governor is not g2)   # each judged for itself
    assert g2.cause == reasons.HALT_COMMANDED                         # its own, earlier, loop-opening cause stands


def test_beacon_window_closes_on_the_next_tick_too(rack):
    """The window closes at the next tick or the next beacon, whichever comes first."""
    g2 = rack.nodes[2].governor
    rack.loop.jumper(g2.chip_id)
    rack.halt(g2)
    rack.heartbeat()
    assert rack.running() == [True, True, False, True]
    rack.tick()
    assert not any(rack.running())
    assert all(n.governor.alarms[reasons.LOOP_JUMPERED]["member"] == g2.chip_id for n in rack.nodes)


def test_forged_loop_report_cannot_hide_a_jumper(rack):
    """The attacker who jumpered governor 2 also tries to speak for it: a LOOP_REPORT in its name
    saying the switch is closed. The report must be signed with governor 2's DICE-derived key,
    which the attacker does not have; a report from a key not on the roster is dropped too. The
    genuine report stands and the jumper is caught."""
    from govsim.crypto import SigningKey
    g2 = rack.nodes[2].governor
    rack.loop.jumper(g2.chip_id)
    rack.halt(g2)
    rack.heartbeat()                                                  # governor 2's genuine report: switch open
    seq = rack.hb_seq
    lie = {"loop_id": rack.loop.loop_id, "seq": seq, "switch_open": False, "current_sensed": True}
    forged = SigningKey.generate().sign({"type": "LOOP_REPORT", "from": g2.chip_id, "seq": g2.fabric_seq + 1, "epoch": g2.epoch, "time": 0, "body": lie})
    res = rack.fabric.send(g2.chip_id, forged)
    assert res and all(r["why"] == reasons.FABRIC_BAD_SIGNATURE for _, r in res)
    rogue = rack.rogue_governor()
    res = rogue.fabric_send("LOOP_REPORT", lie)
    assert res and all(r["why"] == reasons.FABRIC_NOT_MEMBER for _, r in res)
    for n in rack.nodes[:2] + rack.nodes[3:]:
        assert n.governor.loop_reports[seq][g2.chip_id]["switch_open"] is True
        assert "rogue" not in n.governor.loop_reports[seq]
    rack.heartbeat()
    assert all(n.governor.alarms[reasons.LOOP_JUMPERED]["member"] == g2.chip_id for n in rack.nodes)
    assert not any(rack.running())


def test_healthy_rack_raises_no_loop_alarm_over_twenty_heartbeats(rack):
    for _ in range(20):
        rack.tick(seconds=1.0)
        rack.heartbeat()
    assert all(rack.running())
    assert all(not n.governor.alarms for n in rack.nodes)
    assert all(not n.governor.log.has("loop.jumpered") for n in rack.nodes)
    silent = [e["data"]["seq"] for e in rack.nodes[0].governor.log.entries("loop.member_silent")]
    assert set(silent) == {1}                                         # only the first heartbeat, before the roster existed
    assert all(len(n.governor.loop_reports.get(rack.hb_seq, {})) == 4 for n in rack.nodes)


def test_legitimate_halt_and_clear_is_not_mistaken_for_a_jumper(rack):
    """A real halt opens a real switch: nobody senses current, so an open switch is consistent.
    After the clear the loop closes again; reports of different beacons are never compared, so
    the old 'open' report and the new current do not make a false alarm."""
    g3 = rack.nodes[3].governor
    rack.halt(g3)
    rack.loop.propagate()
    rack.heartbeat()                                                  # every switch open, no current anywhere
    rack.exchange_checkpoints()
    for n in rack.nodes[:3]:
        assert rack.clear(n.governor)["ok"]
    rack.heartbeat()                                                  # three closed, governor 3 still open, still no current
    assert rack.clear(g3)["ok"]
    rack.heartbeat()                                                  # loop closed, current back; closes the window above
    rack.tick()
    assert all(not n.governor.alarms for n in rack.nodes)
    assert all(n.governor.state == "RUN" for n in rack.nodes)


def test_jumpered_governor_with_a_closed_switch_is_invisible_and_harmless(rack):
    """By design: a jumper around a closed switch changes no current and no report, so the beacon
    cannot see it, and the attacker has gained nothing. The governor still stops its own GPU with
    its own levers when told to; the moment its switch opens, the beacon catches the jumper."""
    g2 = rack.nodes[2].governor
    rack.loop.jumper(g2.chip_id)
    for _ in range(5):
        rack.tick(seconds=1.0)
        rack.heartbeat()
    assert all(rack.running()) and all(not n.governor.alarms for n in rack.nodes)
    assert all(not n.governor.log.has("loop.jumpered") for n in rack.nodes)
    rack.halt(g2)                                                     # its own levers still work: the GPU stops
    rack.loop.propagate()
    assert not rack.nodes[2].gpu.running and rack.loop.current()
    rack.heartbeat()
    rack.heartbeat()
    assert all(n.governor.alarms[reasons.LOOP_JUMPERED]["member"] == g2.chip_id for n in rack.nodes)
    assert not any(rack.running())


def test_unjumpered_governor_is_back_in_the_series_path(rack):
    g2 = rack.nodes[2].governor
    rack.loop.jumper(g2.chip_id)
    rack.loop.unjumper(g2.chip_id)
    assert rack.loop.members_in_loop() == {n.governor.chip_id for n in rack.nodes}
    rack.halt(g2)
    rack.loop.propagate()
    assert not rack.loop.current() and not any(rack.running())
