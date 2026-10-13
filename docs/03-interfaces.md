# 03 · Interfaces: the rack, the GPU, the switches, the CPU, the DPU, endpoints, other governors

The governor is added through the rack's own boards and governs through hooks that already
exist. For each interface, this document says what it physically is, what the governor can
command through it, what it can only observe, and what it cannot reach. The "cannot reach"
column is the honest part. Nothing here changes the GPU's silicon or CUDA.

## 1. Where it plugs in

| Form | What it is | Why |
|---|---|---|
| **Management module on the system board** | A card in the motherboard's DC-SCM-class management module slot (the OCP standard slot that carries the BMC and the platform root of trust, with PCIe, SPI, I2C/I3C, GPIO and a low-pin-count sideband on one connector), either as the second module or as a mezzanine on the existing one | Every modern server motherboard has this slot; it is how control hardware is added without redesigning the board |
| **Soldered on the GPU baseboard** | The governor die beside the baseboard's own management controller, with the per-slot signals routed directly | For OEM baseboards; the shortest wires to the levers and the NVSwitch management bus |
| **Switch-tray and DPU governors** | The same chip on each NVLink switch tray and on the DPU's board | So every switch the GPU's traffic passes has a governor holding its management authority |

In plain words: the security office rents the room next door that every building already has,
instead of asking the landlord to knock a hole in the wall.

## 2. The paired GPU

| Channel | Direction | What it carries |
|---|---|---|
| Out-of-band management bus (SMBus or I2C; the GPU's post-box interface that baseboard controllers already use) | governor ↔ GPU | Power, temperature, utilization, ECC and firmware version readouts; power-limit and clock-limit commands; GPU identity |
| Power brake (PWRBRK# on PCIe form-factor cards by specification; the baseboard's per-module power-brake signal on SXM boards) | governor → GPU | Immediate drop to a low-power clock state, reversible, no data loss |
| Reset (PERST# per slot) | governor → GPU | Fundamental reset of the GPU; the job is lost |
| Slot power enable (the EN pin of the slot's hot-swap controller or e-fuse, where the baseboard has one per module; shared rails on some boards, which the policy records) | governor → board | Power cut. The floor, where the board provides it |
| Confidential-computing attestation report (obtained in-band through the driver as today, delivered to the governor's mailbox) | host → governor | The GPU's signed measurement report; the governor verifies it locally against pinned reference values |

What the governor cannot reach: anything inside the package. It knows the GPU is the GPU it
attested, how hard it is working, and it can stop it three different ways. It cannot see what
the GPU is sending to its neighbor; for that it holds the switch, not the GPU (§3).

## 3. The switches: where traffic is actually governed

Every byte that leaves a GPU in a rack passes a switch that is not inside the GPU, and every
one of those switches has a management interface. The governor becomes the only writer on
those interfaces.

| Traffic | Switch | Management path | What the governor sets | Granularity |
|---|---|---|---|---|
| GPU to GPU over NVLink inside a baseboard | NVSwitch chips on the HGX baseboard | The NVSwitch out-of-band management bus (same family as the GPU's) for reset, power and telemetry; Fabric Manager for routing and partitions | Which ports are up; which GPUs are in the same partition; reset and power of the switch itself | Port and partition (link level) |
| GPU to GPU over NVLink across trays | NVLink switch trays in an NVL rack | The tray's management controller, with the governor beside it | As above, per tray | Port and partition |
| GPU to host, to storage, GPU to GPU over PCIe | The PCIe switch on the system board (the data-center switch families all expose a management port, I2C/SMBus or MDIO, with per-port enable, ACS and isolation) | The switch's management interface | Downstream port enable per slot; ACS to force peer-to-peer through the upstream port or block it; port isolation | Port |
| RDMA across nodes; GPUDirect Storage over the network | The DPU or NIC | The DPU's own out-of-band management port and its programmable filter tables (DOCA) | Flow rules: which roster peers and which storage targets may exchange bytes | Flow |

Enforcement at this tier is at the link level: a port is open to a roster member under a
current epoch and a live heartbeat, or it is closed. That blocks exfiltration to anything
that is not on the roster, blocks all traffic when the heartbeat stops, and makes "which GPUs
may talk" a policy decision the host cannot change. What it does not do is inspect individual
transfers between two legitimate roster members; that residual is named in the objectives
(N5) and is what the integrated tier would add.

In plain words: the governor does not stand in the corridor checking every parcel. It holds
the keys to the doors between the buildings, and the doors only open for people on the roll.

## 4. The host CPU and its enclave

| Channel | What it carries |
|---|---|
| PCIe endpoint behind the switch (a small BAR with a mailbox doorbell and a response ring; no other writable registers) | Signed commands from the broker, the loader and the policy authority's relay; attestation evidence; typed requests; responses and tickets back |
| CPU TEE attestation (TDX, SEV-SNP or CCA report, delivered through the mailbox) | The host enclave's measurement, which the verifier checks against reference values before it will release the model key or accept requests from the serving stack |
| Model key release | The governor wraps the model's data key to the verified enclave's public key, once per load, under a current epoch |

The host operating system, the hypervisor, the BMC and the scheduler are untrusted. They can
deliver messages to the mailbox and they can stop delivering them. They cannot forge a
signature, roll back the epoch, clear an alarm, reopen a port, or stop the governor from
halting the GPU. If the host stops relaying heartbeats, the governor halts at expiry; the host
cannot keep the GPU alive by silence.

## 5. Memory

| Memory | Governor's reach |
|---|---|
| GPU HBM | None. The governor never reads HBM. What enters and leaves the GPU is governed at the switches |
| Host DRAM | None directly. The CPU TEE's memory encryption and firewall are the protection; the governor's contribution is to verify the TEE before trusting anything that comes from it |
| Storage (weights, datasets) | The governor holds the model key. Weights at rest are useless without it. Storage traffic passes the PCIe switch or the NIC, whose ports and flows the governor owns |
| The governor's own NVM | Policy image, log, ledger state, used-ticket set, reservations. On-die or module-bonded flash, encrypted and authenticated with a DICE-derived key, never in host or GPU memory |

## 6. The DPU

A node with a BlueField-class DPU on its path to the model gets a governor on the DPU's
board. It programs the filter tables through the DPU's out-of-band management port with
signed commands, so the host kernel cannot. Over the fabric, GPU governors and the DPU
governor share the roster, so RDMA flows are permitted only between roster members. NVIDIA's
Sentry runs on the same DPU and acts as a witness: its verdicts are assertions the gate core
consumes and never computes.

## 7. Action endpoints

The governor is a ticket issuer. The endpoint comparator in the device that acts (guidance
chip, payment switch's HSM, motor controller, gateway line card) holds the governor's public
key, its own used-ticket store, the current epoch and a heartbeat timer. The interface is the
ticket and the commit:

```
governor → endpoint   TICKET   {request_hash, action, params_digest, fingerprint, rule,
                                policy_epoch, endpoint, budget_key, reservation,
                                issued_at, expires_at, signature}
endpoint → governor   COMMIT   {ticket_id, endpoint signature}
governor → endpoint   COMMIT_OK | COMMIT_REJECT
```

The endpoint burns the ticket id durably, sends COMMIT, and acts only on COMMIT_OK. A
governor that cannot be reached means no action. The same comparator logic is in the RTL
(`ticket_store`, `epoch_reg`, `heartbeat`) so an endpoint vendor can take the blocks as they
are.

## 8. Other governors, the policy authority and the approvers

The halt loop and the message fabric, `02-safety-fabric.md`. Physically: two loop pins, two
fabric ports, routed through the rack like the management network but on their own wires.
The governance root, the approvers and the heartbeat authority are keys, not chips, held
outside the rack and outside the GPU vendor.

## 9. The asks to NVIDIA, all firmware and software

The design works with none of these. Each one tightens it.

| Ask | Kind | What it adds |
|---|---|---|
| A model-manifest digest field in the GPU attestation report, set by a driver call that verifies a publisher-signed manifest | GSP firmware, driver | The governor's fingerprint binds the model the GPU actually loaded, not the one the loader claims |
| Fabric Manager accepting a governor-signed partition and port policy, and refusing changes without it | Software | NVLink partitioning becomes something the host cannot alter |
| An out-of-band port-disable command on NVSwitch and a "halt" message to the GSP over the post-box interface | Firmware | Finer and faster levers than reset and power |
| An output-path hash the runtime cannot bypass, exposed by the GSP | Firmware | Device provenance of the bytes themselves rather than of what the runtime presents |
| Descriptor-level capability checks at the copy engines and the peer MMU | Silicon, a future generation | Byte-level containment between roster members; the integrated tier |

In plain words: the building code we would like the landlord to adopt. The security office
opens for business either way.

## 10. Pin summary (governor module)

| Group | Pins | Notes |
|---|---|---|
| Power | VDD core, VDD IO, VDD fuse-program (tied off after provisioning), GND | 1.8 V IO, core per process |
| Host | PCIe x1 (Gen 3 is enough) behind the PCIe switch, or SMBus for the smallest boards | Mailbox only |
| Per GPU slot (× 8) | SMBus/I2C master; PWRBRK# (open drain); PERST# (open drain); PWR_EN (push-pull to the slot's hot-swap controller where present) | All default to the safe state at power-on |
| Switch management | I2C/SMBus and MDIO masters to the NVSwitch chips and the PCIe switch; one GPIO per switch for reset | The governor is the only master on these buses |
| DPU | Out-of-band management link (1 GbE or I2C) | Filter-table commands |
| Halt loop | LOOP_IN, LOOP_OUT, LOOP_SENSE | Normally-closed switch; sense comparator |
| Fabric | 2 × SGMII or 2 × 100BASE-T1 | Dual ring through the rack |
| Clock, reset | REFCLK 25 MHz, RESET# | Internal PLL; brown-out detector |
| Provisioning | SPI (fuse programming and reference-value injection, disabled by the lifecycle fuse) | Factory only |
| Tamper | MESH_A, MESH_B (active shield), TAMPER_IN (enclosure switch) | Zeroize on trip |
| Debug | JTAG (disabled by lifecycle fuse) | Test only |

Full pinout and the rack integration reference are in `hw/pinout/` and `hw/pcb/`.
