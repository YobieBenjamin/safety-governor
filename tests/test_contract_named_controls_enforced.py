# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""CONTRACT-NAMED-CONTROLS-ENFORCED: the controls the rulebook names are enforced, not just stored.

Four gaps from docs/REVIEW-2026-10-22-fact-check.md section 7, which an external audit on the same
day called out as failures someone could reasonably expect these fields to prevent:
GAP-REVOCATIONS-UNENFORCED revocations were stored and never read; GAP-SANDBOX-FLAG-IGNORED CAP_REQUEST ignored the sandbox flag; GAP-HAZARD-BUDGET-PER-GOVERNOR the session
hazard budget was counted per governor, so a session spread over several chips got several budgets;
GAP-WORKLOAD-TOKEN-SURVIVES-RULE-CHANGE a workload token kept working after the rulebook changed. Falsified if any of these still holds.
"""
from govsim import reasons
from govsim.cluster import build_rack
from govsim.policy import sign_policy

BIG = {"pay_small_limit": 1_000_000}
NO_SAMPLING = {**BIG, "audit": {"sample_rate": 0.0, "escrow_classes": ["hazard"], "store": "audit-store"}}


def _new_edition(rack, **image_changes):
    rack.policy_version += 1
    image = rack.make_policy_image(rack.policy_version, **{**rack.policy_kw})
    image.update(image_changes)
    image = sign_policy(image, rack.governance[: rack.threshold])
    assert rack.change_epoch(image)["committed"]
    for node in rack.nodes:                     # the host presents its manifest again under the new edition (GAP-WORKLOAD-TOKEN-SURVIVES-RULE-CHANGE)
        if node.governor.state == "RUN" and node.governor.model_digest:
            rack.load_model(node)
    return image


# ---------------------------------------------------------------- GAP-REVOCATIONS-UNENFORCED revocations are enforced
def test_a_revoked_observer_key_is_not_a_witness():
    r = build_rack(1, "rack", policy_kw=NO_SAMPLING)
    r.bring_up()
    node = r.nodes[0]
    _new_edition(r, revocations=[r.observer.public.key_id])
    res = r.respond(node, "s", b"fine", observer={"hazard_class": "none"})
    assert not res["released"][0] and node.egress.bytes_delivered == 0


def test_a_revoked_gpu_cannot_attest():
    r = build_rack(1, "rack")
    r.bring_up()
    node = r.nodes[0]
    gpu_id = node.governor.verified["gpu"]["chip_id"]
    _new_edition(r, revocations=[gpu_id])
    out = r.attest(node)
    assert not out["gpu"]["ok"] and out["gpu"]["why"] == reasons.ATTEST_REVOKED


def test_a_revoked_approver_cannot_release_a_hold():
    r = build_rack(1, "rack", policy_kw=BIG)
    r.bring_up()
    node = r.nodes[0]
    g = node.governor
    approvers = r.approvers["payments.transfer.large"]
    _new_edition(r, revocations=[approvers[0].public.key_id])
    held = r.request(node, "payments.transfer", {"amount": 5000, "currency": "USD", "destination": "acct-1"})
    assert held.get("hold_id")
    r.clock.advance(120)
    r.heartbeat()
    r.approve(g, held["hold_id"], held["request_hash"], approvers[0])        # revoked: must not count
    second = r.approve(g, held["hold_id"], held["request_hash"], approvers[1])  # valid, but only one valid approval in all
    assert not second.get("ticket"), second


# ---------------------------------------------------------------- GAP-SANDBOX-FLAG-IGNORED the sandbox closes CAP_REQUEST too
def test_a_sandboxed_governor_grants_no_peer_capability():
    r = build_rack(2, "rack", policy_kw={"sandbox": True, **NO_SAMPLING})
    r.bring_up()
    node, other = r.nodes
    peer = other.governor.verified["gpu"]["chip_id"]
    for point in ("nvswitch", "dpu"):
        res = r.cap_request(node, point=point, peer=peer, direction="both", budget=1000, ttl=60)
        assert not res["ok"] and res["why"] == reasons.EP_SANDBOXED, (point, res)


def test_without_the_sandbox_the_same_request_is_granted():
    r = build_rack(2, "rack", policy_kw=NO_SAMPLING)
    r.bring_up()
    node, other = r.nodes
    peer = other.governor.verified["gpu"]["chip_id"]
    assert r.cap_request(node, point="nvswitch", peer=peer, direction="both", budget=1000, ttl=60)["ok"]


# ---------------------------------------------------------------- GAP-HAZARD-BUDGET-PER-GOVERNOR one hazard budget per session, whichever chip
def test_a_session_spread_over_two_governors_gets_one_hazard_budget():
    r = build_rack(2, "rack", policy_kw={**NO_SAMPLING, "on_hazard": "human", "hazard_budget": {"max": 2, "window_s": 600}})
    r.bring_up()
    a, b = r.nodes
    hz = {"hazard_class": "hazard", "category": "c"}
    first = [r.respond(a, "sess", f"a{i}".encode(), observer=hz)["request"]["cause"] for i in range(2)]
    third = r.respond(b, "sess", b"b0", observer=hz)["request"]["cause"]
    assert first == [reasons.RELEASE_HAZARD, reasons.RELEASE_HAZARD]
    assert third == reasons.SESSION_HAZARD_BUDGET                       # counted across chips: the third hazard in the session


def test_the_hazard_owner_unreachable_fails_closed():
    r = build_rack(2, "rack", policy_kw={**NO_SAMPLING, "on_hazard": "human", "hazard_budget": {"max": 2, "window_s": 600}})
    r.bring_up()
    a, b = r.nodes
    owner = r.policy["budget_owners"]["hazard"]
    far = b if owner == a.governor.chip_id else a
    r.fabric.split({a.governor.chip_id}, {b.governor.chip_id})
    res = r.respond(far, "sess", b"x", observer={"hazard_class": "hazard", "category": "c"})
    assert not res["released"][0]


# ---------------------------------------------------------------- GAP-WORKLOAD-TOKEN-SURVIVES-RULE-CHANGE a token dies with its edition
def test_a_workload_token_from_the_old_edition_is_refused():
    r = build_rack(1, "rack", policy_kw=BIG)
    r.bring_up()
    node = r.nodes[0]
    g = node.governor
    old_token = node.token
    assert r.change_epoch(r.new_policy())["committed"]          # the edition changes; the host does nothing
    body = {"request_id": "after-edition", "measurement_token": old_token, "action": "payments.transfer",
            "params": {"amount": 5, "currency": "USD", "destination": "acct-1"}, "witnesses": []}
    res = g.command("REQUEST", {}, node.host_sign(body, g.epoch, "REQUEST"))
    assert not res["ok"] and res["why"] == reasons.GATE_NOT_ATTESTED
    r.load_model(node)                                                 # the host presents the manifest again under the new rules
    assert r.request(node, "payments.transfer", {"amount": 5, "currency": "USD", "destination": "acct-1"})["ok"]
