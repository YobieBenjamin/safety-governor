# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Run NVIDIA's own nvtrust local-verifier classes on NVIDIA's public Hopper sample and record what
they conclude, so govsim/hardware_ref/nvtrust.py can be compared against an independent
implementation (tests/test_if_nvtrust.py reads the output).

Not part of the test run: it needs NVIDIA's verifier installed in its own venv, because its pins
(cryptography 43, signxml 3.2, lxml) clash with this repo's. How it was run on 2026-10-23:

    git clone https://github.com/NVIDIA/nvtrust && git -C nvtrust checkout a8090b65872a15bf0fd1f69f3d9b754b1be431b5
    python3 -m venv nvv && nvv/bin/pip install --no-deps ./nvtrust/guest_tools/gpu_verifiers/local_gpu_verifier
    nvv/bin/pip install "lxml>=5.3,<6" "cryptography==43.0.1" "ecdsa==0.18.0" "signxml==3.2.0" "xmlschema==2.2.3" \
        "pyOpenSSL==24.2.1" "PyJWT==2.7.0" "nvidia-ml-py==12.550.52" "asn1==2.7.0" urllib3
    nvv/bin/python -I tools/interfaces/nvtrust_oracle.py a8090b65872a15bf0fd1f69f3d9b754b1be431b5 tests/vectors/nvtrust/nvtrust_oracle.json

Dead ends recorded: the pinned lxml 4.9 has no wheel for Python 3.13 (it needs libxml2 headers
to build), so lxml 5 was installed with --no-deps around it; signxml 5 is incompatible with
cryptography 43, so signxml 3.2.0 was pinned. NVIDIA's full cc_admin --test_no_gpu run stops at
"OCSP request failed" because this machine cannot reach NVIDIA's OCSP service, which is why the
oracle drives the verifier classes directly. NVIDIA's RIM signature check fails offline with
"certificate has expired" for the test RIMs shipped next to the sample.
"""
import json, sys
from hashlib import sha384
from verifier.config import BaseSettings, HopperSettings
from verifier.nvml.nvmlHandlerTest import NvmlHandlerTest
from verifier.attestation import AttestationReport
from verifier.cc_admin_utils import CcAdminUtils
from verifier.rim import RIM

s = HopperSettings()
h = NvmlHandlerTest(settings=s)
report_bytes = h.get_attestation_report()
chain = h.get_attestation_cert_chain()
ar = AttestationReport(report_bytes, s)
resp = ar.get_response_message()
od = resp.get_opaque_data()
fwid = od.get_data("OPAQUE_FIELD_ID_FWID").hex()
chain_ok, expired, _ = CcAdminUtils.verify_gpu_certificate_chain(chain, s, fwid)
sig_ok = ar.verify_signature(chain[0].to_cryptography(), s.signature_length, s.HashFunction)
meas = ar.get_measurements()
out = {
  "nvtrust_commit": sys.argv[1],
  "report_len": len(report_bytes),
  "request_nonce": ar.get_request_message().get_nonce().hex(),
  "chain_len": len(chain),
  "chain_ok": bool(chain_ok),
  "signature_ok": bool(sig_ok),
  "fwid": fwid,
  "driver_version": od.get_data("OPAQUE_FIELD_ID_DRIVER_VERSION").decode().rstrip("\0"),
  "vbios_version_raw": od.get_data("OPAQUE_FIELD_ID_VBIOS_VERSION").hex(),
  "n_measurements": len(meas),
  "measurements": {str(i): m for i, m in enumerate(meas)},
}
# tamper: flip one byte in the signed region and re-verify with NVIDIA's code
bad = bytearray(report_bytes); bad[40] ^= 1
ar_bad = AttestationReport(bytes(bad), s)
out["tampered_signature_ok"] = bool(ar_bad.verify_signature(chain[0].to_cryptography(), s.signature_length, s.HashFunction))
json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)

# RIMs: NVIDIA's own test_no_gpu RIM files, signature checked offline by NVIDIA's code
from verifier.verifier import Verifier
rims = {}
for name, path in (("driver", s.TEST_NO_GPU_DRIVER_RIM_PATH), ("vbios", s.TEST_NO_GPU_VBIOS_RIM_PATH)):
    rim = RIM(rim_name=name, settings=s, rim_path=path)
    entry = {"file": path.rsplit("/", 1)[-1]}
    try:
        entry["schema_ok"] = bool(rim.validate_schema())
    except Exception as e:
        entry["schema_ok"] = False; entry["schema_error"] = repr(e)
    try:
        entry["signature_ok"] = bool(rim.verify_signature(s))
    except Exception as e:
        entry["signature_ok"] = False; entry["signature_error"] = repr(e)
    try:
        rim.parse_measurements(s)
        entry["golden"] = {str(i): {"active": g.is_active(), "values": [g.get_value_at_index(k) for k in range(g.get_number_of_alternatives())]}
                           for i, g in rim.get_measurements().items()}
    except Exception as e:
        entry["parse_error"] = repr(e)
    rims[name] = (rim, entry)
out2 = {k: v[1] for k, v in rims.items()}
import logging, re
from verifier.config import info_log
captured = []
class _H(logging.Handler):
    def emit(self, record):
        captured.append(record.getMessage())
info_log.addHandler(_H())
try:
    vobj = Verifier(ar, rims["driver"][0], rims["vbios"][0], settings=s)
    out2["runtime_vs_golden_ok"] = bool(vobj.verify(s))
    out2["nvidia_mismatch_list"] = [int(m.group(1)) for line in captured for m in [re.match(r"\s*(\d+) \[(Firmware|Driver)\]", line)] if m]
except Exception as e:
    out2["runtime_vs_golden_ok"] = False; out2["runtime_vs_golden_error"] = repr(e)
d = json.load(open(sys.argv[2])); d["rims"] = out2
json.dump(d, open(sys.argv[2], "w"), indent=1, sort_keys=True)
