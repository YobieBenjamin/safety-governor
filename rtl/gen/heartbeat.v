
(* top =  1  *)
module heartbeat(window, tick, clk, rst, remaining, expired, hb_valid);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  wire \$1 ;
  wire \$2 ;
  wire \$3 ;
  wire [32:0] \$4 ;
  reg [31:0] \$5 ;
  wire [31:0] clamped;
  input clk;
  wire clk;
  output expired;
  wire expired;
  input hb_valid;
  wire hb_valid;
  output [31:0] remaining;
  reg [31:0] remaining = 32'd0;
  input rst;
  wire rst;
  input tick;
  wire tick;
  input [31:0] window;
  wire [31:0] window;
  assign \$3  = tick & \$2 ;
  assign \$4  = remaining - 1'h1;
  always @(posedge clk)
    remaining <= \$5 ;
  assign \$1  = window > 13'h1388;
  assign clamped = \$1  ? 32'd5000 : window;
  assign expired = ! remaining;
  assign \$2  = | remaining;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$5  = remaining;
    if (hb_valid) begin
      \$5  = clamped;
    end else if (\$3 ) begin
      \$5  = \$4 [31:0];
    end
    if (rst) begin
      \$5  = 32'd0;
    end
  end
endmodule