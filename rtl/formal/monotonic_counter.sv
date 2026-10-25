// L7-SPLICE: python -m rtl.formal pastes this text into module monotonic_counter (rtl/gen/monotonic_counter.v) just (WAVE-FORMAL-PROOFS-ON-VERILOG (old: L7))
// before endmodule. The block's logic is not touched.
//
// Rules (docs/07-verification-plan.md section 3 monotonic row; docs/04-specification.md section 1 "never decremented,
// persisted"; MONO_LO/MONO_HI read-only):
//   RTL-COUNTER-NEVER-DECREASES between resets the value never decreases. Not even at the top: it saturates (FINDINGS-a.md, RTL-COUNTER-WRAPPED-TO-ZERO).
//   RTL-COUNTER-MOVES-BY-LOAD-INCREMENT the value moves only by load_hwm (up to hwm, never down) or by inc (exactly one step); load_hwm wins.
//      There is no other way in: dec_req, and anything else, leaves the value alone.
//   RTL-COUNTER-DECREMENT-FLAGGED a decrement request is always flagged refused, and refused means exactly that.
//   RTL-COUNTER-AT-LEAST-FUSE-MARK after a load the value is at least the fuse high-water mark, so a power loss cannot take the counter below
//      the last mark the firmware burned (it can take it back TO that mark; that is the design: see RTL-COUNTER-ROLLBACK-ACROSS-RESET).
// Reset is free: it may hit in any cycle. A reset puts the register at zero; RTL-COUNTER-AT-LEAST-FUSE-MARK is what makes that safe, provided
// the boot code strobes load_hwm before anything reads the counter (an obligation on the firmware, RTL-COUNTER-ROLLBACK-ACROSS-RESET).
// Widths are the real ones (64 bits); nothing is parameterized down. No strengthening invariant is needed: every
// property is about one step, so 1-induction already closes it.
  reg f_init = 1;
  always @(posedge clk) f_init <= 0;
  always @(*) assert(refused == dec_req);
  always @(posedge clk) if (!f_init && !$past(rst)) begin
    assert(value >= $past(value));
    if ($past(load_hwm)) begin
      assert(value == ($past(hwm) > $past(value) ? $past(hwm) : $past(value)));
      assert(value >= $past(hwm));
    end else if ($past(inc)) assert(value == ($past(value) == 64'hFFFF_FFFF_FFFF_FFFF ? $past(value) : $past(value) + 64'd1));
    else assert(value == $past(value));
  end
  always @(posedge clk) if (!f_init && $past(rst)) assert(value == 0);
