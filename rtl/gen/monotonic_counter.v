
(* top =  1  *)
module monotonic_counter(load_hwm, inc, dec_req, clk, rst, value, refused, hwm);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  wire \$1 ;
  wire \$2 ;
  wire \$3 ;
  wire \$4 ;
  wire [64:0] \$5 ;
  reg [63:0] \$6 ;
  input clk;
  wire clk;
  input dec_req;
  wire dec_req;
  input [63:0] hwm;
  wire [63:0] hwm;
  input inc;
  wire inc;
  input load_hwm;
  wire load_hwm;
  output refused;
  wire refused;
  input rst;
  wire rst;
  output [63:0] value;
  reg [63:0] value = 64'h0000000000000000;
  assign \$4  = hwm > value;
  assign \$5  = value + 1'h1;
  always @(posedge clk)
    value <= \$6 ;
  assign \$1  = & value;
  assign \$2  = ~ \$1 ;
  assign \$3  = inc & \$2 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$6  = value;
    if (load_hwm) begin
      if (\$4 ) begin
        \$6  = hwm;
      end
    end else if (\$3 ) begin
      \$6  = \$5 [63:0];
    end
    if (rst) begin
      \$6  = 64'h0000000000000000;
    end
  end
  assign refused = dec_req;
endmodule