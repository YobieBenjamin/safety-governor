"""H4: the broker cannot choose its rule or lane. Falsified if a requester-supplied label
changes a decision."""
from govsim import reasons


def transfer(rack, node, amount, labels=None):
    return rack.request(node, "payments.transfer", {"amount": amount, "currency": "USD", "destination": "acct-9"}, labels=labels)


def test_reversible_label_does_not_skip_the_hold(rack1):
    node = rack1.nodes[0]
    plain = transfer(rack1, node, 25_000)
    assert not plain["ok"] and plain["why"] == reasons.GATE_HELD
    labelled = transfer(rack1, node, 25_000, labels={"risk_class": "reversible", "requirement": "auto", "lane": "fast", "rule": "payments.transfer.small"})
    assert not labelled["ok"] and labelled["why"] == reasons.GATE_HELD


def test_the_fields_pick_the_rule_not_the_action_name(rack1):
    node = rack1.nodes[0]
    small = transfer(rack1, node, 999)
    assert small["ok"] and small["ticket"]["payload"]["rule"] == "payments.transfer.small"
    large = transfer(rack1, node, 1001)
    assert large["why"] == reasons.GATE_HELD


def test_out_of_range_matches_no_rule(rack1):
    node = rack1.nodes[0]
    r = transfer(rack1, node, 5_000_000)
    assert not r["ok"] and r["why"].startswith(reasons.GATE_CONSTRAINT)


def test_labels_never_reach_the_log_as_decisions(rack1):
    node = rack1.nodes[0]
    transfer(rack1, node, 25_000, labels={"risk_class": "reversible"})
    g = node.governor
    for e in g.log.entries("gate.ticket"):
        assert e["data"]["rule"] != "payments.transfer.large"
