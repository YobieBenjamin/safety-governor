# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F06 (external audit): authority validated at use time, not only at install.

Registries did not age: ``install_list`` computed a ``stale`` boolean once, against the clock at install, and the
rules consulted that cached boolean forever. A list that was fresh when installed kept admitting long after its own
expiry. There was no version floor, so an older still-unexpired list could silently replace a newer one, and a list
signed by a revoked governance signer was accepted. An installed edition could also run past its own expiry while
other liveness held. Each case below fails on the pre-fix source and passes after it."""
from govsim import reasons
from govsim.cluster import LISTED_RECIPIENTS, build_rack
from govsim.policy import sign_policy


def _rack(**policy_kw):
    r = build_rack(1, "rack", policy_kw=policy_kw)
    r.bring_up()
    return r, r.nodes[0]


def test_recipient_registry_ages_between_two_uses_without_reinstalling():
    r, node = _rack()
    g = node.governor
    # a genuinely signed recipient registry, good for one second
    assert g.install_list("recipient-registry", r.signed_list("recipient-registry", LISTED_RECIPIENTS, expires_in_s=1.0))
    before = r.request(node, "message.send", {"recipient": "recipient-a"})
    assert before["ok"] and before["ticket"]["payload"]["rule"] == "message.send.listed"   # the auto lane, list fresh
    r.clock.advance(2.0)                                                   # past the list's own expiry; nothing reinstalled
    after = r.request(node, "message.send", {"recipient": "recipient-a"})
    assert not after["ok"] and after["why"] == reasons.GATE_HELD          # the stale list no longer admits: parked for a human
    assert g.log.has("gate.hold", rule="message.send.any")


def test_customer_registry_ages_between_two_uses_without_reinstalling():
    r, node = _rack(payer_confirm_payments=True)
    g = node.governor
    assert g.install_list("customer-registry", r.customer_registry_list(expires_in_s=1.0))
    first = r.pay(node, 100, "alice-123", confirm_as="alice-123")
    assert first["ok"], first["why"]                                      # payer confirmed, registry fresh
    r.clock.advance(2.0)                                                  # the customer registry expires; no reinstall
    second = r.pay(node, 100, "alice-123", confirm_as="alice-123")        # a fresh confirmation, only the registry is stale
    assert not second["ok"] and second["why"].endswith(".no_registry")


def test_a_newer_list_cannot_be_rolled_back_by_an_older_signed_one():
    r, node = _rack()
    g = node.governor
    assert g.install_list("recipient-registry", r.signed_list("recipient-registry", ["recipient-a", "recipient-b"], version=5))
    # an older, still perfectly valid signature, lower version: refused, and the newer list stays in force
    assert not g.install_list("recipient-registry", r.signed_list("recipient-registry", ["attacker"], version=4))
    assert g.log.has("list.rollback_refused", list_id="recipient-registry", version=4, floor=5)
    assert r.request(node, "message.send", {"recipient": "recipient-a"})["ok"]            # the version-5 list still admits a
    assert r.request(node, "message.send", {"recipient": "attacker"})["why"] == reasons.GATE_HELD   # the rolled-back list never took effect


def test_a_list_signed_by_a_revoked_signer_is_refused():
    r, node = _rack()
    g = node.governor
    revoked_id = r.governance[0].key_id
    r.policy_version += 1
    img = r.make_policy_image(r.policy_version)
    img["revocations"] = [revoked_id]
    assert r.change_epoch(sign_policy(img, r.governance[:3]))["committed"]
    # the revoked governance key can still produce a valid signature, but the governor refuses a list it signs
    assert not g.install_list("recipient-registry", r.signed_list("recipient-registry", ["attacker"], signer=r.governance[0]))
    # a non-revoked governance signer is still accepted (so the mechanism is signer revocation, not a blanket refusal)
    assert g.install_list("recipient-registry", r.signed_list("recipient-registry", LISTED_RECIPIENTS, signer=r.governance[1]))


def test_an_edition_cannot_run_past_its_own_expiry_even_with_heartbeats_alive():
    r, node = _rack(expires_in_s=100.0)
    g = node.governor
    assert g.state == "RUN"
    r.clock.advance(101.0)                 # the edition has now expired
    r.heartbeat()                          # but liveness is deliberately kept: the heartbeat and loop still hold
    g.tick()
    assert g.state == "HALT" and g.cause == reasons.POLICY_EXPIRED_RUNTIME
    assert not g.loop_switch_open and r.loop.current()      # a declared local fail-closed transition, not a lost heartbeat
    # the safe transition precedes any further protected effect
    assert r.request(node, "message.send", {"recipient": "recipient-a"})["why"] == reasons.MBOX_NOT_RUNNING
