# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The safety fabric: the halt loop and the message fabric (``docs/02-safety-fabric.md``).

The loop is physics: current flows iff the wire is intact and every member's switch is
closed. The message fabric routes signed envelopes between governors and honours partitions;
it never verifies anything itself, because the wire cannot. Verification is the receiver's
job (``Governor.on_fabric``), which is the point: a rogue device can put bytes on the wire and
nothing happens.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .governor import Governor


class HaltLoop:
    """The series current loop: current flows iff the wire is intact and every switch that is in the
    series path is closed. ``jumper`` wires around a governor; the beacon sees that only once it opens."""

    # Jumpering: the governor's switch leaves the series path and its state no longer affects the
    # current, while the governor still senses the loop like everyone else. The member-count beacon
    # (Governor._on_loop_beacon) detects a jumper only when the jumpered governor reports its switch
    # as open while the loop carries current. A jumpered governor whose switch is closed is
    # indistinguishable from a healthy one, and harmless, until it tries to open the loop.

    def __init__(self, sense_period_s: float = 0.0001, loop_id: str = "loop-0"):
        self.members: list["Governor"] = []
        self.wire_intact = True
        self.sense_period_s = sense_period_s
        self.loop_id = loop_id
        self.jumpered: set[str] = set()       # chip ids an attacker wired around

    def join(self, g: "Governor") -> None:
        self.members.append(g)

    def members_in_loop(self) -> set[str]:
        """The governors whose switch is really in the series path."""
        return {m.chip_id for m in self.members if m.chip_id not in self.jumpered}

    def current(self) -> bool:
        if not self.wire_intact:
            return False
        return all(not m.loop_switch_open for m in self.members if m.chip_id not in self.jumpered)

    def cut(self) -> None:
        self.wire_intact = False

    def repair(self) -> None:
        self.wire_intact = True

    def jumper(self, name: str) -> None:
        """Wire around governor ``name``: its switch no longer affects loop current."""
        self.jumpered.add(name)

    def unjumper(self, name: str) -> None:
        self.jumpered.discard(name)

    def propagate(self) -> float:
        """One sense period: every member senses the loop. Returns the time it took."""
        for m in self.members:
            m.sense_loop()
        return self.sense_period_s


class MessageFabric:
    def __init__(self):
        self.members: dict[str, "Governor"] = {}
        self.partition: list[set[str]] | None = None     # groups that can reach each other
        self.down: set[str] = set()                        # governors whose port is unplugged
        self.traffic: list[dict] = []
        self.dropped: list[dict] = []

    def join(self, g: "Governor") -> None:
        self.members[g.chip_id] = g

    def neighbors(self, chip_id: str) -> list[str]:
        """Ring neighbors (the dual ring): the previous and next member ids."""
        ids = list(self.members)
        if chip_id not in ids or len(ids) < 2:
            return []
        i = ids.index(chip_id)
        return list({ids[(i - 1) % len(ids)], ids[(i + 1) % len(ids)]})

    def reachable(self, a: str, b: str) -> bool:
        if a in self.down or b in self.down:
            return False
        if self.partition is None:
            return True
        return any(a in grp and b in grp for grp in self.partition)

    def send(self, sender: str, msg: dict, to: str | None = None) -> list[tuple[str, Any]]:
        """Deliver ``msg`` from ``sender`` to ``to`` (or broadcast). Returns receivers' results."""
        results = []
        targets = [to] if to else [c for c in self.members if c != sender]
        for t in targets:
            if t not in self.members:
                continue
            if not self.reachable(sender, t):
                self.dropped.append({"from": sender, "to": t, "type": msg.get("payload", {}).get("type")})
                continue
            self.traffic.append({"from": sender, "to": t, "type": msg.get("payload", {}).get("type")})
            results.append((t, self.members[t].on_fabric(msg)))
        return results

    def inject(self, msg: dict, to: str | None = None) -> list[tuple[str, Any]]:
        """A device on the wire that is not a member: bytes arrive, that is all."""
        results = []
        for t in ([to] if to else list(self.members)):
            if t in self.members and t not in self.down:
                self.traffic.append({"from": "rogue", "to": t, "type": msg.get("payload", {}).get("type")})
                results.append((t, self.members[t].on_fabric(msg)))
        return results

    def split(self, *groups: set[str]) -> None:
        self.partition = [set(g) for g in groups]

    def heal(self) -> None:
        self.partition = None
        self.down.clear()
