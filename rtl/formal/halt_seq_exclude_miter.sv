// WAVE-FORMAL-PROOFS-ON-VERILOG, halt_seq: EXCLUDE does nothing outside HALTED_INITIAL with no cause (Yobie's call 2, 23 October 2026).
// Two copies of the generated sequencer (rtl/gen/halt_seq.v) get the same inputs, except that copy a sees the free
// cmd_exclude and copy b never does. Whenever the two hold the same registers and copy a is anywhere but
// HALTED_INITIAL with no cause, they hold the same registers one cycle later: in RUN, THROTTLE, HALT and SAFE, and in
// HALTED_INITIAL once a cause is recorded, an EXCLUDE changes nothing at all, not a bit of any register. The property
// is about one transition, so it holds for all time (k-induction closes at once). Run: python -m rtl.formal halt_seq.
module halt_seq_exclude_miter_props(input clk, input rst, input hb_expired, tamper, cmd_halt, cmd_throttle, local_trip,
                                    clear, clear_authorized, hb_ok, loop_sense, tick, loop_lost, cmd_exclude);
  wire [2:0] state_a, cause_a, state_b, cause_b; wire [19:0] timer_a, timer_b; wire [15:0] boot_a, boot_b;
  wire sw_a, sw_b, seen_a, seen_b, exc_a, exc_b, nv_a, nv_b, nvs_a, nvs_b;   // nv: the non-volatile rung record (adversarial audit 3)
  wire pwrbrk_a, perst_a, pwr_en_a, pc_a, nfh_a, pwrbrk_b, perst_b, pwr_en_b, pc_b, nfh_b;
  halt_seq a(.hb_expired(hb_expired),.tamper(tamper),.cmd_halt(cmd_halt),.cmd_throttle(cmd_throttle),.local_trip(local_trip),
    .clear(clear),.clear_authorized(clear_authorized),.hb_ok(hb_ok),.loop_sense(loop_sense),.tick(tick),.clk(clk),.rst(rst),.loop_lost(loop_lost),.cmd_exclude(cmd_exclude),
    .state(state_a),.cause(cause_a),.timer(timer_a),.boot_timer(boot_a),.switch_open(sw_a),.hb_seen(seen_a),.excluded(exc_a),
    .pwrbrk(pwrbrk_a),.perst(perst_a),.pwr_en(pwr_en_a),.ports_closed(pc_a),.no_first_hb(nfh_a),.rung_nv(nv_a),.rung_nv_safe(nvs_a));
  halt_seq b(.hb_expired(hb_expired),.tamper(tamper),.cmd_halt(cmd_halt),.cmd_throttle(cmd_throttle),.local_trip(local_trip),
    .clear(clear),.clear_authorized(clear_authorized),.hb_ok(hb_ok),.loop_sense(loop_sense),.tick(tick),.clk(clk),.rst(rst),.loop_lost(loop_lost),.cmd_exclude(1'b0),
    .state(state_b),.cause(cause_b),.timer(timer_b),.boot_timer(boot_b),.switch_open(sw_b),.hb_seen(seen_b),.excluded(exc_b),
    .pwrbrk(pwrbrk_b),.perst(perst_b),.pwr_en(pwr_en_b),.ports_closed(pc_b),.no_first_hb(nfh_b),.rung_nv(nv_b),.rung_nv_safe(nvs_b));
  wire same = state_a == state_b && cause_a == cause_b && timer_a == timer_b && boot_a == boot_b && sw_a == sw_b
              && seen_a == seen_b && exc_a == exc_b && nv_a == nv_b && nvs_a == nvs_b;
  reg init = 1;
  always @(posedge clk) init <= 0;
  always @(*) assume(!rst || init);
  always @(posedge clk) if (!init && !$past(init) && !$past(rst)) begin
    if ($past(same) && !($past(state_a) == 0 && $past(cause_a) == 0))
      assert(same && pwrbrk_a == pwrbrk_b && perst_a == perst_b && pwr_en_a == pwr_en_b && nfh_a == nfh_b);
  end
endmodule
