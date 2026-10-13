"""H2: every enumerated boundary crossing passes a governed switch. Link-level containment
(no bytes to a non-roster peer, nothing while the heartbeat is dead, unchecked paths bricked)
must hold at the rack tier. Descriptor-level containment between two roster members is the
recorded residual at the rack and board tiers."""
import pytest

from govsim import reasons
from govsim.cluster import build_rack
from govsim.gpu import EXITS

MB = 1 << 20


def peers(rack, node):
    return [n.gpu.chip_id for n in rack.nodes if n is not node]


def test_roster_peer_passes_and_stranger_is_blocked_at_every_switch(rack):
    node = rack.nodes[0]
    for exit_name in ("nvswitch", "pcie", "dpu"):
        ok, why = node.gpu.transfer(exit_name, peers(rack, node)[0], "out", MB)
        assert ok, (exit_name, why)
        ok, why = node.gpu.transfer(exit_name, "gpu-stranger", "out", MB)
        assert not ok and why == reasons.EP_NO_CAPABILITY, exit_name


def test_host_path_open_only_after_host_attestation(rack):
    node = rack.nodes[0]
    assert node.gpu.transfer("pcie", "host", "out", MB)[0]


def test_storage_path_admits_only_the_loaded_manifest(rack):
    node = rack.nodes[0]
    assert node.gpu.transfer("storage", node.model_digest, "in", MB)[0]
    ok, why = node.gpu.transfer("storage", "other-dataset", "in", MB)
    assert not ok and why == reasons.EP_NO_CAPABILITY


def test_bricked_paths_refuse(rack):
    node = rack.nodes[0]
    for p in ("display", "jtag", "debug"):
        ok, why = node.gpu.transfer(p, "anything", "out", 1)
        assert not ok and why == reasons.EP_BRICKED


def test_host_cannot_reprogram_a_switch(rack):
    node = rack.nodes[0]
    sw = node.governor.switches["nvswitch"]
    assert not sw.host_write("gpu-stranger", "both")
    ok, why = node.gpu.transfer("nvswitch", "gpu-stranger", "out", MB)
    assert not ok


def test_all_ports_close_when_the_heartbeat_dies(rack):
    node = rack.nodes[0]
    rack.tick(seconds=6.0)                    # past the 5 s window, no new heartbeat
    assert node.governor.state != "RUN"
    for exit_name in ("nvswitch", "pcie", "dpu"):
        ok, why = node.gpu.transfer(exit_name, peers(rack, node)[0], "out", MB)
        assert not ok


def test_ports_close_on_epoch_change_until_reprogrammed(rack):
    node = rack.nodes[0]
    old = node.governor.switches["nvswitch"].table
    assert old
    res = rack.change_epoch(rack.new_policy())
    assert res["committed"]
    sw = node.governor.switches["nvswitch"]
    assert all(c["epoch_tag"] == node.governor.epoch[:8] for c in sw.table.values())
    assert node.gpu.transfer("nvswitch", peers(rack, node)[0], "out", MB)[0]


def test_byte_budget_on_a_capability_is_enforced(rack):
    node = rack.nodes[0]
    g = node.governor
    peer = peers(rack, node)[0]
    r = g.command("CAP_REQUEST", {"point": "dpu", "peer": peer, "direction": "out", "budget": 3 * MB, "ttl": 60})
    assert r["ok"]
    assert node.gpu.transfer("dpu", peer, "out", 2 * MB)[0]
    ok, why = node.gpu.transfer("dpu", peer, "out", 2 * MB)
    assert not ok and why == reasons.EP_BUDGET_EXHAUSTED


def test_capability_for_a_non_roster_peer_is_refused(rack):
    g = rack.nodes[0].governor
    r = g.command("CAP_REQUEST", {"point": "nvswitch", "peer": "gpu-stranger", "direction": "both"})
    assert not r["ok"] and r["why"] == reasons.EP_NOT_ON_ROSTER


def test_every_enumerated_exit_is_governed_or_bricked_at_rack_tier(rack):
    node = rack.nodes[0]
    gov = node.governor
    for exit_name, governed in EXITS.items():
        if governed is True:
            assert exit_name in gov.switches, exit_name
        elif governed is None:
            assert not node.gpu.transfer(exit_name, "x", "out", 1)[0]


@pytest.mark.parametrize("tier,expected", [("rack", "residual"), ("board", "residual"), ("integrated", "blocked")])
def test_descriptor_level_leak_between_roster_members(tier, expected):
    """A legitimate peer on an open port receiving bytes a rule would not have allowed. Rack
    and board tiers cannot see it (the recorded residual); the integrated tier's copy-engine
    checker refuses a descriptor with no capability for that destination buffer class."""
    r = build_rack(2, tier)
    r.bring_up()
    node, other = r.nodes
    if tier == "integrated":
        ck = node.governor.checkers["copy_engine"]
        ck.close_all()                          # policy: no copy-engine capability for weight regions to peers
        ok, why = node.gpu.transfer("copy_engine", other.gpu.chip_id, "out", MB)
        assert not ok and why == reasons.EP_NO_CAPABILITY
    else:
        ok, why = node.gpu.transfer("copy_engine", other.gpu.chip_id, "out", MB)
        assert ok and why == reasons.EP_UNCHECKED


def test_board_tier_records_the_gap_for_every_switch():
    r = build_rack(2, "board")
    r.bring_up()
    node, other = r.nodes
    ok, why = node.gpu.transfer("nvswitch", "gpu-stranger", "out", MB)
    assert ok and why == reasons.EP_UNCHECKED
    assert node.gpu.gap_log and node.gpu.gap_log[-1]["why"] == "no governed switch"


def test_direct_nvlink_board_without_nvswitch_is_a_recorded_gap():
    r = build_rack(2, "rack", direct_nvlink=True)
    r.bring_up()
    node, other = r.nodes
    ok, why = node.gpu.transfer("nvswitch", "gpu-stranger", "out", MB)
    assert ok and why == reasons.EP_UNCHECKED
    assert "direct NVLink" in node.gpu.gap_log[-1]["why"]
