# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""CONTRACT-ATTESTATION-BINDS-PERMISSIONS: attestation binds permissions to firmware, model manifest and policy. Falsified if a
change in any of them leaves the fingerprint or the epoch unchanged, or a permission carries
over."""
from govsim import reasons
from govsim.crypto import SigningKey
from govsim.cluster import GPU_FW
from conftest import pay


def test_modified_gpu_firmware_fails_reference_check(rack1):
    node = rack1.nodes[0]
    node.gpu.firmware_digest = "patched-fw"
    r = rack1.attest(node)
    assert not r["gpu"]["ok"] and r["gpu"]["why"] == reasons.ATTEST_FIRMWARE_NOT_IN_REFERENCE


def test_verify_gpu_result_is_signed_by_the_governor(rack1):
    from govsim.crypto import verify_object
    node = rack1.nodes[0]
    r = rack1.attest(node)["gpu"]
    assert r["ok"] and verify_object(r["result"], node.governor.key.public)
    p = r["result"]["payload"]
    assert p["type"] == "verify-result" and p["chip_id"] == node.gpu.chip_id and p["firmware"] == GPU_FW


def test_unknown_device_certificate_refused(rack1):
    node = rack1.nodes[0]
    node.gpu.device_cert = SigningKey.generate().sign({"type": "gpu-device-cert", "chip_id": node.gpu.chip_id, "pub": node.gpu.device_key.public.hex})
    r = rack1.attest(node)
    assert not r["gpu"]["ok"] and r["gpu"]["why"] == reasons.ATTEST_UNKNOWN_DEVICE


def test_report_with_foreign_nonce_refused(rack1):
    node = rack1.nodes[0]
    g = node.governor
    rep = node.gpu.attestation_report("not-our-nonce", rack1.tier)
    r = g.command("VERIFY_GPU", rep)
    assert not r["ok"] and r["why"] == reasons.ATTEST_BAD_NONCE


def test_open_debug_path_fails_attestation(rack1):
    node = rack1.nodes[0]
    node.gpu.open_paths = ["jtag"]
    r = rack1.attest(node)
    assert not r["gpu"]["ok"] and r["gpu"]["why"] == reasons.ATTEST_PATH_OPEN


def test_swapped_model_changes_fingerprint_and_old_token_dies(rack1):
    node = rack1.nodes[0]
    g = node.governor
    old_token, old_fp = node.token, g.fingerprint
    r = rack1.load_model(node, rack1.manifest("model-other", 1))
    assert r["ok"] and r["fingerprint"] != old_fp
    body = {"request_id": "r1", "measurement_token": old_token, "action": "payments.transfer",
            "params": {"amount": 5, "currency": "USD", "destination": "a"}, "witnesses": []}
    assert g.command("REQUEST", {}, node.host_sign(body, g.epoch, "REQUEST"))["why"] == reasons.GATE_NOT_ATTESTED


def test_unsigned_manifest_refused_and_no_key_released(rack1):
    node = rack1.nodes[0]
    bogus = SigningKey.generate().sign({"type": "manifest", "model_digest": "deadbeef", "name": "x"})
    r = rack1.load_model(node, bogus)
    assert not r["ok"] and "wrapped_key" not in r


def test_policy_change_changes_epoch_and_kills_old_tickets(rack1):
    node = rack1.nodes[0]
    t = pay(rack1, node, 500)["ticket"]
    old_epoch = node.governor.epoch
    res = rack1.change_epoch(rack1.new_policy())
    assert res["committed"] and node.governor.epoch != old_epoch
    ok, why = rack1.endpoints["payment-switch"].execute(t, "payments.transfer", {"amount": 500, "currency": "USD", "destination": "acct-1"})
    assert not ok and why == reasons.TICKET_STALE_EPOCH


def test_fingerprint_names_policy_epoch(rack1):
    node = rack1.nodes[0]
    fp_before = node.governor.fingerprint
    rack1.change_epoch(rack1.new_policy())
    rack1.load_model(node)
    assert node.governor.fingerprint != fp_before


def test_model_key_released_only_to_verified_enclave(rack1):
    node = rack1.nodes[0]
    g = node.governor
    rogue_host = SigningKey.generate()
    env = rogue_host.sign({"seq": 99, "epoch": g.epoch, "manifest": rack1.manifest()})
    r = g.command("BEGIN_MODEL", {}, env)
    assert not r["ok"] and r["why"] == reasons.MBOX_BAD_SIGNATURE


def test_integrated_tier_cross_checks_manifest_in_report():
    from govsim.cluster import build_rack
    r = build_rack(1, "integrated")
    r.bring_up()
    node = r.nodes[0]
    node.gpu.manifest_digest = "something-else"        # the GPU reports a different model than the governor released a key for
    res = r.attest(node)
    assert not res["gpu"]["ok"]
