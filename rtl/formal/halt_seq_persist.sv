// WAVE-FORMAL-PROOFS-ON-VERILOG, halt_seq: a halt survives a reset (adversarial audit 3). Proven on the generated
// sequencer (rtl/gen/halt_seq.v) with reset FREE in every cycle, not only at power-on: a power cycle is a reset of
// every register except the non-volatile rung record (rung_nv, rung_nv_safe: reset_less in the Amaranth source,
// standing for an NVM or fuse-backed register written by the hardware). Run: python -m rtl.formal halt_seq
// (rtl/formal/blocks_b.py runs it as one of halt_seq's checks, on the real Verilog and on every mutant).
// The rules:
//   RTL-HALT-RECORD-FOLLOWS-RUNG the record is set whenever the sequencer is in HALT or SAFE (any cause), and the SAFE record
//      whenever it is in SAFE; it is written in the same cycle the halt lands, so no reset can fall between the two.
//   RTL-HALT-RECORD-SURVIVES-RESET the record never falls except on an authorized clear (clear && clear_authorized) of a
//      chip that is not in HALTED_INITIAL; no reset, however often, touches it.
//   RTL-HALT-RECORD-BLOCKS-ARMING while the record is set the chip is never in RUN or THROTTLE, its loop switch never
//      closes, it never records an arming (hb_seen), and it is never excluded.
//   RTL-HALT-RESTORED-AFTER-RESET a chip that comes out of reset with the record set is in HALTED_INITIAL with every lever
//      asserted and the loop switch open, and one cycle later (unless a tamper or a HALT command takes that cycle) it is
//      in HALT, or in SAFE when the SAFE record is set, with cause 5 (C_PERSIST) and the loop switch open.
//   RTL-HALT-RESTORED-STAYS a halted chip (HALT or SAFE) leaves only by an authorized clear, and every lever stays asserted
//      except slot power in HALT, across any number of resets (a reset puts it in HALTED_INITIAL, which is safer, and
//      the next cycle restores the rung).
// Strengthening invariants for k-induction: the sequencer's state and cause encodings (cause 5 included), the switch
// in each halted rung, and the exclusion invariant of halt_seq.sv.
module halt_seq_persist_props(input clk, input rst, input hb_expired, tamper, cmd_halt, cmd_throttle, local_trip, clear,
                              clear_authorized, hb_ok, loop_sense, tick, loop_lost, cmd_exclude);
  wire [2:0] state, cause; wire pwrbrk, perst, pwr_en, switch_open, ports_closed; wire [19:0] timer;
  wire hb_seen, no_first_hb, excluded, rung_nv, rung_nv_safe; wire [15:0] boot_timer;
  halt_seq dut(.hb_expired(hb_expired),.tamper(tamper),.cmd_halt(cmd_halt),.cmd_throttle(cmd_throttle),.local_trip(local_trip),
    .clear(clear),.clear_authorized(clear_authorized),.hb_ok(hb_ok),.loop_sense(loop_sense),.tick(tick),.clk(clk),.rst(rst),.state(state),.pwrbrk(pwrbrk),
    .perst(perst),.pwr_en(pwr_en),.switch_open(switch_open),.ports_closed(ports_closed),.cause(cause),.timer(timer),.loop_lost(loop_lost),
    .cmd_exclude(cmd_exclude),.hb_seen(hb_seen),.boot_timer(boot_timer),.no_first_hb(no_first_hb),.excluded(excluded),
    .rung_nv(rung_nv),.rung_nv_safe(rung_nv_safe));
  wire clr = clear && clear_authorized;
  reg init = 1;
  always @(posedge clk) init <= 0;
  always @(*) begin
    if (!init) begin
      // strengthening: the encodings (cause 5 is the restored rung)
      assert(state <= 4); assert(cause <= 5);
      if (state == 0) assert(cause == 0);
      if (state == 1) assert(cause == 0 && !switch_open);
      if (state == 2) assert(cause == 2);
      if (cause == 5) assert(state == 3 || state == 4);
      if ((state == 3 || state == 4) && cause != 2) assert(switch_open);
      if (excluded) assert(state == 0 && cause == 0 && !switch_open);
      // RTL-HALT-RECORD-FOLLOWS-RUNG
      if (state == 3 || state == 4) assert(rung_nv);
      if (state == 4) assert(rung_nv_safe);
      if (rung_nv_safe) assert(rung_nv);
      // RTL-HALT-RECORD-BLOCKS-ARMING (the state half)
      if (rung_nv) assert(state != 1 && state != 2 && !excluded);
      if (rung_nv && state == 0) assert(switch_open && pwrbrk && perst && !pwr_en);
    end
  end
  always @(posedge clk) if (!init && !$past(init)) begin
    // RTL-HALT-RECORD-SURVIVES-RESET: the record falls only on an authorized clear, reset or no reset
    if ($past(rung_nv) && !rung_nv) assert($past(clr) && $past(state) != 0 && !$past(tamper));
    if ($past(rung_nv_safe) && !rung_nv_safe) assert($past(clr) && $past(state) != 0 && !$past(tamper));
    // RTL-HALT-RECORD-FOLLOWS-RUNG: it rises only with the chip in HALT or SAFE, or as a halt lands in a reset cycle
    if (!$past(rung_nv) && rung_nv) assert(state == 3 || state == 4 || $past(rst));
    // RTL-HALT-RECORD-BLOCKS-ARMING (the switch and the arming record): a reset opens the switch; nothing closes it
    if ($past(rung_nv) && !$past(rst) && $past(switch_open)) assert(switch_open);
    if ($past(rung_nv) && !$past(rst) && !$past(hb_seen)) assert(!hb_seen);
    // RTL-HALT-RESTORED-AFTER-RESET: out of reset with the record set, every lever asserted and the loop open
    if ($past(rst) && rung_nv) assert(state == 0 && switch_open && pwrbrk && perst && !pwr_en);
    // RTL-HALT-RESTORED-AFTER-RESET: the next cycle restores the rung on record with cause 5 and the loop open
    if (!$past(rst) && $past(state) == 0 && $past(rung_nv) && !$past(tamper) && !$past(cmd_halt))
      assert(state == ($past(rung_nv_safe) ? 3'd4 : 3'd3) && cause == 5 && switch_open);
    // RTL-HALT-RESTORED-STAYS: no way out of HALT or SAFE without an authorized clear (a reset only goes to the safer
    // HALTED_INITIAL, and the record brings the rung back)
    if (!$past(rst) && ($past(state) == 3 || $past(state) == 4) && !$past(clr)) assert(state == 3 || state == 4);
    if (!$past(rst) && $past(state) == 4 && !$past(clr)) assert(state == 4);
    if ($past(rst) && ($past(state) == 3 || $past(state) == 4) && !$past(clr)) assert(state == 0 && rung_nv);
  end
endmodule
