// Formal properties for monotonic_counter. P8: the edition (here the time and anti-rollback
// reference) only moves forward. Reset is assumed low: a power loss is the hwm's job (m_P8_hwm_floor).
// With -D WRAP the counter starts at 2^64-1 and the strict property is asserted: the increment wraps.
reg f_init = 1'b1;
always @(posedge clk) f_init <= 1'b0;
always @* assume (!rst);
`ifdef WRAP
initial assume (value == 64'hFFFFFFFFFFFFFFFF);
`endif

reg [63:0] p_value, p_hwm;
reg p_load, p_inc;
always @(posedge clk) begin p_value <= value; p_hwm <= hwm; p_load <= load_hwm; p_inc <= inc; end

always @(posedge clk) if (!f_init) begin
`ifdef WRAP
  m_P8_never_decreases_strict: assert (value >= p_value);
`else
  // the one exception is the wrap of an increment at 2^64-1 (2^64 microseconds, about 584,000 years)
  m_P8_never_decreases: assert (value >= p_value || (p_inc && !p_load && p_value == 64'hFFFFFFFFFFFFFFFF));
  m_P8_hwm_floor:       assert (!p_load || (value >= p_hwm && value >= p_value));
  m_inc_by_one:         assert (!(p_inc && !p_load) || value == p_value + 64'd1);
  m_dec_req_no_effect:  assert (p_load || p_inc || value == p_value);
`endif
end
always @* m_dec_refused_flag: assert (refused == dec_req);
