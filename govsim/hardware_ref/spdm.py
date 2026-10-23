"""The governor as an SPDM responder (DMTF DSP0274, public), bound to its own measurement
registers and DICE identity, plus a requester that checks everything it is told.

Messages implemented (DSP0274 1.1.1 section numbers; 1.2 adds the signing context and the
VCA prefix on L1/L2):

    GET_VERSION / VERSION                  10.2
    GET_CAPABILITIES / CAPABILITIES        10.3
    NEGOTIATE_ALGORITHMS / ALGORITHMS      10.4
    GET_DIGESTS / DIGESTS                  10.7
    GET_CERTIFICATE / CERTIFICATE          10.8   (chain format 10.6.1)
    CHALLENGE / CHALLENGE_AUTH             10.9   (transcript M1/M2 10.9.2.1)
    GET_MEASUREMENTS / MEASUREMENTS        10.11  (block 10.11.1, DMTF field 10.11.1.1)
    ERROR                                  10.12

Byte layouts follow DSP0274 as implemented by DMTF's libspdm (include/industry_standard/spdm.h,
pinned in docs/interfaces/sources.csv). Algorithms: ECDSA P-384 with SHA-384 only, which is
what NVIDIA's GPUs use (the nvtrust sample is SPDM 1.1, P-384, SHA-384).

The binding to the governor (``GovernorIdentity``):
- CDI_0 and CDI_1 are recomputed exactly as ``govsim/root.py`` ``SiliconRoot.boot`` computes
  them (the fused secret, the loader measurement, the firmware measurement).
- The DeviceID key (P-384) is derived from CDI_0; the alias key (P-384), which signs SPDM
  responses, from CDI_1. A loader change changes both; a firmware change changes only the alias.
- The certificate chain is root CA (the provisioning authority; a test CA here), DeviceID
  certificate (CA, path length 0), alias certificate (leaf) carrying the firmware measurement
  in a TCG DICE FWID extension (OID 2.23.133.5.4.1, the one nvtrust's verifier reads).
- Measurement index 1 is meas0 (loader), 2 is meas1 (firmware), 3 the policy epoch, 4 the
  lifecycle state and firmware version. Values are SHA-384 digests of the raw register
  contents, or the raw contents when a 1.2 requester sets RawBitStreamRequested.

What this is not: the transport binding (MCTP over SMBus, or PCIe DOE) is not modelled; the
spdm-emu socket framing is used only to talk to DMTF's tools. No sessions (KEY_EXCHANGE).
"""
from __future__ import annotations

import datetime
import hashlib
import os
import socket
import struct
from dataclasses import dataclass, field

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
from cryptography.x509.oid import NameOID

from ..crypto import hkdf

# --------------------------------------------------------------------------- constants (DSP0274)
GET_VERSION, VERSION = 0x84, 0x04
GET_CAPABILITIES, CAPABILITIES = 0xE1, 0x61
NEGOTIATE_ALGORITHMS, ALGORITHMS = 0xE3, 0x63
GET_DIGESTS, DIGESTS = 0x81, 0x01
GET_CERTIFICATE, CERTIFICATE = 0x82, 0x02
CHALLENGE, CHALLENGE_AUTH = 0x83, 0x03
GET_MEASUREMENTS, MEASUREMENTS = 0xE0, 0x60
ERROR = 0x7F
ERR_INVALID_REQUEST, ERR_UNEXPECTED_REQUEST, ERR_UNSUPPORTED_REQUEST, ERR_VERSION_MISMATCH = 0x01, 0x04, 0x07, 0x41

V10, V11, V12 = 0x10, 0x11, 0x12
SUPPORTED = (V11, V12)
ASYM_ECDSA_P384 = 1 << 7          # BaseAsymAlgo bit 7
HASH_SHA384 = 1 << 1              # BaseHashAlgo bit 1
MEAS_HASH_SHA384 = 1 << 2         # MeasurementHashAlgo bit 2
MEAS_SPEC_DMTF = 0x01
CAP_CERT, CAP_CHAL, CAP_MEAS_SIG, CAP_MEAS_FRESH = 1 << 1, 1 << 2, 2 << 3, 1 << 5
RSP_FLAGS = CAP_CERT | CAP_CHAL | CAP_MEAS_SIG | CAP_MEAS_FRESH
# CT = 2^CTExponent us is the time to produce a signed response. docs/04-specification.md
# section 9: one P-384 signature takes about 17 ms on the OTBN-class engine. 2^15 us = 32.8 ms.
CT_EXPONENT = 15
H = 48                            # SHA-384
SIG = 96                          # P-384 r || s
NONCE = 32
MAX_PORTION = 1024
DATA_TRANSFER_SIZE = MAX_SPDM_MSG = 4096
SIGN_PREFIX = "dmtf-spdm-v{}.{}.*"
CTX_CHALLENGE = b"responder-challenge_auth signing"
CTX_MEASUREMENTS = b"responder-measurements signing"
TCG_DICE_FWID_OID = x509.ObjectIdentifier("2.23.133.5.4.1")
OID_SHA256 = bytes.fromhex("0609608648016503040201")     # DER of 2.16.840.1.101.3.4.2.1
P384_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC7634D81F4372DDF581A0DB248B0A77AECEC196ACCC52973

MEAS_TYPE_MUTABLE_FW, MEAS_TYPE_HW_CONFIG, MEAS_TYPE_FW_CONFIG = 0x01, 0x02, 0x03
MEAS_RAW = 0x80                   # DMTFSpecMeasurementValueType bit 7: raw bit stream


def sha384(b: bytes) -> bytes:
    return hashlib.sha384(b).digest()


def signing_input(version: int, context: bytes, transcript: bytes) -> bytes:
    """What the ECDSA signature covers. 1.0 and 1.1: the transcript itself. 1.2 and later: the
    100-byte signing context (the version prefix four times, zero pad, the context string)
    followed by the transcript hash."""
    if version <= V11:
        return transcript
    prefix = (SIGN_PREFIX.format(version >> 4, version & 0xF).encode()) * 4
    pad = b"\x00" * (36 - len(context))
    return prefix + pad + context + sha384(transcript)


def ecdsa_sign(key: ec.EllipticCurvePrivateKey, data: bytes) -> bytes:
    r, s = decode_dss_signature(key.sign(data, ec.ECDSA(hashes.SHA384())))
    return r.to_bytes(48, "big") + s.to_bytes(48, "big")


def ecdsa_verify(pub: ec.EllipticCurvePublicKey, sig: bytes, data: bytes) -> bool:
    if len(sig) != SIG:
        return False
    try:
        pub.verify(encode_dss_signature(int.from_bytes(sig[:48], "big"), int.from_bytes(sig[48:], "big")), data, ec.ECDSA(hashes.SHA384()))
        return True
    except InvalidSignature:
        return False


def p384_from_seed(seed: bytes, label: bytes) -> ec.EllipticCurvePrivateKey:
    d = int.from_bytes(hkdf(seed, b"spdm-p384:" + label, 64), "big") % (P384_N - 1) + 1
    return ec.derive_private_key(d, ec.SECP384R1())


def _der_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _tlv(tag: int, body: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(body)) + body


def dice_tcbinfo_fwid(fwid: bytes) -> bytes:
    """DiceTcbInfo ::= SEQUENCE { ..., fwids [6] IMPLICIT FWIDLIST, ... } with one FWID
    { hashAlg sha256, digest }. Only the fwids field is populated. The FWID digest is the last
    bytes of the extension value, which is where nvtrust's verifier looks."""
    fw = _tlv(0x30, OID_SHA256 + _tlv(0x04, fwid))
    return _tlv(0x30, _tlv(0xA6, fw))


# --------------------------------------------------------------------------- identity
@dataclass
class GovernorIdentity:
    """The governor's DICE identity as SPDM sees it, derived from a booted ``SiliconRoot``."""
    root: object                                   # govsim.root.SiliconRoot (booted)
    ca_key: ec.EllipticCurvePrivateKey             # the provisioning authority (test CA here)
    epoch: str = ""

    def __post_init__(self):
        r = self.root
        if not r.booted:
            raise RuntimeError("root not booted")
        # The same formula as govsim/root.py SiliconRoot.boot.
        self.cdi0 = r.fuses.derive(b"cdi0:" + bytes.fromhex(r.meas0.value))
        self.cdi1 = r.fuses.derive(b"cdi1:" + self.cdi0 + bytes.fromhex(r.meas1.value))
        self.device_id_key = p384_from_seed(self.cdi0, b"deviceid")
        self.alias_key = p384_from_seed(self.cdi1, b"alias")
        self.chain_ders = self._chain()
        root_der = self.chain_ders[0]
        body = sha384(root_der) + b"".join(self.chain_ders)
        self.cert_chain = struct.pack("<HH", 4 + len(body), 0) + body        # DSP0274 10.6.1

    def _chain(self) -> list[bytes]:
        now = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        far = datetime.datetime(9999, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
        chip = self.root.fuses.chip_id

        def name(cn: str) -> x509.Name:
            return x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Safety Governor model"), x509.NameAttribute(NameOID.COMMON_NAME, cn)])

        def ski(pub):
            return x509.SubjectKeyIdentifier.from_public_key(pub)

        ca_pub = self.ca_key.public_key()
        ca = (x509.CertificateBuilder().subject_name(name("Governor provisioning root (TEST)")).issuer_name(name("Governor provisioning root (TEST)"))
              .public_key(ca_pub).serial_number(1).not_valid_before(now).not_valid_after(far)
              .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
              .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
              .add_extension(ski(ca_pub), critical=False)
              .sign(self.ca_key, hashes.SHA384()))
        dev_pub = self.device_id_key.public_key()
        dev = (x509.CertificateBuilder().subject_name(name(f"Governor DeviceID {chip}")).issuer_name(ca.subject)
               .public_key(dev_pub).serial_number(int.from_bytes(sha384(self.cdi0)[:8], "big") >> 1).not_valid_before(now).not_valid_after(far)
               .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
               .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
               .add_extension(ski(dev_pub), critical=False)
               .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_pub), critical=False)
               .sign(self.ca_key, hashes.SHA384()))
        alias_pub = self.alias_key.public_key()
        fwid = bytes.fromhex(self.root.meas1.value)
        alias = (x509.CertificateBuilder().subject_name(name(f"Governor Alias {chip}")).issuer_name(dev.subject)
                 .public_key(alias_pub).serial_number(int.from_bytes(sha384(self.cdi1)[:8], "big") >> 1).not_valid_before(now).not_valid_after(far)
                 .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                 .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), critical=True)
                 .add_extension(x509.UnrecognizedExtension(TCG_DICE_FWID_OID, dice_tcbinfo_fwid(fwid)), critical=False)
                 .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(dev_pub), critical=False)
                 .sign(self.device_id_key, hashes.SHA384()))
        return [c.public_bytes(serialization.Encoding.DER) for c in (ca, dev, alias)]

    def raw_measurements(self) -> dict[int, tuple[int, bytes]]:
        r = self.root
        epoch = bytes.fromhex(self.epoch) if self.epoch else b"\x00" * 32
        lifecycle = str(r.fuses.lifecycle).encode() + b":" + struct.pack("<I", int(r.firmware_version))
        return {
            1: (MEAS_TYPE_MUTABLE_FW, bytes.fromhex(r.meas0.value)),
            2: (MEAS_TYPE_MUTABLE_FW, bytes.fromhex(r.meas1.value)),
            3: (MEAS_TYPE_FW_CONFIG, epoch),
            4: (MEAS_TYPE_HW_CONFIG, lifecycle),
        }


def measurement_block(index: int, mtype: int, raw: bytes, want_raw: bool) -> bytes:
    if want_raw:
        vtype, value = mtype | MEAS_RAW, raw
    else:
        vtype, value = mtype, sha384(raw)
    dmtf = struct.pack("<BH", vtype, len(value)) + value
    return struct.pack("<BBH", index, MEAS_SPEC_DMTF, len(dmtf)) + dmtf


def requester_flags_valid(flags: int, version: int) -> bool:
    """The GET_CAPABILITIES requester flag rules of DSP0274 (1.1 and 1.2), as libspdm encodes
    them in libspdm_check_request_flag_compatibility. Added after DMTF's SPDM-Responder-Validator
    failed test case 2.4 against the first version of this responder."""
    bit = lambda n, w=1: (flags >> n) & ((1 << w) - 1)
    cert, chal, enc, mac, mut, kex, psk = bit(1), bit(2), bit(6), bit(7), bit(8), bit(9), bit(10, 2)
    encap, hb, kupd, hsclear, pubkey = bit(12), bit(13), bit(14), bit(15), bit(16)
    if psk in (2, 3):
        return False
    if kex or psk:
        if not mac and not enc:
            return False
    elif mac or enc or hsclear or hb or kupd:
        return False
    if not kex and psk == 1 and hsclear:
        return False
    if cert or pubkey:
        if cert and pubkey:
            return False
        if not chal and not kex:
            return False
    elif chal or mut:
        return False
    if mut and not kex and not chal:
        return False
    if version == V11 and mut and not encap:
        return False
    return True


# --------------------------------------------------------------------------- responder
@dataclass
class Responder:
    ident: GovernorIdentity
    versions: tuple = SUPPORTED
    rng: object = os.urandom
    state: str = "start"
    version: int = V10
    message_a: bytearray = field(default_factory=bytearray)
    message_b: bytearray = field(default_factory=bytearray)
    message_m: bytearray = field(default_factory=bytearray)
    log: list = field(default_factory=list)

    def _err(self, code: int, data: int = 0) -> bytes:
        return bytes([self.version, ERROR, code, data])

    def handle(self, req: bytes) -> bytes:
        rsp = self._handle(req)
        self.log.append((req, rsp))
        return rsp

    def _handle(self, req: bytes) -> bytes:
        if len(req) < 4:
            return self._err(ERR_INVALID_REQUEST)
        ver, code = req[0], req[1]
        if code == GET_VERSION:
            if ver != V10 or len(req) != 4:
                self.version = V10
                return self._err(ERR_VERSION_MISMATCH if ver != V10 else ERR_INVALID_REQUEST)
            self.version = V10
            self.state = "version"
            self.message_a = bytearray(req)
            self.message_b.clear()
            self.message_m.clear()
            entries = b"".join(struct.pack("<H", v << 8) for v in self.versions)
            rsp = bytes([V10, VERSION, 0, 0, 0, len(self.versions)]) + entries
            self.message_a += rsp
            return rsp
        if self.state == "start":
            return self._err(ERR_UNEXPECTED_REQUEST)
        if code == GET_CAPABILITIES:
            return self._capabilities(req)
        if ver != self.version:
            return self._err(ERR_VERSION_MISMATCH)
        if code == NEGOTIATE_ALGORITHMS:
            return self._algorithms(req)
        if self.state != "negotiated":
            return self._err(ERR_UNEXPECTED_REQUEST)
        if code != GET_MEASUREMENTS:
            self.message_m.clear()
        if code == GET_DIGESTS:
            if len(req) != 4:
                return self._err(ERR_INVALID_REQUEST)
            rsp = bytes([self.version, DIGESTS, 0, 0x01]) + sha384(self.ident.cert_chain)
            self.message_b += req + rsp
            return rsp
        if code == GET_CERTIFICATE:
            return self._certificate(req)
        if code == CHALLENGE:
            return self._challenge(req)
        if code == GET_MEASUREMENTS:
            return self._measurements(req)
        return self._err(ERR_UNSUPPORTED_REQUEST, code)

    def _capabilities(self, req: bytes) -> bytes:
        ver = req[0]
        if self.state != "version":
            return self._err(ERR_UNEXPECTED_REQUEST)
        if ver not in self.versions:
            return self._err(ERR_VERSION_MISMATCH)
        want = 20 if ver >= V12 else 12
        if len(req) < want:
            return self._err(ERR_INVALID_REQUEST)
        flags = struct.unpack_from("<I", req, 8)[0]
        if not requester_flags_valid(flags, ver):
            return bytes([ver, ERROR, ERR_INVALID_REQUEST, 0])
        if ver >= V12:
            dts, mms = struct.unpack_from("<II", req, 12)
            chunk = bool(flags & (1 << 17))
            if dts < 42 or dts > mms or (not chunk and dts != mms):
                return bytes([ver, ERROR, ERR_INVALID_REQUEST, 0])
        self.version = ver
        rsp = bytes([ver, CAPABILITIES, 0, 0, 0, CT_EXPONENT, 0, 0]) + struct.pack("<I", RSP_FLAGS)
        if ver >= V12:
            rsp += struct.pack("<II", DATA_TRANSFER_SIZE, MAX_SPDM_MSG)
        self.message_a += req[:want] + rsp
        self.state = "capabilities"
        return rsp

    def _algorithms(self, req: bytes) -> bytes:
        if self.state != "capabilities":
            return self._err(ERR_UNEXPECTED_REQUEST)
        if len(req) < 32:
            return self._err(ERR_INVALID_REQUEST)
        n_struct = req[2]
        length, meas_spec = struct.unpack_from("<HB", req, 4)
        base_asym, base_hash = struct.unpack_from("<II", req, 8)
        ext_asym, ext_hash = req[28], req[29]
        if length != len(req) or length > 128:
            return self._err(ERR_INVALID_REQUEST)
        off = 32 + 4 * (ext_asym + ext_hash)
        types = []
        for _ in range(n_struct):
            if off + 4 > len(req):
                return self._err(ERR_INVALID_REQUEST)
            atype, count = req[off], req[off + 1]
            types.append(atype)
            off += 2 + (count >> 4) + 4 * (count & 0xF)
        if off != len(req):
            return self._err(ERR_INVALID_REQUEST)
        if not (base_asym & ASYM_ECDSA_P384) or not (base_hash & HASH_SHA384) or not (meas_spec & MEAS_SPEC_DMTF):
            return self._err(ERR_INVALID_REQUEST)        # no common algorithm
        structs = b"".join(bytes([t, 0x20, 0, 0]) for t in types)   # nothing selected: no key exchange here
        body = struct.pack("<BB", MEAS_SPEC_DMTF, 0) + struct.pack("<III", MEAS_HASH_SHA384, ASYM_ECDSA_P384, HASH_SHA384) + bytes(12) + bytes([0, 0, 0, 0]) + structs
        rsp = bytes([self.version, ALGORITHMS, len(types), 0]) + struct.pack("<H", 6 + len(body)) + body
        self.message_a += req + rsp
        self.state = "negotiated"
        return rsp

    def _certificate(self, req: bytes) -> bytes:
        if len(req) != 8:
            return self._err(ERR_INVALID_REQUEST)
        slot = req[2] & 0xF
        offset, length = struct.unpack_from("<HH", req, 4)
        chain = self.ident.cert_chain
        if slot != 0 or offset >= len(chain):
            return self._err(ERR_INVALID_REQUEST)
        portion = min(length, MAX_PORTION, len(chain) - offset)
        rsp = bytes([self.version, CERTIFICATE, slot, 0]) + struct.pack("<HH", portion, len(chain) - offset - portion) + chain[offset:offset + portion]
        self.message_b += req + rsp
        return rsp

    def _summary(self, kind: int) -> bytes:
        if kind == 0:
            return b""
        blocks = b"".join(measurement_block(i, t, raw, False) for i, (t, raw) in sorted(self.ident.raw_measurements().items())
                          if kind == 0xFF or (t & 0x7F) == 0x00)       # TCB: immutable ROM blocks only
        return sha384(blocks)

    def _challenge(self, req: bytes) -> bytes:
        if len(req) != 4 + NONCE:
            return self._err(ERR_INVALID_REQUEST)
        slot, kind = req[2] & 0xF, req[3]
        if slot != 0 or kind not in (0, 1, 0xFF):
            return self._err(ERR_INVALID_REQUEST)
        body = bytes([self.version, CHALLENGE_AUTH, slot, 0x01]) + sha384(self.ident.cert_chain) + self.rng(NONCE) + self._summary(kind) + struct.pack("<H", 0)
        m1 = bytes(self.message_a) + bytes(self.message_b) + req + body
        sig = ecdsa_sign(self.ident.alias_key, signing_input(self.version, CTX_CHALLENGE, m1))
        self.message_b.clear()
        return body + sig

    def _measurements(self, req: bytes) -> bytes:
        attrs, op = req[2], req[3]
        signed = bool(attrs & 0x01)
        want_raw = self.version >= V12 and bool(attrs & 0x02)
        need = 4 + (NONCE + 1 if signed else 0)
        if len(req) != need:
            return self._err(ERR_INVALID_REQUEST)
        if signed and (req[-1] & 0xF) != 0:
            return self._err(ERR_INVALID_REQUEST)
        meas = self.ident.raw_measurements()
        if op == 0:
            param1, record, nblocks = len(meas), b"", 0
        elif op == 0xFF:
            param1 = 0
            record = b"".join(measurement_block(i, t, raw, want_raw) for i, (t, raw) in sorted(meas.items()))
            nblocks = len(meas)
        elif op in meas:
            param1 = 0
            t, raw = meas[op]
            record, nblocks = measurement_block(op, t, raw, want_raw), 1
        else:
            return self._err(ERR_INVALID_REQUEST)
        body = bytes([self.version, MEASUREMENTS, param1, 0]) + bytes([nblocks]) + len(record).to_bytes(3, "little") + record
        body += self.rng(NONCE) + struct.pack("<H", 0)
        self.message_m += req
        if not signed:
            self.message_m += body
            return body
        l1 = (bytes(self.message_a) if self.version >= V12 else b"") + bytes(self.message_m) + body
        sig = ecdsa_sign(self.ident.alias_key, signing_input(self.version, CTX_MEASUREMENTS, l1))
        self.message_m.clear()
        return body + sig


# --------------------------------------------------------------------------- requester
class SpdmError(Exception):
    pass


@dataclass
class Requester:
    """Asks, and verifies everything: the chain against a pinned root, CHALLENGE_AUTH over M1,
    MEASUREMENTS over L1. ``send`` is a function bytes -> bytes (in-process or a socket)."""
    send: object
    trusted_root_der: bytes
    want_version: int | None = None
    version: int = V10
    message_a: bytearray = field(default_factory=bytearray)
    message_b: bytearray = field(default_factory=bytearray)
    message_m: bytearray = field(default_factory=bytearray)

    def _x(self, req: bytes, expect: int) -> bytes:
        rsp = self.send(req)
        if len(rsp) < 4:
            raise SpdmError("short response")
        if rsp[1] == ERROR:
            raise SpdmError(f"ERROR code 0x{rsp[2]:02x} data 0x{rsp[3]:02x} for request 0x{req[1]:02x}")
        if rsp[1] != expect:
            raise SpdmError(f"expected 0x{expect:02x}, got 0x{rsp[1]:02x}")
        if rsp[0] != (V10 if expect == VERSION else self.version):
            raise SpdmError(f"response version 0x{rsp[0]:02x}")
        return rsp

    def vca(self) -> int:
        req = bytes([V10, GET_VERSION, 0, 0])
        rsp = self._x(req, VERSION)
        n = rsp[5]
        offered = sorted({struct.unpack_from("<H", rsp, 6 + 2 * i)[0] >> 8 for i in range(n)})
        common = [v for v in offered if v in SUPPORTED and (self.want_version is None or v == self.want_version)]
        if not common:
            raise SpdmError(f"no common version in {offered}")
        self.version = max(common)
        self.message_a = bytearray(req + rsp)
        req = bytes([self.version, GET_CAPABILITIES, 0, 0, 0, 10, 0, 0]) + struct.pack("<I", CAP_CERT | CAP_CHAL)
        if self.version >= V12:
            req += struct.pack("<II", DATA_TRANSFER_SIZE, MAX_SPDM_MSG)
        rsp = self._x(req, CAPABILITIES)
        self.rsp_flags = struct.unpack_from("<I", rsp, 8)[0]
        self.message_a += req + rsp
        body = struct.pack("<BB", MEAS_SPEC_DMTF, 0) + struct.pack("<II", ASYM_ECDSA_P384, HASH_SHA384) + bytes(12) + bytes(4)
        req = bytes([self.version, NEGOTIATE_ALGORITHMS, 0, 0]) + struct.pack("<H", 6 + len(body)) + body
        rsp = self._x(req, ALGORITHMS)
        mh, asym, bh = struct.unpack_from("<III", rsp, 8)
        if asym != ASYM_ECDSA_P384 or bh != HASH_SHA384:
            raise SpdmError(f"responder chose asym 0x{asym:x} hash 0x{bh:x}")
        self.meas_hash = mh
        self.message_a += req + rsp
        return self.version

    def digests_and_chain(self) -> list[x509.Certificate]:
        req = bytes([self.version, GET_DIGESTS, 0, 0])
        rsp = self._x(req, DIGESTS)
        if not rsp[3] & 1:
            raise SpdmError("slot 0 empty")
        digest0 = rsp[4:4 + H]
        self.message_b = bytearray(req + rsp)
        chain, offset = b"", 0
        while True:
            req = bytes([self.version, GET_CERTIFICATE, 0, 0]) + struct.pack("<HH", offset, MAX_PORTION)
            rsp = self._x(req, CERTIFICATE)
            portion, remainder = struct.unpack_from("<HH", rsp, 4)
            chain += rsp[8:8 + portion]
            self.message_b += req + rsp
            offset += portion
            if remainder == 0:
                break
        if sha384(chain) != digest0:
            raise SpdmError("certificate chain does not match its digest")
        length = struct.unpack_from("<H", chain, 0)[0]
        if length != len(chain):
            raise SpdmError("certificate chain length field wrong")
        root_hash, ders = chain[4:4 + H], chain[4 + H:]
        certs = []
        while ders:
            if ders[0] != 0x30:
                raise SpdmError("bad DER")
            if ders[1] & 0x80:
                nl = ders[1] & 0x7F
                ln = 2 + nl + int.from_bytes(ders[2:2 + nl], "big")
            else:
                ln = 2 + ders[1]
            certs.append(x509.load_der_x509_certificate(ders[:ln]))
            ders = ders[ln:]
        if certs[0].public_bytes(serialization.Encoding.DER) != self.trusted_root_der or sha384(self.trusted_root_der) != root_hash:
            raise SpdmError("chain does not start at the pinned root")
        for parent, child in zip(certs, certs[1:]):
            try:
                child.verify_directly_issued_by(parent)
            except (ValueError, TypeError, InvalidSignature) as e:
                raise SpdmError(f"chain link broken at {child.subject.rfc4514_string()}: {e}")
        self.chain_raw, self.certs = chain, certs
        self.leaf_pub = certs[-1].public_key()
        return certs

    def challenge(self, kind: int = 0xFF) -> dict:
        nonce = os.urandom(NONCE)
        req = bytes([self.version, CHALLENGE, 0, kind]) + nonce
        rsp = self._x(req, CHALLENGE_AUTH)
        off = 4
        if rsp[off:off + H] != sha384(self.chain_raw):
            raise SpdmError("CHALLENGE_AUTH names a different chain")
        off += H + NONCE
        summary = rsp[off:off + (H if kind else 0)]
        off += len(summary)
        opaque_len = struct.unpack_from("<H", rsp, off)[0]
        off += 2 + opaque_len
        body, sig = rsp[:off], rsp[off:]
        m1 = bytes(self.message_a) + bytes(self.message_b) + req + body
        if not ecdsa_verify(self.leaf_pub, sig, signing_input(self.version, CTX_CHALLENGE, m1)):
            raise SpdmError("CHALLENGE_AUTH signature does not verify")
        self.message_b.clear()
        return {"summary": summary.hex()}

    def measurements(self, raw: bool = False) -> dict[int, dict]:
        """One signed GET_MEASUREMENTS for all indices."""
        nonce = os.urandom(NONCE)
        attrs = 0x01 | (0x02 if raw and self.version >= V12 else 0)
        req = bytes([self.version, GET_MEASUREMENTS, attrs, 0xFF]) + nonce + bytes([0])
        self.message_m.clear()
        rsp = self._x(req, MEASUREMENTS)
        nblocks = rsp[4]
        rec_len = int.from_bytes(rsp[5:8], "little")
        record = rsp[8:8 + rec_len]
        off = 8 + rec_len + NONCE
        opaque_len = struct.unpack_from("<H", rsp, off)[0]
        off += 2 + opaque_len
        body, sig = rsp[:off], rsp[off:]
        l1 = (bytes(self.message_a) if self.version >= V12 else b"") + req + body
        if not ecdsa_verify(self.leaf_pub, sig, signing_input(self.version, CTX_MEASUREMENTS, l1)):
            raise SpdmError("MEASUREMENTS signature does not verify")
        out, p = {}, 0
        for _ in range(nblocks):
            idx, spec, size = struct.unpack_from("<BBH", record, p)
            vtype, vsize = struct.unpack_from("<BH", record, p + 4)
            out[idx] = {"type": vtype, "raw": bool(vtype & MEAS_RAW), "value": record[p + 7:p + 7 + vsize].hex()}
            p += 4 + size
        if p != len(record):
            raise SpdmError("measurement record length mismatch")
        return out

    def attest(self, raw: bool = False) -> dict:
        self.vca()
        self.digests_and_chain()
        ch = self.challenge()
        return {"version": f"{self.version >> 4}.{self.version & 0xF}", "challenge": ch, "measurements": self.measurements(raw)}


# --------------------------------------------------------------------------- spdm-emu socket framing
SOCKET_NORMAL, SOCKET_SHUTDOWN, SOCKET_TEST = 0x0001, 0xFFFE, 0xDEAD
TRANSPORT_NONE = 0


def _recv_exact(s: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed")
        buf += chunk
    return buf


def emu_send(s: socket.socket, command: int, payload: bytes) -> None:
    s.sendall(struct.pack(">III", command, TRANSPORT_NONE, len(payload)) + payload)


def emu_recv(s: socket.socket) -> tuple[int, bytes]:
    command, transport, size = struct.unpack(">III", _recv_exact(s, 12))
    if transport != TRANSPORT_NONE:
        raise ConnectionError(f"transport type {transport}, expected NONE")
    return command, _recv_exact(s, size) if size else b""


def serve_emu(responder: Responder, port: int, ready=None, timeout: float = 60.0) -> list[str]:
    """Serve one spdm-emu requester connection (``--trans NONE``) until it shuts down."""
    events = []
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    srv.settimeout(timeout)
    if ready:
        ready.set()
    try:
        conn, _ = srv.accept()
        conn.settimeout(timeout)
        with conn:
            while True:
                cmd, payload = emu_recv(conn)
                if cmd == SOCKET_TEST:
                    emu_send(conn, SOCKET_TEST, b"Server Hello!\x00")
                elif cmd == SOCKET_NORMAL:
                    emu_send(conn, SOCKET_NORMAL, responder.handle(payload))
                elif cmd == SOCKET_SHUTDOWN:
                    emu_send(conn, SOCKET_SHUTDOWN, b"")
                    events.append("shutdown")
                    break
                else:
                    emu_send(conn, 0xFFFF, b"")
                    events.append(f"unknown command 0x{cmd:x}")
    finally:
        srv.close()
    return events


def emu_client(port: int, timeout: float = 30.0, wait: float = 10.0):
    """Connect to an spdm-emu responder, retrying until it listens (it serves one connection)."""
    import time
    deadline = time.monotonic() + wait
    while True:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
            break
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.1)

    def send(req: bytes) -> bytes:
        emu_send(s, SOCKET_NORMAL, req)
        cmd, rsp = emu_recv(s)
        if cmd != SOCKET_NORMAL:
            raise ConnectionError(f"socket command 0x{cmd:x}")
        return rsp

    def close():
        try:
            emu_send(s, SOCKET_SHUTDOWN, b"")
            emu_recv(s)
        finally:
            s.close()

    return send, close


def test_ca(seed: bytes = b"governor-test-provisioning-root") -> ec.EllipticCurvePrivateKey:
    """A deterministic TEST provisioning CA. Never a production key."""
    return p384_from_seed(hashlib.sha256(seed).digest(), b"test-ca")
