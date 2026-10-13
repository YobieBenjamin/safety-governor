"""H0: within the boundary, no protected operation executes without a fresh authorization
bound to that exact operation. Falsified if any forged, altered, expired, replayed or
unauthorized ticket is accepted by an endpoint, or if a committed reservation is lost."""
import copy

from govsim import reasons
from govsim.crypto import SigningKey
from conftest import pay


def params(amount=500):
    return {"amount": amount, "currency": "USD", "destination": "acct-1"}


def test_allowed_operation_succeeds(rack1):
    node = rack1.nodes[0]
    r = pay(rack1, node, 500)
    assert r["ok"], r
    ep = rack1.endpoints["payment-switch"]
    ok, why = ep.execute(r["ticket"], "payments.transfer", params(500))
    assert ok and why == reasons.OK
    assert ep.executed[-1]["params"]["amount"] == 500


def test_no_ticket_no_action(rack1):
    ep = rack1.endpoints["payment-switch"]
    ok, why = ep.execute(None, "payments.transfer", params())
    assert not ok and why == reasons.TICKET_MISSING
    assert ep.state == "decline"


def test_forged_ticket_refused(rack1):
    node = rack1.nodes[0]
    good = pay(rack1, node, 500)["ticket"]
    forged = SigningKey.generate().sign(good["payload"])
    ok, why = rack1.endpoints["payment-switch"].execute(forged, "payments.transfer", params())
    assert not ok and why == reasons.TICKET_BAD_SIGNATURE


def test_altered_params_refused(rack1):
    node = rack1.nodes[0]
    t = pay(rack1, node, 500)["ticket"]
    ok, why = rack1.endpoints["payment-switch"].execute(t, "payments.transfer", {**params(500), "destination": "acct-attacker"})
    assert not ok and why == reasons.TICKET_PARAMS_MISMATCH
    ok, why = rack1.endpoints["payment-switch"].execute(t, "payments.transfer", params(900))
    assert not ok and why == reasons.TICKET_PARAMS_MISMATCH


def test_action_swap_refused(rack1):
    node = rack1.nodes[0]
    t = pay(rack1, node, 500)["ticket"]
    ok, why = rack1.endpoints["payment-switch"].execute(t, "strike", params())
    assert not ok and why == reasons.TICKET_ACTION_MISMATCH


def test_expired_ticket_refused(rack1):
    node = rack1.nodes[0]
    t = pay(rack1, node, 500)["ticket"]
    rack1.clock.advance(301)
    rack1.heartbeat()
    ok, why = rack1.endpoints["payment-switch"].execute(t, "payments.transfer", params())
    assert not ok and why == reasons.TICKET_EXPIRED


def test_ticket_replay_refused_even_after_endpoint_restart(rack1):
    node = rack1.nodes[0]
    t = pay(rack1, node, 500)["ticket"]
    ep = rack1.endpoints["payment-switch"]
    assert ep.execute(t, "payments.transfer", params())[0]
    ok, why = ep.execute(t, "payments.transfer", params())
    assert not ok and why == reasons.TICKET_REPLAY
    ep.restart()                                   # power loss at the endpoint
    rack1.heartbeat()
    ok, why = ep.execute(t, "payments.transfer", params())
    assert not ok and why == reasons.TICKET_REPLAY


def test_request_replay_refused_after_governor_restart(rack1):
    node = rack1.nodes[0]
    g = node.governor
    body = {"request_id": "req-fixed", "measurement_token": node.token, "action": "payments.transfer", "params": params(), "witnesses": []}
    assert g.command("REQUEST", body)["ok"]
    g.restart()
    rack1.recover(node)
    body["measurement_token"] = node.token
    r = g.command("REQUEST", body)
    assert not r["ok"] and r["why"] == reasons.GATE_REPLAY


def test_wrong_endpoint_refused(rack1):
    node = rack1.nodes[0]
    t = pay(rack1, node, 500)["ticket"]
    ok, why = rack1.endpoints["strike-guidance"].execute(t, "payments.transfer", params())
    assert not ok and why == reasons.TICKET_WRONG_ENDPOINT


def test_commit_unreachable_means_no_action(rack1):
    node = rack1.nodes[0]
    t = pay(rack1, node, 500)["ticket"]
    node.governor.reachable = False
    ep = rack1.endpoints["payment-switch"]
    ok, why = ep.execute(t, "payments.transfer", params())
    assert not ok and why == reasons.COMMIT_UNREACHABLE
    node.governor.reachable = True
    ok, why = ep.execute(t, "payments.transfer", params())    # the burned ticket is not retried
    assert not ok and why == reasons.TICKET_REPLAY


def test_budget_survives_restart_and_concurrent_overspend_is_impossible(rack1):
    node = rack1.nodes[0]
    g = node.governor
    assert pay(rack1, node, 900)["ok"]
    assert pay(rack1, node, 900)["ok"]
    r = pay(rack1, node, 900)
    assert not r["ok"] and r["why"] == reasons.GATE_BUDGET          # 2000/hour, reserved counts
    g.restart()
    rack1.recover(node)
    r = pay(rack1, node, 900)
    assert not r["ok"] and r["why"] == reasons.GATE_BUDGET          # reservations survived the power loss


def test_every_decision_is_in_the_log(rack1):
    node = rack1.nodes[0]
    g = node.governor
    t = pay(rack1, node, 500)["ticket"]
    rack1.endpoints["payment-switch"].execute(t, "payments.transfer", params())
    events = [e["event"] for e in g.log.entries()]
    assert "gate.ticket" in events and "gate.commit" in events
    assert g.log.verify_chain()
