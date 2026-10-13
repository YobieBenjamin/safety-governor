# Rack integration reference

How the governor module goes into a rack built from NVIDIA GPUs, baseboards and switches
exactly as they ship. For the system integrator and the baseboard OEM. The electrical
details here are the design intent; the exact connector pins come from the board's own
documentation.

## 1. Where the module sits

| Board | What goes there | Why |
|---|---|---|
| System board (motherboard) | The governor module in the management-module slot (DC-SCM-class), or as a mezzanine on the existing module | The slot already carries PCIe, I2C/I3C, GPIO and a sideband to the board; it is how control hardware is added without a board redesign |
| GPU baseboard (HGX / NVL tray) | Either routed from the module through the baseboard connector, or the governor die soldered beside the baseboard's management controller | The per-slot signals and the NVSwitch management bus live here |
| NVLink switch tray | A governor beside the tray's management controller | Owns the tray's switch ports |
| DPU board | A governor on the DPU's board, or the DPU's own root of trust running the governor firmware | Owns the filter tables |

## 2. Per GPU slot (× 8 on an HGX baseboard)

| Signal | From | To | Notes |
|---|---|---|---|
| GPU post-box management bus (SMBus/I2C) | governor I2C master | GPU module | The governor is the only master. The BMC's access to the GPU is routed through the governor as a pass-through that the governor can refuse |
| PWRBRK# (PCIe form factor) or the baseboard's power-brake signal (SXM) | governor open-drain | GPU | Asserted at power-on; released in RUN |
| PERST# | governor open-drain | GPU | Asserted at power-on; released in RUN after bring-up |
| PWR_EN | governor push-pull | slot hot-swap controller / e-fuse enable | Where the baseboard has per-module power control. Boards with shared rails: PWR_EN is not connected and the policy records "no slot power cut" for that board, so the floor is reset |
| Slot present, slot fault | slot | governor GPIO | Presence and fault inputs for the roster and the log |

## 3. Switch management buses

| Switch | Bus | Governor's role |
|---|---|---|
| NVSwitch chips on the baseboard | The NVSwitch out-of-band management bus (same family as the GPU's), plus the reset lines | Only master; reset, power and telemetry today; port disable and partition when the firmware ask in `docs/03-interfaces.md` §9 is met; Fabric Manager's in-band path is unchanged |
| PCIe switch on the system board | The switch's management port (I2C/SMBus or MDIO) and its reset | Only master; downstream port enable per slot, ACS, port isolation |
| DPU | The DPU's out-of-band management port | Signed filter-table commands via the DPU governor |

The BMC keeps its own buses to everything else. Where a BMC previously owned one of the
buses above, it now reaches that device through the governor, which forwards reads and
refuses writes that are not its own.

## 4. The two cluster wires

| Wire | Physical | Routing | Notes |
|---|---|---|---|
| Halt loop | Series current loop, 4 to 20 mA class, one twisted pair | LOOP_OUT of governor N to LOOP_IN of governor N+1 through every tray in the domain, back to the domain's supervisor governor | A jumper plug terminates the last tray. Broken loop = halt. Loop continuity is part of the rack's power-on self-test |
| Message fabric | Dual ring, 100BASE-T1 (two-wire) or SGMII over the rack's existing management cabling but on separate pairs | Ring A clockwise, ring B counter-clockwise through the trays | No connection to the management network's switches; a governor-to-governor wire only |

Both wires leave each tray on one small connector next to the management connector; the
rack harness carries them tray to tray.

## 5. Power-on sequence

1. Rack power on. Governors boot halted: every slot's PWRBRK# and PERST# asserted, PWR_EN
   low, every governed switch port closed, loop switches open.
2. Governors measure boot, derive keys, load their policy image from NVM, and verify it.
3. The rack's loop continuity test passes (every governor's LOOP_OUT closed only after step
   2 succeeds; a governor that failed to boot keeps the loop open and the rack does not start).
4. The policy authority's first heartbeat enters at the supervisor governor and fans out.
   Armed governors see loop current and go to RUN: PWR_EN high, PERST# released after the
   slot's power-good, PWRBRK# released.
5. The host boots, the driver attests each GPU, the governors verify and form the roster, the
   switch ports open for roster members, the model key is released, the job starts.

## 6. The prototype board (Leg A)

A small carrier with the sky130 prototype: SPI to a host adapter, one GPU slot's three
signals and SMBus on a header, a PCIe switch management header, the loop comparator and
switch, two RS-485 transceivers for the fabric, an external secure element for provisioning
and an SPI flash. Two of these, a PCIe GPU in a workstation, and a PCIe switch evaluation
board are enough for the bring-up plan in `docs/08-silicon-plan.md` §2.5.
