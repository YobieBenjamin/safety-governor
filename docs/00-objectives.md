# 00 · Design objectives

This document says what the Safety Governor is for, what it must do, what it must never do,
and what it deliberately does not attempt. Everything later in `docs/` traces back to a
numbered line here. Tests in `tests/` cite these numbers.

> **Plain-English version:** `10-plain-english-walkthrough.md` §1 and §15.
> **Backed by:** every requirement names its test in the last column of its table; the live
> result of all of them is `results/report.md` (`./run.sh`). Model `govsim/`, tests `tests/`,
> hardware blocks `rtl/governor_rtl/`, silicon flow `hw/`.

## The problem, in one paragraph

A frontier model runs across thousands of GPUs and emits trillions of tokens. No device can
read meaning off a wire, and no AI can be trusted to police another AI, because a guard has to
be tamperproof, always invoked and small enough to verify, and a model is none of those.
Prevention therefore lives at the point of action: the wire that releases a weapon, the switch
that moves money, the controller that moves a robot. The blog series argues that case. The
chip in this repository is the hardware that makes the argument enforceable: a governor for
every GPU, added through the rack's own boards, that holds the rules, verifies the hardware,
mints the permissions, keeps the books, signs what the verified runtime presents, holds the
keys to the switches the GPU's traffic already passes, and can physically stop the GPU, with a
private fail-safe link to every other governor in the rack. It asks NVIDIA for no new silicon
and changes nothing in CUDA, because NVIDIA has most of the market and a design that needs
them to rebuild the GPU is a design that does not ship.

In plain words: the model is the engine. The governor is the brass balls on the shaft that
close the valve when the engine runs away, and this governor is wired to every other governor
in the factory, so when one closes its valve the rest know within a millisecond.

## G · Goals

| Id | Goal | Why |
|---|---|---|
| GOAL-ENFORCE-CONTRACT-IN-HARDWARE | Enforce the security contract from the reference stack in hardware the host cannot bypass: within a declared boundary, every protected operation requires a fresh authorization bound to that exact operation | The contract is the whole point; software alone cannot be tamperproof |
| GOAL-OWN-GOVERNOR-PER-GPU | Give every GPU its own governor with physical, vendor-independent authority over it and over the switches its traffic passes | Authority has to be local. A chip that can only ask the GPU nicely is a classifier with a heatsink |
| GOAL-WORK-WITH-NVIDIA-AS-SHIPPED | Work with NVIDIA's GPUs, baseboards and CUDA exactly as they ship: added through the rack's boards, governing through management interfaces that already exist. The system board and its management-module slot are the OEM's; the HGX baseboard, its NVSwitch chips and its hardware management controller are NVIDIA's, so what the governor reaches on the baseboard is what the baseboard exposes at its connector, and anything soldered onto the baseboard is an ask | NVIDIA has most of the market; a design that needs new GPU silicon or a CUDA change does not ship |
| GOAL-UNREACHABLE-GOVERNOR-LINK | Link all governors in a cluster over a channel that no model, host or network switch can reach | Frontier jobs span nodes; a halt or an epoch change that reaches some GPUs and not others is a hazard |
| GOAL-FAIL-SAFE-ALWAYS | Fail safe: loss of power, loss of heartbeat, a broken loop wire, a bad policy load or a detected tamper all end in the specified safe transition, never in "carry on" | A safety system that fails open is a decoration |
| GOAL-SMALL-ENOUGH-TO-VERIFY | Be small enough to verify: control firmware in the class of a verified kernel, hardware blocks with written-down invariants, and a proof-assumption list | The third test of a reference monitor |
| GOAL-UNDER-ONE-PERCENT-COST | Cost under one percent of GPU throughput, measured on the whole protected deployment | A governor nobody turns on protects nobody |
| GOAL-BUILDABLE-NOW-AT-RACK | Be buildable now at the rack tier, with the same firmware, policy format and fabric on the board-only fallback, and with every ask to the GPU vendor limited to firmware and software that tighten the design rather than enable it | The ask to the vendor should be a short list of software changes, not a redesign |
| GOAL-KEYS-OUT-OF-VENDOR-HANDS | Keep the governance keys out of the chip vendor's hands and out of the operator's hands | The party deciding what may run is not the party selling the chip or renting it |

## R · Requirements

Each requirement is testable. The last column names where it is tested today: `sim` is the
functional model in `govsim/` (tests in `tests/`), `rtl` is the Amaranth simulation in
`rtl/tests/`, `silicon` is deferred to the verification plan.

### Identity and boot

| Id | Requirement | Tested |
|---|---|---|
| REQUIREMENT-DEVICE-SECRET-IN-FUSES | The chip holds a unique device secret in one-time-programmable fuses readable only by the key-derivation engine | sim (`fuses.py`), silicon |
| REQUIREMENT-MEASURED-BOOT-DERIVES-KEY | Boot is measured: each stage extends a register that can only be extended, never written, and the signing key is derived from the measurement (DICE) | sim, rtl (`measure_reg`) |
| REQUIREMENT-FUSED-ANTI-ROLLBACK | An anti-rollback counter in fuses rejects firmware older than the last accepted version; the policy version is fused the same way | sim (boot refused; rollback refused with the stored image gone) |
| REQUIREMENT-DEBUG-FUSED-OFF | Debug and scan access is disabled by a lifecycle fuse before shipment; an access attempt in the production state is refused and logged | sim, rtl (`lifecycle`) |
| REQUIREMENT-GLITCH-DETECTORS-ZEROIZE | Voltage, clock and temperature glitch detectors, and an active shield over the key store, trigger zeroization of volatile keys | silicon (modelled as a flag in sim) |

### Policy and epochs

| Id | Requirement | Tested |
|---|---|---|
| REQUIREMENT-POLICY-NEEDS-GOVERNANCE-SIGNATURES | A policy image is accepted only with k-of-n signatures from governance keys whose hashes are in ROM or fuses | sim |
| REQUIREMENT-EPOCH-UNWRITABLE-BY-HOST | The policy epoch is the digest of the accepted image, held in a register no host path can write | sim, rtl (`epoch_reg`) |
| REQUIREMENT-SUPERSEDED-EPOCH-REFUSED | A ticket, a capability or a fabric message from a superseded epoch is refused | sim |
| REQUIREMENT-NO-GOVERNOR-ON-OLD-RULES | An epoch change leaves no governor on the old rules: the authority commits to the members that acknowledged, the heartbeat carries the new epoch, a member that never staged cannot accept it and halts at expiry, and a member that staged but saw no commit halts at the staged-policy deadline | sim (CONTRACT-PARTITIONS-END-SAFE) |

### Authorization

| Id | Requirement | Tested |
|---|---|---|
| REQUIREMENT-RULEBOOK-SELECTS-RULE-AND-LANE | Every protected operation is authorized; the rulebook selects the rule and the lane from the verified workload, the action and the typed fields, and from nothing the requester supplies | sim (CONTRACT-FRESH-AUTHORIZATION-PER-OPERATION, CONTRACT-BROKER-CANNOT-PICK-RULE) |
| REQUIREMENT-AUTHORIZATION-IS-DURABLE-TRANSACTION | Authorization is a transaction: check, reserve, commit; replay state, reservations, holds and the used-ticket set survive power loss | sim (CONTRACT-FRESH-AUTHORIZATION-PER-OPERATION) |
| REQUIREMENT-ONE-LEDGER-OWNS-BUDGET | One ledger owns a budget key, named in the policy image and checked at load (an image with an ownerless budget key does not load); a shared allowance is reserved at the owner over the fabric, never estimated locally | sim (CONTRACT-SHARED-BUDGET-NO-OVERSPEND) |
| REQUIREMENT-ALARM-CLEARED-BY-CHECKABLE-RULE | Any party may raise an alarm; an alarm is cleared only by a rule the chip can check or by an approver key | sim (CONTRACT-ALARMS-ARE-MONOTONE) |
| REQUIREMENT-OVERRIDE-NEEDS-QUORUM-REASON | Human override requires the policy's quorum of approvers, a written reason, and a latency floor; every override is in the log | sim (CONTRACT-OVERRIDE-SLOW-AND-LOGGED) |

### Attestation and keys

| Id | Requirement | Tested |
|---|---|---|
| REQUIREMENT-LOCAL-ATTESTATION-WITH-NONCE | The governor verifies the paired GPU's and the host enclave's attestation locally against reference values signed by the governance root; verification uses a fresh nonce and the result expires | sim (CONTRACT-ATTESTATION-BINDS-PERMISSIONS) |
| REQUIREMENT-FINGERPRINT-COVERS-WORKLOAD | The workload fingerprint covers firmware, the model manifest digest and the policy digest; a change in any of them changes the fingerprint | sim (CONTRACT-ATTESTATION-BINDS-PERMISSIONS) |
| REQUIREMENT-KEY-RELEASED-TO-VERIFIED-ENCLAVE | The model's decryption key is released only to a verified enclave under a current epoch | sim (CONTRACT-ATTESTATION-BINDS-PERMISSIONS) |

### Enforcement points (rack tier)

| Id | Requirement | Tested |
|---|---|---|
| REQUIREMENT-EVERY-EXIT-UNDER-CAPABILITY | Every enumerated exit from the GPU passes a switch whose port or flow is open only under a capability issued by the governor (rack tier: NVSwitch ports, PCIe switch ports and ACS, DPU flows); a path with no governed switch is disabled by policy | sim (CONTRACT-EVERY-CROSSING-GOVERNED) |
| REQUIREMENT-CAPABILITY-FIELDS-AND-TAG | Capabilities name the point, the peer, the direction, a byte budget, an expiry and the epoch, and carry an integrity tag | sim, rtl (`cap_table`) |
| REQUIREMENT-REFUSED-TRANSFERS-LOGGED | Refused transfers are drained to the log with source, destination and size | sim |

### Physical levers (all tiers)

| Id | Requirement | Tested |
|---|---|---|
| REQUIREMENT-LEVERS-NEED-NO-COOPERATION | The governor can throttle (power brake), reset (PERST#) and power-cut (slot enable, where the board provides it) its GPU without the GPU's cooperation, and can close every governed switch port around it | sim (CONTRACT-LEVERS-WITHOUT-GPU-COOPERATION), rtl (`halt`) |
| REQUIREMENT-PHYSICAL-HALT-CURRENT-LOOP | The halt loop is a physical current loop; any governor opening it, or a break in the wire, drives every governor's halt output within the bound | sim (CONTRACT-HALT-REACHES-EVERY-GPU), rtl (`halt_loop`) |
| REQUIREMENT-HALT-SURVIVES-POWER-CYCLE | A governor cannot clear a halt on its own, and a power cycle does not clear it either: the open cause is durable and comes back as the same rung; clearing requires the policy authority's signed command after the cause is logged and a neighbor has acknowledged the checkpoint | sim (CONTRACT-HALT-REACHES-EVERY-GPU) |

### Fabric

| Id | Requirement | Tested |
|---|---|---|
| REQUIREMENT-SIGNED-FABRIC-MESSAGES | Fabric messages are signed with DICE-derived keys, carry sequence numbers, a monotonic-counter timestamp and the epoch, and are accepted only from roster members; last-seen sequence numbers survive a power loss so a restart does not reopen the replay window | sim (CONTRACT-ONLY-ROSTER-SPEAKS-ONCE) |
| REQUIREMENT-ROSTER-FROM-MUTUAL-ATTESTATION | The roster is built from mutual attestation at job start and expires with the job | sim (CONTRACT-ONLY-ROSTER-SPEAKS-ONCE) |
| REQUIREMENT-HEARTBEAT-FANS-OUT-SIGNED | The heartbeat fans out over the fabric; each relay signs it and the hop count is bounded; the governor clamps any signed window to the policy's expiry; a governor past its expiry enters safe mode | sim (CONTRACT-PARTITIONS-END-SAFE), rtl (`heartbeat`) |
| REQUIREMENT-CHECKPOINT-INCLUDES-NEIGHBOR-HEADS | Each log checkpoint includes the last checkpoint heads of the governor's fabric neighbors | sim (CONTRACT-ONLY-ROSTER-SPEAKS-ONCE) |

### Provenance and metering

| Id | Requirement | Tested |
|---|---|---|
| REQUIREMENT-SIGNED-PROVENANCE-RECORD | A response gets a signed device-provenance record naming chip, firmware, model digest, policy epoch, roster, output hash, counters and time. At the integrated tier the hash is over the bytes themselves; at the rack tier it is over what the verified runtime presents, and the governor cross-checks the bytes that left for the host through its PCIe switch port against the bytes presented, raising an alarm and closing the port when the difference exceeds the policy's slack | sim (CONTRACT-LEAKAGE-WITHIN-BUDGET) |
| REQUIREMENT-PER-MODEL-COUNTERS-READ-ONLY | Tokens, kernel cycles and bytes are counted per model digest in registers the host can read and not write | sim, rtl (`meter`) |
| REQUIREMENT-OUTPUT-CHANNEL-BUDGETS | The permitted output channel carries query and byte budgets per workload, and an unpresented-bytes slack; exceeding any of them trips a limit | sim (CONTRACT-LEAKAGE-WITHIN-BUDGET) |

### Cost

| Id | Requirement | Tested |
|---|---|---|
| REQUIREMENT-PER-TOKEN-WORK-ZERO | Per-token work in the governor is zero; per-transfer work is one table lookup; per-response work is one hash finalization and a share of one batched signature. Firmware time on action paths is under one percent of GPU time; the signing engine, priced at OpenTitan's published OTBN cycle count, keeps up at under 50 percent utilization with batching | sim (`bench.py`) |
| REQUIREMENT-DEPLOYMENT-OVERHEAD-UNDER-ONE-PERCENT | Whole-deployment overhead under one percent, including tail latency, small requests, collectives, logging and revocation | silicon (Phase 2 measurement) |

## N · Non-goals

| Id | Not a goal | Why it is excluded |
|---|---|---|
| GOAL-NOT-UNDERSTANDING-TOKEN-CONTENT | Understanding the content of tokens | Silicon sees integers. Meaning enters only through the broker's typed request |
| GOAL-NOT-STOPPING-HARMFUL-SENTENCES | Stopping a harmful sentence over an allowed channel | That is the semantic residual; it belongs to narrow rulebooks, witnesses and humans |
| GOAL-NOT-MAKING-FACTS-TRUE | Making a declared fact true | A valid signature proves who signed a list, not that the list is complete. The assumptions register owns this |
| GOAL-NOT-REPLACING-ENDPOINT-COMPARATOR | Replacing the endpoint comparator | The guarantee lives in the device that acts. The governor mints tickets; it does not fire the missile or move the money |
| GOAL-NOT-INSPECTING-ROSTER-TRANSFERS | Inspecting individual transfers between two legitimate roster members | From the board the governor governs links and flows, not descriptors; byte-level checks inside the GPU are a future vendor ask, not a requirement |
| GOAL-NOT-SURVIVING-FAB-COMPROMISE | Surviving fab-level compromise, decapping with unlimited budget, or a leaked vendor signing key | Tamper response raises the cost; it does not make it infinite |
| GOAL-NOT-ONLY-SAFETY-LAYER | Being the only safety layer | It is the floor under the stack, not the stack |

## T · Tiers

The plan of record is the rack tier. It assumes NVIDIA's GPUs, baseboards and CUDA exactly
as they ship, and it governs through the management interfaces the rack already has. The
board-only tier is the fallback for systems where a switch's management cannot be reached.
The integrated tier is a future ask, kept for completeness and not required.

| Tier | Placement | Enforcement | What it cannot do | Needs |
|---|---|---|---|---|
| **Rack (plan of record)** | A governor module on the system board (DC-SCM-class slot), reaching the GPU baseboard through the baseboard's connector; one governor instance per GPU slot; governors on the NVLink switch trays and the DPU. Soldering the governor onto the HGX baseboard beside NVIDIA's management controller is the shortest wiring and is an ask to NVIDIA, because the baseboard is theirs | Per-slot levers (power brake, reset, slot power) where the board exposes them; NVSwitch partitions through Fabric Manager and switch reset; PCIe switch ports and ACS; DPU flow tables; attestation via the GPU's confidential-computing report; tickets, budgets, epochs, log, meter | Inspect individual transfers between two roster members | A slot on the system board; the switch management buses the OEM controls; the per-slot signals the baseboard exposes at its connector. On PCIe-card servers, where the slots are on the OEM's board, nothing from NVIDIA; on HGX, the lever signals the baseboard does not expose are an ask |
| Board-only (fallback) | The same module, where switch management is unreachable or the baseboard has direct NVLink with no NVSwitch | Levers, attestation, tickets, budgets, epochs, log, meter | Any port authority | As above, minus the switch buses |
| Integrated (future ask) | Hooks inside the GPU: descriptor-level checkers at the copy engines and the peer MMU, an inline output hash | Byte-level containment between roster members; device provenance of the bytes themselves | Nothing on the enumerated list | NVIDIA firmware and, for the checkers, silicon |

The same firmware, policy format, ticket format, fabric protocol and RTL blocks run on all
three. What changes between tiers is only how fine the enforcement is.

## Acceptance

The design is accepted for tape-out when: every `sim` test passes at the rack tier, with the
rack tier's one residual (CONTRACT-EVERY-CROSSING-GOVERNED at descriptor level between roster members) recorded as an
expected gap, and at the board-only tier with its gaps recorded; every `rtl` test
passes and the generated Verilog hardens through the LibreLane flow with clean DRC and LVS;
the assumptions register has a row for every input any rule relies on; and the threat model's
residual list has been reviewed by someone who did not write it.
