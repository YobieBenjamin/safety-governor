
(* top =  1  *)
module ticket_store(burn, id_in, clk, rst, seen, burned, full, query);
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
  reg \$33 ;
  reg \$34 ;
  reg \$35 ;
  reg \$36 ;
  reg \$37 ;
  reg \$38 ;
  reg \$39 ;
  wire \$4 ;
  reg \$40 ;
  reg [31:0] \$41 ;
  reg [31:0] \$42 ;
  reg [31:0] \$43 ;
  reg [31:0] \$44 ;
  reg [31:0] \$45 ;
  reg [31:0] \$46 ;
  reg [31:0] \$47 ;
  reg [31:0] \$48 ;
  wire \$5 ;
  wire \$6 ;
  wire \$7 ;
  wire \$8 ;
  wire \$9 ;
  input burn;
  wire burn;
  output burned;
  reg burned;
  input clk;
  wire clk;
  reg [3:0] free;
  output full;
  wire full;
  reg [31:0] id0 = 32'd0;
  reg [31:0] id1 = 32'd0;
  reg [31:0] id2 = 32'd0;
  reg [31:0] id3 = 32'd0;
  reg [31:0] id4 = 32'd0;
  reg [31:0] id5 = 32'd0;
  reg [31:0] id6 = 32'd0;
  reg [31:0] id7 = 32'd0;
  input [31:0] id_in;
  wire [31:0] id_in;
  wire match;
  input query;
  wire query;
  input rst;
  wire rst;
  output seen;
  reg seen;
  reg v0 = 1'h0;
  reg v1 = 1'h0;
  reg v2 = 1'h0;
  reg v3 = 1'h0;
  reg v4 = 1'h0;
  reg v5 = 1'h0;
  reg v6 = 1'h0;
  reg v7 = 1'h0;
  always @(posedge clk)
    v7 <= \$40 ;
  always @(posedge clk)
    id0 <= \$41 ;
  always @(posedge clk)
    id1 <= \$42 ;
  always @(posedge clk)
    id2 <= \$43 ;
  always @(posedge clk)
    id3 <= \$44 ;
  always @(posedge clk)
    id4 <= \$45 ;
  always @(posedge clk)
    id5 <= \$46 ;
  always @(posedge clk)
    id6 <= \$47 ;
  always @(posedge clk)
    id7 <= \$48 ;
  assign \$1  = id0 == id_in;
  assign \$2  = v0 & \$1 ;
  assign \$3  = id1 == id_in;
  assign \$4  = v1 & \$3 ;
  assign \$5  = id2 == id_in;
  assign \$6  = v2 & \$5 ;
  assign \$7  = id3 == id_in;
  assign \$8  = v3 & \$7 ;
  assign \$9  = id4 == id_in;
  assign \$10  = v4 & \$9 ;
  assign \$11  = id5 == id_in;
  assign \$12  = v5 & \$11 ;
  assign \$13  = id6 == id_in;
  assign \$14  = v6 & \$13 ;
  assign \$15  = id7 == id_in;
  assign \$16  = v7 & \$15 ;
  assign \$17  = ~ v7;
  assign \$18  = ~ v6;
  assign \$19  = ~ v5;
  assign \$20  = ~ v4;
  assign \$21  = ~ v3;
  assign \$22  = ~ v2;
  assign \$23  = ~ v1;
  assign \$24  = ~ v0;
  assign full = free == 4'h8;
  assign \$25  = ~ seen;
  assign \$26  = burn & \$25 ;
  assign \$27  = free != 4'h8;
  assign \$28  = \$26  & \$27 ;
  assign \$29  = ~ seen;
  assign \$30  = burn & \$29 ;
  assign \$31  = free != 4'h8;
  assign \$32  = \$30  & \$31 ;
  always @(posedge clk)
    v0 <= \$33 ;
  always @(posedge clk)
    v1 <= \$34 ;
  always @(posedge clk)
    v2 <= \$35 ;
  always @(posedge clk)
    v3 <= \$36 ;
  always @(posedge clk)
    v4 <= \$37 ;
  always @(posedge clk)
    v5 <= \$38 ;
  always @(posedge clk)
    v6 <= \$39 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$41  = id0;
    if (\$32 ) begin
      casez (free)
        4'h0:
            \$41  = id_in;
      endcase
    end
    if (rst) begin
      \$41  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$42  = id1;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$42  = id_in;
      endcase
    end
    if (rst) begin
      \$42  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$43  = id2;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$43  = id_in;
      endcase
    end
    if (rst) begin
      \$43  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$44  = id3;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$44  = id_in;
      endcase
    end
    if (rst) begin
      \$44  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$45  = id4;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            /* empty */;
        4'h4:
            \$45  = id_in;
      endcase
    end
    if (rst) begin
      \$45  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$46  = id5;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            /* empty */;
        4'h4:
            /* empty */;
        4'h5:
            \$46  = id_in;
      endcase
    end
    if (rst) begin
      \$46  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$47  = id6;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            /* empty */;
        4'h4:
            /* empty */;
        4'h5:
            /* empty */;
        4'h6:
            \$47  = id_in;
      endcase
    end
    if (rst) begin
      \$47  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$48  = id7;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            /* empty */;
        4'h4:
            /* empty */;
        4'h5:
            /* empty */;
        4'h6:
            /* empty */;
        4'h7:
            \$48  = id_in;
      endcase
    end
    if (rst) begin
      \$48  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    seen = 1'h0;
    if (\$2 ) begin
      seen = 1'h1;
    end
    if (\$4 ) begin
      seen = 1'h1;
    end
    if (\$6 ) begin
      seen = 1'h1;
    end
    if (\$8 ) begin
      seen = 1'h1;
    end
    if (\$10 ) begin
      seen = 1'h1;
    end
    if (\$12 ) begin
      seen = 1'h1;
    end
    if (\$14 ) begin
      seen = 1'h1;
    end
    if (\$16 ) begin
      seen = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    free = 4'h8;
    if (\$17 ) begin
      free = 4'h7;
    end
    if (\$18 ) begin
      free = 4'h6;
    end
    if (\$19 ) begin
      free = 4'h5;
    end
    if (\$20 ) begin
      free = 4'h4;
    end
    if (\$21 ) begin
      free = 4'h3;
    end
    if (\$22 ) begin
      free = 4'h2;
    end
    if (\$23 ) begin
      free = 4'h1;
    end
    if (\$24 ) begin
      free = 4'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    burned = 1'h0;
    if (\$28 ) begin
      burned = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$33  = v0;
    if (\$32 ) begin
      casez (free)
        4'h0:
            \$33  = 1'h1;
      endcase
    end
    if (rst) begin
      \$33  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$34  = v1;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$34  = 1'h1;
      endcase
    end
    if (rst) begin
      \$34  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$35  = v2;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$35  = 1'h1;
      endcase
    end
    if (rst) begin
      \$35  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$36  = v3;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$36  = 1'h1;
      endcase
    end
    if (rst) begin
      \$36  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$37  = v4;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            /* empty */;
        4'h4:
            \$37  = 1'h1;
      endcase
    end
    if (rst) begin
      \$37  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$38  = v5;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            /* empty */;
        4'h4:
            /* empty */;
        4'h5:
            \$38  = 1'h1;
      endcase
    end
    if (rst) begin
      \$38  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$39  = v6;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            /* empty */;
        4'h4:
            /* empty */;
        4'h5:
            /* empty */;
        4'h6:
            \$39  = 1'h1;
      endcase
    end
    if (rst) begin
      \$39  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$40  = v7;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            /* empty */;
        4'h4:
            /* empty */;
        4'h5:
            /* empty */;
        4'h6:
            /* empty */;
        4'h7:
            \$40  = 1'h1;
      endcase
    end
    if (rst) begin
      \$40  = 1'h0;
    end
  end
  assign match = seen;
endmodule