"""pytest plugin for H19: run every test with the trace sink on and replay its trace at teardown.

    python3 -m pytest -p h19_plugin tests/test_h00_contract.py        (with tests/ on PYTHONPATH)

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
from proofs.replay import replay  # noqa: E402

RESULTS: dict[str, dict] = {}


@pytest.fixture(autouse=True)
def h19_trace(request):
    with Trace() as tr:
        yield tr
    rep = replay(tr.events)         # raises NoTransition, naming the first event the machines refuse
    RESULTS[request.node.nodeid] = {"events": rep.events, "steps": rep.steps, "arms": rep.arms}


def pytest_sessionfinish(session):
    path = os.environ.get("H19_REPORT")
    if path:
        Path(path).write_text(json.dumps(RESULTS))
