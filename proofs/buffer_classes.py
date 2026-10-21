#!/usr/bin/env python3
"""Machine-checked proofs of buffer classes (policy.BUFFER_POLICY, DescriptorChecker, Governor._capability).

    python3 proofs/buffer_classes.py

At the integrated tier a descriptor checker at the copy engine and the peer MMU keys its table on
(peer, direction, buffer class), and the governor writes an entry only where the policy's buffer policy allows that
class to go to that peer. Proven by induction, for any number of buffer classes and any number of peers (both are
uninterpreted sorts, so a class the policy never named is covered):

  (1) weights never cross: a class whose scope is "none" crosses to no peer, host or roster;
  (2) activations go only to roster peers: a class whose scope is "roster" crosses only to a roster peer;
  (3) outputs go only to the host: a class whose scope is "host" crosses only to the host and never to a roster peer;
  (4) a class with no entry, or an unknown scope, crosses nowhere: fail closed;
  (5) a peer that is neither the host nor on the roster receives no class at all;
  (6) the governor writes no entry the buffer policy does not allow.

The machine. A peer is the host, a roster member, or a stranger (host and roster are disjoint). Scope codes are
0 none, 1 roster, 2 host, 3 any-roster-or-host; any other code is treated as none, as the code does. State:
  cap[c][p]   the checker holds an entry for class c to peer p        swcap[p]   the class-blind switch holds an entry for p
  crossed[c][p]  ghost: bytes of class c have gone to p              scope, host, roster, checker, forced  (fixed for the run)
There are two exits. The checked exit (copy engine, peer MMU) passes class c to p when the checker holds the entry;
with no checker (rack and board tiers) it passes anything (EP_UNCHECKED). The switch exit (NVSwitch, PCIe, DPU) cannot
see a class: it passes anything to a peer it holds an entry for.

THE ASSUMPTION THAT CARRIES THE PROOF. The theorems (1) to (5) hold when `forced` is true: every byte that leaves
device memory for a switch has first been through the descriptor checker, which is what the integrated tier means
(the checker is in the DMA path). `forced` is a property of the silicon, not something this model derives. Without it
the same machine lets weights cross a class-blind switch to a roster peer (found below, as a search that must succeed),
and at the rack and board tiers there is no checker at all (the recorded residual N5, tests/test_h02). Both gaps are
shown as runs of the machine, not hidden.

Left out, on purpose: the capability MAC (a relabelled class fails it, tested in H2b), expiry, epoch tag and byte budget
of an entry (budgets.py), direction (every entry here is "both"), a policy edition change mid-run, and the rule that the
host is reachable only through the PCIe point.
"""
from __future__ import annotations

import sys

from z3 import And, BoolSort, DeclareSort, If, Implies, IntSort, Not, Or

from _kit import Machine, finish, g, reach, run

Cls, Peer = DeclareSort("Cls"), DeclareSort("Peer")
I, B = IntSort(), BoolSort()

m = Machine({"scope": ((Cls,), I), "host": ((Peer,), B), "roster": ((Peer,), B), "checker": ((), B), "forced": ((), B),
             "cap": ((Cls, Peer), B), "swcap": ((Peer,), B), "crossed": ((Cls, Peer), B)},
            {"c": Cls, "p": Peer})


def allowed(s, c, p):
    """policy.buffer_allowed, for a peer that is the host or a roster member."""
    sc = g(s, "scope", c)
    return Or(And(g(s, "host", p), Or(sc == 2, sc == 3)), And(g(s, "roster", p), Or(sc == 1, sc == 3)))


def assume(s, q):
    return And(Not(And(g(s, "host", q.p), g(s, "roster", q.p))), Implies(s.forced, s.checker))


def init(s, q):
    return And(Not(g(s, "cap", q.c, q.p)), Not(g(s, "swcap", q.p)), Not(g(s, "crossed", q.c, q.p)))


def inv(s, q):
    c, p = q.c, q.p
    return And(
        Implies(g(s, "cap", c, p), allowed(s, c, p)),                                   # (6) only allowed entries are written
        Implies(g(s, "swcap", p), Or(g(s, "host", p), g(s, "roster", p))),              # a switch entry is for the host or a roster peer
        Implies(s.forced, Implies(g(s, "crossed", c, p), allowed(s, c, p))),             # what crossed was allowed
    )


def attempt(s, t, guard, **chg):
    return Or(And(guard, m.upd(s, t, **chg)), And(Not(guard), m.upd(s, t)))


def mint_checker_entry(s, t, p):        # Governor._capability_batch / cap_request at a checker: the buffer policy has the last word
    return attempt(s, t, And(s.checker, allowed(s, p.c, p.p)), cap=((p.c, p.p), True))


def mint_switch_entry(s, t, p):         # at a switch there is no class to key on; the peer must be the host or on the roster
    return attempt(s, t, Or(g(s, "host", p.p), g(s, "roster", p.p)), swcap=((p.p,), True))


def checked_exit(s, t, p):              # copy engine / peer MMU: the checker passes the class if it holds the entry
    return attempt(s, t, If(s.checker, g(s, "cap", p.c, p.p), True), crossed=((p.c, p.p), True))


def switch_exit(s, t, p):               # the switch passes anything to a peer it holds an entry for; forced: via the checker first
    return attempt(s, t, And(g(s, "swcap", p.p), If(s.forced, g(s, "cap", p.c, p.p), True)), crossed=((p.c, p.p), True))


steps = [("mint a checker entry", mint_checker_entry), ("mint a switch entry", mint_switch_entry),
         ("transfer at the checked exit", checked_exit), ("transfer at the switch exit", switch_exit)]


def thm(name, claim):
    return [(f"{name} (checked exit)", "transfer at the checked exit", claim), (f"{name} (switch exit)", "transfer at the switch exit", claim)]


theorems = []
theorems += thm("(1) a class with scope none crosses to no peer",
                lambda s, t, p: Implies(And(t.forced, g(t, "scope", p.c) == 0), Not(g(t, "crossed", p.c, p.p))))
theorems += thm("(2) a roster-scope class crosses only to a roster peer, never the host",
                lambda s, t, p: Implies(And(t.forced, g(t, "scope", p.c) == 1, g(t, "crossed", p.c, p.p)),
                                        And(g(t, "roster", p.p), Not(g(t, "host", p.p)))))
theorems += thm("(3) a host-scope class crosses only to the host, never a roster peer",
                lambda s, t, p: Implies(And(t.forced, g(t, "scope", p.c) == 2, g(t, "crossed", p.c, p.p)),
                                        And(g(t, "host", p.p), Not(g(t, "roster", p.p)))))
theorems += thm("(4) a class with an unknown scope crosses nowhere",
                lambda s, t, p: Implies(And(t.forced, Or(g(t, "scope", p.c) < 0, g(t, "scope", p.c) > 3)), Not(g(t, "crossed", p.c, p.p))))
theorems += thm("(5) a stranger receives no class at all",
                lambda s, t, p: Implies(And(t.forced, Not(g(t, "host", p.p)), Not(g(t, "roster", p.p))), Not(g(t, "crossed", p.c, p.p))))
theorems += [("(6) the governor writes no checker entry the buffer policy disallows", "mint a checker entry",
              lambda s, t, p: Implies(Not(allowed(s, p.c, p.p)), g(t, "cap", p.c, p.p) == g(s, "cap", p.c, p.p)))]


def fixed(forced, checker, scope, **peer):
    def init_fn(s, p):
        parts = [init(s, p), s.forced == forced, s.checker == checker, g(s, "scope", p.c) == scope]
        if "host" in peer:
            parts += [g(s, "host", p.p) == peer["host"], g(s, "roster", p.p) == peer["roster"]]
        return And(*parts)
    return init_fn


def activations_reach_a_roster_peer():
    return reach(m, fixed(True, True, 1, host=False, roster=True), [mint_checker_entry, mint_switch_entry, checked_exit, switch_exit],
                 lambda t, p, s0: g(t, "crossed", p.c, p.p), assume)


def outputs_reach_the_host():
    return reach(m, fixed(True, True, 2, host=True, roster=False), [mint_checker_entry, mint_switch_entry, switch_exit],
                 lambda t, p, s0: g(t, "crossed", p.c, p.p), assume)


def gap_class_blind_switch():
    """Found: weights (scope none) cross a class-blind switch to a roster peer when the path is not forced through the checker."""
    return reach(m, fixed(False, True, 0, host=False, roster=True), [mint_switch_entry, switch_exit],
                 lambda t, p, s0: g(t, "crossed", p.c, p.p), assume)


def gap_no_checker():
    """Found: at the rack and board tiers (no checker) weights leave through the copy engine with EP_UNCHECKED (N5)."""
    return reach(m, fixed(False, False, 0, host=False, roster=True), [checked_exit],
                 lambda t, p, s0: g(t, "crossed", p.c, p.p), assume)


live = [("activations cross to a roster peer when the policy says roster (not vacuous)", activations_reach_a_roster_peer),
        ("outputs cross to the host when the policy says host (not vacuous)", outputs_reach_the_host),
        ("RECORDED GAP, found as it must be: weights cross a class-blind switch if the path is not forced through the checker", gap_class_blind_switch),
        ("RECORDED GAP, found as it must be: with no checker (rack, board tier) weights leave unchecked (N5)", gap_no_checker)]


def main() -> int:
    return finish(run(m, init, inv, steps, theorems, live, assume))


if __name__ == "__main__":
    sys.exit(main())
