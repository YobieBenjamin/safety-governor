# FPGA build report: governor core + SMBus target on the ULX3S (ECP5 LFE5U-85F-6BG381C)

Written by `hw/fpga/build.sh` on 2026-10-24 01:07 UTC, nextpnr seed 1, router2. Do not edit by hand: rerun the build.

## Verdict

- 30 MHz: met, Fmax 36.07 MHz.
- Bench bitstream: `build/30mhz/governor_ulx3s_85f_30mhz.bit` at 30 MHz. The governor's timers run on a 1 us tick divided from whatever the clock is, so the heartbeat, throttle, halt and loop-sense timings are the same at any of these clocks.
- Build manifest (`30mhz/manifest.json`): fail-closed, source_rev `5d2dc0094a29bb08`, stages top,pll,synth,pnr,pack,report, bitstream sha256 `477de080ac9bd84a`. The verdict is read from this manifest, not from the bitstream's presence.

## Utilisation

After synthesis (yosys `synth_ecp5`) and after place and route (nextpnr), 30 MHz build:

| Cell | Synthesis |
|---|---|
| CCU2C | 399 |
| EHXPLLL | 1 |
| L6MUX21 | 3209 |
| LUT4 | 17957 |
| PFUMX | 5513 |
| TRELLIS_FF | 12857 |
| TRELLIS_IO | 2 |

| Resource | Used | Available | Percent |
|---|---|---|---|
| DCCA | 1 | 56 | 1.8 |
| EHXPLLL | 1 | 4 | 25.0 |
| TRELLIS_COMB | 18869 | 83640 | 22.6 |
| TRELLIS_FF | 12857 | 83640 | 15.4 |
| TRELLIS_IO | 26 | 365 | 7.1 |

## Timing, 30 MHz build

| Clock | Achieved (MHz) | Constraint (MHz) | Met |
|---|---|---|---|
| `$glbnet$clk` | 36.07 | 30.00 | yes |

Critical path:

From `posedge $glbnet$clk` to `posedge $glbnet$clk`:

| Step | Delay (ns) | Net or cell |
|---|---|---|
| clk-to-q | 0.52 | `core.gov.core.cap_storage.cap_storage_lk_peer_TRELLIS_FF_Q_2 -> core.gov.core.cap_storage.` |
| routing | 3.27 | `core.gov.core.cap_storage.cap_storage_lk_peer[2]` |
| logic | 0.24 | `core.gov.core.cap_storage.point0_LUT4_D_1_Z_LUT4_D_Z_LUT4_Z_D_PFUMX_Z_C0_LUT4_Z -> core.go` |
| routing | 0.42 | `core.gov.core.cap_storage.point0_LUT4_D_1_Z_LUT4_D_Z_LUT4_Z_D_PFUMX_Z_C0[4]` |
| logic | 0.26 | `core.gov.core.cap_storage.point0_LUT4_D_1_Z_LUT4_D_Z_LUT4_Z_D_PFUMX_Z_BLUT_LUT4_Z -> core.` |
| routing | 0.78 | `core.gov.core.cap_storage.point0_LUT4_D_1_Z_LUT4_D_Z_LUT4_Z_D[2]` |
| logic | 0.24 | `core.gov.core.cap_storage.point0_LUT4_D_1_Z_LUT4_D_Z_LUT4_Z -> core.gov.core.cap_storage.p` |
| ... | | 43 more steps |
| logic | 0.24 | `core.rb_TRELLIS_FF_Q_20_DI_L6MUX21_Z_D1_PFUMX_Z_C0_LUT4_Z_D_CCU2C_COUT_CIN_CCU2C_COUT_CIN_` |
| routing | 5.38 | `core.rb_TRELLIS_FF_Q_20_DI_L6MUX21_Z_D1_PFUMX_Z_C0_LUT4_Z_D_CCU2C_COUT_CIN_CCU2C_COUT_CIN_` |
| logic | 0.26 | `core.gov.core.cap_storage.budget2_TRELLIS_FF_Q_14_DI_L6MUX21_Z_D1_L6MUX21_Z_D1_PFUMX_Z_ALU` |
| routing | 0.00 | `core.gov.core.cap_storage.budget2_TRELLIS_FF_Q_14_DI_L6MUX21_Z_D1` |
| logic | 0.24 | `core.gov.core.cap_storage.budget2_TRELLIS_FF_Q_14_DI_L6MUX21_Z_D1_L6MUX21_Z_D0_PFUMX_Z_ALU` |
| routing | 0.61 | `core.gov.core.cap_storage.budget2_TRELLIS_FF_Q_14_DI` |
| setup | 0.00 | `core.gov.core.cap_storage.budget2_TRELLIS_FF_Q_14 -> core.gov.core.cap_storage.budget2_TRE` |

57 steps, 27.72 ns in total.

Bitstream `governor_ulx3s_85f_30mhz.bit`: 577314 bytes, sha256 `477de080ac9bd84a1f79e2440f19d9268f94b5e730181378cb2ac48b90b6aa60`.

## What is in the bitstream

- `governor_core`, all of it (default sizes: 8-entry capability tables on four points, 8-entry ticket store, 4 meter slots), with a 1 us tick.
- The SMBus target (`rtl/governor_rtl/smbus.py`), address 0x58.
- The bench firmware stand-in (`hw/fpga/top.py`): four halt-path pins and a shift chain over SPI that drives every other firmware-side port of the core and reads its outputs back (`fw_chain.json`). It is how a host plays the firmware, and it keeps synthesis from pruning the parts of the core whose inputs would otherwise be tied off.
- Not in it: Ibex, the crypto engines, SRAM macros, NVM, PCIe and SGMII PHYs (they come with the OpenTitan integration, docs/08).

Bitstreams are build products and are not committed. Flash: `openFPGALoader -b ulx3s <file>.bit` (add `-f` to write the SPI flash).

## Findings from this build

**RTL-CORE-HALTS-AFTER-REACHING-RUN. The core halts itself one cycle after it first reaches RUN when the loop sense strobe runs from power-on.**
`LoopIO` counts sense samples with no current. Before the governor arms, its own loop switch is open, so on a
one-governor loop (and on any loop where this governor's switch is the open one) there is no current and the
debounce counter saturates: `loop_lost` is high while the core sits in HALTED_INITIAL. The heartbeat arms the core,
the switch closes, current flows, and `HaltSeq` goes to RUN without looking at `loop_lost`. The next cycle
`loop_lost & in_run` wins the priority chain and the core halts with cause LOOP. The counter clears only on the next
sample with current, up to 100 us later, and by then the switch is open again, so it never clears. The same happens
after every clear that follows a loop halt.
Reproducer: `rtl/tests/test_smbus.py::test_core_reaches_run_and_stays_there_with_the_sense_strobe_running_from_power_on`
(strict xfail: it fails by assertion today and turns red as XPASS the day the RTL is fixed).
`rtl/tests/test_blocks.py` does not see it because it raises `sample` only after the core is in RUN.
Proposed fix, not applied (halt.py is not this branch's): in `HaltSeq`, enter RUN only on `loop_sense & ~loop_lost`,
so an armed core waits for one clean sense sample (at most 100 us). Until then the bench (`host_test.py levers` and
`soak`) cannot hold RUN and will say so.

**RTL-FPGA-MISSES-50-MHZ. 50 MHz is not met on the ECP5: the design reaches about 38 MHz, limited by the capability table's one-cycle
lookup.** The critical path (below) runs from a lookup input of `cap_dpu` through the eight-entry CAM compare, the
priority select and the 24-bit budget compare and decrement, into the budget register, in one cycle (docs/04
section 9: "1 cycle at the checker clock"). In the router2 run at seed 1: 26.4 ns, 4.7 ns logic and 21.7 ns routing.
Nothing in the SMBus target or the bench harness is on it. Options, none applied: register the match and decrement a
cycle later (a two-cycle lookup the spec would have to say), or run the bench slower. The build does the second on
its own: the timers run on a 1 us tick divided from the clock, so the slower bench bitstream behaves the same at the
heartbeat, throttle, halt and loop-sense scale. This says nothing about sky130 at 50 MHz; that is LibreLane's STA.

**Spec and RTL disagreements noticed (recorded, not changed).** docs/04 section 2 lists MBOX_STATUS codes 0 to 6;
`mailbox.py` also returns 7 (wrong command, added 22 October), and the register is 3 bits where the table says 8.
docs/04 says 16 meter slots; the RTL meter has 4, so CSR reads of METER_SLOT[4..15] return 0.

## What did not work on the way here

| Attempt | What happened | Numbers | What I did |
|---|---|---|---|
| First CRC-8 in Amaranth, written as a loop of `Mux` | every level referenced the previous one twice, so the expression tree doubled eight times | `rtl/gen/smbus.v` came out at 109,431 lines | rewrote it as the XOR matrix CRC-8 really is: 1,451 lines |
| Formal proof, first three runs | k-induction failed on states no real bus reaches (receive shift register out of step with the monitor; a bit counter of 15; a write step after a repeated start) | each failure found in 6 to 9 s | added the invariants that tie the target to the monitor; then bounded (25 cycles) in 29 s and induction in about 1 s |
| Catching the 11 mutants in the bounded check | impossible at depth 25: one doorbell write is 8 bytes of 9 clocks through a 2-flop synchronizer and a 3-cycle filter, hundreds of cycles | 11 of 11 caught, all by the induction step | replayed every mutant as concrete bus traffic in `rtl/tests/test_smbus.py`; each fails a named rule there by assertion |
| `assign pad = oe ? 0 : 1'bz` for SDA/SCL | yosys left two `$_TBUF_` cells ("limited support for tri-state logic") | 2 cells | instantiated the ECP5 `BB` pad primitive directly |
| `ecppll -f /some/path/pll.v` | the WebAssembly build of ecppll can only write inside its working directory | no file written | run it inside the build directory |
| First structural check that `csr_addr` reaches no flip-flop | passed on the planted bug too: `yosys -q` swallows `select -list` output, so the list was always empty | 0 hits on a planted register | write the selection to a file; now 0 hits on the real core, more than 0 on the planted one |
| nextpnr with its default router (router1) at 50 MHz | did not converge: after about 20 minutes of routing 38,495 of 88,079 arcs were still overused and the count had stopped falling | stopped by hand at iteration 119,000 | switched to router2: routed in 193 s |
| `yosys ltp` to find the long path before routing | the WebAssembly yosys ran out of call stack on this netlist | trap: call stack exhausted | read the critical path from nextpnr after routing instead |
| A smaller part: ECP5 12F (ULX3S 12F, the cheaper board) | Lattice rates the part at 12k LUTs and the design needs 17,306 LUT4, so by the datasheet it does not fit. But nextpnr models the 12F as the 25F die it is built on and places the design anyway | `nextpnr-ecp5 --12k`: 17,284 of 24,288 LUT cells (71 percent), 12,828 flip-flops (52 percent), placement finished | stayed on the 85F. Whether a 12F board runs a design over its rated size is untested here and outside Lattice's ratings; worth one try on real hardware because the 12F board is cheaper |
| iCE40 (the yowasp-nextpnr-ice40 path in the brief) | does not fit | the core alone maps to 14,531 LUT4 on ECP5 out of context; the largest iCE40 HX8K has 7,680 logic cells | not attempted further |
| Raspberry Pi price lookup | the fetch was not approved in time | none | BENCH.md lists a price only where I read one (the ULX3S) |

## Toolchain

| Package | Version |
|---|---|
| amaranth | 0.5.10 |
| amaranth-yosys | 0.50.0.0.post129 |
| yowasp-yosys | not installed |
| yowasp-nextpnr-ecp5 | not installed |
