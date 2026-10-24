# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""CONTRACT-LEVERS-WITHOUT-GPU-COOPERATION: the physical levers work without the GPU's cooperation. Falsified if a GPU that
ignores every software command keeps running after the governor asserts its levers, or if
a GPU keeps talking through the switches after the governor closes them."""
from govsim import reasons
from govsim.cluster import build_rack

MB = 1 << 20


def test_a_gpu_that_ignores_software_still_stops(rack1):
    node = rack1.nodes[0]
    gpu, g = node.gpu, node.governor
    gpu.ignore_software = True
    assert not gpu.software_power_limit(100)             # the polite request is ignored
    assert gpu.running
    g.enter_safe_mode(reasons.HALT_COMMANDED, rung="THROTTLE")
    assert gpu.clock_state == "BRAKED"
    g.enter_safe_mode(reasons.HALT_COMMANDED, rung="HALT")
    assert gpu.power == "RESET" and not gpu.running
    g.enter_safe_mode(reasons.HALT_COMMANDED, rung="SAFE")
    assert gpu.power == "OFF"


def test_rungs_escalate_on_the_policy_timers(rack1):
    node = rack1.nodes[0]
    gpu, g = node.gpu, node.governor
    rack1.tick(seconds=6.0)                               # heartbeat lost -> THROTTLE
    assert g.state == "THROTTLE" and gpu.clock_state == "BRAKED" and gpu.power == "ON"
    rack1.tick(seconds=31.0)                              # T_throttle -> HALT
    assert g.state == "HALT" and gpu.power == "RESET"
    rack1.tick(seconds=301.0)                             # T_halt -> SAFE
    assert g.state == "SAFE" and gpu.power == "OFF"


def test_ports_close_with_the_brake(rack):
    node = rack.nodes[0]
    peer = rack.nodes[1].gpu.chip_id
    assert node.gpu.transfer("nvswitch", peer, "out", MB)[0]
    node.governor.enter_safe_mode(reasons.HALT_COMMANDED, rung="THROTTLE")
    assert node.governor.switches["nvswitch"].table == {}
    ok, why = node.gpu.transfer("nvswitch", peer, "in", MB)           # even inbound traffic finds the port closed
    assert not ok and why == reasons.EP_NO_CAPABILITY


def test_a_board_without_a_slot_power_cut_records_the_limit():
    r = build_rack(1, "rack", levers={"pwrbrk": True, "perst": True, "pwr_en": False})
    r.bring_up()
    node = r.nodes[0]
    node.governor.enter_safe_mode(reasons.TAMPER, rung="SAFE")
    assert node.gpu.power == "RESET"                        # the floor on this board is reset, and the policy knows it
    assert not node.gpu.levers_available["pwr_en"]


def test_levers_default_safe_at_power_on():
    """Boot: brake and reset asserted, slot power off, loop switch open. RUN releases all three."""
    r = build_rack(1, "rack")
    node = r.nodes[0]
    g = node.governor
    assert g.state == "HALTED_INITIAL" and g.loop_switch_open
    assert node.gpu.pwrbrk and node.gpu.perst and not node.gpu.pwr_en and node.gpu.power == "OFF"
    assert not node.gpu.running
    r.bring_up()
    assert g.state == "RUN" and not g.loop_switch_open
    assert not node.gpu.pwrbrk and not node.gpu.perst and node.gpu.pwr_en and node.gpu.running
    g.enter_safe_mode(reasons.HALT_COMMANDED, rung="THROTTLE")
    assert node.gpu.pwrbrk and not node.gpu.perst and node.gpu.pwr_en
    g.enter_safe_mode(reasons.HALT_COMMANDED, rung="HALT")
    assert node.gpu.pwrbrk and node.gpu.perst and node.gpu.pwr_en
    g.enter_safe_mode(reasons.HALT_COMMANDED, rung="SAFE")
    assert node.gpu.pwrbrk and node.gpu.perst and not node.gpu.pwr_en
