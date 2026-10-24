// WAVE-FORMAL-PROOFS-ON-VERILOG, heartbeat: properties proven on the generated Verilog (rtl/gen/heartbeat.v), the full 32-bit block.
// Run: python -m rtl.formal. Spec: docs/07-verification-plan.md section 3 (heartbeat row), docs/04 section 9,
// govsim/governor.py (hb_expiry). The rules:
//   RTL-HEARTBEAT-REMAINING-NEVER-RISES expiry cannot be postponed without a valid heartbeat: without hb_valid, remaining never goes up.
//   RTL-HEARTBEAT-RELOADS-EXACT-WINDOW remaining reloads only on hb_valid, and then to exactly the window given (no more, no less).
//   RTL-HEARTBEAT-EXPIRED-AT-ZERO expired is exactly "remaining is zero", so it asserts on the tick that runs the window out.
//   RTL-HEARTBEAT-COUNTDOWN-EXACT the countdown is exact: after a reload with window W and g ticks with no reload, remaining == W - g
//      (floored at 0). So a chip told "W ms" is expired after W ticks, not W+1, not never.
// Strengthening for k-induction: RTL-HEARTBEAT-COUNTDOWN-EXACT is stated over two ghost registers (w = the window last loaded,
// g = ticks counted since, saturating at w). It is the whole state of the block written as a function of
// the ghosts, so it is 1-inductive and needs no other invariant.
module heartbeat_props(input clk, input rst, input hb_valid, input tick, input [31:0] window);
  wire [31:0] remaining; wire expired;
  heartbeat dut(.window(window), .tick(tick), .clk(clk), .rst(rst), .remaining(remaining), .expired(expired), .hb_valid(hb_valid));
  reg init = 1;
  always @(posedge clk) init <= 0;
  reg [31:0] w = 0, g = 0;                // ghosts: the window last loaded, ticks since then
  always @(posedge clk) begin
    if (rst) begin w <= 0; g <= 0; end
    else if (hb_valid) begin w <= window; g <= 0; end
    else if (tick && g < w) g <= g + 1;
  end
  always @(*) begin
    assume(!rst || init);
    if (!init) begin
      // RTL-HEARTBEAT-EXPIRED-AT-ZERO
      assert(expired == (remaining == 0));
      // RTL-HEARTBEAT-COUNTDOWN-EXACT (and the strengthening invariant)
      assert(g <= w);
      assert(remaining == w - g);
    end
  end
  always @(posedge clk) if (!init && !$past(init) && !$past(rst)) begin
    // RTL-HEARTBEAT-REMAINING-NEVER-RISES
    if (!$past(hb_valid)) assert(remaining <= $past(remaining));
    // RTL-HEARTBEAT-REMAINING-NEVER-RISES: it moves by at most one per tick, and only on a tick
    if (!$past(hb_valid) && !$past(tick)) assert(remaining == $past(remaining));
    if (!$past(hb_valid) && $past(tick) && $past(remaining) != 0) assert(remaining == $past(remaining) - 1);
    // RTL-HEARTBEAT-RELOADS-EXACT-WINDOW
    if ($past(hb_valid)) assert(remaining == $past(window));
    if (remaining > $past(remaining)) assert($past(hb_valid));
  end
endmodule
