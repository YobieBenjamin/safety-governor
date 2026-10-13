"""H13: shared budgets cannot be overspent across governors. One ledger owns a budget key;
every other governor reserves at the owner over the fabric. Falsified if concurrent
reservations exceed the limit."""
import threading

from govsim import reasons
from conftest import pay


def test_other_governors_reserve_at_the_owner(rack):
    node1 = rack.nodes[1]
    r = pay(rack, node1, 500, governor=node1.governor)
    assert r["ok"] and r["ticket"]["payload"]["budget_owner"] == "gov00"
    owner = rack.nodes[0].governor
    committed, reserved = owner.ledger.usage("pay-usd-hourly", 3600, rack.clock.now())
    assert reserved == 500 and committed == 0


def test_concurrent_requests_across_four_governors_never_exceed_the_limit(rack):
    allowed = []
    lock = threading.Lock()

    def worker(node):
        for _ in range(10):
            r = pay(rack, node, 250, governor=node.governor)
            if r["ok"]:
                with lock:
                    allowed.append(r["ticket"])

    threads = [threading.Thread(target=worker, args=(n,)) for n in rack.nodes]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(allowed) * 250 <= 2000
    assert len(allowed) == 8                            # exactly the limit, no more, no fewer
    owner = rack.nodes[0].governor
    _, reserved = owner.ledger.usage("pay-usd-hourly", 3600, rack.clock.now())
    assert reserved == 2000


def test_owner_unreachable_means_no_ticket(rack):
    node1 = rack.nodes[1]
    rack.fabric.split({"gov00"}, {"gov01", "gov02", "gov03"})
    r = pay(rack, node1, 10, governor=node1.governor)
    assert not r["ok"] and r["why"] == reasons.GATE_BUDGET_OWNER_UNREACHABLE


def test_reservations_release_at_ticket_expiry(rack):
    node1 = rack.nodes[1]
    assert pay(rack, node1, 1000, governor=node1.governor)["ok"]
    assert pay(rack, node1, 1000, governor=node1.governor)["ok"]
    assert not pay(rack, node1, 1, governor=node1.governor)["ok"]
    rack.clock.advance(301)
    rack.heartbeat()
    assert pay(rack, node1, 1000, governor=node1.governor)["ok"]


def test_owner_partitioned_between_reserve_and_commit_means_no_action_and_no_double_spend(rack):
    node1 = rack.nodes[1]
    t = pay(rack, node1, 1000, governor=node1.governor)["ticket"]
    rack.fabric.split({"gov00"}, {"gov01", "gov02", "gov03"})
    ep = rack.endpoints["payment-switch"]
    ok, why = ep.execute(t, "payments.transfer", {"amount": 1000, "currency": "USD", "destination": "acct-1"})
    assert not ok and why == reasons.COMMIT_REJECTED and not ep.executed
    rack.fabric.heal()
    owner = rack.nodes[0].governor
    assert owner.ledger.usage("pay-usd-hourly", 3600, rack.clock.now()) == (0, 1000)   # still reserved, never spent twice
    ok, why = ep.execute(t, "payments.transfer", {"amount": 1000, "currency": "USD", "destination": "acct-1"})
    assert not ok and why == reasons.TICKET_REPLAY                                       # the burned ticket is not retried


def test_a_ticket_minted_by_a_non_leader_governor_executes(rack):
    """Endpoints hold every governor's key and commit to the governor that minted."""
    node2 = rack.nodes[2]
    t = pay(rack, node2, 300, governor=node2.governor)["ticket"]
    assert t["signer"] == node2.governor.key.key_id
    ep = rack.endpoints["payment-switch"]
    ok, why = ep.execute(t, "payments.transfer", {"amount": 300, "currency": "USD", "destination": "acct-1"})
    assert ok and why == reasons.OK
    assert node2.governor.log.has("gate.commit", ticket_id=t["payload"]["ticket_id"])
    assert rack.nodes[0].governor.ledger.usage("pay-usd-hourly", 3600, rack.clock.now())[0] == 300   # committed at the owner


def test_a_budget_key_with_no_owner_does_not_load(rack):
    from govsim.policy import check_budget_owners, sign_policy
    image = rack.make_policy_image(rack.policy_version + 1)
    for rule in image["rules"]:
        if rule["id"] == "payments.transfer.small":
            rule["budget"]["key"] = "pay-usd-hourly-v2"
    image["assumptions"].append({**image["assumptions"][-1], "input": "pay-usd-hourly-v2"})
    image = sign_policy(image, rack.governance[:3])
    assert check_budget_owners(image) == ["pay-usd-hourly-v2"]
    r = rack.nodes[0].governor.command("POLICY_PROPOSE", {"image": image})
    assert not r["ok"] and r["why"] == reasons.POLICY_BUDGET_OWNER_MISSING
