"""pytest plugin for H19: run every test with the trace sink on and replay its trace at teardown.

    python3 -m pytest -p h19_plugin tests/test_contract_fresh_authorization_per_operation.py        (with tests/ on PYTHONPATH)

A trace the machines refuse turns the test's teardown into an error that names the event. When
H19_REPORT is set, the per-test counts are written there as JSON.
"""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from govsim.trace import Trace  # noqa: E402
from proofs.replay import NoTransition, replay  # noqa: E402

RESULTS: dict[str, dict] = {}

# Tests that inject a fault into the governor on purpose (firmware that forgets its cause). The fault is a step the
# machine does not have, so the replay MUST refuse it; the test passes replay only if the machines name that event.
FAULT_INJECTION = {
    "test_governor_cannot_clear_itself": ("run_entered", "RUN entered with no clear"),
}


@pytest.fixture(autouse=True)
def h19_trace(request):
    with Trace() as tr:
        yield tr
    fault = FAULT_INJECTION.get(request.node.name)
    if fault is not None:
        with pytest.raises(NoTransition) as exc:
            replay(tr.events)
        assert fault[0] in str(exc.value) and fault[1] in str(exc.value), str(exc.value)
        RESULTS[request.node.nodeid] = {"events": len(tr.events), "steps": {}, "arms": 0, "fault_detected": str(exc.value)}
        return
    rep = replay(tr.events)         # raises NoTransition, naming the first event the machines refuse
    RESULTS[request.node.nodeid] = {"events": rep.events, "steps": rep.steps, "arms": rep.arms}


def pytest_sessionfinish(session):
    path = os.environ.get("H19_REPORT")
    if path:
        Path(path).write_text(json.dumps(RESULTS))
