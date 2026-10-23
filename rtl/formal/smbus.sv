// L7, smbus: properties proven on the generated Verilog (rtl/gen/smbus.v).
// Run: python -m rtl.formal. Bounded check, then k-induction: the assertions hold in every reachable state.
//
// The pins (scl_i, sda_i), the tick and the CSR read data are completely free: any waveform at all, glitches,
// half bytes, starts in the middle of bits. The harness carries its own bus monitor, written from the SMBus
// framing and not from the target's code: it watches the target's filtered lines, counts clocks, assembles bytes,
// computes the PEC, and knows the one transaction that may ring the doorbell:
//   S, addr+W, 0x40, count 4, d0 d1 d2 d3, PEC over all of them, P   (no repeated start, nothing after the PEC)
// The safety properties:
//   P1 the doorbell fires only on a STOP that ends exactly that transaction with a correct PEC
//      (so a bad PEC, a wrong command code, a wrong count, a truncated or overlong frame, a repeated start, a
//      wrong address or a timed-out transaction never commit a write)
//   P2 the doorbell carries the four data bytes of that transaction, little-endian
//   P3 the target never pulls SCL (no clock stretching: tLOW:SEXT is zero)
//   P4 the target never drives SDA outside a transaction
//   P5 a transaction whose SCL low (or our own SDA hold) lasts 25,000 ticks is abandoned on that tick
//   P6 the only address the target ever presents to the core is a word-aligned read inside the CSR window
// The rest are the bookkeeping that ties the target's state to the monitor's, which k-induction needs.
module smbus_props(input clk, input rst, input scl_i, sda_i, tick, input [31:0] csr_rdata);
  wire ack, armed, cmd_valid, doorbell, host_ack, pec_error, refused_write, scl_f, scl_oe, scl_p, sda_f, sda_oe, sda_p,
       sr_seen, timeout;
  wire [7:0] cmd, crc, shift, txsh;
  wire [11:0] csr_addr;
  wire [1:0] dcount, phase;
  wire [31:0] doorbell_value, snap, wbuf;
  wire [3:0] nbit;
  wire [2:0] step, txidx;
  wire [14:0] tcount;
  smbus dut(.clk(clk), .rst(rst), .scl_i(scl_i), .sda_i(sda_i), .tick(tick), .csr_rdata(csr_rdata),
    .ack(ack), .armed(armed), .cmd(cmd), .cmd_valid(cmd_valid), .crc(crc), .csr_addr(csr_addr), .dcount(dcount),
    .doorbell(doorbell), .doorbell_value(doorbell_value), .host_ack(host_ack), .nbit(nbit), .pec_error(pec_error),
    .phase(phase), .refused_write(refused_write), .scl_f(scl_f), .scl_oe(scl_oe), .scl_p(scl_p), .sda_f(sda_f),
    .sda_oe(sda_oe), .sda_p(sda_p), .shift(shift), .snap(snap), .sr_seen(sr_seen), .step(step), .tcount(tcount),
    .timeout(timeout), .txidx(txidx), .txsh(txsh), .wbuf(wbuf));

  localparam [6:0] ADDR = 7'h58;
  localparam T = 25000;
  localparam X_ADDR = 0, X_CMD = 1, X_COUNT = 2, X_DATA = 3, X_PEC = 4, X_EXTRA = 5;

  function [7:0] crc8(input [7:0] c, input [7:0] b);
    integer i; reg [7:0] v;
    begin
      v = c ^ b;
      for (i = 0; i < 8; i = i + 1) v = v[7] ? ((v << 1) ^ 8'h07) : (v << 1);
      crc8 = v;
    end
  endfunction

  reg init = 1;
  always @(posedge clk) init <= 0;

  // ---- the monitor
  reg mp_scl = 1, mp_sda = 1, m_busy = 0, m_sr = 0, m_ok = 0;
  reg [3:0] m_bits = 0, m_n = 0;
  reg [7:0] m_sh = 0, m_crc = 0;
  reg [31:0] m_d = 0;
  reg [14:0] m_tc = 0;
  wire m_start = scl_f & mp_scl & mp_sda & ~sda_f;
  wire m_stop  = scl_f & mp_scl & ~mp_sda & sda_f;
  wire m_rise  = scl_f & ~mp_scl;
  wire m_fall  = ~scl_f & mp_scl;
  wire [7:0] m_byte = {m_sh[6:0], sda_f};
  wire m_hold = m_busy & (~scl_f | sda_oe);
  wire m_expire = m_hold & tick & (m_tc == T - 1);
  wire m_commit_ok = m_busy & ~m_sr & (m_n == 8) & m_ok & (m_bits <= 1);

  always @(posedge clk) begin
    if (rst) begin
      mp_scl <= 1; mp_sda <= 1; m_busy <= 0; m_sr <= 0; m_ok <= 0; m_bits <= 0; m_n <= 0; m_sh <= 0; m_crc <= 0;
      m_d <= 0; m_tc <= 0;
    end else begin
      mp_scl <= scl_f; mp_sda <= sda_f;
      if (!m_hold) m_tc <= 0; else if (tick && !m_expire) m_tc <= m_tc + 1;
      if (m_expire) begin
        m_busy <= 0; m_tc <= 0;
      end else if (m_stop) begin
        m_busy <= 0;
      end else if (m_start) begin
        if (!m_busy) begin m_sr <= 0; m_n <= 0; m_ok <= 1; m_crc <= 0; end
        else m_sr <= 1;
        m_busy <= 1; m_bits <= 0;
      end else if (m_rise && m_busy) begin
        m_bits <= (m_bits == 9) ? 9 : m_bits + 1;
        if (m_bits < 7) m_sh <= m_byte;
        else if (m_bits == 7) begin
          m_sh <= m_byte;
          m_n <= (m_n == 15) ? 15 : m_n + 1;
          m_crc <= crc8(m_crc, m_byte);
          case (m_n)
            0: m_ok <= m_ok & (m_byte == {ADDR, 1'b0});
            1: m_ok <= m_ok & (m_byte == 8'h40);
            2: m_ok <= m_ok & (m_byte == 8'h04);
            3: m_d[7:0] <= m_byte;
            4: m_d[15:8] <= m_byte;
            5: m_d[23:16] <= m_byte;
            6: m_d[31:24] <= m_byte;
            7: m_ok <= m_ok & (m_byte == m_crc);
            default: m_ok <= 0;
          endcase
        end
      end else if (m_fall && m_busy && m_bits == 9) m_bits <= 0;
    end
  end

  always @(*) begin
    assume(!rst || init);
    assume(init == rst || !init);
    if (!init) begin
      // P3, P4, P6
      assert(!scl_oe);
      if (!m_busy) assert(!sda_oe);
      assert(csr_addr[1:0] == 0 && csr_addr[11:10] == 0);
      // bookkeeping: the target and the monitor agree on the bus
      assert(mp_scl == scl_p && mp_sda == sda_p);
      assert((phase != 0) == m_busy);
      assert(tcount == m_tc && m_tc < T);
      if (m_busy) assert(sr_seen == m_sr);
      assert(nbit <= 9 && m_bits <= 9 && step <= 6);
      if (phase != 0 && sr_seen) assert(step == X_ADDR || step == 6);
      if (phase == 2) assert(step == 6);
      if (phase == 1 || phase == 2) assert(nbit == m_bits);
      // while receiving, the bits clocked in so far in this frame are the same bits
      if (phase == 1 && nbit >= 1) assert(shift[0] == m_sh[0]);
      if (phase == 1 && nbit >= 2) assert(shift[1:0] == m_sh[1:0]);
      if (phase == 1 && nbit >= 3) assert(shift[2:0] == m_sh[2:0]);
      if (phase == 1 && nbit >= 4) assert(shift[3:0] == m_sh[3:0]);
      if (phase == 1 && nbit >= 5) assert(shift[4:0] == m_sh[4:0]);
      if (phase == 1 && nbit >= 6) assert(shift[5:0] == m_sh[5:0]);
      if (phase == 1 && nbit >= 7) assert(shift[6:0] == m_sh[6:0]);
      // an armed write is exactly the doorbell transaction, complete, with its data
      if (armed) assert(phase == 1 && step == X_EXTRA && !sr_seen && m_n == 8 && m_ok && m_bits <= 1 && wbuf == m_d);
      // the write path, byte by byte (a NACKed byte sends the target to WAIT and is not tracked)
      if (phase == 1 && !sr_seen && (nbit < 8 || ack)) begin
        if (step == X_ADDR)  assert(m_n == 0 && m_ok && crc == m_crc);
        if (step == X_CMD)   assert(m_n == 1 && m_ok && crc == m_crc);
        if (step == X_COUNT) assert(m_n == 2 && (m_ok == (cmd == 8'h40)) && crc == m_crc);
        if (step == X_DATA)  begin
          assert(m_n == 3 + dcount && m_ok && crc == m_crc);
          if (dcount > 0) assert(wbuf[7:0] == m_d[7:0]);
          if (dcount > 1) assert(wbuf[15:8] == m_d[15:8]);
          if (dcount > 2) assert(wbuf[23:16] == m_d[23:16]);
        end
        if (step == X_PEC)   assert(m_n == 7 && m_ok && crc == m_crc && wbuf == m_d);
        if (step == X_EXTRA) assert(m_n == 8 && m_ok && wbuf == m_d);
      end
    end
  end

  always @(posedge clk) if (!init && !$past(init) && !$past(rst)) begin
    // P1: the doorbell rings only on the STOP of the one well-formed, PEC-correct doorbell write, never on a
    // transaction the timeout already killed
    if (doorbell) assert($past(m_stop) && $past(m_commit_ok) && !$past(m_expire));
    // P2: and it carries that write's bytes
    if (doorbell) assert(doorbell_value == $past(m_d));
    // P5: the timeout fires on the tick the monitor says it must, and only then
    assert(timeout == $past(m_expire));
  end
endmodule
