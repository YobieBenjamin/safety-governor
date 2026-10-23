// L7-SPLICE: python -m rtl.formal pastes this text into module epoch_reg (rtl/gen/epoch_reg.v) just before endmodule.
// The block's logic is not touched.
//
// Rules (docs/07-verification-plan.md section 3 epoch_reg row; docs/04-specification.md EPOCH register, RO):
//   E1 the epoch changes only in the cycle after commit AND quorum_ok, and then it is exactly new_epoch.
//      So the host port (host_wr, host_data) has no effect on it, in any cycle, whatever the data.
//   E2 a host write is always flagged refused, and refused means exactly a host write.
//   E3 the tag the capability tables compare is the low 16 bits of the epoch, always.
//   E4 a reset puts the epoch at zero (no policy); the firmware must re-commit a verified image after boot.
// "Never goes backwards" cannot be stated on this block: the epoch is a digest, it has no order. The order lives in
// the policy version counter that the firmware checks before it strobes commit (govsim Fuses.bump_policy). This
// block will accept a re-commit of an old epoch with a quorum; see FINDINGS-a.md, F4.
// Widths are the real ones (256 bits); nothing is parameterized down. Reset is free. 1-step properties: no
// strengthening invariant needed.
  reg f_init = 1;
  always @(posedge clk) f_init <= 0;
  always @(*) begin
    assert(host_refused == host_wr);
    assert(epoch_tag == epoch[15:0]);
  end
  always @(posedge clk) if (!f_init) begin
    if ($past(rst)) assert(epoch == 256'd0);
    else if ($past(commit) && $past(quorum_ok)) assert(epoch == $past(new_epoch));
    else assert(epoch == $past(epoch));
  end
