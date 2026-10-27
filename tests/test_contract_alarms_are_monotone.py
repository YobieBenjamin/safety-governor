# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""CONTRACT-ALARMS-ARE-MONOTONE: alarms are monotone. Any party may raise one; it is cleared only by a rule the chip
can check or by an approver key. Falsified if an alarm is cleared without a rule or key."""
from govsim import reasons
from govsim.crypto import SigningKey
from conftest import pay


def test_anyone_may_raise_and_it_blocks_the_gate(rack1):
    node = rack1.nodes[0]
    g = node.governor
    assert pay(rack1, node, 10)["ok"]
    assert g.command("ALARM_RAISE", {"code": "classifier.stop", "source": "model"})["ok"]
    r = pay(rack1, node, 10)
    assert not r["ok"] and r["why"] == reasons.GATE_ALARM


def test_host_cannot_clear(rack1):
    node = rack1.nodes[0]
    g = node.governor
    g.raise_alarm("classifier.stop", "model")
    r = g.command("ALARM_CLEAR", {"code": "classifier.stop"})
    assert not r["ok"] and r["why"] == reasons.ALARM_CLEAR_UNAUTHORIZED
    stranger = SigningKey.generate().sign({"seq": 1, "code": "classifier.stop"})
    r = g.command("ALARM_CLEAR", {}, stranger)
    assert not r["ok"] and r["why"] == reasons.ALARM_CLEAR_UNAUTHORIZED
    assert "classifier.stop" in g.alarms


def test_approver_key_clears_and_it_is_logged(rack1):
    node = rack1.nodes[0]
    g = node.governor
    g.raise_alarm("classifier.stop", "model")
    env = rack1.approvers["alarms"][0].sign({"seq": 1, "code": "classifier.stop", "type": "alarm_clear"})
    assert g.command("ALARM_CLEAR", {}, env)["ok"]
    assert "classifier.stop" not in g.alarms
    assert g.log.has("alarm.cleared", code="classifier.stop")


def test_alarm_survives_restart(rack1):
    node = rack1.nodes[0]
    g = node.governor
    g.raise_alarm("classifier.stop", "model")
    g.restart()
    assert "classifier.stop" in g.alarms


def test_alarm_propagates_over_the_fabric(rack):
    """A peer's alarm becomes an alarm on the other chips when two distinct members report it (adversarial audit 3:
    one lying member used to freeze the rack with one broadcast). One report is logged, not raised. A chip that is
    itself in trouble still stops its own GPU at once, and a cause that opens the loop stops the whole domain."""
    a, b, c = rack.nodes[0].governor, rack.nodes[1].governor, rack.nodes[2].governor
    a.raise_alarm("tamper.suspected", "governor")
    assert "tamper.suspected" in a.alarms and "tamper.suspected" not in c.alarms
    assert c.log.has("alarm.reported", code="tamper.suspected")
    b.raise_alarm("tamper.suspected", "governor")
    assert "tamper.suspected" in c.alarms and c.alarms["tamper.suspected"]["source"] == "fabric"
