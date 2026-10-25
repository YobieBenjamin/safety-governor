# 01 · The management slot: OCP DC-SCM 2.x, its DC-SCI connector and LTPI

> **Plain words first.** Most new servers have a slot for a small card that holds the board's management computer (the BMC). OCP standardised that card as the Datacenter Secure Control Module, DC-SCM, and its edge connector as DC-SCI. My plan of record puts the governor in that slot, or on a card that rides with the BMC card. This document takes every pin the governor has and says where it lands on that connector, cites the public document for each one, and says plainly which pins have no public home. The short version: the buses fit, the levers do not have pins of their own, they have to travel over LTPI (a serial link on the connector) to logic on the motherboard, and LTPI as written keeps a dead governor's levers where they were. I wrote down the requirement that fixes that.
>
> **Backed by:** `hw/pinout/dcscm_mapping.csv` (the mapping), `hw/pinout/dcsci_public_pins.csv` (the public pin facts it is checked against), `govsim/hardware_ref/dcscm.py` (the checker and the LTPI link-loss model), `tests/test_if_dcscm.py`. One command: `python -m govsim.hardware_ref.dcscm`.

## 1. What I read, and what I could not

| Document | What it gave me | How |
|---|---|---|
| OCP DC-SCM 2.2 Ver 1.0 (`DCSCM22`) | Signal groups and rules, sections 3.5.1 to 3.5.15; standby power and handshake, 3.6 Tables 12 to 14; connector is SFF-TA-1002 Type 1 4C+, 168 pins | WebFetch text extraction; the shell cannot reach opencompute.org (proxy 403) |
| OCP DC-SCI pin spreadsheets, 2.0 and 2.1 (`DCSCI20_SHEET`, `DCSCI21_SHEET`) | The intro tab and the change log only. The pin tab never rendered through `/edit`, `/htmlview`, `/export?format=csv` or `gviz` | Dead end, recorded in `docs/interfaces/sources.csv` |
| Project Argus DC-SCM 2.0 module spec, section 9.4 Tables 2 and 3 (`ARGUS`) | Pin numbers, functions, voltages and directions. Argus states its pinout "fully complies with the OCP DC-SCI Rev2.0 Ver1.0 Pin Definition" | WebFetch text extraction |
| OCP LTPI for DC-SCM 2.2 (`LTPI12`) | GPIO frame (2.2.1.1), link loss (2.5.2), latency (Table 15, Table 16) | WebFetch text extraction |

So the pin numbers in the mapping are a public secondary transcription of the OCP spreadsheet, made by a vendor that built to it. Row `REQUIREMENT-PINS-CONFIRMED-AGAINST-SPREADSHEET` of the compliance matrix stays **open** until someone reads the spreadsheet itself. DC-SCM 2.2 changed some names and added alternates relative to 2.0; where the 2.1 change log says a pin gained an alternate (the LTPI2 and SGMII alternates on the OCP bay pins), the mapping says so in its notes.

## 2. The mapping, in one table

Full detail, one row per physical pin, is in `hw/pinout/dcscm_mapping.csv`. The summary:

| Governor group | Lands on | Public source | Status |
|---|---|---|---|
| PCIe x1 mailbox | DC-SCI lane 5 (A65/A66 out, B65/B66 in), refclk CLK_100M_1 (A68/A69) | DCSCM22 3.5.1.1, 3.5.1.2; ARGUS | designed, refclk pairing to confirm |
| SMBus mailbox | I2C_3V3_1 (A17/A18) | DCSCM22 3.5.7 | designed |
| GPU post-box SMBus, slots 0 to 7 | I2C_3V3_2 to I2C_3V3_9, one bus per slot | DCSCM22 3.5.7; ARGUS | designed; HPM routing to the GPU is OEM, the HGX side is NDA |
| NVSwitch management bus | I2C_I3C_1V8_12 (A58/A59) through a 3.3 to 1.8 V translator | DCSCM22 3.5.7 | designed; HGX side NDA |
| PCIe switch management bus | I2C_I3C_1V8_13 (A61/A62) through a translator | DCSCM22 3.5.7 | designed |
| PWRBRK#, slots 0 to 7 | LTPI2 low-latency GPIO, SCM to HPM, bits 0 to 7 | LTPI12 2.2.1.1, Table 15 | designed, needs REQUIREMENT-LINK-LOSS-ASSERTS-LEVERS |
| PERST#, slots 0 to 7 | LTPI2 low-latency GPIO, bits 8 to 15 | LTPI12 2.2.1.1; DCSCM22 3.5.1.3 | designed, needs REQUIREMENT-LINK-LOSS-ASSERTS-LEVERS |
| PWR_EN, slots 0 to 7 | LTPI2 normal-latency GPIO, bits 0 to 7 | LTPI12 2.2.1.1, Table 16 | designed, needs REQUIREMENT-LINK-LOSS-ASSERTS-LEVERS |
| NVSwitch reset, PCIe switch reset | LTPI2 normal-latency GPIO, bits 8 and 9 | LTPI12 2.2.1.1 | designed |
| TAMPER_IN | HPM_SCM_INTRUSION_N (B27), wired-AND with the module's own switch | DCSCM22 3.5.13 | designed |
| Halt loop, message fabric | Their own connector next to the management connector | `hw/pcb/rack-integration.md` 4 | intentional |
| Power | Module regulators from P12V_AUX (A1 to A4); GND on long pins | DCSCM22 3.6 Table 14 | designed |
| Clock, reset, provisioning SPI, JTAG, mesh, LEDs | On the module only, never on the connector | DCSCM22 3.5.3, 3.5.14 | intentional |

**No public home (flagged, not hidden):** `PEX_MDIO` and `PEX_MDC` (DC-SCI has no MDIO; tunnelling it on the LTPI OEM channel is out of scope of LTPI 1.2 section 2.2.1.5, so the plan is the switch's I2C port), and `DPU_OOB_TX/RX` (1000BASE-T has no DC-SCI home; the SGMII alternates are dual-node only; the plan is the DPU's own governor over the fabric).

**Pins the governor does not have but this mapping needs (proposed, marked `+` in the CSV):**

1. `+PCIE_EP_PERST_N` on A28. The host resets the governor's PCIe endpoint with it. It must reset the endpoint only, never the core or its state, or the host gets a reset button on the governor.
2. `+SLOT_PWRGD` per slot, on LTPI2 low-latency GPIO HPM to SCM. Without it the governor cannot hold PERST# for T_PVPERL after power is valid (`02-pcie-cem-sideband.md`).
3. Eight LTPI2 LVDS pins on the OCP bay (OA5/OA6/OA11/OA12 out, OB5/OB6/OB11/OB12 in). The governor die has no LVDS. The LTPI2 endpoint is an FPGA on the module, inside the governor's trust boundary.

`hw/pinout/governor_module.csv` is not changed by this work. These are proposals for the next pinout revision.

## 3. Why LTPI2 and not LTPI

The DC-SCI already has one LTPI link (A20 to A24, B20 to B24). It belongs to the BMC module's CPLD. If my levers rode that link, the BMC's logic would sit between the governor and the GPU, and the BMC is untrusted in this design (`docs/03-interfaces.md` section 4). The 2.x connector also offers a second link, LTPI2, as an alternate on the OCP bay pins that otherwise carry PCIe lanes 1 and 3. I take LTPI2 for the governor and leave the BMC alone. Cost: those two PCIe lanes. Status open until the 2.2 spreadsheet confirms the alternate.

## 4. The finding: LTPI keeps a dead governor's levers released

LTPI 1.2 section 2.5.2: "For GPIO Channel LTPI shall maintain the state of the GPIOs exposed to the system." Frame loss (Table 14): "The state of GPIOs is maintained from the previous Frame." Nothing in the excerpt I could read defines a safe value before the link first trains.

For a BMC that is a sensible rule: a glitch should not flap the board's signals. For the governor it is the wrong rule. If the governor dies, or its link does, while its GPU is running, the HPM side keeps PWRBRK# released, PERST# released and PWR_EN high. The halt loop still opens (a dead governor's switch is open), so the rest of the domain stops, but this governor's own levers stay where they were. On top of that, PWRBRK# has a pull-up on the card (OAM 1.5 Table 4), so a net nobody drives reads as released.

`tests/test_if_dcscm.py::test_finding_ltpi_as_written_holds_released_levers_on_link_loss` shows it on the model of the spec text, and `test_failsafe_endpoint_asserts_levers_on_link_loss_and_before_training` shows the fix.

**REQUIREMENT-LINK-LOSS-ASSERTS-LEVERS.** The HPM-side LTPI2 endpoint drives every governor lever to its asserted value (PWRBRK# low, PERST# low, PWR_EN low, switch resets asserted) while the link has not reached Operational since power-on, and from the moment Link Lost is declared until the link is Operational again and a fresh frame has arrived. The HPM default for those outputs is the asserted value; they must not depend on pull resistors on the card side.

No public document requires this. It is stricter than LTPI. It needs OEM logic in the HPM CPLD, which is why the matrix row `REQUIREMENT-LINK-LOSS-ASSERTS-LEVERS` is **open**, not designed.

**REQUIREMENT-LOCAL-POWER-FAIL-DRIVES-PERST** comes out of the same hop and is explained in `02-pcie-cem-sideband.md`: the HPM endpoint also ORs the slot's own power-fail into PERST#, because a power-good that crosses LTPI arrives up to 19.2 us late and the CEM wants PERST# within 500 ns.

## 5. Latency

The brake rides a low-latency GPIO. LTPI Table 15 gives 6.40 us constant and 19.20 us random latency at 25 MHz SDR, the slowest rate listed. The loop simulation's worst case (`hw/loop/results.md`) is 317.15 us to the halt output. Add the LTPI hop and it is 336.35 us at the HPM pin, inside the 1 ms bound. The checker recomputes this (`HALT_BOUND`) every run. Normal-latency GPIO is N times the constant latency; PWR_EN and the switch resets are not on the 1 ms path (the SAFE rung is 300 s after HALT by default), so they go there.

## 6. What the checker enforces

`python -m govsim.hardware_ref.dcscm` fails on any of these, each with its own code so a test can plant one fault and see exactly that rule fire (`tests/test_if_dcscm.py::test_planted_fault_is_caught`, 18 planted faults):

- every governor pin in `governor_module.csv` has exactly one row (`UNMAPPED`, `DUP_SIGNAL`, `UNKNOWN_SIGNAL`);
- every DC-SCI pin exists in the public pin file, carries the named function, and is used once (`PIN_NOT_PUBLIC`, `FUNC_NOT_ON_PIN`, `PIN_REUSED`, `MULTI_PIN`);
- voltage matches or a translator is named; direction matches from the SCM's side (`VOLTAGE`, `DIRECTION`);
- LTPI channels are well formed, unique, fit the Default I/O Frame, point the right way, and the brake is on a low-latency bit (`LTPI_CHANNEL`, `LTPI_REUSED`, `LTPI_FRAME`, `LTPI_LATENCY`);
- every lever is present the right number of times, and every lever over LTPI names a fail-safe requirement that this document defines (`LEVER_MISSING`, `LEVER_NO_FAILSAFE`);
- every row cites a source from `docs/interfaces/sources.csv`, a repo file, or says "no public source"; a signal with no public home says so and says why (`NO_SOURCE`, `NO_HOME_UNEXPLAINED`, `NO_HOME_UNFLAGGED`);
- the 1 ms halt bound holds with the LTPI hop (`HALT_BOUND`).

## 7. What is not done

- No card exists. Nothing here has been on a bench.
- The DC-SCM 2.2 power-state sequence (section 3.6) is listed, not modelled.
- Pin numbers are from the Argus transcription, not the OCP spreadsheet.
- The HPM-side CPLD logic for per-slot levers is OEM work with no public reference design. On HGX the deciding document is NVIDIA's HGX Platform Design Guide (NDA, not read).
