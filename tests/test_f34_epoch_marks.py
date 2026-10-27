# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F34: each durable image holds two copies of a monotonic epoch mark, and a restart refuses when they disagree.

Covers VEC-0083. The fix catches a partial or torn write to one copy. It does not catch a consistent rollback of
the whole image: a rolled-back image is internally consistent. The last test documents that open part. Closing
it needs an external anchor (a hardware fuse or an outside counter), which software alone cannot provide.
The first two tests fail on the code before the fix and pass after it."""
import pickle

import pytest

from govsim import store as store_mod
from govsim.cluster import build_rack

MarksDisagree = getattr(store_mod, "MarksDisagree", RuntimeError)   # absent before the fix: the test then fails on behaviour


def _tamper_one_copy(store, value):
    data = pickle.loads(store._nvm)
    data["epoch_mark_b"] = value                     # only one of the two copies is changed
    store._nvm = store_mod._snapshot(data)


def test_a_governor_with_disagreeing_marks_refuses_to_start():
    r = build_rack(1, "rack")
    r.bring_up()
    g = r.nodes[0].governor
    _tamper_one_copy(g.store, 41)
    with pytest.raises(MarksDisagree):
        g.restart()


def test_an_endpoint_with_disagreeing_marks_refuses_to_start():
    r = build_rack(1, "rack")
    r.bring_up()
    ep = r.endpoints["strike-guidance"]
    _tamper_one_copy(ep.store, 41)
    with pytest.raises(MarksDisagree):
        ep.restart()


def test_a_consistent_rollback_of_both_images_is_not_detected_documented_open():
    # Documented open part of F34. Roll both durable images back together to an earlier consistent snapshot.
    r = build_rack(1, "rack")
    r.bring_up()
    node = r.nodes[0]
    g, ep = node.governor, r.endpoints["strike-guidance"]
    snap_g, snap_e = g.store._nvm, ep.store._nvm
    r.clock.advance(5.0)
    r.heartbeat()
    g.restart()
    ep.restart()
    g.store._nvm, ep.store._nvm = snap_g, snap_e      # the labelled rollback: both images, consistent
    g.restart()                                       # starts: nothing outside the images says the state is old
    ep.restart()
