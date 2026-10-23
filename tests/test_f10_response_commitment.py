# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F10: one unsampled response id must not suppress every later random audit draw.

The external audit found that a response id that released without an escrow receipt could be
reused: presenting different bytes under the same id overwrote the committed stream hashes while
preserving the previous ``sampled=False`` draw, so the new content left the rack with no receipt
and no fresh draw. The attacker never predicts the TRNG; it reuses one successful unsampled
identity. The fix makes each response commitment immutable and scoped to the workload instance,
epoch, session and response id: a different hash under an existing identity is refused, a genuine
retry keeps its commitment's draw, and genuinely new content needs a new identity and its own draw.
"""
from govsim import reasons
from govsim.cluster import build_rack

BIG = {"output_queries": 10 ** 6, "output_bytes": 10 ** 12}


def seeded(draws, sample_rate=0.5):
    """A rack whose audit draw comes from a deterministic sequence. ``draws`` are the TRNG fractions
    handed out, one per genuinely new response stream; values >= ``sample_rate`` are unsampled."""
    r = build_rack(1, "rack", rng_seed=7,
                   policy_kw={**BIG, "audit": {"sample_rate": sample_rate, "escrow_classes": [], "store": "audit-store"}})
    r.bring_up()
    node = r.nodes[0]
    seq = list(draws)

    def fraction():
        return seq.pop(0) if seq else 0.99        # exhausted draws fall back to unsampled, never sampled by accident

    node.governor.root.random_fraction = fraction
    return r, node


def test_unsampled_id_cannot_be_reused_to_smuggle_new_bytes_past_the_audit_draw():
    # First draw is unsampled, so the first response releases with no receipt. The reuse attack then
    # presents different bytes under the same id, hoping to inherit that unsampled draw.
    r, node = seeded([0.9])
    g = node.governor
    first = r.respond(node, "s", b"the first response", observer={"hazard_class": "none"}, response_id="X")
    assert first["released"][0] and node.egress.bytes_delivered == len(b"the first response")
    committed = g.responses["X"]["streams"]["response"]
    assert committed == first["response_hash"] and g.responses["X"].get("released") is True
    assert g.responses["X"]["sampled"] is False

    reuse = r.respond(node, "s", b"a different response under the same id", observer={"hazard_class": "none"}, response_id="X")
    # The commitment is immutable: the swap is refused, the committed hash and draw are untouched, and
    # the smuggled bytes never leave the rack.
    assert not reuse["released"][0]
    assert reuse["request"]["why"] == reasons.RELEASE_HASH_MISMATCH
    assert g.responses["X"]["streams"]["response"] == committed       # not overwritten by the new bytes
    assert g.responses["X"]["sampled"] is False                       # the one draw was not re-run or erased
    assert node.egress.bytes_delivered == len(b"the first response")  # only the original content left
    assert g.log.has("output.commitment_conflict", response_id="X", stream="response")


def test_a_sampled_result_cannot_be_erased_by_reusing_the_id_and_a_genuine_retry_still_releases():
    # This draw is sampled, so the response is held for a receipt. The attacker reuses the id with new
    # bytes and a matching receipt, hoping to swap in content the auditor never escrowed.
    r, node = seeded([0.1])
    g = node.governor
    held = r.respond(node, "s", b"a watched response", observer={"hazard_class": "none"}, response_id="Y")
    assert not held["released"][0] and held["request"]["why"] == reasons.RELEASE_ESCROW_REQUIRED
    committed = g.responses["Y"]["streams"]["response"]
    assert g.responses["Y"]["sampled"] is True

    swap = r.respond(node, "s", b"unwatched content", observer={"hazard_class": "none"}, response_id="Y", escrow=True)
    assert not swap["released"][0]
    assert swap["request"]["why"] == reasons.RELEASE_HASH_MISMATCH
    assert g.responses["Y"]["streams"]["response"] == committed       # the committed hash is unchanged
    assert g.responses["Y"]["sampled"] is True                        # the sampled result was not erased
    assert node.egress.bytes_delivered == 0                           # nothing left on the swapped bytes

    # A legitimate retry re-presents the identical, escrowed content and releases: idempotent, same draw.
    retry = r.respond(node, "s", b"a watched response", observer={"hazard_class": "none"}, response_id="Y", escrow=True)
    assert retry["released"][0]
    assert g.responses["Y"]["streams"]["response"] == committed and g.responses["Y"]["sampled"] is True
    assert node.egress.bytes_delivered == len(b"a watched response")
