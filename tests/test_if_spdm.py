"""The governor as an SPDM responder (docs/interfaces/03-spdm.md).

In-process tests: the governor's responder against the governor's requester, the DICE binding,
and planted faults that the requester must catch by assertion. Interop tests against DMTF's
libspdm and SPDM-Responder-Validator run when the spdm-emu binaries are present (see
govsim/hardware_ref/interop.py) and are skipped, with the reason, when they are not.
"""
import hashlib
import struct

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from govsim.crypto import digest
from govsim.fuses import Fuses
from govsim.hardware_ref import interop, spdm
from govsim.root import SiliconRoot


def booted(loader="loader-v1", fw="governor-fw-v1", uds=b"\x11" * 32):
    r = SiliconRoot(Fuses(chip_id="feedface00000001", uds=uds))
    r.boot(digest(loader), digest(fw), 1)
    return r


@pytest.fixture
def ident():
    return spdm.GovernorIdentity(booted(), spdm.test_ca(), epoch=digest("epoch-7"))


def pair(ident, version, responder=None):
    r = responder or spdm.Responder(ident)
    return r, spdm.Requester(r.handle, ident.chain_ders[0], want_version=version)


@pytest.mark.parametrize("version", [spdm.V11, spdm.V12])
def test_attestation_round_trip_binds_the_registers(ident, version):
    _, q = pair(ident, version)
    out = q.attest(raw=True)
    m = out["measurements"]
    root = ident.root
    if version == spdm.V11:                      # 1.1 has no RawBitStreamRequested: digests
        assert m[1]["value"] == hashlib.sha384(bytes.fromhex(root.meas0.value)).hexdigest()
        assert m[2]["value"] == hashlib.sha384(bytes.fromhex(root.meas1.value)).hexdigest()
        assert not m[2]["raw"]
    else:                                        # 1.2 raw: the register contents themselves
        assert m[1]["value"] == root.meas0.value and m[2]["value"] == root.meas1.value and m[2]["raw"]
        assert m[3]["value"] == digest("epoch-7")
    assert out["version"] == f"1.{version & 0xF}"


def test_dice_binding_firmware_changes_alias_only_loader_changes_both():
    ca = spdm.test_ca()
    base = spdm.GovernorIdentity(booted(), ca)
    newfw = spdm.GovernorIdentity(booted(fw="governor-fw-v2"), ca)
    newld = spdm.GovernorIdentity(booted(loader="loader-v2"), ca)
    pub = lambda k: k.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    assert pub(base.device_id_key) == pub(newfw.device_id_key) and pub(base.alias_key) != pub(newfw.alias_key)
    assert pub(base.device_id_key) != pub(newld.device_id_key) and pub(base.alias_key) != pub(newld.alias_key)
    other_chip = spdm.GovernorIdentity(booted(uds=b"\x22" * 32), ca)
    assert pub(base.device_id_key) != pub(other_chip.device_id_key)


def test_alias_certificate_carries_the_firmware_measurement(ident):
    from govsim.hardware_ref.nvtrust import leaf_fwid
    leaf = x509.load_der_x509_certificate(ident.chain_ders[-1])
    assert leaf_fwid(leaf)[-32:] == bytes.fromhex(ident.root.meas1.value)
    assert not leaf.extensions.get_extension_for_class(x509.BasicConstraints).value.ca


def test_wrong_root_is_refused(ident):
    other = spdm.GovernorIdentity(booted(), spdm.p384_from_seed(b"\x01" * 32, b"another-ca"))
    r = spdm.Responder(ident)
    q = spdm.Requester(r.handle, other.chain_ders[0])
    q.vca()
    with pytest.raises(spdm.SpdmError, match="pinned root"):
        q.digests_and_chain()


def flip_last(code):
    def wrap(r):
        orig = r._handle

        def h(req):
            rsp = orig(req)
            if rsp[1] == code and len(rsp) > 100:
                rsp = rsp[:-1] + bytes([rsp[-1] ^ 0x01])
            return rsp
        r._handle = h
        return r
    return wrap


@pytest.mark.parametrize("fault,match", [
    (flip_last(spdm.CHALLENGE_AUTH), "CHALLENGE_AUTH signature"),
    (flip_last(spdm.MEASUREMENTS), "MEASUREMENTS signature"),
])
def test_corrupted_signatures_are_caught(ident, fault, match):
    r = fault(spdm.Responder(ident))
    q = spdm.Requester(r.handle, ident.chain_ders[0])
    with pytest.raises(spdm.SpdmError, match=match):
        q.attest()


def test_corrupted_certificate_is_caught(ident):
    r = spdm.Responder(ident)
    orig = r._handle

    def h(req):
        rsp = orig(req)
        if rsp[1] == spdm.CERTIFICATE:
            rsp = rsp[:-5] + bytes([rsp[-5] ^ 0x80]) + rsp[-4:]
        return rsp
    r._handle = h
    q = spdm.Requester(r.handle, ident.chain_ders[0])
    q.vca()
    with pytest.raises(spdm.SpdmError, match="digest"):
        q.digests_and_chain()


class NoVcaInTranscript(spdm.Responder):
    """A responder that forgets the VCA messages in M1 (a transcript bug)."""
    def _challenge(self, req):
        saved = self.message_a
        self.message_a = bytearray()
        try:
            return super()._challenge(req)
        finally:
            self.message_a = saved


def test_transcript_bug_is_caught(ident):
    r = NoVcaInTranscript(ident)
    q = spdm.Requester(r.handle, ident.chain_ders[0])
    with pytest.raises(spdm.SpdmError, match="CHALLENGE_AUTH signature"):
        q.attest()


def test_signing_context_matters_at_1_2(ident):
    """Signing a 1.2 response the 1.1 way (no signing context) must fail verification."""
    class OldStyle(spdm.Responder):
        def _measurements(self, req):
            v = self.version
            real = spdm.signing_input
            spdm.signing_input = lambda ver, ctx, t: real(spdm.V11, ctx, t)
            try:
                return super()._measurements(req)
            finally:
                spdm.signing_input = real
    r = OldStyle(ident)
    q = spdm.Requester(r.handle, ident.chain_ders[0], want_version=spdm.V12)
    with pytest.raises(spdm.SpdmError, match="MEASUREMENTS signature"):
        q.attest()


def test_protocol_errors(ident):
    r = spdm.Responder(ident)
    assert r.handle(bytes([0x11, spdm.GET_DIGESTS, 0, 0]))[1:3] == bytes([spdm.ERROR, spdm.ERR_UNEXPECTED_REQUEST])
    assert r.handle(bytes([0x11, spdm.GET_VERSION, 0, 0]))[1:3] == bytes([spdm.ERROR, spdm.ERR_VERSION_MISMATCH])
    assert r.handle(bytes([0x10, spdm.GET_VERSION, 0, 0]))[1] == spdm.VERSION
    bad = bytes([0x11, spdm.GET_CAPABILITIES, 0, 0, 0, 0, 0, 0]) + struct.pack("<I", 1 << 7)     # MAC without KEY_EX
    assert r.handle(bad)[1:3] == bytes([spdm.ERROR, spdm.ERR_INVALID_REQUEST])
    assert r.handle(bytes([0x13, spdm.GET_CAPABILITIES, 0, 0, 0, 0, 0, 0, 6, 0, 0, 0]))[1:3] == bytes([spdm.ERROR, spdm.ERR_VERSION_MISMATCH])
    ok = bytes([0x11, spdm.GET_CAPABILITIES, 0, 0, 0, 0, 0, 0]) + struct.pack("<I", 6)
    assert r.handle(ok)[1] == spdm.CAPABILITIES
    assert r.handle(bytes([0x11, spdm.GET_MEASUREMENTS, 0, 0]))[1:3] == bytes([spdm.ERROR, spdm.ERR_UNEXPECTED_REQUEST])


def test_ct_exponent_covers_a_p384_signature_on_the_governor():
    # docs/04-specification.md section 9: about 17 ms per P-384 signature on the OTBN-class engine
    assert (1 << spdm.CT_EXPONENT) >= 17_000


# ------------------------------------------------------------------ interop with DMTF's tools
needs_emu = pytest.mark.skipif(interop.bin_dir() is None, reason="spdm-emu binaries not built here; run python -m govsim.hardware_ref.interop --build")


@needs_emu
def test_interop_with_libspdm_and_the_dmtf_validator():
    ok, res = interop.run_all(interop.bin_dir())
    assert res["verdict"] == {k: True for k in res["verdict"]}, res["verdict"]
    assert res["runs"]["B"]["fail"] == 0 and res["runs"]["B"]["pass"] > 700
    assert ok
