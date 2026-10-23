// L7, alarms: properties proven on the generated Verilog (rtl/gen/alarms.v), the full 32-bit register.
// Run: python -m rtl.formal. Spec: docs/07-verification-plan.md section 3 (alarms row), docs/04 section 2 (ALARMS is
// sticky, cleared only through the clear path), hypothesis H5 (alarms are monotone). The rules:
//   A1 monotone: a set bit stays set unless that very bit is in clear_mask while clear_authorized is high.
//   A2 any source can raise: a bit in set_mask is set next cycle, whatever the clear path says that cycle
//      (raise beats clear, so a clear racing a fresh alarm cannot swallow it).
//   A3 nothing else sets a bit: a bit goes 0 to 1 only through set_mask.
//   A4 the summary and the refusal flag are exact: any == (alarms != 0); clear_refused == (clear_mask != 0 && !auth).
// Every rule is about one transition, so plain 1-step induction closes; no strengthening invariant is needed.
module alarms_props(input clk, input rst, input [31:0] set_mask, input [31:0] clear_mask, input clear_authorized);
  wire [31:0] alarms; wire any, clear_refused;
  alarms dut(.clear_mask(clear_mask), .clear_authorized(clear_authorized), .clk(clk), .rst(rst), .alarms(alarms),
    .any(any), .clear_refused(clear_refused), .set_mask(set_mask));
  reg init = 1;
  always @(posedge clk) init <= 0;
  always @(*) begin
    assume(!rst || init);
    if (!init) begin
      assert(any == (alarms != 0));                                            // A4
      assert(clear_refused == ((clear_mask != 0) && !clear_authorized));       // A4
    end
  end
  always @(posedge clk) if (!init && !$past(init) && !$past(rst)) begin
    // A1: bits that were set and not authorized-cleared are still set
    assert((($past(alarms) & ~($past(clear_mask) & {32{$past(clear_authorized)}})) & ~alarms) == 0);
    // A1 without authorization nothing clears at all
    if (!$past(clear_authorized)) assert(($past(alarms) & ~alarms) == 0);
    // A2
    assert(($past(set_mask) & ~alarms) == 0);
    // A3
    assert((alarms & ~$past(alarms) & ~$past(set_mask)) == 0);
    // and an authorized clear does clear the bits it names (unless raised again that cycle)
    if ($past(clear_authorized)) assert((alarms & $past(clear_mask) & ~$past(set_mask)) == 0);
  end
endmodule
