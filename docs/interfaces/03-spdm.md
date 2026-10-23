# 03 · The governor speaks SPDM

> **Plain words first.** SPDM is the public standard (DMTF DSP0274) that server parts use to prove who they are and what firmware they run. NVIDIA's GPUs speak it. So the governor should too: a server maker's BMC, or a GPU's own verifier, should be able to ask the governor the same questions it asks a GPU and get answers signed by a key that only the governor's measured firmware can produce. I wrote the governor's side of that conversation in Python, tied to the governor's own measurement registers and boot identity, and then tested it against DMTF's own reference code and DMTF's own conformance test suite, built from source here. DMTF's test suite found a real bug in my first version. After the fix, 781 checks pass and none fail.
>
> **Backed by:** `govsim/hardware_ref/spdm.py` (responder, requester), `govsim/hardware_ref/interop.py` (the DMTF tool runs), `tests/test_if_spdm.py`, results in `docs/interfaces/results/spdm-interop.md`. One command: `python -m govsim.hardware_ref.interop` (add `--build` to clone and build DMTF's tools first).

## 1. What is implemented

| Message | DSP0274 1.1.1 section | Notes |
|---|---|---|
| GET_VERSION / VERSION | 10.2 | offers 1.1 and 1.2 |
| GET_CAPABILITIES / CAPABILITIES | 10.3 | CERT, CHAL, MEAS with signature, MEAS_FRESH. CTExponent 15 (32.8 ms), because one P-384 signature takes about 17 ms on the OTBN-class engine (`docs/04-specification.md` section 9). Rejects requester flag combinations the spec forbids, and bad 1.2 transfer sizes |
| NEGOTIATE_ALGORITHMS / ALGORITHMS | 10.4 | ECDSA P-384, SHA-384, DMTF measurement specification; what NVIDIA's GPUs use |
| GET_DIGESTS, GET_CERTIFICATE | 10.7, 10.8; chain format 10.6.1 | one slot; the chain is length, reserved, root hash, then DER certificates root first |
| CHALLENGE / CHALLENGE_AUTH | 10.9; transcript 10.9.2.1 | signed over M1 = VCA, digests and certificates, challenge. At 1.2 the signature covers the 100-byte signing context and the transcript hash |
| GET_MEASUREMENTS / MEASUREMENTS | 10.11; block 10.11.1; DMTF field 10.11.1.1 | signed over L1; at 1.2 L1 starts with VCA. SHA-384 digests, or the raw register bytes when a 1.2 requester sets RawBitStreamRequested |
| ERROR | 10.12 | InvalidRequest, UnexpectedRequest, UnsupportedRequest, VersionMismatch |

I could read the section map and the code table of DSP0274 1.1.1 but the text extractor truncated the body (`DSP0274_11`). The byte layouts follow DMTF's own C implementation, libspdm (`LIBSPDM`, pinned commit), and the interop runs are what check that I read it right.

## 2. Binding to the governor

- **Identity.** CDI_0 and CDI_1 are recomputed from the fused secret and the two measurement registers exactly as `govsim/root.py` computes them at boot. The DeviceID key (P-384) comes from CDI_0, the alias key from CDI_1. Change the loader and both keys change; change the firmware and only the alias key changes; another chip gives another DeviceID (`test_dice_binding_firmware_changes_alias_only_loader_changes_both`).
- **Certificates.** Root CA (the provisioning authority; a deterministic TEST CA here, never a production key), DeviceID certificate (CA, path length 0), alias certificate (leaf, digital signature only) with a TCG DICE FWID extension (OID 2.23.133.5.4.1) carrying the firmware measurement. That is the same OID NVIDIA's verifier reads on a GPU's leaf (`test_alias_certificate_carries_the_firmware_measurement`).
- **Measurements.** Index 1 is meas0 (loader), 2 is meas1 (firmware), 3 the policy epoch, 4 the lifecycle state and firmware version. These are the registers `rtl/governor_rtl/measure_reg.py` holds in silicon (`test_attestation_round_trip_binds_the_registers`).

Simplification: govsim signs everything else with Ed25519. SPDM here uses P-384, derived from the same CDIs, because that is what the GPU side uses and what the production silicon plans to use (`govsim/crypto.py` docstring).

## 3. Interop runs

DMTF's spdm-emu (`SPDMEMU`, commit f7fa1836) built from source here with mbedtls, which brings libspdm and the SPDM-Responder-Validator (`SPDMVAL`) as submodules. Talking over spdm-emu's socket framing with the NONE transport:

| Run | What | Result |
|---|---|---|
| A1 | libspdm requester to the governor responder, 1.1 | pass |
| A2 | same, 1.2, raw measurements, a signature on every GET_MEASUREMENTS | pass |
| A3 | A1 with one CHALLENGE_AUTH signature bit flipped | libspdm rejects (`do_authentication_via_spdm - 80020001`) |
| A4 | A1 with one MEASUREMENTS signature bit flipped | libspdm rejects (`do_measurement_via_spdm - 80010004`) |
| A5 | A1 with libspdm trusting its own sample root | libspdm logs `LIBSPDM_STATUS_VERIF_NO_AUTHORITY` and **exits 0** |
| B | DMTF SPDM-Responder-Validator to the governor responder | 781 assertions pass, 0 fail |
| C1, C2 | the governor's requester to libspdm's responder, 1.1 and 1.2 | pass, all 8 of libspdm's measurement blocks verified |
| C3 | the governor's requester trusting the wrong root | rejected |

A5 matters for anyone reusing spdm-emu as a test harness: its exit code says nothing about whether the chain reached a trusted root. Our harness checks the log line.

The negative controls (A3, A4, A5, C3) are why the passes mean something: the same harness with one planted fault turns into a failure, by libspdm's own verdict.

## 4. The validator found a bug

The first run against the validator: 773 pass, 5 fail, all in test case 2.4 (`spdm_test_case_capabilities_invalid_request`). My responder accepted a GET_CAPABILITIES whose requester flags the spec forbids (for example MAC or ENCRYPT without KEY_EX or PSK), and did not check 1.2's DataTransferSize rules. After it wrongly accepted the first one, its state machine answered the next ones with UnexpectedRequest instead of InvalidRequest. The log is kept: `docs/interfaces/results/spdm-validator-run1-before-fix.log`. The fix is `requester_flags_valid` in `spdm.py`, which follows libspdm's `libspdm_check_request_flag_compatibility`. Second run: 781 pass, 0 fail (`docs/interfaces/results/spdm-validator-latest.log`, rewritten by every interop run).

48 validator cases did not run, all because their setup needs something I do not implement: SPDM 1.0, 1.3 or 1.4, sessions (KEY_EXCHANGE, FINISH, HEARTBEAT, KEY_UPDATE, END_SESSION) and large responses. The list is in `docs/interfaces/results/spdm-interop.md`.

## 5. What is not done

- **Transport binding.** On a real board SPDM rides MCTP over SMBus/I2C or PCIe DOE. DMTF's binding specs are public; I did not read them for this work, and nothing here models them.
- **Sessions.** No KEY_EXCHANGE, so no encrypted channel.
- **Production CA.** Only the TEST CA exists.
- **Python is not the governor.** This is a model of the responder the firmware will run, tested against DMTF's code. The silicon has to be checked again when it exists.
