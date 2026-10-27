// WAVE-FORMAL-PROOFS-ON-VERILOG, halt_seq: properties proven on the generated Verilog (rtl/gen/halt_seq.v), not on the Python model.
// Run: python -m rtl.formal. Bounded check to 25 cycles, then k-induction, which makes the result hold for every
// reachable state, at any depth. The spec these encode is docs/07-verification-plan.md, the halt row.
//
// Yobie's two design calls (23 October 2026, docs/04 sections 2 and 3, docs/02 section 1) add three groups:
//   H  a HALT opens the loop on every rung: cmd_halt in any state ends with the loop switch open, unless an
//      authorized CLEAR wins that cycle (CLEAR outranks HALT, tamper outranks both). In SAFE the state stays SAFE
//      and the command becomes the cause on record (tamper keeps its cause).
//   X  EXCLUDE: an excluded chip sits in HALTED_INITIAL with no cause, its loop switch closed and all three levers
//      asserted (brake, reset, power off) until a valid heartbeat arms it; exclusion is entered only by cmd_exclude in
//      HALTED_INITIAL with no cause and no live heartbeat; the loop switch closes only in HALTED_INITIAL with no cause
//      (by a heartbeat or an EXCLUDE), so a chip halted by loop loss, a command or tamper keeps its loop open whatever
//      EXCLUDE says. A two-copy miter (rtl/formal/blocks_b.py, halt_seq checks) proves EXCLUDE changes nothing at all
//      outside HALTED_INITIAL with no cause.
//   N  NO_FIRST_HEARTBEAT: no_first_hb is exactly "never armed since reset and the boot window (5000 ms here, the
//      chip value) has passed"; the boot timer counts every millisecond spent waiting and nothing else; hb_seen rises
//      only by arming and never falls, so once armed the alarm can never be raised again.
//
// Adversarial audit 3 (rtl/governor_rtl/halt.py docstring) adds:
//   C  a clear is the firmware's clear AND the hardware's clear_authorized (a verified CLEAR frame dispatching) in the
//      same cycle. Every rule below that used to say "unless clear" now says "unless clear && clear_authorized"
//      (clr below), which is a stronger statement: an unauthorized clear excuses nothing.
//   L  a lost heartbeat in RUN or THROTTLE goes to HALT (brake and reset) with the local cause, loop switch closed.
//   R  the non-volatile rung record: rung_nv is exactly "in HALT or SAFE" and rung_nv_safe exactly "in SAFE" (with no
//      reset after power-on, which is what this file assumes); the record falls only on clr. Its behaviour across a
//      reset (survives it, blocks arming, restores HALT or SAFE with cause 5) is proven in halt_seq_persist.sv, with
//      reset free in every cycle (rtl/formal/blocks_b.py, halt_seq checks).
module halt_seq_props(input clk, input rst, input hb_expired, tamper, cmd_halt, cmd_throttle, local_trip, clear, clear_authorized, hb_ok, loop_sense, tick, loop_lost, cmd_exclude);
  wire [2:0] state, cause; wire pwrbrk, perst, pwr_en, switch_open, ports_closed; wire [19:0] timer;
  wire hb_seen, no_first_hb, excluded, rung_nv, rung_nv_safe; wire [15:0] boot_timer;
  halt_seq dut(.hb_expired(hb_expired),.tamper(tamper),.cmd_halt(cmd_halt),.cmd_throttle(cmd_throttle),.local_trip(local_trip),
    .clear(clear),.clear_authorized(clear_authorized),.hb_ok(hb_ok),.loop_sense(loop_sense),.tick(tick),.clk(clk),.rst(rst),.state(state),.pwrbrk(pwrbrk),
    .perst(perst),.pwr_en(pwr_en),.switch_open(switch_open),.ports_closed(ports_closed),.cause(cause),.timer(timer),.loop_lost(loop_lost),
    .cmd_exclude(cmd_exclude),.hb_seen(hb_seen),.boot_timer(boot_timer),.no_first_hb(no_first_hb),.excluded(excluded),
    .rung_nv(rung_nv),.rung_nv_safe(rung_nv_safe));
  wire clr = clear && clear_authorized;   // C: the only clear that counts (adversarial audit 3)
  reg init = 1;
  always @(posedge clk) init <= 0;
  always @(*) begin
    assume(!rst || init);
    assume(init == rst || !init);
    if (!init) begin
      assert(state <= 4);
      // the levers follow the state: power brake and closed ports whenever not RUN
      assert(pwrbrk == (state != 1));
      assert(ports_closed == (state != 1));
      // in a halted rung the loop switch is open
      if ((state == 3 || state == 4) && cause != 2) assert(switch_open);
      // cause 5 (restored from the non-volatile record, adversarial audit 3) is possible here only through the
      // power-on reset cycle (see R below); before that change this line said cause <= 4
      assert(cause <= 5);
      if (state == 2) assert(cause == 2);
      // L (and strengthening): a local cause never opens the loop switch, so a lost heartbeat's HALT keeps it closed
      if (cause == 2) assert(!switch_open);
      if (state == 1) assert(cause == 0 && !switch_open);
      if (state == 0) assert(cause == 0);
      if (state == 1) assert(!switch_open);
      // X: an excluded chip is in HALTED_INITIAL with no cause, its switch closed, every lever asserted
      if (excluded) assert(state == 0 && cause == 0 && !switch_open && pwrbrk && perst && !pwr_en);
      // N: the alarm level is exactly "never armed and the window has passed"
      assert(no_first_hb == (!hb_seen && boot_timer >= 16'd5000));
      // N: running or throttled means the chip was armed (strengthening, and it pins RUN to arming)
      if (state == 1 || state == 2 || cause == 2) assert(hb_seen);
      // R: the non-volatile record covers every halted rung; the SAFE record is set exactly in SAFE or on the way back
      // to it. The record ignores reset (it stands for NVM), so a tamper or HALT strobe in the power-on reset cycle is
      // remembered even though the state register drops it: the only other place the record is set is HALTED_INITIAL
      // right after that reset, with no cause, every lever asserted and the loop switch open, and the next cycle
      // restores HALT or SAFE with cause 5
      if (state == 3 || state == 4) assert(rung_nv);
      if (state == 4) assert(rung_nv_safe);
      if (rung_nv_safe) assert(rung_nv && (state == 4 || state == 0));
      if (rung_nv && state != 3 && state != 4) assert(state == 0 && cause == 0 && switch_open && !hb_seen && !excluded);
      if (cause == 5) assert(state == 3 || state == 4);
    end
  end
  always @(posedge clk) if (!init && !$past(init) && !$past(rst)) begin
    // P: a halted chip (HALT or SAFE) never returns to running without an authorized clear
    if (($past(state) == 3 || $past(state) == 4) && !$past(clr)) assert(state == 3 || state == 4);
    // P: tamper always lands in SAFE, CLEAR or no CLEAR. The first version of this line said "unless cleared that
    // same cycle", which wrote the bug's excuse into the proof (conformance finding CONFORMANCE-CLEAR-BEATS-TAMPER); the excuse is gone
    if ($past(tamper)) assert(state == 4 && cause == 3);
    // P: the chip enters RUN only on a clean loop sample (FPGA finding RTL-CORE-HALTS-AFTER-REACHING-RUN), and only with a live heartbeat
    if (state == 1 && $past(state) != 1) assert($past(loop_sense) && !$past(loop_lost) && $past(hb_ok));
    // P: from SAFE nothing but clear moves the state
    if ($past(state) == 4 && !$past(clr)) assert(state == 4);
    // P: a halt command is obeyed from every rung but SAFE (unless clear or tamper wins that cycle). R: the one case
    // where it lands higher than HALT is a chip whose non-volatile record says SAFE, which goes back to SAFE
    if ($past(cmd_halt) && !$past(clr) && !$past(tamper) && $past(state) != 4)
      assert((state == 3 || (state == 4 && $past(state) == 0 && $past(rung_nv_safe))) && switch_open);
    // H: a halt command opens the loop in every state, SAFE included, unless an authorized CLEAR took that cycle
    if ($past(cmd_halt) && !($past(clr) && $past(state) != 0)) assert(switch_open);
    // H: in SAFE it stays SAFE (no descent, power stays off) and the command is the cause, unless the cause is tamper
    if ($past(cmd_halt) && !$past(clr) && !$past(tamper) && $past(state) == 4)
      assert(state == 4 && !pwr_en && switch_open && cause == ($past(cause) == 3 ? 3'd3 : 3'd4));
    // C: a clear without the hardware's authorization does not release a halted chip (the lines above already say it
    // through clr; this says it in terms of the firmware's clear wire alone)
    if ($past(clear) && !$past(clear_authorized) && ($past(state) == 3 || $past(state) == 4)) assert(state == 3 || state == 4);
    // L: a lost heartbeat in RUN or THROTTLE is HALT with the local cause and the loop switch closed (adversarial audit 3:
    // the brake alone leaves the GPU computing at half clock), unless something stronger takes that cycle
    if ($past(hb_expired) && ($past(state) == 1 || $past(state) == 2) && !$past(tamper) && !$past(clr) && !$past(loop_lost) && !$past(cmd_halt))
      assert(state == 3 && cause == 2 && !switch_open && perst && pwrbrk);
    // L: local_trip and cmd_throttle in RUN (no heartbeat loss, nothing stronger) go to THROTTLE, as before
    if (($past(local_trip) || $past(cmd_throttle)) && $past(state) == 1 && !$past(hb_expired) && !$past(tamper) && !$past(clr)
        && !$past(loop_lost) && !$past(cmd_halt)) assert(state == 2 && cause == 2 && !switch_open);
    // R: the record falls only on an authorized clear, and rises only as the chip enters HALT or SAFE
    if ($past(rung_nv) && !rung_nv) assert($past(clr) && $past(state) != 0);
    if (!$past(rung_nv_safe) && rung_nv_safe) assert(state == 4);
    // P: the rungs climb on their timers: THROTTLE to HALT after t_throttle ticks, HALT to SAFE after t_halt
    if ($past(state) == 2 && $past(tick) && $past(timer) + 1 >= 30000 && !$past(clr) && !$past(tamper)
        && !$past(loop_lost) && !$past(cmd_halt)) assert(state == 3);
    if ($past(state) == 3 && $past(tick) && $past(timer) + 1 >= 300000 && !$past(clr) && !$past(tamper)
        && !$past(cmd_halt)) assert(state == 4);
    // X: exclusion starts only from an EXCLUDE in HALTED_INITIAL with no cause and no live heartbeat
    if (!$past(excluded) && excluded)
      assert($past(cmd_exclude) && $past(state) == 0 && $past(cause) == 0 && !$past(hb_ok) && !$past(tamper) && !$past(cmd_halt));
    // X: exclusion ends only by a heartbeat arming the chip, a HALT or a tamper (and reset)
    if ($past(excluded) && !excluded) assert($past(hb_ok) || $past(cmd_halt) || $past(tamper));
    if ($past(excluded) && !excluded && $past(hb_ok) && !$past(cmd_halt) && !$past(tamper)) assert(hb_seen && state != 3 && state != 4);
    // X: the levers of an excluded chip stay asserted until a valid heartbeat: no RUN, brake and reset held, power
    // off unless a HALT (which opens the loop) moved it to the HALT rung
    if ($past(excluded) && !$past(hb_ok)) assert(state != 1 && pwrbrk && perst && (!pwr_en || (state == 3 && switch_open)));
    // X: the loop switch closes only in HALTED_INITIAL with no cause, by a live heartbeat or an EXCLUDE
    if ($past(switch_open) && !switch_open)
      assert($past(state) == 0 && $past(cause) == 0 && !$past(tamper) && !$past(cmd_halt) && ($past(hb_ok) || $past(cmd_exclude)));
    // X: so a chip halted by loop loss, a command or tamper keeps its loop open until CLEAR, EXCLUDE or not
    if (($past(state) == 3 || $past(state) == 4) && ($past(cause) == 1 || $past(cause) == 3 || $past(cause) == 4) && !$past(clr))
      assert(switch_open);
    // X: an EXCLUDE anywhere but HALTED_INITIAL with no cause does not exclude
    if ($past(cmd_exclude) && !($past(state) == 0 && $past(cause) == 0)) assert(!excluded || $past(excluded));
    // N: hb_seen rises only by arming and never falls before reset
    if ($past(hb_seen)) assert(hb_seen);
    if (!$past(hb_seen) && hb_seen) assert($past(hb_ok) && $past(state) == 0 && $past(cause) == 0 && !$past(tamper) && !$past(cmd_halt));
    // N: arming (HALTED_INITIAL, no cause, a live heartbeat, no record of an uncleared halt, nothing stronger that
    // cycle) always records it
    if ($past(state) == 0 && $past(cause) == 0 && $past(hb_ok) && !$past(rung_nv) && !$past(tamper) && !$past(cmd_halt)) assert(hb_seen);
    // R: while the record of an uncleared halt is set the chip never arms: no RUN, no arming recorded, no switch closing
    if ($past(rung_nv)) assert(state != 1 && state != 2 && !(hb_seen && !$past(hb_seen)) && !(!switch_open && $past(switch_open)));
    // R: and out of HALTED_INITIAL it goes straight back to the rung on record, cause 5, loop open
    if ($past(rung_nv) && $past(state) == 0 && !$past(tamper))
      assert(state == ($past(rung_nv_safe) ? 3'd4 : 3'd3) && cause == 5 && switch_open);
    // N: once armed the alarm level is low for good
    if ($past(hb_seen)) assert(!no_first_hb);
    // N: the boot timer counts each millisecond spent waiting for the first heartbeat (saturating), and nothing else
    if (!$past(hb_seen) && $past(state) == 0 && $past(cause) == 0 && !$past(hb_ok) && $past(tick) && $past(boot_timer) != 16'hffff)
      assert(boot_timer == $past(boot_timer) + 16'd1);
    if (boot_timer != $past(boot_timer))
      assert(boot_timer == $past(boot_timer) + 16'd1 && $past(tick) && !$past(hb_seen) && $past(state) == 0 && $past(cause) == 0 && !$past(hb_ok));
  end
endmodule
