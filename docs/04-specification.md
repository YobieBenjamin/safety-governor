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
> `govsim/bench.py` (the timing budgets priced); tests `tests/test_contract_fresh_authorization_per_operation.py`,
> `test_contract_policy_quorum_no_rollback.py`, `test_contract_broker_cannot_pick_rule.py`, `test_contract_override_slow_and_logged.py`, `test_contract_governor_overhead_bounded.py`;
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
| 0x00C | `CAUSE` | RO | 16 | Bits 2:0 the sequencer's own summary (0 none, 1 loop, 2 local, 3 tamper, 4 command); bit 3 waiting for the first heartbeat, boot window passed; bit 4 excluded; bits 15:8 the firmware's reason code from `govsim/reasons.py` |
| 0x010 | `EPOCH[0..7]` | RO | 256 | Policy epoch (digest of the accepted policy image) |
| 0x030 | `MEAS0[0..7]` | RO | 256 | Measurement register 0 (loader); extend-only |
| 0x050 | `MEAS1[0..7]` | RO | 256 | Measurement register 1 (firmware); extend-only |
| 0x070 | `MONO_LO`, `MONO_HI` | RO | 64 | Monotonic counter |
| 0x078 | `HB_REMAIN` | RO | 32 | Heartbeat time remaining, milliseconds |
| 0x07C | `LOOP` | RO | 2 | bit 0 loop current sensed, bit 1 own switch open |
| 0x080 | `LEVERS` | RO | 3 | bit 0 power brake asserted, bit 1 PERST# asserted, bit 2 PWR_EN low |
| 0x084 | `ALARMS` | RO | 32 | Sticky alarm bits (monotone; cleared only through the clear path). Bit 31 `NO_FIRST_HEARTBEAT` and bit 30 `EXCLUDED` are hardware-owned; bits 29:0 are raised by firmware |
| 0x088 | `BOOT_WAIT` | RO | 16 | Milliseconds the chip waited for its first heartbeat since reset (saturates at 65535; frozen once armed) |
| 0x100 | `MBOX_DOORBELL` | WO (host) | 32 | Length of the command frame placed in the inbound ring |
| 0x104 | `MBOX_STATUS` | RO | 8 | 0 idle, 1 busy, 2 ok, 3 bad signature, 4 bad sequence, 5 bad epoch, 6 refused |
| 0x108 | `MBOX_SEQ` | RO | 32 | Last accepted inbound sequence number (key slot 0; one counter per signer key) |
| 0x200 | `METER_SLOT[n]` | RO | 4×64 per slot | tokens, kernel cycles, bytes in, bytes out, per model digest slot (16 slots) |
| 0x400 | `LOG_HEAD[0..7]` | RO | 256 | Current log head (firmware-mapped: the log engine is firmware over NVM, so the RTL core does not decode it) |
| 0x420 | `LOG_SIZE` | RO | 64 | Entries in the log (firmware-mapped) |

There is no writable register other than the doorbell. Configuration, policy, keys and
clears all arrive as signed mailbox commands. In plain words: the security office has one
letter slot and no light switches on the outside wall.

**Operator signals (decided by Yobie, 23 October 2026).** A chip that is stuck must say so,
by name, in hardware. ALARMS bit 31 is `NO_FIRST_HEARTBEAT`, set by the hardware when the chip has sat in HALTED_INITIAL with no cause and no valid heartbeat for longer than the boot window
(`t_boot_ms`, default 5000 ms; section 9). It is never set once the chip has been armed since reset. ALARMS bit 30
is `EXCLUDED`, set by the hardware while an `EXCLUDE` (section 3) holds. Both are hardware-owned bits: only the sequencer raises them and firmware cannot raise them; like every alarm they stay set until
an authorized clear. CAUSE bits 3 and 4 show the same two conditions live, and `BOOT_WAIT` says how long the chip
waited. So an operator reading one chip over SMBus sees "this chip, waiting for its first heartbeat since reset,
for this long" instead of "the rack won't start". The model's reason codes are `boot.no_first_heartbeat`,
`boot.excluded` and `exclude.not_waiting_for_first_heartbeat`; the alarm is logged with the chip id and the
boot time and sent on the fabric as an `ALARM`, so the neighbours and the supervisor log it too. These two alarms
report why a chip is not running; they do not park the gate of a chip that is running.

## 3. Mailbox commands

Frame: `{seq: u32, epoch: 32 bytes, cmd: u16, body: bytes, sig: 96 bytes (P-384; 64 in the
Ed25519 model)}`. The signature is by a key the policy names for that command class. The
mailbox checks, in order: sequence number greater than the last accepted one for that signer
key, epoch equal to `EPOCH` (except the epoch-exempt commands `POLICY_PROPOSE`,
`POLICY_COMMIT`, `ATTEST`, `HALT`, `CLEAR`, `ALARM_CLEAR` and `EXCLUDE`, which move, repair or inspect the
epoch itself and must work when it is stale), then the signature, then what was signed: the
signed payload names the command it is for (`type` equal to the command in lower case, so a
heartbeat or an approval cannot be presented as a `CLEAR` or an `ALARM_CLEAR`), and a `HALT`
or `CLEAR` also names the chip it is for and carries an expiry no more than 60 s ahead that has
not passed (`mailbox.wrong_command`, `mailbox.expired`; RTL status 7). That last check was added
on 22 October 2026 after a heartbeat cleared a halt in testing. The first failing check is
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
| 0x0E | `HEARTBEAT` | the heartbeat key | validity window, epoch | Reloads the heartbeat timer |
| 0x0F | `HALT` / `THROTTLE` | an authority key (never the heartbeat key) | rung, cause, this chip's id, expiry | Assert the lever; a `HALT` also opens the loop switch, on every rung (see below) |
| 0x10 | `CLEAR` | an authority key (never the heartbeat key); this chip's id and an expiry in the payload | none in the model (the governor checks its own record of which log head a neighbor acknowledged) | Clear the cause if it is in the log and a fabric neighbor has acknowledged the checkpoint that contains it; close the loop switch if no cause remains |
| 0x11 | `LOG_CHECKPOINT` | anyone | none | Signed Merkle root, size, head, neighbor heads |
| 0x12 | `COUNTERS` | anyone | model digest | Meter readout |
| 0x13 | `EXCEPTION_DRAIN` | firmware | none | Refusals at every governed switch since the last drain, handed to the log |
| 0x14 | `ALARM_RAISE` | anyone | cause, request hash, evidence digest | Raises a sticky alarm (any party may) |
| 0x15 | `ALARM_CLEAR` | the policy's alarm approver key | cause | Clears an alarm; logged |
| 0x16 | `EXCLUDE` | an authority key (never the heartbeat key); the same class and checks as `CLEAR`: this chip's id and an expiry in the payload, epoch-exempt | none | Only for a chip waiting for its first heartbeat: close its loop switch, keep its own levers asserted (see below); logged with the signer |
| 0x17 | `KEY_RELEASE` | host (signed, typed), RUN, GPU and host attested | the model's data key, sealed to this governor | The origin gate (`18` §8d): for a model that BEGIN_MODEL presented and the rulebook's `sealed_models` lists, unseal the data key and re-seal it to the attested GPU's confidential-computing key, with a signed lease of `key_lease_s`; logged. Refusals: `key.model_not_loaded`, `key.model_not_in_rulebook`, `key.no_attested_gpu_key`, `key.unwrap_failed` |
| 0x18 | `KEY_RENEW` | host (signed, typed), RUN, GPU attested | none | Extend a live lease while the edition still lists the model and the GPU is not revoked; otherwise the key is revoked (`key.revoked` in the log) and the GPU wipes it when the lease ends. A new edition that drops the model or revokes the GPU revokes at once |

**Two design calls (decided by Yobie, 23 October 2026).** "Silently failing is a bullshit
feature. Operators should have some verbose warning / signal / notice."

1. A HALT opens the loop switch on every rung, SAFE included. A chip that reached SAFE on a
   local cause (a lost heartbeat) still has its loop closed; a signed HALT to it opens the switch so the whole
   domain stops, as `02-safety-fabric.md` section 1 says a HALT does. SAFE outranks HALT, so a HALT to a chip already in SAFE leaves it in SAFE with power off, and the command becomes
   the cause on record (CAUSE bits 2:0 read 4), except that a tamper cause is kept. The priority is unchanged:
   tamper, then an authorized CLEAR, then the rest. Before this the RTL ignored a HALT in SAFE and the model dropped
   to HALT and turned slot power back on (conformance finding CONFORMANCE-HALT-TO-SAFE-CHIP, now closed).
2. A chip that never gets its first heartbeat keeps holding the rack (fail closed, unchanged), loudly (section 2,
   operator signals). The deliberate way out is `EXCLUDE`, signed by the authority under the same rules as `CLEAR`.
   EXCLUDE has no effect in any state but HALTED_INITIAL with no cause, and none while a valid heartbeat is live (that chip arms
   itself). There, the excluded chip closes its own loop switch so the rest of the rack can run, while its own levers stay asserted: its state stays
   HALTED_INITIAL (brake, reset, power off), so its own GPUs never run while it is excluded. EXCLUDE can never close
   the loop of a chip halted by loop loss, a command or tamper. It leaves exclusion when a valid heartbeat arms it normally, on a reset, or when a HALT or a tamper moves it to a halted rung with its loop open. Excluded is a visible state bit and alarm, never silent, and every EXCLUDE is logged with who signed it.

## 4. The policy image

```
PolicyImage {
  version: u32,                  // strictly increasing; the anti-rollback counter tracks it
  issued_at, expires_at: u64,
  governance_keys: [key],         // n keys, each counted once however often it is listed
  threshold: u8,                  // k; at least 1, at most n, and never below the fused threshold
                                  // (GOV_THRESHOLD in the fuses, set at provisioning, raised by an
                                  // edition that asks for more, never lowered by one that asks for less)
  approver_keys: {rule_id: [key], quorum: u8},
  heartbeat_key: key,             // signs heartbeats and nothing else
  authority_keys: [key],          // sign HALT and CLEAR; a different key from the heartbeat's
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
  eval_keys: [key],               // who may attest that a model was evaluated
  deployment_gate: bool,          // BEGIN_MODEL needs an evaluation attestation
  buffer_classes: [name],         // integrated tier: the classes of GPU memory (weights, kv_cache, activations, outputs)
  buffer_policy: {class: none | roster | host | any-roster-or-host},   // where each class may go; no entry means nowhere
  audit: {sample_rate, escrow_classes: [class], store: endpoint_name},   // the chip's own sampling, escrow before release
  streams_required: [stream],     // a response presents these before it can be released (per-rule override below)
  compute_budget: {cycles | null, license_keys: [key]},   // a cycle budget only a signed licence extends
  sandbox: bool,                  // a model organism: the roster opens no peer port
  signatures: [sig]              // k-of-n over everything above
}

Rule {
  id, measurement (a workload measurement, or "*" for any verified workload), action,
  constraints: {param: {min,max} | {in: [...]} | {in_list: list_id} | {not_in_list: list_id} | {digest_of: list_id}},
  requirement: {mode: auto|observer|human, observers: [key_id], max_risk, approvers_quorum,
                allowed_hazard_classes: [class], min_legibility, on_hazard: refuse|human, on_illegible: refuse|human},
                                 // the last four: response.release only
  rate: {max, window_s},
  budget: {key, param, limit, window_s},
  output_budget: {queries, bytes, window_s, unpresented_bytes},   // model.output only
  hazard_budget: {max, window_s} | null,   // response.release only: hazard verdicts per session per window
  endpoint: name | null,
  delay_s,
  inputs: [input_name],          // register rows declared by the author, in addition to the derived ones
  streams_required: [stream] | null   // response.release only; null means the image's default
}
```

The model's `make_policy` and `make_rule` in `govsim/policy.py` are the schema as it runs;
`digest_of` and `revocations` are in the schema and derive register rows, and are not yet
checked at the gate (the program's list).

The epoch is `SHA-256(canonical(PolicyImage without signatures))`. Rules are keyed by the
**workload measurement** `H(gpu_firmware, host_firmware, model_manifest)`; an exact rule beats
a wildcard. The **fingerprint** `H(workload, epoch)` binds tokens, tickets and request hashes
to the policy edition as well (a rule cannot be keyed by the fingerprint because the
fingerprint contains the epoch of the image the rule is in). The loader derives the inputs a
rule relies on from its constraints (`in_list`, `not_in_list`, `digest_of`), its observers and
its budget key, unions them with the declared `inputs`, and refuses an image in which any of
them lacks a row in `assumptions` (R-CONTRACT-ASSUMPTIONS-REGISTER-COMPLETE), or in which a budget key has no `budget_owners` row.
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
| Heartbeat period / expiry | 1 s / 5 s | the period is the authority's own setting; the expiry is policy (`fabric.heartbeat_expiry_s`) and the governor clamps any signed window to it |
| Staged-policy deadline | 10 s | policy (`fabric.epoch_deadline_s`): a governor that staged an image and saw no commit stops accepting heartbeats under the staged epoch and halts as a straggler |
| Ticket validity / workload token validity | 300 s / 3600 s | policy |
| Loop sense period / end-to-end halt bound | 100 µs / 1 ms | not policy-adjustable; design targets measured in Phase 2. Loss of current is declared after two sense periods (debounce) |
| Epoch commit deadline | 10 s | policy |
| Human override latency floor | 60 s | policy, never below 10 s |
| Throttle to halt / halt to safe | 30 s / 300 s | policy; the RTL sequencer and heartbeat timers run on a millisecond tick derived from the microsecond counter |
| Boot window for the first heartbeat (`NO_FIRST_HEARTBEAT`) | 5 s | an RTL parameter (`t_boot_ms`), not policy: the chip has no policy-checked heartbeat yet when it applies; the proof builds use 3 to 5 ms |

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
