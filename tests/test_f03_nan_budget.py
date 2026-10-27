# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F03: a non-finite amount (NaN or infinity) must never poison a budget.

Audit finding F03. NaN < min, NaN > max, NaN < 0 and total + NaN > limit are all False, so an
un-guarded ledger reserves NaN, its aggregate becomes NaN, and every later `aggregate > limit`
check stays False: the budget stops rejecting overspend. The fix rejects bool, NaN and infinity in
three places (canonical serialization, the typed constraint check, and the ledger), so a malformed
amount is refused before any reservation and the aggregate stays finite.

Falsified if a non-finite amount can be signed, can satisfy a numeric rule, can be reserved, or can
leave a budget unable to refuse a later legitimate overspend.
"""
import math

import pytest

from conftest import pay
from govsim.crypto import canonical, finite_number
from govsim.policy import check_constraints

NONFINITE = [float("nan"), float("inf"), float("-inf")]


def test_canonical_refuses_to_serialize_or_sign_nonfinite():
    for v in NONFINITE:
        with pytest.raises(ValueError):
            canonical({"amount": v})
    assert canonical({"amount": 1000}) == b'{"amount":1000}'


def test_finite_number_rejects_nan_inf_and_bool():
    assert finite_number(0) and finite_number(1000) and finite_number(12.5)
    for v in NONFINITE + [True, False, "1000", None]:
        assert not finite_number(v)


def test_numeric_constraint_rejects_nonfinite():
    rule = {"constraints": {"amount": {"min": 0, "max": 1000}}}
    for v in NONFINITE:
        ok, why = check_constraints(rule, {"amount": v}, {})
        assert not ok and why.endswith("not_a_finite_number")
    assert check_constraints(rule, {"amount": 500}, {})[0]


def test_ledger_reserve_refuses_nonfinite_and_keeps_aggregate_finite(rack):
    owner = rack.nodes[0].governor
    for v in NONFINITE:
        assert owner.ledger.reserve("pay-usd-hourly", v, 2000, 3600, rack.clock.now(), 60) is None
    committed, reserved = owner.ledger.usage("pay-usd-hourly", 3600, rack.clock.now())
    assert math.isfinite(committed) and math.isfinite(reserved)
    assert committed == 0 and reserved == 0


def test_nan_payment_never_tickets_and_budget_still_bites(rack):
    node = rack.nodes[0]
    # A NaN small payment must not produce a ticket: refused at signing (ValueError) or denied by the gate.
    try:
        res = pay(rack, node, float("nan"))
        assert not res["ok"]
    except ValueError:
        pass
    # The 2000/hour budget is intact: two 1000 wires fit, the third is refused.
    assert pay(rack, node, 1000)["ok"]
    assert pay(rack, node, 1000)["ok"]
    assert not pay(rack, node, 1000)["ok"]
