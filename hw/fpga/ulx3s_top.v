// ULX3S (Lattice ECP5 LFE5U-85F, CABGA381) top for the governor bench bitstream.
// Logic is bench_top (generated from Amaranth by hw/fpga/top.py); this file only holds what is board-specific:
// the PLL (25 MHz crystal to 50 MHz, the ASIC flow's clock), a power-on reset, and the pads.
// SCL and SDA are open drain: drive 0 or float, the pull-ups are on the host side (see BENCH.md).
// PERST# and PWRBRK# leave the FPGA as push-pull ASSERT lines (1 = assert) into an open-drain inverter (74HC05) whose
// inputs have pull-ups, so an FPGA that is unconfigured, reconfiguring or unplugged still holds both levers asserted.
// The inverter's outputs are the open-drain PERST# and PWRBRK# with 3.3 V pull-ups on the CEM breakout.
module ulx3s_top(
  input  clk_25mhz,
  input  btn_fire1,          // reset button (FIRE1, active high on ULX3S)
  inout  smb_scl, smb_sda,   // management bus, open drain
  output perst_assert, pwrbrk_assert,   // to the 74HC05 inputs (pulled up there): 1 = lever asserted
  output pwr_en,                        // push-pull, 10k pull-down on the bench so it is low when unconfigured
  output loop_closed,
  input  loop_sense,
  input  fw_hb, fw_clear, fw_halt, tamper_n, bench_rst,
  input  fw_sck, fw_sdi, fw_cs_n,
  output fw_sdo,
  output [7:0] led
);
  wire clk, locked;
  pll50 pll(.clkin(clk_25mhz), .clkout0(clk), .locked(locked));

  // reset: held for 2^16 cycles after the PLL locks, and whenever FIRE1 or the bench host's reset line is high
  reg [15:0] por = 0;
  reg rst_q = 1;
  always @(posedge clk) begin
    if (!locked || btn_fire1 || bench_rst) begin por <= 0; rst_q <= 1; end
    else if (por != 16'hFFFF) begin por <= por + 1; rst_q <= 1; end
    else rst_q <= 0;
  end

  wire scl_oe, sda_oe, perst_n_oe, pwrbrk_n_oe, scl_in, sda_in;
  // ECP5 bidirectional pad primitives: T = 1 floats the pad, so the pad is driven only to 0 (open drain)
  BB scl_pad(.I(1'b0), .T(~scl_oe), .O(scl_in), .B(smb_scl));
  BB sda_pad(.I(1'b0), .T(~sda_oe), .O(sda_in), .B(smb_sda));
  bench_top core(
    .clk(clk), .rst(rst_q),
    .scl_i(scl_in), .sda_i(sda_in), .scl_oe(scl_oe), .sda_oe(sda_oe),
    .perst_n_oe(perst_n_oe), .pwrbrk_n_oe(pwrbrk_n_oe), .pwr_en(pwr_en),
    .loop_closed(loop_closed), .loop_sense(loop_sense),
    .fw_hb(fw_hb), .fw_clear(fw_clear), .fw_halt(fw_halt), .tamper_n(tamper_n),
    .fw_sck(fw_sck), .fw_sdi(fw_sdi), .fw_cs_n(fw_cs_n), .fw_sdo(fw_sdo),
    .led(led));

  assign perst_assert  = perst_n_oe;
  assign pwrbrk_assert = pwrbrk_n_oe;
endmodule
