#!/usr/bin/env python3
"""Replay a govsim trace through the abstract machines of the proofs, and raise on the first event they refuse.

    from govsim.trace import Trace
    from proofs.replay import replay
    replay(trace.events)          # returns a Report, or raises NoTransition naming the event

The machines are those of ``core_invariants.py`` (tickets, editions, halt, heartbeat) and ``commit_point.py``
(holds and their clearances), executed on concrete values instead of being handed to Z3. The guards are copied
from the Z3 steps one for one, and ``step_names()`` reads the step names out of the proof files so a test can
fail if the two drift apart. After every step the invariants P1 to P4 are checked on the concrete state.

What each event is allowed to do:

  ticket_issued    core ``issue``: not halted, heartbeat live, no ticket yet for this action. The rule and the
                   witnesses are inputs of the model (``allows``, ``witness``) and are taken as given. A ticket
                   that follows a hold must also be the commit of the commit-point machine, which needs the
                   reviewer clearance that ``hold_released`` records.
  execute_ok       core ``execute``: heartbeat live, the ticket carries the current edition, not yet spent.
  execute_refused  core ``forged execute``: nothing changes. A refusal is always allowed (the system may be
                   stricter than the machine), but a refusal for a reason that makes a claim about the machine
                   (replay, stale edition, heartbeat) must be backed by that state.
  edition_change   core ``new edition``: a quorum (an accepted policy image carries the governance signatures).
  halt             core ``halt``.
  clear            core ``clear``: halted, quorum (the authority's signature), neighbour (the governor checked it).
  run_entered      after a ``clear``: nothing (the machine left the halt at the clear). Via ``arm``, the first
                   RUN after a boot: this is NOT a step of the machine. The theorem's initial state leaves
                   ``halted`` free, and a power cycle is not a step in it. The replayer accepts it only when
                   the halt being left came from a boot, never from a cause, and counts it in ``Report.arms``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).parent

# refusal reasons that claim something about the machine's state, and what they claim
CLAIM_REPLAY = ("ticket.replay",)
CLAIM_STALE = ("ticket.stale_epoch",)
CLAIM_HB = ("endpoint.heartbeat_expired",)


ADMIT_REFUSALS = ("ticket.bad_signature", "ticket.params_mismatch", "ticket.action_mismatch", "ticket.expired", "ticket.not_yet_valid",
                  "ticket.replay", "ticket.stale_epoch", "ticket.wrong_endpoint", "ticket.missing", "endpoint.heartbeat_expired")


class NoTransition(AssertionError):
    """The abstract machine has no enabled transition for this event."""

    def __init__(self, event, step: str, why: str):
        self.event, self.step, self.why = event, step, why
        super().__init__(f"no enabled transition for event {event} (machine step '{step}'): {why}")


def step_names() -> dict[str, list[str]]:
    """The step names of the two proof files, read from their source (z3 is not needed to read them)."""
    core = (HERE / "core_invariants.py").read_text()
    cp = (HERE / "commit_point.py").read_text()
    core_names = re.findall(r'\("([^"]+)", (?:issue|execute|forged_execute|new_epoch|halt|clear|beat_lost|beat_back|environment)\)', core.split("def step_list")[1])
    cp_names = re.findall(r'\("([^"]+)", (?:hold|reviewer_clears|regulator_allclear|reparameterise|budget_runs_out|commit|refused_commit)\)', cp)
    return {"core": core_names, "commit_point": cp_names}


class Core:
    """proofs/core_invariants.py, one governor. Actions are request hashes; the edition is a counter."""

    def __init__(self) -> None:
        self.epoch = 0
        self.halted = True            # a governor that has booted and not yet been armed
        self.halt_from = "boot"       # what put it there: boot | cause
        self.heartbeat = False
        self.ticket: dict[str, int] = {}
        self.used: set[str] = set()
        self.executed: set[str] = set()
        self.burned: set[str] = set()            # ticket burned at the endpoint and then refused: not a step of the machine
        self.okay_at_issue: set[str] = set()
        self.names: dict[int, str] = {}          # edition counter -> the edition's name in govsim
        self.steps: list[str] = []

    def tk(self, a: str) -> int:
        return self.ticket.get(a, -1)

    def check_invariants(self, event) -> None:
        if self.epoch < 0:
            raise NoTransition(event, "invariant", "P0 the edition went negative")
        for a in set(self.ticket) | self.executed | self.used:
            if a in self.executed and a not in self.okay_at_issue:
                raise NoTransition(event, "invariant", f"P1 {a[:12]} executed without an allowed issue")
            if self.tk(a) != -1 and a not in self.okay_at_issue:
                raise NoTransition(event, "invariant", f"P2 {a[:12]} has a ticket without an allowed issue")
            if a in self.executed and a not in self.used:
                raise NoTransition(event, "invariant", f"P3 {a[:12]} executed but not spent")
            if self.tk(a) != -1 and not 0 <= self.tk(a) <= self.epoch:
                raise NoTransition(event, "invariant", f"P4 {a[:12]} carries edition {self.tk(a)} with the edition at {self.epoch}")


class CommitPoint:
    """proofs/commit_point.py for the actions the gate parks: a hold, a reviewer clearance, then the commit.
    A parked action is high severity and irreversible by construction (the rule asked for a human)."""

    def __init__(self) -> None:
        self.held: set[str] = set()
        self.cleared_for: dict[str, int] = {}
        self.version: dict[str, int] = {}
        self.committed: set[str] = set()

    def hold(self, event, a: str) -> None:
        if a in self.committed:
            raise NoTransition(event, "hold", "the action already committed")
        self.held.add(a)
        self.version.setdefault(a, 0)

    def reviewer_clears(self, event, a: str) -> None:
        if a not in self.held:
            raise NoTransition(event, "reviewer clears", "the action is not held")
        self.cleared_for[a] = self.version[a]

    def commit(self, event, a: str) -> None:
        if a in self.committed:
            raise NoTransition(event, "commit", "the action already committed")
        if self.cleared_for.get(a, -1) != self.version.get(a, 0):
            raise NoTransition(event, "commit", "a high-severity action with no reviewer clearance for its version")
        self.committed.add(a)
        self.held.discard(a)


@dataclass
class Report:
    events: int = 0
    steps: dict[str, int] = field(default_factory=dict)
    arms: int = 0
    stutters: dict[str, int] = field(default_factory=dict)

    def count(self, step: str) -> None:
        self.steps[step] = self.steps.get(step, 0) + 1


class Replayer:
    def __init__(self) -> None:
        self.core: dict[str, Core] = {}
        self.cp: dict[str, CommitPoint] = {}
        self.hb: dict[tuple[str, str], bool] = {}
        self.report = Report()

    def machine(self, gov: str) -> Core:
        if gov not in self.core:
            self.core[gov] = Core()
            self.cp[gov] = CommitPoint()
        return self.core[gov]

    def _observe_hb(self, m: Core, gov: str, observer: str, live: bool) -> None:
        """The heartbeat flag of the machine is what the observer sees. A change is a lost / back step."""
        m.heartbeat = live
        last = self.hb.get((gov, observer))
        if last is not None and last != live:
            self.report.count("heartbeat back" if live else "heartbeat lost")
        self.hb[(gov, observer)] = live

    def feed(self, e) -> None:
        self.report.events += 1
        d = e.data
        if e.kind == "execute_refused" and e.gov is None:
            return self._refuse_unknown(e)
        if e.gov is None:
            raise NoTransition(e, "execute", "carried out on a ticket that no governor of the trace minted")
        m = self.machine(e.gov)
        k = e.kind
        if k == "boot":
            m.halted, m.halt_from = True, ("cause" if d.get("cause") else "boot")
            self.hb = {key: v for key, v in self.hb.items() if key[0] != e.gov or key[1] != e.gov}
        elif k == "edition_set":
            if m.names and m.names[m.epoch] != d["edition"]:
                raise NoTransition(e, "new edition", f"boot found edition {d['edition'][:8]} where the machine is at {m.names[m.epoch][:8]} and there was no edition change")
            m.names[m.epoch] = d["edition"]
        elif k == "edition_change":
            if m.names.get(m.epoch) != d["old"]:
                raise NoTransition(e, "new edition", f"changes from {d['old'][:8]}, the machine is at {str(m.names.get(m.epoch))[:8]}")
            # quorum: an accepted image carries the governance signatures (verify_policy ran in _accept_policy)
            m.epoch += 1
            m.names[m.epoch] = d["new"]
            self.report.count("new edition")
        elif k == "halt":
            m.halted, m.halt_from = True, "cause"
            self.report.count("halt")
        elif k == "clear":
            if not m.halted:
                raise NoTransition(e, "clear", "the machine is not halted")
            m.halted = False       # quorum: the authority's signature; neighbour: _cmd_clear checked it before logging
            self.report.count("clear")
        elif k == "run_entered":
            if d["via"] == "arm":
                if m.halt_from != "boot" or not m.halted:
                    raise NoTransition(e, "arm", "RUN entered with no clear, from a halt that a cause put there")
                m.halted = False
                self.report.arms += 1
            elif m.halted:
                raise NoTransition(e, "clear", "RUN entered after a clear the machine does not have")
        elif k == "hold_parked":
            self.cp[e.gov].hold(e, d["action"])
            self.report.count("hold")
        elif k == "hold_released":
            self.cp[e.gov].reviewer_clears(e, d["action"])
            self.cp[e.gov].commit(e, d["action"])
            self.report.count("reviewer clears + commit")
        elif k == "ticket_issued":
            self._issue(e, m)
        elif k == "execute_ok":
            self._execute(e, m)
        elif k == "execute_refused":
            self._refuse(e, m)
        else:
            raise NoTransition(e, "?", "an event kind the replayer does not know")
        m.check_invariants(e)

    def _issue(self, e, m: Core) -> None:
        a, d = e.data["action"], e.data
        self._observe_hb(m, e.gov, e.gov, d["hb"])
        if a in self.cp[e.gov].held:
            raise NoTransition(e, "commit", "a ticket for an action that is still held (no hold_released before it)")
        if m.halted:
            raise NoTransition(e, "issue", f"the machine is halted ({m.halt_from}); the governor was in {d['state']}")
        if not m.heartbeat:
            raise NoTransition(e, "issue", "the governor's heartbeat is not live")
        if m.tk(a) != -1:
            raise NoTransition(e, "issue", "a second ticket for the same action")
        if m.names.get(m.epoch) != d["edition"]:
            raise NoTransition(e, "issue", f"edition {d['edition'][:8]} is not the machine's current {str(m.names.get(m.epoch))[:8]}")
        m.ticket[a] = m.epoch
        m.okay_at_issue.add(a)
        self.report.count("issue")

    def _execute(self, e, m: Core) -> None:
        a, d = e.data["action"], e.data
        self._observe_hb(m, e.gov, d["endpoint"], d["hb"])
        if not m.heartbeat:
            raise NoTransition(e, "execute", "the endpoint carried the action out with its heartbeat expired")
        if m.tk(a) != m.epoch:
            raise NoTransition(e, "execute", f"the ticket carries edition {m.tk(a)} (none = -1), the machine is at {m.epoch}")
        if a in m.used:
            raise NoTransition(e, "execute", "the ticket was already spent")
        if d["endpoint_edition"] != d["edition"]:
            raise NoTransition(e, "execute", "the endpoint holds a different edition than the ticket's")
        m.executed.add(a)
        m.used.add(a)
        self.report.count("execute")

    def _refuse(self, e, m: Core) -> None:
        a, d, why = e.data["action"], e.data, e.data["reason"]
        self._observe_hb(m, e.gov, d["endpoint"], d["hb"])
        if why in CLAIM_REPLAY and a not in m.used and a not in m.burned:
            raise NoTransition(e, "forged execute (refused)", "refused as a replay, but the machine has no spent ticket for the action")
        if why in CLAIM_STALE and m.tk(a) == m.epoch and d["edition"] == d["endpoint_edition"]:
            raise NoTransition(e, "forged execute (refused)", "refused as a stale edition, but the ticket carries the current one")
        if why not in ADMIT_REFUSALS:
            m.burned.add(a)          # the endpoint burns the ticket before the commit and the device checks
        if why in CLAIM_HB and m.heartbeat:
            raise NoTransition(e, "forged execute (refused)", "refused for an expired heartbeat, but the machine's heartbeat is live")
        self.report.count("forged execute (refused)")

    def _refuse_unknown(self, e) -> None:
        self.report.count("forged execute (refused)")


def replay(events) -> Report:
    """Drive the machines with the events in order; raise NoTransition on the first one they refuse."""
    r = Replayer()
    for e in events:
        r.feed(e)
    return r.report
