// L7, halt_seq: properties proven on the generated Verilog (rtl/gen/halt_seq.v), not on the Python model.
// Run: python -m rtl.formal. Bounded check to 25 cycles, then k-induction, which makes the result hold for every
// reachable state, at any depth. The spec these encode is docs/07-verification-plan.md, the halt row.
module halt_seq_props(input clk, input rst, input hb_expired, tamper, cmd_halt, cmd_throttle, local_trip, clear, hb_ok, loop_sense, tick, loop_lost);
  wire [2:0] state, cause; wire pwrbrk, perst, pwr_en, switch_open, ports_closed; wire [19:0] timer;
  halt_seq dut(.hb_expired(hb_expired),.tamper(tamper),.cmd_halt(cmd_halt),.cmd_throttle(cmd_throttle),.local_trip(local_trip),
    .clear(clear),.hb_ok(hb_ok),.loop_sense(loop_sense),.tick(tick),.clk(clk),.rst(rst),.state(state),.pwrbrk(pwrbrk),
    .perst(perst),.pwr_en(pwr_en),.switch_open(switch_open),.ports_closed(ports_closed),.cause(cause),.timer(timer),.loop_lost(loop_lost));
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
      assert(cause <= 4);
      if (state == 2) assert(cause == 2);
      if (state == 1) assert(cause == 0 && !switch_open);
      if (state == 0) assert(cause == 0);
      if (state == 1) assert(!switch_open);
    end
  end
  always @(posedge clk) if (!init && !$past(init) && !$past(rst)) begin
    // P: a halted chip (HALT or SAFE) never returns to running without an authorized clear
    if (($past(state) == 3 || $past(state) == 4) && !$past(clear)) assert(state == 3 || state == 4);
    // P: tamper always lands in SAFE, CLEAR or no CLEAR. The first version of this line said "unless cleared that
    // same cycle", which wrote the bug's excuse into the proof (conformance finding F-05); the excuse is gone
    if ($past(tamper)) assert(state == 4 && cause == 3);
    // P: the chip enters RUN only on a clean loop sample (FPGA finding F1)
    if (state == 1 && $past(state) != 1) assert($past(loop_sense) && !$past(loop_lost));
    // P: from SAFE nothing but clear moves the state
    if ($past(state) == 4 && !$past(clear)) assert(state == 4);
    // P: a halt command is obeyed from every rung but SAFE (unless clear or tamper wins that cycle)
    if ($past(cmd_halt) && !$past(clear) && !$past(tamper) && $past(state) != 4) assert(state == 3 && switch_open);
    // P: the rungs climb on their timers: THROTTLE to HALT after t_throttle ticks, HALT to SAFE after t_halt
    if ($past(state) == 2 && $past(tick) && $past(timer) + 1 >= 30000 && !$past(clear) && !$past(tamper)
        && !$past(loop_lost) && !$past(cmd_halt)) assert(state == 3);
    if ($past(state) == 3 && $past(tick) && $past(timer) + 1 >= 300000 && !$past(clear) && !$past(tamper)
        && !$past(cmd_halt)) assert(state == 4);
  end
endmodule
