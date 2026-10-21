"""Shared plumbing for the Wave 2 proofs: a state machine over Z3 arrays, an induction runner, a trace search.

Each proof file declares its fields (a name, the sorts it is indexed by, the sort of its value), an
initial condition, an invariant at one instance of the indices, and its transitions. The runner checks:

  * the invariant holds in the initial state,
  * every transition takes a state satisfying the invariant (at an arbitrary instance and at the
    transition's own instance) to a state satisfying it, which is induction over every sequence of
    steps and over any number of instances,
  * each named theorem about one transition,
  * each non-vacuity trace: a short sequence the machine can really perform.

Everything is quantifier-free, so Z3 decides it. ``assume`` carries facts about the environment
that no transition may break (the physics of the loop, a fixed policy): they are stated in the
docstring of the file that uses them and are assumed in every state.
"""
from __future__ import annotations

from types import SimpleNamespace

from z3 import And, ArraySort, Const, Not, Solver, Store, sat, unsat

TIMEOUT_MS = 120_000


def prove(name, claim, assumptions) -> bool:
    sol = Solver()
    sol.set("timeout", TIMEOUT_MS)
    sol.add(*assumptions)
    sol.add(Not(claim))
    r = sol.check()
    print(f"{'PROVED ' if r == unsat else 'FAILED ' if r == sat else 'UNKNOWN'} {name}")
    if r == sat:
        print(sol.model())
    return r == unsat


def g(s, name, *idx):
    """Read field ``name`` of state ``s`` at ``idx``."""
    x = getattr(s, name)
    for i in idx:
        x = x[i]
    return x


def _put(arr, idx, val):
    if not idx:
        return val
    return Store(arr, idx[0], _put(arr[idx[0]], idx[1:], val))


class Machine:
    def __init__(self, fields: dict, params: dict):
        self.fields, self.params = fields, params     # fields: name -> (index sorts, value sort); params: name -> sort

    def state(self, tag):
        ns = SimpleNamespace()
        for n, (idx, val) in self.fields.items():
            srt = val
            for i in reversed(idx):
                srt = ArraySort(i, srt)
            setattr(ns, n, Const(f"{n}_{tag}", srt))
        return ns

    def pars(self, tag):
        return SimpleNamespace(**{n: Const(f"{n}_{tag}", srt) for n, srt in self.params.items()})

    def upd(self, s, t, **changes):
        """t is s with the named fields changed: name=(index tuple, new value); every other field is kept."""
        out = []
        for n in self.fields:
            if n in changes:
                idx, val = changes[n]
                out.append(getattr(t, n) == _put(getattr(s, n), tuple(idx), val))
            else:
                out.append(getattr(t, n) == getattr(s, n))
        return And(*out)


def run(m: Machine, init, inv, steps, theorems=(), live=(), assume=lambda s, q: True) -> bool:
    """steps: [(name, fn(s, t, p))]; theorems: [(name, step name, fn(s, t, p) -> claim)]; live: [(name, fn() -> bool)]."""
    s, t = m.state("s"), m.state("t")
    p, k = m.pars("p"), m.pars("k")
    ok = [prove("invariant holds initially", inv(s, k), [init(s, k), assume(s, k)])]
    hyp = [inv(s, k), inv(s, p), assume(s, k), assume(s, p), assume(t, k), assume(t, p)]
    table = dict(steps)
    for name, fn in steps:
        ok.append(prove(f"invariant preserved by: {name}", inv(t, k), hyp + [fn(s, t, p)]))
    for name, step, claim in theorems:
        ok.append(prove(name, claim(s, t, p), hyp + [table[step](s, t, p)]))
    for name, fn in live:
        r = fn()
        print(("OK      " if r else "FAILED  ") + name)
        ok.append(r)
    return all(ok)


def reach(m: Machine, init, seq, goal, assume=lambda s, q: True, extra=None) -> bool:
    """Is there a run init -> seq[0] -> seq[1] ... whose last state meets goal(last, p, first)? All steps share p."""
    states = [m.state(f"r{i}") for i in range(len(seq) + 1)]
    p = m.pars("rp")
    sol = Solver()
    sol.set("timeout", TIMEOUT_MS)
    sol.add(init(states[0], p))
    for st in states:
        sol.add(assume(st, p))
    for i, fn in enumerate(seq):
        sol.add(fn(states[i], states[i + 1], p))
    sol.add(goal(states[-1], p, states[0]))
    if extra is not None:
        sol.add(extra(p))
    return sol.check() == sat


def finish(ok: bool) -> int:
    print()
    print("All proofs hold." if ok else "Some proof failed.")
    return 0 if ok else 1
