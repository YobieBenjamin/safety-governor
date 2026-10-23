// Formal properties for ticket_store. P3: no replay, a burned id is never admitted again.
reg f_init = 1'b1;
always @(posedge clk) f_init <= 1'b0;
always @* assume (!rst);

wire [7:0]   f_v  = {v7, v6, v5, v4, v3, v2, v1, v0};
wire [255:0] f_id = {id7, id6, id5, id4, id3, id2, id1, id0};
reg  [7:0]   p_v;
reg  [255:0] p_id;
always @(posedge clk) begin p_v <= f_v; p_id <= f_id; end

// a witness id chosen by the solver and held fixed: the claim is for every id
(* anyconst *) wire [31:0] w_id;
reg w_burned = 1'b0;
always @(posedge clk) if (burned && id_in == w_id) w_burned <= 1'b1;

wire [7:0] w_hit;
genvar gi, gj;
generate for (gi = 0; gi < 8; gi = gi + 1) begin : g_entry
  assign w_hit[gi] = f_v[gi] && f_id[gi*32 +: 32] == w_id;
  always @(posedge clk) if (!f_init) begin
    t_P3_valid_never_clears: assert (!p_v[gi] || f_v[gi]);
    t_P3_burned_id_never_changes: assert (!p_v[gi] || f_id[gi*32 +: 32] == p_id[gi*32 +: 32]);
  end
  for (gj = gi + 1; gj < 8; gj = gj + 1) begin : g_pair
    always @* t_P3_no_duplicate_ids: assert (!(f_v[gi] && f_v[gj]) || f_id[gi*32 +: 32] != f_id[gj*32 +: 32]);
  end
end endgenerate

always @* begin
  t_P3_burn_only_of_unseen_id: assert (!burned || !seen);
  t_P3_full_refuses_burn:      assert (!(burned && full));
  t_P3_full_means_all_valid:   assert (full == (&f_v));
  t_P3_burned_id_is_seen:      assert (!(w_burned && id_in == w_id) || seen);
  t_P3_burned_id_is_stored:    assert (!w_burned || (|w_hit));
  t_P3_no_second_burn:         assert (!(w_burned && id_in == w_id) || !burned);
end
