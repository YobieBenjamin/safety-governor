#!/usr/bin/env python3
"""Machine-checked proofs of k-of-n human approvals on a hold (Governor._cmd_approve).

    python3 proofs/approvals.py

A rule can park an action on a hold until `approvers_quorum` distinct approvers sign it. The governor mints the
ticket when the quorum is in and the latency floor has passed. Proven here by induction, for any number of holds
and any number of rules (both are uninterpreted sorts):

  (1) a hold is released, and its ticket minted, only with at least `quorum` distinct approvers who are scoped to
      that hold's rule and have signed that hold's request, and only after the latency floor;
  (2) an approver is scoped to a rule (the policy's `approver_keys[rule]`): a signer not listed for the hold's rule,
      a stranger, changes nothing, however well formed their signature;
  (3) a signature counts for one hold only: approving one hold never moves another;
  (4) a hold is released at most once: one hold, at most one ticket;
  (5) a hold id is fresh: a hold that has been released is never created again, so old signatures never count for a new hold.

The machine. Approvers are four explicit identities (so "distinct" is a real count, not a counter that could drift);
holds, rules and the quorum are free. For every hold h:
  exists[h]    the hold is parked and can still be approved       released[h]  its ticket has been minted
  rule[h]      the rule the hold was created under                quorum[h]    max(1, approvers_quorum), fixed at creation
  age_ok[h]    the latency floor has passed (time only moves forward, so this never reverts)
  sig_i[h]     approver i has signed this hold's request          tickets[h]   tickets minted for h
  scoped_i[r]  approver i is listed under rule r (the signed policy; fixed for the run)

Left out, on purpose: the signature itself (a signature that does not verify is the input `sigok = false`, and the
cryptography is assumed unforgeable, as in core_invariants.py); the text of the written reason beyond "non-empty"
(input `reason_ok`); that the request hash matches the hold (input `req_ok`); the wall-clock value of the floor (only
that it has passed); a policy change while a hold is open (holds survive an edition change in the code; here the scope
table is fixed for the run); more than four approvers (the counting argument is the same for any n, and the sort of
holds and rules is unbounded); and the alarm-clear approval ("alarms" scope), which uses the same check.
"""
from __future__ import annotations

import sys

from z3 import And, BoolSort, DeclareSort, If, Implies, IntSort, Not, Or, Sum

from _kit import Machine, finish, g, reach, run

Hold, Rule = DeclareSort("Hold"), DeclareSort("Rule")
I, B = IntSort(), BoolSort()
N = 4

fields = {"exists": ((Hold,), B), "released": ((Hold,), B), "rule": ((Hold,), Rule), "quorum": ((Hold,), I),
          "age_ok": ((Hold,), B), "tickets": ((Hold,), I)}
fields.update({f"sig{i}": ((Hold,), B) for i in range(N)})
fields.update({f"scoped{i}": ((Rule,), B) for i in range(N)})
m = Machine(fields, {"h": Hold, "h2": Hold, "r": Rule, "q": I, "sigok": B, "req_ok": B, "reason_ok": B})


def count(s, h):
    return Sum([If(g(s, f"sig{i}", h), 1, 0) for i in range(N)])


def scoped_count(s, h):
    return Sum([If(And(g(s, f"sig{i}", h), g(s, f"scoped{i}", g(s, "rule", h))), 1, 0) for i in range(N)])


def init(s, q):
    return And(Not(g(s, "exists", q.h)), Not(g(s, "released", q.h)), g(s, "tickets", q.h) == 0,
               *[Not(g(s, f"sig{i}", q.h)) for i in range(N)])


def inv(s, q):
    h = q.h
    return And(
        Implies(g(s, "exists", h), g(s, "quorum", h) >= 1),                           # a quorum is at least one
        Not(And(g(s, "exists", h), g(s, "released", h))),                              # a released hold is no longer open
        g(s, "tickets", h) == If(g(s, "released", h), 1, 0),                           # (4) one ticket, once
        Implies(Not(Or(g(s, "exists", h), g(s, "released", h))), And(*[Not(g(s, f"sig{i}", h)) for i in range(N)])),
        *[Implies(g(s, f"sig{i}", h), g(s, f"scoped{i}", g(s, "rule", h))) for i in range(N)],   # (2) only scoped signers are on file
    )


def create(s, t, p):                 # the gate parks an action: a fresh id, the rule's quorum, no signatures, floor not passed
    fresh = And(Not(g(s, "exists", p.h)), Not(g(s, "released", p.h)), p.q >= 1)
    chg = dict(exists=((p.h,), True), rule=((p.h,), p.r), quorum=((p.h,), p.q), age_ok=((p.h,), False))
    return And(fresh, m.upd(s, t, **chg))


def create_refused(s, t, p):         # an id already in use, or a released one, is never recreated
    return And(Or(g(s, "exists", p.h), g(s, "released", p.h), p.q < 1), m.upd(s, t))


def approve_guard(s, p, i):
    return And(g(s, "exists", p.h), p.sigok, g(s, f"scoped{i}", g(s, "rule", p.h)), p.req_ok, p.reason_ok)


def approve(i):
    def step(s, t, p):               # an attempt by approver i: it counts only if every check passes; otherwise nothing changes
        yes = And(approve_guard(s, p, i), m.upd(s, t, **{f"sig{i}": ((p.h,), True)}))
        no = And(Not(approve_guard(s, p, i)), m.upd(s, t))
        return Or(yes, no)
    return step


def age(s, t, p):                    # the latency floor passes
    return And(g(s, "exists", p.h), m.upd(s, t, age_ok=((p.h,), True)))


def release_guard(s, p):
    return And(g(s, "exists", p.h), count(s, p.h) >= g(s, "quorum", p.h), g(s, "age_ok", p.h))


def release(s, t, p):                # the quorum is in and the floor has passed: mint the ticket, pop the hold
    yes = And(release_guard(s, p), m.upd(s, t, exists=((p.h,), False), released=((p.h,), True), tickets=((p.h,), g(s, "tickets", p.h) + 1)))
    no = And(Not(release_guard(s, p)), m.upd(s, t))      # APPROVE_QUORUM_PENDING or APPROVE_TOO_FAST: nothing is minted
    return Or(yes, no)


steps = [("create hold", create), ("create refused", create_refused), ("age passes", age), ("release attempt", release)]
steps += [(f"approve attempt by approver {i}", approve(i)) for i in range(N)]


def theorems():
    out = [
        ("(1) a release carries at least `quorum` distinct scoped approvers, at least one, after the floor",
         "release attempt",
         lambda s, t, p: Implies(And(g(t, "released", p.h), Not(g(s, "released", p.h))),
                                 And(scoped_count(s, p.h) >= g(s, "quorum", p.h), g(s, "quorum", p.h) >= 1, g(s, "age_ok", p.h)))),
        ("(4) a hold already released mints nothing more", "release attempt",
         lambda s, t, p: Implies(g(s, "released", p.h), g(t, "tickets", p.h) == g(s, "tickets", p.h))),
        ("(4b) a release is a transition from open to released, never the reverse", "release attempt",
         lambda s, t, p: Implies(g(s, "released", p.h), g(t, "released", p.h))),
        ("(5) a hold id that was released is never reopened", "create hold",
         lambda s, t, p: Not(g(s, "released", p.h))),
    ]
    for i in range(N):
        out.append((f"(2) approver {i}, not scoped to the hold's rule, changes no signature", f"approve attempt by approver {i}",
                    lambda s, t, p, i=i: Implies(Not(g(s, f"scoped{i}", g(s, "rule", p.h))), g(t, f"sig{i}", p.h) == g(s, f"sig{i}", p.h))))
        out.append((f"(2b) approver {i}'s unverified or mismatched signature changes nothing", f"approve attempt by approver {i}",
                    lambda s, t, p, i=i: Implies(Not(And(p.sigok, p.req_ok, p.reason_ok)), g(t, f"sig{i}", p.h) == g(s, f"sig{i}", p.h))))
        out.append((f"(3) approver {i}'s signature on one hold moves no other hold", f"approve attempt by approver {i}",
                    lambda s, t, p, i=i: Implies(Not(p.h2 == p.h), And(*[g(t, f"sig{j}", p.h2) == g(s, f"sig{j}", p.h2) for j in range(N)]))))
    return out


def two_of_three():
    # approvers 0 and 1 are listed for the rule; two sign; the floor passes; the hold is released with quorum 2
    seq = [create, approve(0), approve(1), age, release]
    return reach(m, lambda s, p: And(init(s, p), s.scoped0[p.r], s.scoped1[p.r], Not(s.scoped2[p.r]), Not(s.scoped3[p.r])), seq,
                 lambda t, p, s0: And(g(t, "released", p.h), g(t, "quorum", p.h) == 2, p.sigok, p.req_ok, p.reason_ok),
                 extra=lambda p: p.q == 2)


def stranger_cannot_make_quorum():
    # quorum 1, only approver 0 is listed; approver 2 (a stranger) tries; the hold cannot be released on that signature
    seq = [create, approve(2), age, release]
    return reach(m, lambda s, p: And(init(s, p), s.scoped0[p.r], Not(s.scoped2[p.r])), seq,
                 lambda t, p, s0: g(t, "released", p.h), extra=lambda p: p.q == 1) is False


def one_signer_below_quorum():
    seq = [create, approve(0), age, release]
    return reach(m, lambda s, p: And(init(s, p), s.scoped0[p.r]), seq,
                 lambda t, p, s0: g(t, "released", p.h), extra=lambda p: p.q == 2) is False


live = [("two scoped approvers sign, the floor passes, the hold is released at quorum 2 (not vacuous)", two_of_three),
        ("a stranger's signature cannot release a quorum-1 hold, there is no such run (disproof search comes back empty)", stranger_cannot_make_quorum),
        ("one signature cannot release a quorum-2 hold, there is no such run (disproof search comes back empty)", one_signer_below_quorum)]


def main() -> int:
    return finish(run(m, init, inv, steps, theorems(), live))


if __name__ == "__main__":
    sys.exit(main())
