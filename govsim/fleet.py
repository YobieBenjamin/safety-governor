# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""A fleet of racks that share fleet-wide limits (adversarial audit, 2026-10-26).

A budget owned by "fleet" in the edition (``budget_owners``) is counted once for the whole fleet, not once per rack:
every governor of every rack reserves and commits it at the one fleet ledger, so splitting one action across many
racks gets the cap once. A governor that cannot reach the fleet ledger refuses the request (fail closed); it never
falls back to a rack-local count.

What this models, and what it does not: the fleet ledger here is one object that every rack reaches. In a real fleet
it is a replicated service (a quorum of ledger replicas across regions, each reservation committed by the quorum
before the ticket is minted), so that no single ledger is a single point of failure or of capture, and a regional
partition stops fleet-budgeted actions in the cut-off region rather than letting each side spend the whole cap. That
replication is a design obligation recorded in docs/research/fleet-ledger.md; it is not in this model.
"""
from __future__ import annotations

from .clock import SimClock
from .cluster import Rack, build_rack
from .ledger import Ledger
from .store import Store


FLEET_OWNER = "fleet"


class FleetLedger:
    """The fleet-wide count for budgets owned by ``fleet``. Reservations remember the governor that made them;
    only that governor may commit or release one."""

    def __init__(self, clock=None):
        self.ledger = Ledger(Store(), clock)
        self.holder: dict[str, str] = {}
        self.reachable = True             # a partition from the fleet ledger: reserve and commit fail closed

    def reserve(self, key: str, amount: float, limit: float, window_s: float, now: float, ttl: float, reserver: str) -> str | None:
        if not self.reachable:
            return None
        rid = self.ledger.reserve(key, amount, limit, window_s, now, ttl)
        if rid:
            self.holder[rid] = reserver
        return rid

    def commit(self, key: str, rid: str, now: float, reserver: str) -> bool:
        if not self.reachable or self.holder.get(rid) != reserver:
            return False
        return self.ledger.commit(key, rid, now)

    def release(self, key: str, rid: str, reserver: str) -> None:
        if self.reachable and self.holder.get(rid) == reserver:
            self.ledger.release(key, rid)
            self.holder.pop(rid, None)


def build_fleet(n_racks: int, gpus_per_rack: int = 1, tier: str = "rack") -> tuple[list[Rack], FleetLedger]:
    """``n_racks`` racks on one clock, whose payment budget is owned by the fleet, each brought up and wired to one
    fleet ledger."""
    clock = SimClock()
    fleet = FleetLedger(clock)
    racks = []
    for _ in range(n_racks):
        r = build_rack(gpus_per_rack, tier, clock=clock, policy_kw={"fleet_budget": True})
        for node in r.nodes:
            node.governor.fleet_ledger = fleet
        r.bring_up()
        racks.append(r)
    return racks, fleet
