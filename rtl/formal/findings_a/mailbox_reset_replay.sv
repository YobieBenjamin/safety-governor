// L7-SPLICE block: mailbox. FINDINGS-a.md RTL-RESET-ZEROES-MAILBOX-SEQUENCES. Expected to FAIL by assertion. Rule: a dispatched frame's sequence (WAVE-FORMAL-PROOFS-ON-VERILOG (old: L7))
// number is above every sequence number ever accepted for that key slot, with reset allowed in any cycle. The
// sequence registers reset to zero and there is no port to restore them, so an old signed frame replays after reset.
  reg [63:0] f_hi = 0;       // highest sequence ever accepted in key slot 0; survives reset, as NVM would
  // no epoch advance here (adversarial audit 3 added that reset on purpose; frames of an old epoch fail epoch_match):
  // this finding is about a chip reset alone
  always @(*) assume(!epoch_advanced);
  always @(posedge clk) if (!rst && dispatch && key_slot == 0 && frame_seq > f_hi) f_hi <= frame_seq;
  reg f_any = 0;
  always @(posedge clk) if (!rst && dispatch && key_slot == 0) f_any <= 1;
  always @(*) if (dispatch && key_slot == 0 && f_any) assert(frame_seq > f_hi);
