# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Every named rulebook profile builds, passes the shape check, and bounds the extracted key the same way: the cap,
the rate and the mode are enforced at the device under each set of values, not only under the defaults."""
import pytest

from govsim import reasons
from govsim.cluster import LISTED_RECIPIENTS, build_rack
from govsim.crypto import digest, random_id
from govsim.policy import shape_problems
from govsim.profiles import PROFILES

PAY = "payments.transfer"
KEY = "pay-usd-hourly"


def forged(rack, params, changes, rule, action=PAY, endpoint="payment-switch"):
    g, now = rack.nodes[0].governor, rack.clock.now()
    rid = random_id(8)
    t = {"type": "ticket", "ticket_id": random_id(16), "request_id": rid, "request_hash": digest([rid, g.fingerprint, action, params]),
         "action": action, "params_digest": digest(params), "measurement": g.fingerprint, "rule": rule, "policy_epoch": g.epoch,
         "endpoint": endpoint, "budget_key": None, "reservation": None, "budget_owner": None, "governor": g.chip_id,
         "issued_at": g.mono(), "valid_from": now, "expires_at": now + 300, **changes}
    return g.key.sign(t)


def forging_host(rack):
    g = rack.nodes[0].governor
    for ep in rack.endpoints.values():
        real = ep.commit
        def commit(ticket, real=real):
            out = real(ticket)
            if isinstance(out, dict):
                return out
            t = ticket["payload"]
            return g.key.sign({"type": "commit", "ticket_id": t["ticket_id"], "request_hash": t["request_hash"], "endpoint": t["endpoint"],
                               "governor": g.chip_id, "budget_key": t.get("budget_key"), "reservation": t.get("reservation"),
                               "fleet_receipts": [], "at": rack.clock.now()})
        ep.commit = commit


@pytest.mark.parametrize("name", sorted(PROFILES))
def test_every_profile_builds_and_has_a_sound_shape(name):
    rack = build_rack(1, policy_kw=PROFILES[name])
    rack.bring_up()
    assert shape_problems(rack.policy) == []
    r = rack.request(rack.nodes[0], PAY, {"amount": 1, "currency": "USD", "destination": "acct-1"})
    assert r["ok"], r


@pytest.mark.parametrize("name", sorted(PROFILES))
def test_the_extracted_key_is_bounded_by_the_profiles_own_cap_and_rate(name):
    rack = build_rack(1, policy_kw=PROFILES[name])
    rack.bring_up()
    forging_host(rack)
    cap = PROFILES[name].get("pay_small_limit", 2000.0)
    small = next(r for r in rack.policy["rules"] if r["id"] == "payments.transfer.small")
    per_ticket = float(small["constraints"]["amount"]["max"])
    ep = rack.endpoints["payment-switch"]
    moved = 0.0
    for _ in range(200):
        amount = min(per_ticket, cap)
        params = {"amount": amount, "currency": "USD", "destination": "acct-x"}
        t = forged(rack, params, {"budget_key": KEY, "reservation": "forged-" + random_id(4), "budget_owner": "gov00"}, "payments.transfer.small")
        ok, _ = ep.execute(t, PAY, params)
        moved += amount if ok else 0
    assert moved <= cap, (name, moved, cap)
    msg = rack.endpoints["messaging"]
    rate = next(r for r in rack.policy["rules"] if r["id"] == "message.send.listed")["rate"]
    sent = 0
    for i in range(int(rate["max"]) * 3):
        p = {"recipient": LISTED_RECIPIENTS[0], "body": "x"}
        t = forged(rack, p, {}, "message.send.listed", action="message.send", endpoint="messaging")
        sent += msg.execute(t, "message.send", p)[0]
    assert sent <= rate["max"], (name, sent, rate)
