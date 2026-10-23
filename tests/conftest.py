# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
import pytest

from govsim.cluster import build_rack


@pytest.fixture
def rack():
    """A four-GPU rack at the plan-of-record tier, brought up and running."""
    r = build_rack(4, "rack")
    r.bring_up()
    return r


@pytest.fixture
def rack1():
    """A one-GPU rack, for restart and endpoint tests."""
    r = build_rack(1, "rack")
    r.bring_up()
    return r


@pytest.fixture(params=["rack", "board", "integrated"])
def tiered_rack(request):
    r = build_rack(4, request.param)
    r.bring_up()
    r.tier_name = request.param
    return r


def pay(rack, node, amount, governor=None):
    return rack.request(node, "payments.transfer", {"amount": amount, "currency": "USD", "destination": "acct-1"}, governor=governor)


def strike(rack, node, target, risk=0.1, governor=None):
    return rack.request_with_witness(node, "strike", {"target": target, "munition": "gbu-39"}, risk=risk, governor=governor)
