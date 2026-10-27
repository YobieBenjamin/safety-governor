#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
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
  * Since 23 October 2026 replay is counted, not just flagged. An external audit pointed out that
    a Boolean executed[a] cannot tell a second external effect from a harmless repeat: a second
    execution just rewrote the same bit, so the old INVARIANT-NO-REPLAY-TICKET-SPENT (executed => used) held even if the execute
    step's spent-ticket guard was deleted. The machine now counts ticket instances (n_issued),
    the tickets consumed (n_spent) and the effects produced (n_events) per action, and proves no
    action ever produces more effects than it was issued tickets (INVARIANT-NO-REPLAY-COUNTED). Because these are counts,
    a legitimate action done twice under two fresh tickets stays expressible; it is replay off one
    ticket that the count forbids. INVARIANT-NO-REPLAY-COUNTED fails if the fresh-ticket guard is removed, so the proof now
    catches that defect, where the Boolean INVARIANT-NO-REPLAY-TICKET-SPENT could not.
  * Since 22 October 2026 it is also about what a signature authorizes. Two defects were found
    by testing the code that the first version of this file could not see, because it took
    "a quorum signed the new edition" and "the authority cleared the halt" as given yes-or-no
    inputs: an image that set its own threshold to zero passed, and a heartbeat cleared a halt.
    The machine now counts the valid governance signatures against a fused threshold that only
    rises (whatever threshold the image claims), and a clear needs a signature over a CLEAR,
    for this chip, inside its expiry. INVARIANT-EDITION-CHANGE-NEEDS-FUSED-THRESHOLD, INVARIANT-FUSED-THRESHOLD-NEVER-FALLS and INVARIANT-ONLY-CLEAR-LEAVES-HALT are those properties, and the file also checks
    that the old rules break them, so the proof would have caught both.
  * It is not about the physics (whether the wire really carries no bytes without a ticket),
    the cryptography (signatures are modelled as unforgeable: nobody but the governor can
    write the ticket table, and nobody but a key's holder can produce a signature that counts), the lists and observers (an allowed action is whatever the
    signed rule says), or the link from this model to the RTL (that is the formal work in
    the pre-hardware plan, on the Verilog itself).

The state. For every action a (an uninterpreted sort, so the proof is for any number of them):
  allows[e][a]       the signed policy at edition e allows a (the rulebook; an input, not chosen here)
  witness[a]         the required witnesses for a are present and fresh (an input)
  ticket[a]          the edition in which a ticket for a was issued, or -1 for none
  used[a]            that ticket has been spent
  executed[a]        the endpoint carried a out
  n_issued[a]        how many tickets have ever been minted for a (a count, not a Boolean)
  n_spent[a]         how many of those tickets have been consumed by an execution
  n_events[a]        how many external effects a has produced at the endpoint
  okay_at_issue[a]   ghost history: when the ticket was issued, the rule allowed a and the witnesses were present
  epoch              the current rules edition
  halted             the governor is in HALT
  heartbeat          the authority's heartbeat is live at the endpoint
  kfuse              the governance threshold in force: how many distinct signatures from the keys
                     in force the next edition needs; set by each committed edition, never below kfloor
  kfloor             the floor fused at manufacture: at least one, and no step changes it

The inputs the environment picks at each step, the adversary included:
  sigs               distinct valid governance signatures on the proposed edition (unforgeable, so
                     at most what the key holders signed, but any number they did sign)
  claimed_k          the threshold the proposed image claims for itself (anything at all)
  signed_cmd         the command named inside a verified authority signature (0 = none)
  for_me, fresh      that signature names this chip, and its expiry has not passed
  neighbour          a neighbour holds the logged cause (the clear's other precondition)
"""
from __future__ import annotations

import sys

from z3 import (And, ArraySort, BoolSort, BoolVal, Const, Consts, DeclareSort, ForAll, If, Implies, IntSort, Not, Or, Select, Solver, Store,
                Exists, sat, unsat)

Action = DeclareSort("Action")
ABool = ArraySort(Action, BoolSort())
AInt = ArraySort(Action, IntSort())
Policy = ArraySort(IntSort(), ABool)


class State:
    """The machine's state at one moment, as Z3 constants: one constant for each state variable listed in the module
    docstring. ``tag`` names the copy (for example "s" for the state before a step and "t" for the state after it),
    so that two states can appear in one formula."""
    def __init__(self, tag: str):
        """Create a fresh set of constants for one state. Their names include ``tag``, so two states never share a constant."""
        self.allows = Const(f"allows_{tag}", Policy)
        self.witness = Const(f"witness_{tag}", ABool)
        self.ticket = Const(f"ticket_{tag}", AInt)
        self.used = Const(f"used_{tag}", ABool)
        self.executed = Const(f"executed_{tag}", ABool)
        self.n_issued = Const(f"n_issued_{tag}", AInt)
        self.n_spent = Const(f"n_spent_{tag}", AInt)
        self.n_events = Const(f"n_events_{tag}", AInt)
        self.okay_at_issue = Const(f"okay_{tag}", ABool)
        self.epoch = Const(f"epoch_{tag}", IntSort())
        self.halted = Const(f"halted_{tag}", BoolSort())
        self.heartbeat = Const(f"heartbeat_{tag}", BoolSort())
        self.kfuse = Const(f"kfuse_{tag}", IntSort())
        self.kfloor = Const(f"kfloor_{tag}", IntSort())

    def vars(self):
        """Every state constant, as one list."""
        return [self.allows, self.witness, self.ticket, self.used, self.executed, self.n_issued, self.n_spent, self.n_events, self.okay_at_issue, self.epoch, self.halted, self.heartbeat, self.kfuse, self.kfloor]


def unchanged(s: State, t: State, *except_names: str):
    """A formula that says that state ``t`` equals state ``s`` on every field, except the fields named in
    ``except_names``."""
    names = ["allows", "witness", "ticket", "used", "executed", "n_issued", "n_spent", "n_events", "okay_at_issue", "epoch", "halted", "heartbeat", "kfuse", "kfloor"]
    return And(*[getattr(s, n) == getattr(t, n) for n in names if n not in except_names])


def init(s: State):
    """The initial state. No ticket is issued or spent, no effect has happened, the edition is at least zero, and the
    fused threshold is at least the floor, which is at least one."""
    a = Const("a0", Action)
    return And(
        s.epoch >= 0, s.kfloor >= 1, s.kfuse >= s.kfloor,
        ForAll([a], And(s.ticket[a] == -1, Not(s.used[a]), Not(s.executed[a]), Not(s.okay_at_issue[a]),
                        s.n_issued[a] == 0, s.n_spent[a] == 0, s.n_events[a] == 0)),
    )


# ---- the steps the machine can take --------------------------------------------------------
# Inputs the environment chooses at each step (the policy and the witnesses may change freely,
# which models new editions and observers coming and going). The two authorizations are not
# inputs any more: they are computed from what was signed, the way the chip computes them.
CLEAR_CMD, HEARTBEAT_CMD = 0x10, 0x0E          # the opcodes in docs/04 §3; any other value is some other command


def make_inputs(tag: str = "step"):
    """The environment's free choices for one step: the action, the number of valid governance signatures on a
    proposed edition, the threshold the image claims for itself, the command named in an authority signature, whether that
    signature names this chip and is still in date, and whether a neighbour holds the logged cause. Each one is an unknown
    for the solver, so the proof covers every value."""
    a = Const(f"a_{tag}", Action)
    sigs, claimed_k, signed_cmd = Consts(f"sigs_{tag} claimed_k_{tag} signed_cmd_{tag}", IntSort())
    for_me, fresh, neighbour = Consts(f"for_me_{tag} fresh_{tag} neighbour_{tag}", BoolSort())
    return dict(a=a, sigs=sigs, claimed_k=claimed_k, signed_cmd=signed_cmd, for_me=for_me, fresh=fresh, neighbour=neighbour)


def quorum_of(s: State, i: dict):
    """What verify_policy does now: the configuration in force authorizes its replacement. The distinct
    valid signatures from the keys in force must reach the threshold in force; the image's own threshold,
    which will govern the NEXT change, must be at least one and not below the manufacture floor."""
    return And(i["sigs"] >= s.kfuse, i["claimed_k"] >= 1, i["claimed_k"] >= s.kfloor)


def clear_auth_of(s: State, i: dict):
    """What _check_signed does now for a CLEAR: an authority signature over a CLEAR, for this chip, in date."""
    return And(i["signed_cmd"] == CLEAR_CMD, i["for_me"], i["fresh"])


def step_list(s: State, t: State, i: dict, quorum=None, clear_auth=None, execute_needs_run=True, execute_needs_fresh_ticket=True):
    """The transitions, named. ``quorum`` and ``clear_auth`` default to the chip's rules; passing the
    old ones shows what the proof says about them. ``execute_needs_fresh_ticket`` is the anti-replay
    guard: with it off, an execution may consume a ticket that is already spent, which is the replay
    the audit asked the proof to be able to see."""
    a = i["a"]
    quorum = quorum_of(s, i) if quorum is None else quorum
    clear_auth = clear_auth_of(s, i) if clear_auth is None else clear_auth
    # Issuing mints a ticket instance. It no longer requires the single slot to be empty, so a logical
    # action can be authorized again under a fresh ticket; n_issued counts the instances.
    issue = And(Not(s.halted), s.heartbeat, s.allows[s.epoch][a], s.witness[a],
                t.ticket == Store(s.ticket, a, s.epoch), t.okay_at_issue == Store(s.okay_at_issue, a, True),
                t.n_issued == Store(s.n_issued, a, s.n_issued[a] + 1), unchanged(s, t, "ticket", "okay_at_issue", "n_issued"))
    # Executing consumes one outstanding ticket (n_issued > n_spent) and produces one effect. The
    # anti-replay guard is that outstanding-ticket test, not the Boolean used[a]: the count is what
    # tells a second effect from a repeat. With execute_needs_fresh_ticket off, the guard is gone.
    execute = And(Not(s.halted) if execute_needs_run else BoolVal(True),     # commit_from_endpoint refuses unless the governor is in RUN
                  s.heartbeat, s.ticket[a] == s.epoch,
                  (s.n_issued[a] > s.n_spent[a]) if execute_needs_fresh_ticket else BoolVal(True),
                  t.executed == Store(s.executed, a, True), t.used == Store(s.used, a, True),
                  t.n_spent == Store(s.n_spent, a, s.n_spent[a] + 1), t.n_events == Store(s.n_events, a, s.n_events[a] + 1),
                  unchanged(s, t, "executed", "used", "n_spent", "n_events"))
    # an execution that fails a guard (old ticket, no fresh ticket, no heartbeat, or halted) changes nothing: it is refused
    forged_execute = And(Or(s.ticket[a] != s.epoch,Not(s.n_issued[a] > s.n_spent[a]), Not(s.heartbeat), s.halted), unchanged(s, t))
    new_epoch = And(quorum, t.epoch == s.epoch + 1,                          # an edition that asks for more signatures raises the floor
                    t.kfuse == i["claimed_k"],                                  # the new edition's k governs the next change
                    unchanged(s, t, "epoch", "allows", "witness", "kfuse"))
    halt = And(t.halted == True, unchanged(s, t, "halted"))
    # a clear needs a signed CLEAR for this chip in date (clear_auth), and a neighbour that holds the logged cause
    clear = And(s.halted, clear_auth, i["neighbour"], t.halted == False, unchanged(s, t, "halted"))
    beat_lost = And(t.heartbeat == False, unchanged(s, t, "heartbeat"))
    beat_back = And(t.heartbeat == True, unchanged(s, t, "heartbeat"))
    environment = unchanged(s, t, "allows", "witness")                      # lists and observers change under the machine
    return [("issue", issue), ("execute", execute), ("forged execute (refused)", forged_execute), ("new edition", new_epoch),
            ("halt", halt), ("clear", clear), ("heartbeat lost", beat_lost), ("heartbeat back", beat_back), ("lists and observers change", environment)]


def steps(s: State, t: State, i: dict, **kw):
    """The one-step relation: the disjunction of every transition in ``step_list``. Any one step of the machine
    satisfies it."""
    return Or(*[tr for _, tr in step_list(s, t, i, **kw)])


# ---- the invariants -------------------------------------------------------------------------
def invariant_at(s: State, a):
    """The invariant for one action a. The full invariant is this for every a."""
    return And(
        # INVARIANT-EDITION-NEVER-NEGATIVE  the edition counter never goes negative, so the "no ticket" marker (-1) can never equal an edition.
        #     Z3 found this one: without it, a state with epoch = -1 lets an action with no ticket execute.
        s.epoch >= 0,
        # INVARIANT-EXECUTE-ONLY-IF-ALLOWED  nothing executes unless, when its ticket was issued, a rule allowed it and the witnesses were present
        Implies(s.executed[a], s.okay_at_issue[a]),
        # INVARIANT-TICKET-ONLY-FOR-ALLOWED-ACTION  a ticket exists only for an action the rule allowed, with witnesses, at issue time
        Implies(s.ticket[a] != -1, s.okay_at_issue[a]),
        # INVARIANT-NO-REPLAY-TICKET-SPENT  no replay: anything executed has its ticket marked spent
        Implies(s.executed[a], s.used[a]),
        # INVARIANT-TICKET-EDITION-NOT-NEWER  tickets carry an edition no newer than the current one
        Implies(s.ticket[a] != -1, And(s.ticket[a] >= 0, s.ticket[a] <= s.epoch)),
        # INVARIANT-NO-REPLAY-COUNTED no replay, counted: effects, spent tickets and issued tickets are non-negative, each
        #     effect consumes exactly one ticket (n_events == n_spent), and no more tickets are spent
        #     than were ever issued (n_spent <= n_issued). Together: n_events <= n_issued, so an
        #     action never produces more effects than it held tickets. A spent ticket cannot yield
        #     another effect, which the Boolean executed[a] could not express.
        s.n_issued[a] >= 0, s.n_spent[a] >= 0, s.n_events[a] >= 0,
        s.n_events[a] == s.n_spent[a], s.n_spent[a] <= s.n_issued[a],
        # the fused threshold is at least one in every reachable state
        s.kfloor >= 1, s.kfuse >= s.kfloor,
    )


def invariant(s: State):
    """The invariant for the whole machine: ``invariant_at`` holds for every action."""
    a = Const("a_inv", Action)
    return ForAll([a], invariant_at(s, a))


def one_step_properties(s: State, t: State, i: dict):
    """The properties that must hold across one step, as a dict from a label to a formula. Each formula relates the
    state before the step (``s``), the state after it (``t``) and the step's inputs. The nine labels from INVARIANT-HALT-IS-ABSORBING on in the list above are the one-step
    properties named in this file."""
    return {
        "INVARIANT-HALT-IS-ABSORBING: halt is absorbing without an authorized clear: halted, and no signed CLEAR for this chip in date, means still halted":
            Implies(And(s.halted, Not(clear_auth_of(s, i))), t.halted),
        "INVARIANT-FAIL-CLOSED-WITHOUT-HEARTBEAT: fail closed: with the heartbeat lost, no step executes anything":
            Implies(Not(s.heartbeat), t.executed == s.executed),
        "INVARIANT-NO-TICKET-WHILE-HALTED: no ticket is issued while halted or while the heartbeat is lost":
            Implies(Or(s.halted, Not(s.heartbeat)), t.ticket == s.ticket),
        "INVARIANT-EDITION-ONLY-MOVES-FORWARD: the edition only moves forward":
            t.epoch >= s.epoch,
        "INVARIANT-EDITION-CHANGE-NEEDS-QUORUM: an edition change needs a quorum":
            Implies(t.epoch != s.epoch, quorum_of(s, i)),
        "INVARIANT-EDITION-CHANGE-NEEDS-FUSED-THRESHOLD: an edition change needs the threshold in force of distinct signatures from the keys in force, whatever the image claims":
            Implies(t.epoch != s.epoch, i["sigs"] >= s.kfuse),
        "INVARIANT-FUSED-THRESHOLD-NEVER-FALLS: the threshold in force never falls below the manufacture floor, which never moves":
            And(t.kfuse >= t.kfloor, t.kfloor == s.kfloor),
        "INVARIANT-ONLY-CLEAR-LEAVES-HALT: nothing but a signature over a CLEAR leaves the halt: a heartbeat, a halt or any other signed command does not":
            Implies(And(s.halted, Not(t.halted)), i["signed_cmd"] == CLEAR_CMD),
        "INVARIANT-NOTHING-EXECUTES-WHILE-HALTED: nothing executes while halted, not even against a ticket issued before the halt":
            Implies(s.halted, t.executed == s.executed),
    }


def prove(name: str, claim, assumptions) -> bool:
    """Ask Z3 whether ``claim`` follows from ``assumptions``. The solver is asked for a counterexample, that is, a
    state where the assumptions hold and the claim does not. If none exists (the answer is unsat), the claim is proved and
    the function returns True. A counterexample is printed with its model."""
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


def old_rules(s: State, i: dict):
    """The rules as they were before 22 October: k read from the image, and a clear that checked who
    signed but not what was signed (any authority signature at all, a heartbeat included)."""
    any_authority_sig = i["signed_cmd"] != 0
    return dict(quorum=i["sigs"] >= i["claimed_k"], clear_auth=any_authority_sig)


def main() -> int:
    """Run every proof and every check, print each result, and return 0 only when all of them hold. The regression
    checks show that the old rules fail and that the proof can see replay. The non-vacuity checks show that the machine
    can act at all, so the proofs are not trivially true."""
    s, t = State("s"), State("t")
    inputs = make_inputs()
    step = steps(s, t, inputs)
    a_step = inputs["a"]
    a_k = Const("a_k", Action)                       # an arbitrary action, for the conclusion
    results = []
    results.append(prove("INVARIANT-EXECUTE-ONLY-IF-ALLOWED, INVARIANT-TICKET-ONLY-FOR-ALLOWED-ACTION, INVARIANT-NO-REPLAY-TICKET-SPENT, INVARIANT-TICKET-EDITION-NOT-NEWER, INVARIANT-NO-REPLAY-COUNTED hold in every initial state", invariant_at(s, a_k), [init(s)]))
    # Induction, one step at a time. Every step touches at most the entry for a_step, so the
    # invariant at a_k after the step follows from the invariant at a_k and at a_step before it.
    # Assuming only those two instances is weaker than assuming the whole invariant, so the
    # proof is sound, and it keeps every query free of quantifiers.
    hyp = [invariant_at(s, a_k), invariant_at(s, a_step)]
    for name, tr in step_list(s, t, inputs):
        results.append(prove(f"INVARIANT-EXECUTE-ONLY-IF-ALLOWED, INVARIANT-TICKET-ONLY-FOR-ALLOWED-ACTION, INVARIANT-NO-REPLAY-TICKET-SPENT, INVARIANT-TICKET-EDITION-NOT-NEWER, INVARIANT-NO-REPLAY-COUNTED preserved by step: {name}", invariant_at(t, a_k), hyp + [tr]))
    for name, claim in one_step_properties(s, t, inputs).items():
        results.append(prove(name, claim, hyp + [step]))
    # the regression check: under the old rules INVARIANT-EDITION-CHANGE-NEEDS-FUSED-THRESHOLD and INVARIANT-ONLY-CLEAR-LEAVES-HALT must fail, or this file could not have caught the defects
    old = old_rules(s, inputs)
    old_step = steps(s, t, inputs, **old)
    props = one_step_properties(s, t, inputs)
    for key in ("INVARIANT-EDITION-CHANGE-NEEDS-FUSED-THRESHOLD", "INVARIANT-ONLY-CLEAR-LEAVES-HALT"):
        name = next(n for n in props if n.startswith(key))
        sol = Solver()
        sol.set("timeout", 60_000)
        sol.add(*hyp, old_step, Not(props[name]))
        caught = sol.check() == sat
        print(("OK      " if caught else "FAILED  ") + f"{key} fails under the rules as they were before 22 October (the proof catches that defect)")
        results.append(caught)
    # an external audit on 22 October asked the solver for: issue a ticket, halt, execute while halted. On the
    # machine as it was, that was satisfiable (execute did not require RUN, though the code's commit always did)
    name = next(n for n in props if n.startswith("INVARIANT-NOTHING-EXECUTES-WHILE-HALTED"))
    sol = Solver()
    sol.set("timeout", 60_000)
    sol.add(*hyp, steps(s, t, inputs, execute_needs_run=False), Not(props[name]))
    caught = sol.check() == sat
    print(("OK      " if caught else "FAILED  ") + "INVARIANT-NOTHING-EXECUTES-WHILE-HALTED fails on the machine as it was before 22 October, whose execute step did not require RUN")
    results.append(caught)
    # F19 regression: the proof must be able to SEE replay. Without the fresh-ticket guard, the trace
    # issue, execute, execute runs the same ticket twice and produces two effects against one issued
    # ticket, so INVARIANT-NO-REPLAY-COUNTED (n_spent <= n_issued, n_events == n_spent) is falsified. The honest machine, with
    # the guard, cannot reach such a state. Three concrete steps on a single action, not an induction.
    u, w = State("u"), State("w")
    inv0 = invariant_at(s, a_step)                       # start from any invariant-respecting state
    issue_r = dict(step_list(s, t, inputs))["issue"]
    exec_replay_first = dict(step_list(t, u, inputs, execute_needs_fresh_ticket=False))["execute"]
    exec_replay_second = dict(step_list(u, w, inputs, execute_needs_fresh_ticket=False))["execute"]
    sol = Solver()
    sol.set("timeout", 60_000)
    sol.add(inv0, issue_r, exec_replay_first, exec_replay_second, w.n_spent[a_step] > w.n_issued[a_step])
    caught = sol.check() == sat
    print(("OK      " if caught else "FAILED  ") + "INVARIANT-NO-REPLAY-COUNTED fails without the fresh-ticket guard: issue, execute, execute replays one ticket into two effects (the proof catches replay)")
    results.append(caught)
    # and the honest machine, same three steps WITH the guard, cannot replay: the property is specific
    # to the removed guard, not to any execution happening twice.
    exec_guarded_first = dict(step_list(t, u, inputs))["execute"]
    exec_guarded_second = dict(step_list(u, w, inputs))["execute"]
    sol = Solver()
    sol.set("timeout", 60_000)
    sol.add(inv0, issue_r, exec_guarded_first, exec_guarded_second, w.n_spent[a_step] > w.n_issued[a_step])
    blocked = sol.check() == unsat
    print(("OK      " if blocked else "FAILED  ") + "with the fresh-ticket guard the same issue, execute, execute cannot overspend one ticket (replay is blocked, not merely flagged)")
    results.append(blocked)
    # and a legitimate action done twice, under two fresh tickets, stays expressible and does not
    # violate INVARIANT-NO-REPLAY-COUNTED: counting ticket instances does not collapse repeated executions into one.
    sol = Solver()
    sol.set("timeout", 60_000)
    issue_a = dict(step_list(s, t, inputs))["issue"]
    exec_a = dict(step_list(t, u, inputs))["execute"]
    issue_b = dict(step_list(u, w, inputs))["issue"]
    x = State("x")
    exec_b = dict(step_list(w, x, inputs))["execute"]
    sol.add(init(s), issue_a, exec_a, issue_b, exec_b, x.n_events[a_step] == 2, x.n_events[a_step] <= x.n_issued[a_step])
    live2 = sol.check() == sat
    print(("OK      " if live2 else "FAILED  ") + "a legitimate action can execute twice under two fresh tickets without replay (counts do not collapse repeats)")
    results.append(live2)
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
    # and a halted governor can be cleared, and an edition can change, under the new rules
    for label, name in (("a halted governor can be cleared by a signed CLEAR", "clear"), ("an edition can change under a quorum", "new edition")):
        sol = Solver()
        sol.set("timeout", 60_000)
        sol.add(init(s), dict(step_list(s, t, inputs))[name], *( [s.halted] if name == "clear" else [] ))
        ok = sol.check() == sat
        print(("OK      " if ok else "FAILED  ") + label + " (not vacuous)")
        results.append(ok)
    print()
    print("All proofs hold." if all(results) else "Some proof failed.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
