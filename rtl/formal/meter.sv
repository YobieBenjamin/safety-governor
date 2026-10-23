// L7, meter: properties proven on the generated Verilog (rtl/gen/meter.v), the full block: 4 slots, 48-bit counters.
// Run: python -m rtl.formal. Spec: docs/07-verification-plan.md section 3 (meter row), docs/04 section 2
// (METER_SLOT read-only), govsim/governor.py (the compute budget compares metered cycles against the licence).
// The rules, for every slot and every one of the four counters:
//   E1 never decreases. This is what makes the meter usable as evidence for a budget: a counter that can go
//      down lets a job spend past its budget and then read as under it.
//   E2 changes only on strobe for that slot, and then by exactly the amount added, saturating at all ones
//      (a counter that would wrap stops at the top, which reads as "over every budget", the safe side).
//   E3 the host cannot write: host_wr changes nothing (E2 already says only strobe moves a counter) and is
//      flagged (host_wr_refused == host_wr).
// The slot under watch is a solver-chosen constant (anyconst) driven onto rd_slot, so one proof covers every
// slot: the solver may pick any of them. Strengthening for k-induction: none needed, every rule is one step.
module meter_props(input clk, input rst, input strobe, input host_wr, input [1:0] slot,
                   input [47:0] add_tokens, input [47:0] add_cycles, input [47:0] add_in, input [47:0] add_out);
  (* anyconst *) reg [1:0] watch;
  wire [47:0] rd_tokens, rd_cycles, rd_in, rd_out; wire host_wr_refused;
  meter dut(.add_tokens(add_tokens), .add_cycles(add_cycles), .add_in(add_in), .add_out(add_out), .strobe(strobe),
    .host_wr(host_wr), .rd_slot(watch), .clk(clk), .rst(rst), .host_wr_refused(host_wr_refused), .rd_tokens(rd_tokens),
    .rd_cycles(rd_cycles), .rd_in(rd_in), .rd_out(rd_out), .slot(slot));
  reg init = 1;
  always @(posedge clk) init <= 0;
  function [47:0] sat(input [47:0] a, input [47:0] b);
    reg [48:0] s; begin s = {1'b0, a} + {1'b0, b}; sat = s[48] ? 48'hFFFF_FFFF_FFFF : s[47:0]; end
  endfunction
  always @(*) begin
    assume(!rst || init);
    if (!init) assert(host_wr_refused == host_wr);                              // E3
  end
  always @(posedge clk) if (!init && !$past(init) && !$past(rst)) begin
    // E1
    assert(rd_tokens >= $past(rd_tokens)); assert(rd_cycles >= $past(rd_cycles));
    assert(rd_in >= $past(rd_in));         assert(rd_out >= $past(rd_out));
    // E2
    if (!($past(strobe) && $past(slot) == watch)) begin
      assert(rd_tokens == $past(rd_tokens)); assert(rd_cycles == $past(rd_cycles));
      assert(rd_in == $past(rd_in));         assert(rd_out == $past(rd_out));
    end else begin
      assert(rd_tokens == sat($past(rd_tokens), $past(add_tokens)));
      assert(rd_cycles == sat($past(rd_cycles), $past(add_cycles)));
      assert(rd_in == sat($past(rd_in), $past(add_in)));
      assert(rd_out == sat($past(rd_out), $past(add_out)));
    end
  end
endmodule
