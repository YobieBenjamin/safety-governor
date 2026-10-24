// WAVE-FORMAL-PROOFS-ON-VERILOG, measure_reg: properties proven on the generated Verilog (rtl/gen/measure_reg.v), the full 256-bit register.
// Run: python -m rtl.formal. Spec: docs/07-verification-plan.md section 3 (measure_reg row), docs/04 section 2
// (MEAS0/MEAS1 extend-only), the block docstring. The rules:
//   RTL-MEASUREMENT-EXTEND-ONLY-RULE extend-only: value changes only on the cycle the hash engine answers a request this block made
//      (busy, hash_done), and then becomes exactly hash_out. No write port, no other path, no partial write.
//   RTL-MEASUREMENT-HASH-CHAINS-VALUE the engine is fed the chain: hash_in == {value, data} (the old value is always part of the hash input,
//      so an extend cannot replace the value with something that does not depend on it).
//   RTL-MEASUREMENT-ONE-REQUEST-AT-ONCE one request at a time: hash_req pulses only from idle on extend, and busy is entered only by a request.
//      An engine answer that nobody asked for (hash_done while idle) is ignored.
// Strengthening for k-induction: the rules are about one transition each, given busy, so 1-step induction closes.
module measure_reg_props(input clk, input rst, input extend, input [255:0] data, input hash_done, input [255:0] hash_out);
  wire hash_req, busy; wire [511:0] hash_in; wire [255:0] value;
  measure_reg dut(.data(data), .hash_done(hash_done), .hash_out(hash_out), .clk(clk), .rst(rst), .hash_req(hash_req),
    .hash_in(hash_in), .value(value), .busy(busy), .extend(extend));
  reg init = 1;
  always @(posedge clk) init <= 0;
  always @(*) begin
    assume(!rst || init);
    if (!init) begin
      assert(hash_in == {value, data});                                        // RTL-MEASUREMENT-HASH-CHAINS-VALUE
      assert(hash_req == (extend && !busy));                                   // RTL-MEASUREMENT-ONE-REQUEST-AT-ONCE
    end
  end
  always @(posedge clk) if (!init && !$past(init) && !$past(rst)) begin
    // RTL-MEASUREMENT-EXTEND-ONLY-RULE
    if (!($past(busy) && $past(hash_done))) assert(value == $past(value));
    if ($past(busy) && $past(hash_done)) assert(value == $past(hash_out));
    // RTL-MEASUREMENT-ONE-REQUEST-AT-ONCE: busy is entered only through a request and left only on the engine's answer
    if (busy && !$past(busy)) assert($past(hash_req));
    if ($past(busy) && !$past(hash_done)) assert(busy);
    if ($past(busy) && $past(hash_done)) assert(!busy);
    if (!$past(busy) && !$past(hash_req)) assert(!busy);
  end
endmodule
