# 02 · PCIe CEM sideband: PERST#, PWRBRK#, WAKE#, SMBus, 3.3Vaux

> **Plain words first.** A PCIe card has a few extra wires next to its data lanes. Two of them are my levers: PERST# holds the card in reset, PWRBRK# (the power brake) tells it to slow down hard. The rulebook for those wires, the PCI Express Card Electromechanical specification (CEM), is members-only, so I have not read it. The key timing numbers are quoted in public places, the Linux kernel and the Linux kernel mailing list among them, and I checked the governor's real reset logic against them in simulation. It failed three of them. I wrote a small block that fixes all three and proved the fix catches its own planted bugs. One number nobody publishes: how fast a GPU actually slows down after the brake. So my 1 ms promise is a promise about the wire, not about the GPU.
>
> **Backed by:** `govsim/hardware_ref/cem.py` (the rules, the simulation harness), `rtl/governor_rtl/cem_sideband.py` (the fix), `tests/test_if_cem.py`. One command: `python -m govsim.hardware_ref.cem`.

## 1. The numbers and where each one comes from

| Symbol | Value | Meaning | Public source | Members-only original |
|---|---|---|---|---|
| T_PVPERL | 100 ms | power stable to PERST# released | `LINUXPCI`: Linux `drivers/pci/pci.h` at commit 3ac032ef, "PCI Express Card Electromechanical Specification, Revision 5.1, Section 2.9.2, Symbol T_PVPERL"; `LKMLCEM` quoting CEM 2.0 | CEM |
| T_PERST-CLK | 100 us | REFCLK stable before PERST# released | `LINUXPCI`, `LKMLCEM` | CEM |
| T_PERST | 100 us | PERST# active time | `LKMLCEM` (CEM 2.0 table quoted on LKML) | CEM |
| T_FAIL | 500 ns | power level invalid to PERST# active | `LKMLCEM` (CEM 2.0) | CEM |
| PWRBRK# pin | B30, open drain from host, pull-up on the card | where the brake is | `CTYUN` (pin B30), `QUARCH` (open drain from host, among the switched sidebands incl. B30), `OAM15` Table 4 (3.3 V input, 47K pull-up on module, "CEM Compliant Power Break") | CEM 4.0/5.0 and the PWRBRK ECN |
| PWRBRK# response | **no public number** | how fast the card sheds power | `INSPUR` (a patent, not NVIDIA): GPU frequency reduction "may be completed within 5 ms". `CTYUN` shows a response-time table as an image I cannot read. `DELLPAT` has none | CEM ECN; NVIDIA board docs (NDA) |

T_PERST and T_FAIL are quoted from CEM 2.0. I have no public source saying they are unchanged in 4.0 or 5.x. The Linux kernel cites 5.1 for the two it uses, with the same values. If a member reads 5.x and finds a different T_PERST or T_FAIL, the constants at the top of `cem.py` change and the tests say whether the shaper still meets them.

Dead ends: the OCP NIC 3.0 spec has a power-sequencing table (Table 43), but the text extractor stopped at section 2.2 and never reached it (`OCPNIC30`). A vendor blog post (`PRODIGY`) lists T_FAIL as a minimum of 500 ns; that contradicts LKML's quote of the CEM table, which reads it as the bound on the delay, and I went with the CEM quote.

## 2. How the check works

The halt sequencer (`rtl/governor_rtl/halt.py`, `HaltSeq`) is simulated in Amaranth with one clock per microsecond. A slot model in the same netlist turns PWR_EN into a power-good that rises 5 ms later and falls at once, and can brown out on its own. Every change of the pad signals is recorded with its time; `check_trace` applies the rules to the recording. The scenario: boot, run past T_PVPERL; a loss of loop current (HALT) followed at once by an authorized CLEAR with the loop still live, so the sequencer goes straight back toward RUN; run; a 2 ms brown-out nobody commanded; run; a tamper (SAFE, power cut). A second harness drives the shaper alone and asks for a 3 us reset with power held valid.

## 3. Findings on the existing RTL

`HaltSeq` alone, pads driven straight from the sequencer:

| Rule | Measured | Required | Why |
|---|---|---|---|
| T_PVPERL | PERST# released with power not valid | 100 ms after power valid | HALTED_INITIAL to RUN raises PWR_EN and releases PERST# on the same clock edge (`halt.py` lever equations). `docs/03` and `hw/pcb/rack-integration.md` section 5 say "PERST# released after the slot's power-good": the RTL disagrees with the spec. |
| T_PERST | 3 us | 100 us | HALT, then an authorized CLEAR, then RUN: PERST# is asserted for three cycles. In practice firmware takes much longer to authorize a CLEAR, but nothing in the hardware enforces it. |
| T_FAIL | never asserted during the brown-out | 500 ns | The governor has no slot power-good input at all (`hw/pinout/governor_module.csv`), so it cannot see a rail fail it did not command. |

Each is pinned as a test that expects the violation (`test_finding_*` in `tests/test_if_cem.py`), so whoever fixes the RTL flips them on purpose.

## 4. The fix: `CemSideband`

A per-slot block between the sequencer's levers and the pads (`rtl/governor_rtl/cem_sideband.py`):

- PERST# is asserted, combinationally, whenever the sequencer asks, PWR_EN is low, or the slot's power-good is low. No added delay on the way down.
- PERST# is released only after power-good has been high without a break for T_PVPERL.
- Once asserted, PERST# stays asserted for at least T_PERST.
- PWRBRK# and PWR_EN pass straight through. The block can never slow the brake (`test_shaper_never_delays_the_brake` compares the brake edges with and without it).

With the shaper every rule passes: T_PVPERL measured 100.000 ms, T_PERST 101 us on the short request, T_FAIL 0 us. Five mutants of the shaper (T_PVPERL halved, no power-good timer, the power-fail path registered one cycle late, T_PERST cut to 10 us, no hold) are each caught by the rule they break (`test_mutant_caught`), and an unmodified copy of the mutant harness passes (`test_mutant_unmodified_copy_passes`), so the harness itself is not what fails.

**Not done:** the shaper is not wired into `GovernorCore` and has no formal proof yet. I left `top.py` alone on purpose: the WAVE-FORMAL-PROOFS-ON-VERILOG work on other branches is proving `halt_seq` properties on the generated Verilog, and changing the top-level pad path under it would invalidate that work mid-flight. Next step: wire it in, regenerate, and add its three invariants to `rtl/formal`. It also needs the per-slot power-good pin, which `governor_module.csv` does not have (proposed as `+SLOT_PWRGD` in `01-dcscm-dcsci-ltpi.md`).

## 5. T_FAIL across LTPI

When the power-good reaches the governor through LTPI it is up to 19.2 us late (LTPI Table 15). The same scenario with a 20 us hop on power-good fails T_FAIL at 20 us (`test_finding_t_fail_cannot_be_met_through_an_ltpi_hop`). A commanded power cut still passes, because PERST# drops with PWR_EN on the governor side. An uncommanded brown-out does not. So:

**REQ-CEM-FAIL-1.** The HPM-side endpoint ORs the slot's local power-fail into PERST#. The governor's own T_FAIL guarantee holds only where the power-good reaches it directly (the soldered-on-baseboard option, or the prototype board).

## 6. The 1 ms halt bound

The sequencer asserts the brake one clock after `loop_lost` (20 ns at 50 MHz, `brake_latency_cycles`). The loop timing work assumes 10 us for "lever assertion" and gets a 317.15 us worst case; 20 ns fits inside the assumption. Over LTPI the pin sees it at 336.35 us. Both are well under 1 ms.

What the 1 ms does **not** cover: the GPU's own reaction to PWRBRK#. NVML says the brake cuts core clocks "by a factor of 2 or more" (`NVML`). How fast, NVIDIA does not publish. The only public figure I found is a patent from a server maker saying 5 ms. Until NVIDIA's number is public, `docs/02-safety-fabric.md`'s line "the GPU's power brake asserts within 1 ms of the governor's halt output" should be read as the pin, not the clocks. Matrix row `REQUIREMENT-GPU-SLOWDOWN-AFTER-BRAKE` is **members-only**.

## 7. The other sideband pins

| Pin | Governor's use | Requirement | Status |
|---|---|---|---|
| WAKE# | none | A card's WAKE# (open drain, active low per `CTYUN`) must never re-power a slot the governor cut: the platform does not let WAKE# override PWR_EN | open, a platform requirement |
| SMBus (SMCLK/SMDAT) | the GPU's SMBus post-box, 8-bit address 0x9E write / 0x9F read (`PB11133`); the governor is the only master | the SMBPBI command set is NDA (`SMBPBIDG`); the persistent power cap is public (`PB10577`) | designed |
| 3.3Vaux | none | the governor runs from DC-SCM standby P12V_AUX, not the slot's 3.3Vaux; the slot's aux budget is in the members-only CEM | designed |
| REFCLK | none | T_PERST-CLK is the board's job: the governor does not own the slot clock | open, a board requirement |
