// L7, governor_core (rtl/governor_rtl/top.py, every block wired together): properties proven on Verilog generated
// from top.py. Run: python -m rtl.formal. Spec: docs/07-verification-plan.md section 3 (top row, halt, heartbeat,
// halt_loop rows), docs/04 sections 2 and 9, docs/01 (the ladder), docs/02 (the loop).
//
// Two kinds of proof run on the core:
//  1. The host cannot write: two miters on the FULL-SIZE core, the one that is checked in (rtl/formal/blocks_b.py,
//     host_miter). Two copies get the same inputs except the host's (csr_addr and the epoch host write port in one,
//     the doorbell in the other), which differ freely. Every register (outside the mailbox, for the doorbell) and
//     every pin must agree, every cycle. Every register is compared, so the property is 1-inductive and holds for
//     all time, at the real sizes: 8 entries per capability point, 30 s and 300 s timers, a 2^10 us millisecond.
//  2. The functional rules below, on a SMALL build of the same top.py: 2 entries per point, 2 tickets,
//     t_throttle 3 ms, t_halt 4 ms, a millisecond of 2^2 ticks (blocks_b.SMALL). The instance below is generated
//     from that build's port list, with every input free (anyseq).
//
// Why the small build says something about the big one (size and width independence):
//  - The cap tables and the ticket store have no path into the sequencer, the heartbeat, the loop or the pins: their
//    only inputs from the rest of the core are clear_all, now and epoch_tag, and their outputs go only to pins.
//    The full-size csr/doorbell miters exercise that same wiring. So their entry count cannot change RTL-PINS-FOLLOW-SEQUENCER to RTL-LOOP-STAYS-OPEN.
//  - The sequencer's timer comparisons (timer + 1 >= t) are proven at full size, 30 000 and 300 000, in
//    rtl/formal/halt_seq.sv. Here the same comparisons run at 3 and 4 so the solver can reach the top rungs.
//  - ms_div is a free-running counter of tick modulo 2^ms_shift and tick_ms fires when it is all ones. RTL-EXPIRY-NOT-POSTPONED holds
//    for that structure at any width; 2 bits is the smallest that is not trivial. The 10-bit chip value runs in
//    rtl/tests (test_governor_core_timers_run_on_the_millisecond_tick) and in the randomized simulation.
//  - Every other width (32-bit heartbeat, 64-bit counter, 256-bit registers) is the same in both builds.
//
// The rules:
//   RTL-PINS-FOLLOW-SEQUENCER the pins follow the sequencer exactly: brake released only in RUN, PERST# released only in RUN and THROTTLE,
//      slot power on only in RUN, THROTTLE, HALT; the loop pad follows the sequencer's switch.
//   RTL-BOOTS-SAFE the core boots on HALTED_INITIAL with every lever safe and the loop open.
//   RTL-HALT-REACHES-PINS a halt from any cause reaches the pins on the next cycle: tamper (SAFE, power off, loop open), a halt
//      command (HALT, loop open), a debounced loop loss while running (HALT, loop open), a heartbeat expiry while
//      running (THROTTLE, brake on). Clear and the higher-priority causes are the only things that can preempt.
//   RTL-HALTED-STAYS-HALTED a halted core never runs again without an authorized clear.
//   RTL-EXPIRY-NOT-POSTPONED heartbeat expiry cannot be postponed without a valid heartbeat: the millisecond strobe comes every 2^ms_shift
//      microsecond ticks without fail, whatever any other input does (load_hwm included), and the heartbeat's time
//      left goes down by one on each strobe and never up without hb_valid.
//   RTL-LOSS-ALWAYS-SEEN two consecutive samples without loop current always produce a loss (the current loss is always seen).
//   RTL-LOOP-STAYS-OPEN the loop, once opened, stays open until clear: the switch closes only in HALTED_INITIAL with no cause (only
//      boot or clear give that), by a live heartbeat (re-armed) or an authorized EXCLUDE; a cause stays until clear.
//      A chip halted by loop loss, a command or tamper keeps its loop pad open, EXCLUDE or not.
// Yobie's two calls, 23 October 2026 (docs/04 sections 2 and 3, docs/02 section 1):
//   RTL-HALT-REACHES-PINS now also: a halt command to a chip in SAFE opens the loop pad, the chip stays in SAFE with power off, and
//      CAUSE reads command (tamper keeps its cause). So a HALT in any state ends with the loop pad open.
//   RTL-EXCLUDED-LEVERS-SAFE an excluded chip has every lever asserted at the pins (brake, reset, power off) with its loop pad closed, and
//      it never reaches RUN until a valid heartbeat arms it.
//   RTL-ALARMS-HARDWARE-OWNED NO_FIRST_HEARTBEAT and EXCLUDED are hardware-owned, sticky ALARMS bits (31 and 30): each is set the cycle
//      after the sequencer raises it, rises only then (firmware's set_mask cannot), and NO_FIRST_HEARTBEAT is never
//      raised once the chip has been armed. The boot timer counts every millisecond strobe spent waiting, so with
//      RTL-EXPIRY-NOT-POSTPONED the alarm comes t_boot strobes (3 here, 5000 on the chip) after power-on without a heartbeat. CAUSE bits 3
//      and 4 and ALARMS read exactly those signals over the CSR window (and so over SMBus).
// Strengthening invariants for k-induction (the "S" lines): the sequencer's own (state and cause encodings, the
// switch in each rung), the heartbeat's expired/remaining relation, the debounce counter range, and the ghost
// that counts ticks since the last strobe equals the prescaler.
module governor_core_props(input clk, input rst);
  //@@DUT@@
  reg init = 1;
  always @(posedge clk) init <= 0;
  reg [1:0] since = 0;                    // ghost: microsecond ticks since the last millisecond strobe
  always @(posedge clk) if (rst) since <= 0; else if (tick) since <= tick_ms ? 2'd0 : since + 2'd1;
  wire running = halt_state == 1 || halt_state == 2;
  always @(*) begin
    assume(!rst || init);
    if (init) begin
      // RTL-BOOTS-SAFE: the power-on state, before anything has happened
      assert(halt_state == 0 && !pwrbrk_n && !perst_n && !pwr_en && loop_out_open);
    end else begin
      // RTL-PINS-FOLLOW-SEQUENCER
      assert(pwrbrk_n == (halt_state == 1));
      assert(perst_n == (halt_state == 1 || halt_state == 2));
      assert(pwr_en == (halt_state == 1 || halt_state == 2 || halt_state == 3));
      assert(loop_out_open == halt_switch_open);
      // RTL-EXPIRY-NOT-POSTPONED: the strobe is derived from the microsecond tick and comes on every 2^2-th one
      assert(!tick_ms || tick);
      assert(tick_ms == (tick && since == 2'd3));
      // RTL-LOSS-ALWAYS-SEEN (and S: the debounce counter)
      assert(loop_count <= 2);
      assert(loop_loop_lost == (loop_count == 2));
      // S: the sequencer
      assert(halt_state <= 4); assert(halt_cause <= 4);
      if (halt_state == 2) assert(halt_cause == 2);
      if (halt_state == 1) assert(halt_cause == 0 && !halt_switch_open);
      if (halt_state == 0) assert(halt_cause == 0);
      if ((halt_state == 3 || halt_state == 4) && halt_cause != 2) assert(halt_switch_open);
      // S: the heartbeat and the prescaler
      assert(hb_expired == (hb_remaining == 0));
      assert(since == ms_div);
      // RTL-EXCLUDED-LEVERS-SAFE, and S: the sequencer's exclusion and boot-window invariants (proven at full size in halt_seq.sv)
      if (halt_excluded) assert(halt_state == 0 && halt_cause == 0 && !pwrbrk_n && !perst_n && !pwr_en && !loop_out_open);
      assert(halt_no_first_hb == (!halt_hb_seen && halt_boot_timer >= 16'd3));
      if (halt_state == 1 || halt_state == 2 || halt_cause == 2) assert(halt_hb_seen);
      // RTL-ALARMS-HARDWARE-OWNED: what the operator reads
      if (csr_addr == 12'h00C) assert(csr_rdata[2:0] == halt_cause && csr_rdata[3] == halt_no_first_hb && csr_rdata[4] == halt_excluded);
      if (csr_addr == 12'h084) assert(csr_rdata == alarms_alarms);
      if (csr_addr == 12'h088) assert(csr_rdata == {16'd0, halt_boot_timer});
    end
  end
  always @(posedge clk) if (!init && !$past(init) && !$past(rst)) begin
    // RTL-HALT-REACHES-PINS, tamper
    if ($past(halt_tamper) && !$past(halt_clear))
      assert(halt_state == 4 && !pwrbrk_n && !perst_n && !pwr_en && loop_out_open);
    // RTL-HALT-REACHES-PINS, a halt command, from every rung but SAFE
    if ($past(halt_cmd_halt) && !$past(halt_clear) && !$past(halt_tamper) && $past(halt_state) != 4)
      assert(halt_state == 3 && !pwrbrk_n && !perst_n && loop_out_open);
    // RTL-HALT-REACHES-PINS, a halt command to a chip already in SAFE: the loop pad opens, SAFE stays, power stays off (Yobie's call 1)
    if ($past(halt_cmd_halt) && !$past(halt_clear) && !$past(halt_tamper) && $past(halt_state) == 4)
      assert(halt_state == 4 && !pwr_en && loop_out_open && halt_cause == ($past(halt_cause) == 3 ? 3'd3 : 3'd4));
    // RTL-HALT-REACHES-PINS, so in any state: a halt command ends with the loop pad open unless an authorized CLEAR took that cycle
    if ($past(halt_cmd_halt) && !($past(halt_clear) && $past(halt_state) != 0)) assert(loop_out_open);
    // RTL-HALT-REACHES-PINS, a loop loss while running
    if ($past(loop_loop_lost) && ($past(halt_state) == 1 || $past(halt_state) == 2) && !$past(halt_clear) && !$past(halt_tamper))
      assert(halt_state == 3 && !pwrbrk_n && !perst_n && loop_out_open);
    // RTL-HALT-REACHES-PINS, a heartbeat expiry while running
    if ($past(hb_expired) && $past(halt_state) == 1 && !$past(halt_clear) && !$past(halt_tamper) && !$past(loop_loop_lost)
        && !$past(halt_cmd_halt))
      assert(halt_state == 2 && !pwrbrk_n);
    // RTL-HALTED-STAYS-HALTED
    if (($past(halt_state) == 3 || $past(halt_state) == 4) && !$past(halt_clear)) assert(halt_state == 3 || halt_state == 4);
    if ($past(halt_state) != 1 && halt_state == 1) assert($past(halt_state) == 0 && !$past(hb_expired));
    // RTL-EXPIRY-NOT-POSTPONED: the heartbeat
    if (!$past(hb_hb_valid)) assert(hb_remaining <= $past(hb_remaining));
    if (!$past(hb_hb_valid) && !$past(tick_ms)) assert(hb_remaining == $past(hb_remaining));
    if (!$past(hb_hb_valid) && $past(tick_ms) && $past(hb_remaining) != 0) assert(hb_remaining == $past(hb_remaining) - 1);
    // RTL-LOSS-ALWAYS-SEEN
    if ($past(sample) && !$past(loop_sense) && $past(loop_count) >= 1) assert(loop_loop_lost);
    // RTL-LOOP-STAYS-OPEN
    if ($past(halt_switch_open) && !halt_switch_open)
      assert($past(halt_state) == 0 && $past(halt_cause) == 0 && (!$past(hb_expired) || $past(halt_cmd_exclude)));
    if ($past(halt_cause) != 0 && halt_cause == 0) assert($past(halt_clear));
    if (($past(halt_state) == 3 || $past(halt_state) == 4) && $past(halt_cause) != 2 && !$past(halt_clear)) assert(loop_out_open);
    // RTL-EXCLUDED-LEVERS-SAFE: an excluded chip does not run before a valid heartbeat
    if ($past(halt_excluded) && $past(hb_expired)) assert(halt_state != 1 && !pwrbrk_n && !perst_n);
    // RTL-ALARMS-HARDWARE-OWNED: the hardware alarm bits
    if ($past(halt_no_first_hb)) assert(alarms_alarms[31]);
    if (!$past(alarms_alarms[31]) && alarms_alarms[31]) assert($past(halt_no_first_hb));
    if ($past(halt_hb_seen) && !$past(alarms_alarms[31])) assert(!alarms_alarms[31]);
    if ($past(halt_excluded)) assert(alarms_alarms[30]);
    if (!$past(alarms_alarms[30]) && alarms_alarms[30]) assert($past(halt_excluded));
    if (!$past(halt_hb_seen) && $past(halt_state) == 0 && $past(halt_cause) == 0 && $past(hb_expired) && $past(tick_ms)
        && $past(halt_boot_timer) != 16'hffff) assert(halt_boot_timer == $past(halt_boot_timer) + 16'd1);
    if ($past(halt_hb_seen)) assert(halt_hb_seen && !halt_no_first_hb);
  end
endmodule
