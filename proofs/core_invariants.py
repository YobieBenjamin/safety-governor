#!/usr/bin/env python3
"""Machine-checked proofs of the governor's core invariants, on an abstract model.

    python3 proofs/core_invariants.py

The governor is written down here as a small state machine, the way a mathematician would
write it rather than the way govsim simulates it, and Z3 is asked to prove, by induction,
that certain things can never happen in it. Each property is checked two ways: the initial
state satisfies it, and no single step of the machine can take a state that satisfies it to a
state that does not. If Z3 finds no counterexample to either, the property holds in every
reachable state, for every sequence of steps, for any number of actions. That is a proof.

What the proof is about, and what it is not about, is the point of the file:

  * It is about the logic: no execution without a ticket, no ticket without an allowing rule
    and its witnesses, no ticket honoured across an edition change, no replay, no ticket while
    halted or while the heartbeat is lost, no leaving the halt without a quorum, the edition
    only moves forward.
  * It is not about the physics (whether the wire really carries no bytes without a ticket),
    the cryptography (signatures are modelled as unforgeable: nobody but the governor can
    write the ticket table), the lists and observers (an allowed action is whatever the
    signed rule says), or the link from this model to the RTL (that is the formal work in
    the pre-hardware plan, on the Verilog itself).

The state. For every action a (an uninterpreted sort, so the proof is for any number of them):
  allows[e][a]       the signed policy at edition e allows a (the rulebook; an input, not chosen here)
  witness[a]         the required witnesses for a are present and fresh (an input)
  ticket[a]          the edition in which a ticket for a was issued, or -1 for none
  used[a]            that ticket has been spent
  executed[a]        the endpoint carried a out
  okay_at_issue[a]   ghost history: when the ticket was issued, the rule allowed a and the witnesses were present
  epoch              the current rules edition
  halted             the governor is in HALT
  heartbeat          the authority's heartbeat is live at the endpoint
"""
from __future__ import annotations

import sys

from z3 import (And, ArraySort, BoolSort, BoolVal, Const, Consts, DeclareSort, ForAll, Implies, IntSort, Not, Or, Select, Solver, Store,
                Exists, sat, unsat)

Action = DeclareSort("Action")
ABool = ArraySort(Action, BoolSort())
AInt = ArraySort(Action, IntSort())
Policy = ArraySort(IntSort(), ABool)


class State:
    def __init__(self, tag: str):
        self.allows = Const(f"allows_{tag}", Policy)
        self.witness = Const(f"witness_{tag}", ABool)
        self.ticket = Const(f"ticket_{tag}", AInt)
        self.used = Const(f"used_{tag}", ABool)
        self.executed = Const(f"executed_{tag}", ABool)
        self.okay_at_issue = Const(f"okay_{tag}", ABool)
        self.epoch = Const(f"epoch_{tag}", IntSort())
        self.halted = Const(f"halted_{tag}", BoolSort())
        self.heartbeat = Const(f"heartbeat_{tag}", BoolSort())

    def vars(self):
        return [self.allows, self.witness, self.ticket, self.used, self.executed, self.okay_at_issue, self.epoch, self.halted, self.heartbeat]


def unchanged(s: State, t: State, *except_names: str):
    names = ["allows", "witness", "ticket", "used", "executed", "okay_at_issue", "epoch", "halted", "heartbeat"]
    return And(*[getattr(s, n) == getattr(t, n) for n in names if n not in except_names])


def init(s: State):
    a = Const("a0", Action)
    return And(
        s.epoch >= 0,
        ForAll([a], And(s.ticket[a] == -1, Not(s.used[a]), Not(s.executed[a]), Not(s.okay_at_issue[a]))),
    )


# ---- the steps the machine can take --------------------------------------------------------
# Inputs the environment chooses at each step (the policy and the witnesses may change freely,
# which models new editions and observers coming and going; quorum and neighbour are the
# external signatures a clear needs).
def steps(s: State, t: State):
    a = Const("a_step", Action)
    quorum = Const("quorum", BoolSort())
    neighbour = Const("neighbour", BoolSort())

    issue = And(                       # the gate signs a ticket
        Not(s.halted), s.heartbeat,
        s.allows[s.epoch][a], s.witness[a], s.ticket[a] == -1,
        t.ticket == Store(s.ticket, a, s.epoch),
        t.okay_at_issue == Store(s.okay_at_issue, a, True),
        unchanged(s, t, "ticket", "okay_at_issue"),
    )
    execute = And(                     # the endpoint's comparator admits a ticket
        s.heartbeat,
        s.ticket[a] == s.epoch, Not(s.used[a]),
        t.executed == Store(s.executed, a, True),
        t.used == Store(s.used, a, True),
        unchanged(s, t, "executed", "used"),
    )
    forged_execute = And(              # the adversary presents a without a ticket, or a spent one, or one from another edition
        Or(s.ticket[a] != s.epoch, s.used[a], Not(s.heartbeat)),
        unchanged(s, t),               # refused: nothing changes
    )
    new_epoch = And(                   # a new rules edition, committed under quorum
        quorum, t.epoch == s.epoch + 1,
        unchanged(s, t, "epoch", "allows", "witness"),
    )
    halt = And(t.halted == True, unchanged(s, t, "halted"))
    clear = And(s.halted, quorum, neighbour, t.halted == False, unchanged(s, t, "halted"))
    beat_lost = And(t.heartbeat == False, unchanged(s, t, "heartbeat"))
    beat_back = And(t.heartbeat == True, unchanged(s, t, "heartbeat"))
    environment = unchanged(s, t, "allows", "witness")   # lists and observers change under the machine
    named = [("issue", issue), ("execute", execute), ("forged execute (refused)", forged_execute), ("new edition", new_epoch),
             ("halt", halt), ("clear", clear), ("heartbeat lost", beat_lost), ("heartbeat back", beat_back), ("lists and observers change", environment)]
    return Or(*[tr for _, tr in named]), (a, quorum, neighbour)


def step_list(s: State, t: State, inputs):
    """The same transitions as steps(), named, sharing the given input constants."""
    a, quorum, neighbour = inputs
    issue = And(Not(s.halted), s.heartbeat, s.allows[s.epoch][a], s.witness[a], s.ticket[a] == -1,
                t.ticket == Store(s.ticket, a, s.epoch), t.okay_at_issue == Store(s.okay_at_issue, a, True), unchanged(s, t, "ticket", "okay_at_issue"))
    execute = And(s.heartbeat, s.ticket[a] == s.epoch, Not(s.used[a]),
                  t.executed == Store(s.executed, a, True), t.used == Store(s.used, a, True), unchanged(s, t, "executed", "used"))
    forged_execute = And(Or(s.ticket[a] != s.epoch, s.used[a], Not(s.heartbeat)), unchanged(s, t))
    new_epoch = And(quorum, t.epoch == s.epoch + 1, unchanged(s, t, "epoch", "allows", "witness"))
    halt = And(t.halted == True, unchanged(s, t, "halted"))
    clear = And(s.halted, quorum, neighbour, t.halted == False, unchanged(s, t, "halted"))
    beat_lost = And(t.heartbeat == False, unchanged(s, t, "heartbeat"))
    beat_back = And(t.heartbeat == True, unchanged(s, t, "heartbeat"))
    environment = unchanged(s, t, "allows", "witness")
    return [("issue", issue), ("execute", execute), ("forged execute (refused)", forged_execute), ("new edition", new_epoch),
            ("halt", halt), ("clear", clear), ("heartbeat lost", beat_lost), ("heartbeat back", beat_back), ("lists and observers change", environment)]


# ---- the invariants -------------------------------------------------------------------------
def invariant_at(s: State, a):
    """The invariant for one action a. The full invariant is this for every a."""
    return And(
        # P0  the edition counter never goes negative, so the "no ticket" marker (-1) can never equal an edition.
        #     Z3 found this one: without it, a state with epoch = -1 lets an action with no ticket execute.
        s.epoch >= 0,
        # P1  nothing executes unless, when its ticket was issued, a rule allowed it and the witnesses were present
        Implies(s.executed[a], s.okay_at_issue[a]),
        # P2  a ticket exists only for an action the rule allowed, with witnesses, at issue time
        Implies(s.ticket[a] != -1, s.okay_at_issue[a]),
        # P3  no replay: anything executed has its ticket marked spent
        Implies(s.executed[a], s.used[a]),
        # P4  tickets carry an edition no newer than the current one
        Implies(s.ticket[a] != -1, And(s.ticket[a] >= 0, s.ticket[a] <= s.epoch)),
    )


def invariant(s: State):
    a = Const("a_inv", Action)
    return ForAll([a], invariant_at(s, a))


def one_step_properties(s: State, t: State, inputs):
    a, quorum, neighbour = inputs
    return {
        "P5  halt is absorbing without a quorum: halted and no quorum means still halted after any step":
            Implies(And(s.halted, Not(quorum)), t.halted),
        "P6  fail closed: with the heartbeat lost, no step executes anything":
            Implies(Not(s.heartbeat), t.executed == s.executed),
        "P7  no ticket is issued while halted or while the heartbeat is lost":
            Implies(Or(s.halted, Not(s.heartbeat)), t.ticket == s.ticket),
        "P8  the edition only moves forward":
            t.epoch >= s.epoch,
        "P9  an edition change needs a quorum":
            Implies(t.epoch != s.epoch, quorum),
    }


def prove(name: str, claim, assumptions) -> bool:
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
    step, inputs = steps(s, t)
    a_step, quorum, neighbour = inputs
    a_k = Const("a_k", Action)                       # an arbitrary action, for the conclusion
    results = []
    results.append(prove("P1-P4 hold in every initial state", invariant_at(s, a_k), [init(s)]))
    # Induction, one step at a time. Every step touches at most the entry for a_step, so the
    # invariant at a_k after the step follows from the invariant at a_k and at a_step before it.
    # Assuming only those two instances is weaker than assuming the whole invariant, so the
    # proof is sound, and it keeps every query free of quantifiers.
    hyp = [invariant_at(s, a_k), invariant_at(s, a_step)]
    for name, tr in step_list(s, t, inputs):
        results.append(prove(f"P1-P4 preserved by step: {name}", invariant_at(t, a_k), hyp + [tr]))
    for name, claim in one_step_properties(s, t, inputs).items():
        results.append(prove(name, claim, hyp + [step]))
    # a sanity check that the machine is not vacuous: an allowed action can be executed in two steps
    u = State("u")
    issue1 = dict(step_list(s, t, inputs))["issue"]
    exec2 = dict(step_list(t, u, inputs))["execute"]
    sol = Solver()
    sol.set("timeout", 60_000)
    sol.add(init(s), issue1, exec2, u.executed[a_step])
    live = sol.check() == sat
    print(("OK      " if live else "FAILED  ") + "the machine can execute an allowed action (not vacuous)")
    results.append(live)
    print()
    print("All proofs hold." if all(results) else "Some proof failed.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
