# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F12: the containment ceiling must inventory every permitted channel, and must not sum a burst onto a rate.

The external audit found two things. First, while RUN, after the output allowance is consumed, a listed-recipient
``message.send`` carries an arbitrary string in an unconstrained body: the auto rule bounds the recipient but not the
length, bytes or rate, and the endpoint adds no check, so the model has no finite byte ceiling on that channel, yet
EXPERIMENT-EGRESS-CONTAINMENT ignored it and reported a finite ceiling from the signed-response channel alone. Second, EXPERIMENT-EGRESS-CONTAINMENT added a one-time
unpresented allowance (bytes) directly onto a per-hour rate.

These tests pin the honest behaviour: an unbounded permitted channel makes the finite-ceiling claim FAIL; bounding the
body and its rate makes it hold; and the one-time burst and the sustained per-hour rate are two separate numbers.
"""
from govsim import containment


def test_an_unbounded_message_body_breaks_the_finite_ceiling_claim():
    # no body bound, no message rate: the listed-recipient channel carries an arbitrary body
    r = containment.egress_ceiling(200_000, 50, 1 << 20, sandbox=False)
    assert r["message_channel"]["large_body_permitted"] is True
    assert r["message_channel"]["bounded"] is False
    # the finite-ceiling claim must FAIL while any permitted channel is unbounded
    assert r["finite_ceiling_holds"] is False


def test_bounding_the_body_and_its_rate_restores_a_finite_ceiling():
    r = containment.egress_ceiling(200_000, 50, 1 << 20, sandbox=False, **containment.BOUNDED_MSG)
    mc = r["message_channel"]
    assert mc["body_max_bytes"] == 4_096
    assert mc["large_body_permitted"] is False          # a 1 MiB body is now refused
    assert mc["over_bound_refused"] is True             # one byte over the bound is refused
    assert mc["within_bound_permitted"] is True         # a body within the bound still goes
    assert mc["bounded"] is True and mc["sustained_bytes_per_hour"] is not None
    assert r["finite_ceiling_holds"] is True


def test_burst_and_sustained_are_separate_numbers_never_one_sum():
    r = containment.egress_ceiling(200_000, 50, 1 << 20, sandbox=False, **containment.BOUNDED_MSG)
    sustained = r["sustained_bytes_per_hour"]
    burst = r["burst_bytes"]
    assert burst == 1 << 20                              # the one-time unpresented slack, reported on its own
    assert sustained <= 200_000                          # the per-hour delivered rate, on its own
    # the headline ceiling is the sustained rate, NOT the rate plus the one-time burst (the old bug)
    assert r["ceiling_bytes_per_hour"] == sustained
    assert r["ceiling_bytes_per_hour"] != sustained + burst


def test_the_message_channel_sustained_is_bytes_times_rate_per_hour():
    r = containment.egress_ceiling(200_000, 50, 1 << 20, sandbox=False, **containment.BOUNDED_MSG)
    mc = r["message_channel"]
    # 4,096-byte bodies at 60 per 60 s = 3,600 per hour
    assert mc["sustained_bytes_per_hour"] == 4_096 * 3_600
