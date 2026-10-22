# 12. Whole-deployment overhead (N1)

> **In plain words:** the one percent claim was made for one chip. This note runs the whole
> deployment, 72 governors with eight GPU slots each, as a simulation with queues, and asks two
> questions: how much throughput is lost, and how much latency is added at the tail. At the plan
> of record the answers are 0.02 percent and about 57 milliseconds. The claim holds, with one
> condition that matters: the runtime must not hold the GPU slot while it waits for the receipt.
> **Code:** `govsim/deploy.py` (`python -m govsim.deploy`). **Tests:** `tests/test_deploy_overhead.py`.
> **Inputs:** `govsim/bench.py`, `docs/04-specification.md` §9, `docs/10` §14.

## 1. Method

A discrete-event simulation in simpy (`govsim/_minisim.py` is a small stand-in used only when
simpy is not importable). Each of 72 governor chips has:

- one firmware core, a FIFO queue, serving mailbox commands (20 µs), ticket mints (20 µs), log
  appends, the per-window Merkle root, heartbeat fan-out, and edition-change port programming
  (1 ms per port change, 2 ms attestation);
- one signing engine, 17 ms per ECDSA P-384 signature (OpenTitan OTBN, 1,697,985 cycles at
  100 MHz), serial, one signature per 50 ms batch window over the records that finished in it;
- eight GPU slots, one request at a time each, 500 tokens mean (exponential) at 2,000 tokens per
  second, so 250 ms mean service; 0.05 mailbox calls per response, the reference workload of
  `bench.py`. A mailbox call blocks the issuing slot until the firmware answers.

Mid-run, every chip takes an edition change with revocation: attest the staged image, close
and reopen each slot's port with the slot out of service, reissue each slot's live ticket.
Heartbeats run at 1 s, each costing a verify plus a tell to each slot.

Two runs per policy, each against a no-governor baseline with the same random draws:

- **Saturated** (every slot always busy). Throughput lost is the share of slot time spent
  stalled on the governor: firmware queueing, the log append, the port reprogramming, and, if
  the policy holds the slot, the wait for the receipt.
- **Open** (Poisson arrivals at 70 percent of capacity). Added latency is the p99 request
  latency minus the baseline's p99; the receipt wait is also reported alone.

Assumptions not in `bench.py` or docs/04: a log append is 30 µs of firmware per response; the
Merkle root over a window is 20 µs; the heartbeat fan-out is 5 µs times nine. They are small
beside everything else and none moves a conclusion; they are named so Phase 2 can replace them.

## 2. Results (72 governors, 576 GPUs, 30 s of simulated time per run)

Plan of record: 50 ms window, release gated on the receipt, the slot freed for the next request
while the receipt is pending.

| Quantity | Value |
|---|---|
| Throughput lost | 0.017 percent |
| p99 added latency | 56 ms (p99 1200 ms against 1143 ms without the governor) |
| p99 receipt wait | 66.5 ms against the 67 ms bound of docs/04 §9 |
| Busiest signing engine | 28 percent (limit 50) |
| Busiest firmware core | 0.19 percent |

The 67 ms bound holds at the 99th percentile. The maximum seen is 74 ms: a record that
arrives while the firmware is working through the edition change waits behind about 18 ms of
port programming for its Merkle root. The bound in docs/04 §9 is exact only while the firmware
is idle at the window edge.

## 3. Where it crosses one percent

**Mailbox load.** Overhead by mailbox calls per response, plan of record otherwise:

| calls per response | 0.05 | 5 | 20 | 40 | 80 | 160 |
|---|---|---|---|---|---|---|
| overhead (percent) | 0.03 | 0.11 | 0.33 | 0.63 | 1.24 | 2.56 |

It crosses one percent at about 64 mailbox calls per response, 1,300 times the reference
workload. A governor firmware core is not the constraint at any plausible action rate.

**Slot held until the receipt.** If the runtime keeps the GPU slot occupied until the receipt
arrives (no pipelining), the slot idles for the receipt wait on every response:

| window | 20 ms | 30 ms | 50 ms | 100 ms | 200 ms |
|---|---|---|---|---|---|
| serviceable | no | no | yes | yes | yes |
| overhead (percent) | 9.9 | 11.4 | 14.3 | 21.2 | 32.9 |

A window must exceed the 17 ms signature, so no serviceable window gets near one percent:
the disproof condition ("above one percent at every serviceable policy") is met **for this
policy**, and it is asserted as such in the test. It is not met for the plan of record. The
requirement it adds is a design rule: **the runtime releases a response on the receipt but
must not stall the next request on it.** The receipt is latency on the response, not
throughput on the GPU.

## 4. What this does not show

- It is a model. Phase 2 measures real firmware, a real engine and a real mailbox; those
  replace the constants.
- Arrivals are Poisson and sizes exponential. Bursty traffic that lines many responses up
  inside one window changes nothing for the engine (one signature per window) but would raise
  the tail wait for the unlucky first record.
- One edition change, with revocation, is modelled; a storm of them is not. Each costs about
  18 ms of firmware per chip, so even one a second would be under two percent of the core.
- Fabric and switch programming beyond the per-port 1 ms, and cross-chip message latency, are
  not simulated; heartbeats are costed on the receiving chip only.
