#!/usr/bin/env python3
"""Machine-checked proofs of budgets and rate windows: byte, compute and session hazard budgets, per-action rates.

    python3 proofs/budgets.py

Four small machines, each proven by induction over every sequence of steps and for any number of keys
(a key is an uninterpreted sort, so one proof covers every budget key, every fingerprint, every session):

  1. LEDGER   (govsim/ledger.py reserve, commit, release, window purge). Compute and byte budgets that a
              rule spends from are one machine: committed + reserved never exceeds the limit, a commit moves
              an amount from reserved to committed without changing the total, and a refused reserve changes nothing.
  2. RATE     (Ledger.rate_ok, the per-action rate window `rate|fingerprint|action`): at most `max` events are
              counted in a window; an event at the limit is refused; sliding the window only forgets events.
              Keys are separate: counting one key never moves another.
  3. HAZARD   (the response.release session hazard budget): a hazard verdict is counted before the check; one past
              the maximum holds the response and raises the alarm, it never releases; a count over the maximum
              always has the alarm up.
  4. BYTES    (Switch._admit, the per-entry byte budget): bytes passed + bytes left = bytes granted; a pass never
              exceeds what is left; a re-grant by the governor starts a new entry whose total counts what has passed.

Left out, on purpose: wall-clock time (a window slide is any amount the window forgets, so the proof holds for
every clock); per-reservation identity (a commit of a reservation that has already expired or been committed is
refused in the code because its id is gone; here that is the guard `x <= reserved`, so the aggregate is what is
proven); the cap MAC and the signature on a ticket; durability across power loss (the store tests); policy changes
that lower a limit (a reserve is checked against the limit of the moment, and the limit is fixed here).

Assumptions the proof needs, recorded because the code does not enforce all of them: an amount is not negative
(Ledger.reserve refuses a negative amount; Switch._admit does not check, so it relies on a byte count being an
unsigned length, as it is in hardware: see EXPERIMENTS.md, L3), and a limit or maximum is not negative.
"""
from __future__ import annotations

import sys

from z3 import And, BoolSort, DeclareSort, If, Implies, IntSort, Not, Or

from _kit import Machine, finish, g, reach, run

Key = DeclareSort("Key")
I, B = IntSort(), BoolSort()


# ------------------------------------------------------------------------------------------ 1. ledger
def ledger() -> bool:
    print("== 1. ledger: committed + reserved <= limit ==")
    m = Machine({"limit": ((Key,), I), "committed": ((Key,), I), "reserved": ((Key,), I)},
                {"key": Key, "amt": I, "x": I})
    L, C, R = (lambda s, q: g(s, "limit", q.key)), (lambda s, q: g(s, "committed", q.key)), (lambda s, q: g(s, "reserved", q.key))

    def assume(s, q):
        return L(s, q) >= 0

    def init(s, q):
        return And(C(s, q) == 0, R(s, q) == 0)

    def inv(s, q):
        return And(C(s, q) >= 0, R(s, q) >= 0, C(s, q) + R(s, q) <= L(s, q))

    def reserve(s, t, p):
        return And(p.amt >= 0, C(s, p) + R(s, p) + p.amt <= L(s, p), m.upd(s, t, reserved=((p.key,), R(s, p) + p.amt)))

    def reserve_refused(s, t, p):
        return And(Or(p.amt < 0, C(s, p) + R(s, p) + p.amt > L(s, p)), m.upd(s, t))

    def commit(s, t, p):
        return And(0 <= p.x, p.x <= R(s, p), m.upd(s, t, reserved=((p.key,), R(s, p) - p.x), committed=((p.key,), C(s, p) + p.x)))

    def commit_refused(s, t, p):       # the reservation is gone (expired, released, already committed): nothing moves
        return And(Or(p.x < 0, p.x > R(s, p)), m.upd(s, t))

    def release(s, t, p):              # a release, or a reservation whose ttl ran out
        return And(0 <= p.x, p.x <= R(s, p), m.upd(s, t, reserved=((p.key,), R(s, p) - p.x)))

    def slide(s, t, p):                # the window forgets committed spend
        return And(0 <= p.x, p.x <= C(s, p), m.upd(s, t, committed=((p.key,), C(s, p) - p.x)))

    other = m.pars("other")
    steps = [("reserve", reserve), ("reserve refused", reserve_refused), ("commit", commit),
             ("commit refused", commit_refused), ("release or expiry", release), ("window slides", slide)]
    theorems = [
        ("a successful reserve leaves committed + reserved within the limit", "reserve",
         lambda s, t, p: C(t, p) + R(t, p) <= L(t, p)),
        ("a commit does not change the total in use", "commit",
         lambda s, t, p: C(t, p) + R(t, p) == C(s, p) + R(s, p)),
        ("a release gives back exactly what it releases", "release or expiry",
         lambda s, t, p: R(t, p) + p.x == R(s, p)),
        ("a refused reserve changes no key's usage", "reserve refused",
         lambda s, t, p: And(C(t, p) == C(s, p), R(t, p) == R(s, p))),
        ("a reserve on one key leaves every other key alone", "reserve",
         lambda s, t, p: Implies(Not(p.key == other.key), And(g(t, "reserved", other.key) == g(s, "reserved", other.key),
                                                              g(t, "committed", other.key) == g(s, "committed", other.key)))),
    ]

    def fill_to_limit():
        return reach(m, lambda s, p: And(init(s, p), L(s, p) == 10), [reserve, commit, reserve],
                     lambda t, p, s0: And(p.amt == 5, p.x == 5, C(t, p) + R(t, p) == 10))

    def over_limit_refused():
        return reach(m, lambda s, p: And(init(s, p), L(s, p) == 10, p.amt == 10), [reserve, reserve_refused],
                     lambda t, p, s0: True)

    live = [("a key can be filled to its limit by reserve, commit, reserve (not vacuous)", fill_to_limit),
            ("a second reserve past the limit is refused after the first (not vacuous)", over_limit_refused)]
    return run(m, init, inv, steps, theorems, live, assume)


# --------------------------------------------------------------------------------------------- 2. rate
def rate() -> bool:
    print("== 2. rate window: at most max events per window, per key ==")
    m = Machine({"n": ((Key,), I), "mx": ((Key,), I)}, {"key": Key, "x": I})
    N, M = (lambda s, q: g(s, "n", q.key)), (lambda s, q: g(s, "mx", q.key))

    def assume(s, q):
        return M(s, q) >= 0

    def init(s, q):
        return N(s, q) == 0

    def inv(s, q):
        return And(0 <= N(s, q), N(s, q) <= M(s, q))

    def allow(s, t, p):
        return And(N(s, p) < M(s, p), m.upd(s, t, n=((p.key,), N(s, p) + 1)))

    def refuse(s, t, p):
        return And(N(s, p) >= M(s, p), m.upd(s, t))

    def slide(s, t, p):
        return And(0 <= p.x, p.x <= N(s, p), m.upd(s, t, n=((p.key,), N(s, p) - p.x)))

    other = m.pars("other")
    theorems = [
        ("an allowed event leaves at most max events in the window", "allow", lambda s, t, p: N(t, p) <= M(t, p)),
        ("a refused event is not counted", "refuse", lambda s, t, p: N(t, p) == N(s, p)),
        ("counting one key's event never moves another key", "allow",
         lambda s, t, p: Implies(Not(p.key == other.key), g(t, "n", other.key) == g(s, "n", other.key))),
    ]

    def at_limit_then_refused():
        return reach(m, lambda s, p: And(init(s, p), M(s, p) == 2), [allow, allow, refuse], lambda t, p, s0: N(t, p) == 2)

    def slide_reopens():
        return reach(m, lambda s, p: And(init(s, p), M(s, p) == 1, p.x == 1), [allow, refuse, slide, allow], lambda t, p, s0: N(t, p) == 1)

    live = [("a window fills to max and the next event is refused (not vacuous)", at_limit_then_refused),
            ("after the window slides the key accepts an event again (not vacuous)", slide_reopens)]
    return run(m, init, inv, [("allow", allow), ("refuse", refuse), ("window slides", slide)], theorems, live, assume)


# ------------------------------------------------------------------------------------------ 3. hazard
def hazard() -> bool:
    print("== 3. session hazard budget: over the maximum holds and alarms, never releases ==")
    Hz = DeclareSort("Hz")      # a session
    m = Machine({"c": ((Hz,), I), "mx": ((Hz,), I), "alarm": ((Hz,), B)}, {"sess": Hz, "hazard": B, "x": I})
    Cn, M, A = (lambda s, q: g(s, "c", q.sess)), (lambda s, q: g(s, "mx", q.sess)), (lambda s, q: g(s, "alarm", q.sess))

    def assume(s, q):
        return M(s, q) >= 0

    def init(s, q):
        return And(Cn(s, q) == 0, Not(A(s, q)))

    def inv(s, q):
        return And(Cn(s, q) >= 0, Implies(Cn(s, q) > M(s, q), A(s, q)))

    def counted(s, p):
        return Cn(s, p) + If(p.hazard, 1, 0)

    def release(s, t, p):          # the verdict is counted first; within the maximum the response goes on to the other checks
        return And(counted(s, p) <= M(s, p), m.upd(s, t, c=((p.sess,), counted(s, p))))

    def hold(s, t, p):             # past the maximum: hold the response and raise SESSION_HAZARD_BUDGET
        return And(counted(s, p) > M(s, p), m.upd(s, t, c=((p.sess,), counted(s, p)), alarm=((p.sess,), True)))

    def slide(s, t, p):
        return And(0 <= p.x, p.x <= Cn(s, p), m.upd(s, t, c=((p.sess,), Cn(s, p) - p.x)))

    theorems = [
        ("a response goes on to release only with the session count within the maximum", "release",
         lambda s, t, p: Cn(t, p) <= M(t, p)),
        ("one past the maximum raises the alarm", "hold and alarm", lambda s, t, p: A(t, p)),
        ("a verdict with no hazard is not counted", "release", lambda s, t, p: Implies(Not(p.hazard), Cn(t, p) == Cn(s, p))),
        ("an alarm once raised stays raised through a window slide", "window slides", lambda s, t, p: Implies(A(s, p), A(t, p))),
    ]

    def third_hazard_alarms():
        return reach(m, lambda s, p: And(init(s, p), M(s, p) == 2, p.hazard), [release, release, hold], lambda t, p, s0: A(t, p))

    def clean_session_never_counts():
        return reach(m, lambda s, p: And(init(s, p), M(s, p) == 0, Not(p.hazard)), [release, release], lambda t, p, s0: Cn(t, p) == 0)

    live = [("the third hazard verdict of a two-hazard session holds and alarms (not vacuous)", third_hazard_alarms),
            ("a session with no hazard verdicts releases freely at maximum 0 (not vacuous)", clean_session_never_counts)]
    return run(m, init, inv, [("release", release), ("hold and alarm", hold), ("window slides", slide)], theorems, live, assume)


# -------------------------------------------------------------------------------------------- 4. bytes
def byte_budget() -> bool:
    print("== 4. switch byte budget: bytes passed + bytes left = bytes granted ==")
    Ent = DeclareSort("Entry")
    m = Machine({"left": ((Ent,), I), "passed": ((Ent,), I), "granted": ((Ent,), I)}, {"e": Ent, "n": I, "grant": I})
    Lf, Ps, Gr = (lambda s, q: g(s, "left", q.e)), (lambda s, q: g(s, "passed", q.e)), (lambda s, q: g(s, "granted", q.e))

    def init(s, q):
        return And(Gr(s, q) >= 0, Lf(s, q) == Gr(s, q), Ps(s, q) == 0)

    def inv(s, q):
        return And(Lf(s, q) >= 0, Ps(s, q) >= 0, Ps(s, q) + Lf(s, q) == Gr(s, q))

    def admit(s, t, p):
        return And(p.n >= 0, Lf(s, p) >= p.n, m.upd(s, t, left=((p.e,), Lf(s, p) - p.n), passed=((p.e,), Ps(s, p) + p.n)))

    def refuse(s, t, p):           # EP_BUDGET_EXHAUSTED: nothing is counted
        return And(p.n >= 0, Lf(s, p) < p.n, m.upd(s, t))

    def regrant(s, t, p):          # the governor writes a new entry with a fresh budget; what has passed stays counted
        return And(p.grant >= 0, m.upd(s, t, left=((p.e,), p.grant), granted=((p.e,), Ps(s, p) + p.grant)))

    theorems = [
        ("a pass never exceeds what was left", "admit", lambda s, t, p: Lf(t, p) >= 0),
        ("total bytes passed never exceed total bytes granted", "admit", lambda s, t, p: Ps(t, p) <= Gr(t, p)),
        ("a refused pass moves no byte", "refuse", lambda s, t, p: And(Lf(t, p) == Lf(s, p), Ps(t, p) == Ps(s, p))),
        ("a re-grant keeps the bytes already passed counted", "regrant", lambda s, t, p: Ps(t, p) == Ps(s, p)),
    ]

    def exact_drain():
        return reach(m, lambda s, p: And(init(s, p), Gr(s, p) == 10, p.n == 5), [admit, admit], lambda t, p, s0: Lf(t, p) == 0)

    def refused_when_empty():
        return reach(m, lambda s, p: And(init(s, p), Gr(s, p) == 5, p.n == 5), [admit, refuse], lambda t, p, s0: Lf(t, p) == 0)

    live = [("a 10-byte entry passes two 5-byte transfers and is then empty (not vacuous)", exact_drain),
            ("an empty entry refuses the next transfer (not vacuous)", refused_when_empty)]
    return run(m, init, inv, [("admit", admit), ("refuse", refuse), ("regrant", regrant)], theorems, live)


def main() -> int:
    return finish(all([ledger(), rate(), hazard(), byte_budget()]))


if __name__ == "__main__":
    sys.exit(main())
