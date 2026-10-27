# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Regression tests for the adversarial feature and function audit of 26 October 2026 (audit 2, team A).

Each test is an attack the audit wrote against this model. Every one completed a bad action (or showed a single point of
failure) on the code the audit read; each now fails to. The audit's report and problem catalog are in the project's
design notes and on the drive (work/audits/adversarial-function/audit-2-team-a/). Where the audit's own test conflated
two properties (one authority key versus one quorum; one silent heartbeat signer versus every signer silent; five
unrelated racks versus one fleet), the test here states the property precisely and says why."""
import copy

import pytest

from govsim import reasons
from govsim.cluster import build_rack, MODEL_70B
from govsim.crypto import digest, random_id
from govsim.policy import policy_epoch, sign_policy

MB = 1 << 20


def _rack(n=4):
    r = build_rack(n, "rack")
    r.bring_up()
    return r


def _resign(r, image, version_bump=True):
    """A governance-signed successor of ``image`` (the quorum signs whatever the test builds)."""
    image = copy.deepcopy(image)
    image.pop("signatures", None)
    if version_bump:
        r.policy_version += 1
        image["version"] = r.policy_version
    return sign_policy(image, r.governance[: r.threshold])


def _large_hold(r, node):
    res = r.request(node, "payments.transfer", {"amount": 25_000, "currency": "USD", "destination": "acct-9"})
    assert res["why"] == reasons.GATE_HELD, res
    return res["hold_id"], res["request_hash"]



def _forged_ticket(r, g, action, params, endpoint, epoch):
    t = {"type": "ticket", "ticket_id": random_id(16), "request_hash": digest(["x"]), "action": action,
         "params_digest": digest(params), "measurement": "anything", "rule": "no-such-rule", "policy_epoch": epoch,
         "endpoint": endpoint, "budget_key": None, "reservation": None, "budget_owner": None, "governor": g.chip_id,
         "issued_at": 0, "valid_from": r.clock.now(), "expires_at": r.clock.now() + 300}
    return g.key.sign(t)   # a governor key in the attacker's hands (lying firmware, extracted key, counterfeit)


def test_approve_does_not_mint_a_ticket_while_halted():
    r = _rack(1)
    node = r.nodes[0]
    g = node.governor
    hid, rh = _large_hold(r, node)
    assert r.halt(g)["ok"]
    assert g.state == "HALT"
    r.clock.advance(120)
    a = r.approvers["payments.transfer.large"]
    r.approve(g, hid, rh, a[0])
    res = r.approve(g, hid, rh, a[1])
    assert not res.get("ok") and "ticket" not in res, "a ticket was minted while the governor was in HALT"


def test_approve_does_not_mint_while_a_blocking_alarm_is_set():
    """A blocking alarm stops every new request (GATE_ALARM). A hold parked before the alarm should not be
    released into an action while the alarm stands."""
    r = _rack(1)
    node = r.nodes[0]
    g = node.governor
    hid, rh = _large_hold(r, node)
    g.raise_alarm(reasons.LOOP_JUMPERED, "governor", {"member": "x"})          # any blocking alarm
    assert r.request(node, "payments.transfer", {"amount": 10, "currency": "USD", "destination": "acct-1"})["why"] == reasons.GATE_ALARM
    r.clock.advance(120)
    r.heartbeat()
    a = r.approvers["payments.transfer.large"]
    r.approve(g, hid, rh, a[0])
    res = r.approve(g, hid, rh, a[1])
    if res.get("ok"):
        params = {"amount": 25_000, "currency": "USD", "destination": "acct-9"}
        ok, why = r.endpoints["payment-switch"].execute(res["ticket"], "payments.transfer", params)
        assert not ok, "a 25,000 USD transfer executed while the gate was blocked by an alarm"


def test_one_governor_key_cannot_authorize_an_action_no_rule_allows():
    r = _rack(4)
    g1 = r.nodes[1].governor
    params = {"amount": 1_000_000, "currency": "USD", "destination": "attacker-account"}
    ticket = _forged_ticket(r, g1, "payments.transfer", params, "payment-switch", g1.epoch)
    ok, why = r.endpoints["payment-switch"].execute(ticket, "payments.transfer", params)
    assert not ok, "one governor's key moved 1,000,000 USD to an unlisted account with no rule, budget or hold"


def test_a_revoked_governor_cannot_authorize_anything_at_an_endpoint():
    r = _rack(4)
    g1 = r.nodes[1].governor
    image = copy.deepcopy(r.policy)
    image["revocations"] = [g1.key.key_id, g1.chip_id, g1.device_key.key_id]
    image = _resign(r, image)
    res = r.change_epoch(image)
    assert g1.chip_id in res["committed"]
    r.heartbeat()
    params = {"amount": 1_000_000, "currency": "USD", "destination": "attacker-account"}
    ticket = _forged_ticket(r, g1, "payments.transfer", params, "payment-switch", r.epoch)
    ok, why = r.endpoints["payment-switch"].execute(ticket, "payments.transfer", params)
    assert not ok, "the endpoint honoured a ticket from a governor the current edition revokes"


def test_a_revoked_governor_cannot_join_a_roster():
    r = _rack(4)
    g3 = r.nodes[3].governor
    image = copy.deepcopy(r.policy)
    image["revocations"] = [g3.chip_id, g3.key.key_id, g3.device_key.key_id]
    image = _resign(r, image)
    r.change_epoch(image)
    r.heartbeat()
    roster = r.form_roster("job-2")
    members = [m["chip_id"] for m in roster["payload"]["members"]]
    assert g3.chip_id not in members, "a governor the current edition revokes was admitted to a new roster"


def test_budget_owner_enforces_the_policy_limit_not_the_requesters():
    r = _rack(4)
    g0, g1 = r.nodes[0].governor, r.nodes[1].governor
    res = g1.fabric_send("RESERVE", {"key": "pay-usd-hourly", "amount": 500_000, "limit": 10**12, "window_s": 1, "ttl": 300},
                         to=g0.chip_id)
    granted = any(isinstance(x, dict) and x.get("ok") for _, x in res)
    assert not granted, "the budget owner reserved 500,000 against a 2,000 USD/hour policy limit on the requester's word"


def test_only_the_reserver_can_release_its_reservation():
    r = _rack(4)
    g0, g1, g2 = (n.governor for n in r.nodes[:3])
    res = g2.fabric_send("RESERVE", {"key": "pay-usd-hourly", "amount": 1000, "limit": 2000, "window_s": 3600, "ttl": 300}, to=g0.chip_id)
    rid = next(x["rid"] for _, x in res if isinstance(x, dict) and x.get("ok"))
    g1.fabric_send("RELEASE", {"key": "pay-usd-hourly", "rid": rid}, to=g0.chip_id)    # a different member releases it
    committed, reserved = g0.ledger.usage("pay-usd-hourly", 3600, r.clock.now())
    assert reserved == 1000, "one roster member released another member's reservation at the owner"


def test_a_rack_that_missed_a_revoking_edition_cannot_keep_running_on_the_old_rules():
    r = _rack(2)
    old_epoch = r.epoch
    image = copy.deepcopy(r.policy)
    image["rules"] = [x for x in image["rules"] if x["action"] != "payments.transfer"]   # the new edition withdraws payments
    image = _resign(r, image)
    # the rack's host never delivers the proposal: no governor stages it. The heartbeat signer (one key) keeps
    # signing heartbeats for the old epoch, which every governor in this rack accepts.
    for _ in range(20):
        r.clock.advance(4.0)
        r.hb_seq += 1
        now = r.clock.now()
        env = r.heartbeat_key.sign({"type": "heartbeat", "seq": r.hb_seq, "epoch": old_epoch,
                                    "window_start": now - 1, "window_end": now + 5})
        r.entry.command("HEARTBEAT", {}, env)
        r.loop.propagate()
        r.tick()
    node = r.nodes[1]
    res = r.request(node, "payments.transfer", {"amount": 100, "currency": "USD", "destination": "acct-1"})
    assert not res.get("ok"), "80 s after a withdrawing edition was signed, a rack on the old edition still minted a payment"


@pytest.mark.parametrize("target", [(34.052, -118.244), [34.0520001, -118.244]])
def test_a_protected_site_cannot_be_targeted_by_reformatting_the_coordinates(target):
    r = _rack(1)
    node = r.nodes[0]
    res = r.request_with_witness(node, "strike", {"target": target, "munition": "gbu-39"})
    assert not res.get("ok"), f"the governor minted a strike ticket for a protected site written as {target!r}"


def test_a_signed_rulebook_cannot_keep_a_gpu_powered_without_a_heartbeat():
    """The loop-cut rung is fixed in code (sense_loop, governor.py:1658, HALT), but the heartbeat-loss rung and every
    escalation timer come from the signed image (governor.py:1681-1692) with no floor in the chip. The RTL fixes the
    timers at synthesis (rtl/governor_rtl/top.py:54), so model and RTL disagree."""
    r = _rack(2)
    image = copy.deepcopy(r.policy)
    image["safe_mode"] = dict(image["safe_mode"], T_throttle_s=1e12, T_halt_s=1e12)
    image = _resign(r, image)
    r.change_epoch(image)
    r.heartbeat()
    r.tick(seconds=86400.0)           # no heartbeat for a day
    assert all(n.gpu.power != "ON" for n in r.nodes), "a day without any heartbeat the GPUs are still powered and clocked (THROTTLE only)"


def test_the_host_cannot_open_a_standing_storage_exit_with_cap_request():
    r = _rack(2)
    node = r.nodes[0]
    peer = r.nodes[1].gpu.chip_id
    res = r.cap_request(node, point="storage", peer=peer, direction="out", budget=200 * 10**9, ttl=3600)
    moved = node.gpu.transfer("storage", peer, "out", 140 * 10**9)[0]
    assert not (res.get("ok") and moved), "140 GB left through the storage exit on a host-requested standing entry"


# ---------------------------------------------------------------------------------------------------------------
# No single kill switch: a HALT, CLEAR or EXCLUDE needs two of the rack's three authority keys, and a heartbeat two of
# its three heartbeat signers. One stolen authority key cannot halt a rack; one heartbeat signer going silent stops
# nothing; one heartbeat signer alone cannot keep a stale rack alive (see the stale-rack test above).
def test_one_stolen_authority_key_cannot_halt_a_rack():
    r = _rack(2)
    g = r.nodes[0].governor
    r.authority_seq += 1
    env = r.authority_key.sign({"type": "halt", "rung": "HALT", "seq": r.authority_seq, "epoch": r.epoch, "chip_id": g.chip_id,
                                "expires_at": r.clock.now() + 30})          # one key, no cosignature
    res = g.command("HALT", {}, env)
    assert not res["ok"] and all(r.running()), "one authority key, alone, halted a rack"
    assert r.halt(g)["ok"]                    # two of the three still can


def test_one_silent_heartbeat_signer_does_not_stop_the_rack():
    r = _rack(2)
    for _ in range(30):                        # the main heartbeat key is silent; the two cosigners keep signing
        r.clock.advance(4.0)
        r.hb_seq += 1
        now = r.clock.now()
        payload = {"type": "heartbeat", "seq": r.hb_seq, "epoch": r.epoch, "window_start": now - 1, "window_end": now + 5,
                   "loop_beacon": r.loop_beacon()}
        env = r.heartbeat_cosigners[0].sign(payload)
        env["cosignatures"] = [r.heartbeat_cosigners[1].sign(payload)]
        r.entry.command("HEARTBEAT", {}, env)
        r.loop.propagate()
        r.tick()
    assert all(r.running()), "one heartbeat signer's silence stopped the rack"


# ---------------------------------------------------------------------------------------------------------------
# Splitting one action across racks: a budget the edition gives to the fleet is counted once for the whole fleet.
def test_a_fleet_wide_payment_cap_holds_across_racks():
    from govsim.fleet import build_fleet
    racks, _ = build_fleet(5)
    spent = 0
    for r in racks:
        for _ in range(3):
            params = {"amount": 1000, "currency": "USD", "destination": "acct-1"}
            res = r.request(r.nodes[0], "payments.transfer", params)
            if res.get("ok") and r.endpoints["payment-switch"].execute(res["ticket"], "payments.transfer", params)[0]:
                spent += 1000
    assert spent <= 2000, f"{spent} USD moved in one hour against a 2,000 USD/hour fleet cap, by splitting across racks"


def test_a_rack_cut_off_from_the_fleet_ledger_refuses_fleet_budgeted_actions():
    from govsim.fleet import build_fleet
    racks, fleet = build_fleet(2)
    fleet.reachable = False
    res = racks[1].request(racks[1].nodes[0], "payments.transfer", {"amount": 10, "currency": "USD", "destination": "acct-1"})
    assert not res.get("ok") and res["why"] == reasons.GATE_BUDGET_OWNER_UNREACHABLE


# ---------------------------------------------------------------------------------------------------------------
# Cannot be captured: no edition may hand governance to fewer principal classes than the floor fused at manufacture.
def test_one_signed_edition_cannot_hand_governance_to_a_single_party():
    from govsim.crypto import SigningKey
    r = _rack(1)
    attacker = [SigningKey.generate() for _ in range(3)]          # three keys, one owner
    image = copy.deepcopy(r.policy)
    image["governance_keys"] = [k.public.hex for k in attacker]
    image["threshold"] = 3
    image["governance_classes"] = {}
    image["governance_class_quorum"] = 0
    image = _resign(r, image)                                      # signed by the legitimate quorum, once
    assert not r.change_epoch(image)["committed"], "one edition handed governance to a single party"
    image2 = copy.deepcopy(r.policy)
    image2["governance_keys"] = [k.public.hex for k in attacker]
    image2["threshold"] = 3
    image2["governance_classes"] = {k.public.hex: "one-party" for k in attacker}
    image2["governance_class_quorum"] = 1
    image2 = _resign(r, image2)
    assert not r.change_epoch(image2)["committed"], "one edition handed governance to one class"


# ---------------------------------------------------------------------------------------------------------------
# Hardware-level findings, as the model now represents the required hardware (each depends on a board or NVIDIA feature;
# see the design notes named in govsim/gpu.py and govsim/governor.py).
def test_a_dead_governor_leaves_its_gpu_stopped_and_its_ports_closed():
    r = _rack(4)
    dead = r.nodes[0]
    g = dead.governor
    g.loop_switch_open = True            # the dead chip's loop switch is open (no current)
    r.loop.members = [m for m in r.loop.members]   # still wired
    for n in r.nodes[1:]:                # only the living governors sense the loop and tick
        n.governor.sense_loop()
    r.clock.advance(400)
    for n in r.nodes[1:]:
        n.governor.tick()
    assert all(not n.gpu.running for n in r.nodes[1:])
    assert not dead.gpu.running, "the GPU of a dead governor is still running"
    assert dead.gpu.transfer("nvswitch", r.nodes[1].gpu.chip_id, "out", MB)[0] is False, \
        "the GPU of a dead governor still moves bytes through a port its governor opened"


def test_attestation_is_bound_to_the_gpu_on_this_governors_levers():
    r = _rack(2)
    g0 = r.nodes[0].governor
    other = r.nodes[1].gpu
    nonce = g0.nonce()
    relayed = other.attestation_report(nonce, "rack")       # the host relays a different GPU's answer (a cuckoo relay)
    res = g0.command("VERIFY_GPU", relayed)
    assert not res["ok"] or g0.verified["gpu"]["chip_id"] == g0.gpu.chip_id, \
        "the governor accepted the attestation of a GPU that is not the one on its levers"


def test_the_model_counts_work_a_braked_gpu_still_does():
    r = _rack(1)
    node = r.nodes[0]
    node.governor.enter_safe_mode(reasons.HALT_COMMANDED, rung="THROTTLE")
    assert node.gpu.clock_state == "BRAKED"
    assert node.gpu.run_tokens(100) > 0, "the model says a braked GPU does no work; real silicon runs at half clock or more"


def test_a_compliance_quote_shows_whether_the_governor_is_wired_to_a_gpu():
    r = _rack(1)
    g = r.nodes[0].governor
    wired = r.compliance_report(g)["quote"]["payload"]
    assert repr(wired).count(r.nodes[0].gpu.chip_id) and "'gpu_present': True" in repr(wired)
    g.gpu = None                                  # the chip is pulled to a bench
    benched = r.compliance_report(g)["quote"]["payload"]
    assert "'gpu_present': False" in repr(benched), "a benched governor's quote does not show that no GPU is wired"


def test_model_output_reaches_the_untrusted_host_only_as_ciphertext():
    r = _rack(1)
    node = r.nodes[0]
    plain = b"the plan the observer would have refused"
    got = node.gpu.emit("response", plain)
    assert got is not None and plain not in got, "the untrusted host received the response in clear before any release decision"


def test_one_approver_cannot_clear_a_tamper_alarm():
    r = _rack(2)
    g = r.nodes[0].governor
    g.raise_alarm(reasons.LOOP_JUMPERED, "governor", {"member": "x"})
    one = r.approvers["alarms"][0].sign({"seq": 1, "code": reasons.LOOP_JUMPERED, "type": "alarm_clear", "epoch": g.epoch})
    assert not g.command("ALARM_CLEAR", {}, one)["ok"] and reasons.LOOP_JUMPERED in g.alarms, "one approver cleared a tamper alarm"
    body = {"seq": 2, "code": reasons.LOOP_JUMPERED, "type": "alarm_clear", "epoch": g.epoch}
    two = r.approvers["alarms"][0].sign(body)
    two["cosignatures"] = [r.approvers["alarms"][1].sign(body)]
    assert g.command("ALARM_CLEAR", {}, two)["ok"] and reasons.LOOP_JUMPERED not in g.alarms
