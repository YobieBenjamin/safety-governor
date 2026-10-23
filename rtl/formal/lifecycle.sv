// L7-SPLICE: python -m rtl.formal pastes this text into module lifecycle (rtl/gen/lifecycle.v) just before endmodule,
// so the assertions see the block's own registers. The block's logic is not touched.
//
// Rules (docs/07-verification-plan.md section 3 lifecycle row, docs/04-specification.md LIFECYCLE register,
// govsim/fuses.py advance_lifecycle and debug_access):
//   L1 the state never goes down (TEST < PROVISIONED < PRODUCTION < DECOMMISSIONED), except that a reset puts the
//      register back to its reset value; the fuses are what survive a reset.
//   L2 the state changes only through load (up to the fuse value) or advance (up to advance_to); load wins.
//   L3 debug is granted only when the state is below PRODUCTION AND the fuses have been read since the last reset
//      AND what the fuses said was below PRODUCTION. This is the no-path-back-to-debug rule: a reset cannot open a
//      window in which a PRODUCTION chip answers JTAG before the fuse mirror is loaded (FINDINGS-a.md, F1).
//   L4 every debug request that is not granted is flagged refused; every advance that cannot move the state up is
//      flagged refused.
// Reset is left free here: it may hit in any cycle, because a warm reset or a reset glitch is exactly the attack
// on a lifecycle controller. Widths are the real ones (2 bits); nothing is parameterized down.
// Strengthening invariant for k-induction: I1 the block's loaded flag equals the shadow f_loaded (set by load,
// cleared by reset), I2 once loaded the state is at least the highest fuse value read since the reset, and I3
// before any load the shadow fuse value is still zero (without I3 induction starts from a state that remembers a
// fuse value nobody read).
  reg f_init = 1;
  reg f_loaded = 0;
  reg [1:0] f_fuse = 0;           // highest fuse value read since the last reset
  always @(posedge clk) begin
    f_init <= 0;
    if (rst) begin f_loaded <= 0; f_fuse <= 0; end
    else if (load) begin f_loaded <= 1; if (fuse_state > f_fuse) f_fuse <= fuse_state; end
  end
  always @(*) begin
    // L3
    if (debug_grant) assert(state < 2 && f_loaded && f_fuse < 2);
    assert(debug_grant == (debug_req && f_loaded && state < 2));
    // L4
    assert(debug_refused == (debug_req && !debug_grant));
    assert(advance_refused == (advance && advance_to <= state));
    // I1, I2
    assert(loaded == f_loaded);
    if (f_loaded) assert(state >= f_fuse);
    if (!f_loaded) assert(f_fuse == 0);
  end
  always @(posedge clk) if (!f_init && !$past(rst)) begin
    // L1
    assert(state >= $past(state));
    // L2
    if ($past(load)) assert(state == ($past(fuse_state) > $past(state) ? $past(fuse_state) : $past(state)));
    else if ($past(advance)) assert(state == ($past(advance_to) > $past(state) ? $past(advance_to) : $past(state)));
    else assert(state == $past(state));
  end
  always @(posedge clk) if (!f_init && $past(rst)) assert(state == 0 && !loaded);
