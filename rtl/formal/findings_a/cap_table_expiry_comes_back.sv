// L7-SPLICE block: cap_table. FINDINGS-a.md F7. Expected to FAIL by assertion. Rule: once a capability has expired
// it never allows again. Expiry is checked only at lookup against the `now` input; an entry nobody looked up while it
// was expired stays valid, and when `now` goes back (governor_core wires now to the low 32 bits of the microsecond
// counter, which wrap every 71.6 minutes) it allows again.
  (* anyconst *) reg [2:0] f_w;
  wire [7:0]   f_val  = {valid7, valid6, valid5, valid4, valid3, valid2, valid1, valid0};
  wire [255:0] f_exp  = {expiry7, expiry6, expiry5, expiry4, expiry3, expiry2, expiry1, expiry0};
  reg f_dead = 0;           // slot W has been valid at a time at or past its expiry
  always @(posedge clk) begin
    if (ins_ok && !f_val[f_w]) f_dead <= 0;                       // refilled (the first free slot may be W)
    if (f_val[f_w] && f_exp[32*f_w +: 32] <= now) f_dead <= 1;
  end
  always @(*) if (allow && hit[2:0] == f_w && f_dead) assert(0);
