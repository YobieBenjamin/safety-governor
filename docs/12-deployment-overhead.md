# 12. Whole-deployment overhead (N1)

> **In plain words:** the one percent claim was made for one chip. This note runs the whole
> deployment, 72 governors with eight GPU slots each, as a simulation with queues, and asks two
> questions: how much throughput is lost, and how much latency is added at the tail. At the plan
> of record the answers are about 0.02 percent and about 42 milliseconds, *measured as the tokens
> the governed run produces below a no-governor baseline, not a bookkeeping sum*. The claim holds,
> with one condition that matters: the runtime must not hold the GPU slot while it waits for the
> receipt. **Code:** `govsim/deploy.py` (`python -m govsim.deploy`). **Tests:**
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
  it as a cross-check, and the two agree to within rounding. For the plan of record the slot is
  freed the instant the record is logged, so the receipt wait is off the slot's path: it adds
  latency to the response but not throughput to the GPU. The worst case, the slot held until the
  receipt, is swept separately.
- **Open** (Poisson arrivals at 70 percent of capacity). Added latency is the p99 of the request
  latency minus the baseline's p99, and the p99 wait for the provenance receipt. In this one-
  process-per-slot model a request never queues, so the added latency is the receipt wait, not a
  load tail; the throughput effect of load is the saturated comparison above.

The log-write (30 µs), Merkle-root (20 µs) and heartbeat fan-out (5 µs times nine) costs are
assumptions not in `bench.py` or docs/04; they are named here, swept in `sensitivity` (ten times
any one stays under one percent), and are the figures Phase 2 replaces.

## 2. Results (72 governors, 576 GPUs, 30 s of simulated time per run)

Plan of record: 50 ms window, release gated on the receipt, the slot freed for the next request
while the receipt is pending.

| Quantity | Value |
|---|---|
| Throughput lost (measured) | 0.015 percent (34,273,417 governed vs 34,278,595 baseline tokens) |
| Cross-check: stall share | 0.017 percent |
| p99 added latency | 42 ms (p99 1185 ms against 1143 ms without the governor) |
| p99 receipt wait | 66.5 ms against the 67 ms idle-core bound of docs/04 §9 |
| Max receipt wait | 68 ms: the one record that lands on the mid-run edition change, which adds its 18 ms of firmware |
| Busiest signing engine | about 28 percent (limit 50) |
| Busiest firmware core | 0.21 percent |

The 67 ms bound of docs/04 §9 is exact only for an idle firmware core at the window edge; the
maximum seen (68 ms) is the one record that lands on the edition change, which adds about 18 ms of
firmware to that chip, so the realistic bound is window plus signature plus the edition change.
`measure` reports both, and the test asserts the realistic one.

## 3. Where it crosses one percent

**Mailbox load.** Overhead by mailbox calls per response, plan of record otherwise, 10 s:

| calls per response | 0.05 | 5 | 20 | 40 | 80 | 160 |
|---|---|---|---|---|---|---|
| overhead (percent) | 0.02 | 0.11 | 0.38 | 0.73 | 1.45 | 3.01 |

It crosses one percent at about 55 mailbox calls per response, about 1,100x the reference workload
(0.05). A governor firmware core is not the constraint at any plausible action rate. The results
table runs 30 s and the sweeps 10 s, so the edition-change term, one event per chip, is divided by
a shorter simulated time and reads a little higher at 10 s; the mailbox term itself is the same.

**Slot held until the receipt.** If the runtime keeps the GPU slot occupied until the receipt
arrives (no pipelining), the slot idles for the receipt wait on every response:

| window | 20 ms | 30 ms | 50 ms | 100 ms | 200 ms |
|---|---|---|---|---|---|
| serviceable | no | no | yes | yes | yes |
| overhead (percent) | 9.9 | 11.4 | 14.3 | 21.2 | 32.9 |

A window must exceed the 17 ms signature, so no serviceable window gets near one percent: the
disproof condition ("above one percent at every serviceable policy") is met **for this policy**,
and it is asserted as such in the test. It is **not** met for the plan of record, which costs
0.015 percent; the test asserts both sides. The requirement it adds is a design rule: **the
runtime releases a response on the receipt but must not stall the next request on it.** The receipt
is latency on the response, not throughput on the GPU.

**Named assumptions.** Ten times any of the three costs named above (swept in `sensitivity`, 10
s): log write 0.13 percent, Merkle root 0.02 percent, heartbeat fan-out 0.02 percent. None moves
the plan of record off the sub-one-percent figure.

## 4. What this does not show

- It is a model. Phase 2 measures real firmware, a real engine and a real mailbox; those replace
  the constants.
- Arrivals are Poisson and sizes exponential, and the open regime is one process per slot, so a
  request never queues: the added latency is the receipt wait, not a load tail. Bursty traffic that
  lines many responses up inside one window changes nothing for the engine (one signature per
  window) but would raise the tail wait for the unlucky first record.
- One edition change, with revocation, is modelled; a storm of them is not. Each costs about
  18 ms of firmware per chip, so even one a second would be under two percent of the core.
- Fabric and switch programming beyond the per-port 1 ms, and cross-chip message latency, are not
  simulated; heartbeats are costed on the receiving chip only.
