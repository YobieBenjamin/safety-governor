
(* top =  1  *)
module halt_seq(hb_expired, tamper, cmd_halt, cmd_throttle, local_trip, clear, hb_ok, loop_sense, tick, clk, rst, state, pwrbrk, perst, pwr_en, switch_open, ports_closed, cause, timer, loop_lost);
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
  wire [20:0] \$23 ;
  wire \$24 ;
  wire [20:0] \$25 ;
  wire [20:0] \$26 ;
  wire \$27 ;
  wire [20:0] \$28 ;
  wire \$29 ;
  wire \$3 ;
  wire \$30 ;
  wire \$31 ;
  wire \$32 ;
  wire \$33 ;
  wire \$34 ;
  reg [2:0] \$35 ;
  reg [2:0] \$36 ;
  reg \$37 ;
  reg [19:0] \$38 ;
  wire \$4 ;
  wire \$5 ;
  wire \$6 ;
  wire \$7 ;
  wire \$8 ;
  wire \$9 ;
  output [2:0] cause;
  reg [2:0] cause = 3'h0;
  input clear;
  wire clear;
  input clk;
  wire clk;
  input cmd_halt;
  wire cmd_halt;
  input cmd_throttle;
  wire cmd_throttle;
  input hb_expired;
  wire hb_expired;
  input hb_ok;
  wire hb_ok;
  input local_trip;
  wire local_trip;
  input loop_lost;
  wire loop_lost;
  input loop_sense;
  wire loop_sense;
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
  assign \$1  = | state;
  assign \$2  = clear & \$1 ;
  assign \$3  = state == 1'h1;
  assign \$4  = state == 2'h2;
  assign \$5  = \$3  | \$4 ;
  assign \$6  = loop_lost & \$5 ;
  assign \$7  = state != 3'h4;
  assign \$8  = cmd_halt & \$7 ;
  assign \$9  = hb_expired | local_trip;
  assign \$10  = \$9  | cmd_throttle;
  assign \$11  = state == 1'h1;
  assign \$12  = \$10  & \$11 ;
  assign \$13  = ! state;
  assign \$14  = ! cause;
  assign \$15  = \$13  & \$14 ;
  assign \$16  = \$15  & hb_ok;
  assign \$17  = state == 2'h2;
  assign \$18  = tick & \$17 ;
  assign \$19  = state == 2'h3;
  assign \$20  = tick & \$19 ;
  assign \$21  = ~ loop_lost;
  assign \$22  = loop_sense & \$21 ;
  assign \$23  = timer + 1'h1;
  assign \$24  = \$23  >= 15'h7530;
  assign \$25  = timer + 1'h1;
  assign \$26  = timer + 1'h1;
  assign \$27  = \$26  >= 19'h493e0;
  assign \$28  = timer + 1'h1;
  assign pwrbrk = state != 1'h1;
  assign \$29  = ! state;
  assign \$30  = state == 2'h3;
  assign \$31  = \$29  | \$30 ;
  assign \$32  = state == 3'h4;
  assign perst = \$31  | \$32 ;
  assign \$33  = | state;
  assign \$34  = state != 3'h4;
  assign pwr_en = \$33  & \$34 ;
  assign ports_closed = state != 1'h1;
  always @(posedge clk)
    state <= \$35 ;
  always @(posedge clk)
    cause <= \$36 ;
  always @(posedge clk)
    switch_open <= \$37 ;
  always @(posedge clk)
    timer <= \$38 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$35  = state;
    if (tamper) begin
      \$35  = 3'h4;
    end else if (\$2 ) begin
      \$35  = 3'h0;
    end else if (\$6 ) begin
      \$35  = 3'h3;
    end else if (\$8 ) begin
      \$35  = 3'h3;
    end else if (\$12 ) begin
      \$35  = 3'h2;
    end else if (\$16 ) begin
      if (\$22 ) begin
        \$35  = 3'h1;
      end
    end else if (\$18 ) begin
      if (\$24 ) begin
        \$35  = 3'h3;
      end
    end else if (\$20 ) begin
      if (\$27 ) begin
        \$35  = 3'h4;
      end
    end
    if (rst) begin
      \$35  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$36  = cause;
    if (tamper) begin
      \$36  = 3'h3;
    end else if (\$2 ) begin
      \$36  = 3'h0;
    end else if (\$6 ) begin
      \$36  = 3'h1;
    end else if (\$8 ) begin
      \$36  = 3'h4;
    end else if (\$12 ) begin
      \$36  = 3'h2;
    end
    if (rst) begin
      \$36  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$37  = switch_open;
    if (tamper) begin
      \$37  = 1'h1;
    end else if (\$2 ) begin
    end else if (\$6 ) begin
      \$37  = 1'h1;
    end else if (\$8 ) begin
      \$37  = 1'h1;
    end else if (\$12 ) begin
    end else if (\$16 ) begin
      \$37  = 1'h0;
    end
    if (rst) begin
      \$37  = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$38  = timer;
    if (tamper) begin
    end else if (\$2 ) begin
      \$38  = 20'h00000;
    end else if (\$6 ) begin
      \$38  = 20'h00000;
    end else if (\$8 ) begin
      \$38  = 20'h00000;
    end else if (\$12 ) begin
      \$38  = 20'h00000;
    end else if (\$16 ) begin
    end else if (\$18 ) begin
      (* full_case = 32'd1 *)
      if (\$24 ) begin
        \$38  = 20'h00000;
      end else begin
        \$38  = \$25 [19:0];
      end
    end else if (\$20 ) begin
      (* full_case = 32'd1 *)
      if (\$27 ) begin
        \$38  = 20'h00000;
      end else begin
        \$38  = \$28 [19:0];
      end
    end
    if (rst) begin
      \$38  = 20'h00000;
    end
  end
endmodule