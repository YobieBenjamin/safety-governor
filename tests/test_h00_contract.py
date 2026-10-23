# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
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
    assert g.command("REQUEST", {}, node.host_sign(body, g.epoch, "REQUEST"))["ok"]
    g.restart()
    rack1.recover(node)
    body["measurement_token"] = node.token
    r = g.command("REQUEST", {}, node.host_sign(body, g.epoch, "REQUEST"))
    assert not r["ok"] and r["why"] == reasons.GATE_REPLAY


def test_unsigned_request_is_refused(rack1):
    """A request must be signed by the host enclave the governor verified; the body alone is nothing."""
    node = rack1.nodes[0]
    g = node.governor
    body = {"request_id": "r", "measurement_token": node.token, "action": "payments.transfer", "params": params(), "witnesses": []}
    r = g.command("REQUEST", body)
    assert not r["ok"] and r["why"] == reasons.MBOX_BAD_SIGNATURE
    stranger = SigningKey.generate().sign({"seq": 1, "epoch": g.epoch, **body})
    r = g.command("REQUEST", {}, stranger)
    assert not r["ok"] and r["why"] == reasons.MBOX_BAD_SIGNATURE
    assert not g.log.has("gate.ticket")


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


def test_rate_window_trips(rack1):
    """The small-payment rule allows 100 requests a minute; the 101st is refused and the window recovers."""
    node = rack1.nodes[0]
    whys = [pay(rack1, node, 1)["why"] for _ in range(101)]
    assert whys[:100] == [reasons.OK] * 100 and whys[100] == reasons.GATE_RATE
    rack1.clock.advance(61)
    rack1.heartbeat()
    assert pay(rack1, node, 1)["ok"]


def test_governor_side_commit_rejects_a_stale_epoch_ticket(rack1):
    """The endpoint's epoch check is not the only one: the governor refuses to commit a ticket from the old epoch."""
    node = rack1.nodes[0]
    g = node.governor
    t = pay(rack1, node, 500)["ticket"]
    assert rack1.change_epoch(rack1.new_policy())["committed"]
    assert not g.commit_from_endpoint(t)
    assert g.log.has("gate.commit_rejected", why=reasons.TICKET_STALE_EPOCH)


def test_governor_side_commit_rejects_while_throttled(rack1):
    node = rack1.nodes[0]
    g = node.governor
    t = pay(rack1, node, 500)["ticket"]
    g.enter_safe_mode(reasons.HALT_COMMANDED, rung="THROTTLE")
    assert not g.commit_from_endpoint(t)
    assert g.log.has("gate.commit_rejected", why=reasons.MBOX_NOT_RUNNING)


def test_commit_through_the_mailbox_is_signed_by_the_endpoint(rack1):
    node = rack1.nodes[0]
    g = node.governor
    t = pay(rack1, node, 500)["ticket"]
    forged = SigningKey.generate().sign({"seq": 1, "epoch": g.epoch, "ticket": t})
    r = g.command("COMMIT", {}, forged)
    assert not r["ok"] and r["why"] == reasons.MBOX_BAD_SIGNATURE
    r = rack1.commit_via_mailbox(g, "payment-switch", t)
    assert r["ok"] and g.log.has("gate.commit", ticket_id=t["payload"]["ticket_id"])
    assert not rack1.commit_via_mailbox(g, "payment-switch", t)["ok"]        # the reservation is spent


def test_power_loss_at_every_save_point_never_double_spends(rack1):
    """The store fails at the n-th save inside a request, then at the m-th save inside its commit.
    After every such power loss: nothing reserved beyond the limit, no ticket without a
    reservation, and no action without a commit."""
    from govsim.store import PowerLoss
    node = rack1.nodes[0]
    g = node.governor
    ep = rack1.endpoints["payment-switch"]
    key, limit = "pay-usd-hourly", 2000

    def usage():
        return g.ledger.usage(key, 3600, rack1.clock.now())

    def fresh_window():
        g.ledger.budgets.pop(key, None)
        g.store.save()

    for n in range(1, 7):                                   # the request's save points
        g.store.fail_after(n)
        try:
            r = pay(rack1, node, 900)
        except PowerLoss:
            r = None
        g.store.fail_after(None)
        g.restart()
        rack1.recover(node)
        committed, reserved = usage()
        assert committed + reserved <= limit, n
        if r is not None and r["ok"]:
            assert r["ticket"]["payload"]["reservation"] in g.ledger.budgets[key]["reserved"], n
        fresh_window()
    for m in range(1, 4):                                   # the commit's save points
        t = pay(rack1, node, 900)["ticket"]
        g.store.fail_after(m)
        try:
            ok, _ = ep.execute(t, "payments.transfer", params(900))
        except PowerLoss:
            ok = False
        g.store.fail_after(None)
        g.restart()
        rack1.recover(node)
        committed, reserved = usage()
        assert committed + reserved <= limit, m
        acted = any(e["ticket"] == t["payload"]["ticket_id"] for e in ep.executed)
        assert acted == ok and (not acted or committed >= 900), m          # an action always has its commit
        ep.restart()
        rack1.heartbeat()
        fresh_window()


def test_every_ledger_step_saves_before_it_returns():
    """Each durable step is its own NVM write, so a power loss between steps loses nothing committed."""
    from govsim.clock import SimClock
    from govsim.ledger import Ledger
    from govsim.store import Store
    store, clock = Store(), SimClock()
    ledger = Ledger(store, clock)
    now = clock.now()
    for step in (lambda: ledger.reserve("k", 5, 100, 60, now, 30), lambda: ledger.mark("h", now), lambda: ledger.rate_ok("r", 10, 60, now)):
        before = store.writes
        step()
        assert store.writes == before + 1
    rid = ledger.reserve("k", 5, 100, 60, now, 30)
    before = store.writes
    assert ledger.commit("k", rid, now) and store.writes == before + 1
    rid = ledger.reserve("k", 5, 100, 60, now, 30)
    before = store.writes
    ledger.release("k", rid)
    assert store.writes == before + 1
