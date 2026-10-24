// Registered name: WAVE-FORMAL-PROOFS-ON-VERILOG (old ID L7 is kept because code matches on it)
// L7-SPLICE block: ticket_store. FINDINGS-a.md RTL-RESET-EMPTIES-TICKET-STORE. Expected to FAIL by assertion: python -m rtl.formal reports it
// "reproduced". Rule: a burned ticket id is never burned (admitted) again, now with reset allowed in any cycle.
// The block's store is volatile and a reset empties it, so after a reset the same id burns a second time.
  (* anyconst *) reg [31:0] f_w;
  reg f_wburned = 0;
  always @(posedge clk) if (!rst && burned && id_in == f_w) f_wburned <= 1;   // the shadow survives the reset, as NVM would
  always @(*) if (f_wburned && id_in == f_w) assert(!burned);
