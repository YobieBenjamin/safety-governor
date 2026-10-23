// Formal properties for mailbox.
// P3: no replay, the sequence must be above the slot's last accepted one. P10/P12: a command is
// dispatched only on a verified signature over that very command (a signature over a heartbeat
// never dispatches CLEAR). Commit point: the check order, and a wrong-command frame consumes
// nothing.
//
// Interface assumption (default task): while the mailbox is in VERIFY, the frame fields it checked at the
// doorbell are held (the RTL does not latch them). Tasks that drop an assumption are expected to
// fail and document the gap:
//   -D NOLATCH  frame_seq/key_slot/cmd may change during VERIFY: a dispatch with a stale sequence
//   -D MIDHALT  `running` may fall during VERIFY: a needs_run command dispatches while not running
reg f_init = 1'b1;
always @(posedge clk) f_init <= 1'b0;
always @* assume (!rst);

wire [255:0] lseq = {seq7, seq6, seq5, seq4, seq3, seq2, seq1, seq0};
wire [31:0] cur_last = lseq[key_slot*32 +: 32];
wire seq_ok_now = frame_seq > cur_last;

// what the frame looked like in the last cycle outside VERIFY, that is, at the doorbell
reg [31:0] c_seq; reg [2:0] c_slot; reg [7:0] c_cmd; reg c_epm, c_epe;
always @(posedge clk) if (!verify_req) begin
  c_seq <= frame_seq; c_slot <= key_slot; c_cmd <= cmd; c_epm <= epoch_match; c_epe <= epoch_exempt;
end
`ifndef NOLATCH
always @* if (verify_req) assume (frame_seq == c_seq && key_slot == c_slot && cmd == c_cmd
                                  && epoch_match == c_epm && epoch_exempt == c_epe);
`endif

reg p_fsm, p_doorbell, p_sig_done, p_sig_ok, p_dispatch, p_seq_ok, p_epm, p_epe, p_nr, p_run;
reg [31:0] p_seq; reg [2:0] p_slot; reg [7:0] p_cmd, p_signed; reg [255:0] p_lseq;
always @(posedge clk) begin
  p_fsm <= fsm_state; p_doorbell <= doorbell; p_sig_done <= sig_done; p_sig_ok <= sig_ok; p_dispatch <= dispatch;
  p_seq_ok <= seq_ok_now; p_epm <= epoch_match; p_epe <= epoch_exempt; p_nr <= needs_run; p_run <= running;
  p_seq <= frame_seq; p_slot <= key_slot; p_cmd <= cmd; p_signed <= signed_cmd; p_lseq <= lseq;
end

`ifdef NOLATCH
always @* b_P3_dispatch_sequence_above_last: assert (!dispatch || seq_ok_now);
`elsif MIDHALT
always @* b_dispatch_needs_run_when_required: assert (!dispatch || !needs_run || running);
`else
// invariant that makes the induction go through: a frame in VERIFY passed the doorbell checks
always @* b_inv_verify_passed_doorbell: assert (!fsm_state || (c_seq > lseq[c_slot*32 +: 32] && (c_epm || c_epe)));

always @* begin
  b_P12_dispatch_only_on_signed_same_command: assert (!dispatch || (verify_req && sig_done && sig_ok && signed_cmd == cmd));
  b_P3_dispatch_sequence_above_last:          assert (!dispatch || seq_ok_now);
  b_dispatch_epoch_matches_or_exempt:         assert (!dispatch || epoch_match || epoch_exempt);
  b_no_dispatch_outside_verify:               assert (!dispatch || fsm_state);
end

genvar gi;
generate for (gi = 0; gi < 8; gi = gi + 1) begin : g_slot
  always @(posedge clk) if (!f_init)
    b_P3_last_seq_only_rises: assert (lseq[gi*32 +: 32] >= p_lseq[gi*32 +: 32]);
end endgenerate

always @(posedge clk) if (!f_init) begin
  b_last_seq_changes_only_on_dispatch: assert (lseq == p_lseq || p_dispatch);
  b_dispatch_consumes_and_reports: assert (!p_dispatch || (status == 3'd2 && cmd_out == p_signed && cmd_out == p_cmd
                                                          && lseq[p_slot*32 +: 32] == p_seq));
  // the checks run in order and the first failure is what status reports
  b_order_sequence_first: assert (!(!p_fsm && p_doorbell && !p_seq_ok) || (status == 3'd4 && !fsm_state));
  b_order_epoch_second:   assert (!(!p_fsm && p_doorbell && p_seq_ok && !(p_epm || p_epe)) || (status == 3'd5 && !fsm_state));
  b_order_running_third:  assert (!(!p_fsm && p_doorbell && p_seq_ok && (p_epm || p_epe) && p_nr && !p_run) || (status == 3'd6 && !fsm_state));
  b_order_then_verify:    assert (!(!p_fsm && p_doorbell && p_seq_ok && (p_epm || p_epe) && !(p_nr && !p_run)) || (status == 3'd1 && fsm_state));
  b_wrong_command_consumes_nothing: assert (!(p_fsm && p_sig_done && p_sig_ok && p_signed != p_cmd) ||
                                            (status == 3'd7 && lseq == p_lseq && !fsm_state));
  b_bad_signature_consumes_nothing: assert (!(p_fsm && p_sig_done && !p_sig_ok) || (status == 3'd3 && lseq == p_lseq && !fsm_state));
end
`endif
