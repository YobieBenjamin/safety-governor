"""Yobie's two design calls of 23 October 2026 in the functional model ("silently failing is a bullshit feature").

1. A signed HALT to a governor already in SAFE opens its loop switch; the governor stays in SAFE with slot power off
   (conformance F-07: the model used to drop to HALT and turn the power back on).
2. A governor that never gets its first heartbeat keeps holding the rack, loudly: NO_FIRST_HEARTBEAT past the boot
   window, logged with the chip and since when. The way out is EXCLUDE: signed by the authority, bound to the chip,
   expiring, logged with its signer. The excluded chip closes its loop switch and keeps its own levers on.
The RTL side is rtl/tests/test_yobie_calls.py and rtl/formal (halt_seq.sv, governor_core.sv).
"""
from govsim import reasons
from govsim.cluster import build_rack
from govsim.crypto import SigningKey
from govsim.governor import BOOT_WINDOW_S, HALTED_INITIAL, RUN, SAFE

from conftest import pay

OFF = {"pwrbrk": True, "perst": True, "pwr_en": False}


# ------------------------------------------------------------------------------------------- call 1: HALT in SAFE
def test_halt_to_a_governor_in_safe_opens_the_loop_and_stays_safe():
    rack = build_rack(2, "rack")
    rack.bring_up()
    g, other = rack.nodes[0].governor, rack.nodes[1].governor
    g.enter_safe_mode(reasons.HEARTBEAT_LOST)
    g._apply_rung("HALT", opens_loop=False)
    g._apply_rung("SAFE", opens_loop=False)
    assert g.state == SAFE and g.loop_switch_open is False and rack.loop.current()
    assert rack.halt(g)["ok"]
    assert g.state == SAFE and g.levers == OFF, f"model went to {g.state}, levers {g.levers}"
    assert g.loop_switch_open is True and not rack.loop.current()
    entry = g.log.entries("halt.cause")[-1]["data"]
    assert entry["cause"] == reasons.HALT_COMMANDED and entry["rung"] == SAFE and entry["requested"] == "HALT"
    rack.tick()
    assert other.state != RUN                                  # the neighbour stopped too: the loop opened


# ------------------------------------------------------------------------------- call 2: the first heartbeat
def stuck_rack():
    """Three governors; the third never gets its first heartbeat (its fabric port is unplugged, so the fan-out
    never reaches it). Nobody runs: its switch is open, so there is no loop current."""
    rack = build_rack(3, "rack")
    stuck = rack.nodes[2].governor
    rack.fabric.down.add(stuck.chip_id)
    rack.heartbeat()
    return rack, stuck


def test_one_missing_first_heartbeat_holds_the_rack_and_says_so():
    rack, stuck = stuck_rack()
    assert all(n.governor.state == HALTED_INITIAL for n in rack.nodes)       # fail closed, unchanged
    rack.tick(BOOT_WINDOW_S / 2)
    assert reasons.NO_FIRST_HEARTBEAT not in stuck.alarms                   # inside the window: quiet
    rack.heartbeat()
    rack.tick(BOOT_WINDOW_S)
    assert reasons.NO_FIRST_HEARTBEAT in stuck.alarms, "a chip waiting past the boot window said nothing"
    a = stuck.alarms[reasons.NO_FIRST_HEARTBEAT]
    assert a["chip_id"] == stuck.chip_id and a["since"] == stuck.boot_at and a["source"] == "hardware"
    assert stuck.log.has("alarm.raised", code=reasons.NO_FIRST_HEARTBEAT, chip_id=stuck.chip_id)
    for n in rack.nodes[:2]:                                   # the armed ones are not the culprit, and say nothing
        assert reasons.NO_FIRST_HEARTBEAT not in n.governor.alarms
    assert reasons.CODES[reasons.NO_FIRST_HEARTBEAT] > max(v for k, v in reasons.CODES.items() if k not in reasons.ADDED)


def test_the_neighbours_log_it_when_the_fabric_reaches_them():
    """A rack that ran, then one board power-cycles and its first heartbeat after the reset never comes. Its switch
    opened at reset, so the rack is down (fail closed); its fabric still works, so the neighbours log who it is."""
    rack = build_rack(3, "rack")
    rack.bring_up()
    stuck = rack.nodes[2].governor
    stuck.restart()
    rack.tick(BOOT_WINDOW_S + 1)                               # no heartbeat for anyone after the reset
    assert reasons.NO_FIRST_HEARTBEAT in stuck.alarms
    for n in rack.nodes[:2]:
        assert n.governor.state != RUN                         # stopped by the open loop, not waiting for a heartbeat
        a = n.governor.alarms.get(reasons.NO_FIRST_HEARTBEAT)
        assert a is not None and a["chip_id"] == stuck.chip_id and a["source"] == "fabric"


def test_exclude_lets_the_rest_run_and_keeps_the_excluded_chip_off():
    rack, stuck = stuck_rack()
    rack.tick(BOOT_WINDOW_S + 1)
    r = rack.exclude(stuck)
    assert r["ok"], r
    assert stuck.excluded and stuck.state == HALTED_INITIAL and stuck.levers == OFF and stuck.loop_switch_open is False
    assert stuck.gpu.pwr_en is False and stuck.gpu.pwrbrk is True                # its own GPU is held off
    e = stuck.log.entries("exclude")[-1]["data"]
    assert e["by"] == rack.authority_key.public.key_id and e["chip_id"] == stuck.chip_id
    assert reasons.EXCLUDED in stuck.alarms and reasons.NO_FIRST_HEARTBEAT in stuck.alarms
    rack.heartbeat()
    assert [n.governor.state for n in rack.nodes] == [RUN, RUN, HALTED_INITIAL]
    assert stuck.levers == OFF
    for n in rack.nodes[:2]:
        rack.install_lists(n)
        rack.attest(n)
        rack.load_model(n)
    assert pay(rack, rack.nodes[0], 10)["ok"]                  # status alarms do not park a running neighbour's gate
    rack.fabric.heal()                                         # its heartbeat finally arrives: it arms normally
    rack.heartbeat()
    assert not stuck.excluded and stuck.state == RUN
    assert stuck.log.has("exclude.ended", by="heartbeat")


def test_exclude_is_refused_unless_the_chip_is_waiting_for_its_first_heartbeat():
    rack = build_rack(2, "rack")
    rack.bring_up()
    g = rack.nodes[0].governor
    r = rack.exclude(g)                                        # running
    assert not r["ok"] and r["why"] == reasons.EXCLUDE_NOT_WAITING and g.state == RUN
    assert rack.halt(g)["ok"]                                  # halted by a command: the loop stays open
    r = rack.exclude(g)
    assert not r["ok"] and r["why"] == reasons.EXCLUDE_NOT_WAITING and g.loop_switch_open
    assert g.log.has("deny.exclude", why=reasons.EXCLUDE_NOT_WAITING)
    h = rack.nodes[1].governor
    rack.loop.cut()                                            # halted by loop loss
    rack.tick()
    assert h.cause in (reasons.LOOP_BROKEN, reasons.HALT_COMMANDED) and not rack.exclude(h)["ok"] and h.loop_switch_open
    h.tamper_event()                                           # tamper: zeroized, nothing verifies at all
    assert rack.exclude(h)["why"] == reasons.TAMPER_ZEROIZED and h.loop_switch_open


def test_exclude_needs_the_authority_bound_to_this_chip_and_fresh():
    rack, stuck = stuck_rack()
    other = rack.nodes[0].governor
    payload = {"type": "exclude", "seq": 999, "epoch": rack.epoch, "chip_id": stuck.chip_id,
               "expires_at": rack.clock.now() + 30}
    for env, why in (
        (rack.heartbeat_key.sign(payload), reasons.MBOX_BAD_SIGNATURE),                    # never the heartbeat key
        (SigningKey.generate().sign(payload), reasons.MBOX_BAD_SIGNATURE),
        (rack.authority_key.sign({**payload, "type": "clear"}), reasons.MBOX_WRONG_COMMAND),  # typed
        (rack.authority_key.sign({**payload, "chip_id": other.chip_id}), reasons.MBOX_WRONG_COMMAND),  # bound to the chip
        (rack.authority_key.sign({**payload, "expires_at": rack.clock.now() - 1}), reasons.MBOX_EXPIRED),
        (rack.authority_key.sign({k: v for k, v in payload.items() if k != "expires_at"}), reasons.MBOX_EXPIRED),
    ):
        r = stuck.command("EXCLUDE", {}, env)
        assert not r["ok"] and r["why"] == why, (r, why)
        assert not stuck.excluded and stuck.loop_switch_open
    good = rack.authority_key.sign(payload)
    assert stuck.command("EXCLUDE", {}, good)["ok"]
    r = stuck.command("EXCLUDE", {}, good)                     # a replay is refused
    assert not r["ok"] and r["why"] == reasons.MBOX_BAD_SEQUENCE


def test_a_halt_ends_an_exclusion_with_the_loop_open_and_a_reset_forgets_it():
    rack, stuck = stuck_rack()
    assert rack.exclude(stuck)["ok"]
    assert rack.halt(stuck)["ok"]
    assert not stuck.excluded and stuck.loop_switch_open and stuck.log.has("exclude.ended", by="halt")
    rack2, stuck2 = stuck_rack()
    assert rack2.exclude(stuck2)["ok"]
    stuck2.restart()                                           # a reset ends it: the chip holds the rack again
    assert not stuck2.excluded and stuck2.loop_switch_open and stuck2.state == HALTED_INITIAL
