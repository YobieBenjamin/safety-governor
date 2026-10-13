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
  the governor's own signatures keeps one engine. The functional model uses Ed25519 for speed
  of implementation. The architecture does not depend on the curve.
- "Durable" means written to the governor's authenticated NVM before the operation returns.
- Reason codes are strings in the model and 16-bit codes in silicon; the mapping is in
  `govsim/reasons.py`.
- Time is the governor's monotonic counter (64-bit, 1 µs ticks, never decremented, persisted
  across power loss with a fuse-backed high-water mark). Wall time is advisory and comes
  from signed heartbeats.

## 2. Register map (control and status, CSR bus, 32-bit)

The host sees exactly one BAR: the mailbox doorbell, the response ring, and read-only status.
Everything else below is internal to the governor's firmware and listed so the RTL and the
verification plan agree.

| Offset | Name | Access | Bits | Meaning |
|---|---|---|---|---|
| 0x000 | `ID` | RO | 32 | Silicon id and revision |
| 0x004 | `LIFECYCLE` | RO | 2 | 0 test, 1 provisioned, 2 production, 3 decommissioned (fuse-backed, monotone) |
| 0x008 | `STATE` | RO | 3 | 0 BOOT, 1 HALTED_INITIAL, 2 RUN, 3 THROTTLE, 4 HALT, 5 SAFE |
| 0x00C | `CAUSE` | RO | 16 | Last safe-mode cause code |
| 0x010 | `EPOCH[0..7]` | RO | 256 | Policy epoch (digest of the accepted policy image) |
| 0x030 | `MEAS0[0..7]` | RO | 256 | Measurement register 0 (loader); extend-only |
| 0x050 | `MEAS1[0..7]` | RO | 256 | Measurement register 1 (firmware); extend-only |
| 0x070 | `MONO_LO`, `MONO_HI` | RO | 64 | Monotonic counter |
| 0x078 | `HB_REMAIN` | RO | 32 | Heartbeat ticks remaining |
| 0x07C | `LOOP` | RO | 2 | bit 0 loop current sensed, bit 1 own switch open |
| 0x080 | `LEVERS` | RO | 3 | bit 0 power brake asserted, bit 1 PERST# asserted, bit 2 PWR_EN low |
| 0x084 | `ALARMS` | RO | 32 | Sticky alarm bits (monotone; cleared only through the clear path) |
| 0x100 | `MBOX_DOORBELL` | WO (host) | 32 | Length of the command frame placed in the inbound ring |
| 0x104 | `MBOX_STATUS` | RO | 8 | 0 idle, 1 busy, 2 ok, 3 bad signature, 4 bad sequence, 5 bad epoch, 6 refused |
| 0x108 | `MBOX_SEQ` | RO | 32 | Last accepted inbound sequence number |
| 0x200 | `METER_SLOT[n]` | RO | 4×64 per slot | tokens, kernel cycles, bytes in, bytes out, per model digest slot (16 slots) |
| 0x400 | `LOG_HEAD[0..7]` | RO | 256 | Current log head |
| 0x420 | `LOG_SIZE` | RO | 64 | Entries in the log |

There is no writable register other than the doorbell. Configuration, policy, keys and
clears all arrive as signed mailbox commands. In plain words: the security office has one
letter slot and no light switches on the outside wall.

## 3. Mailbox commands

Frame: `{seq: u32, epoch: 32 bytes, cmd: u16, body: bytes, sig: 64 bytes}`. The signature is
by a key the policy names for that command class. The mailbox FSM checks, in order:
sequence number greater than `MBOX_SEQ` for that signer, epoch equal to `EPOCH` (except
`POLICY_PROPOSE`, `POLICY_COMMIT` and `ATTEST`), signature valid for the command class.
Only then is the command dispatched.

| Code | Command | Signer class | Body | Effect |
|---|---|---|---|---|
| 0x01 | `ATTEST` | anyone | nonce | Returns the governor's quote: measurements, epoch, lifecycle, counters, over the nonce |
| 0x02 | `VERIFY_GPU` | host (unsigned allowed; result is signed by the governor) | GPU attestation report, governor nonce | Verifier checks the report; on success stores the GPU fingerprint for the job |
| 0x03 | `VERIFY_HOST` | host | CPU TEE report | As above for the host enclave |
| 0x04 | `BEGIN_MODEL` | verified loader | publisher-signed manifest | Verifies manifest signature against the policy's publisher keys; extends the fingerprint with the manifest digest; returns the wrapped model key |
| 0x05 | `END_MODEL` | verified loader | model digest | Finalizes the meter slot |
| 0x06 | `REQUEST` | verified broker | typed request (§5) | Gate core; returns a ticket, a hold id, or a refusal |
| 0x07 | `APPROVE` | approver | hold id, request hash | Releases a hold if the policy quorum for that rule is met |
| 0x08 | `COMMIT` | endpoint | ticket id | Commits the reservation |
| 0x09 | `SIGN_OUTPUT` | verified runtime | stream id, claimed prompt hash, nonce | Returns the device-provenance record (§6) |
| 0x0A | `CAP_REQUEST` | driver (rack tier: a request to open a switch port or flow to a roster peer) | point, peer, direction, byte budget, ttl | Capability or refusal; the governor programs the switch |
| 0x0B | `ROSTER_JOIN` | driver | peer quote | Starts roster formation on the fabric |
| 0x0C | `POLICY_PROPOSE` | policy authority | image, version, expiry, signatures | Stage a new image; reply with ack on the fabric |
| 0x0D | `POLICY_COMMIT` | policy authority | image digest | Switch the epoch (cluster-atomic rule in `02`) |
| 0x0E | `HEARTBEAT` | policy authority | validity window, epoch | Reloads the heartbeat timer |
| 0x0F | `HALT` / `THROTTLE` | policy authority | rung, cause | Assert the lever |
| 0x10 | `CLEAR` | policy authority | cause id, acknowledged log head | Clear the cause; close the loop switch if no cause remains |
| 0x11 | `LOG_CHECKPOINT` | anyone | none | Signed Merkle root, size, head, neighbor heads |
| 0x12 | `COUNTERS` | anyone | model digest | Meter readout |
| 0x13 | `EXCEPTION_DRAIN` | firmware | none | Refusals since the last drain, for the log |

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
  budget_owners: {budget_key: governor_key_id},
  rules: [Rule],
  assumptions: [RegisterRow],     // 06-assumptions-register.md; load fails if a rule input lacks a row
  safe_mode: {cause_code: first_rung, T_throttle_ms, T_halt_ms},
  fabric: {heartbeat_period_ms, heartbeat_expiry_ms, max_hops, epoch_deadline_ms, loop_bound_us},
  signatures: [sig]              // k-of-n over everything above
}

Rule {
  id, measurement (fingerprint or "*" for any verified), action,
  constraints: {param: {min,max} | {in:[...]} | {not_in_list: list_id} | {digest_of: list_id}},
  requirement: {mode: auto|observer|human, observers: [key_id], max_risk, approvers_quorum},
  rate: {max, window_s},
  budget: {key, param, limit, window_s},
  endpoint: name | null,
  delay_ms: u32
}
```

The epoch is `SHA-256(canonical(PolicyImage without signatures))`. A rule's constraints may
name only inputs that have a row in `assumptions`; the loader refuses an image that does not
satisfy that (R-H7).

## 5. Typed request, ticket, capability

![One request through the gate](figures/fig-request.png)

```
Request {request_id, measurement_token, action, params{...}, witnesses: [Assertion]}
   request_hash = SHA-256(canonical(request_id, fingerprint, action, params))

Ticket {ticket_id (random 128-bit), request_hash, action, params_digest, measurement, rule,
        policy_epoch, endpoint, budget_key, reservation, issued_at, expires_at, sig_governor}

Capability (32 bytes packed) {
   point: u8      // rack tier: 0 NVSwitch port, 1 PCIe switch port, 2 DPU flow, 3 storage path, 4 output path;
                  // integrated tier adds 5 copy engine, 6 peer MMU
   peer: u64      // roster member id, host enclave id, manifest id or flow id
   dir: u2        // in, out, both
   budget: u40    // bytes
   expiry: u32    // monotonic ticks (coarse)
   epoch_tag: u16 // low bits of the epoch
   mac: u64       // truncated HMAC under the controller key
}
```

The capability table in RTL holds 256 entries per enforcement point as a content-addressable
memory keyed on `(point, peer, dir)`; a lookup decrements `budget` and refuses at zero, on
expiry, or on an epoch-tag mismatch. The MAC is checked at insertion, not per lookup; the
table itself is inside the governor's domain. At the rack tier the table is the governor's
source of truth for what it has programmed into the switches: a port or flow is open in the
switch exactly when a matching, unexpired entry exists, and the governor re-derives the
switch configuration from the table after any epoch, roster or heartbeat event.

## 6. Device-provenance record

```
Record {chip_id, fw_measurement, model_digest, policy_epoch, roster_id,
        prompt_hash (as claimed by the runtime), output_hash, token_count,
        nonce, time, counters{tokens, cycles, bytes_in, bytes_out}, sig_governor}
```

It establishes device provenance only. Workload provenance is the verified runtime's own
record; execution integrity is research. The blog's three-claim table applies.

## 7. Crypto suite and key hierarchy

| Need | Primitive | Implementation note |
|---|---|---|
| Hashing, measurement, log chain | SHA-256 | Hardware engine; also hashes what the verified runtime presents for signing |
| MAC for capabilities, NVM authentication | HMAC-SHA-256 | Same engine |
| Signatures | ECDSA P-384 over SHA-384 (what the NVIDIA GPU attestation chain and SEV-SNP use); P-256 for TPM-class endpoints | OTBN-class big-number coprocessor (OpenTitan's OTBN ships P-256 and P-384 ECDSA, X25519, RSA, SHA-2/3 and post-quantum ML-KEM and ML-DSA programs; Ed25519 would need its own program); constant time |
| NVM encryption | AES-256-GCM | Hardware engine |
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
| Device-provenance signature | under 2 ms per ECDSA signature on an OTBN-class coprocessor at 100 MHz, a budget rather than a measurement; a dedicated ECC engine is faster. Per-response signing therefore caps at a few hundred responses per second per engine, so records are batched: one signature per batch window (default 10 ms) over a Merkle root of the records in the window, each record carrying its path | 2 ms per signature; 10 ms batch window |
| Heartbeat period / expiry | 1 s / 5 s | policy |
| Loop sense period / end-to-end halt bound | 100 µs / 1 ms | fixed in silicon |
| Epoch commit deadline | 10 s | policy |
| Human override latency floor | 60 s | policy, never below 10 s |
| Throttle to halt / halt to safe | 30 s / 300 s | policy |

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
| Die area | ~10 mm² for the control core without crypto; crypto engines as additional macros | < 4 mm² including crypto, NVM macro separate |
| Clock | 50 MHz | 400 MHz core |
| Power | < 250 mW | < 500 mW |
| Package | QFN-64 (prototype) | BGA-169 with the SGMII and PCIe PHYs |
| I/O | SPI, I2C, GPIO, UART (prototype: no PCIe PHY at 130 nm) | PCIe Gen 3 x1, 2 × SGMII, 8 × I2C/SMBus, MDIO, GPIO |
| Operating range | 0 to 85 °C | -40 to 105 °C (data-center hot aisle margin) |
| Reliability | n/a | 10-year, 24/7, 125 °C junction qualification; FIT target per IEC 61508 SIL 2 hardware |

The prototype proves the control core, the levers, the loop and the fabric protocol on a
real board with real GPUs; the product node adds the PHYs and the crypto engines as hard IP.
Details in `08-silicon-plan.md`.
