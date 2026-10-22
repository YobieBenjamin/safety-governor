**Revision 1** (2026-10-22 10:19) on the local model qwen3.8-27b-64k:latest: 45 turns, estimated $1.9129, acceptance `python3 -m pytest -q tests/test_h20_exits.py`: **pass**. The gate reviews the branch again.

Agent summary:

All 9 tests pass; the 2 warnings are the intentional "report, don't fail" ones. Done.

## Summary — revision 1 of #8 (P2)

Fixed the blocking and unsupported-claim findings; left the false-positive warnings, with reasons. Three commits on `exp/p2`, working tree clean, acceptance passes (`9 passed, 2 warnings`).

**Register (`docs/research/exit-register.md`):**
- `X30` (LTPI) `governed` → `unaccounted (NDA)`: a transport is not a lever, so it cannot count as governed (correctness + the "governed over-applied" finding).
- `X05`/`X06`/`X07`: evidence `DESIGN` → `PARTIAL`, now citing the external path lever (PCIe switch port `S15`/`S16`, DPU OOB port `S20`); DOCA Flow and the model key are kept as the design refinement. Answers "governed requires evidence above DESIGN" without dropping the DPU/storage rows the model treats as governed.
- `X19`, `X27`: `from_module` `NDA` → `no`, which BLR F2 settles (DC-SCI carries no per-endpoint PERST and no REFCLK to the module).
- Counts now `governed 14, NDA 12`; note 5 no longer asserts "one DC-SCI connector per slot" as fact (now a stated assumption); source key made contiguous (`S21/S22/S24`→`S20/S21/S22`) and the A100 brief `PB-10577` gets its URL.

**Test (`tests/test_h20_exits.py`):**
- Em dash in source (the block) built with `chr(0x2014)`.
- Model-agreement test widened: each `True` model exit must have a governed row backed by external evidence (not design intent); unshown bricks on `jtag`/`debug` are reported, not passed silently.
- Retrofit test now enforces the witness/lock relationship (a witness must name an undo path; a lock must not).

**`EXPERIMENTS.md`:** reverted the out-of-scope `partial` status change to its pre-branch state (brief names only register + test; acceptance passed).

**Left unchanged, with reason:** the ~32 verifier number-warnings (part numbers, spec versions, voltages, and the recomputed counts) are legitimate register content, not fabricated results; the counts are recomputed by `test_stated_counts_match_the_table`, so not mistaken. The disproof half of the brief stays open (no web in this run, stated in note 4). The 12 NDA rows stay NDA by the brief's "report, don't fail" rule.

## Commit messages
- P2 (#8) revision 1: revert the out-of-scope EXPERIMENTS.md status change
The brief names only the register and the test, and the acceptance passed, so the P2 row
goes back to its pre-branch state (open; the HGX design guide is an ask).

Co-Authored-By: Claude Code <noreply@anthropic.com>
Agent: wave 2, issue #8 (revision 1)

- P2 (#8) revision 1: test - widen the two weak checks and drop the em dash from source
The model-agreement test now requires each True model exit to have a governed row backed
by external evidence (VERIFIED or PARTIAL, not design intent), and it reports (not fails)
the None exits the register cannot show as bricked. The retrofit test now enforces the
witness/lock relationship: a witness must name an undo path, a lock must not. The em dash
in test_no_em_dashes is built with chr(0x2014) so the test source carries no em dash.

Co-Authored-By: Claude Code <noreply@anthropic.com>
Agent: wave 2, issue #8 (revision 1)

- P2 (#8) revision 1: register - governed rows now cite an external lever, not design intent
X05/X06/X07 moved from DESIGN to PARTIAL on the external path lever (the PCIe switch
port S15/S16 and the DPU OOB port S20), with DOCA Flow and the model key kept as the
design refinement. X30 (the LTPI transport) is unaccounted (NDA), not governed, since a
transport is not a lever. X19 and X27 take from_module no: the DC-SCI carries no
per-endpoint PERST and no REFCLK to the module (BLR F2). Counts now 14 governed, 12 NDA.
The source key is contiguous (S21/S22/S24 -> S20/S21/S22) and the A100 brief PB-10577 gets
its URL. Note 5 no longer asserts one DC-SCI connector per slot as fact.

Co-Authored-By: Claude Code <noreply@anthropic.com>
Agent: wave 2, issue #8 (revision 1)

- P2 (#8): exit register for HGX and NVL72 with retrofit columns, and the test that fails on any unaccounted row
Agent: wave 2, issue #8

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

