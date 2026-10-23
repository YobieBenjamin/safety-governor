// L7-SPLICE block: epoch_reg. FINDINGS-a.md F4. Expected to FAIL by assertion. Rule (the brief's reading of
// anti-rollback): once the epoch has moved on from a value, it never goes back to it. The register has no notion of
// order: any commit with a quorum is taken, including a re-commit of an earlier, still validly signed image.
  reg f_init = 1;
  always @(posedge clk) f_init <= 0;
  (* anyconst *) reg [255:0] f_old;
  reg f_was = 0, f_left = 0;
  always @(posedge clk) begin
    if (epoch == f_old) f_was <= 1;
    if (f_was && epoch != f_old) f_left <= 1;
  end
  always @(*) begin
    assume(rst == f_init);
    if (!f_init && f_left) assert(epoch != f_old);
  end
