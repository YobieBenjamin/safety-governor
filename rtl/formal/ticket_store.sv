// L7-SPLICE: python -m rtl.formal pastes this text into module ticket_store (rtl/gen/ticket_store.v) just before (WAVE-FORMAL-PROOFS-ON-VERILOG (old: L7))
// endmodule. The block's logic is not touched.
//
// Rules (docs/07-verification-plan.md section 3 ticket_store row; the block docstring; govsim/endpoints.py
// ActionEndpoint.consumed, the functional model of the used-ticket set):
//   RTL-TICKET-SINGLE-USE single use: once an id has been burned it is seen forever after and can never be burned again, so the
//      endpoint, which admits only on `burned`, admits each ticket id at most once. Checked for an arbitrary id W
//      the solver picks (anyconst), so it holds for every id.
//   RTL-TICKET-SEEN-AND-FULL-EXACT seen is exactly "some valid slot holds id_in"; full is exactly "every slot is valid".
//   RTL-TICKET-BURN-WHEN-UNSEEN burn succeeds (burned) exactly when the id is not seen and the store is not full. Full means refuse: the
//      store never evicts a burned id to make room.
//   RTL-TICKET-BURN-FIRST-FREE-SLOT a successful burn writes the id into the first free slot and changes nothing else; no other cycle changes
//      the store. A valid slot is never cleared and its id never changes.
// No grant-without-authorization rule applies here: the ticket's signature is the endpoint's check, before burn.
// No expiry rule applies here either: validity windows are on the endpoint's clock (docs/04 section 1).
// Reset: only in the first cycle. The block's registers are a volatile stand-in for the NVM used-ticket set, and a
// reset empties them; a reset in mid-run lets a used ticket in again. That is FINDINGS-a.md RTL-RESET-EMPTIES-TICKET-STORE, reproduced by
// rtl/formal/findings_a/ticket_store_reset_replay.sv, not hidden.
// Widths are the real ones: 8 entries of 32-bit ids. Nothing is parameterized down.
// Strengthening invariant for k-induction: RTL-TICKET-BURNED-ID-HELD if W has been burned, some valid slot holds W.
  reg f_init = 1;
  always @(posedge clk) f_init <= 0;
  (* anyconst *) reg [31:0] f_w;
  reg f_wburned = 0;
  always @(posedge clk) if (!rst && burned && id_in == f_w) f_wburned <= 1;
  wire [7:0] f_v = {v7, v6, v5, v4, v3, v2, v1, v0};
  wire [255:0] f_ids = {id7, id6, id5, id4, id3, id2, id1, id0};
  reg f_seen, f_holds_w; reg [3:0] f_free; integer f_i, f_j;
  always @(*) begin
    f_seen = 0; f_holds_w = 0; f_free = 8;
    for (f_i = 7; f_i >= 0; f_i = f_i - 1) begin
      if (f_v[f_i] && f_ids[32*f_i +: 32] == id_in) f_seen = 1;
      if (f_v[f_i] && f_ids[32*f_i +: 32] == f_w) f_holds_w = 1;
      if (!f_v[f_i]) f_free = f_i;
    end
  end
  always @(*) begin
    assume(rst == f_init);
    if (!f_init) begin
      // RTL-TICKET-SEEN-AND-FULL-EXACT, RTL-TICKET-BURN-WHEN-UNSEEN
      assert(seen == f_seen);
      assert(full == (f_v == 8'hFF));
      assert(burned == (burn && !f_seen && f_v != 8'hFF));
      // RTL-TICKET-SINGLE-USE and its invariant RTL-TICKET-BURNED-ID-HELD
      if (f_wburned) assert(f_holds_w);
      if (f_wburned && id_in == f_w) assert(seen && !burned);
    end
  end
  reg [3:0] f_pfree; reg [7:0] f_pv; reg [255:0] f_pids; reg [31:0] f_pid; reg f_pburned;
  always @(posedge clk) begin f_pfree <= f_free; f_pv <= f_v; f_pids <= f_ids; f_pid <= id_in; f_pburned <= burned; end
  always @(posedge clk) if (!f_init && !$past(f_init)) begin
    // RTL-TICKET-BURN-FIRST-FREE-SLOT
    for (f_j = 0; f_j < 8; f_j = f_j + 1) begin
      if (f_pburned && f_pfree == f_j) assert(f_v[f_j] && f_ids[32*f_j +: 32] == f_pid);
      else begin
        assert(f_v[f_j] == f_pv[f_j]);
        if (f_pv[f_j]) assert(f_ids[32*f_j +: 32] == f_pids[32*f_j +: 32]);
      end
    end
  end
