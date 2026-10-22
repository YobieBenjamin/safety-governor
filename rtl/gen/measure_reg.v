
(* top =  1  *)
module measure_reg(data, hash_done, hash_out, clk, rst, hash_req, hash_in, value, busy, extend);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  wire \$1 ;
  wire \$2 ;
  reg \$3 ;
  reg [255:0] \$4 ;
  output busy;
  reg busy;
  input clk;
  wire clk;
  input [255:0] data;
  wire [255:0] data;
  input extend;
  wire extend;
  reg fsm_state = 1'h0;
  input hash_done;
  wire hash_done;
  output [511:0] hash_in;
  wire [511:0] hash_in;
  input [255:0] hash_out;
  wire [255:0] hash_out;
  output hash_req;
  reg hash_req;
  input rst;
  wire rst;
  output [255:0] value;
  reg [255:0] value = 256'h0000000000000000000000000000000000000000000000000000000000000000;
  always @(posedge clk)
    fsm_state <= \$3 ;
  always @(posedge clk)
    value <= \$4 ;
  assign \$1  = ! fsm_state;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$4  = value;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (hash_done) begin
            \$4  = hash_out;
          end
    endcase
    if (rst) begin
      \$4  = 256'h0000000000000000000000000000000000000000000000000000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    hash_req = 1'h0;
    casez (fsm_state)
      1'h0:
          if (extend) begin
            hash_req = 1'h1;
          end
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    busy = 1'h0;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          busy = 1'h1;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$3  = fsm_state;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          if (extend) begin
            \$3  = 1'h1;
          end
      1'h1:
          if (hash_done) begin
            \$3  = 1'h0;
          end
    endcase
    if (rst) begin
      \$3  = 1'h0;
    end
  end
  assign hash_in = { value, data };
  assign \$2  = fsm_state;
endmodule