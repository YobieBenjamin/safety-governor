# Sweep report

Generated 2026-10-13 16:38 UTC by `govsim sweep`.

`pass`: the hypothesis held. `gap`: it failed exactly as the design predicts for that tier (the recorded residual). `FAIL`: it failed in a way the design does not predict.

| Id | Hypothesis | rack (plan of record) | board (fallback) | integrated (future ask) |
|---|---|---|---|---|
| H0 | every protected operation needs a fresh, exact, single-use authorization | pass | pass | pass |
| H1 | attestation binds permissions to firmware, model and policy | pass | pass | pass |
| H2a | link-level: no bytes to a non-roster peer; unchecked paths bricked | pass | gap | pass |
| H2b | descriptor-level: a transfer between two roster members a rule would not allow | gap | gap | pass |
| H3 | policy changes only with a quorum, never backwards | pass | pass | pass |
| H4 | the broker cannot choose its rule or lane | pass | pass | pass |
| H5 | alarms are monotone | pass | pass | pass |
| H6 | the comparator holds with every layer above it compromised | pass | pass | pass |
| H7 | the assumptions register is complete or the policy does not load | pass | pass | pass |
| H8 | human override is slow and fully logged | pass | pass | pass |
| H9 | zero per-token work; modelled overhead under one percent | pass | pass | pass |
| H10 | permitted-channel leakage trips the budget | pass | pass | pass |
| H11 | a halt reaches every GPU within the bound; nobody clears alone | pass | pass | pass |
| H12 | only roster members speak on the fabric; forged heartbeats fail | pass | pass | pass |
| H13 | shared budgets cannot be overspent across governors | pass | pass | pass |
| H14 | partitions and epoch changes end in safe states | pass | pass | pass |
| H15 | no debug path in production; tamper zeroizes | pass | pass | pass |
| H16 | the levers work without the GPU's cooperation | pass | pass | pass |

## Modelled overhead (H9)

A model, not a measurement: operation counts from the functional model priced with the figures in `docs/04-specification.md` §9, against a GPU doing 2,000 tokens per second.

| Tier | Tokens | Governor time | GPU time | Overhead |
|---|---|---|---|---|
| rack | 100,000 | 205.1 ms | 50.0 s | 0.410 % |
| integrated | 100,000 | 205.1 ms | 50.0 s | 0.410 % |

## What the gaps mean

- **H2b at rack and board**: from the board the governor governs links and flows, not descriptors. Two legitimate roster members can exchange bytes a rule would not have allowed. That is the residual named in `docs/00-objectives.md` N5; the in-GPU checkers of the integrated tier close it.
- **H2a at board**: a system where the switches' management is unreachable, or a baseboard with direct NVLink and no NVSwitch, has no port authority. The governor still has its levers, its tickets and its log; it cannot keep a stranger off the link.
