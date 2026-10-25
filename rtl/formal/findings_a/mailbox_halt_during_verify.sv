// L7-SPLICE block: mailbox. FINDINGS-a.md RTL-MAILBOX-FRAME-NOT-HELD (second half). Expected to FAIL by assertion. Rule: a run-only command (WAVE-FORMAL-PROOFS-ON-VERILOG (old: L7))
// is never dispatched while the governor is not running. Even with the frame fields held still, `running` is sampled
// only at the doorbell, so a halt that lands while the signature is being checked does not stop the dispatch.
  reg f_init = 1;
  always @(posedge clk) f_init <= 0;
  always @(*) begin
    assume(rst == f_init);
    if (!f_init && dispatch) assert(!needs_run || running);
  end
  // RTL-MAILBOX-FRAME-HELD-STILL, written combinationally over last cycle's values: yosys registers a check inside always @(posedge clk), so
  // an assume written there constrains the cycle before, and the newest cycle of a trace would go unconstrained
  reg [31:0] q_seq; reg [2:0] q_slot; reg [7:0] q_cmd; reg q_em, q_ex, q_nr;
  always @(posedge clk) begin q_seq <= frame_seq; q_slot <= key_slot; q_cmd <= cmd; q_em <= epoch_match; q_ex <= epoch_exempt; q_nr <= needs_run; end
  always @(*) if (!f_init && fsm_state)
    assume(frame_seq == q_seq && key_slot == q_slot && cmd == q_cmd && epoch_match == q_em && epoch_exempt == q_ex && needs_run == q_nr);
