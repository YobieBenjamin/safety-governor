// L7-SPLICE block: monotonic_counter. FINDINGS-a.md RTL-COUNTER-ROLLBACK-ACROSS-RESET. Expected to FAIL by assertion. Rule from docs/04 section 1 (WAVE-FORMAL-PROOFS-ON-VERILOG (old: L7))
// ("never decremented, persisted"), read across a power cycle: after a reset and the boot-time load, the counter is
// at least where it was before the reset. It is only at least the fuse high-water mark, which the firmware burns
// now and then, so every tick since the last burn is lost. The fuse value is held constant here (no burn in between).
  reg f_init = 1;
  always @(posedge clk) f_init <= 0;
  reg [63:0] f_top = 0;     // highest value seen; survives reset
  reg f_rst = 0, f_after = 0;   // a reset has happened; and the high-water mark has been loaded since
  always @(posedge clk) begin
    if (value > f_top) f_top <= value;
    if (rst) f_rst <= 1;
    if (!rst && f_rst && load_hwm) f_after <= 1;
  end
  reg [63:0] q_hwm;
  always @(posedge clk) q_hwm <= hwm;
  always @(*) if (!f_init) assume(hwm == q_hwm);   // combinational: a clocked assume lags a cycle
  always @(*) if (!f_init && f_after && !rst) assert(value >= f_top);
