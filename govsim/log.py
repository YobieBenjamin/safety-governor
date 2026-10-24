# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The log engine: a hash chain in the governor's NVM, signed checkpoints, and the heads of
fabric neighbors folded into each checkpoint (requirement REQUIREMENT-CHECKPOINT-INCLUDES-NEIGHBOR-HEADS)."""
from __future__ import annotations

from typing import Any

from .crypto import SigningKey, canonical, sha256
from .store import Store


class Log:
    def __init__(self, store: Store, clock):
        self.store = store
        self.clock = clock
        self._entries = store.get("log", [])
        self.neighbor_heads: dict[str, str] = store.get("neighbor_heads", {})

    @property
    def head(self) -> str:
        return self._entries[-1]["head"] if self._entries else "0" * 64

    @property
    def size(self) -> int:
        return len(self._entries)

    def append(self, event: str, data: dict[str, Any] | None = None) -> str:
        entry = {"seq": len(self._entries), "time": self.clock.now(), "event": event, "data": data or {}, "prev": self.head}
        entry["head"] = sha256(bytes.fromhex(entry["prev"]) + canonical({k: v for k, v in entry.items() if k != "head"}))
        self._entries.append(entry)
        self.store.save()          # appended before the operation returns
        return entry["head"]

    def entries(self, event: str | None = None) -> list[dict]:
        return [e for e in self._entries if event is None or e["event"] == event]

    def has(self, event: str, **match) -> bool:
        for e in self._entries:
            if e["event"] == event and all(e["data"].get(k) == v for k, v in match.items()):
                return True
        return False

    def record_neighbor_head(self, chip_id: str, head: str) -> None:
        self.neighbor_heads[chip_id] = head
        self.store.save()

    def checkpoint(self, key: SigningKey, chip_id: str) -> dict:
        return key.sign({"type": "checkpoint", "chip_id": chip_id, "head": self.head, "size": self.size,
                         "neighbor_heads": dict(self.neighbor_heads), "time": self.clock.now()})

    def verify_chain(self) -> bool:
        prev = "0" * 64
        for e in self._entries:
            if e["prev"] != prev:
                return False
            body = {k: v for k, v in e.items() if k != "head"}
            if e["head"] != sha256(bytes.fromhex(prev) + canonical(body)):
                return False
            prev = e["head"]
        return True
