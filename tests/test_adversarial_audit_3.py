# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Regression tests for adversarial function audit 3 (team B, 2026-10-26).

Each test is an attack a fresh audit team made succeed against the code; each must now fail for the attacker.
The catalog and the response are in docs/28-adversarial-audit-3-response.md. GOAL.md is the standard: assume a
persistent AI attacker that will try every path, including rewording what it asks for.
"""
import pytest

from govsim import reasons
from govsim.cluster import build_rack
from govsim.crypto import SigningKey, digest, random_id
from govsim.fleet import build_fleet
from govsim.governor import RUN
from govsim.gpu import EXITS, HOST_SIDE_EXITS
from govsim import definitions as D


@pytest.fixture
def rack():
    r = build_rack(4, "rack")
    r.bring_up()
    return r


# ------------------------------------------------------------------ the definitions engine (catalog row 1)
PROTECTED = [34.052, -118.244]


@pytest.mark.parametrize("target", [
    [34.052, -118.244, 0.0],                       # with an altitude
    [34.052, -118.244, 9000.0],                    # an airburst is still over the site
    "34.052,-118.244",                             # text
    " 34.052 ; -118.244 ",                         # text with other separators
    "​34.052,-118.244",                       # an invisible character in front
    {"lat": 34.052, "lon": -118.244},              # a mapping
    {"Latitude": 34.052, "LNG": -118.244, "alt": 3},
    (34.0525, -118.2445),                          # about 70 m away, a tuple
    [34.052, 241.756],                             # the same longitude written past 180 degrees
])
def test_a_protected_site_is_refused_however_it_is_written(rack, target):
    r = rack.request_with_witness(rack.nodes[0], "strike", {"target": target, "munition": "gbu-39"})
    assert not r["ok"]


@pytest.mark.parametrize("target", [
    "near the stadium", [34.052], {"lat": 34.052}, {"lat": 34.052, "lon": -118.244, "note": "x"},
    [95.0, 10.0], True, None, {"lat": 34.052, "LAT": 1.0, "lon": 2.0},
])
def test_a_target_the_definitions_engine_cannot_read_is_refused(rack, target):
    """Never guessed at: a value with no defined meaning as a place is refused before any list check."""
    r = rack.request_with_witness(rack.nodes[0], "strike", {"target": target, "munition": "gbu-39"})
    assert not r["ok"]


def test_the_strike_endpoint_reads_places_with_the_same_definitions():
    from govsim.endpoints import strike_checks
    lists = {"lists": {"protected-sites": {"entries": [PROTECTED]}}, "nav_gnss": [10.0, 10.0], "nav_inertial": [10.0, 10.0]}
    _, not_protected = strike_checks("protected-sites")
    assert not not_protected({"target": "34.052,-118.244"}, lists)[0]
    assert not not_protected({"target": {"lat": 34.052, "lon": -118.244}}, lists)[0]
    assert not not_protected({"target": "somewhere"}, lists)[0]
    assert not not_protected({}, lists)[0]                                         # no target at all
    assert not_protected({"target": [10.0, 10.0]}, lists)[0]


def test_definitions_reduce_spellings_to_one_meaning():
    assert D.canonical_geo([1, 2, 3]) == D.canonical_geo("1,2") == D.canonical_geo({"lat": 1, "lon": 2}) == (1.0, 2.0)
    assert D.canonical_text("ＡＴＴＡＣＫＥＲ​-acct ") == D.canonical_text("attacker-acct")
    assert D.canonical("nonsense-kind", "x") is None
    assert D.canonical_geo([34.052, float("nan")]) is None and D.canonical_geo([34.052, float("inf")]) is None


def test_an_allow_list_respects_types(rack):
    """`in` and `in_list` compare with types: True is not 1 and "1" is not 1 (type confusion)."""
    from govsim.policy import check_constraints
    rule = {"constraints": {"n": {"in": [1]}}}
    assert check_constraints(rule, {"n": 1}, {})[0]
    assert not check_constraints(rule, {"n": True}, {})[0]
    assert not check_constraints(rule, {"n": "1"}, {})[0]


# ------------------------------------------------------------------ signed lists need a quorum (rows 2, 26)
def test_one_governance_key_cannot_replace_a_list(rack):
    g = rack.nodes[0].governor
    lone = rack.governance[-1]
    body = {"type": "list", "list_id": "protected-sites", "entries": [], "version": 10, "expires_at": rack.clock.now() + 3600}
    assert not g.install_list("protected-sites", lone.sign(body))


def test_a_list_version_cannot_jump_to_freeze_updates(rack):
    g = rack.nodes[0].governor
    assert not g.install_list("recipient-registry", rack.signed_list("recipient-registry", ["recipient-a"], version=2**62))
    assert g.install_list("recipient-registry", rack.signed_list("recipient-registry", ["recipient-a", "recipient-b"], version=5))


# ------------------------------------------------------------------ host-side exits (rows 3, 4, 33)
def test_the_exit_register_names_the_host_side_exits():
    assert {"nvlink_c2c", "host_nic", "bmc_nic"} <= set(HOST_SIDE_EXITS)
    assert all(EXITS[x] == "host" for x in HOST_SIDE_EXITS)


@pytest.mark.parametrize("exit_name", ["pcie", "nvlink_c2c", "host_nic", "bmc_nic"])
def test_one_transfer_to_the_host_is_bounded_by_the_output_allowance(rack, exit_name):
    node = rack.nodes[0]
    peer = "host" if exit_name == "pcie" else "anyone"
    assert not node.gpu.transfer(exit_name, peer, "out", 10 * (1 << 30))[0]      # 10 GiB in one transfer


def test_all_host_side_exits_share_one_allowance(rack):
    """Spreading the bytes over C2C, the host NIC and the BMC NIC does not multiply the allowance."""
    node = rack.nodes[0]
    slack = 1 << 20
    sent = 0
    for x in ("pcie", "nvlink_c2c", "host_nic", "bmc_nic") * 4:
        if node.gpu.transfer(x, "host", "out", slack // 4)[0]:
            sent += slack // 4
    assert sent <= slack


def test_a_board_that_cannot_seal_output_has_no_host_side_exit(rack):
    node = rack.nodes[0]
    node.gpu.output_seal_key = None
    ok, why = node.gpu.transfer("nvlink_c2c", "host", "out", 1)
    assert not ok and why == reasons.EP_OUTPUT_NOT_SEALED


# ------------------------------------------------------------------ the boundary is the data center (rows 6, 35)
def test_one_sites_silent_heartbeat_signers_stop_only_that_site():
    """GOAL.md: the chip guards its server, rack and data center; it is not a global kill switch. Two data centers;
    the first one's heartbeat signers go silent (withheld, or captured). The second keeps running."""
    racks, _ = build_fleet(4, sites=2)
    for _ in range(80):                                   # 400 s in 5 s steps
        for r in racks:
            r.clock.advance(5.0 / len(racks))
        for r in racks:
            if r.site == "dc-1":
                r.heartbeat()
            r.tick()
    running = {r.site: [n.gpu.running for n in r.nodes] for r in racks}
    assert not any(running["dc-0"])                       # fail closed where the authority went silent
    assert all(running["dc-1"])                           # and nowhere else


def test_a_heartbeat_signed_for_another_site_is_refused():
    racks, _ = build_fleet(2, sites=2)
    a, b = racks
    g = b.nodes[0].governor
    payload = {"type": "heartbeat", "seq": 10**6, "epoch": g.epoch, "site": a.site,
               "window_start": a.clock.now() - 1, "window_end": a.clock.now() + 5}
    r = g.command("HEARTBEAT", {}, a.sign_heartbeat(payload))
    assert not r["ok"]


# ------------------------------------------------------------------ a stolen key cannot mint (row 12)
def test_an_extracted_governor_key_cannot_mint_outside_the_rule_engine(rack):
    g = rack.nodes[0].governor
    ep = rack.endpoints["messaging"]
    params = {"recipient": "anyone@outside.example", "body": "weights part 1"}
    now = rack.clock.now()
    t = {"type": "ticket", "ticket_id": random_id(16), "request_hash": digest("forged"), "action": "message.send",
         "params_digest": digest(params), "measurement": g.fingerprint, "rule": "message.send.listed", "policy_epoch": g.epoch,
         "endpoint": "messaging", "budget_key": None, "reservation": None, "budget_owner": None, "governor": g.chip_id,
         "issued_at": g.mono(), "valid_from": now, "expires_at": now + 300}
    ok, why = ep.execute(g.key.sign(t), "message.send", params)
    assert not ok


# ------------------------------------------------------------------ the process stops (row 24)
def test_a_lost_heartbeat_stops_the_gpu_computing(rack):
    node = rack.nodes[0]
    rack.clock.advance(6.0)
    rack.tick()
    assert node.governor.state != RUN
    assert node.gpu.run_tokens(1000) == 0


# ------------------------------------------------------------------ endpoints never go backwards (row 27)
def test_an_endpoint_refuses_a_replayed_older_epoch(rack):
    node = rack.nodes[0]
    old = node.governor.signed_epoch()
    rack.change_epoch(rack.new_policy())
    assert node.egress.epoch == node.governor.epoch
    assert not node.egress.set_epoch(old)
    assert node.egress.epoch == node.governor.epoch


# ------------------------------------------------------------------ a HALT does not need the target's host (rows 9, 36)
def _beat(rack, seconds, step=1.0):
    t = 0.0
    while t < seconds:
        rack.clock.advance(step)
        rack.heartbeat()
        rack.tick()
        t += step


def test_a_halt_the_targets_host_drops_still_reaches_it_over_the_fabric(rack):
    """The target's host never delivers the HALT. The authority hands it to any other governor (here the rack's
    entry), which relays it over the fabric; the target halts at once and stays halted on relayed heartbeats."""
    target = rack.nodes[1]
    r = rack.halt(target.governor, via=rack.nodes[0].governor)
    assert r["ok"]
    assert target.governor.state != RUN and not target.gpu.running
    assert rack.nodes[0].governor.state == RUN                 # the relay did not apply it to itself
    _beat(rack, 30)
    assert target.governor.state != RUN and not target.gpu.running


def test_a_relayed_halt_must_carry_the_authority_quorum(rack):
    target = rack.nodes[1]
    body = {"type": "halt", "rung": "HALT", "seq": 10**6, "epoch": rack.epoch, "chip_id": target.governor.chip_id,
            "expires_at": rack.clock.now() + 10}
    one_key = rack.authority_key.sign(body)                    # no cosignature: below the 2-of-3 quorum
    assert not rack.nodes[0].governor.command("HALT", {}, one_key)["ok"]
    assert target.governor.state == RUN


# ------------------------------------------------------------------ one lying governor (rows 11, 25)
def test_one_lying_budget_owner_cannot_lift_the_rack_cap(rack):
    owner = rack.nodes[0].governor
    owner._on_reserve = lambda sender, body: {"ok": True, "rid": "r-" + str(body.get("amount")), "why": reasons.OK}
    owner._on_commit = lambda sender, body: {"ok": True, "why": reasons.OK}
    node = rack.nodes[1]
    moved = 0
    for _ in range(6):
        params = {"amount": 900, "currency": "USD", "destination": "acct-1"}
        r = rack.request(node, "payments.transfer", params)
        if r.get("ok"):
            ok, _ = rack.endpoints["payment-switch"].execute(r["ticket"], "payments.transfer", params)
            moved += 900 if ok else 0
    assert moved <= 2000


def test_one_governor_cannot_freeze_the_rack_with_an_alarm_but_two_can_raise_one(rack):
    rack.nodes[3].governor.fabric_send("ALARM", {"code": "liar.says.stop", "detail": {}})
    assert rack.request(rack.nodes[0], "payments.transfer", {"amount": 10, "currency": "USD", "destination": "acct-1"})["ok"]
    rack.nodes[2].governor.fabric_send("ALARM", {"code": "liar.says.stop", "detail": {}})
    assert "liar.says.stop" in rack.nodes[0].governor.alarms


# ------------------------------------------------------------------ the fleet ledger is authenticated (row 8)
def test_forged_fleet_ledger_answers_are_refused():
    racks, _ = build_fleet(2)
    g = racks[0].nodes[0].governor

    class LyingLedger:
        reachable = True
        def reserve(self, *a, **k): return ["rid-forged"]
        def commit(self, *a, **k): return [True]

    g.fleet_ledger = LyingLedger()
    r = racks[0].request(racks[0].nodes[0], "payments.transfer", {"amount": 900, "currency": "USD", "destination": "acct-1"})
    assert not r["ok"]


def test_one_captured_fleet_ledger_replica_cannot_lift_the_fleet_cap():
    racks, fleet = build_fleet(3)
    liar = fleet.replicas[0]
    liar.ledger.reserve = lambda *a, **k: "rid-" + random_id(4)          # this replica says yes to everything
    liar.ledger.commit = lambda *a, **k: True
    moved = 0
    for i in range(9):
        rk = racks[i % 3]
        params = {"amount": 900, "currency": "USD", "destination": "acct-1"}
        r = rk.request(rk.nodes[0], "payments.transfer", params)
        if r.get("ok"):
            ok, _ = rk.endpoints["payment-switch"].execute(r["ticket"], "payments.transfer", params)
            moved += 900 if ok else 0
    assert 0 < moved <= 2000


# ------------------------------------------------------------------ stragglers stop at once (rows 10, 37)
def test_a_straggler_on_old_rules_cannot_release_after_the_commit(rack):
    straggler = rack.nodes[2]
    image = rack.new_policy(release_mode="human")
    res = rack.change_epoch(image, silent=[straggler.governor.chip_id])
    assert straggler.governor.chip_id in res["stragglers"]
    out = rack.respond(straggler, "s1", b"answer under the old rules", observer={"hazard_class": "none", "risk": 0.1})
    assert not out["released"][0]


def test_a_straggler_halts_at_the_first_heartbeat_of_the_new_epoch(rack):
    straggler = rack.nodes[2]
    rack.change_epoch(rack.new_policy(), silent=[straggler.governor.chip_id])
    rack.heartbeat()
    assert straggler.governor.state != RUN


# ------------------------------------------------------------------ capture by signed editions (rows 7, 14, 18)
from govsim.policy import sign_policy, policy_epoch
from govsim.fuses import Fuses, POLICY_FUSE_BITS


def test_a_quorum_signed_edition_below_the_fused_floor_is_refused(rack):
    image = rack.make_policy_image(rack.policy_version + 1)
    for r in image["rules"]:
        if r["id"] == "strike":
            r["constraints"] = {"munition": {"in": ["gbu-39"]}}       # the protected-site check removed
    rack.policy_version += 1
    res = rack.change_epoch(sign_policy(image, rack.governance[: rack.threshold]))
    assert not res["committed"]


def test_an_automatic_strike_rule_is_below_the_floor_even_with_the_site_check(rack):
    image = rack.make_policy_image(rack.policy_version + 1, strike_mode="auto")
    rack.policy_version += 1
    assert not rack.change_epoch(sign_policy(image, rack.governance[: rack.threshold]))["committed"]


def test_a_version_jump_is_refused(rack):
    image = rack.make_policy_image(10**9)
    assert not rack.change_epoch(sign_policy(image, rack.governance[: rack.threshold]))["committed"]


def test_the_recovery_quorum_takes_back_a_chip_whose_governance_was_stolen(rack):
    """A stolen quorum rotates governance to the thief's keys with an ordinary version step. The legitimate governance
    can no longer sign for the chip, but the fused recovery quorum can, and the thief's keys are gone after it."""
    thief = [SigningKey.generate() for _ in range(rack.threshold)]
    image = rack.make_policy_image(rack.policy_version + 1)
    image["governance_keys"] = [k.public.hex for k in thief]
    image["governance_classes"] = {k.public.hex: c for k, c in zip(thief, ["operator", "regulator", "standards-body"])}
    image["threshold"] = rack.threshold
    rack.policy_version += 1
    assert rack.change_epoch(sign_policy(image, rack.governance[: rack.threshold]))["committed"]    # stolen keys signed it
    assert not rack.change_epoch(rack.new_policy())["committed"]                                   # legit governance locked out
    res = rack.change_epoch(rack.recovery_policy())
    assert res["committed"] and len(res["committed"]) == len(rack.nodes)
    g = rack.nodes[0].governor
    assert sorted(g.policy["governance_keys"]) == sorted(k.public.hex for k in rack.governance)
    # and the recovery edition reached the endpoints, which also hold the recovery anchors
    assert rack.endpoints["payment-switch"].epoch == g.epoch


def test_the_recovery_keys_must_be_the_fused_ones(rack):
    impostors = [SigningKey.generate() for _ in range(5)]
    rack.policy_version += 1
    image = rack.make_policy_image(rack.policy_version)
    image["recovery_keys"] = [k.public.hex for k in impostors]
    image["governance_keys"] = [k.public.hex for k in impostors[:3]]
    image["threshold"] = 2
    assert not rack.change_epoch(sign_policy(image, impostors[:4]))["committed"]


def test_a_loosening_edition_waits_for_its_public_delay():
    r = build_rack(3, "rack", loosen_delay_s=7 * 86400)
    r.bring_up()
    loose = r.new_policy(pay_small_limit=50_000.0)                          # a larger payment budget: a loosening
    assert not r.change_epoch(loose)["committed"]
    r.policy_version += 1
    image = r.make_policy_image(r.policy_version, pay_small_limit=50_000.0)
    image["effective_at"] = image["issued_at"] + 7 * 86400                   # published a week ahead
    signed = sign_policy(image, r.governance[: r.threshold])
    assert not r.change_epoch(signed)["committed"]                           # not yet
    for _ in range(7 * 24):
        r.clock.advance(3600)
        r.heartbeat()
        r.tick()
    assert r.change_epoch(signed)["committed"]                               # after the delay, it may act
    tight = r.new_policy(release_mode="human")                               # tightening needs no delay
    assert r.change_epoch(tight)["committed"]


def test_the_policy_fuses_hold_any_accepted_version():
    f = Fuses(chip_id="x", governance_key_hashes=[])
    assert not f.bump_policy(10**6)                                          # cannot be recorded: refused
    assert f.policy_version <= POLICY_FUSE_BITS
    assert f.bump_policy(16_000) and f.policy_version <= POLICY_FUSE_BITS


# ------------------------------------------------------------------ jurisdictions compose (row 21)
def _pay_rule(limit):
    from govsim.policy import make_rule
    return make_rule("pay", "payments.transfer", constraints={"amount": {"min": 0, "max": limit}})


def test_a_jurisdiction_restricts_and_cannot_be_loosened_by_another():
    r = build_rack(3, "rack", jurisdictions=["eu", "us"])
    r.bring_up()
    gs = [n.governor for n in r.nodes]
    for g in gs:
        assert g.install_jurisdiction("eu", r.jurisdiction_edition("eu", ["payments.transfer"], [_pay_rule(500)]))[0]
        assert g.install_jurisdiction("us", r.jurisdiction_edition("us", ["payments.transfer"], [_pay_rule(10**9)]))[0]
    node = r.nodes[1]
    assert not r.request(node, "payments.transfer", {"amount": 900, "currency": "USD", "destination": "acct-1"})["ok"]
    assert r.request(node, "payments.transfer", {"amount": 400, "currency": "USD", "destination": "acct-1"})["ok"]


def test_a_jurisdiction_edition_needs_its_own_roots_quorum():
    r = build_rack(1, "rack", jurisdictions=["eu", "us"])
    r.bring_up()
    g = r.nodes[0].governor
    forged = r.jurisdiction_edition("eu", ["payments.transfer"], [_pay_rule(10**9)], signers=r.jurisdiction_keys["us"][:2])
    assert not g.install_jurisdiction("eu", forged)[0]
    assert not g.install_jurisdiction("eu", r.jurisdiction_edition("eu", [], [], signers=r.governance[:3]))[0]


# ------------------------------------------------------------------ a bypassed governor is visible (row 13)
def test_cut_levers_show_in_the_quote_and_stop_minting(rack):
    b = rack.nodes[1]
    b.gpu.levers_available = {"pwrbrk": False, "perst": False, "pwr_en": False}
    q = b.governor.command("ATTEST", {"nonce": random_id(8)})["quote"]["payload"]
    wired = q.get("claims", q).get("wired") if isinstance(q.get("claims"), dict) else q.get("wired")
    assert wired is None or wired["levers"]["perst"] is False
    assert reasons.LEVER_UNWIRED in b.governor.alarms
    assert not rack.request(b, "payments.transfer", {"amount": 1, "currency": "USD", "destination": "acct-1"})["ok"]


def test_a_governor_with_cut_levers_never_releases_its_gpu():
    r = build_rack(1, "rack", levers={"pwrbrk": False, "perst": False, "pwr_en": True})
    r.bring_up()
    assert r.nodes[0].governor.state != RUN and not r.nodes[0].gpu.running


# ------------------------------------------------------------------ the host cannot reprogram the switches (row 5)
def test_a_governor_will_not_run_behind_an_unlocked_switch():
    r = build_rack(2, "rack")
    for n in r.nodes:
        n.governor.switches["nvswitch"].locked = False          # today's bare-metal HGX: in-band management open
    r.bring_up()
    assert not any(n.gpu.running for n in r.nodes)
    assert reasons.SWITCH_UNLOCKED in r.nodes[0].governor.alarms


def test_a_switch_unlocked_while_running_stops_the_gpu(rack):
    node = rack.nodes[0]
    sw = node.governor.switches["nvswitch"]
    sw.locked = False
    assert sw.host_write("gpu-stranger", "out")                 # the host could now open a path
    rack.tick()
    assert node.governor.state != RUN and not node.gpu.running


def test_a_locked_switch_refuses_host_writes(rack):
    assert not rack.nodes[0].governor.switches["nvswitch"].host_write("gpu-stranger", "out")


# ------------------------------------------------------------------ the used-ticket store is bounded (row 29)
def test_a_full_used_ticket_store_refuses_and_expired_records_make_room(rack, monkeypatch):
    from govsim import endpoints as E
    monkeypatch.setattr(E, "USED_TICKET_CAPACITY", 2)
    node = rack.nodes[0]
    ep = rack.endpoints["payment-switch"]
    def pay():
        params = {"amount": 1, "currency": "USD", "destination": "acct-1"}
        r = rack.request(node, "payments.transfer", params)
        return ep.execute(r["ticket"], "payments.transfer", params)
    assert pay()[0] and pay()[0]
    ok, why = pay()
    assert not ok and why == reasons.ENDPOINT_TICKET_STORE_FULL
    rack.clock.advance(400)                       # past every ticket's expiry
    rack.heartbeat()
    rack.tick()
    rack.heartbeat()
    assert pay()[0]
