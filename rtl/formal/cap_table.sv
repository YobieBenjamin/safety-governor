// L7-SPLICE: python -m rtl.formal pastes this text into module cap_table (rtl/gen/cap_table.v) just before endmodule.
// The block's logic is not touched.
//
// Rules (docs/07-verification-plan.md section 3 cap_table row; docs/04-specification.md section 5, Capability; the
// block docstring):
//   C1 a lookup allows only through the FIRST valid entry whose point and peer match and whose direction matches
//      (or is "both"), and only if that entry has not expired (expiry > now), carries the current epoch tag, and has
//      at least the bytes asked for. The reason code names the first check that failed, in that order. No lookup,
//      no allow.
//   C2 no grant without authorization: an entry becomes valid only through an insert with mac_ok, into the first
//      free slot, and never in a clear_all cycle. ins_ok and ins_full say exactly that.
//   C3 a valid entry's point, peer, direction, expiry and epoch tag never change; its budget only goes down, and
//      only by the bytes of an allowed lookup through it. An expired hit drops the entry. clear_all drops them all.
//      Nothing else changes the table.
//   C4 the budget is spent at most once: for an arbitrary slot W (anyconst), the bytes allowed through W since it
//      was filled plus what is left in W always equal the budget it was filled with. So the total ever allowed
//      through one capability never exceeds its grant, and the budget never underflows.
// Disagreements, recorded in FINDINGS-a.md: the spec says a lookup "refuses at zero" (and the verification plan says
// "budget > 0"); this RTL allows a zero-byte lookup on an exhausted entry (F6, reproduced by findings_a/). An entry
// past its expiry stays valid until a lookup touches it, and `now` is a free input, so a `now` that wraps can bring
// an expired entry back (F7).
// Reset is free (any cycle): a reset empties the table, which closes every port, the safe direction.
// Widths are the real Amaranth defaults the prototype core instantiates: 8 entries, 3-bit point, 16-bit peer,
// 24-bit budget, 32-bit expiry and time, 16-bit tag. Nothing is parameterized down.
// Strengthening invariant for k-induction: I1 for slot W, while W is valid, spent + budget == granted (that is C4
// itself; it is inductive given C3).
  reg f_init = 1;
  always @(posedge clk) f_init <= 0;
  wire [7:0]   f_val  = {valid7, valid6, valid5, valid4, valid3, valid2, valid1, valid0};
  wire [23:0]  f_pt   = {point7, point6, point5, point4, point3, point2, point1, point0};
  wire [127:0] f_peer = {peer7, peer6, peer5, peer4, peer3, peer2, peer1, peer0};
  wire [15:0]  f_dir  = {dir7, dir6, dir5, dir4, dir3, dir2, dir1, dir0};
  wire [191:0] f_bud  = {budget7, budget6, budget5, budget4, budget3, budget2, budget1, budget0};
  wire [255:0] f_exp  = {expiry7, expiry6, expiry5, expiry4, expiry3, expiry2, expiry1, expiry0};
  wire [127:0] f_tag  = {etag7, etag6, etag5, etag4, etag3, etag2, etag1, etag0};
  reg [3:0] f_hit, f_free; integer f_i, f_j;
  always @(*) begin
    f_hit = 8; f_free = 8;
    for (f_i = 7; f_i >= 0; f_i = f_i - 1) begin
      if (f_val[f_i] && f_pt[3*f_i +: 3] == lk_point && f_peer[16*f_i +: 16] == lk_peer
          && (f_dir[2*f_i +: 2] == lk_dir || f_dir[2*f_i +: 2] == 2)) f_hit = f_i;
      if (!f_val[f_i]) f_free = f_i;
    end
  end
  wire [2:0]  f_h = f_hit[2:0];
  wire f_any = f_hit != 8;
  wire f_expired = f_any && f_exp[32*f_h +: 32] <= now;
  wire f_stale = f_any && !f_expired && f_tag[16*f_h +: 16] != epoch_tag;
  wire f_short = f_any && !f_expired && !f_stale && f_bud[24*f_h +: 24] < lk_bytes;
  wire f_allow = lk && f_any && !f_expired && !f_stale && !f_short;
  wire f_insok = ins && mac_ok && f_free != 8 && !clear_all;
  // C4 shadow for slot W
  (* anyconst *) reg [2:0] f_w;
  reg [23:0] f_granted = 0; reg [24:0] f_spent = 0;
  always @(posedge clk) begin
    if (f_insok && f_free == f_w) begin f_granted <= ins_budget; f_spent <= 0; end
    else if (f_allow && f_h == f_w) f_spent <= f_spent + lk_bytes;
  end
  always @(*) if (!f_init) begin
    // C1
    if (!lk) assert(!allow);
    else begin
      assert(allow == f_allow);
      if (!f_any) assert(reason == 1);
      else if (f_expired) assert(reason == 2);
      else if (f_stale) assert(reason == 3);
      else if (f_short) assert(reason == 4);
      else assert(reason == 0);
    end
    if (allow) assert(f_exp[32*f_h +: 32] > now && f_tag[16*f_h +: 16] == epoch_tag && f_bud[24*f_h +: 24] >= lk_bytes);
    // C2
    assert(ins_ok == f_insok);
    assert(ins_full == (ins && f_free == 8));
    // C4 / I1
    if (f_val[f_w]) assert({1'b0, f_bud[24*f_w +: 24]} + f_spent == {1'b0, f_granted});
  end
  // C2, C3: the next table, entry by entry, from the previous one
  reg [7:0] p_val; reg [23:0] p_pt; reg [127:0] p_peer; reg [15:0] p_dir; reg [191:0] p_bud; reg [255:0] p_exp; reg [127:0] p_tag;
  reg p_insok, p_allow, p_expdrop, p_clear, p_rst; reg [3:0] p_free; reg [2:0] p_h;
  reg [2:0] p_ipt; reg [15:0] p_ipeer; reg [1:0] p_idir; reg [23:0] p_ibud, p_bytes; reg [31:0] p_iexp; reg [15:0] p_itag;
  always @(posedge clk) begin
    p_val <= f_val; p_pt <= f_pt; p_peer <= f_peer; p_dir <= f_dir; p_bud <= f_bud; p_exp <= f_exp; p_tag <= f_tag;
    p_insok <= f_insok; p_allow <= f_allow; p_expdrop <= lk && f_expired; p_clear <= clear_all; p_rst <= rst;
    p_free <= f_free; p_h <= f_h; p_bytes <= lk_bytes;
    p_ipt <= ins_point; p_ipeer <= ins_peer; p_idir <= ins_dir; p_ibud <= ins_budget; p_iexp <= ins_expiry; p_itag <= ins_epoch_tag;
  end
  always @(posedge clk) if (!f_init) begin
    for (f_j = 0; f_j < 8; f_j = f_j + 1) begin
      if (p_rst || p_clear) assert(!f_val[f_j]);
      else if (p_insok && p_free == f_j) begin
        assert(f_val[f_j] && f_pt[3*f_j +: 3] == p_ipt && f_peer[16*f_j +: 16] == p_ipeer && f_dir[2*f_j +: 2] == p_idir
               && f_bud[24*f_j +: 24] == p_ibud && f_exp[32*f_j +: 32] == p_iexp && f_tag[16*f_j +: 16] == p_itag);
      end else begin
        // C2: nothing but an authorized insert makes an entry valid
        if (!p_val[f_j]) assert(!f_val[f_j]);
        else begin
          assert(f_pt[3*f_j +: 3] == p_pt[3*f_j +: 3] && f_peer[16*f_j +: 16] == p_peer[16*f_j +: 16]
                 && f_dir[2*f_j +: 2] == p_dir[2*f_j +: 2] && f_exp[32*f_j +: 32] == p_exp[32*f_j +: 32]
                 && f_tag[16*f_j +: 16] == p_tag[16*f_j +: 16]);
          if (p_expdrop && p_h == f_j) assert(!f_val[f_j]);
          else assert(f_val[f_j]);
          if (p_allow && p_h == f_j) assert(f_bud[24*f_j +: 24] == p_bud[24*f_j +: 24] - p_bytes);
          else assert(f_bud[24*f_j +: 24] == p_bud[24*f_j +: 24]);
        end
      end
    end
  end
