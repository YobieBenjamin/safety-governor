// WAVE-FORMAL-PROOFS-ON-VERILOG, governor_core: a reachability witness for FINDINGS-b.md. From power-on, with loop current present and one
// valid heartbeat that is then never renewed, the small build (blocks_b.SMALL) reaches SAFE with the slot powered
// off and its loop pad still closed. The solver must find the trace; python -m rtl.formal prints its length.
module governor_core_cover_props(input clk, input rst);
  //@@DUT@@
  reg init = 1;
  always @(posedge clk) init <= 0;
  always @(*) begin
    assume(!rst);
    // a quiet chip: no tamper, no command, no clear, no local trip; loop current always present
    assume(!halt_tamper && !halt_cmd_halt && !halt_cmd_throttle && !halt_local_trip && !halt_clear && loop_sense);
    assume(!mono_load_hwm);
    if (!init) cover(halt_state == 4 && halt_cause == 2 && !pwr_en && !loop_out_open);
  end
endmodule
