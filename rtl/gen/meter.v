
(* top =  1  *)
module meter(add_tokens, add_cycles, add_in, add_out, strobe, host_wr, rd_slot, clk, rst, host_wr_refused, rd_tokens, rd_cycles, rd_in, rd_out, slot);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  reg [47:0] \$1 ;
  wire [47:0] \$10 ;
  reg [47:0] \$11 ;
  wire [48:0] \$12 ;
  reg [47:0] \$13 ;
  wire [48:0] \$14 ;
  wire [47:0] \$15 ;
  reg [47:0] \$16 ;
  wire [48:0] \$17 ;
  reg [47:0] \$18 ;
  wire [48:0] \$19 ;
  wire [48:0] \$2 ;
  wire [47:0] \$20 ;
  reg [47:0] \$21 ;
  reg [47:0] \$22 ;
  reg [47:0] \$23 ;
  reg [47:0] \$24 ;
  reg [47:0] \$25 ;
  reg [47:0] \$26 ;
  reg [47:0] \$27 ;
  reg [47:0] \$28 ;
  reg [47:0] \$29 ;
  reg [47:0] \$3 ;
  reg [47:0] \$30 ;
  reg [47:0] \$31 ;
  reg [47:0] \$32 ;
  reg [47:0] \$33 ;
  reg [47:0] \$34 ;
  reg [47:0] \$35 ;
  reg [47:0] \$36 ;
  wire [48:0] \$4 ;
  wire [47:0] \$5 ;
  reg [47:0] \$6 ;
  wire [48:0] \$7 ;
  reg [47:0] \$8 ;
  wire [48:0] \$9 ;
  input [47:0] add_cycles;
  wire [47:0] add_cycles;
  input [47:0] add_in;
  wire [47:0] add_in;
  input [47:0] add_out;
  wire [47:0] add_out;
  input [47:0] add_tokens;
  wire [47:0] add_tokens;
  reg [47:0] bin0 = 48'h000000000000;
  reg [47:0] bin1 = 48'h000000000000;
  reg [47:0] bin2 = 48'h000000000000;
  reg [47:0] bin3 = 48'h000000000000;
  reg [47:0] bout0 = 48'h000000000000;
  reg [47:0] bout1 = 48'h000000000000;
  reg [47:0] bout2 = 48'h000000000000;
  reg [47:0] bout3 = 48'h000000000000;
  input clk;
  wire clk;
  reg [47:0] cyc0 = 48'h000000000000;
  reg [47:0] cyc1 = 48'h000000000000;
  reg [47:0] cyc2 = 48'h000000000000;
  reg [47:0] cyc3 = 48'h000000000000;
  input host_wr;
  wire host_wr;
  output host_wr_refused;
  wire host_wr_refused;
  output [47:0] rd_cycles;
  reg [47:0] rd_cycles;
  output [47:0] rd_in;
  reg [47:0] rd_in;
  output [47:0] rd_out;
  reg [47:0] rd_out;
  input [1:0] rd_slot;
  wire [1:0] rd_slot;
  output [47:0] rd_tokens;
  reg [47:0] rd_tokens;
  input rst;
  wire rst;
  input [1:0] slot;
  wire [1:0] slot;
  input strobe;
  wire strobe;
  reg [47:0] tok0 = 48'h000000000000;
  reg [47:0] tok1 = 48'h000000000000;
  reg [47:0] tok2 = 48'h000000000000;
  reg [47:0] tok3 = 48'h000000000000;
  assign \$2  = \$1  + add_tokens;
  assign \$4  = \$3  + add_tokens;
  assign \$5  = \$2 [48] ? 48'hffffffffffff : \$4 [47:0];
  assign \$7  = \$6  + add_cycles;
  assign \$9  = \$8  + add_cycles;
  assign \$10  = \$7 [48] ? 48'hffffffffffff : \$9 [47:0];
  assign \$12  = \$11  + add_in;
  assign \$14  = \$13  + add_in;
  assign \$15  = \$12 [48] ? 48'hffffffffffff : \$14 [47:0];
  assign \$17  = \$16  + add_out;
  assign \$19  = \$18  + add_out;
  assign \$20  = \$17 [48] ? 48'hffffffffffff : \$19 [47:0];
  always @(posedge clk)
    tok0 <= \$21 ;
  always @(posedge clk)
    tok1 <= \$22 ;
  always @(posedge clk)
    tok2 <= \$23 ;
  always @(posedge clk)
    tok3 <= \$24 ;
  always @(posedge clk)
    cyc0 <= \$25 ;
  always @(posedge clk)
    cyc1 <= \$26 ;
  always @(posedge clk)
    cyc2 <= \$27 ;
  always @(posedge clk)
    cyc3 <= \$28 ;
  always @(posedge clk)
    bin0 <= \$29 ;
  always @(posedge clk)
    bin1 <= \$30 ;
  always @(posedge clk)
    bin2 <= \$31 ;
  always @(posedge clk)
    bin3 <= \$32 ;
  always @(posedge clk)
    bout0 <= \$33 ;
  always @(posedge clk)
    bout1 <= \$34 ;
  always @(posedge clk)
    bout2 <= \$35 ;
  always @(posedge clk)
    bout3 <= \$36 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (slot)
      2'h0:
          \$1  = tok0;
      2'h1:
          \$1  = tok1;
      2'h2:
          \$1  = tok2;
      2'h3:
          \$1  = tok3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (slot)
      2'h0:
          \$3  = tok0;
      2'h1:
          \$3  = tok1;
      2'h2:
          \$3  = tok2;
      2'h3:
          \$3  = tok3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (slot)
      2'h0:
          \$6  = cyc0;
      2'h1:
          \$6  = cyc1;
      2'h2:
          \$6  = cyc2;
      2'h3:
          \$6  = cyc3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (slot)
      2'h0:
          \$8  = cyc0;
      2'h1:
          \$8  = cyc1;
      2'h2:
          \$8  = cyc2;
      2'h3:
          \$8  = cyc3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (slot)
      2'h0:
          \$11  = bin0;
      2'h1:
          \$11  = bin1;
      2'h2:
          \$11  = bin2;
      2'h3:
          \$11  = bin3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (slot)
      2'h0:
          \$13  = bin0;
      2'h1:
          \$13  = bin1;
      2'h2:
          \$13  = bin2;
      2'h3:
          \$13  = bin3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (slot)
      2'h0:
          \$16  = bout0;
      2'h1:
          \$16  = bout1;
      2'h2:
          \$16  = bout2;
      2'h3:
          \$16  = bout3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (slot)
      2'h0:
          \$18  = bout0;
      2'h1:
          \$18  = bout1;
      2'h2:
          \$18  = bout2;
      2'h3:
          \$18  = bout3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (rd_slot)
      2'h0:
          rd_tokens = tok0;
      2'h1:
          rd_tokens = tok1;
      2'h2:
          rd_tokens = tok2;
      2'h3:
          rd_tokens = tok3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (rd_slot)
      2'h0:
          rd_cycles = cyc0;
      2'h1:
          rd_cycles = cyc1;
      2'h2:
          rd_cycles = cyc2;
      2'h3:
          rd_cycles = cyc3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (rd_slot)
      2'h0:
          rd_in = bin0;
      2'h1:
          rd_in = bin1;
      2'h2:
          rd_in = bin2;
      2'h3:
          rd_in = bin3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (rd_slot)
      2'h0:
          rd_out = bout0;
      2'h1:
          rd_out = bout1;
      2'h2:
          rd_out = bout2;
      2'h3:
          rd_out = bout3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$21  = tok0;
    if (strobe) begin
      casez (slot)
        2'h0:
            \$21  = \$5 ;
      endcase
    end
    if (rst) begin
      \$21  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$22  = tok1;
    if (strobe) begin
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            \$22  = \$5 ;
      endcase
    end
    if (rst) begin
      \$22  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$23  = tok2;
    if (strobe) begin
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            /* empty */;
        2'h2:
            \$23  = \$5 ;
      endcase
    end
    if (rst) begin
      \$23  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$24  = tok3;
    if (strobe) begin
      (* full_case = 32'd1 *)
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            /* empty */;
        2'h2:
            /* empty */;
        2'h3:
            \$24  = \$5 ;
      endcase
    end
    if (rst) begin
      \$24  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$25  = cyc0;
    if (strobe) begin
      casez (slot)
        2'h0:
            \$25  = \$10 ;
      endcase
    end
    if (rst) begin
      \$25  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$26  = cyc1;
    if (strobe) begin
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            \$26  = \$10 ;
      endcase
    end
    if (rst) begin
      \$26  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$27  = cyc2;
    if (strobe) begin
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            /* empty */;
        2'h2:
            \$27  = \$10 ;
      endcase
    end
    if (rst) begin
      \$27  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$28  = cyc3;
    if (strobe) begin
      (* full_case = 32'd1 *)
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            /* empty */;
        2'h2:
            /* empty */;
        2'h3:
            \$28  = \$10 ;
      endcase
    end
    if (rst) begin
      \$28  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$29  = bin0;
    if (strobe) begin
      casez (slot)
        2'h0:
            \$29  = \$15 ;
      endcase
    end
    if (rst) begin
      \$29  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$30  = bin1;
    if (strobe) begin
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            \$30  = \$15 ;
      endcase
    end
    if (rst) begin
      \$30  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$31  = bin2;
    if (strobe) begin
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            /* empty */;
        2'h2:
            \$31  = \$15 ;
      endcase
    end
    if (rst) begin
      \$31  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$32  = bin3;
    if (strobe) begin
      (* full_case = 32'd1 *)
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            /* empty */;
        2'h2:
            /* empty */;
        2'h3:
            \$32  = \$15 ;
      endcase
    end
    if (rst) begin
      \$32  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$33  = bout0;
    if (strobe) begin
      casez (slot)
        2'h0:
            \$33  = \$20 ;
      endcase
    end
    if (rst) begin
      \$33  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$34  = bout1;
    if (strobe) begin
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            \$34  = \$20 ;
      endcase
    end
    if (rst) begin
      \$34  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$35  = bout2;
    if (strobe) begin
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            /* empty */;
        2'h2:
            \$35  = \$20 ;
      endcase
    end
    if (rst) begin
      \$35  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$36  = bout3;
    if (strobe) begin
      (* full_case = 32'd1 *)
      casez (slot)
        2'h0:
            /* empty */;
        2'h1:
            /* empty */;
        2'h2:
            /* empty */;
        2'h3:
            \$36  = \$20 ;
      endcase
    end
    if (rst) begin
      \$36  = 48'h000000000000;
    end
  end
  assign host_wr_refused = host_wr;
endmodule