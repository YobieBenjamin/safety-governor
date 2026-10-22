CLAIMS (summary + commit messages)

1. "All 9 tests pass; the 2 warnings are the intentional 'report, don't fail' ones."
   - `+def test_every_row_has_a_known_status_and_a_source():` … `+def test_no_em_dashes():` — nine `def test_` functions in the test file (the "9").
   - `+        warnings.warn(f"{len(nda)} rows wait on the HGX design guide or a board document: {nda}")` and `+        warnings.warn(f"the model bricks these exits by policy but the register cannot show it: {unshown}")` — exactly two `warnings.warn` sites, both in report-not-fail paths (the "2 warnings … report, don't fail").
   - [no test-run output in the diff, so "pass" is not shown; only the 9 functions and 2 warning sites are visible]

2. "Fixed the blocking and unsupported-claim findings; left the false-positive warnings, with reasons."
   - `+| X30 | … | unaccounted (NDA) | A transport, not a lever: …` and `+| X05 | … | governed | The path crosses the PCIe switch port (X03, S15 S16) and the DPU OOB port (S20); …` — the register changes that fix the blocking/unsupported findings.
   - `+    if nda:` / `+        warnings.warn(…)` — the warnings left in place.
   - ["with reasons" is stated in the summary, not in the diff]

3. "Three commits on `exp/p2`, working tree clean, acceptance passes (`9 passed, 2 warnings`)."
   - NOT FOUND (commit count, branch name, and "working tree clean" are git metadata not in the diff; no test output, so "9 passed / 2 warnings" not shown — only the 9 functions and 2 warning sites exist in the test file).

4. "`X30` (LTPI) `governed` → `unaccounted (NDA)`: a transport is not a lever, so it cannot count as governed."
   - `+| X30 | LTPI GPIO, I2C, UART and OEM tunnel between the DC-SCM and the host-board CPLD | both | both | The channel the module would use to reach any lever above: 16 low-latency and 16 normal-latency GPIO each way by default, I2C, 2 UARTs; OEM tunnel method out of scope of the spec | unaccounted (NDA) | A transport, not a lever: it limits the module to the signals the CPLD firmware maps onto it, so whether it reaches a lever is the CPLD firmware's mapping (NDA) | pcie | witness | NDA | The CPLD image on the host board, which the board vendor controls | VERIFIED (spec) | BLR F1, F3; S6 S7 |`
   - [new-file diff: shows the new `unaccounted (NDA)` state only; the prior `governed` is not in this diff]

5. "`X05`/`X06`/`X07`: evidence `DESIGN` → `PARTIAL`, now citing the external path lever (PCIe switch port `S15`/`S16`, DPU OOB port `S20`); DOCA Flow and the model key are kept as the design refinement."
   - `+| X05 | … | governed | The path crosses the PCIe switch port (X03, S15 S16) and the DPU OOB port (S20); either can be closed, and that is the external lever. DOCA Flow steering over the DPU OOB port (docs/03 s3) is the in-band refinement (design); for a NIC without a DPU governor the lever is the switch port | dpu | witness | NDA | … | PARTIAL | BLR E1, E2, F1; S15 S16 S20; docs/03 s3, s6 |`
   - `+| X06 | … | governed | Same as X05 on the tray: the DPU OOB port (S20) and the PCIe switch port (X03) are the external levers; DOCA Flow steering is the in-band refinement (design) | dpu | witness | NDA | Same as X05; the tray BMC | PARTIAL | BLR E1, E2; S15 S16 S20; docs/03 s3, s6 |`
   - `+| X07 | … | governed | Port or flow control on the path (the X03 switch port, S15 S16; the X05 DPU OOB port, S20) is the external path lever; the model key held by the governor (weights useless without it, docs/03 s5) is an added design layer | storage | witness | NDA | … | PARTIAL | BLR E1, E2; S15 S16 S20; docs/03 s5; tests/test_h02 |`
   - [new-file diff: shows `PARTIAL` only; the prior `DESIGN` is not in this diff]

6. "Answers 'governed requires evidence above DESIGN' without dropping the DPU/storage rows the model treats as governed."
   - `+| X05 | … | governed | … | PARTIAL | …`, `+| X06 | … | governed | … | PARTIAL | …`, `+| X07 | … | governed | … | PARTIAL | …` — DPU (X05/X06) and storage (X07) stay `governed` with `PARTIAL` (non-DESIGN) evidence.
   - ["'governed requires evidence above DESIGN' is a brief requirement, not a line in the diff"]

7. "`X19`, `X27`: `from_module` `NDA` → `no`, which BLR F2 settles (DC-SCI carries no per-endpoint PERST and no REFCLK to the module)."
   - `+| X19 | … | governed | Hold the group's reset. Not per GPU at the connector; PEX_STRAP default 11 gives one reset for all devices | pcie | witness | no | Host CPLD or FPGA; the BMC through it. The DC-SCI carries one PERST per node and it flows from the host board to the module, so the module cannot drive it: per-GPU reset from the slot is `no` by specification (BLR F2) | VERIFIED | BLR B2, F2; S1 S6 |`
   - `+| X27 | … | unaccounted (NDA) | Gating the clock stops the link, but the clock buffer and who controls its output-enable are not public; the DC-SCI carries no REFCLK to the module, so from_module is `no` (BLR F2) | pcie | witness | no | Host board clock buffer, CPLD | UNKNOWN | BLR B2, F2; S1 S6 |`
   - [new-file diff: shows `no` only; the prior `NDA` is not in this diff]

8. "Counts now `governed 14, NDA 12`."
   - `+Counts at this commit: `governed` 14, `recorded-gap` 2, `bricked` 2, `unaccounted (NDA)` 12, `unaccounted` 0. The test counts them from the table.`

9. "note 5 no longer asserts 'one DC-SCI connector per slot' as fact (now a stated assumption)."
   - `+5. **The "second module" wording.** docs/03 s1 and hw/pcb/rack-integration.md say the governor rides as a second module or a mezzanine on the existing one. Whether a real host board carries one DC-SCI connector per slot (so that a second module needs a second slot and the mezzanine form fits one slot) is not settled by the public record: BLR F4 shows the MGX subset publishes only a pinout subset, so the connector-per-slot count is an assumption to check against a host-board pinout, not a finding of this run.`
   - [new-file diff: shows the current "assumption" wording; the prior "as fact" wording is not in this diff]

10. "source key made contiguous (`S21/S22/S24`→`S20/S21/S22`) and the A100 brief `PB-10577` gets its URL."
    - `+- S20 BlueField-3 pinouts: https://networking-docs.nvidia.com/bf3dpu/pinouts-description` / `+- S21 NVIDIA switch BMC user manual: https://docs.nvidia.com/networking/display/nvidiaswitchbmcusermanualv8800021955/supported+redfish+scheme+uris` / `+- S22 NVSwitch technical overview: https://images.nvidia.com/content/pdf/nvswitch-technical-overview.pdf` — `S20/S21/S22` present and contiguous at the end.
    - `+- S17 NVIDIA product briefs: PB-10577 (A100): https://oraprdnt.uqtr.uquebec.ca/portail/docs/GSC7528/O0005582917_PB_10577_001_v02.pdf ; PB-11133 (H100 PCIe): … ; PB-11470 (L40S): …` — `PB-10577` carries a URL.
    - [new-file diff: shows `S20/S21/S22` and the URL, but not the prior `S21/S22/S24` nor that the URL was added this revision]

11. Test: "Em dash in source (the block) built with `chr(0x2014)`."
    - `+def test_no_em_dashes():` / `+    em_dash = chr(0x2014)` / `+    assert em_dash not in REGISTER.read_text()`

12. Test: "Model-agreement test widened: each `True` model exit must have a governed row backed by external evidence (not design intent); unshown bricks on `jtag`/`debug` are reported, not passed silently."
    - `+        if governed is True:` / `+            gov = [r for r in rows_for if r["status"] == "governed"]` / `+            assert gov, f"{name} is governed in the model but the register has no governed row"` / `+            supported = [r for r in gov if "VERIFIED" in r["evidence"].upper() or "PARTIAL" in r["evidence"].upper()]` / `+            assert supported, f"{name} is only governed by design intent: {[r['id'] for r in gov]}"`
    - `+            if any(s == "unaccounted (NDA)" for s in statuses):` / `+                unshown.append(name)` / `+    if unshown:` / `+        warnings.warn(f"the model bricks these exits by policy but the register cannot show it: {unshown}")`

13. Test: "Retrofit test now enforces the witness/lock relationship (a witness must name an undo path; a lock must not)."
    - `+        if r["class"] == "lock":` / `+            assert r["from_module"] == "yes", f"{r['id']}: a lock needs a module that can drive it"` / `+            assert not has_undo, f"{r['id']}: a lock must have no undo path the governor does not own"` / `+        else:` / `+            assert has_undo, f"{r['id']}: a witness must name what undoes the lever"`

14. "`EXPERIMENTS.md`: reverted the out-of-scope `partial` status change to its pre-branch state (brief names only register + test; acceptance passed)."
    - NOT FOUND (the diff contains only `docs/research/exit-register.md` and `tests/test_h20_exits.py`; no `EXPERIMENTS.md` change is present).

15. "the ~32 verifier number-warnings (part numbers, spec versions, voltages, and the recomputed counts) are legitimate register content, not fabricated results."
    - Numbers are present as register content, e.g. `+| X03 | … (PEX89000 I2C hot-plug; Switchtec TWI/UART …) …` (part numbers), `+- S6 OCP DC-SCM 2.2: …` (spec version), `+| X17 | … 54 V bulk input …` (voltage), `+Counts at this commit: `governed` 14, …` (counts).
    - [the literal "32" does not appear anywhere in the diff; the "not fabricated results" judgment is the summary's, not a line in the diff]

16. "the counts are recomputed by `test_stated_counts_match_the_table`, so not mistaken."
    - `+def test_stated_counts_match_the_table():` / `+    c = Counter(r["status"] for r in rows())` / `+    m = re.search(r"Counts at this commit: `governed` (\d+), `recorded-gap` (\d+), `bricked` (\d+), "` / `+                  r"`unaccounted \(NDA\)` (\d+), `unaccounted` (\d+)", text)` / `+    got = tuple(int(x) for x in m.groups())` / `+    want = (c["governed"], c["recorded-gap"], c["bricked"], c["unaccounted (NDA)"], c["unaccounted"])` / `+    assert got == want, (got, want)`

17. "The disproof half of the brief stays open (no web in this run, stated in note 4)."
    - `+4. **Disproof status.** The disproof "no lever reachable from the module slot on any public DC-SCM 2.x board" is neither confirmed nor refuted: this run surveyed no public host boards beyond the NVIDIA MGX subset (BLR C5, F4), which publishes only a pinout subset. Open item for a run with web access: survey public DC-SCM 2.x host boards for any DC-SCI GPIO, I2C or SGPIO net that reaches a power-brake, reset or enable input.`

18. "The 12 NDA rows stay NDA by the brief's 'report, don't fail' rule."
    - `+def test_nda_rows_are_reported_not_failed():` / `+    nda = [r["id"] for r in rows() if r["status"] == "unaccounted (NDA)"]` / `+    if nda:` / `+        warnings.warn(f"{len(nda)} rows wait on the HGX design guide or a board document: {nda}")` — NDA rows warn, not assert-fail.
    - `+Counts at this commit: `governed` 14, `recorded-gap` 2, `bricked` 2, `unaccounted (NDA)` 12, `unaccounted` 0.` — the 12 NDA rows.

19. (commit 1) "revert the out-of-scope EXPERIMENTS.md status change … the P2 row goes back to its pre-branch state (open; the HGX design guide is an ask)."
    - NOT FOUND (no `EXPERIMENTS.md` in the diff).

20. (commit 2) "test - widen the two weak checks and drop the em dash from source … model-agreement test now requires each True model exit to have a governed row backed by external evidence (VERIFIED or PARTIAL, not design intent), and it reports (not fails) the None exits … retrofit test now enforces the witness/lock relationship … em dash in test_no_em_dashes is built with chr(0x2014)."
    - `+            supported = [r for r in gov if "VERIFIED" in r["evidence"].upper() or "PARTIAL" in r["evidence"].upper()]` / `+            assert supported, f"{name} is only governed by design intent: …"` ; `+    if unshown:` / `+        warnings.warn(…)` ; `+            assert not has_undo, …` / `+            assert has_undo, …` ; `+    em_dash = chr(0x2014)` — same evidence as claims 11, 12, 13.

21. (commit 3) "register - governed rows now cite an external lever, not design intent … X05/X06/X07 … PARTIAL … X30 … unaccounted (NDA) … X19 and X27 take from_module no … Counts now 14 governed, 12 NDA. The source key is contiguous (S21/S22/S24 -> S20/S21/S22) and the A100 brief PB-10577 gets its URL. Note 5 no longer asserts one DC-SCI connector per slot as fact."
    - Same evidence as claims 4, 5, 7, 8, 9, 10 (the X30, X05–X07, X19, X27, counts, S20–S22, S17, and note-5 lines).
    - [new-file diff: the "moved from DESIGN", "governed →", "S21/S22/S24 →", "gets its URL" transitions are not shown, only the resulting state]

22. (commit 4) "exit register for HGX and NVL72 with retrofit columns, and the test that fails on any unaccounted row."
    - `+# Exit register: every path that reaches or leaves a GPU (October 2026)` and the `| tray |` column carrying `HGX`/`NVL72`; retrofit columns in `+COLUMNS = ["id", "path", "tray", "direction", "carries", "status", "lever_or_how", "model_exit", "class", "from_module", "undo_paths", "evidence", "source"]`.
    - `+def test_no_row_is_unaccounted():` / `+    bad = [r["id"] for r in rows() if r["status"] == "unaccounted"]` / `+    assert not bad, f"unaccounted rows: {bad}"` — the test that fails on any unaccounted row.

NUMBERS (numbers in the two changed documents)

1. 14, 2, 2, 12, 0 (the five status counts) — computed by `+    c = Counter(r["status"] for r in rows())` … `+    assert got == want, (got, want)` and recorded in `+Counts at this commit: `governed` 14, `recorded-gap` 2, `bricked` 2, `unaccounted (NDA)` 12, `unaccounted` 0.` (computed + recorded; cross-checked by hand: governed X01,02,03,05,06,07,13,14,15,16,18,19,20,22 = 14; recorded-gap X08,09 = 2; bricked X10,29 = 2; NDA X04,11,12,17,21,23,24,25,26,27,28,30 = 12; unaccounted = 0; 30 rows total).

2. 54 V — recorded (asserted, not computed) in `+| X17 | … | The contribution spec shows only the 54 V bulk input; per-module stages are not described. …` and `+| X18 | HGX 54 V bulk power | … | Power to all eight GPUs and the NVSwitches …`.

3. 3.3 V — recorded in `+| X26 | HGX 3.3 V GPIO: presence, brake, thermal trip, power-good | …`.

4. "at least 2x" — recorded in `+| X15 | Tray power brake: … | into GPUs | Hardware clock slowdown (at least 2x) of the tray's GPUs …`.

5. 16 / 16+16 (GPIO each way) — recorded in `+| X30 | … | 16 low-latency and 16 normal-latency GPIO each way by default, I2C, 2 UARTs; OEM tunnel method out of scope of the spec …` and `+3. **What the slot does give.** The DC-SCI has the transport: 18 I2C ports, two UARTs, two NC-SI, JTAG, SGPIO, and LTPI with 16+16 GPIO each way (BLR F1, F3). …`.

6. 18 (I2C ports) — recorded in `+3. **What the slot does give.** The DC-SCI has the transport: 18 I2C ports, two UARTs, two NC-SI, JTAG, SGPIO, …` (asserted, citing `BLR F1, F3`; not computed in the diff).

7. 2 / two UARTs — recorded in `+| X12 | … | The DC-SCI carries 2 UARTs and JTAG; no public document says which are populated or fused …` and `+3. … 18 I2C ports, two UARTs, …`.

8. two NC-SI / NC-SI — recorded in `+3. … two UARTs, two NC-SI, JTAG, SGPIO, …` and `+| X13 | … | BMC over NC-SI or the DPU OOB port; …` (X05 `BMC over NC-SI or the DPU OOB port`).

9. 2x I2C — recorded in `+| X21 | HGX SMBPBI and NSM out-of-band management bus to GPUs and NVSwitches, 2x I2C and the HMC | …`.

10. x16 Gen5, 8 (per baseboard) — recorded in `+| X03 | GPU to host and to PCIe peers on x16 Gen5, 8 per baseboard | HGX | …`.

11. x2 Gen4 — recorded in `+| X20 | HGX x2 Gen4 PCIe to the PM41028 for NVSwitch management | …`.

12. x1 Gen2, 2.0 (USB) — recorded in `+| X25 | HGX PCIe x1 Gen2 to the baseboard FPGA, USB 2.0 to the HMC | …`.

13. PEX_RST0..2_N, GPUs 0-3, GPUs 4-7, PEX_STRAP 11 — recorded in `+| X19 | HGX PCIe reset, `PEX_RST0..2_N` grouped (GPUs 0-3, GPUs 4-7, NVSwitch and PM41028) | … | Hold the group's reset. Not per GPU at the connector; PEX_STRAP default 11 gives one reset for all devices …`.

14. PEX89000 — recorded in `+| X03 | … (PEX89000 I2C hot-plug; Switchtec TWI/UART and per-port hot-plug) …` and `+- S15 Broadcom PEX89000 brief: https://www.mouser.com/datasheet/2/678/PEX89000_PB102-3394994.pdf`.

15. PM41028 — recorded in `+| X19 | … (GPUs 0-3, GPUs 4-7, NVSwitch and PM41028) …` and `+| X20 | … | Hold `PEX_RST2` (NVSwitch plus PM41028) …`.

16. AST2600 — recorded in `+| X13 | … | The BMC owns all of these lines today (AST2600 SGPIO); …`.

17. LM5066I (×2) — recorded in `+| X13 | … | … the two LM5066I hot-swap controllers; Redfish ComputerSystem.Reset and AuxPowerReset …`.

18. PCA9555 — recorded in `+| X14 | … | BMC GPIO and PCA9555 expanders; Redfish Reset; HMC reset action …`.

19. BlueField-3, ConnectX — recorded in `+| X06 | GPU to the BlueField-3 and ConnectX on the compute tray | NVL72 | …` and `+- S20 BlueField-3 pinouts: https://networking-docs.nvidia.com/bf3dpu/pinouts-description`.

20. H100, H200, GB200, NVL72, eight / eight-GPU — recorded in `+Claim P (docs/20, experiment P2) holds by enumeration or not at all. This is the enumeration for an HGX H100/H200 eight-GPU baseboard and a GB200 NVL72 compute tray …` and `+| X18 | … | Power to all eight GPUs and the NVSwitches …`.

21. PB-10577, PB-11133, PB-11470 — recorded in `+- S17 NVIDIA product briefs: PB-10577 (A100): …PB_10577_001_v02.pdf ; PB-11133 (H100 PCIe): …PB-11133-001_v01.pdf ; PB-11470 (L40S): …`.

22. DG-10333-001 — recorded in `+- `unaccounted (NDA)` (public documents cannot settle it; the HGX design guide DG-10333-001, …` and `+1. NVIDIA HGX Platform Design Guide DG-10333-001 and the baseboard pin map: …`.

23. DG-06034-002 — recorded in `+| X22 | … | SMBPBI async request set power limit (command set under NDA, DG-06034-002). …` and `+2. SMBPBI Design Guide DG-06034-002 and the NSM specification: …`.

24. DC-SCM 2.2 / 2.x — recorded in `+Claim P (docs/20, experiment P2) holds by enumeration or not at all. This is the enumeration for an HGX H100/H200 eight-GPU baseboard and a GB200 NVL72 compute tray, with the retrofit question (a governor module in the DC-SCM 2.x slot) …`, `+- S6 OCP DC-SCM 2.2: https://www.opencompute.org/documents/ocp-dc-scm-rev2-2-ver1-0-pdf`, `+| X30 | LTPI GPIO, I2C, UART and OEM tunnel between the DC-SCM and the host-board CPLD …`.

25. LTPI 1.2 — recorded in `+- S7 OCP DC-SCM 2.2 LTPI 1.2: https://www.opencompute.org/documents/ocp-dc-scm-2-2-ltpi-ver1-0-pdf`.

26. r1 v0.1 — recorded in `+- S1 OCP HGX Baseboard Contribution r1 v0.1: https://www.opencompute.org/documents/open-compute-specification-hgx-baseboard-contribution-r1-v0-1-pdf`.

27. DU-12143-001, v1-2 — recorded in `+- S13 GB200 NVL partition guide DU-12143-001: https://docs.nvidia.com/multi-node-nvlink-systems/partition-guide-v1-2.pdf`.

28. v25022444 (NVOS) — recorded in `+- S12 NVOS user manual for NVLink switches: https://docs.nvidia.com/networking/display/nvidianvosusermanualfornvlinkswitchesv25022444/nvlink+interface+commands`.

29. R550 — recorded in `+- S14 NVML HW power brake slowdown: https://docs.nvidia.com/deploy/archive/R550/nvml-api/group__nvmlClocksEventReasons.html`.

30. 2026 (October 2026) — recorded in `+# Exit register: every path that reaches or leaves a GPU (October 2026)`.

31. 0x2014 — computed/recorded in `+    em_dash = chr(0x2014)`.

32. 20 (two thresholds) — recorded literals in `+    assert len(rs) >= 20` and `+            assert len(r["lever_or_how"]) > 20, r["id"]`.

33. five `(\d+)` capture groups — part of the count computation in `+    m = re.search(r"Counts at this commit: `governed` (\d+), `recorded-gap` (\d+), `bricked` (\d+), "` / `+                  r"`unaccounted \(NDA\)` (\d+), `unaccounted` (\d+)", text)`.

34. Other numeric tokens (recorded as literals in URLs/refs; not computed): `1013474` in `+- S4 Linux DTS for the GB200NVL BMC, NVIDIA, v4: https://lists.infradead.org/pipermail/linux-arm-kernel/2025-March/1013474.html`; `1e17db5ba79cc6134d4742f0d7bb1d263c88ee19`, `v4` in `+- S5 OpenBMC platform-init for nvidia-gb200: https://gerrit.openbmc.org/plugins/gitiles/openbmc/platform-init/+/1e17db5ba79cc6134d4742f0d7bb1d263c88ee19/platform.cpp`; `101024` in `+- S8 OCP MGX Accelerated Computing Rack and Trays: https://www.opencompute.org/documents/mgx-accelerated-computing-rack-and-trays-specification-101024-pdf`; `678`, `PB102-3394994` in `+- S15 Broadcom PEX89000 brief: https://www.mouser.com/datasheet/2/678/PEX89000_PB102-3394994.pdf`; `DS00006173` in `+- S16 Microchip Switchtec Gen6 sell sheet … https://www.microchip.com/content/dam/mchp/documents/DCS/ProductDocuments/Brochures/Switchtec-PFX-PSX-Gen-6-Sell-Sheet-DS00006173.pdf , …`; `GSC7528`, `O0005582917`, `10577_001_v02`, `11133-001_v01` in the S17 line (item 21); `2023/12` in the S17 H100 URL; `v8800021955` in `+- S21 NVIDIA switch BMC user manual: https://docs.nvidia.com/networking/display/nvidiaswitchbmcusermanualv8800021955/supported+redfish+scheme+uris`.

35. Row IDs X01–X30 and reference tokens S1–S22, BLR/NSW/doc section numbers (e.g. `BLR F2`, `NSW 2, 3, 5`, `docs/03 s3`) — recorded throughout the register (e.g. `+| X30 | … | BLR F1, F3; S6 S7 |`, `+| X01 | … | NSW 2, 3, 5; S9 S10 S11 S22 |`); these are identifiers/section refs, not computed values.
