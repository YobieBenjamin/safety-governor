// L7, governor_core: design FACTS, not safety rules. They record what the RTL does about the open question in
// FINDINGS-b.md (a lost heartbeat climbs to SAFE on one chip without opening the loop to its neighbours), proven
// by k-induction on the same small build as governor_core.sv. If someone changes the design on purpose, these are
// expected to fail and FINDINGS-b.md must be updated with them. Run: python -m rtl.formal.
//   F-a a local cause (heartbeat loss, local trip, throttle command) never opens this chip's loop switch, on any
//       rung, SAFE included: the neighbours keep their loop current and keep running.
// The old F-b ("a signed HALT to a chip already in SAFE does not open the loop") was removed on 23 October 2026,
// when Yobie decided a HALT opens the loop on every rung. Its replacement is a proven rule, not a fact: G3 in
// governor_core.sv and the H rules in halt_seq.sv.
module governor_core_facts_props(input clk, input rst);
  //@@DUT@@
  reg init = 1;
  always @(posedge clk) init <= 0;
  always @(*) begin
    assume(!rst || init);
    if (!init) begin
      if (halt_cause == 2) assert(!halt_switch_open && !loop_out_open);          // F-a
      // strengthening, the sequencer's own invariants
      assert(halt_state <= 4); assert(halt_cause <= 4);
      if (halt_state == 2) assert(halt_cause == 2);
      if (halt_state == 1) assert(halt_cause == 0 && !halt_switch_open);
      if (halt_state == 0) assert(halt_cause == 0);
    end
  end
endmodule
