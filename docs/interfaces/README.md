# docs/interfaces · the governor against the public NVIDIA server environment

Start with `COMPLIANCE-MATRIX.md` if you build servers or work with NVIDIA. Start with `PLAIN-ENGLISH.md` if you do not.

| File | What |
|---|---|
| `COMPLIANCE-MATRIX.md` | every requirement, its public source, status (tested / designed / open / members-only / NDA), and the evidence file. Generated from `compliance_matrix.csv` |
| `PLAIN-ENGLISH.md` | the same, for a non-engineer, with everything that did not work |
| `01-dcscm-dcsci-ltpi.md` | OCP DC-SCM 2.x slot, DC-SCI pins, LTPI; REQ-LTPI-FS-1 |
| `02-pcie-cem-sideband.md` | PERST#, PWRBRK#, WAKE#, SMBus, 3.3Vaux timing against the RTL; REQ-CEM-FAIL-1 |
| `03-spdm.md` | the governor as an SPDM responder, interop with DMTF's tools |
| `04-nvtrust.md` | NVIDIA GPU evidence into VERIFY_GPU |
| `sources.csv` | every document used or tried, with URL, access level and how it was read |
| `results/` | generated interop results and DMTF validator logs, including the failing first run |

One command checks all of it:

```
python -m govsim.hardware_ref            # about 2 minutes; SPDM interop runs if spdm-emu is built
python -m govsim.hardware_ref --build    # also clones and builds DMTF spdm-emu (a few minutes, ~150 MB)
```

The tests are `tests/test_if_*.py` and run with the rest of the suite.
