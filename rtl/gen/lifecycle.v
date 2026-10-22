
(* top =  1  *)
module lifecycle(load, advance, advance_to, debug_req, clk, rst, state, debug_grant, debug_refused, advance_refused, fuse_state);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  wire \$1 ;
  wire \$2 ;
  wire \$3 ;
  wire \$4 ;
  wire \$5 ;
  reg [1:0] \$6 ;
  input advance;
  wire advance;
  output advance_refused;
  wire advance_refused;
  input [1:0] advance_to;
  wire [1:0] advance_to;
  input clk;
  wire clk;
  output debug_grant;
  wire debug_grant;
  output debug_refused;
  wire debug_refused;
  input debug_req;
  wire debug_req;
  input [1:0] fuse_state;
  wire [1:0] fuse_state;
  input load;
  wire load;
  input rst;
  wire rst;
  output [1:0] state;
  reg [1:0] state = 2'h0;
  assign advance_refused = advance & \$3 ;
  assign \$4  = state < 2'h2;
  assign debug_grant = debug_req & \$4 ;
  assign \$5  = state >= 2'h2;
  assign debug_refused = debug_req & \$5 ;
  always @(posedge clk)
    state <= \$6 ;
  assign \$1  = fuse_state > state;
  assign \$2  = advance_to > state;
  assign \$3  = advance_to <= state;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$6  = state;
    if (load) begin
      if (\$1 ) begin
        \$6  = fuse_state;
      end
    end else if (advance) begin
      if (\$2 ) begin
        \$6  = advance_to;
      end
    end
    if (rst) begin
      \$6  = 2'h0;
    end
  end
endmodule