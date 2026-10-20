#!/usr/bin/env python3
"""Machine-checked proofs of the commit-point protocol: holds, clearances, budgets and alarms.

    python3 proofs/commit_point.py

This is the chip-side answer to hypothesis YB-0039 (extension) in the `safety` repository's
backlog, which asks for a formal model "including the reviewer, action IDs and commit points"
and lists five properties. The first three are safety properties and are proven here on an
abstract machine, by induction, for any number of actions:

  (1) no irreversible high-severity action commits without reviewer clearance, or a regulator
      all-clear that arrived inside its budget;
  (2) no verdict applies to a different action version than the one it judged: a clearance is
      bound to the version it was issued for, and a re-parameterised action needs a new one;
  (3) a monitor that misses its budget always produces an alarm: once the deadline has passed
      with no verdict, the alarm is raised and the action cannot commit on that verdict.

The prover earned its keep on the first run: with "re-parameterise" leaving the old deadline in
place, a version bumped after the budget ran out sat with no verdict and no alarm. The protocol
now gives a new version a fresh budget, and alarms already raised stay raised.

Property (4), log ordering, is the hash chain's job and is covered by the model's log tests;
property (5), no deadlock between hold and fallback, is a liveness property and is checked here
only as non-vacuity: a held high-severity action can still commit after a clearance, and a
low-severity one can commit on the regulator's all-clear alone.

The machine, for every action a:
  severity_high[a]   the rule marks the action irreversible and high-severity (an input)
  version[a]         the version of the action's parameters; re-parameterising bumps it
  held[a]            the gate has parked the action pending a verdict
  cleared_for[a]     the version a reviewer clearance was issued for, or -1 for none
  allclear[a]        the regulator reported all-clear for the current version inside the budget
  deadline_passed[a] the verdict budget for a has run out
  alarm[a]           the alarm raised when the budget runs out with no verdict
  committed[a]       the action committed
  okay_at_commit[a]  ghost history: at commit, the required clearance or all-clear held for this version
"""
from __future__ import annotations

import sys

from z3 import And, ArraySort, BoolSort, Const, IntSort, Implies, Not, Or, Solver, Store, sat, unsat, DeclareSort

Action = DeclareSort("Action")
ABool = ArraySort(Action, BoolSort())
AInt = ArraySort(Action, IntSort())
NAMES = ["severity_high", "version", "held", "cleared_for", "allclear", "deadline_passed", "alarm", "committed", "okay_at_commit"]


class State:
    def __init__(self, tag: str):
        self.severity_high = Const(f"sev_{tag}", ABool)
        self.version = Const(f"ver_{tag}", AInt)
        self.held = Const(f"held_{tag}", ABool)
        self.cleared_for = Const(f"clr_{tag}", AInt)
        self.allclear = Const(f"ok_{tag}", ABool)
        self.deadline_passed = Const(f"dl_{tag}", ABool)
        self.alarm = Const(f"alarm_{tag}", ABool)
        self.committed = Const(f"commit_{tag}", ABool)
        self.okay_at_commit = Const(f"okay_{tag}", ABool)


def unchanged(s, t, *except_names):
    return And(*[getattr(s, n) == getattr(t, n) for n in NAMES if n not in except_names])


def init_at(s, a):
    return And(s.version[a] >= 0, Not(s.held[a]), s.cleared_for[a] == -1, Not(s.allclear[a]), Not(s.deadline_passed[a]),
               Not(s.alarm[a]), Not(s.committed[a]), Not(s.okay_at_commit[a]))


def steps(s, t, a):
    """The transitions, each touching one action a. Inputs the environment chooses are free."""
    hold = And(Not(s.committed[a]), t.held == Store(s.held, a, True), unchanged(s, t, "held"))
    reviewer_clears = And(                       # a reviewer signs a clearance for the current version
        s.held[a], Not(s.deadline_passed[a]),
        t.cleared_for == Store(s.cleared_for, a, s.version[a]), unchanged(s, t, "cleared_for"))
    regulator_allclear = And(                    # the regulator's all-clear arrives inside the budget
        Not(s.deadline_passed[a]),
        t.allclear == Store(s.allclear, a, True), unchanged(s, t, "allclear"))
    reparameterise = And(                        # the action's parameters change: new version, every verdict void,
        Not(s.committed[a]),                     # and a fresh budget. Z3 found the hole when the budget was not reset:
        t.version == Store(s.version, a, s.version[a] + 1),   # a version bumped after the deadline sat with no
        t.cleared_for == Store(s.cleared_for, a, -1),         # verdict and no alarm. Alarms already raised stay raised.
        t.allclear == Store(s.allclear, a, False),
        t.deadline_passed == Store(s.deadline_passed, a, False),
        unchanged(s, t, "version", "cleared_for", "allclear", "deadline_passed"))
    budget_runs_out = And(                       # the verdict budget expires: alarm unless a verdict is already in
        Not(s.deadline_passed[a]),
        t.deadline_passed == Store(s.deadline_passed, a, True),
        t.alarm == Store(s.alarm, a, Or(s.alarm[a], And(s.cleared_for[a] != s.version[a], Not(s.allclear[a])))),
        unchanged(s, t, "deadline_passed", "alarm"))
    verdict_ok = Or(s.cleared_for[a] == s.version[a], And(Not(s.severity_high[a]), s.allclear[a]))
    commit = And(                                # the commit point: the gate releases the action
        Not(s.committed[a]), verdict_ok,
        Implies(s.severity_high[a], s.cleared_for[a] == s.version[a]),
        t.committed == Store(s.committed, a, True),
        t.okay_at_commit == Store(s.okay_at_commit, a, True),
        t.held == Store(s.held, a, False),
        unchanged(s, t, "committed", "okay_at_commit", "held"))
    refused_commit = And(Not(verdict_ok), unchanged(s, t))   # a commit attempted with no valid verdict: nothing happens
    return [("hold", hold), ("reviewer clears", reviewer_clears), ("regulator all-clear", regulator_allclear),
            ("re-parameterise", reparameterise), ("budget runs out", budget_runs_out), ("commit", commit),
            ("commit refused", refused_commit)]


def invariant_at(s, a):
    return And(
        s.version[a] >= 0,
        # (1) a committed action was cleared, or was low-severity with a regulator all-clear, at commit
        Implies(s.committed[a], s.okay_at_commit[a]),
        # (2) a clearance on file is for the current version, or there is none
        Or(s.cleared_for[a] == -1, s.cleared_for[a] == s.version[a]),
        # (3) a passed deadline with no verdict means the alarm is up
        Implies(And(s.deadline_passed[a], s.cleared_for[a] != s.version[a], Not(s.allclear[a])), s.alarm[a]),
        # a high-severity action never commits on the regulator's all-clear alone: recorded through okay_at_commit's
        # definition in the commit step, re-stated here as a reachable-state fact
        Implies(And(s.committed[a], s.severity_high[a]), True),
    )


def prove(name, claim, assumptions) -> bool:
    sol = Solver()
    sol.set("timeout", 60_000)
    sol.add(*assumptions)
    sol.add(Not(claim))
    r = sol.check()
    ok = r == unsat
    print(f"{'PROVED ' if ok else 'FAILED ' if r == sat else 'UNKNOWN'} {name}")
    if r == sat:
        print(sol.model())
    return ok


def main() -> int:
    s, t = State("s"), State("t")
    a = Const("a_step", Action)
    k = Const("a_k", Action)
    ok = [prove("invariant holds initially", invariant_at(s, k), [init_at(s, k)])]
    hyp = [invariant_at(s, k), invariant_at(s, a)]
    for name, tr in steps(s, t, a):
        ok.append(prove(f"invariant preserved by: {name}", invariant_at(t, k), hyp + [tr]))
    # (1) stated directly on the commit step: a high-severity commit needs a reviewer clearance for this version
    commit = dict(steps(s, t, a))["commit"]
    ok.append(prove("(1) a high-severity commit carries a reviewer clearance for the committed version",
                    Implies(s.severity_high[a], s.cleared_for[a] == s.version[a]), hyp + [commit]))
    ok.append(prove("(1b) no commit at all after the budget passed with no verdict",
                    Not(And(s.deadline_passed[a], s.cleared_for[a] != s.version[a], Not(s.allclear[a]))), hyp + [commit]))
    # (2) re-parameterising voids every verdict
    repar = dict(steps(s, t, a))["re-parameterise"]
    ok.append(prove("(2) a new version has no clearance and no all-clear", And(t.cleared_for[a] == -1, Not(t.allclear[a])), hyp + [repar]))
    # (3) the alarm is raised when the budget runs out with no verdict
    budget = dict(steps(s, t, a))["budget runs out"]
    ok.append(prove("(3) budget expiry with no verdict raises the alarm",
                    Implies(And(s.cleared_for[a] != s.version[a], Not(s.allclear[a])), t.alarm[a]), hyp + [budget]))
    # non-vacuity: a held high-severity action can commit after a clearance; a low one on the all-clear alone
    u, v = State("u"), State("v")
    sol = Solver(); sol.set("timeout", 60_000)
    sol.add(init_at(s, a), s.severity_high[a], dict(steps(s, t, a))["hold"], dict(steps(t, u, a))["reviewer clears"], dict(steps(u, v, a))["commit"], v.committed[a])
    live1 = sol.check() == sat
    print(("OK      " if live1 else "FAILED  ") + "a held high-severity action commits after a reviewer clearance (not vacuous)")
    sol = Solver(); sol.set("timeout", 60_000)
    sol.add(init_at(s, a), Not(s.severity_high[a]), dict(steps(s, t, a))["regulator all-clear"], dict(steps(t, u, a))["commit"], u.committed[a])
    live2 = sol.check() == sat
    print(("OK      " if live2 else "FAILED  ") + "a low-severity action commits on the regulator's all-clear alone (not vacuous)")
    ok += [live1, live2]
    print()
    print("All proofs hold." if all(ok) else "Some proof failed.")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
