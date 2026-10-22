
(* top =  1  *)
module loop_io(switch_open, sample, clk, rst, loop_out_open, loop_lost, count, loop_sense);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  wire \$1 ;
  wire \$2 ;
  wire [2:0] \$3 ;
  reg [1:0] \$4 ;
  input clk;
  wire clk;
  output [1:0] count;
  reg [1:0] count = 2'h0;
  output loop_lost;
  wire loop_lost;
  output loop_out_open;
  wire loop_out_open;
  input loop_sense;
  wire loop_sense;
  input rst;
  wire rst;
  input sample;
  wire sample;
  input switch_open;
  wire switch_open;
  always @(posedge clk)
    count <= \$4 ;
  assign loop_lost = count >= 2'h2;
  assign \$1  = ~ loop_sense;
  assign \$2  = count < 2'h2;
  assign \$3  = count + 1'h1;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$4  = count;
    if (sample) begin
      (* full_case = 32'd1 *)
      if (\$1 ) begin
        if (\$2 ) begin
          \$4  = \$3 [1:0];
        end
      end else begin
        \$4  = 2'h0;
      end
    end
    if (rst) begin
      \$4  = 2'h0;
    end
  end
  assign loop_out_open = switch_open;
endmodule