// Formal properties for cap_table.
// P1: nothing passes unless a rule allowed it: a lookup is allowed only against an entry with matching
// (point, peer, dir), enough budget, not expired, and the current epoch tag. P4: the entry carries
// the epoch (edition) tag, a stale tag is refused. The budget never underflows, and an entry is
// inserted only with mac_ok.
reg f_init = 1'b1;
always @(posedge clk) f_init <= 1'b0;
always @* assume (!rst);

wire [7:0]   f_v  = {valid7, valid6, valid5, valid4, valid3, valid2, valid1, valid0};
wire [191:0] f_bud = {budget7, budget6, budget5, budget4, budget3, budget2, budget1, budget0};
wire [255:0] f_exp = {expiry7, expiry6, expiry5, expiry4, expiry3, expiry2, expiry1, expiry0};
wire [127:0] f_tag = {etag7, etag6, etag5, etag4, etag3, etag2, etag1, etag0};
wire [23:0]  f_pt  = {point7, point6, point5, point4, point3, point2, point1, point0};
wire [127:0] f_peer = {peer7, peer6, peer5, peer4, peer3, peer2, peer1, peer0};
wire [15:0]  f_dir = {dir7, dir6, dir5, dir4, dir3, dir2, dir1, dir0};

reg [7:0]   p_v;
reg [191:0] p_bud;
reg p_ins, p_mac_ok, p_clear_all;
always @(posedge clk) begin p_v <= f_v; p_bud <= f_bud; p_ins <= ins; p_mac_ok <= mac_ok; p_clear_all <= clear_all; end

wire [7:0] f_ok;
genvar gi;
generate for (gi = 0; gi < 8; gi = gi + 1) begin : g_entry
  assign f_ok[gi] = f_v[gi] && f_pt[gi*3 +: 3] == lk_point && f_peer[gi*16 +: 16] == lk_peer
                    && (f_dir[gi*2 +: 2] == lk_dir || f_dir[gi*2 +: 2] == 2'd2)
                    && f_exp[gi*32 +: 32] > now && f_tag[gi*16 +: 16] == epoch_tag
                    && f_bud[gi*24 +: 24] >= lk_bytes;
  always @(posedge clk) if (!f_init) begin
    c_no_underflow_budget_never_rises: assert (!p_v[gi] || f_bud[gi*24 +: 24] <= p_bud[gi*24 +: 24]);
    c_P1_entry_appears_only_by_insert: assert (!(!p_v[gi] && f_v[gi]) || (p_ins && p_mac_ok && !p_clear_all));
  end
end endgenerate

always @* begin
  c_P1_allow_needs_a_matching_entry: assert (!allow || (lk && (|f_ok)));
  c_P1_allow_reason_ok: assert (!allow || reason == 3'd0);
  c_P1_insert_needs_mac: assert (!ins_ok || (ins && mac_ok));
  c_P1_deny_has_a_reason: assert (allow || !lk || reason != 3'd0);
end
