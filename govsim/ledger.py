# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Budgets, reservations, rate windows and the replay store, all durable.

Requirements R11 and R12. ``reserve`` is the check-and-reserve half of the transaction;
``commit`` and ``release`` are the other half. Everything is saved before returning.
"""
from __future__ import annotations

import threading

from .crypto import finite_number, random_id
from .store import Store


class Ledger:
    def __init__(self, store: Store, clock):
        self.store = store
        self.clock = clock
        self.lock = threading.RLock()
        self.budgets = store.get("budgets", {})        # key -> {"committed": [[amount, t]], "reserved": {rid: [amount, expires]}}
        self.replay = store.get("replay", {})          # request_hash -> t
        self.windows = store.get("windows", {})        # key -> [t, ...]

    def _purge(self, key: str, window_s: float, now: float) -> dict:
        b = self.budgets.setdefault(key, {"committed": [], "reserved": {}})
        b["committed"] = [[a, t] for a, t in b["committed"] if now - t < window_s]
        b["reserved"] = {rid: v for rid, v in b["reserved"].items() if v[1] > now}
        return b

    def usage(self, key: str, window_s: float, now: float) -> tuple[float, float]:
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
        with self.lock:
            b = self.budgets.get(key)
            if not b or rid not in b["reserved"]:
                return False
            amount, _ = b["reserved"].pop(rid)
            b["committed"].append([amount, now])
            self.store.save()
            return True

    def release(self, key: str, rid: str) -> None:
        with self.lock:
            b = self.budgets.get(key)
            if b and rid in b["reserved"]:
                b["reserved"].pop(rid)
                self.store.save()

    # --- replay and rate -----------------------------------------------------
    def seen(self, request_hash: str) -> bool:
        return request_hash in self.replay

    def mark(self, request_hash: str, now: float) -> None:
        with self.lock:
            self.replay[request_hash] = now
            self.store.save()

    def rate_mark(self, key: str, now: float) -> None:
        """Count one event in the key's window without a limit (the limit is judged with ``rate_count``)."""
        with self.lock:
            self.windows.setdefault(key, []).append(now)
            self.store.save()

    def rate_count(self, key: str, window_s: float, now: float) -> int:
        with self.lock:
            return len([t for t in self.windows.get(key, []) if now - t < window_s])

    def rate_ok(self, key: str, max_count: int, window_s: float, now: float) -> bool:
        with self.lock:
            w = [t for t in self.windows.get(key, []) if now - t < window_s]
            if len(w) >= max_count:
                self.windows[key] = w
                return False
            w.append(now)
            self.windows[key] = w
            self.store.save()
            return True
