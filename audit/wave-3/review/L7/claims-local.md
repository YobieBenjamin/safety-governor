## Claims (from agent summary + commit messages)

The agent summary made **no claims** (recorded as "none: the run ended at the 90-minute limit or without a final message; exit 1"). All claims below are from the commit messages.

1. **SymbiYosys properties exist (written for the RTL)** — `+Status: written, not yet run. `rtl/formal/` holds SymbiYosys properties for `ticket_store`, `epoch_reg`, `halt_seq`, `cap_table`, `monotonic_counter` and `mailbox` …` (EXPERIMENTS.md); six new `rtl/formal/*.svh` files in the diff.
2. **The properties target rtl/gen (injected into `rtl/gen/<block>.v`)** — `+`make formal` runs `run_formal.py`: for each hard-core block it injects `<block>.svh` in front of the final `endmodule` of `rtl/gen/<block>.v`` (README.md); `+GEN = os.path.join(HERE, "..", "gen")` and `+For each block the properties in ``rtl/formal/<block>.svh`` are injected in front of the last ``endmodule`` of the generated file` (run_formal.py).
3. **Six hard-core blocks are covered** — EXPERIMENTS.md line names six (`ticket_store`, `epoch_reg`, `halt_seq`, `cap_table`, `monotonic_counter`, `mailbox`); six new `.svh` files; `+BLOCKS = {…}` has six entries; `+EQUIV = ["ticket_store", "epoch_reg", "halt_seq", "cap_table", "monotonic_counter", "mailbox"]` (run_formal.py).
4. **Expected-failure tasks are included** — `+## Tasks that are expected to fail (findings about the RTL)` (README.md); `+if expected == "fail":` branch in run_formal.py.
5. **For three RTL gaps** — three README table rows `+| `monotonic_counter:wrap` |`, `+| `mailbox:nolatch` |`, `+| `mailbox:midhalt` |`; three `expected == "fail"` tasks in `BLOCKS` (monotonic_counter:wrap, mailbox:nolatch, mailbox:midhalt).
6. **A gate-level equivalence job is included** — `+## Netlist equivalence` and `+This is an in-flow **Yosys** gate netlist, **not** the LibreLane netlist the brief names` (README.md); `+def run_equiv(…)` (run_formal.py). *Caveat recorded in diff: it is a Yosys `abc`-mapped netlist, not the LibreLane netlist, and "the real comparison cannot run here."*
7. **A `make formal` target is added** — `+formal: ; python3 rtl/formal/run_formal.py` and `+formal-%: ; python3 rtl/formal/run_formal.py $*` (Makefile).
8. **This is wave 3** — `+## L7: formal proofs on the Verilog (wave 3, issue #7)` (EXPERIMENTS.md).
9. **This is issue #7** — same line as #8.
10. **Work left uncommitted by the agent, committed by the launcher** — NOT FOUND (process statement about how the diff was produced; no evidence in the diff).

## Numbers (in changed documents)

1. **3** ("wave 3") — EXPERIMENTS.md header `(wave 3, issue #7)` — recorded (label, not computed).
2. **7** ("issue #7") — same line — recorded (label, not computed).
3. **3** ("three expected-failure tasks") — EXPERIMENTS.md Status line — recorded; countable in diff (3 `fail` tasks in `BLOCKS`, 3 README rows).
4. **1** ("The one `make formal` run") — EXPERIMENTS.md — recorded (prose count, not computed).
5. **1** ("Error 1") — EXPERIMENTS.md block `+    make: *** [formal] Error 1` — recorded (make exit code).
6. **64 / 2^64−1** ("wraps at 2^64-1") — EXPERIMENTS.md; equals the 64-bit max, also `+  m_P8_never_decreases: assert (value >= p_value || (p_inc && !p_load && p_value == 64'hFFFFFFFFFFFFFFFF))` (monotonic_counter.svh) — recorded.
7. **64** ("2^64 wrap", "2^64 microseconds") — README property-map + expected-fail table — recorded; matches `64'hFFFFFFFFFFFFFFFF` and the `2^64 microseconds` comment in monotonic_counter.svh.
8. **1** ("that one step") — README wrap row `+ … carries that one step as an escape clause` — recorded (the single wrap step; the escape clause).
9. **2** ("two steps") — README `+ … then incrementing -- two steps` — recorded; the `wrap` task's `bmc` depth is **3** in `BLOCKS`, which bounds a depth-2 counterexample (no contradiction).
10. **P1, P3, P4, P5, P6, P7, P8, P9, P10, P12, P13, CP** — property-number labels — README "## Property map" table — recorded (labels, not computed).
11. **7, 0** (`[7:0]`) — cap_table.svh `+reg [7:0] p_v;` / `+wire [7:0] f_v` — recorded (code).
12. **191, 0** — cap_table.svh `+reg [191:0] p_bud;` / `+wire [191:0] f_bud` — recorded.
13. **255, 0** — cap_table.svh `+wire [255:0] f_exp` — recorded.
14. **127, 0** — cap_table.svh `+wire [127:0] f_tag`, `+wire [127:0] f_peer` — recorded.
15. **23, 0** — cap_table.svh `+wire [23:0] f_pt` — recorded.
16. **15, 0** — cap_table.svh `+wire [15:0] f_dir` — recorded.
17. **3, 16, 2, 32, 24** — cap_table.svh slice widths `f_pt[gi*3 +: 3]`, `f_peer[gi*16 +: 16]`, `f_dir[gi*2 +: 2]`, `f_exp[gi*32 +: 32]`, `f_tag[gi*16 +: 16]`, `f_bud[gi*24 +: 24]` — recorded.
18. **3, 0** (`3'd0`) — cap_table.svh `+c_P1_allow_reason_ok: assert (!allow || reason == 3'd0);` — recorded.
19. **2** (`2'd2`) — cap_table.svh `+&& (f_dir[gi*2 +: 2] == lk_dir || f_dir[gi*2 +: 2] == 2'd2)` — recorded.
20. **0, 8, 1** — cap_table.svh loop `+generate for (gi = 0; gi < 8; gi = gi + 1)` — recorded.
21. **1** (`1'b1`/`1'b0`) — cap_table.svh `+reg f_init = 1'b1;` / `+always @(posedge clk) f_init <= 1'b0;` — recorded.
22. **255, 0** — epoch_reg.svh `+reg [255:0] p_epoch, p_new_epoch;` — recorded.
23. **15, 0** — epoch_reg.svh `+e_tag_is_low_16_bits: assert (epoch_tag == epoch[15:0]);` — recorded.
24. **1** — epoch_reg.svh `+reg f_init = 1'b1;` / `f_init <= 1'b0` — recorded.
25. **0, 1, 2, 3, 4** — halt_seq.svh `+localparam HI = 0, RUN = 1, THR = 2, HLT = 3, SAF = 4;` and `+localparam C_NONE = 0, C_LOOP = 1, C_LOCAL = 2, C_TAMPER = 3, C_COMMAND = 4;` — recorded.
26. **2, 0** — halt_seq.svh `+reg [2:0] p_state, p_cause;` — recorded.
27. **1** — halt_seq.svh `+reg f_init = 1'b1;` / `f_init <= 1'b0` — recorded.
28. **255, 0** — mailbox.svh `+wire [255:0] lseq`, `+reg [255:0] p_lseq;` — recorded.
29. **32** — mailbox.svh `+cur_last = lseq[key_slot*32 +: 32];`, `+lseq[gi*32 +: 32]` — recorded.
30. **31, 0** — mailbox.svh `+reg [31:0] c_seq;`, `+reg [31:0] p_seq;` — recorded.
31. **2, 0** — mailbox.svh `+reg [2:0] c_slot;`, `+reg [2:0] p_slot;` — recorded.
32. **7, 0** — mailbox.svh `+reg [7:0] c_cmd;`, `+reg [7:0] p_cmd, p_signed;` — recorded.
33. **0, 8** — mailbox.svh loop `+generate for (gi = 0; gi < 8; gi = gi + 1)` — recorded.
34. **1, 2, 3, 4, 5, 6, 7** (status codes `3'd1`…`3'd7`) — mailbox.svh `b_CP_order_*` / `b_P12_*` asserts (`status == 3'd4`, `3'd5`, `3'd6`, `3'd1`, `3'd7`, `3'd3`, `3'd2`) — recorded.
35. **3, 0** (`3'd` width in status codes) — mailbox.svh — recorded.
36. **1** — mailbox.svh `+reg f_init = 1'b1;` / `f_init <= 1'b0` — recorded.
37. **63, 0** — monotonic_counter.svh `+reg [63:0] p_value, p_hwm;` — recorded.
38. **64** — monotonic_counter.svh `+p_value == 64'hFFFFFFFFFFFFFFFF`, `+value == p_value + 64'd1` — recorded.
39. **1** (`64'd1`) — monotonic_counter.svh — recorded.
40. **64, 1** ("2^64-1", "2^64 microseconds") — monotonic_counter.svh comment `+// … wrap of an increment at 2^64-1 (2^64 microseconds,` — recorded.
41. **584,000** ("about 584,000 years") — monotonic_counter.svh comment `+// about 584,000 years)` — **recorded in a comment, but NOT computed anywhere in the diff** (an asserted approximation; ~2^64 μs ÷ (365.25 d/yr) ≈ 5.8×10⁵ yr).
42. **2** ("depth of two") — monotonic_counter.svh comment `+// the strict property is broken on that second step, at a depth of two.` — recorded.
43. **1** — monotonic_counter.svh `+reg f_init = 1'b1;` / `f_init <= 1'b0` — recorded.
44. **6, 4, 8, 5, 4, 3, 8, 6, 6** — run_formal.py `BLOCKS` task depths (ticket_store 6, epoch_reg 4, halt_seq 8, cap_table 5, monotonic_counter prove 4 / wrap 3, mailbox prove 8 / nolatch 6 / midhalt 6) — recorded (chosen bounds, not computed).
45. **6** (count of blocks) — run_formal.py `BLOCKS` (6 entries) and `EQUIV` (6 entries) — recorded; countable.
46. **3000** — run_formal.py `+timeout=3000` — recorded.
47. **12** — run_formal.py `+\n".join((p.stdout + p.stderr).strip().splitlines()[-12:])` — recorded.
48. **5** — run_formal.py `+equiv_simple -seq 5`, `+equiv_induct -seq 5` — recorded.
49. **0, 1, 2** — run_formal.py return codes `+return 0 if not fails else 1`, `+return 2` — recorded.
50. **7, 0** — ticket_store.svh `+wire [7:0] f_v`, `+reg [7:0] p_v;` — recorded.
51. **255, 0** — ticket_store.svh `+wire [255:0] f_id`, `+reg [255:0] p_id;` — recorded.
52. **31, 0** — ticket_store.svh `+(* anyconst *) wire [31:0] w_id;` — recorded.
53. **0, 8, 1** — ticket_store.svh loop `+generate for (gi = 0; gi < 8; …)`, `+for (gj = gi + 1; gj < 8; …)` — recorded.
54. **32** — ticket_store.svh `+f_id[gi*32 +: 32]` — recorded.
55. **1** — ticket_store.svh `+reg w_burned = 1'b0;` / `+reg f_init = 1'b1;` — recorded.

Makefile (changed lines): **no numeric tokens.**

No number that appears in a changed document is wholly absent from the diff; the only asserted-but-not-derived value is **584,000** (#41), which is recorded as a comment but not computed in the diff.
