# WAVE-FORMAL-PROOFS-ON-VERILOG findings, work stream b (heartbeat, meter, alarms, measure_reg, loop_io, governor_core)

Everything here is backed by something that runs. The one command is `python -m rtl.formal`; the lines it prints
are quoted where they matter. Date: 23 October 2026. The plain-English version, and every dead end, is in
`PLAIN-ENGLISH-b.md` next to this file.

## RTL-METER-COULD-GO-DOWN. The meter could be made to go down (fixed)

**What.** `meter.py` added with a plain `+`. A 48-bit counter plus a 48-bit `add_*` wraps, so one strobe with a
large enough add moved the counter below where it was. The meter is the evidence the firmware compares against the
compute budget (`govsim/governor.py`, the per-tick cycle check), so a counter that can go down lets a job spend past
its budget and then read as under it.

**Evidence.** Rule RTL-METER-NEVER-DECREASES of `rtl/formal/meter.sv` ("never decreases") failed the bounded check on the old Verilog in a
few cycles: `bounded check failed: meter_props: props.sv:31 ... props.sv:41` (every counter, every slot).

**Fix.** The adds saturate (`_sat_add` in `meter.py`): a counter that would pass all ones stays at all ones, which
reads as over every budget, the safe side. The old adder is kept as a mutant ("the old wrapping add") and is caught
by assertion. Regression: `rtl/tests/test_formal_proof_regressions.py::test_meter_counter_cannot_be_moved_down_by_a_large_add`
fails on the old code by assertion (the counter reads 4 after 5 + 0xFFFF on a 16-bit build).

## RTL-HEARTBEAT-KEPT-ALIVE-WITHOUT-HEARTBEAT. The heartbeat could be kept alive without a heartbeat (fixed)

**What.** `top.py` made the millisecond strobe from the low ten bits of the monotonic counter:
`tick_ms = tick & (mono.value[:10] == 1023)`. The monotonic counter's `load_hwm` has priority over its increment and
may move the value anywhere upward. Driving `load_hwm` every cycle with `hwm = value + 1024` keeps the low bits fixed
(the counter still only goes up, so the monotonic block's own rule is not broken), and then no millisecond strobe
ever comes. The heartbeat never expires and the THROTTLE and HALT timers never climb, with no valid heartbeat.
`load_hwm` is documented as "a one-cycle strobe at boot", but nothing in the RTL makes it one: it is a port, and
whoever drives the counter's fuse interface can hold it high.

**Evidence.** Rule RTL-EXPIRY-NOT-POSTPONED of `rtl/formal/governor_core.sv` (the strobe comes on every 2^ms_shift-th tick, whatever any
other input does, `load_hwm` included). The old tap is a mutant ("the old millisecond tap on the monotonic counter")
and is caught by assertion. Regression: `test_heartbeat_expires_even_while_load_hwm_is_hammered` runs the full-size
core for three milliseconds of ticks with `load_hwm` hammered; on the old code the heartbeat is still alive and the
test fails by assertion.

**Fix.** A dedicated prescaler `ms_div` counts `tick`; `tick_ms` fires when it is all ones. It starts at zero with
the counter, so the timing is unchanged when nobody touches `load_hwm` (the existing core timer test still passes and
MONO_LO still counts every microsecond). `ms_shift` became a constructor parameter (default 10) so the proof can use
a short millisecond. docs/04 ("derived from the microsecond counter") still reads true in spirit: the strobe is
derived from the microsecond tick, no longer from the counter's value.

## RTL-LOST-HEARTBEAT-LOOP-STAYS-CLOSED. The open question: a lost heartbeat climbs to SAFE on one chip and the loop stays closed (decided 23 October 2026)

The question recorded with the halt_seq proof: a lost heartbeat climbs THROTTLE, HALT, SAFE (power off) on this chip
alone and never opens the loop to its neighbours. What the integrated RTL does, seen from loop_io and governor_core:

1. **Confirmed end to end, at the pins.** `python -m rtl.formal` prints
   `FACT governor_core: lost heartbeat climbs to SAFE with the loop closed: ... (trace of 28 cycles found)`. From
   power-on, with loop current present and one heartbeat that is never renewed, the solver finds a run of the core
   that reaches SAFE with PWR_EN low and `loop_out_open` low (`rtl/formal/governor_core_cover.sv`, small build).
2. **It is an invariant, not one trace.** `rtl/formal/governor_core_facts.sv` proves by k-induction that whenever
   the sequencer's cause is LOCAL (2), the loop switch and the pad are closed, on every rung. Heartbeat loss, a local
   trip and a throttle command all write LOCAL. This matches docs/01 and docs/02 ("local causes throttle and halt that
   governor's own slot without opening the loop"). The neighbours keep loop current and keep running; they learn of
   it only through the fabric and the log, never through the loop.
3. **HALT to a chip already in SAFE does not open the loop (closed).** The text below is the record of what was
   wrong. **Closed** on branch feat/yobie-calls (23 October 2026) by Yobie's decision, written into docs/04 section
   3: "A HALT opens the loop switch on every rung, SAFE included". In SAFE, `cmd_halt` now sets `switch_open` and
   makes the command the cause (tamper keeps its cause); the state stays SAFE. The design fact RTL-OLD-SAFE-HALT-LOOP-FACT that recorded the
   old behaviour is removed from `governor_core_facts.sv`. In its place, proven by k-induction: halt_seq.sv, H rules
   ("a halt command opens the loop in every state, SAFE included, unless an authorized CLEAR took that cycle", and
   in SAFE "it stays SAFE, power off, cause command unless tamper"); governor_core.sv, RTL-HALT-REACHES-PINS, the same at the pins. The
   old behaviour is a planted mutant ("a HALT to a chip in SAFE leaves the loop closed") and is caught; the
   reproducer `test_finding_cmd_halt_in_safe_opens_the_loop` (conformance CONFORMANCE-HALT-TO-SAFE-CHIP, also closed) and
   `rtl/tests/test_yobie_calls.py::test_halt_to_a_chip_in_safe_opens_its_loop_and_stays_safe` are guards, and both
   fail by assertion on the old sequencer. Was: a signed HALT to a chip that is already in SAFE does not open the
   loop either. The sequencer obeys
   `cmd_halt` only when `state != SAFE`. Send HALT to a chip that lost its heartbeat and has climbed to SAFE and the
   cause stays LOCAL and the switch stays closed. The same facts file proves it (rule RTL-OLD-SAFE-HALT-LOOP-FACT). docs/02 says "Any
   governor opens its switch on a loop-opening cause: a signed HALT"; for a chip in SAFE the RTL disagrees. HALT
   carries "this chip's id" (docs/04 section 3), so a HALT aimed at that chip to stop the domain stops nothing. A chip
   in THROTTLE or HALT from a local cause does open on HALT (RTL-HALT-REACHES-PINS is proven from every rung but SAFE). Not changed: it
   is a design decision. The one-line change would be to let `cmd_halt` set `switch_open` in SAFE as well.
4. **The asymmetry at boot.** The switch starts open and closes only when armed (HALTED_INITIAL, no cause, a live
   heartbeat). A governor that never receives its first heartbeat holds the whole loop open, and nobody in the domain
   reaches RUN (they need loop current). A governor that loses its heartbeat after arming stops only itself. Proven
   pieces: RTL-BOOTS-SAFE (boots open), RTL-LOOP-STAYS-OPEN (the switch closes only through arming), RTL-LOCAL-CAUSE-KEEPS-LOOP-CLOSED. So before the first heartbeat a missing
   heartbeat is a domain stop; after it, a local one. **Decided** (23 October 2026, Yobie): it stays a domain stop (fail
   closed), but loud, named and with a deliberate way out. The sequencer counts the milliseconds it waits for its
   first heartbeat (`boot_timer`, `BOOT_WAIT` at 0x088); past `t_boot_ms` (5000 on the chip, 3 in the small build)
   it raises `no_first_hb`, which the core makes the hardware-owned sticky ALARMS bit 31 NO_FIRST_HEARTBEAT and the
   live CAUSE bit 3. An authorized EXCLUDE (`cmd_exclude`) closes that chip's switch while it stays in HALTED_INITIAL
   with every lever asserted; ALARMS bit 30 and CAUSE bit 4 say so. Proven: halt_seq.sv, the X and N rules, plus a
   two-copy miter showing EXCLUDE changes no register outside HALTED_INITIAL with no cause; governor_core.sv, RTL-LOOP-STAYS-OPEN
   (now "closes by a heartbeat or an EXCLUDE, and never for a chip halted by loop loss, command or tamper"), RTL-EXCLUDED-LEVERS-SAFE, RTL-ALARMS-HARDWARE-OWNED.
   Nine planted bugs in halt.py and four in top.py for these rules, all caught by assertion.
5. **loop_io is not where the stickiness lives.** `loop_lost` falls on the first sample that sees current again (RTL-LOOP-LOSS-STICKY-UNTIL-CURRENT
   proves it falls only then). What is sticky is the sequencer's switch (RTL-LOOP-STAYS-OPEN: once opened by a cause, it closes only
   through clear and re-arming). A current loss shorter than two samples never reaches the sequencer; a longer one is
   acted on only while the chip is RUN or THROTTLE. In HALT or SAFE the loss is not written to CAUSE (the levers are
   already down, so this is a logging gap, not a safety one).

## RTL-OTHER-PROOF-OBSERVATIONS. Other things the proofs surfaced

- **The heartbeat window is not clamped in hardware.** docs/04 section 9 and docs/02 say the governor clamps any
  signed window to the policy's expiry. The RTL loads whatever 32-bit `window` it is given (rule RTL-HEARTBEAT-RELOADS-EXACT-WINDOW proves "exactly
  the window given"); the clamp lives in govsim (`governor.py`, `hb_expiry = min(...)`), so on the chip it is the
  firmware's job. A firmware bug can give a 49-day window. Not changed (it needs a policy register in hardware);
  recorded so nobody reads RTL-HEARTBEAT-RELOADS-EXACT-WINDOW as the clamp.
- **The meter has no freeze.** govsim freezes a slot at END_MODEL (`final`); the RTL keeps counting into it. The
  freeze is firmware state. Not a safety problem for the meter rules (counts only go up), an RTL/model difference.
- **The CSR window is read-only by construction, at full size.** Structural proof on the flattened netlist of the
  checked-in core: everything reachable from `csr_addr`, `epoch_host_wr` and `epoch_host_data` (194 netlist objects)
  contains no register and no pin but `csr_rdata`. From the doorbell (388 objects): only the mailbox's registers, its
  three outputs to the firmware, and `csr_rdata`. A two-copy semantic miter on the small build proves the same thing a
  second way (84 and 74 registers compared, k-induction in yices).
- **`epoch_host_wr` and `epoch_host_data` reach nothing at all.** They are in the CSR host set above.

## Proven, bounded only, and why

- heartbeat, meter, alarms, measure_reg, loop_io: the full-size blocks as checked in, bounded check plus k-induction
  (every reachable state), in yices, z3 and boolector. Plus thousands of random cycles each against a spec model in
  amaranth.sim. Every mutant caught by assertion.
- governor_core: RTL-PINS-FOLLOW-SEQUENCER, RTL-BOOTS-SAFE, RTL-HALT-REACHES-PINS, RTL-HALTED-STAYS-HALTED, RTL-EXPIRY-NOT-POSTPONED, RTL-LOSS-ALWAYS-SEEN and RTL-LOOP-STAYS-OPEN proven by k-induction (every reachable state) on the small build of the same `top.py`
  (2 entries per point, 2 tickets, 3 ms and 4 ms timers, a 4-tick millisecond), in yices, z3 and boolector. The
  design facts and the small-build miters run in yices only (minutes each in yices, far longer in the others on this
  shared machine). The randomized core simulation (3000 cycles, every rung visited, `load_hwm` hammered half the
  time) catches 5 of the 7 core mutants in the recorded run (`last-run-b.txt`). It misses "reading MBOX_STATUS
  restarts the millisecond" (a random address lands on 0x104 about once in 4096 cycles) and "the host's CSR address
  selects the meter slot" (it does not model the meter). The proofs catch both. The argument for why the small build covers the full
  size is in the header of `governor_core.sv`. The host rules are proven on the full-size netlist structurally, which
  holds for all time and at any size. Nothing in my set is bounded-only; what is "small build only" is listed here.
