// Formal properties for monotonic_counter. P8: the edition (here the time and anti-rollback
// reference) only moves forward. Reset is assumed low: a power loss is the hwm's job (m_P8_hwm_floor).
//
// The register's only decreasing step is the wrap of an increment at 2^64-1 (2^64 microseconds,
// about 584,000 years). The prove task carries that one step as an escape clause, so P8 holds
// modulo it; the -D WRAP task asserts the strict form with no escape clause and is written to find
// that step.
//
// The wrap is reached without fighting the register's init value (0): a free load_hwm strobe loads
// the free input hwm -- the solver sets hwm = 2^64-1 -- and the following inc wraps it to 0. The
// strict property is broken on that second step, at a depth of two. (An initial assume on value would
// contradict the $initstate and leave no reachable trace, so the task would be vacuous; the load
// path is the reachable way to 2^64-1.)
reg f_init = 1'b1;
always @(posedge clk) f_init <= 1'b0;
always @* assume (!rst);

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
  m_P8_inc_by_one:      assert (!(p_inc && !p_load) || value == p_value + 64'd1);
  m_P8_dec_req_no_effect: assert (p_load || p_inc || value == p_value);
`endif
end
always @* m_P8_dec_refused_flag: assert (refused == dec_req);
