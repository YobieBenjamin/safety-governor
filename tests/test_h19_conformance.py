"""H19: trace conformance. Every govsim trace is replayed through the abstract machines of the proofs.
Falsified if the simulation takes a step the theorem's machine does not have (a model bug or a gap in the theorem).

The detailed tests of H0 to H18 are run again with the trace sink on (tests/h19_plugin.py) and each
test's trace is replayed at teardown: the first event the machines have no transition for fails that test.
One of those tests, ``test_governor_cannot_clear_itself``, injects a firmware fault on purpose; its trace is
refused by the machines by design, and the plugin asserts the refusal names the event. So the trace set is
replayed clean for every test except that one injected fault.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from govsim import reasons
from govsim.cluster import build_rack
from govsim.governor import Governor
from govsim.trace import Trace
from proofs.replay import NoTransition, replay, step_names

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
sys.path.insert(0, str(TESTS))
from h19_plugin import FAULT_INJECTION  # noqa: E402   the injected faults, by test name

PAY = {"amount": 100, "currency": "USD", "destination": "acct-1"}


def test_every_hypothesis_test_trace_replays(tmp_path):
    files = sorted(str(p) for p in TESTS.glob("test_h*.py") if p.name != "test_h19_conformance.py")
    report = tmp_path / "report.json"
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(TESTS), str(ROOT)]), H19_REPORT=str(report))
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "h19_plugin", "-p", "no:cacheprovider", *files],
                          cwd=ROOT, env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-6000:] + proc.stderr[-2000:]
    results = json.loads(report.read_text())
    assert len(results) >= 200, f"only {len(results)} tests were traced"
    steps = {}
    for r in results.values():
        for k, v in r["steps"].items():
            steps[k] = steps.get(k, 0) + v
    for needed in ("issue", "execute", "forged execute (refused)", "new edition", "halt", "clear"):
        assert steps.get(needed), f"no trace exercised the machine step '{needed}': {steps}"
    # every trace replays clean except the injected fault(s); the faulted names are exactly FAULT_INJECTION,
    # and each fault's refusal was asserted at teardown (it names the step and its reason). A test that never
    # drives a governor produces no events and so vacuously conforms; the step checks above are what keep the
    # aggregate non-vacuous.
    faulted = {k.rsplit("::", 1)[-1] for k, r in results.items() if r.get("fault_detected")}
    assert faulted == set(FAULT_INJECTION), f"faulted {sorted(faulted)}; expected the injected {sorted(FAULT_INJECTION)}"
    for k, r in results.items():
        if r.get("fault_detected"):
            txt = r["fault_detected"]
            step, why = FAULT_INJECTION[k.rsplit("::", 1)[-1]]
            assert step in txt and why in txt, f"the faulted trace's refusal did not name its event: {txt}"


def test_step_names_match_the_proof_files():
    names = step_names()
    assert {"issue", "execute", "forged execute (refused)", "new edition", "halt", "clear", "heartbeat lost", "heartbeat back"} <= set(names["core"])
    assert {"hold", "reviewer clears", "commit"} <= set(names["commit_point"])


def _pay(rack):
    return rack.request(rack.nodes[0], "payments.transfer", PAY)


def test_a_sound_governor_replays():
    with Trace() as tr:
        rack = build_rack(4, "rack")
        rack.bring_up()
        t = _pay(rack)["ticket"]
        ok, _ = rack.endpoints["payment-switch"].execute(t, "payments.transfer", PAY)
        assert ok
    rep = replay(tr.events)
    assert rep.steps["issue"] == 1 and rep.steps["execute"] == 1


def test_a_governor_that_issues_while_halted_fails_replay_naming_the_event(monkeypatch):
    """The broken governor: the mailbox's 'must be RUN' check is commented out, so a halted governor still signs tickets."""
    orig = Governor.command

    def broken_command(self, cmd, body=None, env=None):
        saved, self.state = self.state, "RUN"       # the check `self.state != RUN` can no longer refuse
        try:
            return orig(self, cmd, body, env)
        finally:
            self.state = saved
    with Trace() as tr:
        rack = build_rack(4, "rack")
        rack.bring_up()
        rack.halt(rack.nodes[0].governor)
        monkeypatch.setattr(Governor, "command", broken_command)
        r = _pay(rack)
        assert r.get("ok"), "the broken governor should have signed a ticket"
    with pytest.raises(NoTransition) as exc:
        replay(tr.events)
    assert "ticket_issued" in str(exc.value) and "halted" in str(exc.value)


def test_an_endpoint_that_ignores_the_edition_fails_replay_naming_the_event(monkeypatch):
    """The broken endpoint and governor: the stale-edition checks are removed, so a ticket from the old edition executes."""
    with Trace() as tr:
        rack = build_rack(4, "rack")
        rack.bring_up()
        t = _pay(rack)["ticket"]
        rack.change_epoch(rack.new_policy())
        ep = rack.endpoints["payment-switch"]
        ep.epoch = t["payload"]["policy_epoch"]                       # the endpoint check `policy_epoch != self.epoch` is gone
        monkeypatch.setattr(Governor, "commit_from_endpoint", lambda self, ticket: True)   # and so is the governor's
        ep.heartbeat(rack.clock.now())
        ok, _ = ep.execute(t, "payments.transfer", PAY)
        assert ok, "the broken endpoint should have carried the stale ticket out"
    with pytest.raises(NoTransition) as exc:
        replay(tr.events)
    assert "execute_ok" in str(exc.value)


def test_the_first_run_after_a_boot_is_a_named_gap_not_a_transition():
    """Gap in the theorem: the initial state leaves ``halted`` free and there is no boot/arm step, so a
    governor's first RUN after a boot is not a transition the machine has. The replayer names it ``arm``
    (Report.arms) and accepts it only from a halt a boot put there -- so the gap is a documented count, not a
    step the machine silently allows."""
    with Trace() as tr:
        rack = build_rack(4, "rack")
        rack.bring_up()
        t = _pay(rack)["ticket"]
        rack.endpoints["payment-switch"].execute(t, "payments.transfer", PAY)
    rep = replay(tr.events)
    assert rep.arms >= 1                                     # each governor's boot-to-RUN; the machine has no step for it
    assert "arm" not in rep.steps                             # it is a named gap, not a machine step the machines accept
    assert rep.steps.get("issue") and rep.steps.get("execute")   # and the rack did real work, so the arms are not vacuous


def test_a_burn_without_execute_is_a_stutter_the_machine_has_no_step_for(monkeypatch):
    """Gap in the theorem: the endpoint burns the ticket before the commit and the device checks and may then
    refuse. The core machine has no ``used``-without-``executed`` step, so the replayer absorbs the refusal as a
    stutter and tracks the burn in Report.burned. This test isolates the burn (a burned, un-executed ticket that
    the machine accepts) so the gap rests on a trace, not on the replayer's bookkeeping alone."""
    with Trace() as tr:
        rack = build_rack(4, "rack")
        rack.bring_up()
        t = _pay(rack)["ticket"]
        rack.halt(rack.nodes[0].governor)                   # the committing governor is halted: the commit will fail
        ep = rack.endpoints["payment-switch"]
        ok, why = ep.execute(t, "payments.transfer", PAY)
        assert not ok and why in (reasons.COMMIT_REJECTED, reasons.COMMIT_UNREACHABLE)
        assert t["payload"]["ticket_id"] in ep.consumed and not ep.executed    # the ticket was burned, nothing carried out
    rep = replay(tr.events)                                 # accepted: the machine has no burn step, so it is a stutter
    assert rep.burned >= 1
    assert "forged execute (refused)" in rep.steps
