
(* top =  1  *)
module epoch_reg(quorum_ok, new_epoch, host_wr, host_data, clk, rst, epoch, epoch_tag, host_refused, commit);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  wire \$1 ;
  reg [255:0] \$2 ;
  input clk;
  wire clk;
  input commit;
  wire commit;
  output [255:0] epoch;
  reg [255:0] epoch = 256'h0000000000000000000000000000000000000000000000000000000000000000;
  output [15:0] epoch_tag;
  wire [15:0] epoch_tag;
  input [255:0] host_data;
  wire [255:0] host_data;
  output host_refused;
  wire host_refused;
  input host_wr;
  wire host_wr;
  input [255:0] new_epoch;
  wire [255:0] new_epoch;
  input quorum_ok;
  wire quorum_ok;
  input rst;
  wire rst;
  assign \$1  = commit & quorum_ok;
  always @(posedge clk)
    epoch <= \$2 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$2  = epoch;
    if (\$1 ) begin
      \$2  = new_epoch;
    end
    if (rst) begin
      \$2  = 256'h0000000000000000000000000000000000000000000000000000000000000000;
    end
  end
  assign epoch_tag = epoch[15:0];
  assign host_refused = host_wr;
endmodule