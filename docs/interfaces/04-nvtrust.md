# 04 · NVIDIA's GPU evidence into the governor (nvtrust)

> **Plain words first.** When an NVIDIA GPU runs in confidential-computing mode, its driver can hand out a signed report: a list of measurements of what the GPU booted, signed by a key burned into that GPU and certified by NVIDIA. NVIDIA publishes the code that checks those reports, and a real sample report, in its nvtrust repository. I wrote the governor's reader for that report and ran it on NVIDIA's sample. It reaches the same conclusions as NVIDIA's own checker, byte for byte, including where NVIDIA's own checker says the sample does not match NVIDIA's own test reference files. Some checks the governor cannot do on its own, like asking NVIDIA's servers whether a certificate was revoked, and I say which.
>
> **Backed by:** `govsim/hardware_ref/nvtrust.py` (the adapter), the new `_verify_gpu_nvidia` path in `govsim/governor.py`, NVIDIA's public sample in `tests/vectors/nvtrust/` (BSD-3-Clause, license file alongside), NVIDIA's verifier's own conclusions in `tests/vectors/nvtrust/nvtrust_oracle.json` (made by `tools/interfaces/nvtrust_oracle.py`), `tests/test_if_nvtrust.py`.

## 1. What NVIDIA's evidence is

From `guest_tools/gpu_verifiers/local_gpu_verifier` in nvtrust (`NVTRUST`, commit a8090b65):

- The "attestation report" is an SPDM 1.1 GET_MEASUREMENTS request (37 bytes, signature requested, all blocks, a 32-byte nonce) followed by the MEASUREMENTS response: 64 measurement blocks of 48 bytes, a responder nonce, NVIDIA's opaque data as (type, length, value) fields, and a 96-byte ECDSA P-384 signature.
- The signature covers request plus response without the signature, hashed with SHA-384.
- The certificate chain comes from the driver, leaf first, five certificates. NVIDIA's verifier throws away the root the device sends and uses its own pinned `verifier_device_root.pem`.
- The leaf certificate carries a TCG DICE FWID extension. On Hopper the last 48 bytes are the FWID, which must equal the report's FWID opaque field.

## 2. What the adapter checks, and how

| Check | How | Notes |
|---|---|---|
| Certificate chain to the pinned root | **cryptographic** | the pinned root comes from the governor's signed policy, not from the device |
| Report signature | **cryptographic** | ECDSA P-384 / SHA-384, leaf key |
| FWID binding | **cryptographic** | both sides are under signatures already checked |
| Nonce | **cryptographic**, then compared by the governor | the nonce is inside the signed bytes; the governor checks it is one it issued, and spends it |
| Measurements against golden values | **parsed and compared** | golden values come from the governor's signed policy |
| Driver and VBIOS version | **parsed and compared** | signed fields |
| RIM signatures (where golden values come from) | **not on the governor** | XML-DSig is checked off-chip, with nvtrust, when the policy is built |
| Revocation (OCSP) | **not done** | the governor has no network; the policy's revocation list is its only input |
| Certificate dates | **not done** | the governor has no trusted wall clock |
| Debug or CC-mode state | **not done** | no opaque field is publicly documented as a debug flag |
| Model manifest | **not available** | the report has no such field; it is the first ask to NVIDIA (`docs/03-interfaces.md` section 9). At the integrated tier the governor refuses NVIDIA reports until it exists |

`Evidence.checks` in the adapter returns exactly this table, so the governor's response says which checks were cryptographic and which were not.

## 3. Results on NVIDIA's sample

Everything below compares against `nvtrust_oracle.json`: NVIDIA's own `AttestationReport`, `CcAdminUtils.verify_gpu_certificate_chain`, `RIM` and `Verifier` classes run on the same bytes (nvtrust commit a8090b65, its `local_gpu_verifier` 2.7.3).

- Parse: nonce, 64 measurement values, FWID, driver version 550.90.07, VBIOS 96.00.9f.00.01, identical (`test_parse_agrees_with_nvidias_verifier`).
- Chain and signature: both say valid (`test_crypto_checks_agree_with_nvidias_verifier`).
- Tamper: flip byte 40 and both say the signature fails (`test_tampered_report_fails_like_nvidias_verifier`).
- Golden values: NVIDIA ships two test RIM files next to the sample. NVIDIA's verifier says the sample does **not** match them, at indices 1, 2, 3, 7, 9, 11, 21, 22, 25, 26, 27, 29, 30, 31, 32, 34, 36, 37, 39 and 40. The adapter gives the same list (`test_golden_comparison_reproduces_nvidias_result_on_its_own_test_rims`).

Through the governor's mailbox (`VERIFY_GPU` with `format: nvidia-spdm-1.1`), with the NVIDIA reference value delivered in a governance-signed epoch change:

- accepted when the policy's golden values are the sample's own measurements, with the result signed by the governor; a second use of the same nonce is refused (`test_verify_gpu_accepts_nvidias_sample_through_signed_policy`). Using the sample's own values as golden is circular on purpose: it tests the plumbing, not the GPU.
- refused against NVIDIA's test RIMs, as NVIDIA's verifier would (`test_verify_gpu_refuses_against_nvidias_test_rims`);
- refused for a nonce the governor did not issue, a flipped byte, a truncated report, a revoked GPU, a wrong driver version.

The public sample's nonce is fixed, so the tests add it to the governor's issued set by hand. A real run uses `Governor.nonce()`, the driver asks the GPU for a report over that nonce, and the host posts it to the mailbox.

## 4. What did not work

- NVIDIA's full command-line check (`cc_admin --test_no_gpu`) gets as far as "GPU attestation report certificate chain validation successful" and stops at "OCSP request failed": no route to NVIDIA's OCSP service from here. That is why the oracle drives NVIDIA's classes directly.
- NVIDIA's RIM signature check fails offline on both test RIM files with "certificate has expired" (the run date was 23 October 2026). So the public record does not let anyone, NVIDIA's code included, show golden values that are both signed and match this sample.
- NVIDIA's verifier pins lxml 4.9, which has no wheel for Python 3.13 and needs libxml2 headers to build; I installed it with `--no-deps` around lxml 5 and signxml 3.2.0. Logged in `tools/interfaces/nvtrust_oracle.py`.
- The repo ships only a Hopper sample. Blackwell uses a different FWID encoding (NVIDIA's code has a branch for it); untested here.
- I did not fabricate any NVIDIA-signed data. Every NVIDIA byte in `tests/vectors/nvtrust/` is NVIDIA's.
