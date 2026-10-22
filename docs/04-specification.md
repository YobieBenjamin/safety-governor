# 04 · Specification

This is the implementable description: registers, formats, timing, crypto, firmware,
memory budgets and physical targets. The functional model in `govsim/` and the RTL in
`rtl/governor_rtl/` follow it; where they simplify, the simplification is named.

> **In plain words:** this is the part an engineer builds from: the exact registers, message
> formats, rulebook format, key hierarchy, timers, memory sizes and physical targets. Nothing
> here is new; it pins down what the architecture says so that the model, the hardware and
> the tests cannot drift apart.
> **Plain-English version:** `10-plain-english-walkthrough.md` §8, §9 and §14.
> **Backed by:** model `govsim/governor.py` (`command` and one `_cmd_*` handler per mailbox
> code), `govsim/policy.py` (the policy image, k-of-n), `govsim/ledger.py`, `govsim/crypto.py`,
> `govsim/bench.py` (the timing budgets priced); tests `tests/test_h00_contract.py`,
> `test_h03_quorum.py`, `test_h04_lane.py`, `test_h08_override.py`, `test_h09_overhead.py`;
> hardware `rtl/governor_rtl/mailbox.py`, `ticket_store.py`, `meter.py`, `top.py` (the CSR
> window).

## 1. Conventions

- All multi-byte fields are little-endian. All hashes are SHA-256 unless stated. Production
  signatures are ECDSA P-384 over SHA-384: that is the curve the NVIDIA GPU attestation chain
  uses (the local verifier in NVIDIA's nvtrust checks 96-byte signatures with SHA-384) and the
  curve AMD's SEV-SNP VCEK uses, so the governor's verifier needs it anyway, and using it for
  the governor's own signatures keeps one engine. The functional model uses Ed25519 (64-byte
  signatures) for speed of implementation; a P-384 signature is 96 bytes. The architecture does
  not depend on the curve.
- "Durable" means written to the governor's authenticated NVM before the operation returns.
- Reason codes are strings in the model and 16-bit codes in silicon; the mapping is in
  `govsim/reasons.py`.
- Time is the governor's monotonic counter (64-bit, 1 µs ticks, never decremented, persisted
  across power loss with a fuse-backed high-water mark). The model ticks and persists it in
  `Governor.tick()` and stamps fabric messages, records, rosters and tickets with it. Wall time
  is advisory and comes from signed heartbeats; ticket validity windows are in the endpoint's
  clock because the endpoint is what compares them.

## 2. Register map (control and status, CSR bus, 32-bit)

The host sees exactly one BAR: the mailbox doorbell, the response ring, and read-only status.
Everything else below is internal to the governor's firmware and listed so the RTL and the
verification plan agree.

| Offset | Name | Access | Bits | Meaning |
|---|---|---|---|---|
| 0x000 | `ID` | RO | 32 | Silicon id and revision |
| 0x004 | `LIFECYCLE` | RO | 2 | 0 test, 1 provisioned, 2 production, 3 decommissioned (fuse-backed, monotone) |
| 0x008 | `STATE` | RO | 3 | 0 HALTED_INITIAL, 1 RUN, 2 THROTTLE, 3 HALT, 4 SAFE (the safe-mode sequencer's rungs; firmware boot happens before the first state is visible) |
| 0x00C | `CAUSE` | RO | 16 | Bits 2:0 the sequencer's own summary (0 none, 1 loop, 2 local, 3 tamper, 4 command); bits 15:8 the firmware's reason code from `govsim/reasons.py` |
| 0x010 | `EPOCH[0..7]` | RO | 256 | Policy epoch (digest of the accepted policy image) |
| 0x030 | `MEAS0[0..7]` | RO | 256 | Measurement register 0 (loader); extend-only |
| 0x050 | `MEAS1[0..7]` | RO | 256 | Measurement register 1 (firmware); extend-only |
| 0x070 | `MONO_LO`, `MONO_HI` | RO | 64 | Monotonic counter |
| 0x078 | `HB_REMAIN` | RO | 32 | Heartbeat time remaining, milliseconds |
| 0x07C | `LOOP` | RO | 2 | bit 0 loop current sensed, bit 1 own switch open |
| 0x080 | `LEVERS` | RO | 3 | bit 0 power brake asserted, bit 1 PERST# asserted, bit 2 PWR_EN low |
| 0x084 | `ALARMS` | RO | 32 | Sticky alarm bits (monotone; cleared only through the clear path) |
| 0x100 | `MBOX_DOORBELL` | WO (host) | 32 | Length of the command frame placed in the inbound ring |
| 0x104 | `MBOX_STATUS` | RO | 8 | 0 idle, 1 busy, 2 ok, 3 bad signature, 4 bad sequence, 5 bad epoch, 6 refused |
| 0x108 | `MBOX_SEQ` | RO | 32 | Last accepted inbound sequence number (key slot 0; one counter per signer key) |
| 0x200 | `METER_SLOT[n]` | RO | 4×64 per slot | tokens, kernel cycles, bytes in, bytes out, per model digest slot (16 slots) |
| 0x400 | `LOG_HEAD[0..7]` | RO | 256 | Current log head (firmware-mapped: the log engine is firmware over NVM, so the RTL core does not decode it) |
| 0x420 | `LOG_SIZE` | RO | 64 | Entries in the log (firmware-mapped) |

There is no writable register other than the doorbell. Configuration, policy, keys and
clears all arrive as signed mailbox commands. In plain words: the security office has one
letter slot and no light switches on the outside wall.

## 3. Mailbox commands

Frame: `{seq: u32, epoch: 32 bytes, cmd: u16, body: bytes, sig: 96 bytes (P-384; 64 in the
Ed25519 model)}`. The signature is by a key the policy names for that command class. The
mailbox checks, in order: sequence number greater than the last accepted one for that signer
key, epoch equal to `EPOCH` (except the epoch-exempt commands `POLICY_PROPOSE`,
`POLICY_COMMIT`, `ATTEST`, `HALT`, `CLEAR` and `ALARM_CLEAR`, which move, repair or inspect the
epoch itself and must work when it is stale), then the signature. The first failing check is
the reason reported; the model (`_check_signed`) and the RTL (`mailbox.py`) check in the same
order and a test in each suite pins it. Only then is the command dispatched. Commands that
carry their own authentication in the body (an attestation report, a k-of-n signed policy
image) are accepted without a frame signature and say so below.

| Code | Command | Signer class | Body | Effect |
|---|---|---|---|---|
| 0x01 | `ATTEST` | anyone | nonce | Returns the governor's quote: measurements, epoch, lifecycle, counters, over the nonce |
| 0x02 | `VERIFY_GPU` | host (unsigned; the report authenticates itself; the result is a governor-signed envelope) | GPU attestation report, governor nonce | Verifier checks the report; on success stores the GPU measurement for the job |
| 0x03 | `VERIFY_HOST` | host (unsigned; the report authenticates itself) | CPU TEE report | As above for the host enclave; establishes the host enclave key that signs `REQUEST`, `CAP_REQUEST` and `ROSTER_JOIN` |
| 0x04 | `BEGIN_MODEL` | verified loader | publisher-signed manifest | Verifies manifest signature against the policy's publisher keys; extends the fingerprint with the manifest digest; returns the wrapped model key |
| 0x05 | `END_MODEL` | verified loader | model digest | Freezes the meter slot for that model |
| 0x06 | `REQUEST` | verified host enclave (fresh attestation required) | typed request (§5) | Gate core; returns a ticket, a hold id, or a refusal |
| 0x07 | `APPROVE` | approver | hold id, request hash | Releases a hold if the policy quorum for that rule is met |
| 0x08 | `COMMIT` | endpoint (signed with the endpoint's key) | ticket id | Commits the reservation; the governor refuses a stale-epoch ticket and refuses while not in RUN |
| 0x09 | `SIGN_OUTPUT` | verified runtime | stream id, claimed prompt hash, nonce | Returns the device-provenance record (§6) |
| 0x0A | `CAP_REQUEST` | verified host enclave (fresh attestation required) | point, peer, direction, byte budget, ttl | Capability or refusal; the governor programs the switch. The peer `host` is accepted only on the PCIe point, never on NVSwitch, DPU or storage |
| 0x0B | `ROSTER_JOIN` | verified host enclave | job id | The governor broadcasts its quote on the fabric; roster formation follows (`02-safety-fabric.md`) |
| 0x0C | `POLICY_PROPOSE` | policy authority (frame unsigned; the image carries its k-of-n signatures, which the governor verifies itself) | image, version, expiry, signatures | Stage the image; the governor records when it staged it |
| 0x0D | `POLICY_COMMIT` | policy authority (as above) | image digest | Switch the epoch (the rack-wide rule in `02`) |
| 0x0E | `HEARTBEAT` | policy authority | validity window, epoch | Reloads the heartbeat timer |
| 0x0F | `HALT` / `THROTTLE` | policy authority | rung, cause | Assert the lever |
| 0x10 | `CLEAR` | policy authority | none in the model (the governor checks its own record of which log head a neighbor acknowledged) | Clear the cause if it is in the log and a fabric neighbor has acknowledged the checkpoint that contains it; close the loop switch if no cause remains |
| 0x11 | `LOG_CHECKPOINT` | anyone | none | Signed Merkle root, size, head, neighbor heads |
| 0x12 | `COUNTERS` | anyone | model digest | Meter readout |
| 0x13 | `EXCEPTION_DRAIN` | firmware | none | Refusals at every governed switch since the last drain, handed to the log |
| 0x14 | `ALARM_RAISE` | anyone | cause, request hash, evidence digest | Raises a sticky alarm (any party may) |
| 0x15 | `ALARM_CLEAR` | the policy's alarm approver key | cause | Clears an alarm; logged |

## 4. The policy image

```
PolicyImage {
  version: u32,                  // strictly increasing; the anti-rollback counter tracks it
  issued_at, expires_at: u64,
  governance_keys: [key],         // n keys; threshold k
  threshold: u8,
  approver_keys: {rule_id: [key], quorum: u8},
  heartbeat_key: key,
  publisher_keys: [key],          // may sign model manifests
  reference_values: [{device_class, firmware_digest, valid_until}],
  revocations: [chip_id | key_id],
  endpoints: [{name, pubkey, safe_transition}],
  observer_keys: [key],           // witnesses whose verdicts the observer lane accepts
  budget_owners: {budget_key: governor_chip_id},   // every budget key a rule names must have an owner; no default
  rules: [Rule],
  assumptions: [RegisterRow],     // 06-assumptions-register.md; load fails if a rule input lacks a row
  override_floor_s: 60,           // never below 10
  safe_mode: {default_rung, T_throttle_s, T_halt_s, causes: {cause_code: first_rung}},
  fabric: {heartbeat_expiry_s, max_hops, epoch_deadline_s, loop_bound_s},
  signatures: [sig]              // k-of-n over everything above
}

Rule {
  id, measurement (a workload measurement, or "*" for any verified workload), action,
  constraints: {param: {min,max} | {in_list: list_id} | {not_in_list: list_id} | {digest_of: list_id}},
  requirement: {mode: auto|observer|human, observers: [key_id], max_risk, approvers_quorum},
  rate: {max, window_s},
  budget: {key, param, limit, window_s},
  output_budget: {queries, bytes, window_s, unpresented_bytes},
  endpoint: name | null,
  delay_s,
  inputs: [input_name]           // register rows declared by the author, in addition to the derived ones
}
```

The epoch is `SHA-256(canonical(PolicyImage without signatures))`. Rules are keyed by the
**workload measurement** `H(gpu_firmware, host_firmware, model_manifest)`; an exact rule beats
a wildcard. The **fingerprint** `H(workload, epoch)` binds tokens, tickets and request hashes
to the policy edition as well (a rule cannot be keyed by the fingerprint because the
fingerprint contains the epoch of the image the rule is in). The loader derives the inputs a
rule relies on from its constraints (`in_list`, `not_in_list`, `digest_of`), its observers and
its budget key, unions them with the declared `inputs`, and refuses an image in which any of
them lacks a row in `assumptions` (R-H7), or in which a budget key has no `budget_owners` row.
The heartbeat period is the authority's own configuration and is not a governor policy field;
the governor enforces only `heartbeat_expiry_s`.

## 5. Typed request, ticket, capability

![One request through the gate](figures/fig-request.png)

```
Request {request_id, measurement_token, action, params{...}, witnesses: [Assertion]}
   request_hash = SHA-256(canonical(request_id, fingerprint, action, params))

Ticket {ticket_id (random 128-bit), request_hash, action, params_digest, measurement, rule,
        policy_epoch, endpoint, budget_key, budget_owner, reservation, issued_at (monotonic counter),
        valid_from, expires_at (endpoint clock), sig_governor}

Capability (32 bytes packed) {
   point: u8      // rack tier: 0 NVSwitch port, 1 PCIe switch port, 2 DPU flow, 3 storage path;
                  // integrated tier adds 4 copy engine, 5 peer MMU
   peer: u64      // roster member id, host enclave id, manifest id or flow id
   dir: u2        // in, out, both
   budget: u40    // bytes
   expiry: u32    // monotonic ticks (coarse)
   epoch_tag: u16 // low bits of the epoch
   mac: u64       // truncated HMAC under the controller key
}
```

The capability table is a content-addressable memory keyed on `(point, peer, dir)`; a lookup
decrements `budget` and refuses at zero, on expiry, or on an epoch-tag mismatch. The MAC is
checked at insertion, not per lookup; the table itself is inside the governor's domain. The
product target is 256 entries per point with the field widths above; the prototype core that
`make gds` hardens instantiates the Amaranth defaults (8 entries per point, 16-bit peer, 24-bit
budget, 32-bit ticket id, 8-bit command, 4 meter slots of 48 bits) so that the invariants are
proven on a small die first. The sizes are parameters of `GovernorCore`. At the rack tier the table is the governor's
source of truth for what it has programmed into the switches: a port or flow is open in the
switch exactly when a matching, unexpired entry exists, and the governor re-derives the
switch configuration from the table after any epoch, roster or heartbeat event.

## 6. Device-provenance record

```
Record {chip_id, fw_measurement, model_digest, policy_epoch, roster_id,
        prompt_hash (as claimed by the runtime), prompt_hash_verified: false,
        output_hash, output_hash_inline (true only at the integrated tier),
        nonce, time (monotonic counter), counters{tokens, cycles, bytes_in, bytes_out}, sig_governor}
```

It establishes device provenance only. Workload provenance is the verified runtime's own
record; execution integrity is research. The blog's three-claim table applies.

## 7. Crypto suite and key hierarchy

| Need | Primitive | Implementation note |
|---|---|---|
| Hashing, measurement, log chain | SHA-256 | Hardware engine; also hashes what the verified runtime presents for signing |
| MAC for capabilities, NVM authentication | HMAC-SHA-256 | Same engine |
| Signatures | ECDSA P-384 over SHA-384 (what the NVIDIA GPU attestation chain and SEV-SNP use); P-256 for TPM-class endpoints | OTBN-class big-number coprocessor. OpenTitan's OTBN library carries ECDSA P-256 and P-384, Ed25519 and X25519, RSA, SHA-256/512 and SHA-3/SHAKE programs; ML-DSA and ML-KEM are being built for the next OTBN generation (larger memories, SIMD, a KMAC interface) and are not in Earl Grey silicon. Constant time. Cost: see §9 |
| NVM encryption and authentication | AES-256-CTR with HMAC-SHA-256 (encrypt-then-MAC) | OpenTitan's AES block does ECB, CBC, CFB, OFB and CTR and has no GCM; the MAC comes from the HMAC engine |
| Randomness | TRNG (ring-oscillator entropy source with health tests) feeding a DRBG | Health tests per SP 800-90B |
| Key derivation | HKDF-SHA-256 | Hardware or firmware |

Key hierarchy:

```
UDS (fuses, 256 bits)
 └─ CDI_0 = KDF(UDS, MEAS0)                 // loader identity
     └─ CDI_1 = KDF(CDI_0, MEAS1)            // firmware identity (DICE layer 1)
         ├─ K_sign = KDF(CDI_1, "sign")      // quotes, tickets, records, checkpoints, fabric
         ├─ K_nvm  = KDF(CDI_1, "nvm")       // NVM encryption and authentication
         ├─ K_cap  = KDF(CDI_1, "cap")       // capability MACs
         └─ K_wrap = KDF(CDI_1, "wrap")      // model key wrapping to verified enclaves
```

A firmware change changes CDI_1 and every key under it. Outstanding tickets from the old
firmware fail to verify, which is the intended behaviour: an upgrade is an epoch event.

## 8. Control firmware

- Size target: under 10,000 lines of C or Rust, no dynamic allocation, no interrupt-driven
  data path. Verified-kernel class: the proof assumptions (hardware model, DMA absence, the
  crypto engines' correctness) are written down in `07-verification-plan.md`.
- Responsibilities: mailbox dispatch, verifier, gate core, ledger, policy loading, fabric
  protocol, log engine, safe-mode sequencing.
- Not responsible for: any per-token or per-transfer work. The checkers, the hash engine and
  the meter run without firmware involvement.
- Update: signed by the governance root, measured at boot, gated by the anti-rollback counter.

## 9. Timing parameters (defaults; policy may tighten)

| Parameter | Default | Bound |
|---|---|---|
| Mailbox command, `auto` rule, ticket minted | 20 µs (firmware) / 2 µs (hard gate core) | 100 µs |
| Capability lookup | 1 cycle at the checker clock | hidden in the switch's own port logic; the governor programs ports, it does not sit on them |
| Switch port open or close after a roster, epoch or heartbeat event | 1 ms (management-bus write) | 10 ms |
| Device-provenance signature | 17 ms per ECDSA P-384 signature on an OTBN-class coprocessor at 100 MHz: OpenTitan's published OTBN figure is 1,697,985 cycles for a constant-time P-384 sign (704,126 for P-256, 7 ms). Per-response signing would therefore cap at about 59 responses per second per engine, so records are batched: one signature per batch window over a Merkle root of the records in the window, each record carrying its path. The window must be longer than the signature; default 50 ms. The engine is shared by every slot the governor chip serves and at a 50 ms window is busy at most 34 percent of the time whatever the load. The record trails the response; a runtime that waits for it before releasing a response adds at most window plus signature, 67 ms. A dedicated ECC engine would shorten all of this; none is assumed | window above 17 ms; engine utilization under 50 percent |
| Post-quantum hybrid signature (C3) | A hybrid signature per batch: ECDSA P-384 plus ML-DSA-65 (Dilithium3), both on the one OTBN-class engine. ML-DSA is not in Earl Grey silicon and no OTBN-specific measured cycle count is in the repo (§7, docs/08, docs/18 §9: a future OpenTitan release or a software implementation, cost measured in Phase 2). The model's stand-in is the pqm4 ML-DSA-65 sign on a Cortex-M4, **10,000,000 cycles on average -- an UNVERIFIED placeholder with no checked source at revision 1 (no web access); re-check the current pqm4 release and the M4->OTBN scaling before relying on it**. Scaling assumption, unverified: 1.0x (the M4 count assumed equal on the OTBN-class engine; a software SHAKE on OTBN could make it optimistic). Hybrid cost ~117 ms/batch (17 ms P-384 + 100 ms ML-DSA). At the 50 ms window the single engine is at 234 percent (cannot keep up); at a 250 ms window, under one second, it is at 47 percent, so the disproof -- no window under one second keeps the engine under 100 percent -- did not hold, conditional on the unverified figure above; the record latency rises to at most 367 ms. The figure is a mean over rejection sampling; a 2x pessimism factor stands in for its tail (an assumption, not a measurement -- a real tail bound needs a Phase 2 measurement; at 2x the 250 ms window still leaves only ~13 percent slack, so the result is sensitive). The model counts signing only: tickets are a 20 us firmware path and verification and session setup are not on the engine, so "no second engine needed" holds for the signing workload, not the chip as a whole. | window above 117 ms and under 1 s; engine utilization under 50 percent (conditional on the unverified ML-DSA figure) |
| Heartbeat period / expiry | 1 s / 5 s | the period is the authority's own setting; the expiry is policy (`fabric.heartbeat_expiry_s`) and the governor clamps any signed window to it |
| Staged-policy deadline | 10 s | policy (`fabric.epoch_deadline_s`): a governor that staged an image and saw no commit stops accepting heartbeats under the staged epoch and halts as a straggler |
| Ticket validity / workload token validity | 300 s / 3600 s | policy |
| Loop sense period / end-to-end halt bound | 100 µs / 1 ms | not policy-adjustable; design targets measured in Phase 2. Loss of current is declared after two sense periods (debounce) |
| Epoch commit deadline | 10 s | policy |
| Human override latency floor | 60 s | policy, never below 10 s |
| Throttle to halt / halt to safe | 30 s / 300 s | policy; the RTL sequencer and heartbeat timers run on a millisecond tick derived from the microsecond counter |

## 10. Memory and storage budgets

| Store | Size | Contents |
|---|---|---|
| ROM | 64 KB | Boot loader, governance key hashes, DICE engine |
| OTP fuses | 8 Kbit | UDS, anti-rollback (256 one-time bits as a thermometer code), lifecycle, chip id, configuration |
| SRAM | 512 KB | Firmware working set, capability tables, roster, in-flight requests |
| NVM (authenticated, encrypted) | 16 MB on-die or package-bonded | Policy image (≤ 1 MB), log (circular, checkpointed off-chip), ledger state, used-ticket set (2^20 entries as a cuckoo table), reservations |

## 11. Physical targets

| Target | Prototype (sky130, 130 nm MPW) | Product (22 nm FD-SOI or 16 nm FinFET) |
|---|---|---|
| Die area | about 2 mm² for the control core as configured (1.4 × 1.4 mm in `hw/librelane/governor_core/config.json`), inside a ~10 mm² shuttle harness user area; crypto engines and SRAM macros extra | < 4 mm² including crypto, NVM macro separate |
| Clock | 50 MHz | 400 MHz core |
| Power | < 250 mW | < 500 mW |
| Package | QFN-64 (prototype) | BGA-169 with the SGMII and PCIe PHYs |
| I/O | SPI, I2C, GPIO, UART at 3.3 V (the open sky130 PDK has no PCIe or SGMII PHY) | PCIe Gen 3 x1, 2 × SGMII, 8 × I2C/SMBus, MDIO, GPIO at 1.8 V |
| Operating range | 0 to 85 °C | -40 to 105 °C (data-center hot aisle margin) |
| Reliability | n/a | 10-year, 24/7, 125 °C junction qualification; IEC 61508 SIL 2 hardware metrics (PFH, safe failure fraction, hardware fault tolerance), with a dangerous-failure-rate budget in FIT |

The prototype proves the control core, the levers, the loop and the fabric protocol on a
real board with real GPUs; the product node adds the PHYs and the crypto engines as hard IP.
Details in `08-silicon-plan.md`.
