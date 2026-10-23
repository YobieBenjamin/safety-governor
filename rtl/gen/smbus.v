
(* top =  1  *)
module smbus(sda_i, tick, csr_rdata, clk, rst, scl_oe, sda_oe, csr_addr, doorbell, doorbell_value, timeout, pec_error, refused_write, scl_f, sda_f, scl_p, sda_p, phase, step, nbit, shift
, ack, sr_seen, cmd, cmd_valid, dcount, wbuf, crc, armed, snap, txidx, txsh, host_ack, tcount, scl_i);
  reg \$auto$verilog_backend.cc:2355:dump_module$1  = 0;
  wire \$1 ;
  wire \$10 ;
  wire \$100 ;
  wire \$101 ;
  wire \$102 ;
  wire \$103 ;
  wire \$104 ;
  wire \$105 ;
  wire [7:0] \$106 ;
  wire [7:0] \$107 ;
  wire \$108 ;
  wire [7:0] \$109 ;
  wire \$11 ;
  wire \$110 ;
  wire [7:0] \$111 ;
  wire [7:0] \$112 ;
  wire \$113 ;
  wire [7:0] \$114 ;
  wire \$115 ;
  wire [7:0] \$116 ;
  wire [7:0] \$117 ;
  wire \$118 ;
  wire [7:0] \$119 ;
  wire \$12 ;
  wire \$120 ;
  wire [7:0] \$121 ;
  wire \$122 ;
  wire [7:0] \$123 ;
  wire [7:0] \$124 ;
  wire \$125 ;
  wire [7:0] \$126 ;
  wire \$127 ;
  wire [7:0] \$128 ;
  wire \$129 ;
  wire \$13 ;
  wire [7:0] \$130 ;
  wire [7:0] \$131 ;
  wire \$132 ;
  wire [7:0] \$133 ;
  wire \$134 ;
  wire [7:0] \$135 ;
  wire [7:0] \$136 ;
  wire \$137 ;
  wire [7:0] \$138 ;
  wire \$139 ;
  wire [15:0] \$14 ;
  wire [7:0] \$140 ;
  wire [7:0] \$141 ;
  wire \$142 ;
  wire [7:0] \$143 ;
  wire \$144 ;
  wire [7:0] \$145 ;
  wire [7:0] \$146 ;
  wire \$147 ;
  wire [7:0] \$148 ;
  wire \$149 ;
  wire \$15 ;
  wire \$150 ;
  wire [3:0] \$151 ;
  wire [3:0] \$152 ;
  wire \$153 ;
  wire \$154 ;
  wire \$155 ;
  wire \$156 ;
  wire \$157 ;
  wire \$158 ;
  wire \$159 ;
  wire \$16 ;
  wire \$160 ;
  wire [7:0] \$161 ;
  wire [7:0] \$162 ;
  wire \$163 ;
  wire [7:0] \$164 ;
  wire \$165 ;
  wire [7:0] \$166 ;
  wire [7:0] \$167 ;
  wire \$168 ;
  wire [7:0] \$169 ;
  wire \$17 ;
  wire \$170 ;
  wire [7:0] \$171 ;
  wire [7:0] \$172 ;
  wire \$173 ;
  wire [7:0] \$174 ;
  wire \$175 ;
  wire [7:0] \$176 ;
  wire \$177 ;
  wire [7:0] \$178 ;
  wire [7:0] \$179 ;
  wire \$18 ;
  wire \$180 ;
  wire [7:0] \$181 ;
  wire \$182 ;
  wire [7:0] \$183 ;
  wire \$184 ;
  wire [7:0] \$185 ;
  wire [7:0] \$186 ;
  wire \$187 ;
  wire [7:0] \$188 ;
  wire \$189 ;
  wire \$19 ;
  wire [7:0] \$190 ;
  wire [7:0] \$191 ;
  wire \$192 ;
  wire [7:0] \$193 ;
  wire \$194 ;
  wire [7:0] \$195 ;
  wire [7:0] \$196 ;
  wire \$197 ;
  wire [7:0] \$198 ;
  wire \$199 ;
  wire \$2 ;
  wire \$20 ;
  wire [7:0] \$200 ;
  wire [7:0] \$201 ;
  wire \$202 ;
  wire [7:0] \$203 ;
  wire \$204 ;
  wire \$205 ;
  wire \$206 ;
  wire \$207 ;
  wire \$208 ;
  wire \$209 ;
  wire \$21 ;
  wire \$210 ;
  reg \$211 ;
  reg [1:0] \$212 ;
  reg \$213 ;
  reg [1:0] \$214 ;
  reg \$215 ;
  reg \$216 ;
  reg \$217 ;
  reg \$218 ;
  reg \$219 ;
  wire \$22 ;
  reg \$220 ;
  reg [14:0] \$221 ;
  reg [1:0] \$222 ;
  reg \$223 ;
  reg \$224 ;
  reg \$225 ;
  reg [31:0] \$226 ;
  reg [7:0] \$227 ;
  reg \$228 ;
  reg [2:0] \$229 ;
  wire \$23 ;
  reg [3:0] \$230 ;
  reg [7:0] \$231 ;
  reg \$232 ;
  reg [31:0] \$233 ;
  reg [2:0] \$234 ;
  reg [7:0] \$235 ;
  reg [1:0] \$236 ;
  reg [31:0] \$237 ;
  reg \$238 ;
  reg [7:0] \$239 ;
  wire \$24 ;
  wire \$25 ;
  wire \$26 ;
  wire [4:0] \$27 ;
  wire [4:0] \$28 ;
  wire \$29 ;
  wire [2:0] \$3 ;
  wire \$30 ;
  wire \$31 ;
  wire \$32 ;
  wire \$33 ;
  wire \$34 ;
  wire \$35 ;
  wire \$36 ;
  wire \$37 ;
  wire \$38 ;
  wire \$39 ;
  wire \$4 ;
  wire \$40 ;
  wire [2:0] \$41 ;
  wire \$42 ;
  wire \$43 ;
  wire \$44 ;
  wire \$45 ;
  wire \$46 ;
  wire \$47 ;
  wire \$48 ;
  wire \$49 ;
  wire \$5 ;
  wire \$50 ;
  wire \$51 ;
  wire [7:0] \$52 ;
  wire [7:0] \$53 ;
  wire \$54 ;
  wire [7:0] \$55 ;
  wire \$56 ;
  wire [7:0] \$57 ;
  wire [7:0] \$58 ;
  wire \$59 ;
  wire [2:0] \$6 ;
  wire [7:0] \$60 ;
  wire \$61 ;
  wire [7:0] \$62 ;
  wire [7:0] \$63 ;
  wire \$64 ;
  wire [7:0] \$65 ;
  wire \$66 ;
  wire [7:0] \$67 ;
  wire \$68 ;
  wire [7:0] \$69 ;
  wire \$7 ;
  wire [7:0] \$70 ;
  wire \$71 ;
  wire [7:0] \$72 ;
  wire \$73 ;
  wire [7:0] \$74 ;
  wire \$75 ;
  wire [7:0] \$76 ;
  wire [7:0] \$77 ;
  wire \$78 ;
  wire [7:0] \$79 ;
  wire \$8 ;
  wire \$80 ;
  wire [7:0] \$81 ;
  wire [7:0] \$82 ;
  wire \$83 ;
  wire [7:0] \$84 ;
  wire \$85 ;
  wire [7:0] \$86 ;
  wire [7:0] \$87 ;
  wire \$88 ;
  wire [7:0] \$89 ;
  wire \$9 ;
  wire \$90 ;
  wire [7:0] \$91 ;
  wire [7:0] \$92 ;
  wire \$93 ;
  wire [7:0] \$94 ;
  wire \$95 ;
  wire \$96 ;
  wire [3:0] \$97 ;
  wire [3:0] \$98 ;
  wire \$99 ;
  output ack;
  reg ack = 1'h0;
  output armed;
  reg armed = 1'h0;
  wire [7:0] \byte ;
  input clk;
  wire clk;
  output [7:0] cmd;
  reg [7:0] cmd = 8'h00;
  output cmd_valid;
  reg cmd_valid = 1'h0;
  output [7:0] crc;
  reg [7:0] crc = 8'h00;
  wire [7:0] crc_next;
  output [11:0] csr_addr;
  wire [11:0] csr_addr;
  input [31:0] csr_rdata;
  wire [31:0] csr_rdata;
  output [1:0] dcount;
  reg [1:0] dcount = 2'h0;
  output doorbell;
  reg doorbell = 1'h0;
  output [31:0] doorbell_value;
  reg [31:0] doorbell_value = 32'd0;
  wire expire;
  wire fall;
  output host_ack;
  reg host_ack = 1'h0;
  output [3:0] nbit;
  reg [3:0] nbit = 4'h0;
  output pec_error;
  reg pec_error = 1'h0;
  output [1:0] phase;
  reg [1:0] phase = 2'h0;
  output refused_write;
  reg refused_write = 1'h0;
  wire rise;
  input rst;
  wire rst;
  output scl_f;
  reg scl_f = 1'h1;
  reg [1:0] scl_fcnt = 2'h0;
  input scl_i;
  wire scl_i;
  output scl_oe;
  wire scl_oe;
  output scl_p;
  reg scl_p = 1'h1;
  wire scl_s;
  output sda_f;
  reg sda_f = 1'h1;
  reg [1:0] sda_fcnt = 2'h0;
  input sda_i;
  wire sda_i;
  output sda_oe;
  reg sda_oe = 1'h0;
  output sda_p;
  reg sda_p = 1'h1;
  wire sda_s;
  output [7:0] shift;
  reg [7:0] shift = 8'h00;
  output [31:0] snap;
  reg [31:0] snap = 32'd0;
  output sr_seen;
  reg sr_seen = 1'h0;
  wire start;
  output [2:0] step;
  reg [2:0] step = 3'h0;
  wire stop;
  output [14:0] tcount;
  reg [14:0] tcount = 15'h0000;
  input tick;
  wire tick;
  output timeout;
  reg timeout = 1'h0;
  reg [7:0] tx_byte;
  output [2:0] txidx;
  reg [2:0] txidx = 3'h0;
  output [7:0] txsh;
  reg [7:0] txsh = 8'h00;
  output [31:0] wbuf;
  reg [31:0] wbuf = 32'd0;
  assign \$1  = scl_s != scl_f;
  assign \$2  = scl_fcnt == 2'h2;
  assign \$3  = scl_fcnt + 1'h1;
  assign \$4  = sda_s != sda_f;
  assign \$5  = sda_fcnt == 2'h2;
  assign \$6  = sda_fcnt + 1'h1;
  assign \$7  = | phase;
  assign \$8  = ~ scl_f;
  assign \$9  = \$8  | sda_oe;
  assign \$10  = \$7  & \$9 ;
  assign \$11  = ~ \$10 ;
  assign \$12  = ~ expire;
  assign \$13  = tick & \$12 ;
  assign \$14  = tcount + 1'h1;
  assign \$15  = phase == 1'h1;
  assign \$16  = phase == 2'h2;
  assign \$17  = \$15  | \$16 ;
  assign \$18  = rise & \$17 ;
  assign \$19  = phase == 1'h1;
  assign \$20  = phase == 2'h2;
  assign \$21  = \$19  | \$20 ;
  assign \$22  = fall & \$21 ;
  assign \$23  = | phase;
  assign \$24  = armed & \$23 ;
  assign \$25  = ! phase;
  assign \$26  = nbit == 4'h9;
  assign \$27  = nbit + 1'h1;
  assign \$28  = \$26  ? 5'h09 : \$27 ;
  assign \$29  = step == 3'h5;
  assign \$30  = nbit >= 1'h1;
  assign \$31  = \$29  & \$30 ;
  assign \$32  = phase == 1'h1;
  assign \$33  = nbit == 4'h8;
  assign \$34  = nbit < 3'h7;
  assign \$35  = nbit == 3'h7;
  assign \$36  = shift[6:0] != 7'h58;
  assign \$37  = ~ sda_f;
  assign \$38  = cmd == 7'h40;
  assign \$39  = { shift[6:0], sda_f } == 3'h4;
  assign \$40  = \$38  & \$39 ;
  assign \$41  = dcount + 1'h1;
  assign \$42  = dcount == 2'h3;
  assign \$43  = { shift[6:0], sda_f } == crc;
  assign \$44  = ~ sda_f;
  assign \$45  = phase == 1'h1;
  assign \$46  = nbit == 4'h8;
  assign \$47  = nbit == 4'h9;
  assign \$48  = ~ ack;
  assign \$49  = step == 3'h6;
  assign \$50  = step == 3'h5;
  assign \$51  = ~ tx_byte[7];
  assign \$52  = crc ^ tx_byte;
  assign \$53  = crc ^ tx_byte;
  assign \$54  = \$52 [0] ^ \$53 [6];
  assign \$55  = crc ^ tx_byte;
  assign \$56  = \$54  ^ \$55 [7];
  assign \$57  = crc ^ tx_byte;
  assign \$58  = crc ^ tx_byte;
  assign \$59  = \$57 [0] ^ \$58 [1];
  assign \$60  = crc ^ tx_byte;
  assign \$61  = \$59  ^ \$60 [6];
  assign \$62  = crc ^ tx_byte;
  assign \$63  = crc ^ tx_byte;
  assign \$64  = \$62 [0] ^ \$63 [1];
  assign \$65  = crc ^ tx_byte;
  assign \$66  = \$64  ^ \$65 [2];
  assign \$67  = crc ^ tx_byte;
  assign \$68  = \$66  ^ \$67 [6];
  assign \$69  = crc ^ tx_byte;
  assign \$70  = crc ^ tx_byte;
  assign \$71  = \$69 [1] ^ \$70 [2];
  assign \$72  = crc ^ tx_byte;
  assign \$73  = \$71  ^ \$72 [3];
  assign \$74  = crc ^ tx_byte;
  assign \$75  = \$73  ^ \$74 [7];
  assign \$76  = crc ^ tx_byte;
  assign \$77  = crc ^ tx_byte;
  assign \$78  = \$76 [2] ^ \$77 [3];
  assign \$79  = crc ^ tx_byte;
  assign \$80  = \$78  ^ \$79 [4];
  assign \$81  = crc ^ tx_byte;
  assign \$82  = crc ^ tx_byte;
  assign \$83  = \$81 [3] ^ \$82 [4];
  assign \$84  = crc ^ tx_byte;
  assign \$85  = \$83  ^ \$84 [5];
  assign \$86  = crc ^ tx_byte;
  assign \$87  = crc ^ tx_byte;
  assign \$88  = \$86 [4] ^ \$87 [5];
  assign \$89  = crc ^ tx_byte;
  assign \$90  = \$88  ^ \$89 [6];
  assign \$91  = crc ^ tx_byte;
  assign \$92  = crc ^ tx_byte;
  assign \$93  = \$91 [5] ^ \$92 [6];
  assign \$94  = crc ^ tx_byte;
  assign \$95  = \$93  ^ \$94 [7];
  assign \$96  = txidx == 3'h7;
  assign \$97  = txidx + 1'h1;
  assign \$98  = \$96  ? 4'h7 : \$97 ;
  assign \$99  = nbit >= 1'h1;
  assign \$100  = nbit <= 3'h7;
  assign \$101  = \$99  & \$100 ;
  assign \$102  = nbit == 4'h8;
  assign \$103  = nbit == 4'h9;
  assign \$104  = ~ txsh[6];
  assign \$105  = ~ tx_byte[7];
  assign \$106  = crc ^ tx_byte;
  assign \$107  = crc ^ tx_byte;
  assign \$108  = \$106 [0] ^ \$107 [6];
  assign \$109  = crc ^ tx_byte;
  assign \$110  = \$108  ^ \$109 [7];
  assign \$111  = crc ^ tx_byte;
  assign \$112  = crc ^ tx_byte;
  assign \$113  = \$111 [0] ^ \$112 [1];
  assign \$114  = crc ^ tx_byte;
  assign \$115  = \$113  ^ \$114 [6];
  assign \$116  = crc ^ tx_byte;
  assign \$117  = crc ^ tx_byte;
  assign \$118  = \$116 [0] ^ \$117 [1];
  assign \$119  = crc ^ tx_byte;
  assign \$120  = \$118  ^ \$119 [2];
  assign \$121  = crc ^ tx_byte;
  assign \$122  = \$120  ^ \$121 [6];
  assign \$123  = crc ^ tx_byte;
  assign \$124  = crc ^ tx_byte;
  assign \$125  = \$123 [1] ^ \$124 [2];
  assign \$126  = crc ^ tx_byte;
  assign \$127  = \$125  ^ \$126 [3];
  assign \$128  = crc ^ tx_byte;
  assign \$129  = \$127  ^ \$128 [7];
  assign \$130  = crc ^ tx_byte;
  assign \$131  = crc ^ tx_byte;
  assign \$132  = \$130 [2] ^ \$131 [3];
  assign \$133  = crc ^ tx_byte;
  assign \$134  = \$132  ^ \$133 [4];
  assign \$135  = crc ^ tx_byte;
  assign \$136  = crc ^ tx_byte;
  assign \$137  = \$135 [3] ^ \$136 [4];
  assign \$138  = crc ^ tx_byte;
  assign \$139  = \$137  ^ \$138 [5];
  assign \$140  = crc ^ tx_byte;
  assign \$141  = crc ^ tx_byte;
  assign \$142  = \$140 [4] ^ \$141 [5];
  assign \$143  = crc ^ tx_byte;
  assign \$144  = \$142  ^ \$143 [6];
  assign \$145  = crc ^ tx_byte;
  assign \$146  = crc ^ tx_byte;
  assign \$147  = \$145 [5] ^ \$146 [6];
  assign \$148  = crc ^ tx_byte;
  assign \$149  = \$147  ^ \$148 [7];
  assign \$150  = txidx == 3'h7;
  assign \$151  = txidx + 1'h1;
  assign \$152  = \$150  ? 4'h7 : \$151 ;
  assign \$153  = scl_f & scl_p;
  assign \$154  = \$153  & sda_p;
  assign \$155  = ~ sda_f;
  assign start = \$154  & \$155 ;
  assign \$156  = scl_f & scl_p;
  assign \$157  = ~ sda_p;
  assign \$158  = \$156  & \$157 ;
  assign stop = \$158  & sda_f;
  assign \$159  = ~ scl_p;
  assign rise = scl_f & \$159 ;
  assign \$160  = ~ scl_f;
  assign fall = \$160  & scl_p;
  assign \$161  = crc ^ { shift[6:0], sda_f };
  assign \$162  = crc ^ { shift[6:0], sda_f };
  assign \$163  = \$161 [0] ^ \$162 [6];
  assign \$164  = crc ^ { shift[6:0], sda_f };
  assign \$165  = \$163  ^ \$164 [7];
  assign \$166  = crc ^ { shift[6:0], sda_f };
  assign \$167  = crc ^ { shift[6:0], sda_f };
  assign \$168  = \$166 [0] ^ \$167 [1];
  assign \$169  = crc ^ { shift[6:0], sda_f };
  assign \$170  = \$168  ^ \$169 [6];
  assign \$171  = crc ^ { shift[6:0], sda_f };
  assign \$172  = crc ^ { shift[6:0], sda_f };
  assign \$173  = \$171 [0] ^ \$172 [1];
  assign \$174  = crc ^ { shift[6:0], sda_f };
  assign \$175  = \$173  ^ \$174 [2];
  assign \$176  = crc ^ { shift[6:0], sda_f };
  assign \$177  = \$175  ^ \$176 [6];
  assign \$178  = crc ^ { shift[6:0], sda_f };
  assign \$179  = crc ^ { shift[6:0], sda_f };
  assign \$180  = \$178 [1] ^ \$179 [2];
  assign \$181  = crc ^ { shift[6:0], sda_f };
  assign \$182  = \$180  ^ \$181 [3];
  assign \$183  = crc ^ { shift[6:0], sda_f };
  assign \$184  = \$182  ^ \$183 [7];
  assign \$185  = crc ^ { shift[6:0], sda_f };
  assign \$186  = crc ^ { shift[6:0], sda_f };
  assign \$187  = \$185 [2] ^ \$186 [3];
  assign \$188  = crc ^ { shift[6:0], sda_f };
  assign \$189  = \$187  ^ \$188 [4];
  assign \$190  = crc ^ { shift[6:0], sda_f };
  assign \$191  = crc ^ { shift[6:0], sda_f };
  assign \$192  = \$190 [3] ^ \$191 [4];
  assign \$193  = crc ^ { shift[6:0], sda_f };
  assign \$194  = \$192  ^ \$193 [5];
  assign \$195  = crc ^ { shift[6:0], sda_f };
  assign \$196  = crc ^ { shift[6:0], sda_f };
  assign \$197  = \$195 [4] ^ \$196 [5];
  assign \$198  = crc ^ { shift[6:0], sda_f };
  assign \$199  = \$197  ^ \$198 [6];
  assign \$200  = crc ^ { shift[6:0], sda_f };
  assign \$201  = crc ^ { shift[6:0], sda_f };
  assign \$202  = \$200 [5] ^ \$201 [6];
  assign \$203  = crc ^ { shift[6:0], sda_f };
  assign \$204  = \$202  ^ \$203 [7];
  assign \$205  = | phase;
  assign \$206  = ~ scl_f;
  assign \$207  = \$206  | sda_oe;
  assign \$208  = \$205  & \$207 ;
  assign \$209  = \$208  & tick;
  assign \$210  = tcount == 15'h61a7;
  assign expire = \$209  & \$210 ;
  always @(posedge clk)
    scl_f <= \$211 ;
  always @(posedge clk)
    scl_fcnt <= \$212 ;
  always @(posedge clk)
    sda_f <= \$213 ;
  always @(posedge clk)
    sda_fcnt <= \$214 ;
  always @(posedge clk)
    scl_p <= \$215 ;
  always @(posedge clk)
    sda_p <= \$216 ;
  always @(posedge clk)
    doorbell <= \$217 ;
  always @(posedge clk)
    timeout <= \$218 ;
  always @(posedge clk)
    pec_error <= \$219 ;
  always @(posedge clk)
    refused_write <= \$220 ;
  always @(posedge clk)
    tcount <= \$221 ;
  always @(posedge clk)
    phase <= \$222 ;
  always @(posedge clk)
    sda_oe <= \$223 ;
  always @(posedge clk)
    armed <= \$224 ;
  always @(posedge clk)
    cmd_valid <= \$225 ;
  always @(posedge clk)
    doorbell_value <= \$226 ;
  always @(posedge clk)
    crc <= \$227 ;
  always @(posedge clk)
    sr_seen <= \$228 ;
  always @(posedge clk)
    step <= \$229 ;
  always @(posedge clk)
    nbit <= \$230 ;
  always @(posedge clk)
    shift <= \$231 ;
  always @(posedge clk)
    ack <= \$232 ;
  always @(posedge clk)
    snap <= \$233 ;
  always @(posedge clk)
    txidx <= \$234 ;
  always @(posedge clk)
    cmd <= \$235 ;
  always @(posedge clk)
    dcount <= \$236 ;
  always @(posedge clk)
    wbuf <= \$237 ;
  always @(posedge clk)
    host_ack <= \$238 ;
  always @(posedge clk)
    txsh <= \$239 ;
  \smbus.scl_sync  scl_sync (
    .clk(clk),
    .rst(rst),
    .scl_i(scl_i),
    .stage1(scl_s)
  );
  \smbus.sda_sync  sda_sync (
    .clk(clk),
    .rst(rst),
    .sda_i(sda_i),
    .stage1(sda_s)
  );
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$211  = scl_f;
    if (\$1 ) begin
      if (\$2 ) begin
        \$211  = scl_s;
      end
    end
    if (rst) begin
      \$211  = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    if (\$1 ) begin
      (* full_case = 32'd1 *)
      if (\$2 ) begin
        \$212  = 2'h0;
      end else begin
        \$212  = \$3 [1:0];
      end
    end else begin
      \$212  = 2'h0;
    end
    if (rst) begin
      \$212  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$213  = sda_f;
    if (\$4 ) begin
      if (\$5 ) begin
        \$213  = sda_s;
      end
    end
    if (rst) begin
      \$213  = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    if (\$4 ) begin
      (* full_case = 32'd1 *)
      if (\$5 ) begin
        \$214  = 2'h0;
      end else begin
        \$214  = \$6 [1:0];
      end
    end else begin
      \$214  = 2'h0;
    end
    if (rst) begin
      \$214  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$215  = scl_f;
    if (rst) begin
      \$215  = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$216  = sda_f;
    if (rst) begin
      \$216  = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$217  = 1'h0;
    if (expire) begin
    end else if (stop) begin
      if (\$24 ) begin
        \$217  = 1'h1;
      end
    end
    if (rst) begin
      \$217  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$218  = 1'h0;
    if (expire) begin
      \$218  = 1'h1;
    end
    if (rst) begin
      \$218  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$219  = 1'h0;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          casez (step)
            3'h0:
                /* empty */;
            3'h1:
                /* empty */;
            3'h2:
                /* empty */;
            3'h3:
                /* empty */;
            3'h4:
                (* full_case = 32'd1 *)
                if (\$43 ) begin
                end else begin
                  \$219  = 1'h1;
                end
          endcase
        end
      end
    end
    if (rst) begin
      \$219  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$220  = 1'h0;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          casez (step)
            3'h0:
                if (\$36 ) begin
                end else if (\$37 ) begin
                  if (sr_seen) begin
                    \$220  = 1'h1;
                  end
                end
            3'h1:
                /* empty */;
            3'h2:
                (* full_case = 32'd1 *)
                if (\$40 ) begin
                end else begin
                  \$220  = 1'h1;
                end
          endcase
        end
      end
    end
    if (rst) begin
      \$220  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$221  = tcount;
    if (\$11 ) begin
      \$221  = 15'h0000;
    end else if (\$13 ) begin
      \$221  = \$14 [14:0];
    end
    if (expire) begin
      \$221  = 15'h0000;
    end
    if (rst) begin
      \$221  = 15'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$222  = phase;
    if (expire) begin
      \$222  = 2'h0;
    end else if (stop) begin
      \$222  = 2'h0;
    end else if (start) begin
      \$222  = 2'h1;
    end else if (\$18 ) begin
    end else if (\$22 ) begin
      (* full_case = 32'd1 *)
      if (\$45 ) begin
        if (\$46 ) begin
        end else if (\$47 ) begin
          if (\$48 ) begin
            \$222  = 2'h3;
          end else if (\$49 ) begin
            \$222  = 2'h2;
          end
        end
      end else begin
        if (\$101 ) begin
        end else if (\$102 ) begin
        end else if (\$103 ) begin
          (* full_case = 32'd1 *)
          if (host_ack) begin
            \$222  = 2'h2;
          end else begin
            \$222  = 2'h3;
          end
        end
      end
    end
    if (rst) begin
      \$222  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$223  = sda_oe;
    if (expire) begin
      \$223  = 1'h0;
    end else if (stop) begin
      \$223  = 1'h0;
    end else if (start) begin
      \$223  = 1'h0;
    end else if (\$18 ) begin
    end else if (\$22 ) begin
      (* full_case = 32'd1 *)
      if (\$45 ) begin
        if (\$46 ) begin
          \$223  = ack;
        end else if (\$47 ) begin
          \$223  = 1'h0;
          if (\$48 ) begin
          end else if (\$49 ) begin
            \$223  = \$51 ;
          end
        end
      end else begin
        if (\$101 ) begin
          \$223  = \$104 ;
        end else if (\$102 ) begin
          \$223  = 1'h0;
        end else if (\$103 ) begin
          (* full_case = 32'd1 *)
          if (host_ack) begin
            \$223  = \$105 ;
          end else begin
            \$223  = 1'h0;
          end
        end
      end
    end
    if (rst) begin
      \$223  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$224  = armed;
    if (expire) begin
      \$224  = 1'h0;
    end else if (stop) begin
      \$224  = 1'h0;
    end else if (start) begin
      \$224  = 1'h0;
    end else if (\$18 ) begin
      if (\$31 ) begin
        \$224  = 1'h0;
      end
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          (* full_case = 32'd1 *)
          casez (step)
            3'h0:
                /* empty */;
            3'h1:
                /* empty */;
            3'h2:
                /* empty */;
            3'h3:
                /* empty */;
            3'h4:
                /* empty */;
            default:
                \$224  = 1'h0;
          endcase
        end
      end
    end else if (\$22 ) begin
      if (\$45 ) begin
        if (\$46 ) begin
        end else if (\$47 ) begin
          if (\$48 ) begin
          end else if (\$49 ) begin
          end else if (\$50 ) begin
            \$224  = 1'h1;
          end
        end
      end
    end
    if (rst) begin
      \$224  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$225  = cmd_valid;
    if (expire) begin
      \$225  = 1'h0;
    end else if (stop) begin
      \$225  = 1'h0;
    end else if (start) begin
      if (\$25 ) begin
        \$225  = 1'h0;
      end
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          casez (step)
            3'h0:
                /* empty */;
            3'h1:
                \$225  = 1'h1;
          endcase
        end
      end
    end
    if (rst) begin
      \$225  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$226  = doorbell_value;
    if (expire) begin
    end else if (stop) begin
      if (\$24 ) begin
        \$226  = wbuf;
      end
    end
    if (rst) begin
      \$226  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$227  = crc;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
      if (\$25 ) begin
        \$227  = 8'h00;
      end
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          casez (step)
            3'h0:
                if (\$36 ) begin
                end else if (\$37 ) begin
                  (* full_case = 32'd1 *)
                  if (sr_seen) begin
                  end else begin
                    \$227  = { \$204 , \$199 , \$194 , \$189 , \$184 , \$177 , \$170 , \$165  };
                  end
                end else if (cmd_valid) begin
                  \$227  = { \$204 , \$199 , \$194 , \$189 , \$184 , \$177 , \$170 , \$165  };
                end
            3'h1:
                \$227  = { \$204 , \$199 , \$194 , \$189 , \$184 , \$177 , \$170 , \$165  };
            3'h2:
                if (\$40 ) begin
                  \$227  = { \$204 , \$199 , \$194 , \$189 , \$184 , \$177 , \$170 , \$165  };
                end
            3'h3:
                \$227  = { \$204 , \$199 , \$194 , \$189 , \$184 , \$177 , \$170 , \$165  };
          endcase
        end
      end
    end else if (\$22 ) begin
      (* full_case = 32'd1 *)
      if (\$45 ) begin
        if (\$46 ) begin
        end else if (\$47 ) begin
          if (\$48 ) begin
          end else if (\$49 ) begin
            \$227  = { \$95 , \$90 , \$85 , \$80 , \$75 , \$68 , \$61 , \$56  };
          end
        end
      end else begin
        if (\$101 ) begin
        end else if (\$102 ) begin
        end else if (\$103 ) begin
          if (host_ack) begin
            \$227  = { \$149 , \$144 , \$139 , \$134 , \$129 , \$122 , \$115 , \$110  };
          end
        end
      end
    end
    if (rst) begin
      \$227  = 8'h00;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$228  = sr_seen;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
      (* full_case = 32'd1 *)
      if (\$25 ) begin
        \$228  = 1'h0;
      end else begin
        \$228  = 1'h1;
      end
    end
    if (rst) begin
      \$228  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$229  = step;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
      \$229  = 3'h0;
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          casez (step)
            3'h0:
                if (\$36 ) begin
                end else if (\$37 ) begin
                  (* full_case = 32'd1 *)
                  if (sr_seen) begin
                  end else begin
                    \$229  = 3'h1;
                  end
                end else if (cmd_valid) begin
                  \$229  = 3'h6;
                end
            3'h1:
                \$229  = 3'h2;
            3'h2:
                if (\$40 ) begin
                  \$229  = 3'h3;
                end
            3'h3:
                if (\$42 ) begin
                  \$229  = 3'h4;
                end
            3'h4:
                if (\$43 ) begin
                  \$229  = 3'h5;
                end
          endcase
        end
      end
    end
    if (rst) begin
      \$229  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$230  = nbit;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
      \$230  = 4'h0;
    end else if (\$18 ) begin
      \$230  = \$28 [3:0];
    end else if (\$22 ) begin
      (* full_case = 32'd1 *)
      if (\$45 ) begin
        if (\$46 ) begin
        end else if (\$47 ) begin
          \$230  = 4'h0;
        end
      end else begin
        if (\$101 ) begin
        end else if (\$102 ) begin
        end else if (\$103 ) begin
          \$230  = 4'h0;
        end
      end
    end
    if (rst) begin
      \$230  = 4'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$231  = shift;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
          \$231  = { shift[6:0], sda_f };
        end else if (\$35 ) begin
          \$231  = { shift[6:0], sda_f };
        end
      end
    end
    if (rst) begin
      \$231  = 8'h00;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$232  = ack;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          (* full_case = 32'd1 *)
          casez (step)
            3'h0:
                (* full_case = 32'd1 *)
                if (\$36 ) begin
                  \$232  = 1'h0;
                end else if (\$37 ) begin
                  (* full_case = 32'd1 *)
                  if (sr_seen) begin
                    \$232  = 1'h0;
                  end else begin
                    \$232  = 1'h1;
                  end
                end else if (cmd_valid) begin
                  \$232  = 1'h1;
                end else begin
                  \$232  = 1'h0;
                end
            3'h1:
                \$232  = 1'h1;
            3'h2:
                (* full_case = 32'd1 *)
                if (\$40 ) begin
                  \$232  = 1'h1;
                end else begin
                  \$232  = 1'h0;
                end
            3'h3:
                \$232  = 1'h1;
            3'h4:
                (* full_case = 32'd1 *)
                if (\$43 ) begin
                  \$232  = 1'h1;
                end else begin
                  \$232  = 1'h0;
                end
            default:
                \$232  = 1'h0;
          endcase
        end
      end
    end
    if (rst) begin
      \$232  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$233  = snap;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          casez (step)
            3'h0:
                if (\$36 ) begin
                end else if (\$37 ) begin
                end else if (cmd_valid) begin
                  \$233  = csr_rdata;
                end
          endcase
        end
      end
    end
    if (rst) begin
      \$233  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$234  = txidx;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          casez (step)
            3'h0:
                if (\$36 ) begin
                end else if (\$37 ) begin
                end else if (cmd_valid) begin
                  \$234  = 3'h0;
                end
          endcase
        end
      end
    end else if (\$22 ) begin
      (* full_case = 32'd1 *)
      if (\$45 ) begin
        if (\$46 ) begin
        end else if (\$47 ) begin
          if (\$48 ) begin
          end else if (\$49 ) begin
            \$234  = \$98 [2:0];
          end
        end
      end else begin
        if (\$101 ) begin
        end else if (\$102 ) begin
        end else if (\$103 ) begin
          if (host_ack) begin
            \$234  = \$152 [2:0];
          end
        end
      end
    end
    if (rst) begin
      \$234  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$235  = cmd;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          casez (step)
            3'h0:
                /* empty */;
            3'h1:
                \$235  = { shift[6:0], sda_f };
          endcase
        end
      end
    end
    if (rst) begin
      \$235  = 8'h00;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$236  = dcount;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          casez (step)
            3'h0:
                /* empty */;
            3'h1:
                /* empty */;
            3'h2:
                if (\$40 ) begin
                  \$236  = 2'h0;
                end
            3'h3:
                \$236  = \$41 [1:0];
          endcase
        end
      end
    end
    if (rst) begin
      \$236  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$237  = wbuf;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
      if (\$32 ) begin
        if (\$34 ) begin
        end else if (\$35 ) begin
          casez (step)
            3'h0:
                /* empty */;
            3'h1:
                /* empty */;
            3'h2:
                /* empty */;
            3'h3:
                (* full_case = 32'd1 *)
                casez (dcount)
                  2'h0:
                      \$237 [7:0] = { shift[6:0], sda_f };
                  2'h1:
                      \$237 [15:8] = { shift[6:0], sda_f };
                  2'h2:
                      \$237 [23:16] = { shift[6:0], sda_f };
                  2'h3:
                      \$237 [31:24] = { shift[6:0], sda_f };
                endcase
          endcase
        end
      end
    end
    if (rst) begin
      \$237  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$238  = host_ack;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
      if (\$32 ) begin
      end else if (\$33 ) begin
        \$238  = \$44 ;
      end
    end
    if (rst) begin
      \$238  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$239  = txsh;
    if (expire) begin
    end else if (stop) begin
    end else if (start) begin
    end else if (\$18 ) begin
    end else if (\$22 ) begin
      (* full_case = 32'd1 *)
      if (\$45 ) begin
        if (\$46 ) begin
        end else if (\$47 ) begin
          if (\$48 ) begin
          end else if (\$49 ) begin
            \$239  = tx_byte;
          end
        end
      end else begin
        if (\$101 ) begin
          \$239  = { txsh[6:0], 1'h0 };
        end else if (\$102 ) begin
        end else if (\$103 ) begin
          if (host_ack) begin
            \$239  = tx_byte;
          end
        end
      end
    end
    if (rst) begin
      \$239  = 8'h00;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (txidx)
      3'h0:
          tx_byte = 8'h04;
      3'h1:
          tx_byte = snap[7:0];
      3'h2:
          tx_byte = snap[15:8];
      3'h3:
          tx_byte = snap[23:16];
      3'h4:
          tx_byte = snap[31:24];
      3'h5:
          tx_byte = crc;
      default:
          tx_byte = 8'hff;
    endcase
  end
  assign \byte  = { shift[6:0], sda_f };
  assign crc_next = { \$204 , \$199 , \$194 , \$189 , \$184 , \$177 , \$170 , \$165  };
  assign scl_oe = 1'h0;
  assign csr_addr = { 2'h0, cmd, 2'h0 };
endmodule

module \smbus.scl_sync (clk, rst, stage1, scl_i);
  input clk;
  wire clk;
  input rst;
  wire rst;
  input scl_i;
  wire scl_i;
  (* init = 1'h1 *)
  wire scl_s;
  reg stage0 = 1'h1;
  output stage1;
  reg stage1 = 1'h1;
  always @(posedge clk)
    stage0 <= scl_i;
  always @(posedge clk)
    stage1 <= stage0;
  assign scl_s = stage1;
endmodule

module \smbus.sda_sync (clk, rst, stage1, sda_i);
  input clk;
  wire clk;
  input rst;
  wire rst;
  input sda_i;
  wire sda_i;
  (* init = 1'h1 *)
  wire sda_s;
  reg stage0 = 1'h1;
  output stage1;
  reg stage1 = 1'h1;
  always @(posedge clk)
    stage0 <= sda_i;
  always @(posedge clk)
    stage1 <= stage0;
  assign sda_s = stage1;
endmodule