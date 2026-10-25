// L7-SPLICE block: cap_table. FINDINGS-a.md RTL-ZERO-BYTE-SPENT-LOOKUP. Expected to FAIL by assertion. Rule from docs/07 section 3 (WAVE-FORMAL-PROOFS-ON-VERILOG (old: L7))
// ("budget > 0") and docs/04 section 5 ("refuses at zero"): a lookup is never allowed through an entry whose budget
// is zero. The RTL compares budget >= bytes, so a zero-byte lookup on an exhausted entry is allowed.
  wire [7:0]   f_val  = {valid7, valid6, valid5, valid4, valid3, valid2, valid1, valid0};
  wire [191:0] f_bud  = {budget7, budget6, budget5, budget4, budget3, budget2, budget1, budget0};
  always @(*) if (allow) assert(f_bud[24*hit[2:0] +: 24] != 0);
