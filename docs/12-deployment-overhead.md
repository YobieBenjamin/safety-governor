# 12. Whole-deployment overhead (N1)

> **In plain words:** the one percent claim was made for one chip. This note runs the whole
> deployment, 72 governors with eight GPU slots each, as a simulation with queues (72 independent
> chips: there is no cross-chip traffic, so the 72 add sample size, not interaction), and asks two
> questions: how much throughput is lost, and how much latency is added at the tail. At the plan
> of record the answers are about 0.015 percent and about 46 milliseconds, *measured as the tokens
> the governed run produces below a no-governor baseline, not a bookkeeping sum*. The claim holds,
> with one condition that matters: the runtime must not hold the GPU slot while it waits for the
> receipt. That condition is this note's reading of the plan of record, not a sentence of the
> spec (section 2). **Code:** `govsim/deploy.py` (`python -m govsim.deploy`). **Tests:**
> `tests/test_deploy_overhead.py`.
> **Inputs:** `govsim/bench.py`, `docs/04-specification.md` §9, `docs/10` §14.

## 1. Method

A discrete-event simulation in simpy (`python -m govsim.deploy`; the brief provides simpy). Each
of 72 governor chips has:

- one firmware core, a FIFO queue, serving mailbox commands (20 µs), ticket mints (20 µs), log
  appends, the per-window Merkle root, heartbeat fan-out, and edition-change port programming
  (1 ms per port change, 2 ms attestation);
- one signing engine, 17 ms per ECDSA P-384 signature (OpenTitan OTBN, docs/04 §9), serial, one
  signature per 50 ms batch window over the records that finished in it;
- eight GPU slots, one request at a time each, 500 tokens mean (exponential) at 2,000 tokens per
  second, so 250 ms mean service; 0.05 mailbox calls per response, the reference workload of
  `bench.py`. A mailbox call blocks the issuing slot until the firmware answers.

Mid-run, every chip takes an edition change with revocation: attest the staged image, close and
reopen each slot's port with the slot out of service, reissue each slot's live ticket. Heartbeats
run at 1 s, each costing a verify plus a tell to each slot (5 µs times nine).

Two regimes per policy, each against a no-governor baseline with the same random draws:

- **Saturated** (every slot always busy). Throughput lost is *measured*: the tokens the governed
  run produces below the baseline's in the same run; the bookkeeping stall share is printed beside
  it as a cross-check; the two agree to within 0.003 percentage points (0.0151 and 0.0168 percent;
  the stall share also counts slot time inside requests unfinished at the horizon). For the plan of record the slot is
  freed the instant the record is logged, so the receipt wait is off the slot's path: it adds
  latency to the response but not throughput to the GPU. The worst case, the slot held until the
  receipt, is swept separately.
- **Open** (Poisson arrivals at 70 percent of capacity). Added latency is the p99 of the request
  latency minus the baseline's p99, and the p99 wait for the provenance receipt. Latency runs
  from the arrival, so a request that finds its slot busy carries its queueing delay, in the
  baseline and the governed run alike (p99 about 3.3 s, against 1.15 s for the exponential service-time
  tail alone, 250 ms times ln 100). The governor's stalls therefore reach the tail through the queue as well as
  through the receipt wait.

The log-write (30 µs), Merkle-root (20 µs) and heartbeat fan-out (5 µs times nine) costs are
assumptions not in `bench.py` or docs/04; they are named here, swept in `sensitivity` (ten times
any one stays under one percent), and are the figures Phase 2 replaces.

## 2. Results (72 governors, 576 GPUs, 30 s of simulated time per run)

Plan of record: 50 ms window, release gated on the receipt, the slot freed for the next request
while the receipt is pending. **The last clause is this note's assumption.** `bench.py` says only
that a runtime which insists on the record waits one window plus one signature, and docs/04 §9 says
the record trails the response; neither says whether the GPU slot is held meanwhile. The slot-held
reading is therefore swept in section 3 as the alternative, and it is above one percent.

| Quantity | Value |
|---|---|
| Throughput lost (measured) | 0.015 percent (34,273,417 governed vs 34,278,595 baseline tokens) |
| Cross-check: stall share | 0.017 percent |
| p99 added latency | 46 ms (p99 3337 ms against 3291 ms without the governor, queueing included) |
| p99 receipt wait | 66.5 ms against the 67 ms idle-core bound of docs/04 §9 |
| Max receipt wait | 68.4 ms with the mid-run edition change, 67.0 ms without it |
| Busiest signing engine | 28.5 percent (limit 50) |
| Busiest firmware core | 0.21 percent |

The 67 ms bound of docs/04 §9 is exact for an idle firmware core at the window edge, and it is
what the run without the edition change gives (67.0 ms). With the edition change the maximum is
68.4 ms: the Merkle root of one window waits behind a firmware operation of the change (the queue
is FIFO, so it waits for the operations ahead of it, not the whole 18 ms). The excess is 1.4 ms;
the test asserts it is under 5 ms, so the 18 ms is a ceiling, not the observed delay.

## 3. Where it crosses one percent

**Mailbox load.** Stall share of slot time by mailbox calls per response, plan of record
otherwise, 10 s. The sweeps report the stall share; at 80 calls the measured token loss against
the baseline is 1.71 percent against a stall share of 1.45, so the token-based crossing is a
little lower and both are far above the reference workload:

| calls per response | 0.05 | 5 | 20 | 40 | 80 | 160 |
|---|---|---|---|---|---|---|
| stall share (percent) | 0.02 | 0.11 | 0.38 | 0.73 | 1.45 | 3.01 |

It crosses one percent at about 55 mailbox calls per response, about 1,100x the reference workload
(0.05). A governor firmware core is not the constraint at any plausible action rate. The results
table runs 30 s and the sweeps 10 s, so the edition-change term, one event per chip, is divided by
a shorter simulated time and reads a little higher at 10 s; the mailbox term itself is the same.

**Slot held until the receipt.** If the runtime keeps the GPU slot occupied until the receipt
arrives (no pipelining), the slot idles for the receipt wait on every response:

| window | 20 ms | 30 ms | 50 ms | 100 ms | 200 ms |
|---|---|---|---|---|---|
| serviceable | no | no | yes | yes | yes |
| stall share (percent) | 9.9 | 11.4 | 14.3 | 21.2 | 32.9 |

A window must exceed the 17 ms signature, so no serviceable window gets near one percent: the
disproof condition ("above one percent at every serviceable policy") is met **for this policy**,
and it is asserted as such in the test. It is **not** met for the plan of record as read
here (slot freed), which costs 0.015 percent; the test asserts both sides. If the spec's plan of
record is the slot-held reading, the disproof stands and the one percent claim fails for the whole
deployment; which reading is the spec's is an open question for the owner of docs/04 §9. The requirement it adds is a design rule: **the
runtime releases a response on the receipt but must not stall the next request on it.** The receipt
is latency on the response, not throughput on the GPU.

**Named assumptions.** Ten times any of the three costs named above (swept in `sensitivity`, 10
s): log write 0.13 percent, Merkle root 0.02 percent, heartbeat fan-out 0.02 percent. None moves
the plan of record off the sub-one-percent figure.

## 4. What this does not show

- It is a model. Phase 2 measures real firmware, a real engine and a real mailbox; those replace
  the constants.
- Arrivals are Poisson and sizes exponential, one queue per slot at 70 percent load. Bursty traffic that
  lines many responses up inside one window changes nothing for the engine (one signature per
  window) but would raise the tail wait for the unlucky first record.
- One edition change, with revocation, is modelled; a storm of them is not. Each costs about
  18 ms of firmware per chip, so even one a second would be under two percent of the core.
- The 72 chips are independent copies. Heartbeat fan-out is the verify-once, tell-each-slot cost on
  one chip; the authority's fan-out across chips and its latency are not modelled, so "whole
  deployment" here means 72 chips of load, not 72 interacting chips.
- Fabric and switch programming beyond the per-port 1 ms, and cross-chip message latency, are not
  simulated; heartbeats are costed on the receiving chip only.
