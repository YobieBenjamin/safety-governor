
(* top =  1  *)
module cem_sideband(pwr_en_req, pwrbrk_req, pwr_good, tick_us, clk, rst, perst, pwr_en, pwrbrk, pg_timer, hold_timer, perst_q, perst_req);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  wire \$1 ;
  wire \$10 ;
  wire \$11 ;
  wire \$12 ;
  wire \$13 ;
  wire [17:0] \$14 ;
  wire \$15 ;
  wire \$16 ;
  wire \$17 ;
  wire \$18 ;
  wire [7:0] \$19 ;
  wire \$2 ;
  reg \$20 ;
  reg [16:0] \$21 ;
  reg [6:0] \$22 ;
  wire \$3 ;
  wire \$4 ;
  wire \$5 ;
  wire \$6 ;
  wire \$7 ;
  wire \$8 ;
  wire \$9 ;
  input clk;
  wire clk;
  output [6:0] hold_timer;
  reg [6:0] hold_timer = 7'h00;
  output perst;
  wire perst;
  output perst_q;
  reg perst_q = 1'h1;
  input perst_req;
  wire perst_req;
  output [16:0] pg_timer;
  reg [16:0] pg_timer = 17'h00000;
  output pwr_en;
  wire pwr_en;
  input pwr_en_req;
  wire pwr_en_req;
  input pwr_good;
  wire pwr_good;
  output pwrbrk;
  wire pwrbrk;
  input pwrbrk_req;
  wire pwrbrk_req;
  input rst;
  wire rst;
  input tick_us;
  wire tick_us;
  assign \$1  = pwr_en_req & pwr_good;
  assign \$2  = ~ \$1 ;
  assign \$3  = perst_req | \$2 ;
  assign \$4  = pg_timer >= 17'h186a0;
  assign \$5  = ~ \$4 ;
  assign \$6  = \$3  | \$5 ;
  assign \$7  = hold_timer < 7'h64;
  assign \$8  = perst_q & \$7 ;
  assign perst = \$6  | \$8 ;
  assign \$9  = pwr_en_req & pwr_good;
  assign \$10  = ~ \$9 ;
  assign \$11  = pg_timer >= 17'h186a0;
  assign \$12  = ~ \$11 ;
  assign \$13  = tick_us & \$12 ;
  assign \$14  = pg_timer + 1'h1;
  assign \$15  = ~ perst;
  assign \$16  = ~ perst_q;
  assign \$17  = hold_timer < 7'h64;
  assign \$18  = tick_us & \$17 ;
  assign \$19  = hold_timer + 1'h1;
  always @(posedge clk)
    perst_q <= \$20 ;
  always @(posedge clk)
    pg_timer <= \$21 ;
  always @(posedge clk)
    hold_timer <= \$22 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$20  = perst;
    if (rst) begin
      \$20  = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$21  = pg_timer;
    if (\$10 ) begin
      \$21  = 17'h00000;
    end else if (\$13 ) begin
      \$21  = \$14 [16:0];
    end
    if (rst) begin
      \$21  = 17'h00000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$22  = hold_timer;
    if (\$15 ) begin
      \$22  = 7'h00;
    end else if (\$16 ) begin
      \$22  = 7'h00;
    end else if (\$18 ) begin
      \$22  = \$19 [6:0];
    end
    if (rst) begin
      \$22  = 7'h00;
    end
  end
  assign pwr_en = pwr_en_req;
  assign pwrbrk = pwrbrk_req;
endmodule