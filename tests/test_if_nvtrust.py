# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""NVIDIA GPU attestation evidence (nvtrust) into VERIFY_GPU (docs/interfaces/04-nvtrust.md).

All NVIDIA data here is NVIDIA's own public sample from github.com/NVIDIA/nvtrust (BSD-3-Clause,
tests/vectors/nvtrust/LICENSE-nvtrust.txt). Nothing NVIDIA-signed is fabricated. The oracle file
is what NVIDIA's own verifier classes concluded on the same bytes
(tools/interfaces/nvtrust_oracle.py), so these tests compare two independent implementations.
"""
import json

import pytest

from govsim import reasons
from govsim.hardware_ref import nvtrust as N
from govsim.hardware_ref import spdm

ORACLE = json.loads((N.VECTORS / "nvtrust_oracle.json").read_text())


@pytest.fixture(scope="module")
def sample():
    return N.sample()


def test_parse_agrees_with_nvidias_verifier(sample):
    rep_bytes, chain, root = sample
    rep = N.parse_report(rep_bytes)
    assert len(rep_bytes) == ORACLE["report_len"]
    assert rep.version == 0x11 and rep.nonce.hex() == ORACLE["request_nonce"]
    assert len(rep.measurements) == ORACLE["n_measurements"] == 64
    for pos, value in ORACLE["measurements"].items():
        assert rep.measurements[int(pos) + 1].hex() == value          # nvtrust's list position i is block i+1
    assert rep.opaque["FWID"].hex() == ORACLE["fwid"]
    assert rep.opaque["DRIVER_VERSION"].decode().rstrip("\x00") == ORACLE["driver_version"]
    assert rep.opaque["VBIOS_VERSION"].hex() == ORACLE["vbios_version_raw"]
    assert N.vbios_string(rep.opaque["VBIOS_VERSION"]) == "96.00.9f.00.01"


def test_crypto_checks_agree_with_nvidias_verifier(sample):
    ev = N.verify_evidence(*sample)
    assert ev.checks["chain"][0] is ORACLE["chain_ok"] is True
    assert ev.checks["report_signature"][0] is ORACLE["signature_ok"] is True
    assert ev.checks["fwid_binding"][0] is True
    assert ev.ok
    assert {k for k, (_, how) in ev.checks.items() if how == "CRYPTO"} == {"chain", "report_signature", "fwid_binding"}
    assert {k for k, (_, how) in ev.checks.items() if how.startswith("NOT")} == {"revocation", "validity_dates", "debug_state", "model_manifest"}


def test_tampered_report_fails_like_nvidias_verifier(sample):
    rep, chain, root = sample
    bad = bytearray(rep)
    bad[40] ^= 1                                                   # the same byte the oracle flipped
    assert N.verify_evidence(bytes(bad), chain, root).checks["report_signature"][0] is ORACLE["tampered_signature_ok"] is False
    bad = bytearray(rep)
    bad[37 + 8 + 7 + 3] ^= 0x10                                    # inside measurement block 1's value
    assert not N.verify_evidence(bytes(bad), chain, root).checks["report_signature"][0]


def test_wrong_pinned_root_breaks_the_chain(sample):
    rep, chain, _ = sample
    from govsim.root import SiliconRoot
    from govsim.fuses import Fuses
    r = SiliconRoot(Fuses())
    r.boot("00" * 32, "11" * 32, 1)
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    other = x509.load_der_x509_certificate(spdm.GovernorIdentity(r, spdm.test_ca()).chain_ders[0]).public_bytes(serialization.Encoding.PEM).decode()
    assert not N.verify_evidence(rep, chain, other).checks["chain"][0]


def test_golden_comparison_reproduces_nvidias_result_on_its_own_test_rims(sample):
    """NVIDIA ships test RIMs next to the sample. Its own verifier reports the sample does not match
    them, at these indices; ours must say exactly the same."""
    rep = N.parse_report(sample[0])
    golden = {**N.parse_rim_golden((N.VECTORS / "Driver_RIM_test_no_gpu.swidtag").read_text()),
              **N.parse_rim_golden((N.VECTORS / "1010_0200_882_96005E0001_test_no_gpu.swidtag").read_text())}
    assert N.golden_mismatches(rep.measurements, golden) == ORACLE["rims"]["nvidia_mismatch_list"]
    assert ORACLE["rims"]["runtime_vs_golden_ok"] is False
    # and NVIDIA's own RIM signature check fails offline here: the test RIM certificate has expired
    assert ORACLE["rims"]["driver"]["signature_ok"] is False and ORACLE["rims"]["vbios"]["signature_ok"] is False


# ------------------------------------------------------------------ through the governor's mailbox
def nvidia_rack(sample, golden=None, **ref_kw):
    from govsim.cluster import build_rack
    rack = build_rack(1, "rack")
    rack.bring_up()
    rep = N.parse_report(sample[0])
    golden = golden if golden is not None else {i - 1: [v.hex()] for i, v in rep.measurements.items()}
    ref = N.reference_value(sample[2], golden, valid_until=rack.clock.now() + 86400, **ref_kw)
    image = rack.new_policy(extra_refs=[ref])
    res = rack.change_epoch(image)
    g = rack.nodes[0].governor
    assert g.policy and any(r.get("format") == N.FORMAT for r in g.policy["reference_values"]), res
    return rack, g


def test_verify_gpu_accepts_nvidias_sample_through_signed_policy(sample):
    rack, g = nvidia_rack(sample, driver_version="550.90.07", vbios_version="96.00.9f.00.01")
    g.nonces.add(N.parse_report(sample[0]).nonce.hex())           # replaying NVIDIA's fixed-nonce sample; a real run uses g.nonce()
    r = g.command("VERIFY_GPU", N.verify_gpu_body(sample[0], sample[1]))
    assert r["ok"], r
    from govsim.crypto import verify_object
    assert verify_object(r["result"], g.key.public) and r["result"]["payload"]["chip_id"].startswith("nv-")
    assert r["checks"]["revocation"] == [False, "NOT DONE"]
    again = g.command("VERIFY_GPU", N.verify_gpu_body(sample[0], sample[1]))
    assert not again["ok"] and again["why"] == reasons.ATTEST_BAD_NONCE  # the nonce is spent: a replay


def test_verify_gpu_refuses_a_nonce_the_governor_did_not_issue(sample):
    rack, g = nvidia_rack(sample)
    r = g.command("VERIFY_GPU", N.verify_gpu_body(sample[0], sample[1]))
    assert not r["ok"] and r["why"] == reasons.ATTEST_BAD_NONCE


def test_verify_gpu_refuses_against_nvidias_test_rims(sample):
    golden = {**N.parse_rim_golden((N.VECTORS / "Driver_RIM_test_no_gpu.swidtag").read_text()),
              **N.parse_rim_golden((N.VECTORS / "1010_0200_882_96005E0001_test_no_gpu.swidtag").read_text())}
    rack, g = nvidia_rack(sample, golden=golden)
    g.nonces.add(N.parse_report(sample[0]).nonce.hex())
    r = g.command("VERIFY_GPU", N.verify_gpu_body(sample[0], sample[1]))
    assert not r["ok"] and r["why"] == reasons.ATTEST_FIRMWARE_NOT_IN_REFERENCE


@pytest.mark.parametrize("mutate,why", [
    (lambda b: bytes(b[:40]) + bytes([b[40] ^ 1]) + bytes(b[41:]), reasons.ATTEST_BAD_SIGNATURE),
    (lambda b: b[:-1], reasons.ATTEST_BAD_SIGNATURE),
])
def test_verify_gpu_refuses_tampered_evidence(sample, mutate, why):
    rack, g = nvidia_rack(sample)
    g.nonces.add(N.parse_report(sample[0]).nonce.hex())
    r = g.command("VERIFY_GPU", N.verify_gpu_body(mutate(sample[0]), sample[1]))
    assert not r["ok"] and r["why"] == why


def test_verify_gpu_refuses_a_revoked_gpu(sample):
    rack, g = nvidia_rack(sample)
    chip = N.verify_evidence(*sample).chip_id
    g.policy["revocations"] = list(g.policy.get("revocations", [])) + [chip]      # as a signed revocation list would
    g.nonces.add(N.parse_report(sample[0]).nonce.hex())
    r = g.command("VERIFY_GPU", N.verify_gpu_body(sample[0], sample[1]))
    assert not r["ok"] and r["why"] == reasons.ATTEST_REVOKED


def test_verify_gpu_refuses_wrong_driver_version(sample):
    rack, g = nvidia_rack(sample, driver_version="999.0")
    g.nonces.add(N.parse_report(sample[0]).nonce.hex())
    r = g.command("VERIFY_GPU", N.verify_gpu_body(sample[0], sample[1]))
    assert not r["ok"] and r["why"] == reasons.ATTEST_FIRMWARE_NOT_IN_REFERENCE


def test_model_format_reports_still_work(rack1):
    """The NVIDIA path is additive: the model's own report format is untouched."""
    r = rack1.attest(rack1.nodes[0])
    assert r["gpu"]["ok"]
