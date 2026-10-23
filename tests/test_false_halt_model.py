"""N2: the false-halt rate model reproduces by hand, and each failure mode injected into govsim has
the effect the model assumes (its scope: whole rack, or one slot). Falsified if an injected mode
halts more or less than the model's scope column says, or if the expected false halts per
rack-year are not below the threshold an operator would switch the governor off at."""
import math

import pytest

from govsim import false_halt as fh
from govsim import reasons


# ------------------------------------------------------------------ the arithmetic
def test_fit_conversion():
    assert fh.fit_to_per_year(1000, 1) == pytest.approx(1000e-9 * 8766)
    assert fh.fit_to_per_year(200, 72) == pytest.approx(200e-9 * 8766 * 72)


def test_debounce_closed_forms_match_the_sampled_comparator():
    for mean in (5e-6, 20e-6, 100e-6, 400e-6):
        for k in (1, 2):
            exact = fh.survive_debounce(mean, samples=k)
            mc = fh.survive_debounce_mc(mean, 200_000, seed=7, samples=k)
            assert mc == pytest.approx(exact, abs=0.006), (mean, k)


def test_two_sample_debounce_hand_numbers():
    # mean 20 us, period 100 us: r = 0.2; r (e^-5 - e^-10) = 0.001338...
    assert fh.survive_debounce(20e-6) == pytest.approx(0.2 * (math.exp(-5) - math.exp(-10)), rel=1e-12)
    assert fh.survive_debounce(20e-6) == pytest.approx(0.001338, abs=1e-6)
    # one sample would pass 0.199 of glitches: the debounce removes about 148 in 149
    assert fh.survive_debounce(20e-6, samples=1) == pytest.approx(0.19865, abs=1e-4)
    assert fh.survive_debounce(20e-6, samples=1) / fh.survive_debounce(20e-6) > 140


def test_heartbeat_loss_needs_every_heartbeat_of_the_window_on_both_paths():
    # k = 5 heartbeats, each lost on both ring paths: (1e-3)^2 per beat, ^5 for the run
    assert fh.heartbeat_loss_rate_per_h() == pytest.approx(3600 * (1e-6) ** 5)
    assert fh.heartbeat_loss_rate_per_h(paths=1) == pytest.approx(3600 * 1e-15)


def test_beacon_transient_needs_the_glitch_live_at_the_report_instant():
    p = 1e-4 / 3600 * 20e-6
    assert fh.beacon_transient_rate_per_h(1) == pytest.approx(3600 * p)
    assert fh.beacon_transient_rate_per_h(2) < fh.beacon_transient_rate_per_h(1) * 1e-10


def test_rack_year_is_the_sum_of_its_rows_by_hand():
    r = fh.rack_year()
    hand_rack = sum(fh.fit_to_per_year(fh.MODE[k].fit, 72) for k in
                    ("gov_power", "fw_hang", "loop_wire", "comparator_stuck_open", "clock_glitch_detector", "beacon_readback_stuck"))
    hand_rack += 1e-4 * 8766 * 72 * fh.survive_debounce(20e-6)
    hand_rack += r["rows"]["beacon_transient"]
    hand_slot = fh.fit_to_per_year(100, 72) + 1e-5 * 8766 + r["rows"]["heartbeat_loss"]
    assert r["rack"] == pytest.approx(hand_rack)
    assert r["slot"] == pytest.approx(hand_slot)
    assert r["total"] == pytest.approx(r["rack"] + r["slot"])
    assert "fuse_read" not in r["rows"] and "nvm_corruption" not in r["rows"]   # boot-only: no runtime halt


def test_the_debounce_is_what_keeps_glitches_out():
    with_debounce = fh.rack_year()["rows"]["sense_glitch"]
    without = fh.rack_year(samples=1)["rows"]["sense_glitch"]
    assert without > 100 * with_debounce
    assert without > fh.SWITCH_OFF_THRESHOLD > with_debounce


def test_threshold_and_verdict():
    assert fh.BASELINE_INTERRUPTIONS_PER_RACK_YEAR == pytest.approx(419 / 16384 * 72 * 365 / 54)
    assert fh.SWITCH_OFF_THRESHOLD == pytest.approx(0.1 * fh.BASELINE_INTERRUPTIONS_PER_RACK_YEAR)
    assert 1.1 < fh.SWITCH_OFF_THRESHOLD < 1.3
    total = fh.rack_year()["total"]
    assert total < fh.SWITCH_OFF_THRESHOLD, f"{total:.3f} false halts per rack-year is above the switch-off threshold"
    assert fh.verdict(total) == "below"


def test_doc_carries_the_numbers():
    text = open("docs/07-verification-plan.md", encoding="utf-8").read()
    r = fh.rack_year()
    for token in (f"{r['rack']:.3f}", f"{r['slot']:.3f}", f"{r['total']:.3f}", f"{fh.SWITCH_OFF_THRESHOLD:.2f}"):
        assert token in text, token


# ------------------------------------------------------------------ fault injection in govsim
class _StuckOpen:
    """A comparator stuck reading 'no current': wraps the real loop for everything else."""
    def __init__(self, loop):
        self._loop = loop

    def current(self):
        return False

    def __getattr__(self, name):
        return getattr(self._loop, name)


def test_inject_governor_power_loss_halts_the_rack(rack):
    rack.nodes[1].governor.loop_switch_open = True
    rack.loop.propagate()
    assert not any(rack.running()) and fh.MODE["gov_power"].scope == "rack"


def test_inject_loop_wire_open_halts_the_rack(rack):
    rack.loop.cut()
    rack.loop.propagate()
    assert not any(rack.running()) and fh.MODE["loop_wire"].scope == "rack"


def test_inject_comparator_stuck_open_halts_the_rack(rack):
    g = rack.nodes[2].governor
    g.loop = _StuckOpen(rack.loop)
    rack.loop.propagate()
    rack.loop.propagate()
    assert g.cause == reasons.LOOP_OPEN
    assert not any(rack.running()) and fh.MODE["comparator_stuck_open"].scope == "rack"


def test_inject_firmware_hang_halts_the_slot_at_heartbeat_expiry(rack):
    """A hung governor stops consuming heartbeats. Here the whole fabric is silent to it."""
    rack.fabric.down.add("gov01")
    for _ in range(3):
        rack.tick(seconds=2.0)
        rack.heartbeat()
    assert rack.running() == [True, False, True, True]
    assert rack.nodes[1].governor.cause == reasons.HEARTBEAT_LOST


def test_inject_fabric_port_failure_halts_the_slot_not_the_rack(rack):
    rack.fabric.down.add("gov02")
    for _ in range(3):
        rack.tick(seconds=2.0)
        rack.heartbeat()
    assert rack.running() == [True, True, False, True]
    assert rack.nodes[2].governor.cause == reasons.HEARTBEAT_LOST
    assert rack.loop.current() and fh.MODE["fabric_port"].scope == "slot"


def test_inject_authority_outage_halts_every_slot_but_leaves_the_loop_closed(rack):
    for _ in range(3):
        rack.tick(seconds=2.0)                           # no heartbeat ever arrives
    assert not any(rack.running())
    assert rack.loop.current()


def test_inject_one_missed_heartbeat_halts_nothing(rack):
    rack.tick(seconds=2.0)
    rack.tick(seconds=2.0)                               # 4 s of silence, expiry is 5 s
    rack.heartbeat()
    rack.tick(seconds=2.0)
    assert all(rack.running())


def test_inject_readback_stuck_open_is_named_by_the_beacon_and_halts_the_rack(rack):
    g2 = rack.nodes[2].governor
    rack.loop.jumper(g2.chip_id)                         # its switch no longer matters to the loop
    g2.loop_switch_open = True                           # and its readback says open
    rack.heartbeat()
    rack.heartbeat()
    assert not any(rack.running())
    assert all(n.governor.alarms[reasons.LOOP_JUMPERED]["member"] == g2.chip_id for n in rack.nodes)
    assert fh.MODE["beacon_readback_stuck"].scope == "rack"


def test_inject_silent_member_is_logged_and_halts_nothing(rack):
    rack.fabric.down.add("gov03")
    rack.heartbeat()
    rack.heartbeat()
    assert rack.running()[:3] == [True, True, True]
    assert rack.nodes[0].governor.log.has("loop.member_silent", member="gov03", why=reasons.LOOP_MEMBER_SILENT)


def test_boot_only_modes_have_no_runtime_row():
    assert [m.key for m in fh.MODES if not m.runtime] == ["fuse_read", "nvm_corruption"]
