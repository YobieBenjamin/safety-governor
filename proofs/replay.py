#!/usr/bin/env python3
"""Replay a govsim trace through the abstract machines of the proofs, and raise on the first event they refuse.

    from govsim.trace import Trace
    from proofs.replay import replay
    replay(trace.events)          # returns a Report, or raises NoTransition naming the event

The machines are those of ``core_invariants.py`` (tickets, editions, halt, heartbeat) and ``commit_point.py``
(holds and their clearances), executed on concrete values instead of being handed to Z3. The guards are a
concrete re-encoding of those Z3 steps: ``step_names()`` reads the step names out of the proof files and
``replayer_steps()`` reads the step labels the replayer actually drives, and a test cross-checks the two sets
so a guard that names a step the proofs lack fails -- but the guard *logic* is not compared symbolically (z3 is
not installed here, so the prover is not run). The re-encoding is checked instead by replaying the real traces
and by broken-governor fixtures that must fail at a named event. After every step the invariants P1 to P4 are
re-checked on the concrete state; because the guards already enforce them, the check is a consistency guard, not
independent evidence that they hold.

What each event is allowed to do:

  ticket_issued    core ``issue``: not halted, heartbeat live, no ticket yet for this action. The rule and the
                   witnesses are inputs of the model (``allows``, ``witness``) and are taken as given. A ticket
                   for an action the gate still holds is that action's release: it must be released (the
                   commit-point ``reviewer clears`` step, driven at the ``hold_released`` event), else the
                   commit has no clearance and has no enabled transition.
  hold_parked      commit-point ``hold``: the gate parks a high-severity action for a human verdict.
  hold_released    commit-point ``reviewer clears``: the approvers release the hold; the clearance is bound to
                   the action's version. The commit is NOT fused here -- it is driven at the action's carry-out
                   -- so a held action committed with no clearance is a transition the machine does not have.
  heartbeat_back   core ``heartbeat back``: the machine's heartbeat goes live. The machine has one heartbeat
                   (the authority's, live at the endpoint, ``core_invariants.py``); the sink observes it from
                   the governor's accepted heartbeat and, at the endpoint, from the endpoint's own timer.
  heartbeat_lost   core ``heartbeat lost``: the machine's heartbeat goes out. The issue and execute guards read
                   this state, not a flag on their own event.
  execute_ok       core ``execute``: heartbeat live, the ticket carries the current edition, not yet spent. A
                   held action that is carried out is its commit point: the commit-point ``commit`` step, which
                   needs the clearance the ``hold_released`` recorded.
  execute_refused  core ``forged execute``: nothing changes. A refusal is always allowed (the system may be
                   stricter than the machine), but a refusal for a reason that makes a claim about the machine
                   (replay, stale edition, heartbeat) must be backed by that state. A ticket the endpoint burns
                   and then refuses (a post-admit check fails) is a step the machine does not have; the replayer
                   absorbs it as a stutter and tracks the burn in ``Report.burned`` (a gap in the theorem, not a
                   model bug -- the endpoint's post-admit checks are not a step of the core machine).
  edition_change   core ``new edition``: a quorum (an accepted policy image carries the governance signatures).
  halt             core ``halt``.
  clear            core ``clear``: halted, quorum (the authority's signature), neighbour (the governor checked it).
  run_entered      after a ``clear``: nothing (the machine left the halt at the clear). Via ``arm``, the first
                   RUN after a boot: this is NOT a step of the machine. The theorem's initial state leaves
                   ``halted`` free, and a power cycle is not a step in it. The replayer accepts it only when
                   the halt being left came from a boot, never from a cause, and counts it in ``Report.arms``.
                   A RUN entered after a cause with no clear is the one step the machine refuses here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from govsim import reasons

HERE = Path(__file__).parent

# The endpoint's admit checks, in the order ActionEndpoint.admit runs them (govsim/endpoints.py): a refusal for
# any of these names an admit-check reason and is a stutter of ``forged execute``. They are the reasons
# constants, not hard-coded strings, so a renamed or new reason shows up here instead of being silently
# miscounted as a burn. A refusal for a reason not in this set (the endpoint's post-admit checks: the commit,
# the device's own sensors) is a burn without an execute, the gap the theorem does not model.
CLAIM_REPLAY = (reasons.TICKET_REPLAY,)
CLAIM_STALE = (reasons.TICKET_STALE_EPOCH,)
CLAIM_HB = (reasons.ENDPOINT_HEARTBEAT_EXPIRED,)


ADMIT_REFUSALS = (reasons.TICKET_BAD_SIGNATURE, reasons.TICKET_PARAMS_MISMATCH, reasons.TICKET_ACTION_MISMATCH,
                  reasons.TICKET_EXPIRED, reasons.TICKET_NOT_YET_VALID, reasons.TICKET_REPLAY,
                  reasons.TICKET_STALE_EPOCH, reasons.TICKET_WRONG_ENDPOINT, reasons.TICKET_MISSING,
                  reasons.ENDPOINT_HEARTBEAT_EXPIRED)


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


def replayer_steps() -> set[str]:
    """The step labels the replayer actually drives, read out of its own source: the string a ``report.count``
    or a ``NoTransition`` names. The conformance test cross-checks this against the proof files, so a guard
    that names a step the proofs do not have shows up here (z3 is not run, so the guard *logic* is not
    compared symbolically -- this ties the labels, not the logic)."""
    src = Path(__file__).read_text()
    driven = set(re.findall(r'self\.report\.count\("([^"]+)"', src))
    driven |= set(re.findall(r'NoTransition\([^,]+,\s*"([^"]+)"', src))
    return driven


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
    A parked action is high severity and irreversible by construction (the rule asked for a human).

    The clearance and the commit are separate steps driven at separate points of the trace, so the check that
    a committed action carries a clearance for its version is not tautological: ``reviewer_clears`` happens at
    the hold's release (``hold_released``) and ``commit`` at the action's carry-out (``execute_ok``). A held
    action that is committed with no clearance -- a ticket the gate signed for a still-held action -- has no
    enabled transition, and the replay names it. The version never moves (a re-parameterised action is a new
    action hash in govsim), so a stale clearance is a non-issue here; the guard that bites is the missing one."""

    def __init__(self) -> None:
        self.held: set[str] = set()
        self.released: set[str] = set()
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
            raise NoTransition(event, "reviewer clears", "a clearance for an action the gate never held")
        self.cleared_for[a] = self.version[a]
        self.released.add(a)

    def commit(self, event, a: str) -> None:
        if a in self.committed:
            raise NoTransition(event, "commit", "the action already committed")
        # a held action commits only on a clearance bound to its version; an action the gate never held is not
        # this machine's concern (it is the core machine's issue/execute).
        if a in self.held and self.cleared_for.get(a, -1) != self.version.get(a, 0):
            raise NoTransition(event, "commit", "a held action committed with no reviewer clearance for its version")
        self.committed.add(a)
        self.held.discard(a)


@dataclass
class Report:
    events: int = 0
    steps: dict[str, int] = field(default_factory=dict)
    arms: int = 0
    stutters: dict[str, int] = field(default_factory=dict)
    burned: int = 0

    def count(self, step: str) -> None:
        self.steps[step] = self.steps.get(step, 0) + 1


class Replayer:
    def __init__(self) -> None:
        self.core: dict[str, Core] = {}
        self.cp: dict[str, CommitPoint] = {}
        self.report = Report()

    def machine(self, gov: str) -> Core:
        if gov not in self.core:
            self.core[gov] = Core()
            self.cp[gov] = CommitPoint()
        return self.core[gov]

    def _set_hb(self, m: Core, live: bool) -> None:
        """A heartbeat_back / heartbeat_lost event moves the machine's heartbeat; a change is a lost / back step.
        The issue and execute guards read ``m.heartbeat`` (a state the events set), never a flag on their own
        event, so the guard can actually fail on what the heartbeat events say."""
        if m.heartbeat != live:
            self.report.count("heartbeat back" if live else "heartbeat lost")
        m.heartbeat = live

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
            m.halted, m.halt_from, m.heartbeat = True, ("cause" if d.get("cause") else "boot"), False
        elif k == "heartbeat_back":
            self._set_hb(m, True)
        elif k == "heartbeat_lost":
            self._set_hb(m, False)
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
            # the clearance is its own step; the commit is driven later, at the action's carry-out (execute_ok),
            # so a held action committed with no clearance has no enabled transition
            self.cp[e.gov].reviewer_clears(e, d["action"])
            self.report.count("reviewer clears")
        elif k == "ticket_issued":
            self._issue(e, m)
        elif k == "execute_ok":
            self._execute(e, m)
            if e.data["action"] in self.cp[e.gov].held:
                self.cp[e.gov].commit(e, e.data["action"])    # a carried-out held action is its commit point
                self.report.count("commit")
        elif k == "execute_refused":
            self._refuse(e, m)
        else:
            raise NoTransition(e, "?", "an event kind the replayer does not know")
        m.check_invariants(e)

    def _issue(self, e, m: Core) -> None:
        a, d = e.data["action"], e.data
        # a ticket for an action the gate still holds (parked for a human) is its release: it must be released,
        # which is the clearance the commit-point machine needs. A held action with no hold_released has none.
        if a in self.cp[e.gov].held and a not in self.cp[e.gov].released:
            raise NoTransition(e, "commit", "a ticket for an action the gate never released (no hold_released before it)")
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
        if why in CLAIM_REPLAY and a not in m.used and a not in m.burned:
            raise NoTransition(e, "forged execute (refused)", "refused as a replay, but the machine has no spent ticket for the action")
        if why in CLAIM_STALE and m.tk(a) == m.epoch and d["edition"] == d["endpoint_edition"]:
            raise NoTransition(e, "forged execute (refused)", "refused as a stale edition, but the ticket carries the current one")
        if why not in ADMIT_REFUSALS:
            if a not in m.burned:
                m.burned.add(a)      # the endpoint burns the ticket before the commit and the device checks
                self.report.burned += 1
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
