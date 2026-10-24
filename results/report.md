# Sweep report

Generated 2026-10-24 00:05 UTC by `govsim sweep`.

`pass`: the hypothesis held. `gap`: it failed exactly as the design predicts for that tier (the recorded residual). `FAIL`: it failed in a way the design does not predict.

| Id | Hypothesis | rack (plan of record) | board (fallback) | integrated (future ask) |
|---|---|---|---|---|
| H0 | every protected operation needs a fresh, exact, single-use authorization | pass | pass | pass |
| H1 | attestation binds permissions to firmware, model and policy | pass | pass | pass |
| H2a | link-level: no bytes to a non-roster peer; unchecked paths bricked | pass | gap | pass |
| H2b | descriptor-level: a transfer between two roster members the buffer policy would not allow | gap | gap | pass |
| H3 | policy changes only with a quorum, never backwards | pass | pass | pass |
| H4 | the broker cannot choose its rule or lane | pass | pass | pass |
| H5 | alarms are monotone | pass | pass | pass |
| H6 | the comparator holds with every layer above it compromised | pass | pass | pass |
| H7 | the assumptions register is complete or the policy does not load | pass | pass | pass |
| H8 | human override is slow and fully logged | pass | pass | pass |
| H9 | zero per-token work; firmware under one percent of GPU time; the signing engine keeps up | pass | pass | pass |
| H10 | permitted-channel leakage trips the budget | pass | pass | pass |
| H11 | a halt reaches every GPU within the bound; nobody clears alone; a governor jumpered out of the loop is named and the loop opened | pass | pass | pass |
| H12 | only roster members speak on the fabric; forged heartbeats fail | pass | pass | pass |
| H13 | shared budgets cannot be overspent across governors | pass | pass | pass |
| H14 | partitions and epoch changes end in safe states | pass | pass | pass |
| H15 | no debug path in production; tamper zeroizes | pass | pass | pass |
| H16 | the levers work without the GPU's cooperation | pass | pass | pass |
| H17 | no governed action initiates without a ticket and no governed response leaves the rack without a release ticket | pass | pass | pass |
| H18 | oversight survives the model: the observer is always invoked and cannot be impersonated, audit sampling is unpredictable, the evaluated model is the deployed model, compute and hazard budgets bind | pass | pass | pass |

## Modelled cost (H9)

A model, not a measurement: operation counts from the functional model priced with the figures in `docs/04-specification.md` §9, against a GPU doing 2,000 tokens per second with 500-token responses. Firmware time is the share of GPU time spent on action paths. The signing engine (ECDSA P-384 at OpenTitan's published 1,697,985 OTBN cycles, 17 ms at 100 MHz, shared by eight slots) runs beside the GPU and has to keep up; one signature per 50 ms batch window caps it. Record latency is the most a response waits if the runtime insists on its record before release.

| Tier | Tokens | Firmware time | GPU time | Firmware share | Engine, one signature per response | Engine, batched | Record latency |
|---|---|---|---|---|---|---|---|
| rack | 100,000 | 5.2 ms | 50.0 s | 0.010 % | 54 % | 34 % | 67 ms |
| integrated | 100,000 | 5.2 ms | 50.0 s | 0.010 % | 54 % | 34 % | 67 ms |
| rack, 100-token responses | 20,000 | 5.2 ms | 10.0 s | 0.052 % | 272 % (cannot keep up) | 34 % | 67 ms |

## Full request-to-effect path (F23)

The table above prices only the batched provenance records. The real path also requests a release ticket for every response, and the governor signs every ticket. Those per-response release tickets are per-item capabilities: each independently authorises one response to leave, so they cannot be collapsed under one Merkle root the way the records can, and they must be priced too. Below, the records-only figure is the 34 percent above; the full-path figure adds the release-ticket signatures.

| Response size | Records only | Full path (incl. release tickets) |
|---|---|---|
| 500-token responses | 34 % | 88 % |
| 100-token responses | 34 % | 306 % (over one engine) |

At 100-token responses the honest engine load is well over one engine, not 34 percent. The release-ticket signatures are not hidden. The implication, stated plainly: at small response sizes a single OTBN-class engine cannot keep up, and the design needs faster signing hardware, verifiable batch authorisation with atomic per-item consumption, or a keyed endpoint MAC for the release tickets. The 34 percent figure holds only for the records, and only the records were ever batched.

## What the gaps mean

- **H2b at rack and board**: from the board the governor governs links and flows, not descriptors. Two legitimate roster members can exchange bytes the buffer policy would not have allowed (the weights, over the copy engine). That is the residual named in `docs/00-objectives.md` N5. At the integrated tier the descriptor checkers are keyed per buffer class and programmed from the policy image's buffer policy, which closes it there.
- **H2a at board**: a system where the switches' management is unreachable, or a baseboard with direct NVLink and no NVSwitch, has no port authority. The governor still has its levers, its tickets and its log; it cannot keep a stranger off the link.
