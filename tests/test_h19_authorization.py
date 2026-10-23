# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""H19: a signature authorizes exactly what was signed, and a policy cannot set its own quorum.

Two defects found on 22 October 2026 by testing against the code: an image with threshold 0 and no
signatures passed the k-of-n check, because the check read k from the image it was checking; and an
authority heartbeat cleared a halt, because the mailbox checked who signed a frame but not what the
frame said it was for. Falsified if any signed message the system produces is accepted by a command
it was not signed for, if an image can set k below the fused threshold, or if a HALT or CLEAR is
good for another chip or after its expiry.
"""
import pytest

from govsim import reasons
from govsim.crypto import SigningKey
from govsim.governor import Governor
from govsim.policy import sign_policy


# ---------------------------------------------------------------- 1. the quorum is the chip's, not the image's
def test_unsigned_image_with_threshold_zero_refused(rack1):
    g = rack1.nodes[0].governor
    image = rack1.make_policy_image(rack1.policy_version + 1)
    image["threshold"], image["signatures"] = 0, []
    r = g.command("POLICY_PROPOSE", {"image": image})
    assert not r["ok"] and r["why"] == reasons.POLICY_QUORUM and g.staged is None
    assert g.load_policy(image) == (False, reasons.POLICY_QUORUM)          # the boot path runs the same check


def test_image_cannot_lower_k_below_the_fused_threshold(rack1):
    g = rack1.nodes[0].governor
    assert g.fuses.governance_threshold == rack1.threshold == 3
    image = rack1.make_policy_image(rack1.policy_version + 1)
    image["threshold"] = 1
    image = sign_policy(image, rack1.governance[:1])                        # one real governance signature, k claimed as 1
    r = g.command("POLICY_PROPOSE", {"image": image})
    assert not r["ok"] and r["why"] == reasons.POLICY_QUORUM


def test_threshold_above_the_number_of_keys_refused(rack1):
    g = rack1.nodes[0].governor
    image = rack1.make_policy_image(rack1.policy_version + 1)
    image["threshold"] = len(image["governance_keys"]) + 1
    image = sign_policy(image, rack1.governance)
    assert g.command("POLICY_PROPOSE", {"image": image})["why"] == reasons.POLICY_QUORUM


def test_a_key_listed_twice_counts_once(rack1):
    g = rack1.nodes[0].governor
    image = rack1.make_policy_image(rack1.policy_version + 1)
    image["governance_keys"] = [image["governance_keys"][0]] * 3 + image["governance_keys"][3:]
    image = sign_policy(image, rack1.governance[:1])
    assert g.command("POLICY_PROPOSE", {"image": image})["why"] == reasons.POLICY_QUORUM


def _image(rack, version, **changes):
    image = rack.make_policy_image(version)
    image.update(changes)
    return image


def _commit(rack, image, signers):
    """Propose and commit on every governor, signed by ``signers``; the rack's version counter follows."""
    signed = sign_policy(image, signers)
    out = rack.change_epoch(signed)
    if out["committed"]:
        rack.policy_version = image["version"]
    return out["committed"]


def test_an_edition_that_raises_k_binds_the_next_change(rack1):
    """The configuration in force decides: once an edition sets k = 4, the next change needs four of the
    current keys. Three is refused; four is accepted, including a change back down to k = 3, because the
    quorum in force may lower k as long as it stays at or above the manufacture floor."""
    g = rack1.nodes[0].governor
    assert _commit(rack1, _image(rack1, rack1.policy_version + 1, threshold=4), rack1.governance[:3])   # authorized by k = 3 in force
    assert g.fuses.trusted_governance["threshold"] == 4
    three = sign_policy(_image(rack1, rack1.policy_version + 1, threshold=3), rack1.governance[:3])
    assert g.command("POLICY_PROPOSE", {"image": three})["why"] == reasons.POLICY_QUORUM
    assert _commit(rack1, _image(rack1, rack1.policy_version + 1, threshold=3), rack1.governance[:4])   # four in force agree
    assert g.fuses.trusted_governance["threshold"] == 3


def test_the_current_quorum_can_rotate_the_governance_keys(rack1):
    """Key rotation: three of the current keys sign an edition that names five new keys. After it, the old
    keys authorize nothing and the new ones do, and a restart keeps it that way."""
    g = rack1.nodes[0].governor
    old = rack1.governance
    new = [SigningKey.generate() for _ in range(5)]
    rotated = _image(rack1, rack1.policy_version + 1, governance_keys=[k.public.hex for k in new], threshold=3)
    assert _commit(rack1, rotated, old[:3])
    assert g.fuses.trusted_governance["keys"] == [k.public.hex for k in new]
    by_old = sign_policy(_image(rack1, rack1.policy_version + 1, governance_keys=[k.public.hex for k in new]), old[:5])
    assert g.command("POLICY_PROPOSE", {"image": by_old})["why"] == reasons.POLICY_QUORUM      # retired keys count for nothing
    by_new = sign_policy(_image(rack1, rack1.policy_version + 1, governance_keys=[k.public.hex for k in new]), new[:3])
    assert g.command("POLICY_PROPOSE", {"image": by_new})["ok"]
    g.restart()
    assert g.policy["version"] == rotated["version"]                                            # the rotated edition reloads
    assert g.command("POLICY_PROPOSE", {"image": by_old})["why"] == reasons.POLICY_QUORUM


def test_fresh_keys_cannot_install_themselves(rack1):
    """The attack the rotation rule must not open: an image that names attacker keys and is signed by
    them. The fused hashes no longer gatekeep after the first edition, so this is refused only because
    the signatures must come from the keys in force."""
    g = rack1.nodes[0].governor
    mine = [SigningKey.generate() for _ in range(5)]
    image = sign_policy(_image(rack1, rack1.policy_version + 1, governance_keys=[k.public.hex for k in mine], threshold=3), mine)
    assert g.command("POLICY_PROPOSE", {"image": image})["why"] == reasons.POLICY_QUORUM
    assert g.fuses.trusted_governance["keys"] == [k.public.hex for k in rack1.governance]


def test_the_quorum_in_force_cannot_go_below_the_manufacture_floor(rack1):
    g = rack1.nodes[0].governor
    assert g.fuses.governance_threshold == 3
    low = sign_policy(_image(rack1, rack1.policy_version + 1, threshold=2), rack1.governance)      # every key signs, k = 2 asked for
    assert g.command("POLICY_PROPOSE", {"image": low})["why"] == reasons.POLICY_QUORUM


def test_the_fused_threshold_only_goes_up(rack1):
    f = rack1.nodes[0].governor.fuses
    with pytest.raises(ValueError):
        f.bump_governance_threshold(f.governance_threshold - 1)


# ---------------------------------------------------------------- 2. a signature authorizes what it names
def _heartbeat_env(rack, seq_bump=1):
    rack.hb_seq += seq_bump
    now = rack.clock.now()
    return rack.heartbeat_key.sign({"type": "heartbeat", "seq": rack.hb_seq, "epoch": rack.epoch, "window_start": now - 1, "window_end": now + 5})


def _halted_and_clearable(rack, g):
    """Halt g and do everything a legitimate CLEAR needs (the cause logged and acknowledged by a
    neighbour), so that the ONLY thing a test varies is the authorization on the CLEAR itself.
    Each test then shows the right CLEAR succeeds, which proves its refusal was for that reason."""
    assert rack.halt(g)["ok"] and g.cause == reasons.HALT_COMMANDED
    rack.exchange_checkpoints()


def _refused_then_control(rack, g, bad_env):
    r = g.command("CLEAR", {}, bad_env)
    assert not r["ok"] and r["why"] == reasons.CLEAR_UNAUTHORIZED, r
    assert g.cause == reasons.HALT_COMMANDED                                   # still halted
    assert rack.clear(g)["ok"] and g.cause is None                             # control: the right CLEAR, same setup, works


def test_a_heartbeat_does_not_clear_a_halt(rack1):
    """The reported defect, reproduced: a legitimate heartbeat sent as CLEAR."""
    g = rack1.nodes[0].governor
    _halted_and_clearable(rack1, g)
    _refused_then_control(rack1, g, _heartbeat_env(rack1))


def test_the_heartbeat_key_cannot_sign_a_clear(rack1):
    """Even typed as a clear and aimed at this chip: the heartbeat key only ever says alive."""
    g = rack1.nodes[0].governor
    _halted_and_clearable(rack1, g)
    rack1.authority_seq += 1
    env = rack1.heartbeat_key.sign({"type": "clear", "seq": rack1.authority_seq, "epoch": rack1.epoch, "chip_id": g.chip_id,
                                    "expires_at": rack1.clock.now() + 30})
    _refused_then_control(rack1, g, env)


def test_a_halt_is_not_a_clear(rack1):
    g = rack1.nodes[0].governor
    _halted_and_clearable(rack1, g)
    _refused_then_control(rack1, g, rack1._authority_env({"type": "halt", "rung": "HALT"}, g))


def test_a_clear_for_another_chip_is_refused():
    """On a two-governor rack, where a CLEAR also needs a neighbour's acknowledgement: the setup gives it
    one, so the refusal can only be the chip binding (the first version of this test passed for the
    missing acknowledgement instead, which the evidence script caught)."""
    from govsim.cluster import build_rack
    rack = build_rack(2, "rack")
    rack.bring_up()
    a, b = rack.nodes[0].governor, rack.nodes[1].governor
    _halted_and_clearable(rack, a)
    _refused_then_control(rack, a, rack._authority_env({"type": "clear"}, b))


def test_an_expired_clear_is_refused(rack1):
    g = rack1.nodes[0].governor
    _halted_and_clearable(rack1, g)
    env = rack1._authority_env({"type": "clear"}, g, ttl_s=30.0)
    rack1.clock.advance(31.0)
    rack1.heartbeat()
    _refused_then_control(rack1, g, env)


def test_a_clear_good_for_a_day_is_refused(rack1):
    """An authorization cannot be banked: the expiry has a ceiling as well as a floor."""
    g = rack1.nodes[0].governor
    _halted_and_clearable(rack1, g)
    _refused_then_control(rack1, g, rack1._authority_env({"type": "clear"}, g, ttl_s=86400.0))


def test_an_approval_does_not_clear_an_alarm(rack1):
    g = rack1.nodes[0].governor
    g.raise_alarm("classifier.stop", "model")
    approval = rack1.approvers["alarms"][0].sign({"seq": 1, "epoch": g.epoch, "type": "approve", "code": "classifier.stop"})
    r = g.command("ALARM_CLEAR", {}, approval)
    assert not r["ok"] and "classifier.stop" in g.alarms


def test_the_mailbox_names_the_wrong_command(rack1):
    """The reason code says what happened: a good signature over a different command."""
    node = rack1.nodes[0]
    g = node.governor
    env = node.host_sign({"model_digest": node.model_digest}, g.epoch, "END_MODEL")
    assert g._check_signed(env, "host", "REQUEST") == (False, reasons.MBOX_WRONG_COMMAND)


# ---------------------------------------------------------------- 3. every message the system signs, into every command
SIGNED_COMMANDS = ["BEGIN_MODEL", "END_MODEL", "REQUEST", "APPROVE", "COMMIT", "ALARM_CLEAR", "SIGN_OUTPUT",
                   "CAP_REQUEST", "HALT", "CLEAR", "ROSTER_JOIN", "HEARTBEAT"]


def test_no_signed_message_is_accepted_by_a_command_it_was_not_signed_for(monkeypatch):
    """Record every signed frame a normal run delivers (heartbeats, model loads, requests, approvals,
    commits, output signing, alarm clears, halts, clears, roster joins), then replay each one into every
    other signed command on a running governor whose replay counters have been wiped, so the sequence
    check cannot hide a missing type check. Anything but a refusal is an authorization defect."""
    from govsim.cluster import build_rack
    seen: list[tuple[str, dict]] = []
    real = Governor.command

    def recording(self, cmd, body=None, env=None):
        if isinstance(env, dict) and isinstance(env.get("payload"), dict):
            seen.append((cmd, env))
        return real(self, cmd, body, env)

    monkeypatch.setattr(Governor, "command", recording)
    rack = build_rack(1, "rack")
    rack.bring_up()
    node = rack.nodes[0]
    g = node.governor
    small = rack.request(node, "payments.transfer", {"amount": 500, "currency": "USD", "destination": "acct-1"})
    assert small["ok"], small
    rack.commit_via_mailbox(g, "payment-switch", small["ticket"])
    large = rack.request(node, "payments.transfer", {"amount": 5000, "currency": "USD", "destination": "acct-1"})
    assert large.get("hold_id"), large
    for approver in rack.approvers["payments.transfer.large"][:2]:
        rack.approve(g, large["hold_id"], large["request_hash"], approver)
    rack.sign_output(node, "response", b"hello")
    g.raise_alarm("classifier.stop", "model")
    rack.approver_seq["alarms"] = 1
    g.command("ALARM_CLEAR", {}, rack.approvers["alarms"][0].sign({"seq": 1, "code": "classifier.stop", "type": "alarm_clear"}))
    rack.halt(g)
    rack.clear(g)
    rack.heartbeat()
    monkeypatch.setattr(Governor, "command", real)

    kinds = {c for c, _ in seen}
    assert set(SIGNED_COMMANDS) - {"END_MODEL", "CAP_REQUEST"} <= kinds, kinds

    accepted = []
    for own, env in seen:
        for target in SIGNED_COMMANDS:
            if target == own:
                continue
            g.mbox_seq, g.hb_last_seq = {}, -1
            r = g.command(target, {}, env)
            if r.get("ok"):
                accepted.append((own, target, env["payload"].get("type")))
    assert not accepted, f"signed frames accepted by commands they were not signed for: {accepted}"


# ---------------------------------------------------------------- 4. the code side of P13
def test_a_ticket_issued_before_a_halt_does_not_execute_during_it(rack1):
    """The abstract machine let a ticket issued before a halt execute during it (an audit asked the
    solver on 22 October and got SAT). The code always refused at commit; this pins that it does."""
    node = rack1.nodes[0]
    g = node.governor
    params = {"amount": 500, "currency": "USD", "destination": "acct-1"}
    r = rack1.request(node, "payments.transfer", params)
    assert r["ok"] and r["ticket"]
    assert rack1.halt(g)["ok"] and g.state != "RUN"
    ok, why = rack1.endpoints["payment-switch"].execute(r["ticket"], "payments.transfer", params)
    assert not ok
