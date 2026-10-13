# 02 · The safety fabric

Two wires run through every governor in a cluster. They are physically separate from the
data network, the management network and the host. One is dumb and fast. One is smart and
signed. Both are fail-safe.

In plain words: a fire-alarm loop and an intercom. The loop rings every bell the instant any
station is pulled, and rings them if the wire is cut. The intercom carries the details:
who pulled it, which edition of the rulebook is in force, who is still on duty.

> **Plain-English version:** `10-plain-english-walkthrough.md` §6.
> **Backed by:** model `govsim/fabric.py` (`HaltLoop`, `MessageFabric`), `govsim/governor.py`
> (`_heartbeat`, `sense_loop`, `on_fabric`, `publish_checkpoint`), `govsim/cluster.py`
> (`change_epoch`, `exchange_checkpoints`); tests `tests/test_h11_halt_loop.py`,
> `test_h12_fabric_auth.py`, `test_h13_shared_budget.py`, `test_h14_partition.py`; hardware
> `rtl/governor_rtl/halt_loop.py`, `heartbeat.py`, `epoch_reg.py`; wiring
> `hw/pcb/rack-integration.md` §4.

## 1. The halt loop

**What it is.** A supervised series current loop threaded through every governor in a
safety domain, with a live-zero current (the 4 to 20 mA idea: a dead wire reads as zero and
zero means stop), the same fail-open principle as a fire-alarm initiating circuit. Each
governor has a loop-in and a loop-out pin and a switch between them. Each governor also
senses loop current.

![The halt loop as a circuit](figures/fig-halt-loop.png)

**Rules.**

- Any governor opens its switch on a loop-opening cause: a signed HALT from the authority, a
  detected tamper, or loss of loop current itself (`01-architecture.md`, safe-mode machine).
  Local causes (a lost heartbeat, a stale epoch, an exhausted output budget) throttle and
  halt that governor's own slot without opening the loop.
- Loss of loop current at any governor drives that governor's halt output within the debounce
  window of two sense periods (target 100 µs per period, bound 1 ms end to end for a 72-GPU
  domain).
- The switch starts open at power-on and closes when the governor is armed (no open cause
  and a valid heartbeat); the governor goes to RUN when it then sees loop current, which
  means every governor in the domain has closed its switch.
- A broken wire, a lost connector, a dead governor or a pulled board all read as "open"
  and halt the domain. Fail-safe by construction.
- The loop is closed again only when every governor has received a signed CLEAR over the
  message fabric and has logged it. A governor whose cause is not cleared keeps the loop open.
- Domains are configurable: a cluster may run several loops (one per job pod) joined by a
  supervisor governor that bridges them under policy.

**Why a wire and not a message.** A message can be dropped, delayed, replayed or filtered
by anything between sender and receiver. A current loop has no software between a pull and
a bell. Fire codes learned this a century ago.

**Timing.** Sense period 100 µs. Propagation is electrical, so the end-to-end bound is set by
the slowest sense period plus debounce: 1 ms. These are design targets, to be measured on
the bench in Phase 2; the functional model's "100 µs" is a parameter, not a result. The GPU's
power brake asserts within 1 ms of the governor's halt output; reset and power cut follow the
policy's rungs.

**Tested by.** `tests/test_h11_halt_loop.py`: any governor halting halts all; a cut wire
halts all; no governor clears on its own; propagation stays within the bound.

## 2. The message fabric

**What it is.** A private out-of-band network between governors: two SGMII-class ports per
governor forming a dual ring, or a star to a safety switch that is itself a governor. On the
board-level tier the physical layer can be 100BASE-T1 (two-wire automotive Ethernet) or
RS-485 for small clusters. Bandwidth needs are tiny: attestation quotes, rosters, epochs,
heartbeats, reservations and checkpoint heads, kilobytes per second per governor.

**Every message** carries: sender identity (DICE-derived key id), the sender's policy epoch,
a per-sender sequence number, a timestamp from the sender's monotonic counter, the message
type and body, and a signature. A receiver accepts a message only if the sender is on the
current roster (or the message is a roster-formation quote, a roster, or a heartbeat relay,
which carry their own authentication), the epoch matches, the sequence number is greater than
the last seen from that sender, and the signature verifies. Last-seen sequence numbers are
durable, so a receiver that lost power does not reopen the replay window, and a sender that
lost power resumes its numbering above where it was.

In plain words: every note on the intercom is signed, numbered and dated. A note from
someone not on the roll, an old note read out again, or a note under last year's rulebook
goes in the bin.

### Message types

| Type | From → to | Body | Purpose |
|---|---|---|---|
| `QUOTE` | governor → all | Attestation quote over a nonce; GPU fingerprint; capabilities | Roster formation |
| `ROSTER` | roster leader → members | Job id, member list with key ids, expiry, signatures | Scope every later decision |
| `HEARTBEAT` | authority → governors, relayed hop by hop | Validity window, epoch, authority signature, relay signature and hop count | Dead man's switch |
| `POLICY_PROPOSE` / `POLICY_COMMIT` | authority → each governor's mailbox, relayed by the host (a governor holding the authority's relay role may carry them over the fabric) | Policy image with its k-of-n signatures; then the digest | Stage, then switch the epoch. The model delivers them by mailbox; the acknowledgement is the mailbox reply |
| `RESERVE` | governor → budget owner | Budget key, amount, ticket id, expiry | Shared budgets; the owner's reply is `RESERVE_OK` or `RESERVE_DENY` |
| `COMMIT` | governor → budget owner | Reservation id | Spend a reservation; an uncommitted reservation expires with its ticket |
| `ALARM` | governor → all | Cause code, request hash, evidence digest | A witness any governor may raise |
| `HALT_CAUSE` | governor → all | Cause, log head | Why the loop opened |
| `CLEAR` | authority → the governor's mailbox | Signature | Clear the cause and close the loop at one governor, once the cause is in the log and a neighbor has acknowledged the checkpoint |
| `CHECKPOINT` / `CHECKPOINT_ACK` | governor → neighbors → governor | Log Merkle root, size, head, signature; the acknowledgement names the head | Cross-linked logs; the acknowledgement is what CLEAR requires |

### Roster formation

1. A job scheduler (untrusted) names the GPUs it wants.
2. Each named governor broadcasts a `QUOTE` over a nonce derived from the job id and its
   monotonic counter.
3. The lowest chip id among valid quotes acts as roster leader for the job; it assembles the
   `ROSTER` and signs it; each member verifies the leader's signature and the quotes inside
   it before adopting it (a forged roster is dropped and logged).
4. The roster is live at a member when it holds the leader-signed roster; the roster is
   durable until it expires, so a power cycle does not lose it. It expires with the job or at
   its stated time, whichever is first. Member countersignatures, which would let the leader
   know who adopted, are not in the model.
5. The switch ports and flows opened for the job, the shared budgets and the job's output
   records all name the roster id.

A governor whose GPU fails attestation cannot produce a valid `QUOTE` and is simply absent
from the roster. Nothing it says afterwards is accepted. Analogy: no badge, no seat on the bus,
and nobody listens to you shouting from the parking lot.

### Epoch change, cluster-atomic

A policy change that reaches some GPUs and not others is a hazard: a ticket minted under the
new rules could be presented to an endpoint still on the old ones, or the reverse. So the
epoch moves in two phases, and the heartbeat enforces the outcome:

1. `POLICY_PROPOSE` carries the signed image. Every member verifies the image and the quorum
   itself (it does not trust the authority's word), stages it, records when it staged it, and
   acknowledges.
2. The authority sends `POLICY_COMMIT` to the members that acknowledged; each switches its
   epoch register at the commit, and tickets, capabilities and messages from the old epoch
   die there.
3. From then on the authority's heartbeat carries the new epoch. A member that never staged
   the image cannot accept that heartbeat (`POLICY_STALE_EPOCH`), its timer expires, and it
   enters safe mode as `HEARTBEAT_LOST`.
4. A member that staged the image but never saw the commit accepts the new-epoch heartbeat
   only until the staged-policy deadline (`fabric.epoch_deadline_s`, default 10 s); after that
   it refuses the heartbeat too and enters safe mode as `EPOCH_STRAGGLER`, on the rung the
   policy names for that cause.

No governor is left running on the old rules; the ones the authority could not reach, or
could not finish with, stop. Analogy: the new edition of the rulebook is handed out,
everyone initials receipt, and the manager says "from now" to those who did. Anyone who did
not initial, or initialled and then missed the word, is sent home, not left working from the
old book.

### Heartbeat fan-out

The policy authority (a key, not a chip) signs a heartbeat with a validity window. It enters
the fabric at one or more governors and is relayed hop by hop; each relay signs the relayed
message with its own fabric key and increments the hop count. A governor accepts a heartbeat
if the authority's signature verifies, the sequence number is new, the window is current, the
relay's signature verifies for a roster member, and the hop count is under the policy limit.
The governor clamps the window to the policy's `heartbeat_expiry_s`, so an over-long window
signed by a careless authority cannot keep a governor alive for longer than the policy allows.
A governor that receives no valid heartbeat before its timer expires enters safe mode. A
partitioned segment that is cut off from the authority halts itself at expiry; nothing in the
segment can forge the authority's signature to keep itself alive.

### Shared budgets

A budget key has exactly one owner, named in the policy image (`budget_owners`); the loader
refuses an image in which a rule's budget key has no owner, so there is no default. A
governor that needs to reserve against a shared key sends `RESERVE` to the owner; the owner
runs the same check-reserve-commit transaction it runs locally and answers. The requesting
governor mints the ticket only on `RESERVE_OK`. Reservations expire with the ticket. If the
owner becomes unreachable between the reservation and the commit, the commit fails and the
endpoint does not act; the reservation expires at the owner and nothing is spent twice. An
automatic release-and-re-request when an owner leaves the roster is not in the model. This is
the blog's rule "one ledger owns a budget key" made concrete across a cluster. Analogy: one
cashier per cash drawer; a second cashier does not guess what is in it.

### Cross-linked logs

Every governor keeps its own hash-chained log and publishes signed checkpoints. Each
checkpoint also includes the latest checkpoint heads it has received from its fabric
neighbors. Rewriting one governor's history now requires rewriting its neighbors', and
theirs, outward through the cluster. Analogy: each security office writes the last line of
the neighbors' log books into its own.

## 3. Partitions and failure

| Event | Loop | Fabric | Outcome |
|---|---|---|---|
| One governor loses power | opens | silent | Domain halts; CLEAR after the cause is understood |
| Fabric link cut, loop intact | closed | partitioned | Segment without the authority halts at heartbeat expiry; segment with the authority continues; roster rebuilt |
| Loop cut, fabric intact | open | up | Domain halts at once; `HALT_CAUSE` says "loop break at governor N" |
| Authority key unreachable | stays closed | up, no heartbeats | Every governor throttles at expiry and climbs its own rungs on the policy timers (availability cost, by design); the loop is for the rack-wide stop, not for this |
| Rogue device plugged into the fabric | closed | sees traffic | Cannot produce a valid quote; never on a roster; its messages are dropped; its presence is logged |
| Replay of an old heartbeat | closed | up | Sequence number and window fail; dropped; logged |

**Tested by.** `tests/test_h12_fabric_auth.py`, `tests/test_h13_shared_budget.py`,
`tests/test_h14_partition.py`.

## 4. What the fabric does not do

It does not carry model data. It does not carry tool-call payloads. It cannot speed up a
halt beyond the loop (it carries the reason, not the stop). It cannot make a governor trust a
GPU that failed attestation. And it is not a consensus protocol in the Paxos sense: the policy
authority is a single key with a quorum behind it, and the fabric's job is to deliver that
authority's decisions to every governor or to halt the ones it cannot reach.
