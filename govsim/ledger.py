# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Durable budgets, budget reservations, rate windows and the replay record.

What it holds: for each budget key, the amounts already spent inside the window (committed) and the
amounts held but not yet spent (reserved). For each rate key, the times of recent events. For each
request hash, the time it was first seen (the replay record). Every call that changes a record saves to
the store before it returns, so a reservation that was granted is not lost in a power cut.

What it guarantees: a reservation is granted only when committed plus reserved plus the new amount stays
within the limit, and the check and the reservation happen in one locked step. A non-finite amount (NaN or
infinity) is refused, so it cannot break that sum (F03, tests/test_f03_nan_budget.py). A reservation leaves
the reserved list when it is committed or released, so it is spent or given back once. A reservation that
is neither expires at its time to live and stops counting.

What it deliberately does NOT do: it does not decide which budget a request uses (the rule does that).
It does not share budgets between chips. A budget is counted at its owner chip (the policy's
``budget_owners``), and other chips ask that owner over the fabric.

Requirements REQUIREMENT-AUTHORIZATION-IS-DURABLE-TRANSACTION and REQUIREMENT-ONE-LEDGER-OWNS-BUDGET. ``reserve`` is the check-and-reserve half of the transaction;
``commit`` and ``release`` are the other half. Everything is saved before returning.
"""
from __future__ import annotations

import threading

from .crypto import finite_number, random_id
from .store import Store


class Ledger:
    """The durable budget, rate and replay store of one governor. Methods that record a change take the lock and
    save before they return. ``usage`` may trim expired entries in memory, and those trims are saved with the next
    write. ``rate_count`` and ``seen`` only read."""

    def __init__(self, store: Store, clock):
        """Load the budgets, the replay record and the rate windows from the store. ``clock`` is the chip's clock."""
        self.store = store
        self.clock = clock
        self.lock = threading.RLock()
        self.budgets = store.get("budgets", {})        # key -> {"committed": [[amount, t]], "reserved": {rid: [amount, expires]}}
        self.replay = store.get("replay", {})          # request_hash -> t
        self.windows = store.get("windows", {})        # key -> [t, ...]

    def _purge(self, key: str, window_s: float, now: float) -> dict:
        """Drop committed amounts older than the window, and reservations past their expiry, for one budget key.
        Returns that key's budget record, already trimmed."""
        b = self.budgets.setdefault(key, {"committed": [], "reserved": {}})
        # old committed amounts leave the window, so the budget refills as time passes
        b["committed"] = [[a, t] for a, t in b["committed"] if now - t < window_s]
        b["reserved"] = {rid: v for rid, v in b["reserved"].items() if v[1] > now}
        return b

    def usage(self, key: str, window_s: float, now: float) -> tuple[float, float]:
        """The amount committed inside the window, and the amount reserved and not yet expired, for one budget
        key. Output: (committed, reserved)."""
        with self.lock:
            b = self._purge(key, window_s, now)
            return sum(a for a, _ in b["committed"]), sum(v[0] for v in b["reserved"].values())

    def reserve(self, key: str, amount: float, limit: float, window_s: float, now: float, ttl: float) -> str | None:
        """committed + reserved + amount <= limit, else None. One critical section."""
        with self.lock:
            if not finite_number(amount) or amount < 0:   # a NaN or infinity would pass every < / > check and poison the aggregate (F03)
                return None
            committed, reserved = self.usage(key, window_s, now)
            if committed + reserved + amount > limit:
                return None
            rid = random_id(8)
            self.budgets[key]["reserved"][rid] = [amount, now + ttl]
            self.store.save()
            return rid

    def commit(self, key: str, rid: str, now: float) -> bool:
        """Spend one reservation: it moves from reserved to committed, dated ``now``. Returns False when the
        reservation does not exist (never made, expired, or already committed or released)."""
        with self.lock:
            b = self.budgets.get(key)
            if not b or rid not in b["reserved"]:
                return False
            amount, _ = b["reserved"].pop(rid)
            b["committed"].append([amount, now])
            self.store.save()
            return True

    def release(self, key: str, rid: str) -> None:
        """Give back one reservation that was not spent. Does nothing when the reservation does not exist."""
        with self.lock:
            b = self.budgets.get(key)
            if b and rid in b["reserved"]:
                b["reserved"].pop(rid)
                self.store.save()

    # --- replay and rate -----------------------------------------------------
    def seen(self, request_hash: str) -> bool:
        """True when this request hash has been recorded before. The governor refuses such a request as a replay."""
        return request_hash in self.replay

    def mark(self, request_hash: str, now: float) -> None:
        """Record that a request hash was seen at ``now``. The governor calls this before any hold or ticket is made."""
        with self.lock:
            self.replay[request_hash] = now
            self.store.save()

    def rate_mark(self, key: str, now: float) -> None:
        """Count one event in the key's window without a limit (the limit is judged with ``rate_count``)."""
        with self.lock:
            self.windows.setdefault(key, []).append(now)
            self.store.save()

    def rate_count(self, key: str, window_s: float, now: float) -> int:
        """How many events for this key fall inside the last ``window_s`` seconds."""
        with self.lock:
            return len([t for t in self.windows.get(key, []) if now - t < window_s])

    def rate_ok(self, key: str, max_count: int, window_s: float, now: float) -> bool:
        """Check a rate limit and count this event if the limit is not yet reached. When the limit is reached it
        returns False and counts nothing. Output: True when the event is allowed."""
        with self.lock:
            w = [t for t in self.windows.get(key, []) if now - t < window_s]
            if len(w) >= max_count:
                self.windows[key] = w
                return False
            w.append(now)
            self.windows[key] = w
            self.store.save()
            return True
