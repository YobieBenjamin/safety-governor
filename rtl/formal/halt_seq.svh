// Formal properties for halt_seq (the rung and the levers).
// P5: halt is absorbing without an authorized clear. P6: fail closed, the loop closes and the rung
// reaches RUN only when armed. P7/P13: the levers are applied in every rung but RUN, so nothing
// passes while halted. The commit-point hold is the same register: the rung does not leave
// HALT/SAFE except through `clear`, which the mailbox only raises on a signed CLEAR.
localparam HI = 0, RUN = 1, THR = 2, HLT = 3, SAF = 4;
localparam C_NONE = 0, C_LOOP = 1, C_LOCAL = 2, C_TAMPER = 3, C_COMMAND = 4;

reg f_init = 1'b1;
always @(posedge clk) f_init <= 1'b0;
always @* assume (!rst);

reg [2:0] p_state, p_cause;
reg p_sw, p_clear, p_tamper, p_loop_lost, p_cmd_halt, p_hb_ok, p_loop_sense;
always @(posedge clk) begin
  p_state <= state; p_cause <= cause; p_sw <= switch_open;
  p_clear <= clear; p_tamper <= tamper; p_loop_lost <= loop_lost; p_cmd_halt <= cmd_halt;
  p_hb_ok <= hb_ok; p_loop_sense <= loop_sense;
end

wire p_in_run = (p_state == RUN) || (p_state == THR);
wire p_cleared = p_clear && (p_state != HI);
wire p_hard_cause = p_tamper || (p_loop_lost && p_in_run) || (p_cmd_halt && p_state != SAF);

// invariants of the register state
always @* begin
  h_inv_state_in_range: assert (state <= SAF);
  h_inv_cause_in_range: assert (cause <= C_COMMAND);
  h_P6_inv_open_cause_keeps_switch_open: assert (!(cause == C_LOOP || cause == C_TAMPER || cause == C_COMMAND) || switch_open);
  h_P6_inv_run_means_armed: assert (state != RUN || (cause == C_NONE && !switch_open));
  h_boot_state: assert (!f_init || (state == HI && switch_open && cause == C_NONE && pwrbrk && perst && !pwr_en && ports_closed));
  // levers follow the rung exactly, and every rung but RUN applies the brake and closes the ports
  h_P7_pwrbrk:  assert (pwrbrk == (state != RUN));
  h_P7_perst:   assert (perst == (state == HI || state == HLT || state == SAF));
  h_P7_pwr_en:  assert (pwr_en == (state != HI && state != SAF));
  h_P13_ports:  assert (ports_closed == (state != RUN));
  h_P13_halted_means_levers: assert (!(state == HLT || state == SAF) || (pwrbrk && perst && ports_closed));
end

// transitions
always @(posedge clk) if (!f_init) begin
  h_P5_no_descent_without_clear: assert (state >= p_state || (p_cleared && state == HI && cause == C_NONE));
  h_P5_halt_absorbing:  assert (!(p_state == HLT && !p_cleared) || (state == HLT || state == SAF));
  h_P5_safe_absorbing:  assert (!(p_state == SAF && !p_cleared) || state == SAF);
  h_P5_throttle_never_relaxes: assert (!(p_state == THR && !p_cleared) || state >= THR);
  h_P6_enter_run_only_armed: assert (!(state == RUN && p_state != RUN) ||
                                     (p_state == HI && p_cause == C_NONE && p_hb_ok && p_loop_sense && !p_tamper && !p_cmd_halt));
  h_P6_hard_cause_opens_loop_and_halts: assert (!(p_hard_cause && !p_cleared) || (state >= HLT && switch_open));
  h_P6_tamper_is_safe: assert (!(p_tamper && !p_cleared) || (state == SAF && cause == C_TAMPER && switch_open));
  h_P6_switch_closes_only_armed: assert (!(p_sw && !switch_open) ||
                                         (p_state == HI && p_cause == C_NONE && p_hb_ok && !p_tamper && !p_cmd_halt));
  h_P6_clear_does_not_close_switch: assert (!p_cleared || (switch_open == p_sw && state == HI && cause == C_NONE));
end
