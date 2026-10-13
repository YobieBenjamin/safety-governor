# 01 · Architecture

> **In plain words:** the GPU is the star employee with no alarm bell wired in; the governor
> is the security office next door. This document says where that office is, what is in it,
> how it opens in the morning, what a working day looks like, and how it shuts everything down.
> **Plain-English version:** `10-plain-english-walkthrough.md` §2 to §5.
> **Backed by:** model `govsim/governor.py`, `govsim/cluster.py` (`build_rack`); hardware
> `rtl/governor_rtl/top.py` (`GovernorCore`) and the blocks named in the table below; wiring
> `hw/pcb/rack-integration.md`; tests `tests/test_h01`, `h11`, `h14`, `h16`.

## Where the governor lives

A modern AI rack is a stack of boards. The system board (the motherboard) with its
management-module slot, the PCIe switches, the DPU or NIC and the power shelf are the OEM's,
and they already carry control hardware that is not NVIDIA's: a BMC, a root of trust,
hot-swap controllers, switch management. The HGX baseboard, with the GPUs, the NVSwitch chips
and its hardware management controller (HMC), is NVIDIA's, and what the system board can
reach on it is what its connector exposes: the management bus to the GPUs and the HMC, and
the reset and power signals the OEM wires. The governor is added at the OEM's level and
reaches the baseboard through that connector. On servers built from PCIe-card GPUs the
slots are on the OEM's board and every lever is the OEM's to wire.

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

![Where the governor goes in the rack](figures/fig-rack.png)

One governor instance per GPU slot. Physically, a governor chip serves the slots on one
baseboard (up to eight channels on an HGX board, four on an NVL72 compute tray), with a
dedicated lever channel and management-bus channel per slot, so that each GPU still has its
own identity record, its own budgets and its own halt rung. NVLink switch trays and the DPU
get governors of their own. The governor is a PCIe endpoint behind the PCIe switch (or an
SMBus device on the smallest boards) so the host can deliver attestation evidence and
requests to its mailbox. Soldering the governor onto the HGX baseboard beside the HMC, with
the per-slot signals routed directly, is the shortest wiring; it is an ask to NVIDIA, not a
plan-of-record assumption, because the baseboard is theirs.

In plain words: the GPU is the star employee with no alarm bell wired in. The governor is the
small security office next door, with a copy of the rulebook, the employee's badge photo, a
log book, the key to the breaker panel, the keys to the doors between buildings, and a phone
line to every other security office in the complex that the tenants cannot tap. It rents the
room next door; it does not ask the landlord to rebuild the building.

## Blocks

![The governor die: five regions](figures/fig-die.png)

| Block | Function | Reference |
|---|---|---|
| **Fuses (OTP)** | Unique device secret, anti-rollback counter, lifecycle state (test, production, decommissioned), governance key hashes, configuration | `govsim/fuses.py`; `rtl/governor_rtl/monotonic.py`, `lifecycle.py` |
| **Silicon root** | Measured boot, extend-only measurement registers, DICE key derivation, quote engine, TRNG, monotonic counter (ticked and persisted; stamps messages, records and tickets) | `govsim/root.py`; `rtl/governor_rtl/measure_reg.py`, `monotonic.py` |
| **Crypto engines** | SHA-256/384, HMAC, AES (CTR and CBC; authenticated with HMAC), ECDSA P-256 and P-384 on an OTBN-class coprocessor, TRNG. Integrated IP, not designed here | spec in `04-specification.md` §7 |
| **Verifier** | Checks the paired GPU's confidential-computing attestation report and the host enclave's report against reference values signed by the governance root; at model load issues the workload token: the workload measurement `H(gpu firmware, host firmware, model manifest)` keys the rulebook and the fingerprint `H(workload, policy epoch)` binds tokens and tickets | `govsim/governor.py` (`_cmd_verify_gpu`, `_cmd_verify_host`, `_cmd_begin_model`) |
| **Policy store + epoch register** | Holds the accepted policy image; epoch is its digest in a register with no host write path (`Governor.epoch` is a read-only property that only `_accept_policy` moves) | `govsim/policy.py`; `rtl/governor_rtl/epoch_reg.py` |
| **Gate core** | Default-deny rulebook: workload measurement × action → rule, exact before wildcard; typed limits; lane (`auto`, `observer`, `human`); witnesses; budget; endpoint binding; mints tickets or parks holds | `govsim/governor.py` (`_cmd_request`, `_cmd_approve`) |
| **Ledger** | Durable budgets, reservations, rate windows, replay store; owner of its budget keys; fabric protocol for shared keys | `govsim/ledger.py` |
| **Ticket store** | Durable used-ticket set for the governor's own endpoint role and for tickets it verifies on behalf of local devices | `rtl/governor_rtl/ticket_store.py` |
| **Switch management and the capability table** | The rack tier's enforcement points: which NVSwitch ports, PCIe switch ports and NIC flows are open, to which roster peer, until when; programmed through the switches' management interfaces with the governor as the only writer | `govsim/endpoints.py`; `rtl/governor_rtl/cap_table.py` |
| **Hash-and-sign engine** | Hashes what the verified runtime presents; signs device-provenance records (batched under one signature per window, `04-specification.md` §9) and log checkpoints; at the rack tier cross-checks the bytes that left for the host through the PCIe switch port against the bytes presented | `govsim/governor.py` (`_cmd_sign_output`, `_check_unpresented_output`) |
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
        ──► halt loop: switch open; it closes when the governor is armed (no open cause, a
            valid heartbeat), and the governor goes to RUN when it then sees loop current
        ──► fabric: announce identity (quote over nonce) ──► wait for roster
```

![Boot and the DICE key chain](figures/fig-boot.png)

The governor comes up *halted*: brake and reset asserted, slot power off, every governed
port closed, loop switch open. Nothing it governs may run until the policy authority has
said hello, every governor in the domain has closed its switch, and the roster has formed.
If the governor went down with an open safe-mode cause, the cause is durable and it comes
back on the same rung with its switch open; a power cycle does not clear a halt. In plain
words: the building opens when the fire marshal has checked the alarm, not before.

## Job lifecycle

1. **Attest.** The host delivers the GPU's confidential-computing attestation report
   (obtained in-band through the driver, exactly as today) and the CPU enclave's report to
   the mailbox. The verifier checks both against pinned reference values, with a nonce the
   governor chose, and signs the result. The host enclave's key established here is what
   must sign every later request. Analogy: the bouncer compares the face with the photo book
   he carries; he does not take the guest's word.
2. **Roster.** Governors of the GPUs in the job exchange quotes over the fabric and build a
   roster with a job id and an expiry. The governor then opens exactly the NVSwitch ports,
   PCIe switch paths and NIC flows that connect roster members, and no others. Analogy: roll
   call with ID badges before the bus leaves, and only then do the doors between the
   buildings unlock, for those people.
3. **Load.** The weight loader inside the CPU enclave asks for the model key. The governor
   releases it only to a verified enclave, under a current epoch, for a manifest the
   governance root's publisher keys have signed. The manifest digest completes the workload
   measurement and the governor issues the workload token. Analogy: the safety-deposit box
   needs the bank's key and yours, turned together.
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

![The safe-mode ladder](figures/fig-safe-mode.png)

The order is deliberate. Closing the ports and braking the power is reversible and loses
nothing. A reset loses the job. A power cut is the floor. Which rung a given cause starts on
is a policy field, because the safe transition is an application decision: a training job can
be reset; a GPU driving a surgical robot's planner should be throttled while the robot
completes its controlled withdrawal, then reset.

Which causes open the loop is also deliberate. Loop-opening causes (the loop itself opening,
a detected tamper, a signed HALT) stop the whole domain. Local causes (a lost heartbeat, a
stale epoch, an exhausted output budget) throttle this governor's own slot and climb the
rungs on the policy's timers without opening the loop, so one governor's lost heartbeat does
not stop the rack. The open cause and the rung are durable: a power cycle brings the governor
back on the same rung.

No rung can be climbed back up by the governor alone. CLEAR is a signed command from the
policy authority, accepted only after the cause has been written to the log and the log
checkpoint has been acknowledged by at least one fabric neighbor. Analogy: only the fire
marshal resets the alarm, and only after the report is filed.

## Tiers

| Tier | Where | Enforcement | Status |
|---|---|---|---|
| **Rack (plan of record)** | Governor module on the system board, lever and management channels to each slot through the baseboard connector, management authority over the PCIe switch and the DPU, partition authority over NVSwitch through Fabric Manager | Link-level: ports and flows open only between roster members under a current epoch and a live heartbeat; levers per slot where exposed; attestation, tickets, budgets, log, meter | Buildable now on the OEM's boards; on HGX the per-slot signals the baseboard does not expose are an ask |
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
