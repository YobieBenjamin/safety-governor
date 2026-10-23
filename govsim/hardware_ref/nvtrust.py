# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""NVIDIA GPU attestation evidence (the nvtrust format) turned into the governor's VERIFY_GPU input.

What the evidence is (read from NVIDIA's public nvtrust repo, commit pinned in
docs/interfaces/sources.csv as NVTRUST; guest_tools/gpu_verifiers/local_gpu_verifier):

- The "attestation report" is an SPDM 1.1 GET_MEASUREMENTS request (37 bytes: version 0x11,
  code 0xE0, Param1 bit 0 = signature requested, Param2 0xFF = all blocks, a 32-byte nonce, a
  slot byte) followed by the MEASUREMENTS response: measurement record, a responder nonce,
  NVIDIA opaque data as (type u16 LE, length u16 LE, value) fields, and a 96-byte ECDSA P-384
  signature (r || s).
- The signature covers request || response-without-signature, hashed with SHA-384 (nvtrust
  attestation/__init__.py ``concatenate`` and ``verify_signature``, HopperSettings.HashFunction).
- The certificate chain comes from the driver, leaf first. nvtrust drops the device-supplied
  root and appends its pinned ``verifier_device_root.pem``; we do the same, with the pinned root
  coming from the governor's signed policy.
- The leaf certificate carries a TCG DICE FWID extension (OID 2.23.133.5.4.1 / .1.1); on Hopper
  the FWID is its last 48 bytes and must equal the opaque OPAQUE_FIELD_ID_FWID (nvtrust
  cc_admin_utils ``extract_fwid``, ``verify_gpu_certificate_chain``).

What this adapter checks, and how (``Evidence.checks`` names each one):

    chain             CRYPTO   every certificate signed by the next, ending at the pinned root
    report_signature  CRYPTO   ECDSA P-384 / SHA-384 over request || response body, leaf key
    fwid_binding      CRYPTO   leaf FWID == report FWID (both under signatures checked above)
    nonce             CRYPTO   the request nonce is inside the signed bytes; equality to the
                               governor's own nonce is checked by the governor (VERIFY_GPU)
    measurements      PARSED   values are signed fields; comparison is against golden values the
                               governor's policy carries. Those golden values come from NVIDIA RIM
                               files whose XML-DSig signatures this adapter does NOT verify: that
                               happens when the policy is built, off-chip, with nvtrust itself.
    driver/vbios ver  PARSED   signed fields, compared as strings
    revocation        NOT DONE no OCSP on the governor (no network, no wall clock); the policy's
                               revocation list is the governor's only revocation input
    validity dates    NOT DONE the governor has no trusted wall clock; policy freshness stands in
    debug / CC mode   NOT DONE the opaque fields that might report it are not documented publicly
                               as a debug flag; the existing govsim "open_paths" check has no
                               NVIDIA equivalent we can point to
    model manifest    NOT AVAILABLE: no such field in the report (the ask to NVIDIA, docs/03 section 9)

Nothing here fabricates NVIDIA-signed data. The tests run on NVIDIA's own public sample
(tests/vectors/nvtrust/) and compare against what NVIDIA's own verifier classes conclude
(tests/vectors/nvtrust/nvtrust_oracle.json, produced by tools/interfaces/nvtrust_oracle.py).
"""
from __future__ import annotations

import hashlib
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from . import REPO

FORMAT = "nvidia-spdm-1.1"
VECTORS = REPO / "tests/vectors/nvtrust"
REQ_LEN = 37
SIG_LEN = 96
NONCE_LEN = 32
FWID_OIDS = ("2.23.133.5.4.1.1", "2.23.133.5.4.1")
OPAQUE_TYPES = {
    1: "CERT_ISSUER_NAME", 2: "CERT_AUTHORITY_KEY_IDENTIFIER", 3: "DRIVER_VERSION", 4: "GPU_INFO", 5: "SKU",
    6: "VBIOS_VERSION", 7: "MANUFACTURER_ID", 8: "TAMPER_DETECTION", 9: "SMC", 10: "VPR", 11: "NVDEC0_STATUS",
    12: "MSRSCNT", 13: "CPRINFO", 14: "BOARD_ID", 15: "CHIP_SKU", 16: "CHIP_SKU_MOD", 17: "PROJECT",
    18: "PROJECT_SKU", 19: "PROJECT_SKU_MOD", 20: "FWID", 21: "PROTECTED_PCIE_STATUS", 22: "SWITCH_PDI",
    23: "FLOORSWEPT_PORTS", 24: "POSITION_ID", 25: "LOCK_SWITCH_STATUS", 32: "GPU_LINK_CONN",
    33: "SYS_ENABLE_STATUS", 34: "OPAQUE_DATA_VERSION", 35: "CHIP_INFO", 36: "FEATURE_FLAG", 255: "INVALID",
}


class EvidenceError(Exception):
    pass


@dataclass
class Report:
    request: bytes
    response: bytes
    version: int
    nonce: bytes
    measurements: dict[int, bytes]          # block index (1-based, as on the wire) -> value
    opaque: dict[str, bytes]
    signature: bytes

    @property
    def signed_bytes(self) -> bytes:
        return self.request + self.response[:-SIG_LEN]


def load_hex_report(text: str) -> bytes:
    return bytes.fromhex(re.sub(r"\s+", "", text))


def parse_report(data: bytes) -> Report:
    if len(data) < REQ_LEN + 8 + SIG_LEN:
        raise EvidenceError("too short")
    req, rsp = data[:REQ_LEN], data[REQ_LEN:]
    if req[1] != 0xE0 or not (req[2] & 1):
        raise EvidenceError("not a signed GET_MEASUREMENTS request")
    if rsp[1] != 0x60 or rsp[0] != req[0]:
        raise EvidenceError("not a MEASUREMENTS response of the same version")
    nblocks = rsp[4]
    rec_len = int.from_bytes(rsp[5:8], "little")
    rec = rsp[8:8 + rec_len]
    meas, p = {}, 0
    for _ in range(nblocks):
        idx, spec, size = struct.unpack_from("<BBH", rec, p)
        vtype, vsize = struct.unpack_from("<BH", rec, p + 4)
        if spec != 1 or size != 3 + vsize:
            raise EvidenceError(f"block {idx}: not a DMTF measurement")
        meas[idx] = rec[p + 7:p + 7 + vsize]
        p += 4 + size
    if p != rec_len:
        raise EvidenceError("measurement record length mismatch")
    off = 8 + rec_len + NONCE_LEN
    olen = struct.unpack_from("<H", rsp, off)[0]
    opaque_raw = rsp[off + 2:off + 2 + olen]
    if off + 2 + olen + SIG_LEN != len(rsp):
        raise EvidenceError("response length does not leave exactly one P-384 signature")
    opaque, q = {}, 0
    while q < len(opaque_raw):
        t, n = struct.unpack_from("<HH", opaque_raw, q)
        opaque[OPAQUE_TYPES.get(t, f"TYPE_{t}")] = opaque_raw[q + 4:q + 4 + n]
        q += 4 + n
    return Report(req, rsp, req[0], req[4:4 + NONCE_LEN], meas, opaque, rsp[-SIG_LEN:])


def split_pem_chain(text: str) -> list[x509.Certificate]:
    return [x509.load_pem_x509_certificate(m.encode()) for m in re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", text, re.S)]


def leaf_fwid(cert: x509.Certificate) -> bytes:
    for ext in cert.extensions:
        if ext.oid.dotted_string in FWID_OIDS:
            return ext.value.value[-48:]
    return b""


def vbios_string(raw: bytes) -> str:
    """nvtrust's VBIOS formatting (utils ``format_vbios_version``), reimplemented: read the
    field little-endian, take the upper half, append the last byte of the lower half, dot it."""
    value = raw[::-1].hex()
    h = len(value) // 2
    temp = value[h:] + value[h - 2:h]
    return ".".join(temp[i:i + 2] for i in range(0, len(temp), 2))


@dataclass
class Evidence:
    report: Report
    chip_id: str
    checks: dict = field(default_factory=dict)        # name -> (ok, how)

    @property
    def ok(self) -> bool:
        return all(ok for ok, how in self.checks.values() if how == "CRYPTO")


def verify_evidence(report_bytes: bytes, chain_pem: str, pinned_root_pem: str) -> Evidence:
    rep = parse_report(report_bytes)
    certs = split_pem_chain(chain_pem)
    if not certs:
        raise EvidenceError("no certificates")
    pinned = x509.load_pem_x509_certificate(pinned_root_pem.encode())
    chain = certs[:-1] + [pinned]                    # nvtrust: device root dropped, pinned root appended
    ok_chain = True
    for child, parent in zip(chain, chain[1:]):
        try:
            child.verify_directly_issued_by(parent)
        except (ValueError, TypeError, InvalidSignature):
            ok_chain = False
    try:
        pinned.verify_directly_issued_by(pinned)
    except (ValueError, TypeError, InvalidSignature):
        ok_chain = False
    leaf = chain[0]
    pub = leaf.public_key()
    ok_sig = False
    if isinstance(pub, ec.EllipticCurvePublicKey) and pub.curve.name == "secp384r1":
        der = encode_dss_signature(int.from_bytes(rep.signature[:48], "big"), int.from_bytes(rep.signature[48:], "big"))
        try:
            pub.verify(der, rep.signed_bytes, ec.ECDSA(hashes.SHA384()))
            ok_sig = True
        except InvalidSignature:
            ok_sig = False
    rfwid = rep.opaque.get("FWID", b"")
    ok_fwid = bool(rfwid) and leaf_fwid(leaf) == rfwid
    ev = Evidence(rep, chip_id="nv-" + format(leaf.serial_number, "x"))
    ev.checks = {
        "chain": (ok_chain, "CRYPTO"),
        "report_signature": (ok_sig, "CRYPTO"),
        "fwid_binding": (ok_fwid, "CRYPTO"),
        "measurements": (True, "PARSED"),
        "driver_version": (True, "PARSED"),
        "vbios_version": (True, "PARSED"),
        "revocation": (False, "NOT DONE"),
        "validity_dates": (False, "NOT DONE"),
        "debug_state": (False, "NOT DONE"),
        "model_manifest": (False, "NOT AVAILABLE"),
    }
    return ev


def golden_mismatches(measurements: dict[int, bytes], golden: dict[int, list[str]]) -> list[int]:
    """Golden indices (0-based, as RIM files and nvtrust number them) whose runtime value matches
    none of the alternatives. Runtime block i+1 is golden index i."""
    bad = []
    for i, values in sorted(golden.items()):
        rt = measurements.get(int(i) + 1, b"").hex()
        if rt not in [v.lower() for v in values]:
            bad.append(int(i))
    return bad


def parse_rim_golden(xml_text: str) -> dict[int, list[str]]:
    """Active golden measurements from an NVIDIA RIM (SWID tag) file. PARSED ONLY: the XML-DSig
    signature is not checked here (see the module docstring)."""
    import xml.etree.ElementTree as ET
    ns_hash = "{http://www.w3.org/2001/04/xmlenc#sha384}"
    root = ET.fromstring(xml_text)
    out: dict[int, list[str]] = {}
    for el in root.iter():
        if el.tag.endswith("Resource") and "index" in el.attrib:
            if el.attrib.get("active") == "False":
                continue
            n = int(el.attrib.get("alternatives", "1"))
            out[int(el.attrib["index"])] = [el.attrib[ns_hash + f"Hash{k}"] for k in range(n)]
    return out


def verify_gpu_body(report_bytes: bytes, chain_pem: str) -> dict:
    """The VERIFY_GPU mailbox body for NVIDIA evidence: the raw bytes, as the driver hands them over."""
    return {"format": FORMAT, "report": report_bytes.hex(), "cert_chain": chain_pem}


def reference_value(pinned_root_pem: str, golden: dict[int, list[str]], valid_until: float, driver_version: str | None = None,
                    vbios_version: str | None = None) -> dict:
    """A policy reference-value record for NVIDIA GPUs (the governor's existing reference_values list)."""
    return {"device_class": "gpu", "format": FORMAT, "root_pem": pinned_root_pem,
            "root_sha384": hashlib.sha384(x509.load_pem_x509_certificate(pinned_root_pem.encode()).public_bytes(serialization.Encoding.DER)).hexdigest(),
            "golden": {str(k): v for k, v in golden.items()}, "driver_version": driver_version, "vbios_version": vbios_version,
            "valid_until": valid_until}


def sample() -> tuple[bytes, str, str]:
    """NVIDIA's public Hopper sample: report bytes, certificate chain PEM, pinned device root PEM."""
    return (load_hex_report((VECTORS / "hopperAttestationReport.txt").read_text()),
            (VECTORS / "hopperCertChain.txt").read_text(),
            (VECTORS / "verifier_device_root.pem").read_text())


def summary() -> dict:
    rep, chain, root = sample()
    ev = verify_evidence(rep, chain, root)
    return {"chip_id": ev.chip_id, "nonce": ev.report.nonce.hex(), "checks": {k: f"{'ok' if ok else 'no'} ({how})" for k, (ok, how) in ev.checks.items()},
            "driver_version": ev.report.opaque.get("DRIVER_VERSION", b"").decode(errors="replace").rstrip("\x00"),
            "vbios_version": vbios_string(ev.report.opaque.get("VBIOS_VERSION", b"")), "blocks": len(ev.report.measurements)}


if __name__ == "__main__":
    import json
    print(json.dumps(summary(), indent=1))
