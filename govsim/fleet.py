# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""A fleet of racks that share fleet-wide limits (adversarial audits 2 and 3, 2026-10-26).

A budget owned by "fleet" in the edition (``budget_owners``) is counted once for the whole fleet, not once per rack:
every governor of every rack reserves and commits it at the fleet ledger, so splitting one action across many racks
gets the cap once. A governor that cannot get a quorum of ledger answers refuses the request (fail closed); it never
falls back to a rack-local count.

The fleet ledger is a set of replicas, each with its own count and its own signing key, and the edition names the
replica keys and how many must agree (``fleet_ledger``: {"keys": [...], "threshold": k}). The model uses all of them
(k = n): each replica counts independently, and with a majority rule concurrent requests could land on different
pairs and spend up to n/k times the cap, while with all of them every allowed request is counted by every honest
replica and a lying replica can only refuse. Audit 3 found that the
governor trusted the ledger's answer with no signature; in silicon the governor reaches a fleet service only through
the untrusted host or network, so the host could answer "reserved" to everything. Now every answer is a receipt
signed by a replica over the key, the amount, the reserving governor and a fresh nonce the governor chose, and the
governor needs ``k`` distinct replicas' receipts before it mints and again before it commits. Fewer than ``k``
lying or captured replicas, or a host forging answers, cannot lift a fleet cap.

What this does not model: replicas in different regions with real network partitions and consensus between them.
Each replica here counts independently; with every replica required, the cap holds against any number of lying
replicas, at the price that one unreachable replica stops fleet-budgeted actions (fail closed). Consensus among
replicas would allow a majority rule; it is not modelled. Recorded in
docs/research/fleet-ledger.md.
"""
from __future__ import annotations

from .clock import SimClock
from .crypto import SigningKey
from .cluster import Rack, build_rack
from .ledger import Ledger
from .store import Store


FLEET_OWNER = "fleet"


class LedgerReplica:
    """One replica of the fleet ledger: its own count, its own key, and the governor that made each reservation."""

    def __init__(self, clock):
        self.ledger = Ledger(Store(), clock)
        self.key = SigningKey.generate()
        self.holder: dict[str, str] = {}
        self.reachable = True

    def reserve(self, key, amount, limit, window_s, now, ttl, reserver, nonce, binding=None) -> dict | None:
        """``binding`` names the request hash and the endpoint the reservation is for; it is signed into the receipt,
        so the endpoint can refuse a receipt that was made for another request or another device (30 October 2026)."""
        if not self.reachable:
            return None
        rid = self.ledger.reserve(key, amount, limit, window_s, now, ttl)
        if not rid:
            return None
        self.holder[rid] = reserver
        return self.key.sign({"type": "fleet-reserve", "key": key, "amount": amount, "reserver": reserver,
                              "nonce": nonce, "rid": rid, "binding": binding or {}})

    def release(self, key, rid, reserver) -> bool:
        """Give back a reservation that will not be spent (a reservation the governor could not complete at the
        threshold of replicas). Only the governor that made it may release it."""
        if not self.reachable or self.holder.get(rid) != reserver:
            return False
        self.ledger.release(key, rid)
        self.holder.pop(rid, None)
        return True

    def commit(self, key, rid, now, reserver, nonce) -> dict | None:
        if not self.reachable or self.holder.get(rid) != reserver or not self.ledger.commit(key, rid, now):
            return None
        return self.key.sign({"type": "fleet-commit", "key": key, "rid": rid, "reserver": reserver, "nonce": nonce})


class FleetLedger:
    """The fleet-wide count for budgets owned by ``fleet``: ``n`` replicas, of which ``threshold`` must answer.
    The governor talks to it through ``reserve`` and ``commit``, which return the replicas' signed receipts."""

    def __init__(self, clock=None, replicas: int = 3, threshold: int = 3):
        self.replicas = [LedgerReplica(clock) for _ in range(replicas)]
        self.threshold = threshold

    @property
    def reachable(self) -> bool:
        return sum(r.reachable for r in self.replicas) >= self.threshold

    @reachable.setter
    def reachable(self, value: bool) -> None:
        for r in self.replicas:
            r.reachable = value

    def edition_entry(self) -> dict:
        """What an edition names for this ledger: the replica keys and the threshold."""
        return {"keys": [r.key.public.hex for r in self.replicas], "threshold": self.threshold}

    def reserve(self, key, amount, limit, window_s, now, ttl, reserver, nonce, binding=None) -> list[dict]:
        return [x for r in self.replicas if (x := r.reserve(key, amount, limit, window_s, now, ttl, reserver, nonce, binding))]

    def release(self, key, rids: dict, reserver) -> int:
        """Release the reservations in ``rids`` (replica key id -> reservation id). Returns how many were released."""
        n = 0
        for r in self.replicas:
            rid = rids.get(r.key.public.key_id)
            if rid and r.release(key, rid, reserver):
                n += 1
        return n

    def commit(self, key, rids: dict, now, reserver, nonce) -> list[dict]:
        out = []
        for r in self.replicas:
            rid = rids.get(r.key.public.key_id)
            if rid and (x := r.commit(key, rid, now, reserver, nonce)):
                out.append(x)
        return out


def build_fleet(n_racks: int, gpus_per_rack: int = 1, tier: str = "rack", sites: int = 1) -> tuple[list[Rack], FleetLedger]:
    """``n_racks`` racks on one clock, whose payment budget is owned by the fleet, each brought up and wired to one
    fleet ledger. The racks are spread round-robin over ``sites`` data centers; the racks of one site share that
    site's heartbeat signers (2 of 3), and no site's signers can keep another site running or stop it."""
    clock = SimClock()
    fleet = FleetLedger(clock)
    site_keys = [(SigningKey.generate(), [SigningKey.generate() for _ in range(2)]) for _ in range(sites)]
    racks = []
    for i in range(n_racks):
        s = i % sites
        r = build_rack(gpus_per_rack, tier, clock=clock, policy_kw={"fleet_budget": True, "fleet_ledger": fleet.edition_entry()},
                       site=f"dc-{s}", site_heartbeat=site_keys[s])
        for node in r.nodes:
            node.governor.fleet_ledger = fleet
        r.bring_up()
        racks.append(r)
    return racks, fleet
