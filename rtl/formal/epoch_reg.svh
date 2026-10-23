// Formal properties for epoch_reg, injected before the final endmodule of rtl/gen/epoch_reg.v.
// Numbers are the P-numbers of proofs/core_invariants.py (P9: an edition change needs a quorum;
// P10: whatever the image claims, only the verifier's quorum_ok counts).
reg f_init = 1'b1;
always @(posedge clk) f_init <= 1'b0;
always @* assume (!rst);

reg [255:0] p_epoch, p_new_epoch;
reg p_commit, p_quorum_ok, p_host_wr;
always @(posedge clk) begin
  p_epoch <= epoch; p_new_epoch <= new_epoch;
  p_commit <= commit; p_quorum_ok <= quorum_ok; p_host_wr <= host_wr;
end

always @(posedge clk) if (!f_init) begin
  e_P9_change_needs_commit_and_quorum: assert (epoch == p_epoch || (p_commit && p_quorum_ok));
  e_P9_commit_with_quorum_loads:       assert (!(p_commit && p_quorum_ok) || epoch == p_new_epoch);
  e_P10_commit_without_quorum_no_op:   assert (!(p_commit && !p_quorum_ok) || epoch == p_epoch);
  e_P9_host_write_has_no_effect:       assert (!(p_host_wr && !(p_commit && p_quorum_ok)) || epoch == p_epoch);
end
always @* begin
  e_tag_is_low_16_bits: assert (epoch_tag == epoch[15:0]);
  e_host_write_is_flagged: assert (host_refused == host_wr);
end
