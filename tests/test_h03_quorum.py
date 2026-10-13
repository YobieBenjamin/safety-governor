"""H3: policy changes only with a quorum, and never backwards. Falsified if an image with
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
    r = g.command("POLICY_PROPOSE", {"image": older})            # the fuse remembers across a power loss
    assert not r["ok"] and r["why"] == reasons.POLICY_ROLLBACK


def test_commit_without_a_staged_image_refused(rack1):
    g = rack1.nodes[0].governor
    r = g.command("POLICY_COMMIT", {"epoch": "ff" * 32})
    assert not r["ok"] and r["why"] == reasons.POLICY_NOT_STAGED


def test_host_root_cannot_write_the_epoch(rack1):
    g = rack1.nodes[0].governor
    before = g.epoch
    # the host's only interface is the mailbox; there is no command that sets the epoch
    assert "EPOCH_SET" not in [m[5:].upper() for m in dir(g) if m.startswith("_cmd_")]
    r = g.command("EPOCH_SET", {"epoch": "00" * 32})
    assert not r["ok"] and r["why"] == reasons.MBOX_UNKNOWN_COMMAND
    assert g.epoch == before


def test_expired_image_refused(rack1):
    g = rack1.nodes[0].governor
    image = sign_policy(rack1.make_policy_image(rack1.policy_version + 1, expires_in_s=-1), rack1.governance[:3])
    r = g.command("POLICY_PROPOSE", {"image": image})
    assert r["ok"]                                      # staging verifies signatures and version
    r = g.command("POLICY_COMMIT", {"epoch": __import__("govsim.policy", fromlist=["policy_epoch"]).policy_epoch(image)})
    assert not r["ok"] and r["why"] == reasons.POLICY_EXPIRED
