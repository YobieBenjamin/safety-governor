# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F32: the egress re-hashes the held bytes at release and refuses on a mismatch.

Covers VEC-0062. Before the fix the egress released on the committed hash without re-hashing the bytes it
delivered, so bytes written into the DPU's held buffer after commit left the rack. The write itself is a
labelled power (a DPU buffer write is beyond host and BMC); this fix only makes the release check the bytes.
These tests fail on the code before the fix and pass after it."""
from govsim import reasons
from govsim.cluster import build_rack


def _held_response():
    r = build_rack(1, "rack")
    r.bring_up()
    node = r.nodes[0]
    pres = r.present(node, "s", "rW", b"committed-bytes")
    h = pres["response_hash"]
    req = r.request_release(node, "s", "rW", h, pres["stream_hashes"], [r.verdict(h, hazard_class="none", risk=0.1)])
    assert req.get("ok"), req
    return node, req["ticket"]


def test_a_release_of_substituted_bytes_is_refused():
    node, ticket = _held_response()
    node.egress.held[("s", "rW")]["bytes"] = b"substituted-bytes"
    ok, why = node.egress.release(ticket)
    assert not ok and why == reasons.RELEASE_HASH_MISMATCH
    assert node.egress.delivered.get("s", []) == []
    assert ("s", "rW") in node.egress.held                # the held item is not dropped by a refused release


def test_an_unmodified_release_still_delivers_the_committed_bytes():
    node, ticket = _held_response()
    ok, why = node.egress.release(ticket)
    assert ok, why
    assert node.egress.delivered["s"] == [b"committed-bytes"]
