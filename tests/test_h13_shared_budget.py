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
