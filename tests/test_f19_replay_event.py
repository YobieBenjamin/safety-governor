# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F19: the abstract proof must be able to observe repeated execution (replay).

Audit finding F19. The old model recorded execution in two Booleans, ``used`` and ``executed``,
and INVARIANT-NO-REPLAY-TICKET-SPENT checked ``executed => used``. A second execution of the same ticket only rewrote the same
Booleans, so INVARIANT-NO-REPLAY-TICKET-SPENT stayed true even if the execute step's spent-ticket guard was deleted: the
encoding could not tell a second external effect from a harmless repeat, and the proof did not in
fact forbid replay.

The fix models ticket instances as counts: ``n_issued`` (tickets minted), ``n_spent`` (tickets
consumed) and ``n_events`` (external effects), and proves INVARIANT-NO-REPLAY-COUNTED, that an action never produces more
effects than it was issued tickets (n_events == n_spent <= n_issued). The anti-replay guard in the
execute step is the outstanding-ticket test ``n_issued > n_spent``, exposed as the parameter
``execute_needs_fresh_ticket``.

This test is discriminating. On the pre-fix source it does not even import (no such parameter, no
such counters), so it fails; on the fixed source:

  * the guard-removal mutant makes the concrete trace issue, execute, execute overspend one ticket
    into two effects, falsifying the at-most-once property (detection);
  * the unchanged implementation proves the property, as a theorem of every reachable state and on
    that same concrete trace (no replay);
  * an UNRELATED guard removal (the RUN/halt guard) does NOT by itself make that trace overspend,
    so an unrelated failure is not counted as detecting replay;
  * a legitimate action executed twice under two fresh tickets stays expressible and does not
    violate the property, so counting does not collapse repeats.

Run: ``python3 -m pytest -q tests/test_f19_replay_event.py``.
"""
import importlib.util
import os
import pathlib

import pytest

z3 = pytest.importorskip("z3")

_DEFAULT = pathlib.Path(__file__).resolve().parents[1] / "proofs" / "core_invariants.py"
_PATH = pathlib.Path(os.environ.get("CORE_INVARIANTS_PATH", _DEFAULT))


def _load():
    spec = importlib.util.spec_from_file_location("core_invariants_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CI = _load()


def _replay_trace(fresh_ticket_guard: bool, run_guard: bool = True):
    """The trace issue, execute, execute on one action, over fresh states s -> t -> u -> w.
    Returns (states, formulas, action). With fresh_ticket_guard off, the execute steps drop the
    outstanding-ticket (anti-replay) guard; with run_guard off, they drop the RUN/halt guard."""
    s, t, u, w = CI.State("s"), CI.State("t"), CI.State("u"), CI.State("w")
    i = CI.make_inputs()
    a = i["a"]
    issue = dict(CI.step_list(s, t, i))["issue"]
    ex1 = dict(CI.step_list(t, u, i, execute_needs_fresh_ticket=fresh_ticket_guard, execute_needs_run=run_guard))["execute"]
    ex2 = dict(CI.step_list(u, w, i, execute_needs_fresh_ticket=fresh_ticket_guard, execute_needs_run=run_guard))["execute"]
    return (s, t, u, w), [CI.invariant_at(s, a), issue, ex1, ex2], a


def _solve(assumptions):
    sol = z3.Solver()
    sol.set("timeout", 60_000)
    sol.add(*assumptions)
    return sol.check()


def test_mutant_replays_one_ticket_into_two_effects():
    """Guard removed: issue, execute, execute overspends one issued ticket, so n_spent > n_issued
    and n_events > n_issued become reachable. The at-most-once property is falsified."""
    (s, t, u, w), trace, a = _replay_trace(fresh_ticket_guard=False)
    overspent = z3.Or(w.n_spent[a] > w.n_issued[a], w.n_events[a] > w.n_issued[a])
    assert _solve(trace + [overspent]) == z3.sat
    # and the two effects came from a single issued ticket, which is exactly replay
    assert _solve(trace + [w.n_issued[a] == 1, w.n_events[a] == 2]) == z3.sat


def test_unchanged_implementation_proves_at_most_once_on_the_trace():
    """Guard present: the same trace cannot overspend. Replay is blocked, not merely flagged."""
    (s, t, u, w), trace, a = _replay_trace(fresh_ticket_guard=True)
    overspent = z3.Or(w.n_spent[a] > w.n_issued[a], w.n_events[a] > w.n_issued[a])
    assert _solve(trace + [overspent]) == z3.unsat


def test_unchanged_implementation_proves_at_most_once_as_a_theorem():
    """The property is inductive, not an accident of one trace: from any invariant state, an honest
    execute step cannot take n_events above n_issued."""
    s, t = CI.State("s"), CI.State("t")
    i = CI.make_inputs()
    a = i["a"]
    execute = dict(CI.step_list(s, t, i))["execute"]
    hyp = [CI.invariant_at(s, a)]
    at_most_once_after = z3.And(t.n_events[a] <= t.n_issued[a], t.n_spent[a] <= t.n_issued[a])
    assert _solve(hyp + [execute, z3.Not(at_most_once_after)]) == z3.unsat


def test_unrelated_guard_removal_is_not_counted_as_replay_detection():
    """Removing an UNRELATED guard (the RUN/halt guard) while keeping the anti-replay guard does
    NOT make the trace overspend: the second execute is still blocked by the outstanding-ticket
    test. So an unrelated mutation is not mistaken for detecting replay."""
    (s, t, u, w), trace, a = _replay_trace(fresh_ticket_guard=True, run_guard=False)
    overspent = z3.Or(w.n_spent[a] > w.n_issued[a], w.n_events[a] > w.n_issued[a])
    assert _solve(trace + [overspent]) == z3.unsat


def test_repeated_legitimate_actions_stay_expressible():
    """Two fresh tickets, two executions, of the same logical action: expressible and not a
    violation. Counting ticket instances does not collapse repeated executions into one bit."""
    s, t, u, w, x = (CI.State(n) for n in ("s", "t", "u", "w", "x"))
    i = CI.make_inputs()
    a = i["a"]
    issue_a = dict(CI.step_list(s, t, i))["issue"]
    exec_a = dict(CI.step_list(t, u, i))["execute"]
    issue_b = dict(CI.step_list(u, w, i))["issue"]
    exec_b = dict(CI.step_list(w, x, i))["execute"]
    assumptions = [CI.init(s), issue_a, exec_a, issue_b, exec_b,
                   x.n_events[a] == 2, x.n_events[a] <= x.n_issued[a]]
    assert _solve(assumptions) == z3.sat


def test_old_boolean_only_property_could_not_see_replay():
    """The crux of F19, stated as a test: under the guard-removal mutant, the OLD Boolean property
    executed[a] => used[a] still holds across the replay trace, even though a second effect
    occurred. A Boolean cannot witness replay; only the count can."""
    (s, t, u, w), trace, a = _replay_trace(fresh_ticket_guard=False)
    old_p3_after = z3.Implies(w.executed[a], w.used[a])
    # the old property is never violated by the replay trace (it is blind to the second effect)
    assert _solve(trace + [z3.Not(old_p3_after)]) == z3.unsat
    # yet on the very same trace the counted property IS violated
    assert _solve(trace + [w.n_events[a] > w.n_issued[a]]) == z3.sat
