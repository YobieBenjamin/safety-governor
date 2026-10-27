
(* top =  1  *)
module governor_core(doorbell, cause_fw, loop_sense, tick, sample, mono_hwm, mono_load_hwm, mono_dec_req, meas0_extend, meas0_data, meas0_hash_done, meas0_hash_out, meas1_extend, meas1_data, meas1_hash_done, meas1_hash_out, epoch_commit, epoch_quorum_ok, epoch_new_epoch, epoch_host_wr, epoch_host_data
, life_fuse_state, life_load, life_advance, life_advance_to, life_debug_req, tickets_query, tickets_burn, tickets_id_in, hb_hb_valid, hb_window, halt_tamper, halt_cmd_halt, halt_cmd_throttle, halt_local_trip, halt_clear, halt_cmd_exclude, meter_slot, meter_add_tokens, meter_add_cycles, meter_add_in, meter_add_out
, meter_strobe, mbox_frame_seq, mbox_key_slot, mbox_cmd, mbox_signed_cmd, mbox_epoch_match, mbox_epoch_exempt, mbox_needs_run, mbox_sig_done, mbox_sig_ok, alarms_set_mask, alarms_clear_mask, alarms_clear_authorized, cap_nvswitch_ins, cap_nvswitch_ins_point, cap_nvswitch_ins_peer, cap_nvswitch_ins_dir, cap_nvswitch_ins_budget, cap_nvswitch_ins_expiry, cap_nvswitch_ins_epoch_tag, cap_nvswitch_mac_ok
, cap_nvswitch_lk, cap_nvswitch_lk_point, cap_nvswitch_lk_peer, cap_nvswitch_lk_dir, cap_nvswitch_lk_bytes, cap_pcie_ins, cap_pcie_ins_point, cap_pcie_ins_peer, cap_pcie_ins_dir, cap_pcie_ins_budget, cap_pcie_ins_expiry, cap_pcie_ins_epoch_tag, cap_pcie_mac_ok, cap_pcie_lk, cap_pcie_lk_point, cap_pcie_lk_peer, cap_pcie_lk_dir, cap_pcie_lk_bytes, cap_dpu_ins, cap_dpu_ins_point, cap_dpu_ins_peer
, cap_dpu_ins_dir, cap_dpu_ins_budget, cap_dpu_ins_expiry, cap_dpu_ins_epoch_tag, cap_dpu_mac_ok, cap_dpu_lk, cap_dpu_lk_point, cap_dpu_lk_peer, cap_dpu_lk_dir, cap_dpu_lk_bytes, cap_storage_ins, cap_storage_ins_point, cap_storage_ins_peer, cap_storage_ins_dir, cap_storage_ins_budget, cap_storage_ins_expiry, cap_storage_ins_epoch_tag, cap_storage_mac_ok, cap_storage_lk, cap_storage_lk_point, cap_storage_lk_peer
, cap_storage_lk_dir, cap_storage_lk_bytes, clk, rst, csr_rdata, pwrbrk_n, perst_n, pwr_en, loop_out_open, tick_ms, mono_refused, meas0_hash_req, meas0_hash_in, meas1_hash_req, meas1_hash_in, life_debug_grant, tickets_seen, tickets_burned, tickets_full, mbox_verify_req, mbox_dispatch
, mbox_cmd_out, cap_nvswitch_ins_ok, cap_nvswitch_allow, cap_nvswitch_reason, cap_pcie_ins_ok, cap_pcie_allow, cap_pcie_reason, cap_dpu_ins_ok, cap_dpu_allow, cap_dpu_reason, cap_storage_ins_ok, cap_storage_allow, cap_storage_reason, csr_addr);
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
  wire \$33 ;
  wire \$34 ;
  wire \$35 ;
  wire [31:0] \$36 ;
  wire [10:0] \$37 ;
  reg [9:0] \$38 ;
  wire \$4 ;
  wire [31:0] \$5 ;
  wire [31:0] \$6 ;
  wire [12:0] \$7 ;
  wire \$8 ;
  wire \$9 ;
  wire [31:0] alarms_alarms;
  input alarms_clear_authorized;
  wire alarms_clear_authorized;
  input [31:0] alarms_clear_mask;
  wire [31:0] alarms_clear_mask;
  wire [31:0] alarms_hw_set;
  input [31:0] alarms_set_mask;
  wire [31:0] alarms_set_mask;
  output cap_dpu_allow;
  wire cap_dpu_allow;
  wire cap_dpu_clear_all;
  wire [15:0] cap_dpu_epoch_tag;
  input cap_dpu_ins;
  wire cap_dpu_ins;
  input [23:0] cap_dpu_ins_budget;
  wire [23:0] cap_dpu_ins_budget;
  input [1:0] cap_dpu_ins_dir;
  wire [1:0] cap_dpu_ins_dir;
  input [15:0] cap_dpu_ins_epoch_tag;
  wire [15:0] cap_dpu_ins_epoch_tag;
  input [31:0] cap_dpu_ins_expiry;
  wire [31:0] cap_dpu_ins_expiry;
  output cap_dpu_ins_ok;
  wire cap_dpu_ins_ok;
  input [15:0] cap_dpu_ins_peer;
  wire [15:0] cap_dpu_ins_peer;
  input [2:0] cap_dpu_ins_point;
  wire [2:0] cap_dpu_ins_point;
  input cap_dpu_lk;
  wire cap_dpu_lk;
  input [23:0] cap_dpu_lk_bytes;
  wire [23:0] cap_dpu_lk_bytes;
  input [1:0] cap_dpu_lk_dir;
  wire [1:0] cap_dpu_lk_dir;
  input [15:0] cap_dpu_lk_peer;
  wire [15:0] cap_dpu_lk_peer;
  input [2:0] cap_dpu_lk_point;
  wire [2:0] cap_dpu_lk_point;
  input cap_dpu_mac_ok;
  wire cap_dpu_mac_ok;
  wire [31:0] cap_dpu_now;
  output [2:0] cap_dpu_reason;
  wire [2:0] cap_dpu_reason;
  output cap_nvswitch_allow;
  wire cap_nvswitch_allow;
  wire cap_nvswitch_clear_all;
  wire [15:0] cap_nvswitch_epoch_tag;
  input cap_nvswitch_ins;
  wire cap_nvswitch_ins;
  input [23:0] cap_nvswitch_ins_budget;
  wire [23:0] cap_nvswitch_ins_budget;
  input [1:0] cap_nvswitch_ins_dir;
  wire [1:0] cap_nvswitch_ins_dir;
  input [15:0] cap_nvswitch_ins_epoch_tag;
  wire [15:0] cap_nvswitch_ins_epoch_tag;
  input [31:0] cap_nvswitch_ins_expiry;
  wire [31:0] cap_nvswitch_ins_expiry;
  output cap_nvswitch_ins_ok;
  wire cap_nvswitch_ins_ok;
  input [15:0] cap_nvswitch_ins_peer;
  wire [15:0] cap_nvswitch_ins_peer;
  input [2:0] cap_nvswitch_ins_point;
  wire [2:0] cap_nvswitch_ins_point;
  input cap_nvswitch_lk;
  wire cap_nvswitch_lk;
  input [23:0] cap_nvswitch_lk_bytes;
  wire [23:0] cap_nvswitch_lk_bytes;
  input [1:0] cap_nvswitch_lk_dir;
  wire [1:0] cap_nvswitch_lk_dir;
  input [15:0] cap_nvswitch_lk_peer;
  wire [15:0] cap_nvswitch_lk_peer;
  input [2:0] cap_nvswitch_lk_point;
  wire [2:0] cap_nvswitch_lk_point;
  input cap_nvswitch_mac_ok;
  wire cap_nvswitch_mac_ok;
  wire [31:0] cap_nvswitch_now;
  output [2:0] cap_nvswitch_reason;
  wire [2:0] cap_nvswitch_reason;
  output cap_pcie_allow;
  wire cap_pcie_allow;
  wire cap_pcie_clear_all;
  wire [15:0] cap_pcie_epoch_tag;
  input cap_pcie_ins;
  wire cap_pcie_ins;
  input [23:0] cap_pcie_ins_budget;
  wire [23:0] cap_pcie_ins_budget;
  input [1:0] cap_pcie_ins_dir;
  wire [1:0] cap_pcie_ins_dir;
  input [15:0] cap_pcie_ins_epoch_tag;
  wire [15:0] cap_pcie_ins_epoch_tag;
  input [31:0] cap_pcie_ins_expiry;
  wire [31:0] cap_pcie_ins_expiry;
  output cap_pcie_ins_ok;
  wire cap_pcie_ins_ok;
  input [15:0] cap_pcie_ins_peer;
  wire [15:0] cap_pcie_ins_peer;
  input [2:0] cap_pcie_ins_point;
  wire [2:0] cap_pcie_ins_point;
  input cap_pcie_lk;
  wire cap_pcie_lk;
  input [23:0] cap_pcie_lk_bytes;
  wire [23:0] cap_pcie_lk_bytes;
  input [1:0] cap_pcie_lk_dir;
  wire [1:0] cap_pcie_lk_dir;
  input [15:0] cap_pcie_lk_peer;
  wire [15:0] cap_pcie_lk_peer;
  input [2:0] cap_pcie_lk_point;
  wire [2:0] cap_pcie_lk_point;
  input cap_pcie_mac_ok;
  wire cap_pcie_mac_ok;
  wire [31:0] cap_pcie_now;
  output [2:0] cap_pcie_reason;
  wire [2:0] cap_pcie_reason;
  output cap_storage_allow;
  wire cap_storage_allow;
  wire cap_storage_clear_all;
  wire [15:0] cap_storage_epoch_tag;
  input cap_storage_ins;
  wire cap_storage_ins;
  input [23:0] cap_storage_ins_budget;
  wire [23:0] cap_storage_ins_budget;
  input [1:0] cap_storage_ins_dir;
  wire [1:0] cap_storage_ins_dir;
  input [15:0] cap_storage_ins_epoch_tag;
  wire [15:0] cap_storage_ins_epoch_tag;
  input [31:0] cap_storage_ins_expiry;
  wire [31:0] cap_storage_ins_expiry;
  output cap_storage_ins_ok;
  wire cap_storage_ins_ok;
  input [15:0] cap_storage_ins_peer;
  wire [15:0] cap_storage_ins_peer;
  input [2:0] cap_storage_ins_point;
  wire [2:0] cap_storage_ins_point;
  input cap_storage_lk;
  wire cap_storage_lk;
  input [23:0] cap_storage_lk_bytes;
  wire [23:0] cap_storage_lk_bytes;
  input [1:0] cap_storage_lk_dir;
  wire [1:0] cap_storage_lk_dir;
  input [15:0] cap_storage_lk_peer;
  wire [15:0] cap_storage_lk_peer;
  input [2:0] cap_storage_lk_point;
  wire [2:0] cap_storage_lk_point;
  input cap_storage_mac_ok;
  wire cap_storage_mac_ok;
  wire [31:0] cap_storage_now;
  output [2:0] cap_storage_reason;
  wire [2:0] cap_storage_reason;
  input [7:0] cause_fw;
  wire [7:0] cause_fw;
  input clk;
  wire clk;
  input [11:0] csr_addr;
  wire [11:0] csr_addr;
  output [31:0] csr_rdata;
  reg [31:0] csr_rdata;
  input doorbell;
  wire doorbell;
  input epoch_commit;
  wire epoch_commit;
  wire [255:0] epoch_epoch;
  wire [15:0] epoch_epoch_tag;
  input [255:0] epoch_host_data;
  wire [255:0] epoch_host_data;
  input epoch_host_wr;
  wire epoch_host_wr;
  input [255:0] epoch_new_epoch;
  wire [255:0] epoch_new_epoch;
  input epoch_quorum_ok;
  wire epoch_quorum_ok;
  wire [15:0] halt_boot_timer;
  wire [2:0] halt_cause;
  input halt_clear;
  wire halt_clear;
  wire halt_clear_authorized;
  input halt_cmd_exclude;
  wire halt_cmd_exclude;
  input halt_cmd_halt;
  wire halt_cmd_halt;
  input halt_cmd_throttle;
  wire halt_cmd_throttle;
  wire halt_excluded;
  wire halt_hb_expired;
  wire halt_hb_ok;
  input halt_local_trip;
  wire halt_local_trip;
  wire halt_loop_lost;
  wire halt_loop_sense;
  wire halt_no_first_hb;
  wire halt_perst;
  wire halt_ports_closed;
  wire halt_pwr_en;
  wire halt_pwrbrk;
  wire [2:0] halt_state;
  wire halt_switch_open;
  input halt_tamper;
  wire halt_tamper;
  wire halt_tick;
  wire hb_expired;
  input hb_hb_valid;
  wire hb_hb_valid;
  wire [31:0] hb_remaining;
  wire hb_tick;
  input [31:0] hb_window;
  wire [31:0] hb_window;
  input life_advance;
  wire life_advance;
  input [1:0] life_advance_to;
  wire [1:0] life_advance_to;
  output life_debug_grant;
  wire life_debug_grant;
  input life_debug_req;
  wire life_debug_req;
  input [1:0] life_fuse_state;
  wire [1:0] life_fuse_state;
  input life_load;
  wire life_load;
  wire [1:0] life_state;
  wire loop_lost;
  output loop_out_open;
  wire loop_out_open;
  wire \loop_out_open$148 ;
  input loop_sense;
  wire loop_sense;
  wire \loop_sense$145 ;
  input [7:0] mbox_cmd;
  wire [7:0] mbox_cmd;
  output [7:0] mbox_cmd_out;
  wire [7:0] mbox_cmd_out;
  output mbox_dispatch;
  wire mbox_dispatch;
  wire mbox_doorbell;
  wire mbox_epoch_advanced;
  input mbox_epoch_exempt;
  wire mbox_epoch_exempt;
  input mbox_epoch_match;
  wire mbox_epoch_match;
  input [63:0] mbox_frame_seq;
  wire [63:0] mbox_frame_seq;
  input [2:0] mbox_key_slot;
  wire [2:0] mbox_key_slot;
  input mbox_needs_run;
  wire mbox_needs_run;
  wire mbox_running;
  input mbox_sig_done;
  wire mbox_sig_done;
  input mbox_sig_ok;
  wire mbox_sig_ok;
  input [7:0] mbox_signed_cmd;
  wire [7:0] mbox_signed_cmd;
  wire [2:0] mbox_status;
  output mbox_verify_req;
  wire mbox_verify_req;
  input [255:0] meas0_data;
  wire [255:0] meas0_data;
  input meas0_extend;
  wire meas0_extend;
  input meas0_hash_done;
  wire meas0_hash_done;
  output [511:0] meas0_hash_in;
  wire [511:0] meas0_hash_in;
  input [255:0] meas0_hash_out;
  wire [255:0] meas0_hash_out;
  output meas0_hash_req;
  wire meas0_hash_req;
  wire [255:0] meas0_value;
  input [255:0] meas1_data;
  wire [255:0] meas1_data;
  input meas1_extend;
  wire meas1_extend;
  input meas1_hash_done;
  wire meas1_hash_done;
  output [511:0] meas1_hash_in;
  wire [511:0] meas1_hash_in;
  input [255:0] meas1_hash_out;
  wire [255:0] meas1_hash_out;
  output meas1_hash_req;
  wire meas1_hash_req;
  wire [255:0] meas1_value;
  input [47:0] meter_add_cycles;
  wire [47:0] meter_add_cycles;
  input [47:0] meter_add_in;
  wire [47:0] meter_add_in;
  input [47:0] meter_add_out;
  wire [47:0] meter_add_out;
  input [47:0] meter_add_tokens;
  wire [47:0] meter_add_tokens;
  wire [11:0] meter_off;
  wire [47:0] meter_rd_cycles;
  wire [47:0] meter_rd_in;
  wire [47:0] meter_rd_out;
  wire [1:0] meter_rd_slot;
  wire [47:0] meter_rd_tokens;
  input [1:0] meter_slot;
  wire [1:0] meter_slot;
  input meter_strobe;
  wire meter_strobe;
  reg [63:0] meter_val;
  input mono_dec_req;
  wire mono_dec_req;
  input [63:0] mono_hwm;
  wire [63:0] mono_hwm;
  wire mono_inc;
  input mono_load_hwm;
  wire mono_load_hwm;
  output mono_refused;
  wire mono_refused;
  wire [63:0] mono_value;
  reg [9:0] ms_div = 10'h000;
  output perst_n;
  wire perst_n;
  output pwr_en;
  wire pwr_en;
  output pwrbrk_n;
  wire pwrbrk_n;
  input rst;
  wire rst;
  input sample;
  wire sample;
  wire \sample$144 ;
  wire [63:0] seq0;
  wire switch_open;
  input tick;
  wire tick;
  output tick_ms;
  wire tick_ms;
  input tickets_burn;
  wire tickets_burn;
  output tickets_burned;
  wire tickets_burned;
  output tickets_full;
  wire tickets_full;
  input [31:0] tickets_id_in;
  wire [31:0] tickets_id_in;
  input tickets_query;
  wire tickets_query;
  output tickets_seen;
  wire tickets_seen;
  assign \$1  = ms_div == 10'h3ff;
  assign tick_ms = tick & \$1 ;
  assign halt_hb_ok = ~ halt_hb_expired;
  assign \$2  = mbox_cmd == 5'h10;
  assign halt_clear_authorized = mbox_dispatch & \$2 ;
  assign \$3  = epoch_commit & epoch_quorum_ok;
  assign \$4  = epoch_new_epoch != epoch_epoch;
  assign mbox_epoch_advanced = \$3  & \$4 ;
  assign mbox_running = halt_state == 1'h1;
  assign pwrbrk_n = ~ halt_pwrbrk;
  assign perst_n = ~ halt_perst;
  assign alarms_hw_set = \$5  | \$6 ;
  assign \$7  = csr_addr - 10'h200;
  assign \$8  = ~ pwr_en;
  assign \$9  = csr_addr == 5'h10;
  assign \$10  = csr_addr == 6'h30;
  assign \$11  = csr_addr == 7'h50;
  assign \$12  = csr_addr == 5'h14;
  assign \$13  = csr_addr == 6'h34;
  assign \$14  = csr_addr == 7'h54;
  assign \$15  = csr_addr == 5'h18;
  assign \$16  = csr_addr == 6'h38;
  assign \$17  = csr_addr == 7'h58;
  assign \$18  = csr_addr == 5'h1c;
  assign \$19  = csr_addr == 6'h3c;
  assign \$20  = csr_addr == 7'h5c;
  assign \$21  = csr_addr == 6'h20;
  assign \$22  = csr_addr == 7'h40;
  assign \$23  = csr_addr == 7'h60;
  assign \$24  = csr_addr == 6'h24;
  assign \$25  = csr_addr == 7'h44;
  assign \$26  = csr_addr == 7'h64;
  assign \$27  = csr_addr == 6'h28;
  assign \$28  = csr_addr == 7'h48;
  assign \$29  = csr_addr == 7'h68;
  assign \$30  = csr_addr == 6'h2c;
  assign \$31  = csr_addr == 7'h4c;
  assign \$32  = csr_addr == 7'h6c;
  assign \$33  = csr_addr >= 10'h200;
  assign \$34  = csr_addr < 10'h280;
  assign \$35  = \$33  & \$34 ;
  assign \$36  = \$7 [2] ? meter_val[63:32] : meter_val[31:0];
  assign \$37  = ms_div + 1'h1;
  always @(posedge clk)
    ms_div <= \$38 ;
  \governor_core.alarms  alarms (
    .alarms_alarms(alarms_alarms),
    .alarms_clear_authorized(alarms_clear_authorized),
    .alarms_clear_mask(alarms_clear_mask),
    .alarms_hw_set(alarms_hw_set),
    .alarms_set_mask(alarms_set_mask),
    .clk(clk),
    .rst(rst)
  );
  \governor_core.cap_dpu  cap_dpu (
    .cap_dpu_allow(cap_dpu_allow),
    .cap_dpu_clear_all(cap_nvswitch_clear_all),
    .cap_dpu_epoch_tag(epoch_epoch[15:0]),
    .cap_dpu_ins(cap_dpu_ins),
    .cap_dpu_ins_budget(cap_dpu_ins_budget),
    .cap_dpu_ins_dir(cap_dpu_ins_dir),
    .cap_dpu_ins_epoch_tag(cap_dpu_ins_epoch_tag),
    .cap_dpu_ins_expiry(cap_dpu_ins_expiry),
    .cap_dpu_ins_ok(cap_dpu_ins_ok),
    .cap_dpu_ins_peer(cap_dpu_ins_peer),
    .cap_dpu_ins_point(cap_dpu_ins_point),
    .cap_dpu_lk(cap_dpu_lk),
    .cap_dpu_lk_bytes(cap_dpu_lk_bytes),
    .cap_dpu_lk_dir(cap_dpu_lk_dir),
    .cap_dpu_lk_peer(cap_dpu_lk_peer),
    .cap_dpu_lk_point(cap_dpu_lk_point),
    .cap_dpu_mac_ok(cap_dpu_mac_ok),
    .cap_dpu_now(mono_value[31:0]),
    .cap_dpu_reason(cap_dpu_reason),
    .clk(clk),
    .rst(rst)
  );
  \governor_core.cap_nvswitch  cap_nvswitch (
    .cap_nvswitch_allow(cap_nvswitch_allow),
    .cap_nvswitch_clear_all(cap_nvswitch_clear_all),
    .cap_nvswitch_epoch_tag(epoch_epoch[15:0]),
    .cap_nvswitch_ins(cap_nvswitch_ins),
    .cap_nvswitch_ins_budget(cap_nvswitch_ins_budget),
    .cap_nvswitch_ins_dir(cap_nvswitch_ins_dir),
    .cap_nvswitch_ins_epoch_tag(cap_nvswitch_ins_epoch_tag),
    .cap_nvswitch_ins_expiry(cap_nvswitch_ins_expiry),
    .cap_nvswitch_ins_ok(cap_nvswitch_ins_ok),
    .cap_nvswitch_ins_peer(cap_nvswitch_ins_peer),
    .cap_nvswitch_ins_point(cap_nvswitch_ins_point),
    .cap_nvswitch_lk(cap_nvswitch_lk),
    .cap_nvswitch_lk_bytes(cap_nvswitch_lk_bytes),
    .cap_nvswitch_lk_dir(cap_nvswitch_lk_dir),
    .cap_nvswitch_lk_peer(cap_nvswitch_lk_peer),
    .cap_nvswitch_lk_point(cap_nvswitch_lk_point),
    .cap_nvswitch_mac_ok(cap_nvswitch_mac_ok),
    .cap_nvswitch_now(mono_value[31:0]),
    .cap_nvswitch_reason(cap_nvswitch_reason),
    .clk(clk),
    .rst(rst)
  );
  \governor_core.cap_pcie  cap_pcie (
    .cap_pcie_allow(cap_pcie_allow),
    .cap_pcie_clear_all(cap_nvswitch_clear_all),
    .cap_pcie_epoch_tag(epoch_epoch[15:0]),
    .cap_pcie_ins(cap_pcie_ins),
    .cap_pcie_ins_budget(cap_pcie_ins_budget),
    .cap_pcie_ins_dir(cap_pcie_ins_dir),
    .cap_pcie_ins_epoch_tag(cap_pcie_ins_epoch_tag),
    .cap_pcie_ins_expiry(cap_pcie_ins_expiry),
    .cap_pcie_ins_ok(cap_pcie_ins_ok),
    .cap_pcie_ins_peer(cap_pcie_ins_peer),
    .cap_pcie_ins_point(cap_pcie_ins_point),
    .cap_pcie_lk(cap_pcie_lk),
    .cap_pcie_lk_bytes(cap_pcie_lk_bytes),
    .cap_pcie_lk_dir(cap_pcie_lk_dir),
    .cap_pcie_lk_peer(cap_pcie_lk_peer),
    .cap_pcie_lk_point(cap_pcie_lk_point),
    .cap_pcie_mac_ok(cap_pcie_mac_ok),
    .cap_pcie_now(mono_value[31:0]),
    .cap_pcie_reason(cap_pcie_reason),
    .clk(clk),
    .rst(rst)
  );
  \governor_core.cap_storage  cap_storage (
    .cap_storage_allow(cap_storage_allow),
    .cap_storage_clear_all(cap_nvswitch_clear_all),
    .cap_storage_epoch_tag(epoch_epoch[15:0]),
    .cap_storage_ins(cap_storage_ins),
    .cap_storage_ins_budget(cap_storage_ins_budget),
    .cap_storage_ins_dir(cap_storage_ins_dir),
    .cap_storage_ins_epoch_tag(cap_storage_ins_epoch_tag),
    .cap_storage_ins_expiry(cap_storage_ins_expiry),
    .cap_storage_ins_ok(cap_storage_ins_ok),
    .cap_storage_ins_peer(cap_storage_ins_peer),
    .cap_storage_ins_point(cap_storage_ins_point),
    .cap_storage_lk(cap_storage_lk),
    .cap_storage_lk_bytes(cap_storage_lk_bytes),
    .cap_storage_lk_dir(cap_storage_lk_dir),
    .cap_storage_lk_peer(cap_storage_lk_peer),
    .cap_storage_lk_point(cap_storage_lk_point),
    .cap_storage_mac_ok(cap_storage_mac_ok),
    .cap_storage_now(mono_value[31:0]),
    .cap_storage_reason(cap_storage_reason),
    .clk(clk),
    .rst(rst)
  );
  \governor_core.epoch  epoch (
    .clk(clk),
    .epoch_commit(epoch_commit),
    .epoch_epoch(epoch_epoch),
    .epoch_host_refused(epoch_host_wr),
    .epoch_new_epoch(epoch_new_epoch),
    .epoch_quorum_ok(epoch_quorum_ok),
    .rst(rst)
  );
  \governor_core.halt  halt (
    .clk(clk),
    .halt_boot_timer(halt_boot_timer),
    .halt_cause(halt_cause),
    .halt_clear(halt_clear),
    .halt_clear_authorized(halt_clear_authorized),
    .halt_cmd_exclude(halt_cmd_exclude),
    .halt_cmd_halt(halt_cmd_halt),
    .halt_cmd_throttle(halt_cmd_throttle),
    .halt_excluded(halt_excluded),
    .halt_hb_expired(halt_hb_expired),
    .halt_hb_ok(halt_hb_ok),
    .halt_local_trip(halt_local_trip),
    .halt_loop_lost(halt_loop_lost),
    .halt_loop_sense(loop_sense),
    .halt_no_first_hb(halt_no_first_hb),
    .halt_perst(halt_perst),
    .halt_ports_closed(cap_nvswitch_clear_all),
    .halt_pwr_en(pwr_en),
    .halt_pwrbrk(halt_pwrbrk),
    .halt_state(halt_state),
    .halt_switch_open(loop_out_open),
    .halt_tamper(halt_tamper),
    .halt_tick(tick_ms),
    .rst(rst)
  );
  \governor_core.hb  hb (
    .clk(clk),
    .hb_expired(halt_hb_expired),
    .hb_hb_valid(hb_hb_valid),
    .hb_remaining(hb_remaining),
    .hb_tick(tick_ms),
    .hb_window(hb_window),
    .rst(rst)
  );
  \governor_core.life  life (
    .clk(clk),
    .life_advance(life_advance),
    .life_advance_to(life_advance_to),
    .life_debug_grant(life_debug_grant),
    .life_debug_req(life_debug_req),
    .life_fuse_state(life_fuse_state),
    .life_load(life_load),
    .life_state(life_state),
    .rst(rst)
  );
  \governor_core.loop  loop (
    .clk(clk),
    .loop_lost(halt_loop_lost),
    .loop_out_open(loop_out_open),
    .loop_sense(loop_sense),
    .rst(rst),
    .sample(sample)
  );
  \governor_core.mbox  mbox (
    .clk(clk),
    .mbox_cmd(mbox_cmd),
    .mbox_cmd_out(mbox_cmd_out),
    .mbox_dispatch(mbox_dispatch),
    .mbox_doorbell(doorbell),
    .mbox_epoch_advanced(mbox_epoch_advanced),
    .mbox_epoch_exempt(mbox_epoch_exempt),
    .mbox_epoch_match(mbox_epoch_match),
    .mbox_frame_seq(mbox_frame_seq),
    .mbox_key_slot(mbox_key_slot),
    .mbox_needs_run(mbox_needs_run),
    .mbox_running(mbox_running),
    .mbox_sig_done(mbox_sig_done),
    .mbox_sig_ok(mbox_sig_ok),
    .mbox_signed_cmd(mbox_signed_cmd),
    .mbox_status(mbox_status),
    .mbox_verify_req(mbox_verify_req),
    .rst(rst),
    .seq0(seq0)
  );
  \governor_core.meas0  meas0 (
    .clk(clk),
    .meas0_data(meas0_data),
    .meas0_extend(meas0_extend),
    .meas0_hash_done(meas0_hash_done),
    .meas0_hash_out(meas0_hash_out),
    .meas0_hash_req(meas0_hash_req),
    .meas0_value(meas0_value),
    .rst(rst)
  );
  \governor_core.meas1  meas1 (
    .clk(clk),
    .meas1_data(meas1_data),
    .meas1_extend(meas1_extend),
    .meas1_hash_done(meas1_hash_done),
    .meas1_hash_out(meas1_hash_out),
    .meas1_hash_req(meas1_hash_req),
    .meas1_value(meas1_value),
    .rst(rst)
  );
  \governor_core.meter  meter (
    .clk(clk),
    .meter_add_cycles(meter_add_cycles),
    .meter_add_in(meter_add_in),
    .meter_add_out(meter_add_out),
    .meter_add_tokens(meter_add_tokens),
    .meter_rd_cycles(meter_rd_cycles),
    .meter_rd_in(meter_rd_in),
    .meter_rd_out(meter_rd_out),
    .meter_rd_slot(\$7 [6:5]),
    .meter_rd_tokens(meter_rd_tokens),
    .meter_slot(meter_slot),
    .meter_strobe(meter_strobe),
    .rst(rst)
  );
  \governor_core.mono  mono (
    .clk(clk),
    .mono_hwm(mono_hwm),
    .mono_inc(tick),
    .mono_load_hwm(mono_load_hwm),
    .mono_refused(mono_dec_req),
    .mono_value(mono_value),
    .rst(rst)
  );
  \governor_core.tickets  tickets (
    .clk(clk),
    .match(tickets_seen),
    .rst(rst),
    .tickets_burn(tickets_burn),
    .tickets_burned(tickets_burned),
    .tickets_full(tickets_full),
    .tickets_id_in(tickets_id_in)
  );
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (\$7 [4:3])
      2'h0:
          meter_val = { 16'h0000, meter_rd_tokens };
      2'h1:
          meter_val = { 16'h0000, meter_rd_cycles };
      2'h2:
          meter_val = { 16'h0000, meter_rd_in };
      default:
          meter_val = { 16'h0000, meter_rd_out };
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    (* full_case = 32'd1 *)
    casez (csr_addr)
      12'h000:
          csr_rdata = 32'd1397161985;
      12'h004:
          csr_rdata = { 30'h00000000, life_state };
      12'h008:
          csr_rdata = { 29'h00000000, halt_state };
      12'h00c:
          csr_rdata = { 16'h0000, cause_fw, 3'h0, halt_excluded, halt_no_first_hb, halt_cause };
      12'h070:
          csr_rdata = mono_value[31:0];
      12'h074:
          csr_rdata = mono_value[63:32];
      12'h078:
          csr_rdata = hb_remaining;
      12'h07c:
          csr_rdata = { 30'h00000000, loop_out_open, loop_sense };
      12'h080:
          csr_rdata = { 29'h00000000, \$8 , halt_perst, halt_pwrbrk };
      12'h084:
          csr_rdata = alarms_alarms;
      12'h088:
          csr_rdata = { 16'h0000, halt_boot_timer };
      12'h104:
          csr_rdata = { 29'h00000000, mbox_status };
      12'h108:
          csr_rdata = seq0[31:0];
      12'h10c:
          csr_rdata = seq0[63:32];
      default:
          csr_rdata = 32'd0;
    endcase
    if (\$9 ) begin
      csr_rdata = epoch_epoch[31:0];
    end
    if (\$10 ) begin
      csr_rdata = meas0_value[31:0];
    end
    if (\$11 ) begin
      csr_rdata = meas1_value[31:0];
    end
    if (\$12 ) begin
      csr_rdata = epoch_epoch[63:32];
    end
    if (\$13 ) begin
      csr_rdata = meas0_value[63:32];
    end
    if (\$14 ) begin
      csr_rdata = meas1_value[63:32];
    end
    if (\$15 ) begin
      csr_rdata = epoch_epoch[95:64];
    end
    if (\$16 ) begin
      csr_rdata = meas0_value[95:64];
    end
    if (\$17 ) begin
      csr_rdata = meas1_value[95:64];
    end
    if (\$18 ) begin
      csr_rdata = epoch_epoch[127:96];
    end
    if (\$19 ) begin
      csr_rdata = meas0_value[127:96];
    end
    if (\$20 ) begin
      csr_rdata = meas1_value[127:96];
    end
    if (\$21 ) begin
      csr_rdata = epoch_epoch[159:128];
    end
    if (\$22 ) begin
      csr_rdata = meas0_value[159:128];
    end
    if (\$23 ) begin
      csr_rdata = meas1_value[159:128];
    end
    if (\$24 ) begin
      csr_rdata = epoch_epoch[191:160];
    end
    if (\$25 ) begin
      csr_rdata = meas0_value[191:160];
    end
    if (\$26 ) begin
      csr_rdata = meas1_value[191:160];
    end
    if (\$27 ) begin
      csr_rdata = epoch_epoch[223:192];
    end
    if (\$28 ) begin
      csr_rdata = meas0_value[223:192];
    end
    if (\$29 ) begin
      csr_rdata = meas1_value[223:192];
    end
    if (\$30 ) begin
      csr_rdata = epoch_epoch[255:224];
    end
    if (\$31 ) begin
      csr_rdata = meas0_value[255:224];
    end
    if (\$32 ) begin
      csr_rdata = meas1_value[255:224];
    end
    if (\$35 ) begin
      csr_rdata = \$36 ;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$1 ) begin end
    \$38  = ms_div;
    if (tick) begin
      \$38  = \$37 [9:0];
    end
    if (rst) begin
      \$38  = 10'h000;
    end
  end
  assign mono_inc = tick;
  assign hb_tick = tick_ms;
  assign halt_tick = tick_ms;
  assign \sample$144  = sample;
  assign \loop_sense$145  = loop_sense;
  assign switch_open = loop_out_open;
  assign halt_switch_open = loop_out_open;
  assign \loop_out_open$148  = loop_out_open;
  assign loop_lost = halt_loop_lost;
  assign hb_expired = halt_hb_expired;
  assign halt_loop_sense = loop_sense;
  assign mbox_doorbell = doorbell;
  assign halt_pwr_en = pwr_en;
  assign cap_nvswitch_now = mono_value[31:0];
  assign cap_nvswitch_epoch_tag = epoch_epoch[15:0];
  assign epoch_epoch_tag = epoch_epoch[15:0];
  assign halt_ports_closed = cap_nvswitch_clear_all;
  assign cap_pcie_now = mono_value[31:0];
  assign cap_pcie_epoch_tag = epoch_epoch[15:0];
  assign cap_pcie_clear_all = cap_nvswitch_clear_all;
  assign cap_dpu_now = mono_value[31:0];
  assign cap_dpu_epoch_tag = epoch_epoch[15:0];
  assign cap_dpu_clear_all = cap_nvswitch_clear_all;
  assign cap_storage_now = mono_value[31:0];
  assign cap_storage_epoch_tag = epoch_epoch[15:0];
  assign cap_storage_clear_all = cap_nvswitch_clear_all;
  assign meter_off = \$7 [11:0];
  assign meter_rd_slot = \$7 [6:5];
  assign mono_refused = mono_dec_req;
  assign meas0_hash_in = { meas0_value, meas0_data };
  assign meas1_hash_in = { meas1_value, meas1_data };
  assign \$5  = { halt_no_first_hb, 31'h00000000 };
  assign \$6  = { 1'h0, halt_excluded, 30'h00000000 };
endmodule

module \governor_core.alarms (alarms_clear_mask, alarms_clear_authorized, clk, rst, alarms_hw_set, alarms_alarms, alarms_set_mask);
  reg \$auto$verilog_backend.cc:2355:dump_module$2  = 0;
  wire [31:0] \$1 ;
  wire [31:0] \$2 ;
  wire \$3 ;
  wire \$4 ;
  wire [32:0] \$5 ;
  wire [31:0] \$6 ;
  wire [32:0] \$7 ;
  wire [32:0] \$8 ;
  reg [31:0] \$9 ;
  output [31:0] alarms_alarms;
  reg [31:0] alarms_alarms = 32'd0;
  wire alarms_any;
  input alarms_clear_authorized;
  wire alarms_clear_authorized;
  input [31:0] alarms_clear_mask;
  wire [31:0] alarms_clear_mask;
  wire alarms_clear_refused;
  input [31:0] alarms_hw_set;
  wire [31:0] alarms_hw_set;
  input [31:0] alarms_set_mask;
  wire [31:0] alarms_set_mask;
  wire [31:0] cleared;
  input clk;
  wire clk;
  input rst;
  wire rst;
  assign \$1  = alarms_clear_mask & { alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized, alarms_clear_authorized };
  assign \$2  = ~ \$1 ;
  assign cleared = alarms_alarms & \$2 ;
  assign alarms_any = | alarms_alarms;
  assign \$3  = | alarms_clear_mask;
  assign \$4  = ~ alarms_clear_authorized;
  assign alarms_clear_refused = \$3  & \$4 ;
  assign \$7  = \$5  | { 1'h0, \$6  };
  assign \$8  = { 1'h0, cleared } | \$7 ;
  always @(posedge clk)
    alarms_alarms <= \$9 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$2 ) begin end
    \$9  = \$8 [31:0];
    if (rst) begin
      \$9  = 32'd0;
    end
  end
  assign \$5 [31:30] = 2'h0;
  assign { \$5 [32], \$5 [29:0] } = { 1'h0, alarms_set_mask[29:0] };
  assign \$6 [29:0] = 30'h00000000;
  assign \$6 [31:30] = alarms_hw_set[31:30];
endmodule

module \governor_core.cap_dpu (cap_dpu_ins_point, cap_dpu_ins_peer, cap_dpu_ins_dir, cap_dpu_ins_budget, cap_dpu_ins_expiry, cap_dpu_ins_epoch_tag, cap_dpu_mac_ok, cap_dpu_lk, cap_dpu_lk_point, cap_dpu_lk_peer, cap_dpu_lk_dir, cap_dpu_lk_bytes, clk, rst, cap_dpu_clear_all, cap_dpu_now, cap_dpu_epoch_tag, cap_dpu_ins_ok, cap_dpu_allow, cap_dpu_reason, cap_dpu_ins
);
  reg \$auto$verilog_backend.cc:2355:dump_module$3  = 0;
  wire \$1 ;
  wire \$10 ;
  reg \$100 ;
  reg \$101 ;
  reg [2:0] \$102 ;
  reg [2:0] \$103 ;
  reg [2:0] \$104 ;
  reg [2:0] \$105 ;
  reg [2:0] \$106 ;
  reg [2:0] \$107 ;
  reg [2:0] \$108 ;
  reg [2:0] \$109 ;
  wire \$11 ;
  reg [15:0] \$110 ;
  reg [15:0] \$111 ;
  reg [15:0] \$112 ;
  reg [15:0] \$113 ;
  reg [15:0] \$114 ;
  reg [15:0] \$115 ;
  reg [15:0] \$116 ;
  reg [15:0] \$117 ;
  reg [1:0] \$118 ;
  reg [1:0] \$119 ;
  wire \$12 ;
  reg [1:0] \$120 ;
  reg [1:0] \$121 ;
  reg [1:0] \$122 ;
  reg [1:0] \$123 ;
  reg [1:0] \$124 ;
  reg [1:0] \$125 ;
  reg [23:0] \$126 ;
  reg [23:0] \$127 ;
  reg [23:0] \$128 ;
  reg [23:0] \$129 ;
  wire \$13 ;
  reg [23:0] \$130 ;
  reg [23:0] \$131 ;
  reg [23:0] \$132 ;
  reg [23:0] \$133 ;
  reg [31:0] \$134 ;
  reg [31:0] \$135 ;
  reg [31:0] \$136 ;
  reg [31:0] \$137 ;
  reg [31:0] \$138 ;
  reg [31:0] \$139 ;
  wire \$14 ;
  reg [31:0] \$140 ;
  reg [31:0] \$141 ;
  reg [15:0] \$142 ;
  reg [15:0] \$143 ;
  reg [15:0] \$144 ;
  reg [15:0] \$145 ;
  reg [15:0] \$146 ;
  reg [15:0] \$147 ;
  reg [15:0] \$148 ;
  reg [15:0] \$149 ;
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
  wire \$33 ;
  wire \$34 ;
  wire \$35 ;
  wire \$36 ;
  wire \$37 ;
  wire \$38 ;
  wire \$39 ;
  wire \$4 ;
  wire \$40 ;
  wire \$41 ;
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
  wire \$52 ;
  wire \$53 ;
  wire \$54 ;
  wire \$55 ;
  wire \$56 ;
  wire \$57 ;
  wire \$58 ;
  wire \$59 ;
  wire \$6 ;
  wire \$60 ;
  wire \$61 ;
  wire \$62 ;
  wire \$63 ;
  wire \$64 ;
  wire \$65 ;
  wire \$66 ;
  wire \$67 ;
  wire \$68 ;
  wire \$69 ;
  wire \$7 ;
  wire \$70 ;
  wire \$71 ;
  wire \$72 ;
  wire \$73 ;
  wire \$74 ;
  wire \$75 ;
  wire \$76 ;
  reg [31:0] \$77 ;
  wire \$78 ;
  reg [15:0] \$79 ;
  wire \$8 ;
  wire \$80 ;
  reg [23:0] \$81 ;
  wire \$82 ;
  wire \$83 ;
  wire \$84 ;
  wire \$85 ;
  reg [31:0] \$86 ;
  wire \$87 ;
  reg [15:0] \$88 ;
  wire \$89 ;
  wire \$9 ;
  reg [23:0] \$90 ;
  wire \$91 ;
  reg [23:0] \$92 ;
  wire [24:0] \$93 ;
  reg \$94 ;
  reg \$95 ;
  reg \$96 ;
  reg \$97 ;
  reg \$98 ;
  reg \$99 ;
  reg [23:0] budget0 = 24'h000000;
  reg [23:0] budget1 = 24'h000000;
  reg [23:0] budget2 = 24'h000000;
  reg [23:0] budget3 = 24'h000000;
  reg [23:0] budget4 = 24'h000000;
  reg [23:0] budget5 = 24'h000000;
  reg [23:0] budget6 = 24'h000000;
  reg [23:0] budget7 = 24'h000000;
  output cap_dpu_allow;
  reg cap_dpu_allow;
  input cap_dpu_clear_all;
  wire cap_dpu_clear_all;
  input [15:0] cap_dpu_epoch_tag;
  wire [15:0] cap_dpu_epoch_tag;
  input cap_dpu_ins;
  wire cap_dpu_ins;
  input [23:0] cap_dpu_ins_budget;
  wire [23:0] cap_dpu_ins_budget;
  input [1:0] cap_dpu_ins_dir;
  wire [1:0] cap_dpu_ins_dir;
  input [15:0] cap_dpu_ins_epoch_tag;
  wire [15:0] cap_dpu_ins_epoch_tag;
  input [31:0] cap_dpu_ins_expiry;
  wire [31:0] cap_dpu_ins_expiry;
  wire cap_dpu_ins_full;
  output cap_dpu_ins_ok;
  reg cap_dpu_ins_ok;
  input [15:0] cap_dpu_ins_peer;
  wire [15:0] cap_dpu_ins_peer;
  input [2:0] cap_dpu_ins_point;
  wire [2:0] cap_dpu_ins_point;
  input cap_dpu_lk;
  wire cap_dpu_lk;
  input [23:0] cap_dpu_lk_bytes;
  wire [23:0] cap_dpu_lk_bytes;
  input [1:0] cap_dpu_lk_dir;
  wire [1:0] cap_dpu_lk_dir;
  input [15:0] cap_dpu_lk_peer;
  wire [15:0] cap_dpu_lk_peer;
  input [2:0] cap_dpu_lk_point;
  wire [2:0] cap_dpu_lk_point;
  input cap_dpu_mac_ok;
  wire cap_dpu_mac_ok;
  input [31:0] cap_dpu_now;
  wire [31:0] cap_dpu_now;
  output [2:0] cap_dpu_reason;
  reg [2:0] cap_dpu_reason;
  input clk;
  wire clk;
  reg [1:0] dir0 = 2'h0;
  reg [1:0] dir1 = 2'h0;
  reg [1:0] dir2 = 2'h0;
  reg [1:0] dir3 = 2'h0;
  reg [1:0] dir4 = 2'h0;
  reg [1:0] dir5 = 2'h0;
  reg [1:0] dir6 = 2'h0;
  reg [1:0] dir7 = 2'h0;
  reg [15:0] etag0 = 16'h0000;
  reg [15:0] etag1 = 16'h0000;
  reg [15:0] etag2 = 16'h0000;
  reg [15:0] etag3 = 16'h0000;
  reg [15:0] etag4 = 16'h0000;
  reg [15:0] etag5 = 16'h0000;
  reg [15:0] etag6 = 16'h0000;
  reg [15:0] etag7 = 16'h0000;
  reg [31:0] expiry0 = 32'd0;
  reg [31:0] expiry1 = 32'd0;
  reg [31:0] expiry2 = 32'd0;
  reg [31:0] expiry3 = 32'd0;
  reg [31:0] expiry4 = 32'd0;
  reg [31:0] expiry5 = 32'd0;
  reg [31:0] expiry6 = 32'd0;
  reg [31:0] expiry7 = 32'd0;
  wire found;
  reg [3:0] free;
  reg [3:0] hit;
  reg [15:0] peer0 = 16'h0000;
  reg [15:0] peer1 = 16'h0000;
  reg [15:0] peer2 = 16'h0000;
  reg [15:0] peer3 = 16'h0000;
  reg [15:0] peer4 = 16'h0000;
  reg [15:0] peer5 = 16'h0000;
  reg [15:0] peer6 = 16'h0000;
  reg [15:0] peer7 = 16'h0000;
  reg [2:0] point0 = 3'h0;
  reg [2:0] point1 = 3'h0;
  reg [2:0] point2 = 3'h0;
  reg [2:0] point3 = 3'h0;
  reg [2:0] point4 = 3'h0;
  reg [2:0] point5 = 3'h0;
  reg [2:0] point6 = 3'h0;
  reg [2:0] point7 = 3'h0;
  input rst;
  wire rst;
  reg valid0 = 1'h0;
  reg valid1 = 1'h0;
  reg valid2 = 1'h0;
  reg valid3 = 1'h0;
  reg valid4 = 1'h0;
  reg valid5 = 1'h0;
  reg valid6 = 1'h0;
  reg valid7 = 1'h0;
  assign \$1  = ~ valid7;
  assign \$2  = ~ valid6;
  assign \$3  = ~ valid5;
  assign \$4  = ~ valid4;
  assign \$5  = ~ valid3;
  assign \$6  = ~ valid2;
  assign \$7  = ~ valid1;
  assign \$8  = ~ valid0;
  assign found = free != 4'h8;
  assign \$9  = ~ found;
  assign cap_dpu_ins_full = cap_dpu_ins & \$9 ;
  assign \$10  = cap_dpu_ins & cap_dpu_mac_ok;
  assign \$11  = \$10  & found;
  assign \$12  = point7 == cap_dpu_lk_point;
  assign \$13  = valid7 & \$12 ;
  assign \$14  = peer7 == cap_dpu_lk_peer;
  assign \$15  = \$13  & \$14 ;
  assign \$16  = dir7 == cap_dpu_lk_dir;
  assign \$17  = dir7 == 2'h2;
  assign \$18  = \$16  | \$17 ;
  assign \$19  = \$15  & \$18 ;
  assign \$20  = point6 == cap_dpu_lk_point;
  assign \$21  = valid6 & \$20 ;
  assign \$22  = peer6 == cap_dpu_lk_peer;
  assign \$23  = \$21  & \$22 ;
  assign \$24  = dir6 == cap_dpu_lk_dir;
  assign \$25  = dir6 == 2'h2;
  assign \$26  = \$24  | \$25 ;
  assign \$27  = \$23  & \$26 ;
  assign \$28  = point5 == cap_dpu_lk_point;
  assign \$29  = valid5 & \$28 ;
  assign \$30  = peer5 == cap_dpu_lk_peer;
  assign \$31  = \$29  & \$30 ;
  assign \$32  = dir5 == cap_dpu_lk_dir;
  assign \$33  = dir5 == 2'h2;
  assign \$34  = \$32  | \$33 ;
  assign \$35  = \$31  & \$34 ;
  assign \$36  = point4 == cap_dpu_lk_point;
  assign \$37  = valid4 & \$36 ;
  assign \$38  = peer4 == cap_dpu_lk_peer;
  assign \$39  = \$37  & \$38 ;
  assign \$40  = dir4 == cap_dpu_lk_dir;
  assign \$41  = dir4 == 2'h2;
  assign \$42  = \$40  | \$41 ;
  assign \$43  = \$39  & \$42 ;
  assign \$44  = point3 == cap_dpu_lk_point;
  assign \$45  = valid3 & \$44 ;
  assign \$46  = peer3 == cap_dpu_lk_peer;
  assign \$47  = \$45  & \$46 ;
  assign \$48  = dir3 == cap_dpu_lk_dir;
  assign \$49  = dir3 == 2'h2;
  assign \$50  = \$48  | \$49 ;
  assign \$51  = \$47  & \$50 ;
  assign \$52  = point2 == cap_dpu_lk_point;
  assign \$53  = valid2 & \$52 ;
  assign \$54  = peer2 == cap_dpu_lk_peer;
  assign \$55  = \$53  & \$54 ;
  assign \$56  = dir2 == cap_dpu_lk_dir;
  assign \$57  = dir2 == 2'h2;
  assign \$58  = \$56  | \$57 ;
  assign \$59  = \$55  & \$58 ;
  assign \$60  = point1 == cap_dpu_lk_point;
  assign \$61  = valid1 & \$60 ;
  assign \$62  = peer1 == cap_dpu_lk_peer;
  assign \$63  = \$61  & \$62 ;
  assign \$64  = dir1 == cap_dpu_lk_dir;
  assign \$65  = dir1 == 2'h2;
  assign \$66  = \$64  | \$65 ;
  assign \$67  = \$63  & \$66 ;
  assign \$68  = point0 == cap_dpu_lk_point;
  assign \$69  = valid0 & \$68 ;
  assign \$70  = peer0 == cap_dpu_lk_peer;
  assign \$71  = \$69  & \$70 ;
  assign \$72  = dir0 == cap_dpu_lk_dir;
  assign \$73  = dir0 == 2'h2;
  assign \$74  = \$72  | \$73 ;
  assign \$75  = \$71  & \$74 ;
  assign \$76  = hit == 4'h8;
  assign \$78  = \$77  <= cap_dpu_now;
  assign \$80  = \$79  != cap_dpu_epoch_tag;
  assign \$82  = \$81  < cap_dpu_lk_bytes;
  assign \$83  = cap_dpu_ins & cap_dpu_mac_ok;
  assign \$84  = \$83  & found;
  assign \$85  = hit == 4'h8;
  assign \$87  = \$86  <= cap_dpu_now;
  assign \$89  = \$88  != cap_dpu_epoch_tag;
  assign \$91  = \$90  < cap_dpu_lk_bytes;
  assign \$93  = \$92  - cap_dpu_lk_bytes;
  always @(posedge clk)
    valid0 <= \$94 ;
  always @(posedge clk)
    valid1 <= \$95 ;
  always @(posedge clk)
    valid2 <= \$96 ;
  always @(posedge clk)
    valid3 <= \$97 ;
  always @(posedge clk)
    valid4 <= \$98 ;
  always @(posedge clk)
    valid5 <= \$99 ;
  always @(posedge clk)
    valid6 <= \$100 ;
  always @(posedge clk)
    valid7 <= \$101 ;
  always @(posedge clk)
    point0 <= \$102 ;
  always @(posedge clk)
    point1 <= \$103 ;
  always @(posedge clk)
    point2 <= \$104 ;
  always @(posedge clk)
    point3 <= \$105 ;
  always @(posedge clk)
    point4 <= \$106 ;
  always @(posedge clk)
    point5 <= \$107 ;
  always @(posedge clk)
    point6 <= \$108 ;
  always @(posedge clk)
    point7 <= \$109 ;
  always @(posedge clk)
    peer0 <= \$110 ;
  always @(posedge clk)
    peer1 <= \$111 ;
  always @(posedge clk)
    peer2 <= \$112 ;
  always @(posedge clk)
    peer3 <= \$113 ;
  always @(posedge clk)
    peer4 <= \$114 ;
  always @(posedge clk)
    peer5 <= \$115 ;
  always @(posedge clk)
    peer6 <= \$116 ;
  always @(posedge clk)
    peer7 <= \$117 ;
  always @(posedge clk)
    dir0 <= \$118 ;
  always @(posedge clk)
    dir1 <= \$119 ;
  always @(posedge clk)
    dir2 <= \$120 ;
  always @(posedge clk)
    dir3 <= \$121 ;
  always @(posedge clk)
    dir4 <= \$122 ;
  always @(posedge clk)
    dir5 <= \$123 ;
  always @(posedge clk)
    dir6 <= \$124 ;
  always @(posedge clk)
    dir7 <= \$125 ;
  always @(posedge clk)
    budget0 <= \$126 ;
  always @(posedge clk)
    budget1 <= \$127 ;
  always @(posedge clk)
    budget2 <= \$128 ;
  always @(posedge clk)
    budget3 <= \$129 ;
  always @(posedge clk)
    budget4 <= \$130 ;
  always @(posedge clk)
    budget5 <= \$131 ;
  always @(posedge clk)
    budget6 <= \$132 ;
  always @(posedge clk)
    budget7 <= \$133 ;
  always @(posedge clk)
    expiry0 <= \$134 ;
  always @(posedge clk)
    expiry1 <= \$135 ;
  always @(posedge clk)
    expiry2 <= \$136 ;
  always @(posedge clk)
    expiry3 <= \$137 ;
  always @(posedge clk)
    expiry4 <= \$138 ;
  always @(posedge clk)
    expiry5 <= \$139 ;
  always @(posedge clk)
    expiry6 <= \$140 ;
  always @(posedge clk)
    expiry7 <= \$141 ;
  always @(posedge clk)
    etag0 <= \$142 ;
  always @(posedge clk)
    etag1 <= \$143 ;
  always @(posedge clk)
    etag2 <= \$144 ;
  always @(posedge clk)
    etag3 <= \$145 ;
  always @(posedge clk)
    etag4 <= \$146 ;
  always @(posedge clk)
    etag5 <= \$147 ;
  always @(posedge clk)
    etag6 <= \$148 ;
  always @(posedge clk)
    etag7 <= \$149 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$77  = 32'd0;
    casez (hit)
      4'h0:
          \$77  = expiry0;
      4'h1:
          \$77  = expiry1;
      4'h2:
          \$77  = expiry2;
      4'h3:
          \$77  = expiry3;
      4'h4:
          \$77  = expiry4;
      4'h5:
          \$77  = expiry5;
      4'h6:
          \$77  = expiry6;
      4'h7:
          \$77  = expiry7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$79  = 16'h0000;
    casez (hit)
      4'h0:
          \$79  = etag0;
      4'h1:
          \$79  = etag1;
      4'h2:
          \$79  = etag2;
      4'h3:
          \$79  = etag3;
      4'h4:
          \$79  = etag4;
      4'h5:
          \$79  = etag5;
      4'h6:
          \$79  = etag6;
      4'h7:
          \$79  = etag7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$81  = 24'h000000;
    casez (hit)
      4'h0:
          \$81  = budget0;
      4'h1:
          \$81  = budget1;
      4'h2:
          \$81  = budget2;
      4'h3:
          \$81  = budget3;
      4'h4:
          \$81  = budget4;
      4'h5:
          \$81  = budget5;
      4'h6:
          \$81  = budget6;
      4'h7:
          \$81  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$86  = 32'd0;
    casez (hit)
      4'h0:
          \$86  = expiry0;
      4'h1:
          \$86  = expiry1;
      4'h2:
          \$86  = expiry2;
      4'h3:
          \$86  = expiry3;
      4'h4:
          \$86  = expiry4;
      4'h5:
          \$86  = expiry5;
      4'h6:
          \$86  = expiry6;
      4'h7:
          \$86  = expiry7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$88  = 16'h0000;
    casez (hit)
      4'h0:
          \$88  = etag0;
      4'h1:
          \$88  = etag1;
      4'h2:
          \$88  = etag2;
      4'h3:
          \$88  = etag3;
      4'h4:
          \$88  = etag4;
      4'h5:
          \$88  = etag5;
      4'h6:
          \$88  = etag6;
      4'h7:
          \$88  = etag7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$90  = 24'h000000;
    casez (hit)
      4'h0:
          \$90  = budget0;
      4'h1:
          \$90  = budget1;
      4'h2:
          \$90  = budget2;
      4'h3:
          \$90  = budget3;
      4'h4:
          \$90  = budget4;
      4'h5:
          \$90  = budget5;
      4'h6:
          \$90  = budget6;
      4'h7:
          \$90  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$92  = 24'h000000;
    casez (hit)
      4'h0:
          \$92  = budget0;
      4'h1:
          \$92  = budget1;
      4'h2:
          \$92  = budget2;
      4'h3:
          \$92  = budget3;
      4'h4:
          \$92  = budget4;
      4'h5:
          \$92  = budget5;
      4'h6:
          \$92  = budget6;
      4'h7:
          \$92  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    free = 4'h8;
    if (\$1 ) begin
      free = 4'h7;
    end
    if (\$2 ) begin
      free = 4'h6;
    end
    if (\$3 ) begin
      free = 4'h5;
    end
    if (\$4 ) begin
      free = 4'h4;
    end
    if (\$5 ) begin
      free = 4'h3;
    end
    if (\$6 ) begin
      free = 4'h2;
    end
    if (\$7 ) begin
      free = 4'h1;
    end
    if (\$8 ) begin
      free = 4'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    cap_dpu_ins_ok = 1'h0;
    if (cap_dpu_clear_all) begin
    end else if (\$11 ) begin
      cap_dpu_ins_ok = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    hit = 4'h8;
    if (\$19 ) begin
      hit = 4'h7;
    end
    if (\$27 ) begin
      hit = 4'h6;
    end
    if (\$35 ) begin
      hit = 4'h5;
    end
    if (\$43 ) begin
      hit = 4'h4;
    end
    if (\$51 ) begin
      hit = 4'h3;
    end
    if (\$59 ) begin
      hit = 4'h2;
    end
    if (\$67 ) begin
      hit = 4'h1;
    end
    if (\$75 ) begin
      hit = 4'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    cap_dpu_allow = 1'h0;
    if (cap_dpu_lk) begin
      (* full_case = 32'd1 *)
      if (\$76 ) begin
        cap_dpu_allow = 1'h0;
      end else if (\$78 ) begin
        cap_dpu_allow = 1'h0;
      end else if (\$80 ) begin
        cap_dpu_allow = 1'h0;
      end else if (\$82 ) begin
        cap_dpu_allow = 1'h0;
      end else begin
        cap_dpu_allow = 1'h1;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    cap_dpu_reason = 3'h0;
    if (cap_dpu_lk) begin
      (* full_case = 32'd1 *)
      if (\$76 ) begin
        cap_dpu_reason = 3'h1;
      end else if (\$78 ) begin
        cap_dpu_reason = 3'h2;
      end else if (\$80 ) begin
        cap_dpu_reason = 3'h3;
      end else if (\$82 ) begin
        cap_dpu_reason = 3'h4;
      end else begin
        cap_dpu_reason = 3'h0;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$94  = valid0;
    if (cap_dpu_clear_all) begin
      \$94  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$94  = 1'h1;
      endcase
    end
    if (cap_dpu_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              \$94  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$94  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$95  = valid1;
    if (cap_dpu_clear_all) begin
      \$95  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$95  = 1'h1;
      endcase
    end
    if (cap_dpu_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              \$95  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$95  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$96  = valid2;
    if (cap_dpu_clear_all) begin
      \$96  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$96  = 1'h1;
      endcase
    end
    if (cap_dpu_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              \$96  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$96  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$97  = valid3;
    if (cap_dpu_clear_all) begin
      \$97  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$97  = 1'h1;
      endcase
    end
    if (cap_dpu_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              \$97  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$97  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$98  = valid4;
    if (cap_dpu_clear_all) begin
      \$98  = 1'h0;
    end else if (\$84 ) begin
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
            \$98  = 1'h1;
      endcase
    end
    if (cap_dpu_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              /* empty */;
          4'h4:
              \$98  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$98  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$99  = valid5;
    if (cap_dpu_clear_all) begin
      \$99  = 1'h0;
    end else if (\$84 ) begin
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
            \$99  = 1'h1;
      endcase
    end
    if (cap_dpu_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$99  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$99  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$100  = valid6;
    if (cap_dpu_clear_all) begin
      \$100  = 1'h0;
    end else if (\$84 ) begin
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
            \$100  = 1'h1;
      endcase
    end
    if (cap_dpu_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$100  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$100  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$101  = valid7;
    if (cap_dpu_clear_all) begin
      \$101  = 1'h0;
    end else if (\$84 ) begin
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
            \$101  = 1'h1;
      endcase
    end
    if (cap_dpu_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$101  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$101  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$102  = point0;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$102  = cap_dpu_ins_point;
      endcase
    end
    if (rst) begin
      \$102  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$103  = point1;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$103  = cap_dpu_ins_point;
      endcase
    end
    if (rst) begin
      \$103  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$104  = point2;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$104  = cap_dpu_ins_point;
      endcase
    end
    if (rst) begin
      \$104  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$105  = point3;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$105  = cap_dpu_ins_point;
      endcase
    end
    if (rst) begin
      \$105  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$106  = point4;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$106  = cap_dpu_ins_point;
      endcase
    end
    if (rst) begin
      \$106  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$107  = point5;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$107  = cap_dpu_ins_point;
      endcase
    end
    if (rst) begin
      \$107  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$108  = point6;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$108  = cap_dpu_ins_point;
      endcase
    end
    if (rst) begin
      \$108  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$109  = point7;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$109  = cap_dpu_ins_point;
      endcase
    end
    if (rst) begin
      \$109  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$110  = peer0;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$110  = cap_dpu_ins_peer;
      endcase
    end
    if (rst) begin
      \$110  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$111  = peer1;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$111  = cap_dpu_ins_peer;
      endcase
    end
    if (rst) begin
      \$111  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$112  = peer2;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$112  = cap_dpu_ins_peer;
      endcase
    end
    if (rst) begin
      \$112  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$113  = peer3;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$113  = cap_dpu_ins_peer;
      endcase
    end
    if (rst) begin
      \$113  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$114  = peer4;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$114  = cap_dpu_ins_peer;
      endcase
    end
    if (rst) begin
      \$114  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$115  = peer5;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$115  = cap_dpu_ins_peer;
      endcase
    end
    if (rst) begin
      \$115  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$116  = peer6;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$116  = cap_dpu_ins_peer;
      endcase
    end
    if (rst) begin
      \$116  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$117  = peer7;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$117  = cap_dpu_ins_peer;
      endcase
    end
    if (rst) begin
      \$117  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$118  = dir0;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$118  = cap_dpu_ins_dir;
      endcase
    end
    if (rst) begin
      \$118  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$119  = dir1;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$119  = cap_dpu_ins_dir;
      endcase
    end
    if (rst) begin
      \$119  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$120  = dir2;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$120  = cap_dpu_ins_dir;
      endcase
    end
    if (rst) begin
      \$120  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$121  = dir3;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$121  = cap_dpu_ins_dir;
      endcase
    end
    if (rst) begin
      \$121  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$122  = dir4;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$122  = cap_dpu_ins_dir;
      endcase
    end
    if (rst) begin
      \$122  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$123  = dir5;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$123  = cap_dpu_ins_dir;
      endcase
    end
    if (rst) begin
      \$123  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$124  = dir6;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$124  = cap_dpu_ins_dir;
      endcase
    end
    if (rst) begin
      \$124  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$125  = dir7;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$125  = cap_dpu_ins_dir;
      endcase
    end
    if (rst) begin
      \$125  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$126  = budget0;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$126  = cap_dpu_ins_budget;
      endcase
    end
    if (cap_dpu_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              \$126  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$126  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$127  = budget1;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$127  = cap_dpu_ins_budget;
      endcase
    end
    if (cap_dpu_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              \$127  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$127  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$128  = budget2;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$128  = cap_dpu_ins_budget;
      endcase
    end
    if (cap_dpu_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              \$128  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$128  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$129  = budget3;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$129  = cap_dpu_ins_budget;
      endcase
    end
    if (cap_dpu_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              \$129  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$129  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$130  = budget4;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$130  = cap_dpu_ins_budget;
      endcase
    end
    if (cap_dpu_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              /* empty */;
          4'h4:
              \$130  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$130  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$131  = budget5;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$131  = cap_dpu_ins_budget;
      endcase
    end
    if (cap_dpu_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$131  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$131  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$132  = budget6;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$132  = cap_dpu_ins_budget;
      endcase
    end
    if (cap_dpu_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$132  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$132  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$133  = budget7;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$133  = cap_dpu_ins_budget;
      endcase
    end
    if (cap_dpu_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$133  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$133  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$134  = expiry0;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$134  = cap_dpu_ins_expiry;
      endcase
    end
    if (rst) begin
      \$134  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$135  = expiry1;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$135  = cap_dpu_ins_expiry;
      endcase
    end
    if (rst) begin
      \$135  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$136  = expiry2;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$136  = cap_dpu_ins_expiry;
      endcase
    end
    if (rst) begin
      \$136  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$137  = expiry3;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$137  = cap_dpu_ins_expiry;
      endcase
    end
    if (rst) begin
      \$137  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$138  = expiry4;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$138  = cap_dpu_ins_expiry;
      endcase
    end
    if (rst) begin
      \$138  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$139  = expiry5;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$139  = cap_dpu_ins_expiry;
      endcase
    end
    if (rst) begin
      \$139  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$140  = expiry6;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$140  = cap_dpu_ins_expiry;
      endcase
    end
    if (rst) begin
      \$140  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$141  = expiry7;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$141  = cap_dpu_ins_expiry;
      endcase
    end
    if (rst) begin
      \$141  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$142  = etag0;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$142  = cap_dpu_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$142  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$143  = etag1;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$143  = cap_dpu_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$143  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$144  = etag2;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$144  = cap_dpu_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$144  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$145  = etag3;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$145  = cap_dpu_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$145  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$146  = etag4;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$146  = cap_dpu_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$146  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$147  = etag5;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$147  = cap_dpu_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$147  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$148  = etag6;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$148  = cap_dpu_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$148  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$3 ) begin end
    \$149  = etag7;
    if (cap_dpu_clear_all) begin
    end else if (\$84 ) begin
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
            \$149  = cap_dpu_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$149  = 16'h0000;
    end
  end
endmodule

module \governor_core.cap_nvswitch (cap_nvswitch_ins_point, cap_nvswitch_ins_peer, cap_nvswitch_ins_dir, cap_nvswitch_ins_budget, cap_nvswitch_ins_expiry, cap_nvswitch_ins_epoch_tag, cap_nvswitch_mac_ok, cap_nvswitch_lk, cap_nvswitch_lk_point, cap_nvswitch_lk_peer, cap_nvswitch_lk_dir, cap_nvswitch_lk_bytes, clk, rst, cap_nvswitch_clear_all, cap_nvswitch_now, cap_nvswitch_epoch_tag, cap_nvswitch_ins_ok, cap_nvswitch_allow, cap_nvswitch_reason, cap_nvswitch_ins
);
  reg \$auto$verilog_backend.cc:2355:dump_module$4  = 0;
  wire \$1 ;
  wire \$10 ;
  reg \$100 ;
  reg \$101 ;
  reg [2:0] \$102 ;
  reg [2:0] \$103 ;
  reg [2:0] \$104 ;
  reg [2:0] \$105 ;
  reg [2:0] \$106 ;
  reg [2:0] \$107 ;
  reg [2:0] \$108 ;
  reg [2:0] \$109 ;
  wire \$11 ;
  reg [15:0] \$110 ;
  reg [15:0] \$111 ;
  reg [15:0] \$112 ;
  reg [15:0] \$113 ;
  reg [15:0] \$114 ;
  reg [15:0] \$115 ;
  reg [15:0] \$116 ;
  reg [15:0] \$117 ;
  reg [1:0] \$118 ;
  reg [1:0] \$119 ;
  wire \$12 ;
  reg [1:0] \$120 ;
  reg [1:0] \$121 ;
  reg [1:0] \$122 ;
  reg [1:0] \$123 ;
  reg [1:0] \$124 ;
  reg [1:0] \$125 ;
  reg [23:0] \$126 ;
  reg [23:0] \$127 ;
  reg [23:0] \$128 ;
  reg [23:0] \$129 ;
  wire \$13 ;
  reg [23:0] \$130 ;
  reg [23:0] \$131 ;
  reg [23:0] \$132 ;
  reg [23:0] \$133 ;
  reg [31:0] \$134 ;
  reg [31:0] \$135 ;
  reg [31:0] \$136 ;
  reg [31:0] \$137 ;
  reg [31:0] \$138 ;
  reg [31:0] \$139 ;
  wire \$14 ;
  reg [31:0] \$140 ;
  reg [31:0] \$141 ;
  reg [15:0] \$142 ;
  reg [15:0] \$143 ;
  reg [15:0] \$144 ;
  reg [15:0] \$145 ;
  reg [15:0] \$146 ;
  reg [15:0] \$147 ;
  reg [15:0] \$148 ;
  reg [15:0] \$149 ;
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
  wire \$33 ;
  wire \$34 ;
  wire \$35 ;
  wire \$36 ;
  wire \$37 ;
  wire \$38 ;
  wire \$39 ;
  wire \$4 ;
  wire \$40 ;
  wire \$41 ;
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
  wire \$52 ;
  wire \$53 ;
  wire \$54 ;
  wire \$55 ;
  wire \$56 ;
  wire \$57 ;
  wire \$58 ;
  wire \$59 ;
  wire \$6 ;
  wire \$60 ;
  wire \$61 ;
  wire \$62 ;
  wire \$63 ;
  wire \$64 ;
  wire \$65 ;
  wire \$66 ;
  wire \$67 ;
  wire \$68 ;
  wire \$69 ;
  wire \$7 ;
  wire \$70 ;
  wire \$71 ;
  wire \$72 ;
  wire \$73 ;
  wire \$74 ;
  wire \$75 ;
  wire \$76 ;
  reg [31:0] \$77 ;
  wire \$78 ;
  reg [15:0] \$79 ;
  wire \$8 ;
  wire \$80 ;
  reg [23:0] \$81 ;
  wire \$82 ;
  wire \$83 ;
  wire \$84 ;
  wire \$85 ;
  reg [31:0] \$86 ;
  wire \$87 ;
  reg [15:0] \$88 ;
  wire \$89 ;
  wire \$9 ;
  reg [23:0] \$90 ;
  wire \$91 ;
  reg [23:0] \$92 ;
  wire [24:0] \$93 ;
  reg \$94 ;
  reg \$95 ;
  reg \$96 ;
  reg \$97 ;
  reg \$98 ;
  reg \$99 ;
  reg [23:0] budget0 = 24'h000000;
  reg [23:0] budget1 = 24'h000000;
  reg [23:0] budget2 = 24'h000000;
  reg [23:0] budget3 = 24'h000000;
  reg [23:0] budget4 = 24'h000000;
  reg [23:0] budget5 = 24'h000000;
  reg [23:0] budget6 = 24'h000000;
  reg [23:0] budget7 = 24'h000000;
  output cap_nvswitch_allow;
  reg cap_nvswitch_allow;
  input cap_nvswitch_clear_all;
  wire cap_nvswitch_clear_all;
  input [15:0] cap_nvswitch_epoch_tag;
  wire [15:0] cap_nvswitch_epoch_tag;
  input cap_nvswitch_ins;
  wire cap_nvswitch_ins;
  input [23:0] cap_nvswitch_ins_budget;
  wire [23:0] cap_nvswitch_ins_budget;
  input [1:0] cap_nvswitch_ins_dir;
  wire [1:0] cap_nvswitch_ins_dir;
  input [15:0] cap_nvswitch_ins_epoch_tag;
  wire [15:0] cap_nvswitch_ins_epoch_tag;
  input [31:0] cap_nvswitch_ins_expiry;
  wire [31:0] cap_nvswitch_ins_expiry;
  wire cap_nvswitch_ins_full;
  output cap_nvswitch_ins_ok;
  reg cap_nvswitch_ins_ok;
  input [15:0] cap_nvswitch_ins_peer;
  wire [15:0] cap_nvswitch_ins_peer;
  input [2:0] cap_nvswitch_ins_point;
  wire [2:0] cap_nvswitch_ins_point;
  input cap_nvswitch_lk;
  wire cap_nvswitch_lk;
  input [23:0] cap_nvswitch_lk_bytes;
  wire [23:0] cap_nvswitch_lk_bytes;
  input [1:0] cap_nvswitch_lk_dir;
  wire [1:0] cap_nvswitch_lk_dir;
  input [15:0] cap_nvswitch_lk_peer;
  wire [15:0] cap_nvswitch_lk_peer;
  input [2:0] cap_nvswitch_lk_point;
  wire [2:0] cap_nvswitch_lk_point;
  input cap_nvswitch_mac_ok;
  wire cap_nvswitch_mac_ok;
  input [31:0] cap_nvswitch_now;
  wire [31:0] cap_nvswitch_now;
  output [2:0] cap_nvswitch_reason;
  reg [2:0] cap_nvswitch_reason;
  input clk;
  wire clk;
  reg [1:0] dir0 = 2'h0;
  reg [1:0] dir1 = 2'h0;
  reg [1:0] dir2 = 2'h0;
  reg [1:0] dir3 = 2'h0;
  reg [1:0] dir4 = 2'h0;
  reg [1:0] dir5 = 2'h0;
  reg [1:0] dir6 = 2'h0;
  reg [1:0] dir7 = 2'h0;
  reg [15:0] etag0 = 16'h0000;
  reg [15:0] etag1 = 16'h0000;
  reg [15:0] etag2 = 16'h0000;
  reg [15:0] etag3 = 16'h0000;
  reg [15:0] etag4 = 16'h0000;
  reg [15:0] etag5 = 16'h0000;
  reg [15:0] etag6 = 16'h0000;
  reg [15:0] etag7 = 16'h0000;
  reg [31:0] expiry0 = 32'd0;
  reg [31:0] expiry1 = 32'd0;
  reg [31:0] expiry2 = 32'd0;
  reg [31:0] expiry3 = 32'd0;
  reg [31:0] expiry4 = 32'd0;
  reg [31:0] expiry5 = 32'd0;
  reg [31:0] expiry6 = 32'd0;
  reg [31:0] expiry7 = 32'd0;
  wire found;
  reg [3:0] free;
  reg [3:0] hit;
  reg [15:0] peer0 = 16'h0000;
  reg [15:0] peer1 = 16'h0000;
  reg [15:0] peer2 = 16'h0000;
  reg [15:0] peer3 = 16'h0000;
  reg [15:0] peer4 = 16'h0000;
  reg [15:0] peer5 = 16'h0000;
  reg [15:0] peer6 = 16'h0000;
  reg [15:0] peer7 = 16'h0000;
  reg [2:0] point0 = 3'h0;
  reg [2:0] point1 = 3'h0;
  reg [2:0] point2 = 3'h0;
  reg [2:0] point3 = 3'h0;
  reg [2:0] point4 = 3'h0;
  reg [2:0] point5 = 3'h0;
  reg [2:0] point6 = 3'h0;
  reg [2:0] point7 = 3'h0;
  input rst;
  wire rst;
  reg valid0 = 1'h0;
  reg valid1 = 1'h0;
  reg valid2 = 1'h0;
  reg valid3 = 1'h0;
  reg valid4 = 1'h0;
  reg valid5 = 1'h0;
  reg valid6 = 1'h0;
  reg valid7 = 1'h0;
  assign \$1  = ~ valid7;
  assign \$2  = ~ valid6;
  assign \$3  = ~ valid5;
  assign \$4  = ~ valid4;
  assign \$5  = ~ valid3;
  assign \$6  = ~ valid2;
  assign \$7  = ~ valid1;
  assign \$8  = ~ valid0;
  assign found = free != 4'h8;
  assign \$9  = ~ found;
  assign cap_nvswitch_ins_full = cap_nvswitch_ins & \$9 ;
  assign \$10  = cap_nvswitch_ins & cap_nvswitch_mac_ok;
  assign \$11  = \$10  & found;
  assign \$12  = point7 == cap_nvswitch_lk_point;
  assign \$13  = valid7 & \$12 ;
  assign \$14  = peer7 == cap_nvswitch_lk_peer;
  assign \$15  = \$13  & \$14 ;
  assign \$16  = dir7 == cap_nvswitch_lk_dir;
  assign \$17  = dir7 == 2'h2;
  assign \$18  = \$16  | \$17 ;
  assign \$19  = \$15  & \$18 ;
  assign \$20  = point6 == cap_nvswitch_lk_point;
  assign \$21  = valid6 & \$20 ;
  assign \$22  = peer6 == cap_nvswitch_lk_peer;
  assign \$23  = \$21  & \$22 ;
  assign \$24  = dir6 == cap_nvswitch_lk_dir;
  assign \$25  = dir6 == 2'h2;
  assign \$26  = \$24  | \$25 ;
  assign \$27  = \$23  & \$26 ;
  assign \$28  = point5 == cap_nvswitch_lk_point;
  assign \$29  = valid5 & \$28 ;
  assign \$30  = peer5 == cap_nvswitch_lk_peer;
  assign \$31  = \$29  & \$30 ;
  assign \$32  = dir5 == cap_nvswitch_lk_dir;
  assign \$33  = dir5 == 2'h2;
  assign \$34  = \$32  | \$33 ;
  assign \$35  = \$31  & \$34 ;
  assign \$36  = point4 == cap_nvswitch_lk_point;
  assign \$37  = valid4 & \$36 ;
  assign \$38  = peer4 == cap_nvswitch_lk_peer;
  assign \$39  = \$37  & \$38 ;
  assign \$40  = dir4 == cap_nvswitch_lk_dir;
  assign \$41  = dir4 == 2'h2;
  assign \$42  = \$40  | \$41 ;
  assign \$43  = \$39  & \$42 ;
  assign \$44  = point3 == cap_nvswitch_lk_point;
  assign \$45  = valid3 & \$44 ;
  assign \$46  = peer3 == cap_nvswitch_lk_peer;
  assign \$47  = \$45  & \$46 ;
  assign \$48  = dir3 == cap_nvswitch_lk_dir;
  assign \$49  = dir3 == 2'h2;
  assign \$50  = \$48  | \$49 ;
  assign \$51  = \$47  & \$50 ;
  assign \$52  = point2 == cap_nvswitch_lk_point;
  assign \$53  = valid2 & \$52 ;
  assign \$54  = peer2 == cap_nvswitch_lk_peer;
  assign \$55  = \$53  & \$54 ;
  assign \$56  = dir2 == cap_nvswitch_lk_dir;
  assign \$57  = dir2 == 2'h2;
  assign \$58  = \$56  | \$57 ;
  assign \$59  = \$55  & \$58 ;
  assign \$60  = point1 == cap_nvswitch_lk_point;
  assign \$61  = valid1 & \$60 ;
  assign \$62  = peer1 == cap_nvswitch_lk_peer;
  assign \$63  = \$61  & \$62 ;
  assign \$64  = dir1 == cap_nvswitch_lk_dir;
  assign \$65  = dir1 == 2'h2;
  assign \$66  = \$64  | \$65 ;
  assign \$67  = \$63  & \$66 ;
  assign \$68  = point0 == cap_nvswitch_lk_point;
  assign \$69  = valid0 & \$68 ;
  assign \$70  = peer0 == cap_nvswitch_lk_peer;
  assign \$71  = \$69  & \$70 ;
  assign \$72  = dir0 == cap_nvswitch_lk_dir;
  assign \$73  = dir0 == 2'h2;
  assign \$74  = \$72  | \$73 ;
  assign \$75  = \$71  & \$74 ;
  assign \$76  = hit == 4'h8;
  assign \$78  = \$77  <= cap_nvswitch_now;
  assign \$80  = \$79  != cap_nvswitch_epoch_tag;
  assign \$82  = \$81  < cap_nvswitch_lk_bytes;
  assign \$83  = cap_nvswitch_ins & cap_nvswitch_mac_ok;
  assign \$84  = \$83  & found;
  assign \$85  = hit == 4'h8;
  assign \$87  = \$86  <= cap_nvswitch_now;
  assign \$89  = \$88  != cap_nvswitch_epoch_tag;
  assign \$91  = \$90  < cap_nvswitch_lk_bytes;
  assign \$93  = \$92  - cap_nvswitch_lk_bytes;
  always @(posedge clk)
    valid0 <= \$94 ;
  always @(posedge clk)
    valid1 <= \$95 ;
  always @(posedge clk)
    valid2 <= \$96 ;
  always @(posedge clk)
    valid3 <= \$97 ;
  always @(posedge clk)
    valid4 <= \$98 ;
  always @(posedge clk)
    valid5 <= \$99 ;
  always @(posedge clk)
    valid6 <= \$100 ;
  always @(posedge clk)
    valid7 <= \$101 ;
  always @(posedge clk)
    point0 <= \$102 ;
  always @(posedge clk)
    point1 <= \$103 ;
  always @(posedge clk)
    point2 <= \$104 ;
  always @(posedge clk)
    point3 <= \$105 ;
  always @(posedge clk)
    point4 <= \$106 ;
  always @(posedge clk)
    point5 <= \$107 ;
  always @(posedge clk)
    point6 <= \$108 ;
  always @(posedge clk)
    point7 <= \$109 ;
  always @(posedge clk)
    peer0 <= \$110 ;
  always @(posedge clk)
    peer1 <= \$111 ;
  always @(posedge clk)
    peer2 <= \$112 ;
  always @(posedge clk)
    peer3 <= \$113 ;
  always @(posedge clk)
    peer4 <= \$114 ;
  always @(posedge clk)
    peer5 <= \$115 ;
  always @(posedge clk)
    peer6 <= \$116 ;
  always @(posedge clk)
    peer7 <= \$117 ;
  always @(posedge clk)
    dir0 <= \$118 ;
  always @(posedge clk)
    dir1 <= \$119 ;
  always @(posedge clk)
    dir2 <= \$120 ;
  always @(posedge clk)
    dir3 <= \$121 ;
  always @(posedge clk)
    dir4 <= \$122 ;
  always @(posedge clk)
    dir5 <= \$123 ;
  always @(posedge clk)
    dir6 <= \$124 ;
  always @(posedge clk)
    dir7 <= \$125 ;
  always @(posedge clk)
    budget0 <= \$126 ;
  always @(posedge clk)
    budget1 <= \$127 ;
  always @(posedge clk)
    budget2 <= \$128 ;
  always @(posedge clk)
    budget3 <= \$129 ;
  always @(posedge clk)
    budget4 <= \$130 ;
  always @(posedge clk)
    budget5 <= \$131 ;
  always @(posedge clk)
    budget6 <= \$132 ;
  always @(posedge clk)
    budget7 <= \$133 ;
  always @(posedge clk)
    expiry0 <= \$134 ;
  always @(posedge clk)
    expiry1 <= \$135 ;
  always @(posedge clk)
    expiry2 <= \$136 ;
  always @(posedge clk)
    expiry3 <= \$137 ;
  always @(posedge clk)
    expiry4 <= \$138 ;
  always @(posedge clk)
    expiry5 <= \$139 ;
  always @(posedge clk)
    expiry6 <= \$140 ;
  always @(posedge clk)
    expiry7 <= \$141 ;
  always @(posedge clk)
    etag0 <= \$142 ;
  always @(posedge clk)
    etag1 <= \$143 ;
  always @(posedge clk)
    etag2 <= \$144 ;
  always @(posedge clk)
    etag3 <= \$145 ;
  always @(posedge clk)
    etag4 <= \$146 ;
  always @(posedge clk)
    etag5 <= \$147 ;
  always @(posedge clk)
    etag6 <= \$148 ;
  always @(posedge clk)
    etag7 <= \$149 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$77  = 32'd0;
    casez (hit)
      4'h0:
          \$77  = expiry0;
      4'h1:
          \$77  = expiry1;
      4'h2:
          \$77  = expiry2;
      4'h3:
          \$77  = expiry3;
      4'h4:
          \$77  = expiry4;
      4'h5:
          \$77  = expiry5;
      4'h6:
          \$77  = expiry6;
      4'h7:
          \$77  = expiry7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$79  = 16'h0000;
    casez (hit)
      4'h0:
          \$79  = etag0;
      4'h1:
          \$79  = etag1;
      4'h2:
          \$79  = etag2;
      4'h3:
          \$79  = etag3;
      4'h4:
          \$79  = etag4;
      4'h5:
          \$79  = etag5;
      4'h6:
          \$79  = etag6;
      4'h7:
          \$79  = etag7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$81  = 24'h000000;
    casez (hit)
      4'h0:
          \$81  = budget0;
      4'h1:
          \$81  = budget1;
      4'h2:
          \$81  = budget2;
      4'h3:
          \$81  = budget3;
      4'h4:
          \$81  = budget4;
      4'h5:
          \$81  = budget5;
      4'h6:
          \$81  = budget6;
      4'h7:
          \$81  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$86  = 32'd0;
    casez (hit)
      4'h0:
          \$86  = expiry0;
      4'h1:
          \$86  = expiry1;
      4'h2:
          \$86  = expiry2;
      4'h3:
          \$86  = expiry3;
      4'h4:
          \$86  = expiry4;
      4'h5:
          \$86  = expiry5;
      4'h6:
          \$86  = expiry6;
      4'h7:
          \$86  = expiry7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$88  = 16'h0000;
    casez (hit)
      4'h0:
          \$88  = etag0;
      4'h1:
          \$88  = etag1;
      4'h2:
          \$88  = etag2;
      4'h3:
          \$88  = etag3;
      4'h4:
          \$88  = etag4;
      4'h5:
          \$88  = etag5;
      4'h6:
          \$88  = etag6;
      4'h7:
          \$88  = etag7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$90  = 24'h000000;
    casez (hit)
      4'h0:
          \$90  = budget0;
      4'h1:
          \$90  = budget1;
      4'h2:
          \$90  = budget2;
      4'h3:
          \$90  = budget3;
      4'h4:
          \$90  = budget4;
      4'h5:
          \$90  = budget5;
      4'h6:
          \$90  = budget6;
      4'h7:
          \$90  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$92  = 24'h000000;
    casez (hit)
      4'h0:
          \$92  = budget0;
      4'h1:
          \$92  = budget1;
      4'h2:
          \$92  = budget2;
      4'h3:
          \$92  = budget3;
      4'h4:
          \$92  = budget4;
      4'h5:
          \$92  = budget5;
      4'h6:
          \$92  = budget6;
      4'h7:
          \$92  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    free = 4'h8;
    if (\$1 ) begin
      free = 4'h7;
    end
    if (\$2 ) begin
      free = 4'h6;
    end
    if (\$3 ) begin
      free = 4'h5;
    end
    if (\$4 ) begin
      free = 4'h4;
    end
    if (\$5 ) begin
      free = 4'h3;
    end
    if (\$6 ) begin
      free = 4'h2;
    end
    if (\$7 ) begin
      free = 4'h1;
    end
    if (\$8 ) begin
      free = 4'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    cap_nvswitch_ins_ok = 1'h0;
    if (cap_nvswitch_clear_all) begin
    end else if (\$11 ) begin
      cap_nvswitch_ins_ok = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    hit = 4'h8;
    if (\$19 ) begin
      hit = 4'h7;
    end
    if (\$27 ) begin
      hit = 4'h6;
    end
    if (\$35 ) begin
      hit = 4'h5;
    end
    if (\$43 ) begin
      hit = 4'h4;
    end
    if (\$51 ) begin
      hit = 4'h3;
    end
    if (\$59 ) begin
      hit = 4'h2;
    end
    if (\$67 ) begin
      hit = 4'h1;
    end
    if (\$75 ) begin
      hit = 4'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    cap_nvswitch_allow = 1'h0;
    if (cap_nvswitch_lk) begin
      (* full_case = 32'd1 *)
      if (\$76 ) begin
        cap_nvswitch_allow = 1'h0;
      end else if (\$78 ) begin
        cap_nvswitch_allow = 1'h0;
      end else if (\$80 ) begin
        cap_nvswitch_allow = 1'h0;
      end else if (\$82 ) begin
        cap_nvswitch_allow = 1'h0;
      end else begin
        cap_nvswitch_allow = 1'h1;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    cap_nvswitch_reason = 3'h0;
    if (cap_nvswitch_lk) begin
      (* full_case = 32'd1 *)
      if (\$76 ) begin
        cap_nvswitch_reason = 3'h1;
      end else if (\$78 ) begin
        cap_nvswitch_reason = 3'h2;
      end else if (\$80 ) begin
        cap_nvswitch_reason = 3'h3;
      end else if (\$82 ) begin
        cap_nvswitch_reason = 3'h4;
      end else begin
        cap_nvswitch_reason = 3'h0;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$94  = valid0;
    if (cap_nvswitch_clear_all) begin
      \$94  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$94  = 1'h1;
      endcase
    end
    if (cap_nvswitch_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              \$94  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$94  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$95  = valid1;
    if (cap_nvswitch_clear_all) begin
      \$95  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$95  = 1'h1;
      endcase
    end
    if (cap_nvswitch_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              \$95  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$95  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$96  = valid2;
    if (cap_nvswitch_clear_all) begin
      \$96  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$96  = 1'h1;
      endcase
    end
    if (cap_nvswitch_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              \$96  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$96  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$97  = valid3;
    if (cap_nvswitch_clear_all) begin
      \$97  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$97  = 1'h1;
      endcase
    end
    if (cap_nvswitch_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              \$97  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$97  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$98  = valid4;
    if (cap_nvswitch_clear_all) begin
      \$98  = 1'h0;
    end else if (\$84 ) begin
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
            \$98  = 1'h1;
      endcase
    end
    if (cap_nvswitch_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              /* empty */;
          4'h4:
              \$98  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$98  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$99  = valid5;
    if (cap_nvswitch_clear_all) begin
      \$99  = 1'h0;
    end else if (\$84 ) begin
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
            \$99  = 1'h1;
      endcase
    end
    if (cap_nvswitch_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$99  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$99  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$100  = valid6;
    if (cap_nvswitch_clear_all) begin
      \$100  = 1'h0;
    end else if (\$84 ) begin
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
            \$100  = 1'h1;
      endcase
    end
    if (cap_nvswitch_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$100  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$100  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$101  = valid7;
    if (cap_nvswitch_clear_all) begin
      \$101  = 1'h0;
    end else if (\$84 ) begin
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
            \$101  = 1'h1;
      endcase
    end
    if (cap_nvswitch_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$101  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$101  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$102  = point0;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$102  = cap_nvswitch_ins_point;
      endcase
    end
    if (rst) begin
      \$102  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$103  = point1;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$103  = cap_nvswitch_ins_point;
      endcase
    end
    if (rst) begin
      \$103  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$104  = point2;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$104  = cap_nvswitch_ins_point;
      endcase
    end
    if (rst) begin
      \$104  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$105  = point3;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$105  = cap_nvswitch_ins_point;
      endcase
    end
    if (rst) begin
      \$105  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$106  = point4;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$106  = cap_nvswitch_ins_point;
      endcase
    end
    if (rst) begin
      \$106  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$107  = point5;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$107  = cap_nvswitch_ins_point;
      endcase
    end
    if (rst) begin
      \$107  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$108  = point6;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$108  = cap_nvswitch_ins_point;
      endcase
    end
    if (rst) begin
      \$108  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$109  = point7;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$109  = cap_nvswitch_ins_point;
      endcase
    end
    if (rst) begin
      \$109  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$110  = peer0;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$110  = cap_nvswitch_ins_peer;
      endcase
    end
    if (rst) begin
      \$110  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$111  = peer1;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$111  = cap_nvswitch_ins_peer;
      endcase
    end
    if (rst) begin
      \$111  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$112  = peer2;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$112  = cap_nvswitch_ins_peer;
      endcase
    end
    if (rst) begin
      \$112  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$113  = peer3;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$113  = cap_nvswitch_ins_peer;
      endcase
    end
    if (rst) begin
      \$113  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$114  = peer4;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$114  = cap_nvswitch_ins_peer;
      endcase
    end
    if (rst) begin
      \$114  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$115  = peer5;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$115  = cap_nvswitch_ins_peer;
      endcase
    end
    if (rst) begin
      \$115  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$116  = peer6;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$116  = cap_nvswitch_ins_peer;
      endcase
    end
    if (rst) begin
      \$116  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$117  = peer7;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$117  = cap_nvswitch_ins_peer;
      endcase
    end
    if (rst) begin
      \$117  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$118  = dir0;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$118  = cap_nvswitch_ins_dir;
      endcase
    end
    if (rst) begin
      \$118  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$119  = dir1;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$119  = cap_nvswitch_ins_dir;
      endcase
    end
    if (rst) begin
      \$119  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$120  = dir2;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$120  = cap_nvswitch_ins_dir;
      endcase
    end
    if (rst) begin
      \$120  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$121  = dir3;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$121  = cap_nvswitch_ins_dir;
      endcase
    end
    if (rst) begin
      \$121  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$122  = dir4;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$122  = cap_nvswitch_ins_dir;
      endcase
    end
    if (rst) begin
      \$122  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$123  = dir5;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$123  = cap_nvswitch_ins_dir;
      endcase
    end
    if (rst) begin
      \$123  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$124  = dir6;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$124  = cap_nvswitch_ins_dir;
      endcase
    end
    if (rst) begin
      \$124  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$125  = dir7;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$125  = cap_nvswitch_ins_dir;
      endcase
    end
    if (rst) begin
      \$125  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$126  = budget0;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$126  = cap_nvswitch_ins_budget;
      endcase
    end
    if (cap_nvswitch_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              \$126  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$126  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$127  = budget1;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$127  = cap_nvswitch_ins_budget;
      endcase
    end
    if (cap_nvswitch_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              \$127  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$127  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$128  = budget2;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$128  = cap_nvswitch_ins_budget;
      endcase
    end
    if (cap_nvswitch_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              \$128  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$128  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$129  = budget3;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$129  = cap_nvswitch_ins_budget;
      endcase
    end
    if (cap_nvswitch_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              \$129  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$129  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$130  = budget4;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$130  = cap_nvswitch_ins_budget;
      endcase
    end
    if (cap_nvswitch_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              /* empty */;
          4'h4:
              \$130  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$130  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$131  = budget5;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$131  = cap_nvswitch_ins_budget;
      endcase
    end
    if (cap_nvswitch_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$131  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$131  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$132  = budget6;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$132  = cap_nvswitch_ins_budget;
      endcase
    end
    if (cap_nvswitch_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$132  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$132  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$133  = budget7;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$133  = cap_nvswitch_ins_budget;
      endcase
    end
    if (cap_nvswitch_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$133  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$133  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$134  = expiry0;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$134  = cap_nvswitch_ins_expiry;
      endcase
    end
    if (rst) begin
      \$134  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$135  = expiry1;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$135  = cap_nvswitch_ins_expiry;
      endcase
    end
    if (rst) begin
      \$135  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$136  = expiry2;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$136  = cap_nvswitch_ins_expiry;
      endcase
    end
    if (rst) begin
      \$136  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$137  = expiry3;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$137  = cap_nvswitch_ins_expiry;
      endcase
    end
    if (rst) begin
      \$137  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$138  = expiry4;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$138  = cap_nvswitch_ins_expiry;
      endcase
    end
    if (rst) begin
      \$138  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$139  = expiry5;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$139  = cap_nvswitch_ins_expiry;
      endcase
    end
    if (rst) begin
      \$139  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$140  = expiry6;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$140  = cap_nvswitch_ins_expiry;
      endcase
    end
    if (rst) begin
      \$140  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$141  = expiry7;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$141  = cap_nvswitch_ins_expiry;
      endcase
    end
    if (rst) begin
      \$141  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$142  = etag0;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$142  = cap_nvswitch_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$142  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$143  = etag1;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$143  = cap_nvswitch_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$143  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$144  = etag2;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$144  = cap_nvswitch_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$144  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$145  = etag3;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$145  = cap_nvswitch_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$145  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$146  = etag4;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$146  = cap_nvswitch_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$146  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$147  = etag5;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$147  = cap_nvswitch_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$147  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$148  = etag6;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$148  = cap_nvswitch_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$148  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$4 ) begin end
    \$149  = etag7;
    if (cap_nvswitch_clear_all) begin
    end else if (\$84 ) begin
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
            \$149  = cap_nvswitch_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$149  = 16'h0000;
    end
  end
endmodule

module \governor_core.cap_pcie (cap_pcie_ins_point, cap_pcie_ins_peer, cap_pcie_ins_dir, cap_pcie_ins_budget, cap_pcie_ins_expiry, cap_pcie_ins_epoch_tag, cap_pcie_mac_ok, cap_pcie_lk, cap_pcie_lk_point, cap_pcie_lk_peer, cap_pcie_lk_dir, cap_pcie_lk_bytes, clk, rst, cap_pcie_clear_all, cap_pcie_now, cap_pcie_epoch_tag, cap_pcie_ins_ok, cap_pcie_allow, cap_pcie_reason, cap_pcie_ins
);
  reg \$auto$verilog_backend.cc:2355:dump_module$5  = 0;
  wire \$1 ;
  wire \$10 ;
  reg \$100 ;
  reg \$101 ;
  reg [2:0] \$102 ;
  reg [2:0] \$103 ;
  reg [2:0] \$104 ;
  reg [2:0] \$105 ;
  reg [2:0] \$106 ;
  reg [2:0] \$107 ;
  reg [2:0] \$108 ;
  reg [2:0] \$109 ;
  wire \$11 ;
  reg [15:0] \$110 ;
  reg [15:0] \$111 ;
  reg [15:0] \$112 ;
  reg [15:0] \$113 ;
  reg [15:0] \$114 ;
  reg [15:0] \$115 ;
  reg [15:0] \$116 ;
  reg [15:0] \$117 ;
  reg [1:0] \$118 ;
  reg [1:0] \$119 ;
  wire \$12 ;
  reg [1:0] \$120 ;
  reg [1:0] \$121 ;
  reg [1:0] \$122 ;
  reg [1:0] \$123 ;
  reg [1:0] \$124 ;
  reg [1:0] \$125 ;
  reg [23:0] \$126 ;
  reg [23:0] \$127 ;
  reg [23:0] \$128 ;
  reg [23:0] \$129 ;
  wire \$13 ;
  reg [23:0] \$130 ;
  reg [23:0] \$131 ;
  reg [23:0] \$132 ;
  reg [23:0] \$133 ;
  reg [31:0] \$134 ;
  reg [31:0] \$135 ;
  reg [31:0] \$136 ;
  reg [31:0] \$137 ;
  reg [31:0] \$138 ;
  reg [31:0] \$139 ;
  wire \$14 ;
  reg [31:0] \$140 ;
  reg [31:0] \$141 ;
  reg [15:0] \$142 ;
  reg [15:0] \$143 ;
  reg [15:0] \$144 ;
  reg [15:0] \$145 ;
  reg [15:0] \$146 ;
  reg [15:0] \$147 ;
  reg [15:0] \$148 ;
  reg [15:0] \$149 ;
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
  wire \$33 ;
  wire \$34 ;
  wire \$35 ;
  wire \$36 ;
  wire \$37 ;
  wire \$38 ;
  wire \$39 ;
  wire \$4 ;
  wire \$40 ;
  wire \$41 ;
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
  wire \$52 ;
  wire \$53 ;
  wire \$54 ;
  wire \$55 ;
  wire \$56 ;
  wire \$57 ;
  wire \$58 ;
  wire \$59 ;
  wire \$6 ;
  wire \$60 ;
  wire \$61 ;
  wire \$62 ;
  wire \$63 ;
  wire \$64 ;
  wire \$65 ;
  wire \$66 ;
  wire \$67 ;
  wire \$68 ;
  wire \$69 ;
  wire \$7 ;
  wire \$70 ;
  wire \$71 ;
  wire \$72 ;
  wire \$73 ;
  wire \$74 ;
  wire \$75 ;
  wire \$76 ;
  reg [31:0] \$77 ;
  wire \$78 ;
  reg [15:0] \$79 ;
  wire \$8 ;
  wire \$80 ;
  reg [23:0] \$81 ;
  wire \$82 ;
  wire \$83 ;
  wire \$84 ;
  wire \$85 ;
  reg [31:0] \$86 ;
  wire \$87 ;
  reg [15:0] \$88 ;
  wire \$89 ;
  wire \$9 ;
  reg [23:0] \$90 ;
  wire \$91 ;
  reg [23:0] \$92 ;
  wire [24:0] \$93 ;
  reg \$94 ;
  reg \$95 ;
  reg \$96 ;
  reg \$97 ;
  reg \$98 ;
  reg \$99 ;
  reg [23:0] budget0 = 24'h000000;
  reg [23:0] budget1 = 24'h000000;
  reg [23:0] budget2 = 24'h000000;
  reg [23:0] budget3 = 24'h000000;
  reg [23:0] budget4 = 24'h000000;
  reg [23:0] budget5 = 24'h000000;
  reg [23:0] budget6 = 24'h000000;
  reg [23:0] budget7 = 24'h000000;
  output cap_pcie_allow;
  reg cap_pcie_allow;
  input cap_pcie_clear_all;
  wire cap_pcie_clear_all;
  input [15:0] cap_pcie_epoch_tag;
  wire [15:0] cap_pcie_epoch_tag;
  input cap_pcie_ins;
  wire cap_pcie_ins;
  input [23:0] cap_pcie_ins_budget;
  wire [23:0] cap_pcie_ins_budget;
  input [1:0] cap_pcie_ins_dir;
  wire [1:0] cap_pcie_ins_dir;
  input [15:0] cap_pcie_ins_epoch_tag;
  wire [15:0] cap_pcie_ins_epoch_tag;
  input [31:0] cap_pcie_ins_expiry;
  wire [31:0] cap_pcie_ins_expiry;
  wire cap_pcie_ins_full;
  output cap_pcie_ins_ok;
  reg cap_pcie_ins_ok;
  input [15:0] cap_pcie_ins_peer;
  wire [15:0] cap_pcie_ins_peer;
  input [2:0] cap_pcie_ins_point;
  wire [2:0] cap_pcie_ins_point;
  input cap_pcie_lk;
  wire cap_pcie_lk;
  input [23:0] cap_pcie_lk_bytes;
  wire [23:0] cap_pcie_lk_bytes;
  input [1:0] cap_pcie_lk_dir;
  wire [1:0] cap_pcie_lk_dir;
  input [15:0] cap_pcie_lk_peer;
  wire [15:0] cap_pcie_lk_peer;
  input [2:0] cap_pcie_lk_point;
  wire [2:0] cap_pcie_lk_point;
  input cap_pcie_mac_ok;
  wire cap_pcie_mac_ok;
  input [31:0] cap_pcie_now;
  wire [31:0] cap_pcie_now;
  output [2:0] cap_pcie_reason;
  reg [2:0] cap_pcie_reason;
  input clk;
  wire clk;
  reg [1:0] dir0 = 2'h0;
  reg [1:0] dir1 = 2'h0;
  reg [1:0] dir2 = 2'h0;
  reg [1:0] dir3 = 2'h0;
  reg [1:0] dir4 = 2'h0;
  reg [1:0] dir5 = 2'h0;
  reg [1:0] dir6 = 2'h0;
  reg [1:0] dir7 = 2'h0;
  reg [15:0] etag0 = 16'h0000;
  reg [15:0] etag1 = 16'h0000;
  reg [15:0] etag2 = 16'h0000;
  reg [15:0] etag3 = 16'h0000;
  reg [15:0] etag4 = 16'h0000;
  reg [15:0] etag5 = 16'h0000;
  reg [15:0] etag6 = 16'h0000;
  reg [15:0] etag7 = 16'h0000;
  reg [31:0] expiry0 = 32'd0;
  reg [31:0] expiry1 = 32'd0;
  reg [31:0] expiry2 = 32'd0;
  reg [31:0] expiry3 = 32'd0;
  reg [31:0] expiry4 = 32'd0;
  reg [31:0] expiry5 = 32'd0;
  reg [31:0] expiry6 = 32'd0;
  reg [31:0] expiry7 = 32'd0;
  wire found;
  reg [3:0] free;
  reg [3:0] hit;
  reg [15:0] peer0 = 16'h0000;
  reg [15:0] peer1 = 16'h0000;
  reg [15:0] peer2 = 16'h0000;
  reg [15:0] peer3 = 16'h0000;
  reg [15:0] peer4 = 16'h0000;
  reg [15:0] peer5 = 16'h0000;
  reg [15:0] peer6 = 16'h0000;
  reg [15:0] peer7 = 16'h0000;
  reg [2:0] point0 = 3'h0;
  reg [2:0] point1 = 3'h0;
  reg [2:0] point2 = 3'h0;
  reg [2:0] point3 = 3'h0;
  reg [2:0] point4 = 3'h0;
  reg [2:0] point5 = 3'h0;
  reg [2:0] point6 = 3'h0;
  reg [2:0] point7 = 3'h0;
  input rst;
  wire rst;
  reg valid0 = 1'h0;
  reg valid1 = 1'h0;
  reg valid2 = 1'h0;
  reg valid3 = 1'h0;
  reg valid4 = 1'h0;
  reg valid5 = 1'h0;
  reg valid6 = 1'h0;
  reg valid7 = 1'h0;
  assign \$1  = ~ valid7;
  assign \$2  = ~ valid6;
  assign \$3  = ~ valid5;
  assign \$4  = ~ valid4;
  assign \$5  = ~ valid3;
  assign \$6  = ~ valid2;
  assign \$7  = ~ valid1;
  assign \$8  = ~ valid0;
  assign found = free != 4'h8;
  assign \$9  = ~ found;
  assign cap_pcie_ins_full = cap_pcie_ins & \$9 ;
  assign \$10  = cap_pcie_ins & cap_pcie_mac_ok;
  assign \$11  = \$10  & found;
  assign \$12  = point7 == cap_pcie_lk_point;
  assign \$13  = valid7 & \$12 ;
  assign \$14  = peer7 == cap_pcie_lk_peer;
  assign \$15  = \$13  & \$14 ;
  assign \$16  = dir7 == cap_pcie_lk_dir;
  assign \$17  = dir7 == 2'h2;
  assign \$18  = \$16  | \$17 ;
  assign \$19  = \$15  & \$18 ;
  assign \$20  = point6 == cap_pcie_lk_point;
  assign \$21  = valid6 & \$20 ;
  assign \$22  = peer6 == cap_pcie_lk_peer;
  assign \$23  = \$21  & \$22 ;
  assign \$24  = dir6 == cap_pcie_lk_dir;
  assign \$25  = dir6 == 2'h2;
  assign \$26  = \$24  | \$25 ;
  assign \$27  = \$23  & \$26 ;
  assign \$28  = point5 == cap_pcie_lk_point;
  assign \$29  = valid5 & \$28 ;
  assign \$30  = peer5 == cap_pcie_lk_peer;
  assign \$31  = \$29  & \$30 ;
  assign \$32  = dir5 == cap_pcie_lk_dir;
  assign \$33  = dir5 == 2'h2;
  assign \$34  = \$32  | \$33 ;
  assign \$35  = \$31  & \$34 ;
  assign \$36  = point4 == cap_pcie_lk_point;
  assign \$37  = valid4 & \$36 ;
  assign \$38  = peer4 == cap_pcie_lk_peer;
  assign \$39  = \$37  & \$38 ;
  assign \$40  = dir4 == cap_pcie_lk_dir;
  assign \$41  = dir4 == 2'h2;
  assign \$42  = \$40  | \$41 ;
  assign \$43  = \$39  & \$42 ;
  assign \$44  = point3 == cap_pcie_lk_point;
  assign \$45  = valid3 & \$44 ;
  assign \$46  = peer3 == cap_pcie_lk_peer;
  assign \$47  = \$45  & \$46 ;
  assign \$48  = dir3 == cap_pcie_lk_dir;
  assign \$49  = dir3 == 2'h2;
  assign \$50  = \$48  | \$49 ;
  assign \$51  = \$47  & \$50 ;
  assign \$52  = point2 == cap_pcie_lk_point;
  assign \$53  = valid2 & \$52 ;
  assign \$54  = peer2 == cap_pcie_lk_peer;
  assign \$55  = \$53  & \$54 ;
  assign \$56  = dir2 == cap_pcie_lk_dir;
  assign \$57  = dir2 == 2'h2;
  assign \$58  = \$56  | \$57 ;
  assign \$59  = \$55  & \$58 ;
  assign \$60  = point1 == cap_pcie_lk_point;
  assign \$61  = valid1 & \$60 ;
  assign \$62  = peer1 == cap_pcie_lk_peer;
  assign \$63  = \$61  & \$62 ;
  assign \$64  = dir1 == cap_pcie_lk_dir;
  assign \$65  = dir1 == 2'h2;
  assign \$66  = \$64  | \$65 ;
  assign \$67  = \$63  & \$66 ;
  assign \$68  = point0 == cap_pcie_lk_point;
  assign \$69  = valid0 & \$68 ;
  assign \$70  = peer0 == cap_pcie_lk_peer;
  assign \$71  = \$69  & \$70 ;
  assign \$72  = dir0 == cap_pcie_lk_dir;
  assign \$73  = dir0 == 2'h2;
  assign \$74  = \$72  | \$73 ;
  assign \$75  = \$71  & \$74 ;
  assign \$76  = hit == 4'h8;
  assign \$78  = \$77  <= cap_pcie_now;
  assign \$80  = \$79  != cap_pcie_epoch_tag;
  assign \$82  = \$81  < cap_pcie_lk_bytes;
  assign \$83  = cap_pcie_ins & cap_pcie_mac_ok;
  assign \$84  = \$83  & found;
  assign \$85  = hit == 4'h8;
  assign \$87  = \$86  <= cap_pcie_now;
  assign \$89  = \$88  != cap_pcie_epoch_tag;
  assign \$91  = \$90  < cap_pcie_lk_bytes;
  assign \$93  = \$92  - cap_pcie_lk_bytes;
  always @(posedge clk)
    valid0 <= \$94 ;
  always @(posedge clk)
    valid1 <= \$95 ;
  always @(posedge clk)
    valid2 <= \$96 ;
  always @(posedge clk)
    valid3 <= \$97 ;
  always @(posedge clk)
    valid4 <= \$98 ;
  always @(posedge clk)
    valid5 <= \$99 ;
  always @(posedge clk)
    valid6 <= \$100 ;
  always @(posedge clk)
    valid7 <= \$101 ;
  always @(posedge clk)
    point0 <= \$102 ;
  always @(posedge clk)
    point1 <= \$103 ;
  always @(posedge clk)
    point2 <= \$104 ;
  always @(posedge clk)
    point3 <= \$105 ;
  always @(posedge clk)
    point4 <= \$106 ;
  always @(posedge clk)
    point5 <= \$107 ;
  always @(posedge clk)
    point6 <= \$108 ;
  always @(posedge clk)
    point7 <= \$109 ;
  always @(posedge clk)
    peer0 <= \$110 ;
  always @(posedge clk)
    peer1 <= \$111 ;
  always @(posedge clk)
    peer2 <= \$112 ;
  always @(posedge clk)
    peer3 <= \$113 ;
  always @(posedge clk)
    peer4 <= \$114 ;
  always @(posedge clk)
    peer5 <= \$115 ;
  always @(posedge clk)
    peer6 <= \$116 ;
  always @(posedge clk)
    peer7 <= \$117 ;
  always @(posedge clk)
    dir0 <= \$118 ;
  always @(posedge clk)
    dir1 <= \$119 ;
  always @(posedge clk)
    dir2 <= \$120 ;
  always @(posedge clk)
    dir3 <= \$121 ;
  always @(posedge clk)
    dir4 <= \$122 ;
  always @(posedge clk)
    dir5 <= \$123 ;
  always @(posedge clk)
    dir6 <= \$124 ;
  always @(posedge clk)
    dir7 <= \$125 ;
  always @(posedge clk)
    budget0 <= \$126 ;
  always @(posedge clk)
    budget1 <= \$127 ;
  always @(posedge clk)
    budget2 <= \$128 ;
  always @(posedge clk)
    budget3 <= \$129 ;
  always @(posedge clk)
    budget4 <= \$130 ;
  always @(posedge clk)
    budget5 <= \$131 ;
  always @(posedge clk)
    budget6 <= \$132 ;
  always @(posedge clk)
    budget7 <= \$133 ;
  always @(posedge clk)
    expiry0 <= \$134 ;
  always @(posedge clk)
    expiry1 <= \$135 ;
  always @(posedge clk)
    expiry2 <= \$136 ;
  always @(posedge clk)
    expiry3 <= \$137 ;
  always @(posedge clk)
    expiry4 <= \$138 ;
  always @(posedge clk)
    expiry5 <= \$139 ;
  always @(posedge clk)
    expiry6 <= \$140 ;
  always @(posedge clk)
    expiry7 <= \$141 ;
  always @(posedge clk)
    etag0 <= \$142 ;
  always @(posedge clk)
    etag1 <= \$143 ;
  always @(posedge clk)
    etag2 <= \$144 ;
  always @(posedge clk)
    etag3 <= \$145 ;
  always @(posedge clk)
    etag4 <= \$146 ;
  always @(posedge clk)
    etag5 <= \$147 ;
  always @(posedge clk)
    etag6 <= \$148 ;
  always @(posedge clk)
    etag7 <= \$149 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$77  = 32'd0;
    casez (hit)
      4'h0:
          \$77  = expiry0;
      4'h1:
          \$77  = expiry1;
      4'h2:
          \$77  = expiry2;
      4'h3:
          \$77  = expiry3;
      4'h4:
          \$77  = expiry4;
      4'h5:
          \$77  = expiry5;
      4'h6:
          \$77  = expiry6;
      4'h7:
          \$77  = expiry7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$79  = 16'h0000;
    casez (hit)
      4'h0:
          \$79  = etag0;
      4'h1:
          \$79  = etag1;
      4'h2:
          \$79  = etag2;
      4'h3:
          \$79  = etag3;
      4'h4:
          \$79  = etag4;
      4'h5:
          \$79  = etag5;
      4'h6:
          \$79  = etag6;
      4'h7:
          \$79  = etag7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$81  = 24'h000000;
    casez (hit)
      4'h0:
          \$81  = budget0;
      4'h1:
          \$81  = budget1;
      4'h2:
          \$81  = budget2;
      4'h3:
          \$81  = budget3;
      4'h4:
          \$81  = budget4;
      4'h5:
          \$81  = budget5;
      4'h6:
          \$81  = budget6;
      4'h7:
          \$81  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$86  = 32'd0;
    casez (hit)
      4'h0:
          \$86  = expiry0;
      4'h1:
          \$86  = expiry1;
      4'h2:
          \$86  = expiry2;
      4'h3:
          \$86  = expiry3;
      4'h4:
          \$86  = expiry4;
      4'h5:
          \$86  = expiry5;
      4'h6:
          \$86  = expiry6;
      4'h7:
          \$86  = expiry7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$88  = 16'h0000;
    casez (hit)
      4'h0:
          \$88  = etag0;
      4'h1:
          \$88  = etag1;
      4'h2:
          \$88  = etag2;
      4'h3:
          \$88  = etag3;
      4'h4:
          \$88  = etag4;
      4'h5:
          \$88  = etag5;
      4'h6:
          \$88  = etag6;
      4'h7:
          \$88  = etag7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$90  = 24'h000000;
    casez (hit)
      4'h0:
          \$90  = budget0;
      4'h1:
          \$90  = budget1;
      4'h2:
          \$90  = budget2;
      4'h3:
          \$90  = budget3;
      4'h4:
          \$90  = budget4;
      4'h5:
          \$90  = budget5;
      4'h6:
          \$90  = budget6;
      4'h7:
          \$90  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$92  = 24'h000000;
    casez (hit)
      4'h0:
          \$92  = budget0;
      4'h1:
          \$92  = budget1;
      4'h2:
          \$92  = budget2;
      4'h3:
          \$92  = budget3;
      4'h4:
          \$92  = budget4;
      4'h5:
          \$92  = budget5;
      4'h6:
          \$92  = budget6;
      4'h7:
          \$92  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    free = 4'h8;
    if (\$1 ) begin
      free = 4'h7;
    end
    if (\$2 ) begin
      free = 4'h6;
    end
    if (\$3 ) begin
      free = 4'h5;
    end
    if (\$4 ) begin
      free = 4'h4;
    end
    if (\$5 ) begin
      free = 4'h3;
    end
    if (\$6 ) begin
      free = 4'h2;
    end
    if (\$7 ) begin
      free = 4'h1;
    end
    if (\$8 ) begin
      free = 4'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    cap_pcie_ins_ok = 1'h0;
    if (cap_pcie_clear_all) begin
    end else if (\$11 ) begin
      cap_pcie_ins_ok = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    hit = 4'h8;
    if (\$19 ) begin
      hit = 4'h7;
    end
    if (\$27 ) begin
      hit = 4'h6;
    end
    if (\$35 ) begin
      hit = 4'h5;
    end
    if (\$43 ) begin
      hit = 4'h4;
    end
    if (\$51 ) begin
      hit = 4'h3;
    end
    if (\$59 ) begin
      hit = 4'h2;
    end
    if (\$67 ) begin
      hit = 4'h1;
    end
    if (\$75 ) begin
      hit = 4'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    cap_pcie_allow = 1'h0;
    if (cap_pcie_lk) begin
      (* full_case = 32'd1 *)
      if (\$76 ) begin
        cap_pcie_allow = 1'h0;
      end else if (\$78 ) begin
        cap_pcie_allow = 1'h0;
      end else if (\$80 ) begin
        cap_pcie_allow = 1'h0;
      end else if (\$82 ) begin
        cap_pcie_allow = 1'h0;
      end else begin
        cap_pcie_allow = 1'h1;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    cap_pcie_reason = 3'h0;
    if (cap_pcie_lk) begin
      (* full_case = 32'd1 *)
      if (\$76 ) begin
        cap_pcie_reason = 3'h1;
      end else if (\$78 ) begin
        cap_pcie_reason = 3'h2;
      end else if (\$80 ) begin
        cap_pcie_reason = 3'h3;
      end else if (\$82 ) begin
        cap_pcie_reason = 3'h4;
      end else begin
        cap_pcie_reason = 3'h0;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$94  = valid0;
    if (cap_pcie_clear_all) begin
      \$94  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$94  = 1'h1;
      endcase
    end
    if (cap_pcie_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              \$94  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$94  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$95  = valid1;
    if (cap_pcie_clear_all) begin
      \$95  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$95  = 1'h1;
      endcase
    end
    if (cap_pcie_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              \$95  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$95  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$96  = valid2;
    if (cap_pcie_clear_all) begin
      \$96  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$96  = 1'h1;
      endcase
    end
    if (cap_pcie_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              \$96  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$96  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$97  = valid3;
    if (cap_pcie_clear_all) begin
      \$97  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$97  = 1'h1;
      endcase
    end
    if (cap_pcie_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              \$97  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$97  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$98  = valid4;
    if (cap_pcie_clear_all) begin
      \$98  = 1'h0;
    end else if (\$84 ) begin
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
            \$98  = 1'h1;
      endcase
    end
    if (cap_pcie_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              /* empty */;
          4'h4:
              \$98  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$98  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$99  = valid5;
    if (cap_pcie_clear_all) begin
      \$99  = 1'h0;
    end else if (\$84 ) begin
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
            \$99  = 1'h1;
      endcase
    end
    if (cap_pcie_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$99  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$99  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$100  = valid6;
    if (cap_pcie_clear_all) begin
      \$100  = 1'h0;
    end else if (\$84 ) begin
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
            \$100  = 1'h1;
      endcase
    end
    if (cap_pcie_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$100  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$100  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$101  = valid7;
    if (cap_pcie_clear_all) begin
      \$101  = 1'h0;
    end else if (\$84 ) begin
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
            \$101  = 1'h1;
      endcase
    end
    if (cap_pcie_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$101  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$101  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$102  = point0;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$102  = cap_pcie_ins_point;
      endcase
    end
    if (rst) begin
      \$102  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$103  = point1;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$103  = cap_pcie_ins_point;
      endcase
    end
    if (rst) begin
      \$103  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$104  = point2;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$104  = cap_pcie_ins_point;
      endcase
    end
    if (rst) begin
      \$104  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$105  = point3;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$105  = cap_pcie_ins_point;
      endcase
    end
    if (rst) begin
      \$105  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$106  = point4;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$106  = cap_pcie_ins_point;
      endcase
    end
    if (rst) begin
      \$106  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$107  = point5;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$107  = cap_pcie_ins_point;
      endcase
    end
    if (rst) begin
      \$107  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$108  = point6;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$108  = cap_pcie_ins_point;
      endcase
    end
    if (rst) begin
      \$108  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$109  = point7;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$109  = cap_pcie_ins_point;
      endcase
    end
    if (rst) begin
      \$109  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$110  = peer0;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$110  = cap_pcie_ins_peer;
      endcase
    end
    if (rst) begin
      \$110  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$111  = peer1;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$111  = cap_pcie_ins_peer;
      endcase
    end
    if (rst) begin
      \$111  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$112  = peer2;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$112  = cap_pcie_ins_peer;
      endcase
    end
    if (rst) begin
      \$112  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$113  = peer3;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$113  = cap_pcie_ins_peer;
      endcase
    end
    if (rst) begin
      \$113  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$114  = peer4;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$114  = cap_pcie_ins_peer;
      endcase
    end
    if (rst) begin
      \$114  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$115  = peer5;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$115  = cap_pcie_ins_peer;
      endcase
    end
    if (rst) begin
      \$115  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$116  = peer6;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$116  = cap_pcie_ins_peer;
      endcase
    end
    if (rst) begin
      \$116  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$117  = peer7;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$117  = cap_pcie_ins_peer;
      endcase
    end
    if (rst) begin
      \$117  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$118  = dir0;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$118  = cap_pcie_ins_dir;
      endcase
    end
    if (rst) begin
      \$118  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$119  = dir1;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$119  = cap_pcie_ins_dir;
      endcase
    end
    if (rst) begin
      \$119  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$120  = dir2;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$120  = cap_pcie_ins_dir;
      endcase
    end
    if (rst) begin
      \$120  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$121  = dir3;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$121  = cap_pcie_ins_dir;
      endcase
    end
    if (rst) begin
      \$121  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$122  = dir4;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$122  = cap_pcie_ins_dir;
      endcase
    end
    if (rst) begin
      \$122  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$123  = dir5;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$123  = cap_pcie_ins_dir;
      endcase
    end
    if (rst) begin
      \$123  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$124  = dir6;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$124  = cap_pcie_ins_dir;
      endcase
    end
    if (rst) begin
      \$124  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$125  = dir7;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$125  = cap_pcie_ins_dir;
      endcase
    end
    if (rst) begin
      \$125  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$126  = budget0;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$126  = cap_pcie_ins_budget;
      endcase
    end
    if (cap_pcie_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              \$126  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$126  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$127  = budget1;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$127  = cap_pcie_ins_budget;
      endcase
    end
    if (cap_pcie_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              \$127  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$127  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$128  = budget2;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$128  = cap_pcie_ins_budget;
      endcase
    end
    if (cap_pcie_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              \$128  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$128  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$129  = budget3;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$129  = cap_pcie_ins_budget;
      endcase
    end
    if (cap_pcie_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              \$129  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$129  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$130  = budget4;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$130  = cap_pcie_ins_budget;
      endcase
    end
    if (cap_pcie_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              /* empty */;
          4'h4:
              \$130  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$130  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$131  = budget5;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$131  = cap_pcie_ins_budget;
      endcase
    end
    if (cap_pcie_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$131  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$131  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$132  = budget6;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$132  = cap_pcie_ins_budget;
      endcase
    end
    if (cap_pcie_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$132  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$132  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$133  = budget7;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$133  = cap_pcie_ins_budget;
      endcase
    end
    if (cap_pcie_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$133  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$133  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$134  = expiry0;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$134  = cap_pcie_ins_expiry;
      endcase
    end
    if (rst) begin
      \$134  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$135  = expiry1;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$135  = cap_pcie_ins_expiry;
      endcase
    end
    if (rst) begin
      \$135  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$136  = expiry2;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$136  = cap_pcie_ins_expiry;
      endcase
    end
    if (rst) begin
      \$136  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$137  = expiry3;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$137  = cap_pcie_ins_expiry;
      endcase
    end
    if (rst) begin
      \$137  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$138  = expiry4;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$138  = cap_pcie_ins_expiry;
      endcase
    end
    if (rst) begin
      \$138  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$139  = expiry5;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$139  = cap_pcie_ins_expiry;
      endcase
    end
    if (rst) begin
      \$139  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$140  = expiry6;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$140  = cap_pcie_ins_expiry;
      endcase
    end
    if (rst) begin
      \$140  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$141  = expiry7;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$141  = cap_pcie_ins_expiry;
      endcase
    end
    if (rst) begin
      \$141  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$142  = etag0;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$142  = cap_pcie_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$142  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$143  = etag1;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$143  = cap_pcie_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$143  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$144  = etag2;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$144  = cap_pcie_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$144  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$145  = etag3;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$145  = cap_pcie_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$145  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$146  = etag4;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$146  = cap_pcie_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$146  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$147  = etag5;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$147  = cap_pcie_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$147  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$148  = etag6;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$148  = cap_pcie_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$148  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$5 ) begin end
    \$149  = etag7;
    if (cap_pcie_clear_all) begin
    end else if (\$84 ) begin
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
            \$149  = cap_pcie_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$149  = 16'h0000;
    end
  end
endmodule

module \governor_core.cap_storage (cap_storage_ins_point, cap_storage_ins_peer, cap_storage_ins_dir, cap_storage_ins_budget, cap_storage_ins_expiry, cap_storage_ins_epoch_tag, cap_storage_mac_ok, cap_storage_lk, cap_storage_lk_point, cap_storage_lk_peer, cap_storage_lk_dir, cap_storage_lk_bytes, clk, rst, cap_storage_clear_all, cap_storage_now, cap_storage_epoch_tag, cap_storage_ins_ok, cap_storage_allow, cap_storage_reason, cap_storage_ins
);
  reg \$auto$verilog_backend.cc:2355:dump_module$6  = 0;
  wire \$1 ;
  wire \$10 ;
  reg \$100 ;
  reg \$101 ;
  reg [2:0] \$102 ;
  reg [2:0] \$103 ;
  reg [2:0] \$104 ;
  reg [2:0] \$105 ;
  reg [2:0] \$106 ;
  reg [2:0] \$107 ;
  reg [2:0] \$108 ;
  reg [2:0] \$109 ;
  wire \$11 ;
  reg [15:0] \$110 ;
  reg [15:0] \$111 ;
  reg [15:0] \$112 ;
  reg [15:0] \$113 ;
  reg [15:0] \$114 ;
  reg [15:0] \$115 ;
  reg [15:0] \$116 ;
  reg [15:0] \$117 ;
  reg [1:0] \$118 ;
  reg [1:0] \$119 ;
  wire \$12 ;
  reg [1:0] \$120 ;
  reg [1:0] \$121 ;
  reg [1:0] \$122 ;
  reg [1:0] \$123 ;
  reg [1:0] \$124 ;
  reg [1:0] \$125 ;
  reg [23:0] \$126 ;
  reg [23:0] \$127 ;
  reg [23:0] \$128 ;
  reg [23:0] \$129 ;
  wire \$13 ;
  reg [23:0] \$130 ;
  reg [23:0] \$131 ;
  reg [23:0] \$132 ;
  reg [23:0] \$133 ;
  reg [31:0] \$134 ;
  reg [31:0] \$135 ;
  reg [31:0] \$136 ;
  reg [31:0] \$137 ;
  reg [31:0] \$138 ;
  reg [31:0] \$139 ;
  wire \$14 ;
  reg [31:0] \$140 ;
  reg [31:0] \$141 ;
  reg [15:0] \$142 ;
  reg [15:0] \$143 ;
  reg [15:0] \$144 ;
  reg [15:0] \$145 ;
  reg [15:0] \$146 ;
  reg [15:0] \$147 ;
  reg [15:0] \$148 ;
  reg [15:0] \$149 ;
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
  wire \$33 ;
  wire \$34 ;
  wire \$35 ;
  wire \$36 ;
  wire \$37 ;
  wire \$38 ;
  wire \$39 ;
  wire \$4 ;
  wire \$40 ;
  wire \$41 ;
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
  wire \$52 ;
  wire \$53 ;
  wire \$54 ;
  wire \$55 ;
  wire \$56 ;
  wire \$57 ;
  wire \$58 ;
  wire \$59 ;
  wire \$6 ;
  wire \$60 ;
  wire \$61 ;
  wire \$62 ;
  wire \$63 ;
  wire \$64 ;
  wire \$65 ;
  wire \$66 ;
  wire \$67 ;
  wire \$68 ;
  wire \$69 ;
  wire \$7 ;
  wire \$70 ;
  wire \$71 ;
  wire \$72 ;
  wire \$73 ;
  wire \$74 ;
  wire \$75 ;
  wire \$76 ;
  reg [31:0] \$77 ;
  wire \$78 ;
  reg [15:0] \$79 ;
  wire \$8 ;
  wire \$80 ;
  reg [23:0] \$81 ;
  wire \$82 ;
  wire \$83 ;
  wire \$84 ;
  wire \$85 ;
  reg [31:0] \$86 ;
  wire \$87 ;
  reg [15:0] \$88 ;
  wire \$89 ;
  wire \$9 ;
  reg [23:0] \$90 ;
  wire \$91 ;
  reg [23:0] \$92 ;
  wire [24:0] \$93 ;
  reg \$94 ;
  reg \$95 ;
  reg \$96 ;
  reg \$97 ;
  reg \$98 ;
  reg \$99 ;
  reg [23:0] budget0 = 24'h000000;
  reg [23:0] budget1 = 24'h000000;
  reg [23:0] budget2 = 24'h000000;
  reg [23:0] budget3 = 24'h000000;
  reg [23:0] budget4 = 24'h000000;
  reg [23:0] budget5 = 24'h000000;
  reg [23:0] budget6 = 24'h000000;
  reg [23:0] budget7 = 24'h000000;
  output cap_storage_allow;
  reg cap_storage_allow;
  input cap_storage_clear_all;
  wire cap_storage_clear_all;
  input [15:0] cap_storage_epoch_tag;
  wire [15:0] cap_storage_epoch_tag;
  input cap_storage_ins;
  wire cap_storage_ins;
  input [23:0] cap_storage_ins_budget;
  wire [23:0] cap_storage_ins_budget;
  input [1:0] cap_storage_ins_dir;
  wire [1:0] cap_storage_ins_dir;
  input [15:0] cap_storage_ins_epoch_tag;
  wire [15:0] cap_storage_ins_epoch_tag;
  input [31:0] cap_storage_ins_expiry;
  wire [31:0] cap_storage_ins_expiry;
  wire cap_storage_ins_full;
  output cap_storage_ins_ok;
  reg cap_storage_ins_ok;
  input [15:0] cap_storage_ins_peer;
  wire [15:0] cap_storage_ins_peer;
  input [2:0] cap_storage_ins_point;
  wire [2:0] cap_storage_ins_point;
  input cap_storage_lk;
  wire cap_storage_lk;
  input [23:0] cap_storage_lk_bytes;
  wire [23:0] cap_storage_lk_bytes;
  input [1:0] cap_storage_lk_dir;
  wire [1:0] cap_storage_lk_dir;
  input [15:0] cap_storage_lk_peer;
  wire [15:0] cap_storage_lk_peer;
  input [2:0] cap_storage_lk_point;
  wire [2:0] cap_storage_lk_point;
  input cap_storage_mac_ok;
  wire cap_storage_mac_ok;
  input [31:0] cap_storage_now;
  wire [31:0] cap_storage_now;
  output [2:0] cap_storage_reason;
  reg [2:0] cap_storage_reason;
  input clk;
  wire clk;
  reg [1:0] dir0 = 2'h0;
  reg [1:0] dir1 = 2'h0;
  reg [1:0] dir2 = 2'h0;
  reg [1:0] dir3 = 2'h0;
  reg [1:0] dir4 = 2'h0;
  reg [1:0] dir5 = 2'h0;
  reg [1:0] dir6 = 2'h0;
  reg [1:0] dir7 = 2'h0;
  reg [15:0] etag0 = 16'h0000;
  reg [15:0] etag1 = 16'h0000;
  reg [15:0] etag2 = 16'h0000;
  reg [15:0] etag3 = 16'h0000;
  reg [15:0] etag4 = 16'h0000;
  reg [15:0] etag5 = 16'h0000;
  reg [15:0] etag6 = 16'h0000;
  reg [15:0] etag7 = 16'h0000;
  reg [31:0] expiry0 = 32'd0;
  reg [31:0] expiry1 = 32'd0;
  reg [31:0] expiry2 = 32'd0;
  reg [31:0] expiry3 = 32'd0;
  reg [31:0] expiry4 = 32'd0;
  reg [31:0] expiry5 = 32'd0;
  reg [31:0] expiry6 = 32'd0;
  reg [31:0] expiry7 = 32'd0;
  wire found;
  reg [3:0] free;
  reg [3:0] hit;
  reg [15:0] peer0 = 16'h0000;
  reg [15:0] peer1 = 16'h0000;
  reg [15:0] peer2 = 16'h0000;
  reg [15:0] peer3 = 16'h0000;
  reg [15:0] peer4 = 16'h0000;
  reg [15:0] peer5 = 16'h0000;
  reg [15:0] peer6 = 16'h0000;
  reg [15:0] peer7 = 16'h0000;
  reg [2:0] point0 = 3'h0;
  reg [2:0] point1 = 3'h0;
  reg [2:0] point2 = 3'h0;
  reg [2:0] point3 = 3'h0;
  reg [2:0] point4 = 3'h0;
  reg [2:0] point5 = 3'h0;
  reg [2:0] point6 = 3'h0;
  reg [2:0] point7 = 3'h0;
  input rst;
  wire rst;
  reg valid0 = 1'h0;
  reg valid1 = 1'h0;
  reg valid2 = 1'h0;
  reg valid3 = 1'h0;
  reg valid4 = 1'h0;
  reg valid5 = 1'h0;
  reg valid6 = 1'h0;
  reg valid7 = 1'h0;
  assign \$1  = ~ valid7;
  assign \$2  = ~ valid6;
  assign \$3  = ~ valid5;
  assign \$4  = ~ valid4;
  assign \$5  = ~ valid3;
  assign \$6  = ~ valid2;
  assign \$7  = ~ valid1;
  assign \$8  = ~ valid0;
  assign found = free != 4'h8;
  assign \$9  = ~ found;
  assign cap_storage_ins_full = cap_storage_ins & \$9 ;
  assign \$10  = cap_storage_ins & cap_storage_mac_ok;
  assign \$11  = \$10  & found;
  assign \$12  = point7 == cap_storage_lk_point;
  assign \$13  = valid7 & \$12 ;
  assign \$14  = peer7 == cap_storage_lk_peer;
  assign \$15  = \$13  & \$14 ;
  assign \$16  = dir7 == cap_storage_lk_dir;
  assign \$17  = dir7 == 2'h2;
  assign \$18  = \$16  | \$17 ;
  assign \$19  = \$15  & \$18 ;
  assign \$20  = point6 == cap_storage_lk_point;
  assign \$21  = valid6 & \$20 ;
  assign \$22  = peer6 == cap_storage_lk_peer;
  assign \$23  = \$21  & \$22 ;
  assign \$24  = dir6 == cap_storage_lk_dir;
  assign \$25  = dir6 == 2'h2;
  assign \$26  = \$24  | \$25 ;
  assign \$27  = \$23  & \$26 ;
  assign \$28  = point5 == cap_storage_lk_point;
  assign \$29  = valid5 & \$28 ;
  assign \$30  = peer5 == cap_storage_lk_peer;
  assign \$31  = \$29  & \$30 ;
  assign \$32  = dir5 == cap_storage_lk_dir;
  assign \$33  = dir5 == 2'h2;
  assign \$34  = \$32  | \$33 ;
  assign \$35  = \$31  & \$34 ;
  assign \$36  = point4 == cap_storage_lk_point;
  assign \$37  = valid4 & \$36 ;
  assign \$38  = peer4 == cap_storage_lk_peer;
  assign \$39  = \$37  & \$38 ;
  assign \$40  = dir4 == cap_storage_lk_dir;
  assign \$41  = dir4 == 2'h2;
  assign \$42  = \$40  | \$41 ;
  assign \$43  = \$39  & \$42 ;
  assign \$44  = point3 == cap_storage_lk_point;
  assign \$45  = valid3 & \$44 ;
  assign \$46  = peer3 == cap_storage_lk_peer;
  assign \$47  = \$45  & \$46 ;
  assign \$48  = dir3 == cap_storage_lk_dir;
  assign \$49  = dir3 == 2'h2;
  assign \$50  = \$48  | \$49 ;
  assign \$51  = \$47  & \$50 ;
  assign \$52  = point2 == cap_storage_lk_point;
  assign \$53  = valid2 & \$52 ;
  assign \$54  = peer2 == cap_storage_lk_peer;
  assign \$55  = \$53  & \$54 ;
  assign \$56  = dir2 == cap_storage_lk_dir;
  assign \$57  = dir2 == 2'h2;
  assign \$58  = \$56  | \$57 ;
  assign \$59  = \$55  & \$58 ;
  assign \$60  = point1 == cap_storage_lk_point;
  assign \$61  = valid1 & \$60 ;
  assign \$62  = peer1 == cap_storage_lk_peer;
  assign \$63  = \$61  & \$62 ;
  assign \$64  = dir1 == cap_storage_lk_dir;
  assign \$65  = dir1 == 2'h2;
  assign \$66  = \$64  | \$65 ;
  assign \$67  = \$63  & \$66 ;
  assign \$68  = point0 == cap_storage_lk_point;
  assign \$69  = valid0 & \$68 ;
  assign \$70  = peer0 == cap_storage_lk_peer;
  assign \$71  = \$69  & \$70 ;
  assign \$72  = dir0 == cap_storage_lk_dir;
  assign \$73  = dir0 == 2'h2;
  assign \$74  = \$72  | \$73 ;
  assign \$75  = \$71  & \$74 ;
  assign \$76  = hit == 4'h8;
  assign \$78  = \$77  <= cap_storage_now;
  assign \$80  = \$79  != cap_storage_epoch_tag;
  assign \$82  = \$81  < cap_storage_lk_bytes;
  assign \$83  = cap_storage_ins & cap_storage_mac_ok;
  assign \$84  = \$83  & found;
  assign \$85  = hit == 4'h8;
  assign \$87  = \$86  <= cap_storage_now;
  assign \$89  = \$88  != cap_storage_epoch_tag;
  assign \$91  = \$90  < cap_storage_lk_bytes;
  assign \$93  = \$92  - cap_storage_lk_bytes;
  always @(posedge clk)
    valid0 <= \$94 ;
  always @(posedge clk)
    valid1 <= \$95 ;
  always @(posedge clk)
    valid2 <= \$96 ;
  always @(posedge clk)
    valid3 <= \$97 ;
  always @(posedge clk)
    valid4 <= \$98 ;
  always @(posedge clk)
    valid5 <= \$99 ;
  always @(posedge clk)
    valid6 <= \$100 ;
  always @(posedge clk)
    valid7 <= \$101 ;
  always @(posedge clk)
    point0 <= \$102 ;
  always @(posedge clk)
    point1 <= \$103 ;
  always @(posedge clk)
    point2 <= \$104 ;
  always @(posedge clk)
    point3 <= \$105 ;
  always @(posedge clk)
    point4 <= \$106 ;
  always @(posedge clk)
    point5 <= \$107 ;
  always @(posedge clk)
    point6 <= \$108 ;
  always @(posedge clk)
    point7 <= \$109 ;
  always @(posedge clk)
    peer0 <= \$110 ;
  always @(posedge clk)
    peer1 <= \$111 ;
  always @(posedge clk)
    peer2 <= \$112 ;
  always @(posedge clk)
    peer3 <= \$113 ;
  always @(posedge clk)
    peer4 <= \$114 ;
  always @(posedge clk)
    peer5 <= \$115 ;
  always @(posedge clk)
    peer6 <= \$116 ;
  always @(posedge clk)
    peer7 <= \$117 ;
  always @(posedge clk)
    dir0 <= \$118 ;
  always @(posedge clk)
    dir1 <= \$119 ;
  always @(posedge clk)
    dir2 <= \$120 ;
  always @(posedge clk)
    dir3 <= \$121 ;
  always @(posedge clk)
    dir4 <= \$122 ;
  always @(posedge clk)
    dir5 <= \$123 ;
  always @(posedge clk)
    dir6 <= \$124 ;
  always @(posedge clk)
    dir7 <= \$125 ;
  always @(posedge clk)
    budget0 <= \$126 ;
  always @(posedge clk)
    budget1 <= \$127 ;
  always @(posedge clk)
    budget2 <= \$128 ;
  always @(posedge clk)
    budget3 <= \$129 ;
  always @(posedge clk)
    budget4 <= \$130 ;
  always @(posedge clk)
    budget5 <= \$131 ;
  always @(posedge clk)
    budget6 <= \$132 ;
  always @(posedge clk)
    budget7 <= \$133 ;
  always @(posedge clk)
    expiry0 <= \$134 ;
  always @(posedge clk)
    expiry1 <= \$135 ;
  always @(posedge clk)
    expiry2 <= \$136 ;
  always @(posedge clk)
    expiry3 <= \$137 ;
  always @(posedge clk)
    expiry4 <= \$138 ;
  always @(posedge clk)
    expiry5 <= \$139 ;
  always @(posedge clk)
    expiry6 <= \$140 ;
  always @(posedge clk)
    expiry7 <= \$141 ;
  always @(posedge clk)
    etag0 <= \$142 ;
  always @(posedge clk)
    etag1 <= \$143 ;
  always @(posedge clk)
    etag2 <= \$144 ;
  always @(posedge clk)
    etag3 <= \$145 ;
  always @(posedge clk)
    etag4 <= \$146 ;
  always @(posedge clk)
    etag5 <= \$147 ;
  always @(posedge clk)
    etag6 <= \$148 ;
  always @(posedge clk)
    etag7 <= \$149 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$77  = 32'd0;
    casez (hit)
      4'h0:
          \$77  = expiry0;
      4'h1:
          \$77  = expiry1;
      4'h2:
          \$77  = expiry2;
      4'h3:
          \$77  = expiry3;
      4'h4:
          \$77  = expiry4;
      4'h5:
          \$77  = expiry5;
      4'h6:
          \$77  = expiry6;
      4'h7:
          \$77  = expiry7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$79  = 16'h0000;
    casez (hit)
      4'h0:
          \$79  = etag0;
      4'h1:
          \$79  = etag1;
      4'h2:
          \$79  = etag2;
      4'h3:
          \$79  = etag3;
      4'h4:
          \$79  = etag4;
      4'h5:
          \$79  = etag5;
      4'h6:
          \$79  = etag6;
      4'h7:
          \$79  = etag7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$81  = 24'h000000;
    casez (hit)
      4'h0:
          \$81  = budget0;
      4'h1:
          \$81  = budget1;
      4'h2:
          \$81  = budget2;
      4'h3:
          \$81  = budget3;
      4'h4:
          \$81  = budget4;
      4'h5:
          \$81  = budget5;
      4'h6:
          \$81  = budget6;
      4'h7:
          \$81  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$86  = 32'd0;
    casez (hit)
      4'h0:
          \$86  = expiry0;
      4'h1:
          \$86  = expiry1;
      4'h2:
          \$86  = expiry2;
      4'h3:
          \$86  = expiry3;
      4'h4:
          \$86  = expiry4;
      4'h5:
          \$86  = expiry5;
      4'h6:
          \$86  = expiry6;
      4'h7:
          \$86  = expiry7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$88  = 16'h0000;
    casez (hit)
      4'h0:
          \$88  = etag0;
      4'h1:
          \$88  = etag1;
      4'h2:
          \$88  = etag2;
      4'h3:
          \$88  = etag3;
      4'h4:
          \$88  = etag4;
      4'h5:
          \$88  = etag5;
      4'h6:
          \$88  = etag6;
      4'h7:
          \$88  = etag7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$90  = 24'h000000;
    casez (hit)
      4'h0:
          \$90  = budget0;
      4'h1:
          \$90  = budget1;
      4'h2:
          \$90  = budget2;
      4'h3:
          \$90  = budget3;
      4'h4:
          \$90  = budget4;
      4'h5:
          \$90  = budget5;
      4'h6:
          \$90  = budget6;
      4'h7:
          \$90  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$92  = 24'h000000;
    casez (hit)
      4'h0:
          \$92  = budget0;
      4'h1:
          \$92  = budget1;
      4'h2:
          \$92  = budget2;
      4'h3:
          \$92  = budget3;
      4'h4:
          \$92  = budget4;
      4'h5:
          \$92  = budget5;
      4'h6:
          \$92  = budget6;
      4'h7:
          \$92  = budget7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    free = 4'h8;
    if (\$1 ) begin
      free = 4'h7;
    end
    if (\$2 ) begin
      free = 4'h6;
    end
    if (\$3 ) begin
      free = 4'h5;
    end
    if (\$4 ) begin
      free = 4'h4;
    end
    if (\$5 ) begin
      free = 4'h3;
    end
    if (\$6 ) begin
      free = 4'h2;
    end
    if (\$7 ) begin
      free = 4'h1;
    end
    if (\$8 ) begin
      free = 4'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    cap_storage_ins_ok = 1'h0;
    if (cap_storage_clear_all) begin
    end else if (\$11 ) begin
      cap_storage_ins_ok = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    hit = 4'h8;
    if (\$19 ) begin
      hit = 4'h7;
    end
    if (\$27 ) begin
      hit = 4'h6;
    end
    if (\$35 ) begin
      hit = 4'h5;
    end
    if (\$43 ) begin
      hit = 4'h4;
    end
    if (\$51 ) begin
      hit = 4'h3;
    end
    if (\$59 ) begin
      hit = 4'h2;
    end
    if (\$67 ) begin
      hit = 4'h1;
    end
    if (\$75 ) begin
      hit = 4'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    cap_storage_allow = 1'h0;
    if (cap_storage_lk) begin
      (* full_case = 32'd1 *)
      if (\$76 ) begin
        cap_storage_allow = 1'h0;
      end else if (\$78 ) begin
        cap_storage_allow = 1'h0;
      end else if (\$80 ) begin
        cap_storage_allow = 1'h0;
      end else if (\$82 ) begin
        cap_storage_allow = 1'h0;
      end else begin
        cap_storage_allow = 1'h1;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    cap_storage_reason = 3'h0;
    if (cap_storage_lk) begin
      (* full_case = 32'd1 *)
      if (\$76 ) begin
        cap_storage_reason = 3'h1;
      end else if (\$78 ) begin
        cap_storage_reason = 3'h2;
      end else if (\$80 ) begin
        cap_storage_reason = 3'h3;
      end else if (\$82 ) begin
        cap_storage_reason = 3'h4;
      end else begin
        cap_storage_reason = 3'h0;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$94  = valid0;
    if (cap_storage_clear_all) begin
      \$94  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$94  = 1'h1;
      endcase
    end
    if (cap_storage_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              \$94  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$94  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$95  = valid1;
    if (cap_storage_clear_all) begin
      \$95  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$95  = 1'h1;
      endcase
    end
    if (cap_storage_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              \$95  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$95  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$96  = valid2;
    if (cap_storage_clear_all) begin
      \$96  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$96  = 1'h1;
      endcase
    end
    if (cap_storage_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              \$96  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$96  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$97  = valid3;
    if (cap_storage_clear_all) begin
      \$97  = 1'h0;
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$97  = 1'h1;
      endcase
    end
    if (cap_storage_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              \$97  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$97  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$98  = valid4;
    if (cap_storage_clear_all) begin
      \$98  = 1'h0;
    end else if (\$84 ) begin
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
            \$98  = 1'h1;
      endcase
    end
    if (cap_storage_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              /* empty */;
          4'h4:
              \$98  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$98  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$99  = valid5;
    if (cap_storage_clear_all) begin
      \$99  = 1'h0;
    end else if (\$84 ) begin
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
            \$99  = 1'h1;
      endcase
    end
    if (cap_storage_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$99  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$99  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$100  = valid6;
    if (cap_storage_clear_all) begin
      \$100  = 1'h0;
    end else if (\$84 ) begin
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
            \$100  = 1'h1;
      endcase
    end
    if (cap_storage_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$100  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$100  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$101  = valid7;
    if (cap_storage_clear_all) begin
      \$101  = 1'h0;
    end else if (\$84 ) begin
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
            \$101  = 1'h1;
      endcase
    end
    if (cap_storage_lk) begin
      if (\$85 ) begin
      end else if (\$87 ) begin
        casez (hit)
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
              \$101  = 1'h0;
        endcase
      end
    end
    if (rst) begin
      \$101  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$102  = point0;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$102  = cap_storage_ins_point;
      endcase
    end
    if (rst) begin
      \$102  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$103  = point1;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$103  = cap_storage_ins_point;
      endcase
    end
    if (rst) begin
      \$103  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$104  = point2;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$104  = cap_storage_ins_point;
      endcase
    end
    if (rst) begin
      \$104  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$105  = point3;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$105  = cap_storage_ins_point;
      endcase
    end
    if (rst) begin
      \$105  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$106  = point4;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$106  = cap_storage_ins_point;
      endcase
    end
    if (rst) begin
      \$106  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$107  = point5;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$107  = cap_storage_ins_point;
      endcase
    end
    if (rst) begin
      \$107  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$108  = point6;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$108  = cap_storage_ins_point;
      endcase
    end
    if (rst) begin
      \$108  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$109  = point7;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$109  = cap_storage_ins_point;
      endcase
    end
    if (rst) begin
      \$109  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$110  = peer0;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$110  = cap_storage_ins_peer;
      endcase
    end
    if (rst) begin
      \$110  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$111  = peer1;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$111  = cap_storage_ins_peer;
      endcase
    end
    if (rst) begin
      \$111  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$112  = peer2;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$112  = cap_storage_ins_peer;
      endcase
    end
    if (rst) begin
      \$112  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$113  = peer3;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$113  = cap_storage_ins_peer;
      endcase
    end
    if (rst) begin
      \$113  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$114  = peer4;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$114  = cap_storage_ins_peer;
      endcase
    end
    if (rst) begin
      \$114  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$115  = peer5;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$115  = cap_storage_ins_peer;
      endcase
    end
    if (rst) begin
      \$115  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$116  = peer6;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$116  = cap_storage_ins_peer;
      endcase
    end
    if (rst) begin
      \$116  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$117  = peer7;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$117  = cap_storage_ins_peer;
      endcase
    end
    if (rst) begin
      \$117  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$118  = dir0;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$118  = cap_storage_ins_dir;
      endcase
    end
    if (rst) begin
      \$118  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$119  = dir1;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$119  = cap_storage_ins_dir;
      endcase
    end
    if (rst) begin
      \$119  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$120  = dir2;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$120  = cap_storage_ins_dir;
      endcase
    end
    if (rst) begin
      \$120  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$121  = dir3;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$121  = cap_storage_ins_dir;
      endcase
    end
    if (rst) begin
      \$121  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$122  = dir4;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$122  = cap_storage_ins_dir;
      endcase
    end
    if (rst) begin
      \$122  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$123  = dir5;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$123  = cap_storage_ins_dir;
      endcase
    end
    if (rst) begin
      \$123  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$124  = dir6;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$124  = cap_storage_ins_dir;
      endcase
    end
    if (rst) begin
      \$124  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$125  = dir7;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$125  = cap_storage_ins_dir;
      endcase
    end
    if (rst) begin
      \$125  = 2'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$126  = budget0;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$126  = cap_storage_ins_budget;
      endcase
    end
    if (cap_storage_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              \$126  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$126  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$127  = budget1;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$127  = cap_storage_ins_budget;
      endcase
    end
    if (cap_storage_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              \$127  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$127  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$128  = budget2;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$128  = cap_storage_ins_budget;
      endcase
    end
    if (cap_storage_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              \$128  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$128  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$129  = budget3;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$129  = cap_storage_ins_budget;
      endcase
    end
    if (cap_storage_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              \$129  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$129  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$130  = budget4;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$130  = cap_storage_ins_budget;
      endcase
    end
    if (cap_storage_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
          4'h0:
              /* empty */;
          4'h1:
              /* empty */;
          4'h2:
              /* empty */;
          4'h3:
              /* empty */;
          4'h4:
              \$130  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$130  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$131  = budget5;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$131  = cap_storage_ins_budget;
      endcase
    end
    if (cap_storage_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$131  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$131  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$132  = budget6;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$132  = cap_storage_ins_budget;
      endcase
    end
    if (cap_storage_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$132  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$132  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$133  = budget7;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$133  = cap_storage_ins_budget;
      endcase
    end
    if (cap_storage_lk) begin
      (* full_case = 32'd1 *)
      if (\$85 ) begin
      end else if (\$87 ) begin
      end else if (\$89 ) begin
      end else if (\$91 ) begin
      end else begin
        casez (hit)
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
              \$133  = \$93 [23:0];
        endcase
      end
    end
    if (rst) begin
      \$133  = 24'h000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$134  = expiry0;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$134  = cap_storage_ins_expiry;
      endcase
    end
    if (rst) begin
      \$134  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$135  = expiry1;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$135  = cap_storage_ins_expiry;
      endcase
    end
    if (rst) begin
      \$135  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$136  = expiry2;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$136  = cap_storage_ins_expiry;
      endcase
    end
    if (rst) begin
      \$136  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$137  = expiry3;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$137  = cap_storage_ins_expiry;
      endcase
    end
    if (rst) begin
      \$137  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$138  = expiry4;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$138  = cap_storage_ins_expiry;
      endcase
    end
    if (rst) begin
      \$138  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$139  = expiry5;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$139  = cap_storage_ins_expiry;
      endcase
    end
    if (rst) begin
      \$139  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$140  = expiry6;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$140  = cap_storage_ins_expiry;
      endcase
    end
    if (rst) begin
      \$140  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$141  = expiry7;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$141  = cap_storage_ins_expiry;
      endcase
    end
    if (rst) begin
      \$141  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$142  = etag0;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            \$142  = cap_storage_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$142  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$143  = etag1;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$143  = cap_storage_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$143  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$144  = etag2;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$144  = cap_storage_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$144  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$145  = etag3;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            /* empty */;
        4'h3:
            \$145  = cap_storage_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$145  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$146  = etag4;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$146  = cap_storage_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$146  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$147  = etag5;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$147  = cap_storage_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$147  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$148  = etag6;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$148  = cap_storage_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$148  = 16'h0000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$6 ) begin end
    \$149  = etag7;
    if (cap_storage_clear_all) begin
    end else if (\$84 ) begin
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
            \$149  = cap_storage_ins_epoch_tag;
      endcase
    end
    if (rst) begin
      \$149  = 16'h0000;
    end
  end
endmodule

module \governor_core.epoch (epoch_quorum_ok, epoch_new_epoch, epoch_host_refused, clk, rst, epoch_epoch, epoch_commit);
  reg \$auto$verilog_backend.cc:2355:dump_module$7  = 0;
  wire \$1 ;
  reg [255:0] \$2 ;
  input clk;
  wire clk;
  input epoch_commit;
  wire epoch_commit;
  output [255:0] epoch_epoch;
  reg [255:0] epoch_epoch = 256'h0000000000000000000000000000000000000000000000000000000000000000;
  wire [15:0] epoch_epoch_tag;
  input epoch_host_refused;
  wire epoch_host_refused;
  wire epoch_host_wr;
  input [255:0] epoch_new_epoch;
  wire [255:0] epoch_new_epoch;
  input epoch_quorum_ok;
  wire epoch_quorum_ok;
  input rst;
  wire rst;
  assign \$1  = epoch_commit & epoch_quorum_ok;
  always @(posedge clk)
    epoch_epoch <= \$2 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$7 ) begin end
    \$2  = epoch_epoch;
    if (\$1 ) begin
      \$2  = epoch_new_epoch;
    end
    if (rst) begin
      \$2  = 256'h0000000000000000000000000000000000000000000000000000000000000000;
    end
  end
  assign epoch_epoch_tag = epoch_epoch[15:0];
  assign epoch_host_wr = epoch_host_refused;
endmodule

module \governor_core.halt (halt_tamper, halt_cmd_halt, halt_cmd_throttle, halt_local_trip, halt_clear, halt_cmd_exclude, clk, rst, halt_tick, halt_hb_ok, halt_clear_authorized, halt_hb_expired, halt_no_first_hb, halt_pwrbrk, halt_perst, halt_pwr_en, halt_ports_closed, halt_loop_lost, halt_state, halt_cause, halt_switch_open
, halt_excluded, halt_boot_timer, halt_loop_sense);
  reg \$auto$verilog_backend.cc:2355:dump_module$8  = 0;
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
  wire \$33 ;
  wire \$34 ;
  wire \$35 ;
  wire \$36 ;
  wire \$37 ;
  wire [20:0] \$38 ;
  wire \$39 ;
  wire \$4 ;
  wire [20:0] \$40 ;
  wire [20:0] \$41 ;
  wire \$42 ;
  wire [20:0] \$43 ;
  wire \$44 ;
  wire \$45 ;
  wire \$46 ;
  wire \$47 ;
  wire \$48 ;
  wire \$49 ;
  wire \$5 ;
  wire \$50 ;
  wire \$51 ;
  wire \$52 ;
  wire \$53 ;
  wire \$54 ;
  wire [16:0] \$55 ;
  wire \$56 ;
  wire \$57 ;
  wire \$58 ;
  wire \$59 ;
  wire \$6 ;
  wire \$60 ;
  wire \$61 ;
  wire \$62 ;
  wire \$63 ;
  reg \$64 ;
  reg \$65 ;
  reg [2:0] \$66 ;
  reg [2:0] \$67 ;
  reg \$68 ;
  reg [19:0] \$69 ;
  wire \$7 ;
  reg \$70 ;
  reg \$71 ;
  reg [15:0] \$72 ;
  wire \$8 ;
  wire \$9 ;
  input clk;
  wire clk;
  output [15:0] halt_boot_timer;
  reg [15:0] halt_boot_timer = 16'h0000;
  output [2:0] halt_cause;
  reg [2:0] halt_cause = 3'h0;
  input halt_clear;
  wire halt_clear;
  input halt_clear_authorized;
  wire halt_clear_authorized;
  input halt_cmd_exclude;
  wire halt_cmd_exclude;
  input halt_cmd_halt;
  wire halt_cmd_halt;
  input halt_cmd_throttle;
  wire halt_cmd_throttle;
  output halt_excluded;
  reg halt_excluded = 1'h0;
  input halt_hb_expired;
  wire halt_hb_expired;
  input halt_hb_ok;
  wire halt_hb_ok;
  reg halt_hb_seen = 1'h0;
  input halt_local_trip;
  wire halt_local_trip;
  input halt_loop_lost;
  wire halt_loop_lost;
  input halt_loop_sense;
  wire halt_loop_sense;
  output halt_no_first_hb;
  wire halt_no_first_hb;
  output halt_perst;
  wire halt_perst;
  output halt_ports_closed;
  wire halt_ports_closed;
  output halt_pwr_en;
  wire halt_pwr_en;
  output halt_pwrbrk;
  wire halt_pwrbrk;
  reg halt_rung_nv = 1'h0;
  reg halt_rung_nv_safe = 1'h0;
  output [2:0] halt_state;
  reg [2:0] halt_state = 3'h0;
  output halt_switch_open;
  reg halt_switch_open = 1'h1;
  input halt_tamper;
  wire halt_tamper;
  input halt_tick;
  wire halt_tick;
  reg [19:0] halt_timer = 20'h00000;
  input rst;
  wire rst;
  assign \$28  = halt_cmd_exclude & \$27 ;
  assign \$29  = ! halt_cause;
  assign \$30  = \$28  & \$29 ;
  assign \$31  = halt_state == 2'h2;
  assign \$32  = halt_tick & \$31 ;
  assign \$33  = halt_state == 2'h3;
  assign \$34  = halt_tick & \$33 ;
  assign \$35  = halt_cause != 2'h3;
  assign \$36  = ~ halt_loop_lost;
  assign \$37  = halt_loop_sense & \$36 ;
  assign \$38  = halt_timer + 1'h1;
  assign \$39  = \$38  >= 15'h7530;
  assign \$40  = halt_timer + 1'h1;
  assign \$41  = halt_timer + 1'h1;
  assign \$42  = \$41  >= 19'h493e0;
  assign \$43  = halt_timer + 1'h1;
  assign \$44  = halt_tamper | halt_cmd_halt;
  assign \$45  = ~ halt_hb_seen;
  assign \$46  = ! halt_state;
  assign \$47  = \$45  & \$46 ;
  assign \$48  = ! halt_cause;
  assign \$49  = \$47  & \$48 ;
  assign \$50  = ~ halt_hb_ok;
  assign \$51  = \$49  & \$50 ;
  assign \$52  = \$51  & halt_tick;
  assign \$53  = halt_boot_timer != 16'hffff;
  assign \$54  = \$52  & \$53 ;
  assign \$55  = halt_boot_timer + 1'h1;
  assign \$56  = ~ halt_hb_seen;
  assign \$57  = halt_boot_timer >= 13'h1388;
  assign halt_no_first_hb = \$56  & \$57 ;
  assign halt_pwrbrk = halt_state != 1'h1;
  assign \$58  = ! halt_state;
  assign \$59  = halt_state == 2'h3;
  assign \$60  = \$58  | \$59 ;
  assign \$61  = halt_state == 3'h4;
  assign halt_perst = \$60  | \$61 ;
  assign \$62  = | halt_state;
  assign \$63  = halt_state != 3'h4;
  assign halt_pwr_en = \$62  & \$63 ;
  assign halt_ports_closed = halt_state != 1'h1;
  always @(posedge clk)
    halt_rung_nv <= \$64 ;
  always @(posedge clk)
    halt_rung_nv_safe <= \$65 ;
  always @(posedge clk)
    halt_state <= \$66 ;
  always @(posedge clk)
    halt_cause <= \$67 ;
  always @(posedge clk)
    halt_switch_open <= \$68 ;
  always @(posedge clk)
    halt_timer <= \$69 ;
  always @(posedge clk)
    halt_hb_seen <= \$70 ;
  always @(posedge clk)
    halt_excluded <= \$71 ;
  always @(posedge clk)
    halt_boot_timer <= \$72 ;
  assign \$1  = halt_state == 2'h3;
  assign \$2  = halt_state == 3'h4;
  assign \$3  = \$1  | \$2 ;
  assign \$4  = halt_state == 3'h4;
  assign \$5  = halt_clear & halt_clear_authorized;
  assign \$6  = | halt_state;
  assign \$7  = \$5  & \$6 ;
  assign \$8  = ! halt_state;
  assign \$9  = halt_rung_nv & \$8 ;
  assign \$10  = halt_state == 1'h1;
  assign \$11  = halt_state == 2'h2;
  assign \$12  = \$10  | \$11 ;
  assign \$13  = halt_loop_lost & \$12 ;
  assign \$14  = halt_state == 3'h4;
  assign \$15  = halt_cmd_halt & \$14 ;
  assign \$16  = halt_state == 1'h1;
  assign \$17  = halt_state == 2'h2;
  assign \$18  = \$16  | \$17 ;
  assign \$19  = halt_hb_expired & \$18 ;
  assign \$20  = halt_local_trip | halt_cmd_throttle;
  assign \$21  = halt_state == 1'h1;
  assign \$22  = \$20  & \$21 ;
  assign \$23  = ! halt_state;
  assign \$24  = ! halt_cause;
  assign \$25  = \$23  & \$24 ;
  assign \$26  = \$25  & halt_hb_ok;
  assign \$27  = ! halt_state;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$8 ) begin end
    \$64  = halt_rung_nv;
    if (\$3 ) begin
      \$64  = 1'h1;
    end
    if (halt_tamper) begin
      \$64  = 1'h1;
    end else if (\$7 ) begin
      \$64  = 1'h0;
    end else if (\$9 ) begin
    end else if (\$13 ) begin
      \$64  = 1'h1;
    end else if (\$15 ) begin
    end else if (halt_cmd_halt) begin
      \$64  = 1'h1;
    end else if (\$19 ) begin
      \$64  = 1'h1;
    end else if (\$22 ) begin
    end else if (\$26 ) begin
    end else if (\$30 ) begin
    end else if (\$32 ) begin
      if (\$39 ) begin
        \$64  = 1'h1;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$8 ) begin end
    \$65  = halt_rung_nv_safe;
    if (\$4 ) begin
      \$65  = 1'h1;
    end
    if (halt_tamper) begin
      \$65  = 1'h1;
    end else if (\$7 ) begin
      \$65  = 1'h0;
    end else if (\$9 ) begin
    end else if (\$13 ) begin
    end else if (\$15 ) begin
    end else if (halt_cmd_halt) begin
    end else if (\$19 ) begin
    end else if (\$22 ) begin
    end else if (\$26 ) begin
    end else if (\$30 ) begin
    end else if (\$32 ) begin
    end else if (\$34 ) begin
      if (\$42 ) begin
        \$65  = 1'h1;
      end
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$8 ) begin end
    \$66  = halt_state;
    if (halt_tamper) begin
      \$66  = 3'h4;
    end else if (\$7 ) begin
      \$66  = 3'h0;
    end else if (\$9 ) begin
      (* full_case = 32'd1 *)
      if (halt_rung_nv_safe) begin
        \$66  = 3'h4;
      end else begin
        \$66  = 3'h3;
      end
    end else if (\$13 ) begin
      \$66  = 3'h3;
    end else if (\$15 ) begin
    end else if (halt_cmd_halt) begin
      \$66  = 3'h3;
    end else if (\$19 ) begin
      \$66  = 3'h3;
    end else if (\$22 ) begin
      \$66  = 3'h2;
    end else if (\$26 ) begin
      if (\$37 ) begin
        \$66  = 3'h1;
      end
    end else if (\$30 ) begin
    end else if (\$32 ) begin
      if (\$39 ) begin
        \$66  = 3'h3;
      end
    end else if (\$34 ) begin
      if (\$42 ) begin
        \$66  = 3'h4;
      end
    end
    if (rst) begin
      \$66  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$8 ) begin end
    \$67  = halt_cause;
    if (halt_tamper) begin
      \$67  = 3'h3;
    end else if (\$7 ) begin
      \$67  = 3'h0;
    end else if (\$9 ) begin
      \$67  = 3'h5;
    end else if (\$13 ) begin
      \$67  = 3'h1;
    end else if (\$15 ) begin
      if (\$35 ) begin
        \$67  = 3'h4;
      end
    end else if (halt_cmd_halt) begin
      \$67  = 3'h4;
    end else if (\$19 ) begin
      \$67  = 3'h2;
    end else if (\$22 ) begin
      \$67  = 3'h2;
    end
    if (rst) begin
      \$67  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$8 ) begin end
    \$68  = halt_switch_open;
    if (halt_tamper) begin
      \$68  = 1'h1;
    end else if (\$7 ) begin
    end else if (\$9 ) begin
      \$68  = 1'h1;
    end else if (\$13 ) begin
      \$68  = 1'h1;
    end else if (\$15 ) begin
      \$68  = 1'h1;
    end else if (halt_cmd_halt) begin
      \$68  = 1'h1;
    end else if (\$19 ) begin
    end else if (\$22 ) begin
    end else if (\$26 ) begin
      \$68  = 1'h0;
    end else if (\$30 ) begin
      \$68  = 1'h0;
    end
    if (rst) begin
      \$68  = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$8 ) begin end
    \$69  = halt_timer;
    if (halt_tamper) begin
    end else if (\$7 ) begin
      \$69  = 20'h00000;
    end else if (\$9 ) begin
      \$69  = 20'h00000;
    end else if (\$13 ) begin
      \$69  = 20'h00000;
    end else if (\$15 ) begin
    end else if (halt_cmd_halt) begin
      \$69  = 20'h00000;
    end else if (\$19 ) begin
      \$69  = 20'h00000;
    end else if (\$22 ) begin
      \$69  = 20'h00000;
    end else if (\$26 ) begin
    end else if (\$30 ) begin
    end else if (\$32 ) begin
      (* full_case = 32'd1 *)
      if (\$39 ) begin
        \$69  = 20'h00000;
      end else begin
        \$69  = \$40 [19:0];
      end
    end else if (\$34 ) begin
      (* full_case = 32'd1 *)
      if (\$42 ) begin
        \$69  = 20'h00000;
      end else begin
        \$69  = \$43 [19:0];
      end
    end
    if (rst) begin
      \$69  = 20'h00000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$8 ) begin end
    \$70  = halt_hb_seen;
    if (halt_tamper) begin
    end else if (\$7 ) begin
    end else if (\$9 ) begin
    end else if (\$13 ) begin
    end else if (\$15 ) begin
    end else if (halt_cmd_halt) begin
    end else if (\$19 ) begin
    end else if (\$22 ) begin
    end else if (\$26 ) begin
      \$70  = 1'h1;
    end
    if (rst) begin
      \$70  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$8 ) begin end
    \$71  = halt_excluded;
    if (halt_tamper) begin
    end else if (\$7 ) begin
    end else if (\$9 ) begin
    end else if (\$13 ) begin
    end else if (\$15 ) begin
    end else if (halt_cmd_halt) begin
    end else if (\$19 ) begin
    end else if (\$22 ) begin
    end else if (\$26 ) begin
      \$71  = 1'h0;
    end else if (\$30 ) begin
      \$71  = 1'h1;
    end
    if (\$44 ) begin
      \$71  = 1'h0;
    end
    if (rst) begin
      \$71  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$8 ) begin end
    \$72  = halt_boot_timer;
    if (\$54 ) begin
      \$72  = \$55 [15:0];
    end
    if (rst) begin
      \$72  = 16'h0000;
    end
  end
endmodule

module \governor_core.hb (hb_window, clk, rst, hb_tick, hb_expired, hb_remaining, hb_hb_valid);
  reg \$auto$verilog_backend.cc:2355:dump_module$9  = 0;
  wire \$1 ;
  wire \$2 ;
  wire \$3 ;
  wire [32:0] \$4 ;
  reg [31:0] \$5 ;
  wire [31:0] clamped;
  input clk;
  wire clk;
  output hb_expired;
  wire hb_expired;
  input hb_hb_valid;
  wire hb_hb_valid;
  output [31:0] hb_remaining;
  reg [31:0] hb_remaining = 32'd0;
  input hb_tick;
  wire hb_tick;
  input [31:0] hb_window;
  wire [31:0] hb_window;
  input rst;
  wire rst;
  assign \$3  = hb_tick & \$2 ;
  assign \$4  = hb_remaining - 1'h1;
  always @(posedge clk)
    hb_remaining <= \$5 ;
  assign \$1  = hb_window > 13'h1388;
  assign clamped = \$1  ? 32'd5000 : hb_window;
  assign hb_expired = ! hb_remaining;
  assign \$2  = | hb_remaining;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$9 ) begin end
    \$5  = hb_remaining;
    if (hb_hb_valid) begin
      \$5  = clamped;
    end else if (\$3 ) begin
      \$5  = \$4 [31:0];
    end
    if (rst) begin
      \$5  = 32'd0;
    end
  end
endmodule

module \governor_core.life (life_load, life_advance, life_advance_to, life_debug_req, clk, rst, life_debug_grant, life_state, life_fuse_state);
  reg \$auto$verilog_backend.cc:2355:dump_module$10  = 0;
  wire \$1 ;
  reg [1:0] \$10 ;
  wire \$2 ;
  wire \$3 ;
  wire \$4 ;
  wire \$5 ;
  wire \$6 ;
  wire \$7 ;
  wire \$8 ;
  reg \$9 ;
  input clk;
  wire clk;
  input life_advance;
  wire life_advance;
  wire life_advance_refused;
  input [1:0] life_advance_to;
  wire [1:0] life_advance_to;
  output life_debug_grant;
  wire life_debug_grant;
  wire life_debug_refused;
  input life_debug_req;
  wire life_debug_req;
  input [1:0] life_fuse_state;
  wire [1:0] life_fuse_state;
  input life_load;
  wire life_load;
  reg life_loaded = 1'h0;
  output [1:0] life_state;
  reg [1:0] life_state = 2'h0;
  input rst;
  wire rst;
  assign \$1  = life_fuse_state > life_state;
  assign \$2  = life_advance_to > life_state;
  assign \$3  = life_advance_to <= life_state;
  assign life_advance_refused = life_advance & \$3 ;
  assign \$4  = life_debug_req & life_loaded;
  assign \$5  = life_state < 2'h2;
  assign life_debug_grant = \$4  & \$5 ;
  assign \$6  = life_state < 2'h2;
  assign \$7  = life_loaded & \$6 ;
  assign \$8  = ~ \$7 ;
  assign life_debug_refused = life_debug_req & \$8 ;
  always @(posedge clk)
    life_loaded <= \$9 ;
  always @(posedge clk)
    life_state <= \$10 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$10 ) begin end
    \$9  = life_loaded;
    if (life_load) begin
      \$9  = 1'h1;
    end
    if (rst) begin
      \$9  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$10 ) begin end
    \$10  = life_state;
    if (life_load) begin
      if (\$1 ) begin
        \$10  = life_fuse_state;
      end
    end else if (life_advance) begin
      if (\$2 ) begin
        \$10  = life_advance_to;
      end
    end
    if (rst) begin
      \$10  = 2'h0;
    end
  end
endmodule

module \governor_core.loop (sample, clk, rst, loop_lost, loop_out_open, loop_sense);
  reg \$auto$verilog_backend.cc:2355:dump_module$11  = 0;
  wire \$1 ;
  wire \$2 ;
  wire [2:0] \$3 ;
  reg [1:0] \$4 ;
  input clk;
  wire clk;
  reg [1:0] count = 2'h0;
  output loop_lost;
  wire loop_lost;
  input loop_out_open;
  wire loop_out_open;
  input loop_sense;
  wire loop_sense;
  input rst;
  wire rst;
  input sample;
  wire sample;
  wire switch_open;
  always @(posedge clk)
    count <= \$4 ;
  assign loop_lost = count >= 2'h2;
  assign \$1  = ~ loop_sense;
  assign \$2  = count < 2'h2;
  assign \$3  = count + 1'h1;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$11 ) begin end
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
  assign switch_open = loop_out_open;
endmodule

module \governor_core.mbox (mbox_frame_seq, mbox_key_slot, mbox_cmd, mbox_signed_cmd, mbox_epoch_match, mbox_epoch_exempt, mbox_needs_run, mbox_sig_done, mbox_sig_ok, clk, rst, mbox_epoch_advanced, mbox_running, mbox_verify_req, mbox_dispatch, mbox_status, seq0, mbox_cmd_out, mbox_doorbell);
  reg \$auto$verilog_backend.cc:2355:dump_module$12  = 0;
  reg [63:0] \$1 ;
  wire \$10 ;
  wire \$11 ;
  wire \$12 ;
  reg [2:0] \$13 ;
  reg \$14 ;
  reg [63:0] \$15 ;
  reg [63:0] \$16 ;
  reg [63:0] \$17 ;
  reg [63:0] \$18 ;
  reg [63:0] \$19 ;
  wire \$2 ;
  reg [63:0] \$20 ;
  reg [63:0] \$21 ;
  reg [63:0] \$22 ;
  reg [7:0] \$23 ;
  wire \$3 ;
  wire \$4 ;
  wire \$5 ;
  wire \$6 ;
  wire \$7 ;
  wire \$8 ;
  wire \$9 ;
  input clk;
  wire clk;
  reg fsm_state = 1'h0;
  input [7:0] mbox_cmd;
  wire [7:0] mbox_cmd;
  output [7:0] mbox_cmd_out;
  reg [7:0] mbox_cmd_out = 8'h00;
  output mbox_dispatch;
  reg mbox_dispatch;
  input mbox_doorbell;
  wire mbox_doorbell;
  input mbox_epoch_advanced;
  wire mbox_epoch_advanced;
  input mbox_epoch_exempt;
  wire mbox_epoch_exempt;
  input mbox_epoch_match;
  wire mbox_epoch_match;
  input [63:0] mbox_frame_seq;
  wire [63:0] mbox_frame_seq;
  input [2:0] mbox_key_slot;
  wire [2:0] mbox_key_slot;
  input mbox_needs_run;
  wire mbox_needs_run;
  input mbox_running;
  wire mbox_running;
  input mbox_sig_done;
  wire mbox_sig_done;
  input mbox_sig_ok;
  wire mbox_sig_ok;
  input [7:0] mbox_signed_cmd;
  wire [7:0] mbox_signed_cmd;
  output [2:0] mbox_status;
  reg [2:0] mbox_status = 3'h0;
  output mbox_verify_req;
  reg mbox_verify_req;
  input rst;
  wire rst;
  output [63:0] seq0;
  reg [63:0] seq0 = 64'h0000000000000000;
  reg [63:0] seq1 = 64'h0000000000000000;
  reg [63:0] seq2 = 64'h0000000000000000;
  reg [63:0] seq3 = 64'h0000000000000000;
  reg [63:0] seq4 = 64'h0000000000000000;
  reg [63:0] seq5 = 64'h0000000000000000;
  reg [63:0] seq6 = 64'h0000000000000000;
  reg [63:0] seq7 = 64'h0000000000000000;
  wire seq_ok;
  assign seq_ok = \$1  < mbox_frame_seq;
  assign \$2  = mbox_signed_cmd == mbox_cmd;
  assign \$3  = mbox_sig_ok & \$2 ;
  assign \$4  = ! fsm_state;
  assign \$6  = ~ seq_ok;
  assign \$7  = mbox_epoch_match | mbox_epoch_exempt;
  assign \$8  = ~ \$7 ;
  assign \$9  = ~ mbox_running;
  assign \$10  = mbox_needs_run & \$9 ;
  assign \$11  = mbox_signed_cmd == mbox_cmd;
  assign \$12  = mbox_sig_ok & \$11 ;
  always @(posedge clk)
    mbox_status <= \$13 ;
  always @(posedge clk)
    fsm_state <= \$14 ;
  always @(posedge clk)
    seq0 <= \$15 ;
  always @(posedge clk)
    seq1 <= \$16 ;
  always @(posedge clk)
    seq2 <= \$17 ;
  always @(posedge clk)
    seq3 <= \$18 ;
  always @(posedge clk)
    seq4 <= \$19 ;
  always @(posedge clk)
    seq5 <= \$20 ;
  always @(posedge clk)
    seq6 <= \$21 ;
  always @(posedge clk)
    seq7 <= \$22 ;
  always @(posedge clk)
    mbox_cmd_out <= \$23 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    (* full_case = 32'd1 *)
    casez (mbox_key_slot)
      3'h0:
          \$1  = seq0;
      3'h1:
          \$1  = seq1;
      3'h2:
          \$1  = seq2;
      3'h3:
          \$1  = seq3;
      3'h4:
          \$1  = seq4;
      3'h5:
          \$1  = seq5;
      3'h6:
          \$1  = seq6;
      3'h7:
          \$1  = seq7;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    mbox_verify_req = 1'h0;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          mbox_verify_req = 1'h1;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    mbox_dispatch = 1'h0;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (mbox_sig_done) begin
            if (\$3 ) begin
              mbox_dispatch = 1'h1;
            end
          end
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$13  = mbox_status;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          if (mbox_doorbell) begin
            (* full_case = 32'd1 *)
            if (\$6 ) begin
              \$13  = 3'h4;
            end else if (\$8 ) begin
              \$13  = 3'h5;
            end else if (\$10 ) begin
              \$13  = 3'h6;
            end else begin
              \$13  = 3'h1;
            end
          end
      1'h1:
          if (mbox_sig_done) begin
            (* full_case = 32'd1 *)
            if (\$12 ) begin
              \$13  = 3'h2;
            end else if (mbox_sig_ok) begin
              \$13  = 3'h7;
            end else begin
              \$13  = 3'h3;
            end
          end
    endcase
    if (rst) begin
      \$13  = 3'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$14  = fsm_state;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          if (mbox_doorbell) begin
            (* full_case = 32'd1 *)
            if (\$6 ) begin
            end else if (\$8 ) begin
            end else if (\$10 ) begin
            end else begin
              \$14  = 1'h1;
            end
          end
      1'h1:
          if (mbox_sig_done) begin
            \$14  = 1'h0;
          end
    endcase
    if (rst) begin
      \$14  = 1'h0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$15  = seq0;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (mbox_sig_done) begin
            if (\$12 ) begin
              casez (mbox_key_slot)
                3'h0:
                    \$15  = mbox_frame_seq;
              endcase
            end
          end
    endcase
    if (mbox_epoch_advanced) begin
      \$15  = 64'h0000000000000000;
    end
    if (rst) begin
      \$15  = 64'h0000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$16  = seq1;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (mbox_sig_done) begin
            if (\$12 ) begin
              casez (mbox_key_slot)
                3'h0:
                    /* empty */;
                3'h1:
                    \$16  = mbox_frame_seq;
              endcase
            end
          end
    endcase
    if (mbox_epoch_advanced) begin
      \$16  = 64'h0000000000000000;
    end
    if (rst) begin
      \$16  = 64'h0000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$17  = seq2;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (mbox_sig_done) begin
            if (\$12 ) begin
              casez (mbox_key_slot)
                3'h0:
                    /* empty */;
                3'h1:
                    /* empty */;
                3'h2:
                    \$17  = mbox_frame_seq;
              endcase
            end
          end
    endcase
    if (mbox_epoch_advanced) begin
      \$17  = 64'h0000000000000000;
    end
    if (rst) begin
      \$17  = 64'h0000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$18  = seq3;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (mbox_sig_done) begin
            if (\$12 ) begin
              casez (mbox_key_slot)
                3'h0:
                    /* empty */;
                3'h1:
                    /* empty */;
                3'h2:
                    /* empty */;
                3'h3:
                    \$18  = mbox_frame_seq;
              endcase
            end
          end
    endcase
    if (mbox_epoch_advanced) begin
      \$18  = 64'h0000000000000000;
    end
    if (rst) begin
      \$18  = 64'h0000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$19  = seq4;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (mbox_sig_done) begin
            if (\$12 ) begin
              casez (mbox_key_slot)
                3'h0:
                    /* empty */;
                3'h1:
                    /* empty */;
                3'h2:
                    /* empty */;
                3'h3:
                    /* empty */;
                3'h4:
                    \$19  = mbox_frame_seq;
              endcase
            end
          end
    endcase
    if (mbox_epoch_advanced) begin
      \$19  = 64'h0000000000000000;
    end
    if (rst) begin
      \$19  = 64'h0000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$20  = seq5;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (mbox_sig_done) begin
            if (\$12 ) begin
              casez (mbox_key_slot)
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
                3'h5:
                    \$20  = mbox_frame_seq;
              endcase
            end
          end
    endcase
    if (mbox_epoch_advanced) begin
      \$20  = 64'h0000000000000000;
    end
    if (rst) begin
      \$20  = 64'h0000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$21  = seq6;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (mbox_sig_done) begin
            if (\$12 ) begin
              casez (mbox_key_slot)
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
                3'h5:
                    /* empty */;
                3'h6:
                    \$21  = mbox_frame_seq;
              endcase
            end
          end
    endcase
    if (mbox_epoch_advanced) begin
      \$21  = 64'h0000000000000000;
    end
    if (rst) begin
      \$21  = 64'h0000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$22  = seq7;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (mbox_sig_done) begin
            if (\$12 ) begin
              (* full_case = 32'd1 *)
              casez (mbox_key_slot)
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
                3'h5:
                    /* empty */;
                3'h6:
                    /* empty */;
                3'h7:
                    \$22  = mbox_frame_seq;
              endcase
            end
          end
    endcase
    if (mbox_epoch_advanced) begin
      \$22  = 64'h0000000000000000;
    end
    if (rst) begin
      \$22  = 64'h0000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$12 ) begin end
    \$23  = mbox_cmd_out;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (mbox_sig_done) begin
            if (\$12 ) begin
              \$23  = mbox_cmd;
            end
          end
    endcase
    if (rst) begin
      \$23  = 8'h00;
    end
  end
  assign \$5  = fsm_state;
endmodule

module \governor_core.meas0 (meas0_data, meas0_hash_done, meas0_hash_out, clk, rst, meas0_hash_req, meas0_value, meas0_extend);
  reg \$auto$verilog_backend.cc:2355:dump_module$13  = 0;
  wire \$1 ;
  wire \$2 ;
  reg \$3 ;
  reg [255:0] \$4 ;
  input clk;
  wire clk;
  reg fsm_state = 1'h0;
  reg meas0_busy;
  input [255:0] meas0_data;
  wire [255:0] meas0_data;
  input meas0_extend;
  wire meas0_extend;
  input meas0_hash_done;
  wire meas0_hash_done;
  wire [511:0] meas0_hash_in;
  input [255:0] meas0_hash_out;
  wire [255:0] meas0_hash_out;
  output meas0_hash_req;
  reg meas0_hash_req;
  output [255:0] meas0_value;
  reg [255:0] meas0_value = 256'h0000000000000000000000000000000000000000000000000000000000000000;
  input rst;
  wire rst;
  always @(posedge clk)
    fsm_state <= \$3 ;
  always @(posedge clk)
    meas0_value <= \$4 ;
  assign \$1  = ! fsm_state;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$13 ) begin end
    \$4  = meas0_value;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (meas0_hash_done) begin
            \$4  = meas0_hash_out;
          end
    endcase
    if (rst) begin
      \$4  = 256'h0000000000000000000000000000000000000000000000000000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$13 ) begin end
    meas0_hash_req = 1'h0;
    casez (fsm_state)
      1'h0:
          if (meas0_extend) begin
            meas0_hash_req = 1'h1;
          end
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$13 ) begin end
    meas0_busy = 1'h0;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          meas0_busy = 1'h1;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$13 ) begin end
    \$3  = fsm_state;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          if (meas0_extend) begin
            \$3  = 1'h1;
          end
      1'h1:
          if (meas0_hash_done) begin
            \$3  = 1'h0;
          end
    endcase
    if (rst) begin
      \$3  = 1'h0;
    end
  end
  assign meas0_hash_in = { meas0_value, meas0_data };
  assign \$2  = fsm_state;
endmodule

module \governor_core.meas1 (meas1_data, meas1_hash_done, meas1_hash_out, clk, rst, meas1_hash_req, meas1_value, meas1_extend);
  reg \$auto$verilog_backend.cc:2355:dump_module$14  = 0;
  wire \$1 ;
  wire \$2 ;
  reg \$3 ;
  reg [255:0] \$4 ;
  input clk;
  wire clk;
  reg fsm_state = 1'h0;
  reg meas1_busy;
  input [255:0] meas1_data;
  wire [255:0] meas1_data;
  input meas1_extend;
  wire meas1_extend;
  input meas1_hash_done;
  wire meas1_hash_done;
  wire [511:0] meas1_hash_in;
  input [255:0] meas1_hash_out;
  wire [255:0] meas1_hash_out;
  output meas1_hash_req;
  reg meas1_hash_req;
  output [255:0] meas1_value;
  reg [255:0] meas1_value = 256'h0000000000000000000000000000000000000000000000000000000000000000;
  input rst;
  wire rst;
  always @(posedge clk)
    fsm_state <= \$3 ;
  always @(posedge clk)
    meas1_value <= \$4 ;
  assign \$1  = ! fsm_state;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$14 ) begin end
    \$4  = meas1_value;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          if (meas1_hash_done) begin
            \$4  = meas1_hash_out;
          end
    endcase
    if (rst) begin
      \$4  = 256'h0000000000000000000000000000000000000000000000000000000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$14 ) begin end
    meas1_hash_req = 1'h0;
    casez (fsm_state)
      1'h0:
          if (meas1_extend) begin
            meas1_hash_req = 1'h1;
          end
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$14 ) begin end
    meas1_busy = 1'h0;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          /* empty */;
      1'h1:
          meas1_busy = 1'h1;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$14 ) begin end
    \$3  = fsm_state;
    (* full_case = 32'd1 *)
    casez (fsm_state)
      1'h0:
          if (meas1_extend) begin
            \$3  = 1'h1;
          end
      1'h1:
          if (meas1_hash_done) begin
            \$3  = 1'h0;
          end
    endcase
    if (rst) begin
      \$3  = 1'h0;
    end
  end
  assign meas1_hash_in = { meas1_value, meas1_data };
  assign \$2  = fsm_state;
endmodule

module \governor_core.meter (meter_add_tokens, meter_add_cycles, meter_add_in, meter_add_out, meter_strobe, clk, rst, meter_rd_slot, meter_rd_tokens, meter_rd_cycles, meter_rd_in, meter_rd_out, meter_slot);
  reg \$auto$verilog_backend.cc:2355:dump_module$15  = 0;
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
  input [47:0] meter_add_cycles;
  wire [47:0] meter_add_cycles;
  input [47:0] meter_add_in;
  wire [47:0] meter_add_in;
  input [47:0] meter_add_out;
  wire [47:0] meter_add_out;
  input [47:0] meter_add_tokens;
  wire [47:0] meter_add_tokens;
  wire meter_host_wr;
  wire meter_host_wr_refused;
  output [47:0] meter_rd_cycles;
  reg [47:0] meter_rd_cycles;
  output [47:0] meter_rd_in;
  reg [47:0] meter_rd_in;
  output [47:0] meter_rd_out;
  reg [47:0] meter_rd_out;
  input [1:0] meter_rd_slot;
  wire [1:0] meter_rd_slot;
  output [47:0] meter_rd_tokens;
  reg [47:0] meter_rd_tokens;
  input [1:0] meter_slot;
  wire [1:0] meter_slot;
  input meter_strobe;
  wire meter_strobe;
  input rst;
  wire rst;
  reg [47:0] tok0 = 48'h000000000000;
  reg [47:0] tok1 = 48'h000000000000;
  reg [47:0] tok2 = 48'h000000000000;
  reg [47:0] tok3 = 48'h000000000000;
  assign \$2  = \$1  + meter_add_tokens;
  assign \$4  = \$3  + meter_add_tokens;
  assign \$5  = \$2 [48] ? 48'hffffffffffff : \$4 [47:0];
  assign \$7  = \$6  + meter_add_cycles;
  assign \$9  = \$8  + meter_add_cycles;
  assign \$10  = \$7 [48] ? 48'hffffffffffff : \$9 [47:0];
  assign \$12  = \$11  + meter_add_in;
  assign \$14  = \$13  + meter_add_in;
  assign \$15  = \$12 [48] ? 48'hffffffffffff : \$14 [47:0];
  assign \$17  = \$16  + meter_add_out;
  assign \$19  = \$18  + meter_add_out;
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_rd_slot)
      2'h0:
          meter_rd_tokens = tok0;
      2'h1:
          meter_rd_tokens = tok1;
      2'h2:
          meter_rd_tokens = tok2;
      2'h3:
          meter_rd_tokens = tok3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_rd_slot)
      2'h0:
          meter_rd_cycles = cyc0;
      2'h1:
          meter_rd_cycles = cyc1;
      2'h2:
          meter_rd_cycles = cyc2;
      2'h3:
          meter_rd_cycles = cyc3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_rd_slot)
      2'h0:
          meter_rd_in = bin0;
      2'h1:
          meter_rd_in = bin1;
      2'h2:
          meter_rd_in = bin2;
      2'h3:
          meter_rd_in = bin3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    (* full_case = 32'd1 *)
    casez (meter_rd_slot)
      2'h0:
          meter_rd_out = bout0;
      2'h1:
          meter_rd_out = bout1;
      2'h2:
          meter_rd_out = bout2;
      2'h3:
          meter_rd_out = bout3;
    endcase
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$21  = tok0;
    if (meter_strobe) begin
      casez (meter_slot)
        2'h0:
            \$21  = \$5 ;
      endcase
    end
    if (rst) begin
      \$21  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$22  = tok1;
    if (meter_strobe) begin
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$23  = tok2;
    if (meter_strobe) begin
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$24  = tok3;
    if (meter_strobe) begin
      (* full_case = 32'd1 *)
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$25  = cyc0;
    if (meter_strobe) begin
      casez (meter_slot)
        2'h0:
            \$25  = \$10 ;
      endcase
    end
    if (rst) begin
      \$25  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$26  = cyc1;
    if (meter_strobe) begin
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$27  = cyc2;
    if (meter_strobe) begin
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$28  = cyc3;
    if (meter_strobe) begin
      (* full_case = 32'd1 *)
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$29  = bin0;
    if (meter_strobe) begin
      casez (meter_slot)
        2'h0:
            \$29  = \$15 ;
      endcase
    end
    if (rst) begin
      \$29  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$30  = bin1;
    if (meter_strobe) begin
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$31  = bin2;
    if (meter_strobe) begin
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$32  = bin3;
    if (meter_strobe) begin
      (* full_case = 32'd1 *)
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$33  = bout0;
    if (meter_strobe) begin
      casez (meter_slot)
        2'h0:
            \$33  = \$20 ;
      endcase
    end
    if (rst) begin
      \$33  = 48'h000000000000;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$34  = bout1;
    if (meter_strobe) begin
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$35  = bout2;
    if (meter_strobe) begin
      casez (meter_slot)
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
    if (\$auto$verilog_backend.cc:2355:dump_module$15 ) begin end
    \$36  = bout3;
    if (meter_strobe) begin
      (* full_case = 32'd1 *)
      casez (meter_slot)
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
  assign meter_host_wr_refused = 1'h0;
  assign meter_host_wr = 1'h0;
endmodule

module \governor_core.mono (mono_hwm, mono_load_hwm, mono_refused, clk, rst, mono_value, mono_inc);
  reg \$auto$verilog_backend.cc:2355:dump_module$16  = 0;
  wire \$1 ;
  wire \$2 ;
  wire \$3 ;
  wire \$4 ;
  wire [64:0] \$5 ;
  reg [63:0] \$6 ;
  input clk;
  wire clk;
  wire mono_dec_req;
  input [63:0] mono_hwm;
  wire [63:0] mono_hwm;
  input mono_inc;
  wire mono_inc;
  input mono_load_hwm;
  wire mono_load_hwm;
  input mono_refused;
  wire mono_refused;
  output [63:0] mono_value;
  reg [63:0] mono_value = 64'h0000000000000000;
  input rst;
  wire rst;
  assign \$4  = mono_hwm > mono_value;
  assign \$5  = mono_value + 1'h1;
  always @(posedge clk)
    mono_value <= \$6 ;
  assign \$1  = & mono_value;
  assign \$2  = ~ \$1 ;
  assign \$3  = mono_inc & \$2 ;
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$16 ) begin end
    \$6  = mono_value;
    if (mono_load_hwm) begin
      if (\$4 ) begin
        \$6  = mono_hwm;
      end
    end else if (\$3 ) begin
      \$6  = \$5 [63:0];
    end
    if (rst) begin
      \$6  = 64'h0000000000000000;
    end
  end
  assign mono_dec_req = mono_refused;
endmodule

module \governor_core.tickets (tickets_id_in, clk, rst, tickets_full, match, tickets_burned, tickets_burn);
  reg \$auto$verilog_backend.cc:2355:dump_module$17  = 0;
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
  input clk;
  wire clk;
  reg [3:0] free;
  reg [31:0] id0 = 32'd0;
  reg [31:0] id1 = 32'd0;
  reg [31:0] id2 = 32'd0;
  reg [31:0] id3 = 32'd0;
  reg [31:0] id4 = 32'd0;
  reg [31:0] id5 = 32'd0;
  reg [31:0] id6 = 32'd0;
  reg [31:0] id7 = 32'd0;
  output match;
  reg match;
  input rst;
  wire rst;
  input tickets_burn;
  wire tickets_burn;
  output tickets_burned;
  reg tickets_burned;
  output tickets_full;
  wire tickets_full;
  input [31:0] tickets_id_in;
  wire [31:0] tickets_id_in;
  wire tickets_seen;
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
  assign \$1  = id0 == tickets_id_in;
  assign \$2  = v0 & \$1 ;
  assign \$3  = id1 == tickets_id_in;
  assign \$4  = v1 & \$3 ;
  assign \$5  = id2 == tickets_id_in;
  assign \$6  = v2 & \$5 ;
  assign \$7  = id3 == tickets_id_in;
  assign \$8  = v3 & \$7 ;
  assign \$9  = id4 == tickets_id_in;
  assign \$10  = v4 & \$9 ;
  assign \$11  = id5 == tickets_id_in;
  assign \$12  = v5 & \$11 ;
  assign \$13  = id6 == tickets_id_in;
  assign \$14  = v6 & \$13 ;
  assign \$15  = id7 == tickets_id_in;
  assign \$16  = v7 & \$15 ;
  assign \$17  = ~ v7;
  assign \$18  = ~ v6;
  assign \$19  = ~ v5;
  assign \$20  = ~ v4;
  assign \$21  = ~ v3;
  assign \$22  = ~ v2;
  assign \$23  = ~ v1;
  assign \$24  = ~ v0;
  assign tickets_full = free == 4'h8;
  assign \$25  = ~ match;
  assign \$26  = tickets_burn & \$25 ;
  assign \$27  = free != 4'h8;
  assign \$28  = \$26  & \$27 ;
  assign \$29  = ~ match;
  assign \$30  = tickets_burn & \$29 ;
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
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
    \$41  = id0;
    if (\$32 ) begin
      casez (free)
        4'h0:
            \$41  = tickets_id_in;
      endcase
    end
    if (rst) begin
      \$41  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
    \$42  = id1;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            \$42  = tickets_id_in;
      endcase
    end
    if (rst) begin
      \$42  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
    \$43  = id2;
    if (\$32 ) begin
      casez (free)
        4'h0:
            /* empty */;
        4'h1:
            /* empty */;
        4'h2:
            \$43  = tickets_id_in;
      endcase
    end
    if (rst) begin
      \$43  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
            \$44  = tickets_id_in;
      endcase
    end
    if (rst) begin
      \$44  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
            \$45  = tickets_id_in;
      endcase
    end
    if (rst) begin
      \$45  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
            \$46  = tickets_id_in;
      endcase
    end
    if (rst) begin
      \$46  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
            \$47  = tickets_id_in;
      endcase
    end
    if (rst) begin
      \$47  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
            \$48  = tickets_id_in;
      endcase
    end
    if (rst) begin
      \$48  = 32'd0;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
    match = 1'h0;
    if (\$2 ) begin
      match = 1'h1;
    end
    if (\$4 ) begin
      match = 1'h1;
    end
    if (\$6 ) begin
      match = 1'h1;
    end
    if (\$8 ) begin
      match = 1'h1;
    end
    if (\$10 ) begin
      match = 1'h1;
    end
    if (\$12 ) begin
      match = 1'h1;
    end
    if (\$14 ) begin
      match = 1'h1;
    end
    if (\$16 ) begin
      match = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
    tickets_burned = 1'h0;
    if (\$28 ) begin
      tickets_burned = 1'h1;
    end
  end
  always @* begin
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
    if (\$auto$verilog_backend.cc:2355:dump_module$17 ) begin end
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
  assign tickets_seen = match;
endmodule