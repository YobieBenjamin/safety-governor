# 01 · Architecture

## Where the governor lives

A modern AI rack is a stack of boards the GPU vendor does not own outright: the system
board (the motherboard) with its management module slot, the GPU baseboard with its
management buses and the NVSwitch chips, the PCIe switches, the DPU or NIC, the power shelf.
Every one of those boards already carries control hardware that is not NVIDIA's: a BMC, a
root of trust, hot-swap controllers, switch management. The governor is added at that level.

```
 RACK
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  compute tray / node                                                         │
 │  ┌───────────────────────────────────────────────────────────────────────┐   │
 │  │ system board                                                          │   │
 │  │   CPU (TEE) ── PCIe switch ── DPU / NIC ── (network, storage)         │   │
 │  │                   │  ▲ port enable, ACS            ▲ filter tables    │   │
 │  │  ┌────────────────┴──┴─────────────────────────────┴──────────────┐   │   │
 │  │  │ SAFETY GOVERNOR module (DC-SCM-class slot, or soldered)        │   │   │
 │  │  │ one governor instance per GPU slot · fuses · root · verifier  │   │   │
 │  │  │ policy+epoch · gate core · ledger · log · meter · heartbeat   │   │   │
 │  │  │ halt loop · fabric · lever channels · switch management       │   │   │
 │  │  └───┬───────────┬───────────┬───────────────────────────────────┘   │   │
 │  └──────┼───────────┼───────────┼───────────────────────────────────────┘   │
 │         │ per slot: │ SMBus     │ PWRBRK# · PERST# · PWR_EN                  │
 │  ┌──────┴───────────┴───────────┴──────────────────────────────────────┐    │
 │  │ GPU baseboard (HGX / NVL)                                           │    │
 │  │   GPU0 … GPU7  ══ NVLink ══ NVSwitch × N  ◄── port enable, partition │    │
 │  └─────────────────────────────────────────────────────────────────────┘    │
 │         halt loop ─────────────────────────────── message fabric             │
 └────────────┼──────────────────────────────────────────────┼──────────────────┘
              ▼ to every other tray, the NVLink switch trays, the power shelf   ▼
```

One governor instance per GPU slot. Physically, a governor chip serves the slots on one
baseboard (eight channels on an HGX board, two or four on an NVL compute tray), with a
dedicated lever channel and management-bus channel per slot, so that each GPU still has its
own identity record, its own budgets and its own halt rung. NVLink switch trays and the DPU
get governors of their own. The governor is a PCIe endpoint behind the PCIe switch (or an
SMBus device on the smallest boards) so the host can deliver attestation evidence and
requests to its mailbox.

In plain words: the GPU is the star employee with no alarm bell wired in. The governor is the
small security office next door, with a copy of the rulebook, the employee's badge photo, a
log book, the key to the breaker panel, the keys to the doors between buildings, and a phone
line to every other security office in the complex that the tenants cannot tap. It rents the
room next door; it does not ask the landlord to rebuild the building.

## Blocks

| Block | Function | Reference |
|---|---|---|
| **Fuses (OTP)** | Unique device secret, anti-rollback counter, lifecycle state (test, production, decommissioned), governance key hashes, configuration | `govsim/fuses.py`; `rtl/governor_rtl/monotonic.py`, `lifecycle.py` |
| **Silicon root** | Measured boot, extend-only measurement registers, DICE key derivation, quote engine, TRNG, monotonic counter | `govsim/root.py`; `rtl/governor_rtl/measure_reg.py` |
| **Crypto engines** | SHA-256, HMAC, AES-GCM, ECDSA P-256 and Ed25519 (OTBN-class), TRNG. Integrated IP, not designed here | spec in `04-specification.md` §7 |
| **Verifier** | Checks the paired GPU's confidential-computing attestation report and the host enclave's report against reference values signed by the governance root; issues the workload token with the fingerprint `H(firmware, model manifest, policy)` | `govsim/governor.py` (`Verifier`) |
| **Policy store + epoch register** | Holds the accepted policy image; epoch is its digest in a register with no host write path | `govsim/policy.py`; `rtl/governor_rtl/epoch_reg.py` |
| **Gate core** | Default-deny rulebook: fingerprint × action → rule; typed limits; lane (`auto`, `observer`, `human`); witnesses; budget; endpoint binding; mints tickets or parks holds | `govsim/governor.py` (`GateCore`) |
| **Ledger** | Durable budgets, reservations, rate windows, replay store; owner of its budget keys; fabric protocol for shared keys | `govsim/ledger.py` |
| **Ticket store** | Durable used-ticket set for the governor's own endpoint role and for tickets it verifies on behalf of local devices | `rtl/governor_rtl/ticket_store.py` |
| **Switch management and the capability table** | The rack tier's enforcement points: which NVSwitch ports, PCIe switch ports and NIC flows are open, to which roster peer, until when; programmed through the switches' management interfaces with the governor as the only writer | `govsim/endpoints.py`; `rtl/governor_rtl/cap_table.py` |
| **Hash-and-sign engine** | Hashes what the verified runtime presents; signs device-provenance records and log checkpoints | `govsim/governor.py` (`OutputPath`) |
| **Meter** | Tokens, kernel cycles and bytes per model digest, read from the GPU's management bus and the switch counters; read-only to the host | `rtl/governor_rtl/meter.py` |
| **Log engine** | Hash chain in the governor's own NVM; signed Merkle checkpoints; neighbor heads cross-linked | `govsim/log.py` |
| **Heartbeat** | Countdown from the last valid authority token; expiry triggers safe mode | `rtl/governor_rtl/heartbeat.py` |
| **Halt, throttle, power** | Per slot: drives PWRBRK#, PERST#, PWR_EN; drives and senses the halt loop | `rtl/governor_rtl/halt.py` |
| **Fabric port** | Two SGMII-class ports (dual ring) carrying signed messages; roster, epoch consensus, heartbeat fan-out, budget protocol, checkpoint exchange | `govsim/fabric.py` |
| **Mailbox** | The only input from the host: signed commands with sequence numbers; no writable registers | `rtl/governor_rtl/mailbox.py` |
| **Control firmware** | Verified-kernel-class, a few thousand lines: schedules the blocks, handles exceptions, never touches a data path | `04-specification.md` §8 |

## What the governor is not in the path of

Kernels, HBM, the KV cache, NVLink bandwidth, PCIe bandwidth. The governor programs switch
ports; it does not sit on them. Its work grows with boundary crossings and actions, never with
compute or with traffic volume. That is the single property that keeps the one-percent
target credible: a badge reader adds a fraction of a second at the door and nothing to the
work inside the room, and the governor is the office that programs the readers, not a guard
standing in the corridor.

## Boot

```
power on ──► ROM measures loader ──► extend M0 ──► loader measures firmware ──► extend M1
        ──► check anti-rollback ──► derive DICE key from (UDS, M0, M1)
        ──► load policy image from NVM ──► verify k-of-n ──► epoch := H(image)
        ──► all lever channels in the safe state; all governed switch ports closed
        ──► heartbeat timer armed (expired until first valid token)
        ──► halt loop: assert "open" until the policy authority's first heartbeat arrives
        ──► fabric: announce identity (quote over nonce) ──► wait for roster
```

The governor comes up *halted*. Nothing it governs may run until the policy authority has
said hello and the roster has formed. In plain words: the building opens when the fire
marshal has checked the alarm, not before.

## Job lifecycle

1. **Attest.** The host delivers the GPU's confidential-computing attestation report
   (obtained in-band through the driver, exactly as today) and the CPU enclave's report to
   the mailbox. The verifier checks both against pinned reference values, with a nonce the
   governor chose. It issues a workload token naming the fingerprint. Analogy: the bouncer
   compares the face with the photo book he carries; he does not take the guest's word.
2. **Roster.** Governors of the GPUs in the job exchange quotes over the fabric and build a
   roster with a job id and an expiry. The governor then opens exactly the NVSwitch ports,
   PCIe switch paths and NIC flows that connect roster members, and no others. Analogy: roll
   call with ID badges before the bus leaves, and only then do the doors between the
   buildings unlock, for those people.
3. **Load.** The weight loader inside the CPU enclave asks for the model key. The governor
   releases it only to a verified enclave, under a current epoch, for a manifest the
   governance root's publisher keys have signed. The manifest digest is folded into the
   fingerprint. Analogy: the safety-deposit box needs the bank's key and yours, turned together.
4. **Serve.** Kernels run with no gate. The verified runtime presents each response's bytes
   for a signed device-provenance record. The governor reads the meter from the GPU's
   management bus.
5. **Act.** The broker submits a typed request to the mailbox. The gate core answers its four
   questions, reserves the budget (at the owner, over the fabric if shared), and mints a
   ticket or parks a hold. The endpoint burns the ticket, commits, re-checks and acts.
6. **Meter.** Counters per model digest; a policy may require a license token above a
   compute threshold.
7. **Update.** A new policy image with k-of-n signatures arrives; the epoch moves
   rack-atomically (`02-safety-fabric.md`); tickets from the old epoch die.
8. **Stop.** A signed halt, a missed heartbeat, a loop break or a tamper event moves the
   governor to safe mode: ports closed and throttle first, then reset, then power cut, as the
   policy's safe transition for that GPU prescribes.

## Safe-mode state machine

```
             heartbeat ok, loop closed, epoch current, no tamper
   ┌──────────────────────── RUN ◄───────────────────────────────┐
   │ heartbeat expired            loop open / broken              │ signed CLEAR from authority,
   │ OR epoch stale               OR tamper detected              │ cause logged, loop closed
   ▼                              ▼                               │
 THROTTLE (ports closed,      ──► HALT (PERST# asserted) ──► SAFE (PWR_EN low) ──┘
   PWRBRK# asserted)
   t ≥ T_throttle without recovery      t ≥ T_halt without CLEAR
```

The order is deliberate. Closing the ports and braking the power is reversible and loses
nothing. A reset loses the job. A power cut is the floor. Which rung a given cause starts on
is a policy field, because the safe transition is an application decision: a training job can
be reset; a GPU driving a surgical robot's planner should be throttled while the robot
completes its controlled withdrawal, then reset.

No rung can be climbed back up by the governor alone. CLEAR is a signed command from the
policy authority, accepted only after the cause has been written to the log and the log
checkpoint has been acknowledged by at least one fabric neighbor. Analogy: only the fire
marshal resets the alarm, and only after the report is filed.

## Tiers

| Tier | Where | Enforcement | Status |
|---|---|---|---|
| **Rack (plan of record)** | Governor module on the system board, lever and management channels to each slot on the baseboard, management authority over NVSwitch, PCIe switch and DPU | Link-level: ports and flows open only between roster members under a current epoch and a live heartbeat; levers per slot; attestation, tickets, budgets, log, meter | Buildable now; needs nothing from NVIDIA |
| Board-only (fallback) | Same module, on a system where the switches' management is not reachable or a baseboard with direct NVLink and no NVSwitch | Levers, attestation, tickets, budgets, log, meter; no port authority | Buildable now |
| Integrated (future, not required) | Hooks inside the GPU: descriptor-level checkers and an inline output hash | Byte-level containment and device provenance of the bytes themselves | NVIDIA firmware and silicon; a footnote in `03-interfaces.md` §9 |

The same firmware, policy format, ticket format, fabric protocol and RTL blocks run on all
three. What changes between tiers is only how fine the enforcement is.

## Multi-GPU and multi-node

A frontier job spans 8 to 72 GPUs in a rack and many racks. The governor handles that with
one mechanism at every tier: the roster. Governors attest each other, form the roster, and
every later decision (ports, flows, budgets, epochs, halts) is scoped to it. Inside a
baseboard, NVLink traffic between GPUs passes the NVSwitch chips, whose ports the baseboard's
governor owns. Across trays in an NVL rack, NVLink passes the switch trays, whose governors
hold the same authority. Across racks, RDMA passes the DPU, whose governor programs the
filter tables. In plain words: one lifeguard per pool, all the lifeguards on the same whistle,
and the lifeguards hold the keys to the gates between the pools.
