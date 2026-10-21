"""A trace sink beside the log: every governor transition as a typed event, for replay against the abstract machines.

    from govsim.trace import Trace
    with Trace() as tr:
        ...drive a rack...
    tr.events        # list[Event], in the order the transitions happened

The sink does not change the governor. ``Trace.start()`` wraps a handful of methods on the classes
(``Governor._mint``, ``_accept_policy``, ``_apply_rung``, ``ActionEndpoint.execute`` and the log's ``append``)
and ``stop()`` puts the originals back. Each wrapper records what happened and calls through.

Event kinds (``Event.kind``) and the fields in ``Event.data``:

  boot               state, cause              the governor powered up (first boot or a restart)
  edition_set        edition                   the first edition this governor ran under (provisioning or boot)
  edition_change     old, new, via             a new policy edition accepted (via: commit | load | boot)
  ticket_issued      action, ticket_id, edition, state, hb, rule     the gate signed a ticket (action = request hash)
  hold_parked        action, hold_id           the gate parked a request for a human verdict
  hold_released      action, hold_id           the approvers released the hold (always precedes its ticket_issued)
  execute_ok         action, ticket_id, edition, endpoint_edition, hb, endpoint     an endpoint carried the action out
  execute_refused    action, ticket_id, edition, endpoint_edition, hb, endpoint, reason     an endpoint refused
  halt               cause, rung                the governor entered a safe-mode rung
  clear              cause, by                  the authority cleared the cause
  run_entered        via                        the governor entered RUN (via: clear | arm)

``Event.gov`` names the governor (``name#serial``; the serial keeps two racks with the same names apart) or is
None for a refusal whose ticket names no governor of ours (missing, forged).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from . import endpoints as _endpoints
from . import governor as _governor
from . import log as _log
from . import reasons


@dataclass
class Event:
    kind: str
    gov: str | None
    data: dict[str, Any] = field(default_factory=dict)
    seq: int = 0

    def __str__(self) -> str:
        body = ", ".join(f"{k}={v}" for k, v in self.data.items())
        return f"#{self.seq} {self.kind} [{self.gov}] {body}"


_active: "Trace | None" = None


class Trace:
    def __init__(self) -> None:
        self.events: list[Event] = []
        self._serial = itertools.count(1)
        self._ids: dict[int, str] = {}           # id(governor) -> "name#n"
        self._chips: dict[str, str] = {}         # chip id -> governor id
        self._log_owner: dict[int, Any] = {}     # id(Log) -> governor
        self._holds: dict[str, str] = {}         # hold_id -> request hash
        self._cleared: set[str] = set()          # governors whose last clear has not yet been followed by RUN
        self._orig: list[tuple[Any, str, Any]] = []
        self._booting: Any = None

    # -- context manager -----------------------------------------------------------------------
    def __enter__(self) -> "Trace":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    # -- recording -----------------------------------------------------------------------------
    def gid(self, gov) -> str:
        key = id(gov)
        if key not in self._ids:
            self._ids[key] = f"{gov.name}#{next(self._serial)}"
            self._chips[gov.chip_id] = self._ids[key]
        return self._ids[key]

    def emit(self, kind: str, gov: str | None, **data) -> Event:
        e = Event(kind, gov, data, len(self.events))
        self.events.append(e)
        return e

    # -- install / remove the wrappers -----------------------------------------------------------
    def _wrap(self, owner, name: str, make) -> None:
        orig = getattr(owner, name)
        self._orig.append((owner, name, orig))
        setattr(owner, name, make(orig))

    def start(self) -> None:
        global _active
        if _active is not None:
            raise RuntimeError("a trace is already running")
        _active = self
        tr = self
        G, E, L = _governor.Governor, _endpoints.ActionEndpoint, _log.Log

        def boot(orig):
            def _boot(gov):
                tr._booting = gov
                try:
                    return orig(gov)
                finally:
                    tr._booting = None
                    tr.emit("boot", tr.gid(gov), state=gov.state, cause=gov.cause)
                    tr._cleared.discard(tr.gid(gov))
            return _boot

        def log_init(orig):
            def __init__(lg, *a, **k):
                orig(lg, *a, **k)
                if tr._booting is not None:
                    tr._log_owner[id(lg)] = tr._booting
            return __init__

        def append(orig):
            def _append(lg, event, data=None):
                head = orig(lg, event, data)
                gov = tr._log_owner.get(id(lg))
                if gov is not None:
                    tr._on_log(gov, event, data or {})
                return head
            return _append

        def accept(orig):
            def _accept(gov, image, at_boot=False):
                old = gov.epoch
                ok, why = orig(gov, image, at_boot)
                if ok and gov.epoch != old:
                    via = "boot" if tr._booting is gov else ("load" if at_boot else "commit")
                    if old == "":
                        tr.emit("edition_set", tr.gid(gov), edition=gov.epoch)
                    else:
                        tr.emit("edition_change", tr.gid(gov), old=old, new=gov.epoch, via=via)
                return ok, why
            return _accept

        def mint(orig):
            def _mint(gov, rhash, action, params, fp, rule, reservation, now):
                ticket = orig(gov, rhash, action, params, fp, rule, reservation, now)
                tr.emit("ticket_issued", tr.gid(gov), action=rhash, ticket_id=ticket["payload"]["ticket_id"], edition=gov.epoch,
                        state=gov.state, hb=gov.hb_expiry > gov.clock.now(), rule=rule["id"])
                return ticket
            return _mint

        def rung(orig):
            def _apply_rung(gov, rung_, opens_loop=False):
                orig(gov, rung_, opens_loop)
                if rung_ == _governor.RUN:
                    g = tr.gid(gov)
                    tr.emit("run_entered", g, via="clear" if g in tr._cleared else "arm")
                    tr._cleared.discard(g)
            return _apply_rung

        def execute(orig):
            def _execute(ep, ticket, action, params):
                now = ep.clock.now()
                hb = now <= ep.hb_expiry
                t = (ticket or {}).get("payload") or {}
                edition, ep_edition = t.get("policy_epoch"), ep.epoch
                ok, why = orig(ep, ticket, action, params)
                gov = tr._by_chip(t.get("governor"))
                data = dict(action=t.get("request_hash"), ticket_id=t.get("ticket_id"), edition=edition, endpoint_edition=ep_edition,
                            hb=hb, endpoint=ep.name)
                if ok:
                    tr.emit("execute_ok", gov, **data)
                else:
                    tr.emit("execute_refused", gov, reason=why, **data)
                return ok, why
            return _execute

        self._wrap(G, "_boot", boot)
        self._wrap(L, "__init__", log_init)
        self._wrap(L, "append", append)
        self._wrap(G, "_accept_policy", accept)
        self._wrap(G, "_mint", mint)
        self._wrap(G, "_apply_rung", rung)
        self._wrap(E, "execute", execute)

    def stop(self) -> None:
        global _active
        for owner, name, orig in reversed(self._orig):
            setattr(owner, name, orig)
        self._orig.clear()
        _active = None

    # -- helpers ---------------------------------------------------------------------------------
    def _by_chip(self, chip_id: str | None) -> str | None:
        """The governor id for a ticket's ``governor`` field (the chip id), or None when we never saw that chip."""
        return self._chips.get(chip_id) if chip_id else None

    def _on_log(self, gov, event: str, data: dict) -> None:
        g = self.gid(gov)
        if event == "gate.hold":
            self._holds[data["hold_id"]] = data["request_hash"]
            self.emit("hold_parked", g, action=data["request_hash"], hold_id=data["hold_id"])
        elif event == "approve.released":
            # the ticket was minted (and logged) a line earlier; the release is the cause, so it goes before it
            action = self._holds.get(data["hold_id"])
            ev = Event("hold_released", g, {"action": action, "hold_id": data["hold_id"]})
            for i in range(len(self.events) - 1, -1, -1):
                e = self.events[i]
                if e.kind == "ticket_issued" and e.gov == g and e.data["action"] == action:
                    self.events.insert(i, ev)
                    break
            else:
                self.events.append(ev)
            for i, e in enumerate(self.events):
                e.seq = i
        elif event == "halt.cause":
            self._cleared.discard(g)
            self.emit("halt", g, cause=data["cause"], rung=data["rung"])
        elif event == "halt.cleared":
            self._cleared.add(g)
            self.emit("clear", g, cause=data["cause"], by=data["by"])
        elif event == "policy.committed":
            pass          # the edition change itself is recorded by the _accept_policy wrapper
