"""H11: a halt propagates to every GPU in the domain within the bound, fail-safe. Falsified if
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
