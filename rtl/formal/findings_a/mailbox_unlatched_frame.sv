// L7-SPLICE block: mailbox. FINDINGS-a.md RTL-MAILBOX-FRAME-NOT-HELD. Expected to FAIL by assertion. Rule: a dispatched frame carries a (WAVE-FORMAL-PROOFS-ON-VERILOG (old: L7))
// sequence number above the slot's last accepted one. Reset only at the start. No assumption that the frame fields
// hold still while the signature is being checked: the block reads frame_seq at the doorbell for the check and again
// at sig_done for the record, so a frame that changes in between is recorded with a sequence that was never checked.
  reg f_init = 1;
  always @(posedge clk) f_init <= 0;
  wire [255:0] f_seq = {seq7, seq6, seq5, seq4, seq3, seq2, seq1, seq0};
  always @(*) begin
    assume(rst == f_init);
    if (!f_init && dispatch) assert(frame_seq > f_seq[32*key_slot +: 32]);
  end
