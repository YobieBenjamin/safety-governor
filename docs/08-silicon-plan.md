# 08 · The silicon plan: from RTL to a chip you can hold

This document is the path from the design in this repository to a governor module in a
rack beside NVIDIA GPUs. It has three legs. **Leg A** is a prototype of the governor core on
an open 130 nm process through a multi-project-wafer shuttle, using only open tools, so
anyone can reproduce it. **Leg B** is the product governor die on a 22 nm process with hard
IP for the PCIe and fabric PHYs, the crypto engines and the non-volatile memory. **Leg C**,
the plan of record, is that die on a management module that plugs into the rack's system
board (or is soldered on the GPU baseboard), wired to each GPU slot's levers and to the
management buses of the NVSwitch chips, the PCIe switch and the DPU. The RTL, the firmware,
the policy format and the fabric protocol are the same on all three legs. Nothing in the GPU
changes.

In plain words: first a working model built from parts anyone can buy, on a shared ride to the
fab so it costs thousands, not millions. Then the real part. Then the real part in the room
next door to the GPUs, holding the keys to the doors.

> **Plain-English version:** `10-plain-english-walkthrough.md` §13.
> **Backed by:** `rtl/governor_rtl/*.py` and the generated `rtl/gen/*.v` (`make rtl`),
> `hw/librelane/governor_core/config.json` and `hw/README.md` (`make gds`),
> `hw/pinout/governor_module.csv`, `hw/pcb/rack-integration.md`; the tape-out checklist is §5
> of this document.

## 1. Build strategy: stand on an open root of trust

The governor needs a measured-boot core, fuses, a lifecycle controller, a key manager that
does DICE-style derivation, SHA-256/HMAC, AES, a big-number engine for P-256 and P-384, and an
entropy source. That is, almost exactly, the block list of [OpenTitan](https://opentitan.org/),
the open-source silicon root of trust. OpenTitan is real silicon, not a paper design: the Earl
Grey chip taped out in November 2023, validated chips were commercially available in February
2024, production fabrication began in February 2025 at Nuvoton ([Google's announcement](https://opensource.googleblog.com/2025/02/fabrication-begins-for-production-opentitan-silicon.html)),
and OpenTitan shipped in Chromebooks in March 2026 ([OpenTitan's own history](https://opentitan.org/history/)). The
governor is therefore built as **OpenTitan's Earl Grey subsystem plus the governor blocks**:

| From OpenTitan (Apache 2.0) | Governor blocks (this repository) |
|---|---|
| Ibex RISC-V core (runs the control firmware) | Gate core accelerator (rule CAM, comparators) |
| OTP controller, lifecycle controller | Capability table (the source of truth for every switch port and flow the governor has opened) |
| Key manager (DICE-style CDI derivation) | Monotonic counter with fuse-backed high-water mark |
| HMAC/SHA-256, AES (ECB, CBC, CFB, OFB, CTR), KMAC, OTBN with its crypto library (ECDSA P-256 and P-384, Ed25519 and X25519, RSA, SHA-256/512, SHA-3/SHAKE; ML-DSA and ML-KEM are being built for the next OTBN generation, not in Earl Grey silicon) | Epoch register with no host write path |
| CSRNG and entropy source with health tests | Used-ticket store (cuckoo table) |
| SPI device, I2C, GPIO, UART, timers, alert handler | Heartbeat timer, halt sequencer, loop driver and sense |
| Flash controller (product leg) | Meter counters |
| | Signed mailbox FSM, sticky alarm register, log engine |
| | Fabric MAC (SGMII/100BASE-T1) and message engine |

Why: the hardest blocks to get right (fuses, lifecycle, key derivation, side-channel
hardened crypto) are the ones a small team should not write from scratch, and the governor's
own blocks are small, boring and provable. The RTL in `rtl/governor_rtl/` is exactly that
second column, written to drop into OpenTitan's TileLink fabric as peripherals.

## 2. Leg A: the prototype on SkyWater sky130

### 2.1 Process and tools

| Item | Choice | Note |
|---|---|---|
| Process | SkyWater SKY130 (sky130A open PDK), 130 nm, 5 metal layers, 1.8 V core, IO up to 5 V (the harness runs it at 3.3 V) | The open process with the longest shuttle history and the deepest open-tool support; IHP's SG13G2 and GF180MCU are the other open PDKs |
| Standard cells | `sky130_fd_sc_hd` (high density) | 50 MHz target is easy |
| SRAM | OpenRAM-generated macros (e.g., 32 × 1 KB) | Open, tested on sky130 shuttles |
| Fuses / OTP | **No open OTP macro on sky130.** The PDK has ReRAM primitives and a SONOS cell, but neither is a qualified key store. The prototype holds the UDS in a provisioning register written at power-up by an external secure element over SPI, and emulates the anti-rollback counter in authenticated external flash | The prototype proves function, not tamper resistance. Leg B uses real OTP |
| NVM | External SPI NOR flash, encrypted and authenticated with a DICE-derived key | Same as above |
| PHYs | None in the open sky130 PDK. Host interface is SPI; fabric is RS-485 or 100BASE-T1 through an external transceiver; loop pins are GPIO with an external comparator | PCIe and SGMII arrive in Leg B |
| Flow | [LibreLane](https://librelane.readthedocs.io/) (Yosys, OpenROAD, Magic, KLayout, Netgen, OpenSTA), the successor to OpenLane 2 maintained under the FOSSi Foundation after Efabless closed | `hw/librelane/governor_core/config.json` |
| Harness | A shuttle harness (Caravel-class: pad frame, management core, seal ring) with a ~10 mm² user area, or Tiny Tapeout tiles for individual blocks | Both are open; the harness supplies pads, ESD, the seal ring and the scribe |

### 2.2 The flow, step by step

```
rtl/governor_rtl/*.py ──(amaranth)──► rtl/gen/governor_core.v
        │
        ▼  make gds   (LibreLane, Dockerized: pip install librelane; librelane --dockerized ...)
 1. synthesis        Yosys + ABC: Verilog → sky130 gate netlist; area and cell report
 2. floorplan        OpenROAD: die/core area from config; pin placement from hw/pinout; power grid (met4/met5 straps); tap and decap cells
 3. placement        global (RePlAce), resizing, detailed placement; timing-driven
 4. CTS              TritonCTS clock tree on the 50 MHz clock; hold fixing
 5. routing          FastRoute global, TritonRoute detailed; antenna diode insertion
 6. extraction       OpenRCX parasitics → SPEF
 7. timing signoff   OpenSTA at the PDK corners (tt, ss, ff): setup, hold, max cap, max slew
 8. physical signoff Magic DRC and KLayout DRC against the sky130 deck; Netgen LVS netlist vs. layout; antenna check; density/fill (metal fill inserted)
 9. power signoff    IR drop and EM estimate on the straps (OpenROAD psm)
10. GDSII            Magic streams out governor_core.gds (and .lef/.def for the harness); KLayout XOR against the harness template
```

The outputs that go to the shuttle are the GDS of the user project, the LEF, the netlist
for LVS, and the signoff reports. The shuttle operator merges every rider's GDS onto one
reticle, runs the foundry's own DRC once more, and sends the merged GDS for mask data
preparation.

### 2.3 Lithography, in plain words and in detail

A chip is printed, layer by layer, like a photograph with dozens of exposures. The GDS file is
the set of negatives. Each layer of the GDS (diffusion, polysilicon, contacts, five metals,
vias, implants) becomes one **photomask**: a quartz plate with the pattern in chrome. In the
fab, a wafer is coated with photoresist, the mask's pattern is projected onto it with
ultraviolet light through a reduction lens (the mask is drawn 4× larger than the printed
feature), the exposed resist is developed, and the wafer is etched, implanted or plated
through the openings. Then the next layer. Sky130 is a mature node with relaxed design
rules, printed with conventional deep-ultraviolet steppers, no immersion and no
multi-patterning, which is why the open tools can meet its rules.

What the design has to deliver for the masks to be makeable:

| Item | Meaning | Who does it |
|---|---|---|
| DRC-clean GDS | Every polygon obeys the process's width, spacing, enclosure and density rules | us (LibreLane signoff) |
| LVS-clean | The layout is electrically the netlist we simulated | us (Netgen) |
| Antenna-clean | No gate is connected to a long metal run that collects charge during etching without a diode to drain it | us (LibreLane inserts diodes) |
| Metal fill | Every layer has the density the chemical-mechanical polishing step needs | us (LibreLane fill) |
| Layer map | GDS layer numbers mapped to the foundry's mask layers | PDK provides |
| Seal ring, scribe, alignment marks, pad frame | The frame that lets the fab cut and test the die | the shuttle harness provides |
| Mask data preparation | Fracturing polygons into the mask writer's primitives; optical proximity correction (OPC) so the printed shape matches the drawn shape | the foundry and mask shop |
| Reticle assembly | Placing every rider's die on the 20 × 20 mm-class reticle field | the shuttle operator |

In plain words: we deliver a clean negative. The fab makes the stencils and does the printing.
On a shuttle we share the stencils with other riders, which is why it costs thousands instead
of the hundreds of thousands a private mask set costs even at 130 nm.

### 2.4 Shuttle options for Leg A

| Route | Area | Cost class | Notes |
|---|---|---|---|
| sky130 MPW slot from ChipFoundry, the company Efabless's founders started after Efabless closed in March 2025 (first sky130 tapeout September 2025; shuttles run when at least half the slots are sold), on a Caravel-class harness | up to about 15 mm² of die per slot (a Caravel-class user area is about 10 mm²), 38 user IO | low five figures per slot (ChipFoundry lists $14,950), packaged parts returned | Enough for the whole governor core plus OpenRAM macros; this is the plan of record |
| Tiny Tapeout, which continued after Efabless closed, on IHP SG13G2 and, through ChipFoundry, sky130 | tiles of about 0.016 mm² (160 × 100 µm), 24 GPIO per tile (8 in, 8 out, 8 bidirectional) | hundreds of dollars per tile | For individual blocks (the halt loop, the monotonic counter, the capability checker) as early silicon proof of the invariants |
| IHP SG13G2 open shuttle (130 nm BiCMOS, open PDK) | per-run allocation | low five figures | A second open process with an open PDK and its own OpenLane support; an alternative if sky130 capacity is short |

### 2.5 Package, board, bring-up

- **Package.** The harness's standard QFN (prototype); no custom package work.
- **Prototype board.** `hw/pcb/` describes a reference carrier for the prototype: the
  governor, an external secure element for provisioning, SPI flash, an RS-485 or 100BASE-T1
  transceiver pair for the fabric, the loop comparator, the hot-swap controller whose EN pin
  the governor drives, the three wires to a PCIe GPU slot (PWRBRK#, PERST#, SMBus), and an
  I2C/MDIO header for a PCIe switch's management port. A second connector carries the loop
  and the fabric to the next board. The rack module of Leg C is the same circuit on the
  management-module form factor.
- **Bring-up plan.** (1) Power, clock, JTAG in TEST lifecycle. (2) Firmware boot, measurement
  registers, DICE derivation against the model's test vectors. (3) Mailbox round trips from a
  host over SPI. (4) Levers against a real GPU: throttle, reset, power cut, with the GPU
  running a benchmark that ignores software. (5) Two boards: loop and fabric; roster; halt
  propagation on an oscilloscope. (6) Eight boards: epoch change, partition, shared budget.
  (7) Lifecycle advance to PRODUCTION on one part; confirm JTAG refuses.

### 2.6 Schedule and cost (Leg A)

| Phase | Duration | Cost class |
|---|---|---|
| RTL completion and block-level verification (this repository → full peripheral set on OpenTitan) | 3 months | engineering time |
| Flow bring-up, signoff, shuttle submission | 2 months | one shuttle slot |
| Fab, package, return | 4 to 6 months | included in the slot |
| Pairing board (two spins) | parallel | low five figures |
| Bring-up and the Phase 2 measurements | 3 months | engineering time, a node with real GPUs |

About a year to a measured prototype, for a cost dominated by people, not masks.

## 3. Leg B: the product chip

| Item | Choice | Why |
|---|---|---|
| Process | 22 nm FD-SOI (GlobalFoundries 22FDX) first choice; 16/12 nm FinFET if PCIe Gen 4/5 PHYs demand it | FD-SOI gives low leakage, embedded MRAM for the NVM, body-bias for power, and mature security IP; the governor is small and does not need a leading node |
| NVM | Embedded MRAM (22FDX) or eFlash | On-die, authenticated; removes the prototype's external-flash weakness |
| OTP | Foundry anti-fuse OTP macro | Real fuses for the UDS, anti-rollback and lifecycle |
| PHYs | PCIe Gen 3 x1 (host mailbox), 2 × SGMII (fabric), licensed hard IP; I2C/I3C, SMBus and MDIO masters for the switch management buses | The interfaces 130 nm cannot provide |
| Crypto | OpenTitan engines synthesized for the node; side-channel countermeasures enabled | Same RTL as Leg A |
| Security physical design | Active mesh shield on the top metal; voltage, clock and temperature sensors; light sensor; glitch detectors; key SRAM with scrambling; zeroization on alert | R5 in the objectives |
| Package | BGA-169, 10 × 10 mm | Fits a GPU baseboard footprint |
| Qualification | AEC-Q100-style temperature cycling and HTOL as a data-center analogue; IEC 61508 SIL 2 hardware metrics (probability of dangerous failure per hour, safe failure fraction, hardware fault tolerance), with the dangerous-failure budget expressed in FIT | The nuclear-plant analogy demands the nuclear-plant paperwork |
| Flow | Commercial (Synopsys or Cadence) with the foundry PDK under NDA; the same RTL, the same tests | Open tools do not yet carry commercial PDKs |

Mask set and NRE at 22 nm are in the low millions; engineering is the larger cost. Timeline:
18 to 24 months from a validated Leg A prototype to qualified product silicon.

## 4. Leg C: the rack module, the plan of record

The product die from Leg B goes onto a management module and into the rack. No GPU silicon
changes; the work is board and integration work.

| Work item | Who | What it is |
|---|---|---|
| Governor module | this project with a board partner | A DC-SCM-class card: the governor die, an SPI flash, the fabric transceivers, the loop comparator, the per-slot lever drivers, I2C/SMBus and MDIO masters for the switch management buses; the standard management-module connector carries PCIe x1 (mailbox), I2C/I3C, GPIO and power |
| Baseboard integration | the OEM or the system integrator, and NVIDIA for what is on the HGX baseboard | On PCIe-card servers: each slot's PWRBRK#, PERST#, PWR_EN and management bus routed to the module connector. On HGX: the management bus to the GPUs and the HMC and the reset and power signals the baseboard exposes at its connector, routed to the module; anything on the baseboard itself (a soldered governor, the per-slot signals the connector does not carry, the NVSwitch management bus with the governor as the only master) is NVIDIA's board and needs NVIDIA. The PCIe switch management port assigned to the governor |
| Switch-tray and DPU governors | this project with the tray and DPU board owners | The same die on each NVLink switch tray's management board and on the DPU board; fabric and loop routed through the rack alongside the management network, on their own wires |
| Rack cabling | the integrator | The halt loop and the dual-ring fabric through the rack: two connectors per tray, a jumper plug on the last tray; loop continuity is part of the rack's power-on test |
| Firmware for the management interfaces | this project | Drivers for the GPU post-box interface, the NVSwitch management bus, the PCIe switch management port and the DPU out-of-band port, each as a small, verified, write-only-by-governor driver |
| Co-verification | both | The hypothesis catalogue run against the integrated rack simulation (Phase 2 of the experiment program in the companion repository), then against a real node, then against a real rack |
| Qualification | the integrator | Rack-level safety qualification per IEC 61508 practice: FMEA of the loop and the levers, proof-test interval for the halt path, FIT budget for the module |

The asks to NVIDIA that would tighten the result (a manifest digest in the attestation
report, Fabric Manager honouring a governor-signed partition, an out-of-band port disable on
NVSwitch, a halt message to the GSP, and later descriptor-level checkers) are listed in
`03-interfaces.md` §9. None of them gates Leg C.

## 5. Tape-out checklist (Leg A)

- [ ] All `tests/` pass at the rack tier with the descriptor-level residual of H2 recorded as the known gap
- [ ] All `rtl/tests/` pass; invariants in `07-verification-plan.md` §3 hold in simulation
- [ ] Generated Verilog in `rtl/gen/` matches the Amaranth sources (CI regenerates and diffs)
- [ ] LibreLane: synthesis clean, no latches, no combinational loops
- [ ] Timing: setup and hold met at tt, ss, ff with 10 % margin at 50 MHz
- [ ] DRC: Magic and KLayout clean on the sky130 deck
- [ ] LVS: Netgen clean
- [ ] Antenna: clean after diode insertion
- [ ] Fill and density: within the deck's windows on every layer
- [ ] IR drop under 5 % of VDD on the core grid
- [ ] Pin placement matches the harness template; GDS XOR against the template clean outside the user area
- [ ] Lifecycle fuse emulation verified: TEST allows JTAG; PRODUCTION refuses and logs
- [ ] Firmware image measured; DICE test vectors match the functional model
- [ ] Provisioning procedure for the external secure element written and rehearsed
- [ ] The assumptions register row for "prototype holds the UDS in a provisioning register" present and marked as a prototype-only weakness
