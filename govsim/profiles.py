# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Named rulebook profiles: the same rules with different values, so a review can ask whether a result depends on
the numbers the authors happened to choose (Yobie Benjamin, 30 October 2026: "3 audits, one with the same variables
then 2 with different values to see if the configs hold").

Each profile is a set of keyword arguments for ``Rack.make_policy_image`` (``build_rack(n, policy_kw=PROFILES[name])``).
``default`` is the reference rulebook the tests and the red team run on. ``tight`` lowers every cap, ceiling and
window a bank would want low. ``large`` raises them to where a big deployment would run. Every profile must pass
``policy.shape_problems`` with no findings, which ``tests/test_profiles.py`` checks."""
from __future__ import annotations

PROFILES: dict[str, dict] = {
    "default": {},
    "tight": {
        "pay_small_limit": 500.0,                       # the hourly fleet cap for small payments
        "release_max_risk": 0.3,                        # the risk ceiling an observer's verdict must meet for a release
        "strike_max_risk": 0.2,
        "strike_rate": {"max": 2, "window_s": 3600.0},
        "message_rate": {"max": 5, "window_s": 60.0},
        "message_max_bytes": 512,
        "output_queries": 20,
        "output_bytes": 50_000,
        "expires_in_s": 7 * 86400,                      # a one-week edition
        "key_lease_s": 30.0,
    },
    "large": {
        "pay_small_limit": 20_000.0,
        "release_max_risk": 0.7,
        "strike_max_risk": 0.5,
        "strike_rate": {"max": 100, "window_s": 3600.0},
        "message_rate": {"max": 600, "window_s": 60.0},
        "message_max_bytes": 65_536,
        "output_queries": 500,
        "output_bytes": 20_000_000,
        "expires_in_s": 90 * 86400,
        "key_lease_s": 600.0,
    },
}
