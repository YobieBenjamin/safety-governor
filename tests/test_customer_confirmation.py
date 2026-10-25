# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""EXPERIMENT-CUSTOMER-CONFIRMATION (govsim/customer_confirm.py): a payment rule whose witness must be the payer's own key, bound to the request.
Opt-in; the reference rulebook is unchanged (the control check proves it)."""
from govsim import customer_confirm


def test_every_customer_confirm_check_holds():
    failed = [(n, d) for n, ok, d in customer_confirm.checks() if not ok]
    assert not failed, failed
