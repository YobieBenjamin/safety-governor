// L7, loop_io (rtl/governor_rtl/halt_loop.py): properties proven on the generated Verilog (rtl/gen/loop_io.v).
// Run: python -m rtl.formal. Spec: docs/07-verification-plan.md section 3 (halt_loop row), docs/02-safety-fabric.md
// (loss declared after two sense periods), docs/04 section 9. The rules:
//   L1 the pad follows the sequencer: loop_out_open == switch_open, combinationally, every cycle.
//   L2 a current loss is always seen: two consecutive samples with no current drive loop_lost, whatever happens
//      between samples. Stated against a ghost that counts consecutive low samples (saturating at 2), the spec's
//      own definition of the debounce, so this is "loop_lost exactly when the last two samples were both low".
//   L3 one noisy sample is not a loss (the same ghost: one low sample after a high one leaves loop_lost low).
//   L4 the loss is sticky until current is seen again: loop_lost falls only on a sample with current, never
//      between samples and never on a low sample.
// Strengthening for k-induction: the ghost equals the counter (count == lowrun); with it 1-step induction closes.
module loop_io_props(input clk, input rst, input switch_open, input sample, input loop_sense);
  wire loop_out_open, loop_lost; wire [1:0] count;
  loop_io dut(.switch_open(switch_open), .sample(sample), .clk(clk), .rst(rst), .loop_out_open(loop_out_open),
    .loop_lost(loop_lost), .count(count), .loop_sense(loop_sense));
  reg init = 1;
  always @(posedge clk) init <= 0;
  reg [1:0] lowrun = 0;                   // ghost: consecutive samples without current, saturating at 2
  always @(posedge clk) begin
    if (rst) lowrun <= 0;
    else if (sample) lowrun <= loop_sense ? 2'd0 : (lowrun == 2'd2 ? 2'd2 : lowrun + 2'd1);
  end
  always @(*) begin
    assume(!rst || init);
    if (!init) begin
      assert(loop_out_open == switch_open);                                    // L1
      assert(loop_lost == (lowrun == 2'd2));                                   // L2, L3
      assert(count == lowrun);                                                 // strengthening
    end
  end
  always @(posedge clk) if (!init && !$past(init) && !$past(rst)) begin
    // L4
    if ($past(loop_lost) && !loop_lost) assert($past(sample) && $past(loop_sense));
    // L2 directly: a low sample while already one low sample deep is a loss on the next cycle
    if ($past(sample) && !$past(loop_sense) && $past(count) >= 1) assert(loop_lost);
  end
endmodule
