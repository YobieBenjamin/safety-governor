
(* top =  1  *)
module lifecycle(load, advance, advance_to, debug_req, clk, rst, state, debug_grant, debug_refused, advance_refused, loaded, fuse_state);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  wire \$1 ;
  reg [1:0] \$10 ;
  wire \$2 ;
  wire \$3 ;
  wire \$4 ;
  wire \$5 ;
  wire \$6 ;
  wire \$7 ;
  wire \$8 ;
  reg \$9 ;
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
  output loaded;
  reg loaded = 1'h0;
  input rst;
  wire rst;
  output [1:0] state;
  reg [1:0] state = 2'h0;
  assign \$1  = fuse_state > state;
  assign \$2  = advance_to > state;
  assign \$3  = advance_to <= state;
  assign advance_refused = advance & \$3 ;
  assign \$4  = debug_req & loaded;
  assign \$5  = state < 2'h2;
  assign debug_grant = \$4  & \$5 ;
  assign \$6  = state < 2'h2;
  assign \$7  = loaded & \$6 ;
  assign \$8  = ~ \$7 ;
  assign debug_refused = debug_req & \$8 ;
  always @(posedge clk)
    loaded <= \$9 ;
  always @(posedge clk)
    state <= \$10 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$9  = loaded;
    if (load) begin
      \$9  = 1'h1;
    end
    if (rst) begin
      \$9  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$10  = state;
    if (load) begin
      if (\$1 ) begin
        \$10  = fuse_state;
      end
    end else if (advance) begin
      if (\$2 ) begin
        \$10  = advance_to;
      end
    end
    if (rst) begin
      \$10  = 2'h0;
    end
  end
endmodule