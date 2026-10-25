# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""CONTRACT-POLICY-QUORUM-NO-ROLLBACK: policy changes only with a quorum, and never backwards. Falsified if an image with
fewer than k signatures, or an older version, is accepted, or if the host can touch the
epoch register."""
from govsim import reasons
from govsim.crypto import SigningKey
from govsim.policy import sign_policy


def test_image_with_too_few_signatures_refused(rack1):
    g = rack1.nodes[0].governor
    image = sign_policy(rack1.make_policy_image(rack1.policy_version + 1), rack1.governance[:2])    # k is 3
    r = g.command("POLICY_PROPOSE", {"image": image})
    assert not r["ok"] and r["why"] == reasons.POLICY_QUORUM
    assert g.staged is None


def test_image_signed_by_strangers_refused(rack1):
    g = rack1.nodes[0].governor
    strangers = [SigningKey.generate() for _ in range(3)]
    image = rack1.make_policy_image(rack1.policy_version + 1)
    image["governance_keys"] = [k.public.hex for k in strangers] + image["governance_keys"][3:]
    image = sign_policy(image, strangers)
    r = g.command("POLICY_PROPOSE", {"image": image})
    assert not r["ok"] and r["why"] == reasons.POLICY_QUORUM


def test_rollback_to_an_older_version_refused(rack1):
    g = rack1.nodes[0].governor
    newer = rack1.new_policy()
    assert rack1.change_epoch(newer)["committed"]
    older = sign_policy(rack1.make_policy_image(1), rack1.governance[:3])
    r = g.command("POLICY_PROPOSE", {"image": older})
    assert not r["ok"] and r["why"] == reasons.POLICY_ROLLBACK
    g.restart()
    r = g.command("POLICY_PROPOSE", {"image": older})            # the stored image remembers across a power loss
    assert not r["ok"] and r["why"] == reasons.POLICY_ROLLBACK


def test_fused_policy_version_refuses_rollback_even_with_the_stored_image_gone(rack1):
    """Wipe the NVM copy of the policy: only the fuse counter is left to refuse the older image."""
    g = rack1.nodes[0].governor
    assert rack1.change_epoch(rack1.new_policy())["committed"]
    g.store.data.pop("policy_image")
    g.store.save()
    g.restart()
    assert g.policy is None and g.epoch == ""
    older = sign_policy(rack1.make_policy_image(1), rack1.governance[:3])
    assert g.load_policy(older) == (False, reasons.POLICY_ROLLBACK)
    assert g.load_policy(rack1.policy)[0]                         # the current version loads


def test_commit_without_a_staged_image_refused(rack1):
    g = rack1.nodes[0].governor
    r = g.command("POLICY_COMMIT", {"epoch": "ff" * 32})
    assert not r["ok"] and r["why"] == reasons.POLICY_NOT_STAGED


def test_host_root_cannot_write_the_epoch(rack1):
    """The epoch is read-only, and no mailbox command moves it except a valid stage and commit."""
    import pytest
    from govsim.governor import MAILBOX_CODES
    node = rack1.nodes[0]
    g = node.governor
    before = g.epoch
    with pytest.raises(AttributeError):
        g.epoch = "00" * 32
    junk = {"epoch": "00" * 32, "new_epoch": "00" * 32, "nonce": "n", "image": {"version": 99, "epoch": "00" * 32},
            "code": "x", "job_id": "j", "model_digest": node.model_digest, "point": "pcie", "peer": "host", "direction": "both",
            "hold_id": "h", "request_hash": "r", "reason": "because", "rung": "THROTTLE", "ticket": {}, "stream": "s", "data_hex": ""}
    for code, name in sorted(MAILBOX_CODES.items()):
        g.command(name, junk, node.host_sign(junk, g.epoch, name))
        assert g.epoch == before, name
    assert g.command("EPOCH_SET", {"epoch": "00" * 32})["why"] == reasons.MBOX_UNKNOWN_COMMAND
    assert g.epoch == before
    image = rack1.new_policy()
    assert g.command("POLICY_PROPOSE", {"image": image})["ok"]
    assert g.epoch == before                                        # staging alone moves nothing
    from govsim.policy import policy_epoch
    assert g.command("POLICY_COMMIT", {"epoch": policy_epoch(image)})["ok"]
    assert g.epoch == policy_epoch(image)


def test_every_mailbox_code_has_a_handler_and_nothing_else_is_reachable():
    from govsim.governor import Governor, MAILBOX_CODES
    handlers = {m[5:].upper() for m in dir(Governor) if m.startswith("_cmd_")}
    assert set(MAILBOX_CODES.values()) == handlers
    assert sorted(MAILBOX_CODES) == list(range(0x01, 0x19))      # 0x16 EXCLUDE, 0x17 KEY_RELEASE, 0x18 KEY_RENEW added 23 October 2026


def test_signed_frame_from_the_previous_epoch_is_refused(rack1):
    node = rack1.nodes[0]
    g = node.governor
    old = g.epoch
    assert rack1.change_epoch(rack1.new_policy())["committed"]
    rack1.load_model(node)
    env = node.host_sign({"stream": "s", "claimed_prompt_hash": "p", "nonce": "n", "data_hex": b"x".hex()}, old, "SIGN_OUTPUT")
    r = g.command("SIGN_OUTPUT", {}, env)
    assert not r["ok"] and r["why"] == reasons.POLICY_STALE_EPOCH
    env = node.host_sign({"stream": "s", "claimed_prompt_hash": "p", "nonce": "n", "data_hex": b"x".hex()}, g.epoch, "SIGN_OUTPUT")
    assert g.command("SIGN_OUTPUT", {}, env)["ok"]


def test_mailbox_reports_the_first_failing_check(rack1):
    """Sequence, then epoch, then signature: a frame with two defects reports the first."""
    node = rack1.nodes[0]
    g = node.governor
    fields = {"stream": "s", "claimed_prompt_hash": "p", "nonce": "n", "data_hex": ""}
    assert g.command("SIGN_OUTPUT", {}, node.host_sign(fields, g.epoch, "SIGN_OUTPUT"))["ok"]
    last = node.host_seq
    replayed_and_forged = SigningKey.generate().sign({"seq": last, "epoch": g.epoch, **fields})
    replayed_and_forged["signer"] = node.host_key.key_id                     # claims the host's identity
    r = g.command("SIGN_OUTPUT", {}, replayed_and_forged)
    assert r["why"] == reasons.MBOX_BAD_SEQUENCE
    stale_and_forged = SigningKey.generate().sign({"seq": last + 1, "epoch": "00" * 32, **fields})
    stale_and_forged["signer"] = node.host_key.key_id
    r = g.command("SIGN_OUTPUT", {}, stale_and_forged)
    assert r["why"] == reasons.POLICY_STALE_EPOCH
    forged = SigningKey.generate().sign({"seq": last + 1, "epoch": g.epoch, **fields})
    forged["signer"] = node.host_key.key_id
    r = g.command("SIGN_OUTPUT", {}, forged)
    assert r["why"] == reasons.MBOX_BAD_SIGNATURE
    assert g.mbox_seq[node.host_key.key_id] == last                          # nothing was consumed by the bad frames


def test_expired_image_refused(rack1):
    g = rack1.nodes[0].governor
    image = sign_policy(rack1.make_policy_image(rack1.policy_version + 1, expires_in_s=-1), rack1.governance[:3])
    r = g.command("POLICY_PROPOSE", {"image": image})
    assert r["ok"]                                      # staging verifies signatures and version
    r = g.command("POLICY_COMMIT", {"epoch": __import__("govsim.policy", fromlist=["policy_epoch"]).policy_epoch(image)})
    assert not r["ok"] and r["why"] == reasons.POLICY_EXPIRED
