
(* top =  1  *)
module halt_seq(hb_expired, tamper, cmd_halt, cmd_throttle, local_trip, clear, clear_authorized, cmd_exclude, hb_ok, loop_sense, tick, clk, rst, state, pwrbrk, perst, pwr_en, switch_open, ports_closed, cause, timer
, hb_seen, boot_timer, no_first_hb, excluded, rung_nv, rung_nv_safe, loop_lost);
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
  wire \$28 ;
  wire \$29 ;
  wire \$3 ;
  wire \$30 ;
  wire \$31 ;
  wire \$32 ;
  wire \$33 ;
  wire \$34 ;
  wire \$35 ;
  wire \$36 ;
  wire \$37 ;
  wire [20:0] \$38 ;
  wire \$39 ;
  wire \$4 ;
  wire [20:0] \$40 ;
  wire [20:0] \$41 ;
  wire \$42 ;
  wire [20:0] \$43 ;
  wire \$44 ;
  wire \$45 ;
  wire \$46 ;
  wire \$47 ;
  wire \$48 ;
  wire \$49 ;
  wire \$5 ;
  wire \$50 ;
  wire \$51 ;
  wire \$52 ;
  wire \$53 ;
  wire \$54 ;
  wire [16:0] \$55 ;
  wire \$56 ;
  wire \$57 ;
  wire \$58 ;
  wire \$59 ;
  wire \$6 ;
  wire \$60 ;
  wire \$61 ;
  wire \$62 ;
  wire \$63 ;
  reg \$64 ;
  reg \$65 ;
  reg [2:0] \$66 ;
  reg [2:0] \$67 ;
  reg \$68 ;
  reg [19:0] \$69 ;
  wire \$7 ;
  reg \$70 ;
  reg \$71 ;
  reg [15:0] \$72 ;
  wire \$8 ;
  wire \$9 ;
  output [15:0] boot_timer;
  reg [15:0] boot_timer = 16'h0000;
  output [2:0] cause;
  reg [2:0] cause = 3'h0;
  input clear;
  wire clear;
  input clear_authorized;
  wire clear_authorized;
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
  output rung_nv;
  reg rung_nv = 1'h0;
  output rung_nv_safe;
  reg rung_nv_safe = 1'h0;
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
  assign \$28  = cmd_exclude & \$27 ;
  assign \$29  = ! cause;
  assign \$30  = \$28  & \$29 ;
  assign \$31  = state == 2'h2;
  assign \$32  = tick & \$31 ;
  assign \$33  = state == 2'h3;
  assign \$34  = tick & \$33 ;
  assign \$35  = cause != 2'h3;
  assign \$36  = ~ loop_lost;
  assign \$37  = loop_sense & \$36 ;
  assign \$38  = timer + 1'h1;
  assign \$39  = \$38  >= 15'h7530;
  assign \$40  = timer + 1'h1;
  assign \$41  = timer + 1'h1;
  assign \$42  = \$41  >= 19'h493e0;
  assign \$43  = timer + 1'h1;
  assign \$44  = tamper | cmd_halt;
  assign \$45  = ~ hb_seen;
  assign \$46  = ! state;
  assign \$47  = \$45  & \$46 ;
  assign \$48  = ! cause;
  assign \$49  = \$47  & \$48 ;
  assign \$50  = ~ hb_ok;
  assign \$51  = \$49  & \$50 ;
  assign \$52  = \$51  & tick;
  assign \$53  = boot_timer != 16'hffff;
  assign \$54  = \$52  & \$53 ;
  assign \$55  = boot_timer + 1'h1;
  assign \$56  = ~ hb_seen;
  assign \$57  = boot_timer >= 13'h1388;
  assign no_first_hb = \$56  & \$57 ;
  assign pwrbrk = state != 1'h1;
  assign \$58  = ! state;
  assign \$59  = state == 2'h3;
  assign \$60  = \$58  | \$59 ;
  assign \$61  = state == 3'h4;
  assign perst = \$60  | \$61 ;
  assign \$62  = | state;
  assign \$63  = state != 3'h4;
  assign pwr_en = \$62  & \$63 ;
  assign ports_closed = state != 1'h1;
  always @(posedge clk)
    rung_nv <= \$64 ;
  always @(posedge clk)
    rung_nv_safe <= \$65 ;
  always @(posedge clk)
    state <= \$66 ;
  always @(posedge clk)
    cause <= \$67 ;
  always @(posedge clk)
    switch_open <= \$68 ;
  always @(posedge clk)
    timer <= \$69 ;
  always @(posedge clk)
    hb_seen <= \$70 ;
  always @(posedge clk)
    excluded <= \$71 ;
  always @(posedge clk)
    boot_timer <= \$72 ;
  assign \$1  = state == 2'h3;
  assign \$2  = state == 3'h4;
  assign \$3  = \$1  | \$2 ;
  assign \$4  = state == 3'h4;
  assign \$5  = clear & clear_authorized;
  assign \$6  = | state;
  assign \$7  = \$5  & \$6 ;
  assign \$8  = ! state;
  assign \$9  = rung_nv & \$8 ;
  assign \$10  = state == 1'h1;
  assign \$11  = state == 2'h2;
  assign \$12  = \$10  | \$11 ;
  assign \$13  = loop_lost & \$12 ;
  assign \$14  = state == 3'h4;
  assign \$15  = cmd_halt & \$14 ;
  assign \$16  = state == 1'h1;
  assign \$17  = state == 2'h2;
  assign \$18  = \$16  | \$17 ;
  assign \$19  = hb_expired & \$18 ;
  assign \$20  = local_trip | cmd_throttle;
  assign \$21  = state == 1'h1;
  assign \$22  = \$20  & \$21 ;
  assign \$23  = ! state;
  assign \$24  = ! cause;
  assign \$25  = \$23  & \$24 ;
  assign \$26  = \$25  & hb_ok;
  assign \$27  = ! state;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$64  = rung_nv;
    if (\$3 ) begin
      \$64  = 1'h1;
    end
    if (tamper) begin
      \$64  = 1'h1;
    end else if (\$7 ) begin
      \$64  = 1'h0;
    end else if (\$9 ) begin
    end else if (\$13 ) begin
      \$64  = 1'h1;
    end else if (\$15 ) begin
    end else if (cmd_halt) begin
      \$64  = 1'h1;
    end else if (\$19 ) begin
      \$64  = 1'h1;
    end else if (\$22 ) begin
    end else if (\$26 ) begin
    end else if (\$30 ) begin
    end else if (\$32 ) begin
      if (\$39 ) begin
        \$64  = 1'h1;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$65  = rung_nv_safe;
    if (\$4 ) begin
      \$65  = 1'h1;
    end
    if (tamper) begin
      \$65  = 1'h1;
    end else if (\$7 ) begin
      \$65  = 1'h0;
    end else if (\$9 ) begin
    end else if (\$13 ) begin
    end else if (\$15 ) begin
    end else if (cmd_halt) begin
    end else if (\$19 ) begin
    end else if (\$22 ) begin
    end else if (\$26 ) begin
    end else if (\$30 ) begin
    end else if (\$32 ) begin
    end else if (\$34 ) begin
      if (\$42 ) begin
        \$65  = 1'h1;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$66  = state;
    if (tamper) begin
      \$66  = 3'h4;
    end else if (\$7 ) begin
      \$66  = 3'h0;
    end else if (\$9 ) begin
      (* full_case = 32'd1 *)
      if (rung_nv_safe) begin
        \$66  = 3'h4;
      end else begin
        \$66  = 3'h3;
      end
    end else if (\$13 ) begin
      \$66  = 3'h3;
    end else if (\$15 ) begin
    end else if (cmd_halt) begin
      \$66  = 3'h3;
    end else if (\$19 ) begin
      \$66  = 3'h3;
    end else if (\$22 ) begin
      \$66  = 3'h2;
    end else if (\$26 ) begin
      if (\$37 ) begin
        \$66  = 3'h1;
      end
    end else if (\$30 ) begin
    end else if (\$32 ) begin
      if (\$39 ) begin
        \$66  = 3'h3;
      end
    end else if (\$34 ) begin
      if (\$42 ) begin
        \$66  = 3'h4;
      end
    end
    if (rst) begin
      \$66  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$67  = cause;
    if (tamper) begin
      \$67  = 3'h3;
    end else if (\$7 ) begin
      \$67  = 3'h0;
    end else if (\$9 ) begin
      \$67  = 3'h5;
    end else if (\$13 ) begin
      \$67  = 3'h1;
    end else if (\$15 ) begin
      if (\$35 ) begin
        \$67  = 3'h4;
      end
    end else if (cmd_halt) begin
      \$67  = 3'h4;
    end else if (\$19 ) begin
      \$67  = 3'h2;
    end else if (\$22 ) begin
      \$67  = 3'h2;
    end
    if (rst) begin
      \$67  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$68  = switch_open;
    if (tamper) begin
      \$68  = 1'h1;
    end else if (\$7 ) begin
    end else if (\$9 ) begin
      \$68  = 1'h1;
    end else if (\$13 ) begin
      \$68  = 1'h1;
    end else if (\$15 ) begin
      \$68  = 1'h1;
    end else if (cmd_halt) begin
      \$68  = 1'h1;
    end else if (\$19 ) begin
    end else if (\$22 ) begin
    end else if (\$26 ) begin
      \$68  = 1'h0;
    end else if (\$30 ) begin
      \$68  = 1'h0;
    end
    if (rst) begin
      \$68  = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$69  = timer;
    if (tamper) begin
    end else if (\$7 ) begin
      \$69  = 20'h00000;
    end else if (\$9 ) begin
      \$69  = 20'h00000;
    end else if (\$13 ) begin
      \$69  = 20'h00000;
    end else if (\$15 ) begin
    end else if (cmd_halt) begin
      \$69  = 20'h00000;
    end else if (\$19 ) begin
      \$69  = 20'h00000;
    end else if (\$22 ) begin
      \$69  = 20'h00000;
    end else if (\$26 ) begin
    end else if (\$30 ) begin
    end else if (\$32 ) begin
      (* full_case = 32'd1 *)
      if (\$39 ) begin
        \$69  = 20'h00000;
      end else begin
        \$69  = \$40 [19:0];
      end
    end else if (\$34 ) begin
      (* full_case = 32'd1 *)
      if (\$42 ) begin
        \$69  = 20'h00000;
      end else begin
        \$69  = \$43 [19:0];
      end
    end
    if (rst) begin
      \$69  = 20'h00000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$70  = hb_seen;
    if (tamper) begin
    end else if (\$7 ) begin
    end else if (\$9 ) begin
    end else if (\$13 ) begin
    end else if (\$15 ) begin
    end else if (cmd_halt) begin
    end else if (\$19 ) begin
    end else if (\$22 ) begin
    end else if (\$26 ) begin
      \$70  = 1'h1;
    end
    if (rst) begin
      \$70  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$71  = excluded;
    if (tamper) begin
    end else if (\$7 ) begin
    end else if (\$9 ) begin
    end else if (\$13 ) begin
    end else if (\$15 ) begin
    end else if (cmd_halt) begin
    end else if (\$19 ) begin
    end else if (\$22 ) begin
    end else if (\$26 ) begin
      \$71  = 1'h0;
    end else if (\$30 ) begin
      \$71  = 1'h1;
    end
    if (\$44 ) begin
      \$71  = 1'h0;
    end
    if (rst) begin
      \$71  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$72  = boot_timer;
    if (\$54 ) begin
      \$72  = \$55 [15:0];
    end
    if (rst) begin
      \$72  = 16'h0000;
    end
  end
endmodule