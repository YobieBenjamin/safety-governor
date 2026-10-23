
(* top =  1  *)
module halt_seq(hb_expired, tamper, cmd_halt, cmd_throttle, local_trip, clear, cmd_exclude, hb_ok, loop_sense, tick, clk, rst, state, pwrbrk, perst, pwr_en, switch_open, ports_closed, cause, timer, hb_seen
, boot_timer, no_first_hb, excluded, loop_lost);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  wire \$1 ;
  wire \$10 ;
  wire \$11 ;
  wire \$12 ;
  wire \$13 ;
  wire \$14 ;
  wire \$15 ;
  wire \$16 ;
  wire \$17 ;
  wire \$18 ;
  wire \$19 ;
  wire \$2 ;
  wire \$20 ;
  wire \$21 ;
  wire \$22 ;
  wire \$23 ;
  wire \$24 ;
  wire \$25 ;
  wire \$26 ;
  wire \$27 ;
  wire [20:0] \$28 ;
  wire \$29 ;
  wire \$3 ;
  wire [20:0] \$30 ;
  wire [20:0] \$31 ;
  wire \$32 ;
  wire [20:0] \$33 ;
  wire \$34 ;
  wire \$35 ;
  wire \$36 ;
  wire \$37 ;
  wire \$38 ;
  wire \$39 ;
  wire \$4 ;
  wire \$40 ;
  wire \$41 ;
  wire \$42 ;
  wire \$43 ;
  wire \$44 ;
  wire [16:0] \$45 ;
  wire \$46 ;
  wire \$47 ;
  wire \$48 ;
  wire \$49 ;
  wire \$5 ;
  wire \$50 ;
  wire \$51 ;
  wire \$52 ;
  wire \$53 ;
  reg [2:0] \$54 ;
  reg [2:0] \$55 ;
  reg \$56 ;
  reg [19:0] \$57 ;
  reg \$58 ;
  reg \$59 ;
  wire \$6 ;
  reg [15:0] \$60 ;
  wire \$7 ;
  wire \$8 ;
  wire \$9 ;
  output [15:0] boot_timer;
  reg [15:0] boot_timer = 16'h0000;
  output [2:0] cause;
  reg [2:0] cause = 3'h0;
  input clear;
  wire clear;
  input clk;
  wire clk;
  input cmd_exclude;
  wire cmd_exclude;
  input cmd_halt;
  wire cmd_halt;
  input cmd_throttle;
  wire cmd_throttle;
  output excluded;
  reg excluded = 1'h0;
  input hb_expired;
  wire hb_expired;
  input hb_ok;
  wire hb_ok;
  output hb_seen;
  reg hb_seen = 1'h0;
  input local_trip;
  wire local_trip;
  input loop_lost;
  wire loop_lost;
  input loop_sense;
  wire loop_sense;
  output no_first_hb;
  wire no_first_hb;
  output perst;
  wire perst;
  output ports_closed;
  wire ports_closed;
  output pwr_en;
  wire pwr_en;
  output pwrbrk;
  wire pwrbrk;
  input rst;
  wire rst;
  output [2:0] state;
  reg [2:0] state = 3'h0;
  output switch_open;
  reg switch_open = 1'h1;
  input tamper;
  wire tamper;
  input tick;
  wire tick;
  output [19:0] timer;
  reg [19:0] timer = 20'h00000;
  assign \$40  = ~ hb_ok;
  assign \$41  = \$39  & \$40 ;
  assign \$42  = \$41  & tick;
  assign \$43  = boot_timer != 16'hffff;
  assign \$44  = \$42  & \$43 ;
  assign \$45  = boot_timer + 1'h1;
  assign \$46  = ~ hb_seen;
  assign \$47  = boot_timer >= 13'h1388;
  assign no_first_hb = \$46  & \$47 ;
  assign pwrbrk = state != 1'h1;
  assign \$48  = ! state;
  assign \$49  = state == 2'h3;
  assign \$50  = \$48  | \$49 ;
  assign \$51  = state == 3'h4;
  assign perst = \$50  | \$51 ;
  assign \$52  = | state;
  assign \$53  = state != 3'h4;
  assign pwr_en = \$52  & \$53 ;
  assign ports_closed = state != 1'h1;
  always @(posedge clk)
    state <= \$54 ;
  always @(posedge clk)
    cause <= \$55 ;
  always @(posedge clk)
    switch_open <= \$56 ;
  always @(posedge clk)
    timer <= \$57 ;
  always @(posedge clk)
    hb_seen <= \$58 ;
  always @(posedge clk)
    excluded <= \$59 ;
  always @(posedge clk)
    boot_timer <= \$60 ;
  assign \$1  = | state;
  assign \$2  = clear & \$1 ;
  assign \$3  = state == 1'h1;
  assign \$4  = state == 2'h2;
  assign \$5  = \$3  | \$4 ;
  assign \$6  = loop_lost & \$5 ;
  assign \$7  = state == 3'h4;
  assign \$8  = cmd_halt & \$7 ;
  assign \$9  = hb_expired | local_trip;
  assign \$10  = \$9  | cmd_throttle;
  assign \$11  = state == 1'h1;
  assign \$12  = \$10  & \$11 ;
  assign \$13  = ! state;
  assign \$14  = ! cause;
  assign \$15  = \$13  & \$14 ;
  assign \$16  = \$15  & hb_ok;
  assign \$17  = ! state;
  assign \$18  = cmd_exclude & \$17 ;
  assign \$19  = ! cause;
  assign \$20  = \$18  & \$19 ;
  assign \$21  = state == 2'h2;
  assign \$22  = tick & \$21 ;
  assign \$23  = state == 2'h3;
  assign \$24  = tick & \$23 ;
  assign \$25  = cause != 2'h3;
  assign \$26  = ~ loop_lost;
  assign \$27  = loop_sense & \$26 ;
  assign \$28  = timer + 1'h1;
  assign \$29  = \$28  >= 15'h7530;
  assign \$30  = timer + 1'h1;
  assign \$31  = timer + 1'h1;
  assign \$32  = \$31  >= 19'h493e0;
  assign \$33  = timer + 1'h1;
  assign \$34  = tamper | cmd_halt;
  assign \$35  = ~ hb_seen;
  assign \$36  = ! state;
  assign \$37  = \$35  & \$36 ;
  assign \$38  = ! cause;
  assign \$39  = \$37  & \$38 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$54  = state;
    if (tamper) begin
      \$54  = 3'h4;
    end else if (\$2 ) begin
      \$54  = 3'h0;
    end else if (\$6 ) begin
      \$54  = 3'h3;
    end else if (\$8 ) begin
    end else if (cmd_halt) begin
      \$54  = 3'h3;
    end else if (\$12 ) begin
      \$54  = 3'h2;
    end else if (\$16 ) begin
      if (\$27 ) begin
        \$54  = 3'h1;
      end
    end else if (\$20 ) begin
    end else if (\$22 ) begin
      if (\$29 ) begin
        \$54  = 3'h3;
      end
    end else if (\$24 ) begin
      if (\$32 ) begin
        \$54  = 3'h4;
      end
    end
    if (rst) begin
      \$54  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$55  = cause;
    if (tamper) begin
      \$55  = 3'h3;
    end else if (\$2 ) begin
      \$55  = 3'h0;
    end else if (\$6 ) begin
      \$55  = 3'h1;
    end else if (\$8 ) begin
      if (\$25 ) begin
        \$55  = 3'h4;
      end
    end else if (cmd_halt) begin
      \$55  = 3'h4;
    end else if (\$12 ) begin
      \$55  = 3'h2;
    end
    if (rst) begin
      \$55  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$56  = switch_open;
    if (tamper) begin
      \$56  = 1'h1;
    end else if (\$2 ) begin
    end else if (\$6 ) begin
      \$56  = 1'h1;
    end else if (\$8 ) begin
      \$56  = 1'h1;
    end else if (cmd_halt) begin
      \$56  = 1'h1;
    end else if (\$12 ) begin
    end else if (\$16 ) begin
      \$56  = 1'h0;
    end else if (\$20 ) begin
      \$56  = 1'h0;
    end
    if (rst) begin
      \$56  = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$57  = timer;
    if (tamper) begin
    end else if (\$2 ) begin
      \$57  = 20'h00000;
    end else if (\$6 ) begin
      \$57  = 20'h00000;
    end else if (\$8 ) begin
    end else if (cmd_halt) begin
      \$57  = 20'h00000;
    end else if (\$12 ) begin
      \$57  = 20'h00000;
    end else if (\$16 ) begin
    end else if (\$20 ) begin
    end else if (\$22 ) begin
      (* full_case = 32'd1 *)
      if (\$29 ) begin
        \$57  = 20'h00000;
      end else begin
        \$57  = \$30 [19:0];
      end
    end else if (\$24 ) begin
      (* full_case = 32'd1 *)
      if (\$32 ) begin
        \$57  = 20'h00000;
      end else begin
        \$57  = \$33 [19:0];
      end
    end
    if (rst) begin
      \$57  = 20'h00000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$58  = hb_seen;
    if (tamper) begin
    end else if (\$2 ) begin
    end else if (\$6 ) begin
    end else if (\$8 ) begin
    end else if (cmd_halt) begin
    end else if (\$12 ) begin
    end else if (\$16 ) begin
      \$58  = 1'h1;
    end
    if (rst) begin
      \$58  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$59  = excluded;
    if (tamper) begin
    end else if (\$2 ) begin
    end else if (\$6 ) begin
    end else if (\$8 ) begin
    end else if (cmd_halt) begin
    end else if (\$12 ) begin
    end else if (\$16 ) begin
      \$59  = 1'h0;
    end else if (\$20 ) begin
      \$59  = 1'h1;
    end
    if (\$34 ) begin
      \$59  = 1'h0;
    end
    if (rst) begin
      \$59  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$60  = boot_timer;
    if (\$44 ) begin
      \$60  = \$45 [15:0];
    end
    if (rst) begin
      \$60  = 16'h0000;
    end
  end
endmodule