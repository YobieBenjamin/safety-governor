// L7-SPLICE: python -m rtl.formal pastes this text into module mailbox (rtl/gen/mailbox.v) just before endmodule.
// The block's logic is not touched.
//
// Rules (docs/07-verification-plan.md section 3 mailbox row; docs/04-specification.md sections 2 and 3; govsim
// Governor._check_signed; the block docstring):
//   B1 only the doorbell starts anything: in IDLE without a doorbell nothing changes (state, status, every sequence
//      register, cmd_out) and nothing is dispatched. sig_done or sig_ok arriving unasked do nothing.
//   B2 at the doorbell the checks run in the spec's order and the first failure is the status: sequence not above
//      the key slot's last accepted (4), then epoch neither matching nor exempt (5), then a run-only command while not
//      running (6); otherwise busy (1) and the signature is requested (verify_req is exactly "in VERIFY").
//   B3 type binding: a command is dispatched exactly when, in VERIFY, the signature is done, good, AND the command
//      byte inside the signed payload equals the command asked for. A good signature over a different command gives
//      status 7 (S_WRONG_CMD) and does not consume the sequence number. A bad signature gives status 3.
//   B4 a dispatch carries a sequence number above the slot's last accepted one, a good epoch, and, for a run-only
//      command, a governor that was running when the doorbell rang. It then records the sequence for that slot
//      only, sets cmd_out to the command and status to ok (2).
//   B5 every key slot's last accepted sequence number never goes down and changes only on a dispatch for that slot.
// Assumption A1, an obligation on whoever drives this block: while the mailbox is in VERIFY, frame_seq, key_slot,
// cmd, epoch_match, epoch_exempt and needs_run hold the values they had at the doorbell. The block does not latch
// them; without A1 a frame can be checked with one sequence number and recorded with another (FINDINGS-a.md F9,
// reproduced by findings_a/mailbox_unlatched_frame.sv). `running` is NOT assumed stable: a halt during VERIFY is
// allowed, and B4 is stated about the doorbell cycle, which is what the RTL checks (F9 again).
// Reset: only in the first cycle. A reset zeroes every sequence register, so a mid-run reset re-opens every old
// sequence number (F8, reproduced by findings_a/mailbox_reset_replay.sv).
// Widths are the real ones: 8 key slots of 32-bit sequence numbers, 8-bit commands. Nothing is parameterized down.
// Strengthening invariants for k-induction: I1 in VERIFY the frame's sequence is above the slot's last accepted;
// I2 in VERIFY the epoch check passed; I3 in VERIFY a run-only command saw `running` at the doorbell (shadow
// f_runok); I4 in VERIFY the status is busy.
  reg f_init = 1;
  always @(posedge clk) f_init <= 0;
  wire [255:0] f_seq = {seq7, seq6, seq5, seq4, seq3, seq2, seq1, seq0};
  wire [31:0] f_cur = f_seq[32*key_slot +: 32];
  reg f_runok = 0;
  always @(posedge clk) if (!fsm_state && doorbell) f_runok <= running;
  always @(*) begin
    assume(rst == f_init);
    if (!f_init) begin
      assert(verify_req == fsm_state);
      // B3
      assert(dispatch == (fsm_state && sig_done && sig_ok && signed_cmd == cmd));
      // I1..I4, and B4 at the dispatch
      if (fsm_state) assert(frame_seq > f_cur && (epoch_match || epoch_exempt) && (!needs_run || f_runok) && status == 1);
      if (dispatch) assert(frame_seq > f_cur && (epoch_match || epoch_exempt) && (!needs_run || f_runok));
    end
  end
  // A1, written combinationally over last cycle's values: yosys registers a check inside always @(posedge clk), so
  // an assume written there constrains the cycle before, and the newest cycle of a trace would go unconstrained
  reg [31:0] q_seq; reg [2:0] q_slot; reg [7:0] q_cmd; reg q_em, q_ex, q_nr;
  always @(posedge clk) begin q_seq <= frame_seq; q_slot <= key_slot; q_cmd <= cmd; q_em <= epoch_match; q_ex <= epoch_exempt; q_nr <= needs_run; end
  always @(*) if (!f_init && fsm_state)
    assume(frame_seq == q_seq && key_slot == q_slot && cmd == q_cmd && epoch_match == q_em && epoch_exempt == q_ex && needs_run == q_nr);
  integer f_i; reg [255:0] p_seq;
  always @(posedge clk) p_seq <= f_seq;
  always @(posedge clk) if (!f_init && !$past(f_init)) begin
    // B5
    for (f_i = 0; f_i < 8; f_i = f_i + 1) begin
      assert(f_seq[32*f_i +: 32] >= p_seq[32*f_i +: 32]);
      if (!($past(dispatch) && $past(key_slot) == f_i)) assert(f_seq[32*f_i +: 32] == p_seq[32*f_i +: 32]);
      else assert(f_seq[32*f_i +: 32] == $past(frame_seq));
    end
    if (!$past(dispatch)) assert(cmd_out == $past(cmd_out));
    if (!$past(fsm_state)) begin
      if (!$past(doorbell)) begin
        // B1
        assert(!fsm_state && status == $past(status));
      end else if (!($past(frame_seq) > $past(f_cur))) assert(!fsm_state && status == 4);      // B2
      else if (!($past(epoch_match) || $past(epoch_exempt))) assert(!fsm_state && status == 5);
      else if ($past(needs_run) && !$past(running)) assert(!fsm_state && status == 6);
      else assert(fsm_state && status == 1);
    end else begin
      if (!$past(sig_done)) assert(fsm_state && status == 1);
      else if ($past(sig_ok) && $past(signed_cmd) == $past(cmd)) assert(!fsm_state && status == 2 && cmd_out == $past(cmd));  // B3, B4
      else if ($past(sig_ok)) assert(!fsm_state && status == 7);
      else assert(!fsm_state && status == 3);
    end
  end
