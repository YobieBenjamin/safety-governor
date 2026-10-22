# P2 · The exit register: every path by which bytes, requests, responses, weights, power, reset or clock reach or leave a GPU on an HGX baseboard and an NVL72 tray, each governed, bricked or unaccounted, with a source

**Goal.** Claim P is established by enumeration or not at all. Write `docs/research/exit-register.md` as a table: path, tray (HGX H100/H200 eight-GPU; GB200 NVL72 compute tray), direction, what it carries, lever that governs it (BMC power, reset, clock; SMBPBI; NSM port disable; DOCA flow rules; the halt loop) or bricked (how), or unaccounted, evidence level, source. Include debug (JTAG), firmware update paths, out-of-band buses, NVLink, PCIe, the DPU, storage, power and reset nets. Add `tests/test_h20_exits.py` that parses the table and fails on any `unaccounted` row.

**The retrofit question, same register.** Nobody rips out installed racks to add a chip, so the plan of record is a governor module in the system board's management-module slot (DC-SCM 2.x, `docs/03-interfaces.md`, `hw/pcb/rack-integration.md`). For every lever row add two columns: `from_module` (can a module on the DC-SCI connector drive this lever, directly or through LTPI to the host-board CPLD, on at least one publicly documented DC-SCM 2.x host board; yes / no / NDA, with the source) and `undo_paths` (what else on the board can drive the same lever or reverse it: the BMC, the CPLD, a hot-swap controller, the HMC). A lever the module cannot reach, or that something the governor does not sit in front of can reverse, is a witness, not a lock; say so in the row.

**Read first.** `docs/research/board-lever-register.md`, `docs/research/nvswitch-management.md`, `docs/03-interfaces.md`, `hw/pcb/rack-integration.md`, `tests/test_h02_enforcement_points.py` (the model's enumeration).

**Acceptance.** The register exists with every public source cited; the test passes with the rows that public documents can settle and lists the rows that need the HGX design guide under NDA as `unaccounted (NDA)`, which the test reports but does not fail on until the guide is in hand. The retrofit columns are filled for every lever row, with `NDA` where only the design guide can settle it.

**Disproof.** A path that cannot be governed or bricked at the rack tier and that NVIDIA will not close: a disproof of the rack tier as designed. Separately: no lever reachable from the module slot on any public DC-SCM 2.x board, which does not kill the chip but kills the module-swap retrofit and makes it an interposer or a board revision.

**Budget.** One cloud agent with web research, about 120k tokens.

**Acceptance command (the launcher runs it after the agent).** `python3 -m pytest -q tests/test_h20_exits.py`

## Rules for this run
- You are in a git worktree on branch `exp/p2`; it is the only place you write. Run commands from this directory with relative paths; do not cd elsewhere.
- The other repositories of the program are readable at: /Users/yb/safety /Users/yb/hardware-and-silicon. Never edit them: a change they need goes into `patches/<repo>/<file>.patch` here, with a note in your final summary.
- Acceptance: `python3 -m pytest -q tests/test_h20_exits.py`. Run it at most three times. Stop when it passes, or after the third failure; then record exactly what fails in EXPERIMENTS.md (safety-governor) or in the hypothesis's section (safety), with the failing output.
- Read only the files the brief names under Read first and the files you create. Do not read whole directories, do not run the full test suite (the acceptance command is enough), do not search the web, do not start sub-agents.
- Never weaken, skip or delete an existing test. Do not refactor beyond the brief. No em dashes in anything you write.
- Commit as you go with messages that name the issue (#8) and end with the line: Agent: wave 2, issue #8. Do not push, do not open a pull request; the launcher does both.
- This run is capped at 40 turns and an estimated spend of $10. Keep the tree in a working, committed state at all times, so a cap mid-way still leaves usable work.
- Finish with a summary of at most fifteen lines: what was built, what passes, what does not and why, open questions. It is posted on the issue as is.
