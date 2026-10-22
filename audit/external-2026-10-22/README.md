# External audit, 22 October 2026: the reproductions

The scripts that tested each finding of the audit on the snapshot it was made against, before
anything was fixed, and again after. The account is in `docs/REVIEW-2026-10-22-fact-check.md`,
section 9.

| Script | Run from | What it checks |
|---|---|---|
| `repro_sg.py` | a safety-governor checkout: `PYTHONPATH=. python3 audit/external-2026-10-22/repro_sg.py` | Findings 1 (unsigned threshold-0 policy, propose and commit) and 2 (heartbeat as CLEAR on a four-governor rack). Prints REPRODUCED on `dccc1e0`, NOT reproduced after the fix |
| `repro_hs.py` | a hardware-and-silicon checkout: `PYTHONPATH=. python3 <path>/repro_hs.py` | Findings 3 (gate key from public quotes), 4 (old hold approved under a stricter policy), 5 (old epoch replayed) |
| `repro_rollback.py` | the same | 5b: the gate reloading an older signed policy |
| `check_research.py` | `algorithms/YB-0051-low-false-alarm-precision` in autonomic-graph-regulation | The research numbers: C2 at 1%, false alarms per task family, self-consistency plus text at the same false alarms, and a threshold frozen on the reference |
