# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F31: storage egress needs a per-transfer ticket bound to the bytes, and the ticket is single-use.

Covers VEC-0056. Before the fix the storage exit held a standing entry for the model digest with a budget of
2**40 bytes in both directions, so 140 GB left the rack with no ticket. The fix opens storage for loading only,
and an export needs a single-use grant that the governor issues against a weights.write ticket for those bytes.
These tests fail on the code before the fix and pass after it."""
from govsim import reasons
from govsim.cluster import build_rack


def _running_rack():
    r = build_rack(1, "rack")
    r.bring_up()
    node = r.nodes[0]
    return r, node, node.governor


def test_a_storage_export_without_a_ticket_is_refused():
    r, node, g = _running_rack()
    before = sum(node.gpu.switches["storage"].bytes_passed.values())
    ok, why = node.gpu.transfer("storage", node.model_digest, "out", 140 * 10**9)
    assert not ok
    assert sum(node.gpu.switches["storage"].bytes_passed.values()) == before


def test_no_standing_entry_lets_bytes_leave_storage():
    r, node, g = _running_rack()
    table = node.gpu.switches["storage"].table
    assert not any(direction == "out" for (_peer, direction) in table)


def test_a_ticketed_export_moves_exactly_the_granted_bytes_once():
    r, node, g = _running_rack()
    n = 4096
    params = {"destination": node.model_digest, "model_digest": node.model_digest, "bytes": n}
    res = r.request(node, "weights.write", params)
    assert res["ok"], res
    ticket = res["ticket"]
    ok, why = g.grant_storage_export(ticket, n)
    assert ok, why
    ok, why = node.gpu.transfer("storage", node.model_digest, "out", n)
    assert ok, why
    # the same grant cannot move a second transfer, and the same ticket cannot be granted twice
    again, _ = node.gpu.transfer("storage", node.model_digest, "out", n)
    assert not again
    assert g.grant_storage_export(ticket, n) == (False, reasons.TICKET_REPLAY)


def test_a_grant_for_other_bytes_is_refused():
    r, node, g = _running_rack()
    res = r.request(node, "weights.write", {"destination": node.model_digest, "model_digest": node.model_digest, "bytes": 4096})
    assert res["ok"], res
    assert g.grant_storage_export(res["ticket"], 8192) == (False, reasons.TICKET_PARAMS_MISMATCH)
