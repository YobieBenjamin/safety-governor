"""N1: the whole-deployment overhead (docs/12). ``bench.py`` prices one chip's operations; this
module runs 72 governors with eight GPU slots each as a discrete-event simulation and
measures what the one-percent claim needs: throughput lost and tail latency added, with the
queues the per-chip arithmetic leaves out.

What is simulated, per governor chip: one firmware core (a FIFO queue) that serves mailbox
commands, ticket mints, log appends, the per-window Merkle root, heartbeats and the port
programming of an edition change; one signing engine (17 ms per ECDSA P-384 signature, one
signature per batch window over the records that finished in it); eight GPU slots, each
serving requests one at a time. The figures are ``bench.py``'s and docs/04 §9's; the log-write,
Merkle-root and heartbeat fan-out costs are assumptions named in docs/12 and swept in
``sensitivity``.

Two regimes per policy, both with common random numbers against a no-governor baseline:

* saturated: every slot always has a request waiting, as in bench.py's "the GPU is busy
  throughout". Throughput lost is *measured*: the tokens the governed run produces below the
  baseline's in the same simulation, not a bookkeeping sum. The stall share is reported beside it
  as a cross-check. For the plan of record the slot is freed the instant the record is logged, so
  the receipt wait is off the slot's path: it adds latency to the response, not throughput to the
  GPU.
* open: Poisson arrivals at 70 percent of slot capacity. Added latency is the p99 of the request
  latency minus the baseline's p99, and the p99 wait for the provenance receipt. In this one-
  process-per-slot model a request never queues, so the added latency is the receipt wait; the
  throughput effect of load is the saturated comparison above.

The model is not a measurement. Phase 2 on real hardware replaces it.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace

import simpy                                          # brief: installed in the container

from .bench import BATCH_WINDOW_S, COST_S, GPU_SECONDS_PER_TOKEN, SIGN_S, SLOTS_PER_CHIP

GOVERNORS = 72
MEAN_TOKENS = 500
OPEN_LOAD = 0.7                      # open-loop arrival rate as a share of slot capacity
LOG_WRITE_S = 30e-6                  # assumption: one authenticated NVM append per response record
MERKLE_S = 20e-6                     # assumption: one root over the window's records, firmware
HEARTBEAT_PERIOD_S = 1.0             # docs/04 §9
HEARTBEAT_FANOUT_S = COST_S["heartbeat"] * (1 + SLOTS_PER_CHIP)   # verify once, tell each slot
ACTIONS_PER_RESPONSE = 50 / 1000     # bench.py's reference workload
ONE_PERCENT = 1.0


@dataclass(frozen=True)
class Policy:
    """The knobs a deployment can turn. The plan of record is the default."""
    window_s: float = BATCH_WINDOW_S         # signature batch window
    gate: bool = True                        # the runtime releases a response only with its receipt
    hold_slot: bool = False                  # ... and keeps the GPU slot busy until then (worst case)
    actions_per_response: float = ACTIONS_PER_RESPONSE
    edition_change: bool = True              # one edition change with revocation mid-run
    governors: int = GOVERNORS
    log_write_s: float = LOG_WRITE_S         # the three named assumptions, swept in sensitivity()
    merkle_s: float = MERKLE_S
    heartbeat_s: float = HEARTBEAT_FANOUT_S

    @property
    def serviceable(self) -> bool:
        """docs/04 §9: the window is longer than the signature and the engine stays under 50 percent."""
        return self.window_s > SIGN_S and SIGN_S / self.window_s < 0.5

    def label(self) -> str:
        return (f"window={self.window_s*1e3:g} ms gate={'on' if self.gate else 'off'} "
                f"hold_slot={'yes' if self.hold_slot else 'no'} actions/response={self.actions_per_response:g}")


PLAN_OF_RECORD = Policy()


def edition_firmware_s() -> float:
    """Firmware time of one edition change with revocation on one chip: attest the staged image,
    then for each slot close and reopen its port and reissue its live ticket (docs/04 §9)."""
    per_slot = 2 * COST_S["switch_program"] + COST_S["ticket"]
    return COST_S["attest"] + SLOTS_PER_CHIP * per_slot


class Chip:
    def __init__(self, env, idx: int, pol: Policy, governed: bool, rng: random.Random):
        self.env, self.idx, self.pol, self.governed = env, idx, pol, governed
        self.fw = simpy.Resource(env, 1)                       # the firmware core
        self.engine = simpy.Resource(env, 1)
        self.engine_busy_s = 0.0
        self.fw_busy_s = 0.0
        self.pending: list = []                                # (event, ready_time) awaiting a window
        self.slots = [simpy.Resource(env, 1) for _ in range(SLOTS_PER_CHIP)]
        self.stall_s = 0.0                                     # slot time lost to the governor
        self.receipt_waits: list[float] = []
        self.tokens = 0
        self.rng = rng

    def fw_do(self, cost_s: float):
        """Run ``cost_s`` of firmware; the caller's elapsed time includes the queue."""
        req = self.fw.request()
        yield req
        yield self.env.timeout(cost_s)
        self.fw_busy_s += cost_s
        self.fw.release(req)

    def window_loop(self, phase: float):
        yield self.env.timeout(phase % self.pol.window_s)      # the first window closes within one window of start
        while True:
            if self.pending:
                batch, self.pending = self.pending, []
                self.env.process(self._seal(batch))            # the next window opens on schedule
            yield self.env.timeout(self.pol.window_s)

    def _seal(self, batch):
        yield from self.fw_do(self.pol.merkle_s)
        req = self.engine.request()                            # the engine is private to this chip and serial
        yield req
        yield self.env.timeout(SIGN_S)
        self.engine_busy_s += SIGN_S
        self.engine.release(req)
        for ev, _ in batch:
            ev.succeed()

    def heartbeats(self, phase: float):
        yield self.env.timeout(phase)
        while True:
            yield self.env.timeout(HEARTBEAT_PERIOD_S)
            yield from self.fw_do(self.pol.heartbeat_s)

    def edition_change(self, at: float):
        """Staged image attested, every slot's port closed and reopened, outstanding tickets reissued."""
        yield self.env.timeout(at)
        yield from self.fw_do(COST_S["attest"])
        for slot in self.slots:
            self.env.process(self._reprogram(slot))

    def _reprogram(self, slot):
        yield from self.fw_do(COST_S["switch_program"])        # close
        req = slot.request()
        yield req
        t0 = self.env.now
        yield from self.fw_do(COST_S["switch_program"])        # reopen, with the slot held out of service
        yield from self.fw_do(COST_S["ticket"])                # revocation: reissue the slot's live ticket
        slot.release(req)
        self.stall_s += self.env.now - t0

    def _receipt_release(self, ev, done_gpu, arrived, lat, added):
        """The plan-of-record release. The slot is already free, so the receipt wait is recorded
        here, off the slot's path: latency on the response, not throughput on the GPU."""
        yield ev
        released = self.env.now
        self.receipt_waits.append(released - done_gpu)
        lat.append(released - arrived)
        added.append(released - done_gpu)

    def slot_loop(self, s: int, horizon: float, mode: str, lat: list, added: list, seed: int):
        env, slot, pol = self.env, self.slots[s], self.pol
        sizes = random.Random(seed)                            # tokens and arrivals: identical with and without governor
        acts = random.Random(seed ^ 0x5EED)                    # whether a request makes mailbox calls
        mean_service = MEAN_TOKENS * GPU_SECONDS_PER_TOKEN
        t_next = 0.0
        while env.now < horizon:
            tokens = max(10, int(sizes.expovariate(1.0 / MEAN_TOKENS)))
            gap = sizes.expovariate(OPEN_LOAD / mean_service)
            n_act = self._actions(acts)
            if mode == "open":
                t_next += gap
                if t_next > env.now:
                    yield env.timeout(t_next - env.now)
            arrived = env.now if mode == "open" else None
            req = slot.request()
            yield req
            started = env.now
            service = tokens * GPU_SECONDS_PER_TOKEN
            if arrived is None:
                arrived = started
            if self.governed and n_act:
                part = service / (n_act + 1)
                for _ in range(n_act):                         # a mailbox call and a ticket mint block the issuing slot
                    yield env.timeout(part)
                    t0 = env.now
                    yield from self.fw_do(COST_S["mailbox"] + COST_S["ticket"])
                    self.stall_s += env.now - t0
                yield env.timeout(part)
            else:
                yield env.timeout(service)
            done_gpu = env.now
            self.tokens += tokens
            if not self.governed:
                slot.release(req)
                lat.append(done_gpu - arrived)
                added.append(0.0)
                continue
            t0 = env.now
            yield from self.fw_do(pol.log_write_s)             # the record is appended to the log
            ready = env.now
            self.stall_s += ready - t0                         # the log write is on the slot's path
            if pol.gate:
                ev = env.event()
                self.pending.append((ev, ready))               # the window's seal will succeed it
                slot.release(req)                              # the slot is free for the next request now
                if pol.hold_slot:
                    # worst case: the slot idles for the receipt, so that wait IS throughput loss
                    yield ev
                    released = self.env.now
                    self.stall_s += released - ready
                    lat.append(released - arrived)
                    added.append(released - done_gpu)
                    self.receipt_waits.append(released - done_gpu)
                else:
                    # plan of record: the slot is freed; the receipt is waited on off the slot's
                    # path, so it adds latency to the response but not throughput to the GPU
                    self.env.process(self._receipt_release(ev, done_gpu, arrived, lat, added))
            else:
                # no gate: the response is released at the log write; the receipt trails it
                slot.release(req)
                lat.append(ready - arrived)
                added.append(0.0)
                self.pending.append((env.event(), ready))

    def _actions(self, rng: random.Random) -> int:
        a = self.pol.actions_per_response
        n = int(a)
        return n + (1 if rng.random() < a - n else 0)


def run_one(pol: Policy, mode: str, governed: bool, horizon: float, seed: int = 1) -> dict:
    env = simpy.Environment()
    lat: list[float] = []
    added: list[float] = []
    chips = [Chip(env, i, pol, governed, random.Random(seed + i)) for i in range(pol.governors)]
    for c in chips:
        if governed:
            env.process(c.window_loop(c.rng.random() * pol.window_s))
            env.process(c.heartbeats(c.rng.random() * HEARTBEAT_PERIOD_S))
            if pol.edition_change:
                env.process(c.edition_change(horizon / 2))
        for s in range(SLOTS_PER_CHIP):
            env.process(c.slot_loop(s, horizon, mode, lat, added, seed * 100003 + c.idx * 64 + s))
    env.run(until=horizon)
    slot_s = pol.governors * SLOTS_PER_CHIP * horizon
    waits = sorted(w for c in chips for w in c.receipt_waits)
    return {
        "lat": lat, "added": added, "waits": waits,
        "tokens": sum(c.tokens for c in chips),
        "stall_pct": 100.0 * sum(c.stall_s for c in chips) / slot_s,
        "engine_util_pct": 100.0 * max(c.engine_busy_s for c in chips) / horizon,
        "fw_util_pct": 100.0 * max(c.fw_busy_s for c in chips) / horizon,
        "requests": len(lat),
    }


def pct(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def measure(pol: Policy, horizon: float = 30.0, open_horizon: float = 30.0, seed: int = 1) -> dict:
    """Throughput lost and tail latency added for one policy.

    Throughput lost is *measured*: the tokens the governed saturated run produces below the no-
    governor baseline, common random numbers. The bookkeeping stall share is reported beside it as
    a cross-check; the two agree because the only stalls are the ones that reduce the token count.
    """
    sat_g = run_one(pol, "saturated", True, horizon, seed)
    sat_b = run_one(pol, "saturated", False, horizon, seed)
    open_g = run_one(pol, "open", True, open_horizon, seed)
    open_b = run_one(pol, "open", False, open_horizon, seed)
    base_tokens = sat_b["tokens"]
    gov_tokens = sat_g["tokens"]
    throughput = 100.0 * (base_tokens - gov_tokens) / base_tokens if base_tokens else 0.0
    return {
        "policy": pol,
        "overhead_pct": throughput,
        "stall_pct": sat_g["stall_pct"],
        "tokens_governed": gov_tokens,
        "tokens_baseline": base_tokens,
        "engine_util_pct": sat_g["engine_util_pct"],
        "fw_util_pct": sat_g["fw_util_pct"],
        "p99_latency_s": pct(open_g["lat"], 0.99),
        "p99_latency_base_s": pct(open_b["lat"], 0.99),
        "p99_added_s": pct(open_g["lat"], 0.99) - pct(open_b["lat"], 0.99),
        "p99_receipt_wait_s": pct(open_g["waits"], 0.99),
        "max_receipt_wait_s": max(open_g["waits"], default=0.0),
        "requests": open_g["requests"],
    }


def crossing(points: list[tuple[float, float]], level: float = ONE_PERCENT):
    """First x where y reaches ``level``, linearly interpolated; None if it never does."""
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if y0 < level <= y1:
            return x0 + (level - y0) * (x1 - x0) / (y1 - y0)
    return points[0][0] if points and points[0][1] >= level else None


ACTION_AXIS = (0.05, 5, 20, 40, 80, 160)           # mailbox calls per response
WINDOW_AXIS = (0.020, 0.030, 0.050, 0.100, 0.200)  # seconds, serviceable above the 17 ms signature


def sweep_actions(base: Policy = PLAN_OF_RECORD, horizon: float = 10.0) -> list[tuple[float, float]]:
    return [(a, run_one(replace(base, actions_per_response=a), "saturated", True, horizon)["stall_pct"])
            for a in ACTION_AXIS]


def sweep_window_held(horizon: float = 10.0) -> list[tuple[float, float]]:
    """The worst case: the slot is held until the receipt. Overhead against the window."""
    return [(w, run_one(Policy(window_s=w, hold_slot=True), "saturated", True, horizon)["stall_pct"])
            for w in WINDOW_AXIS]


def sensitivity(base: Policy = PLAN_OF_RECORD, horizon: float = 10.0) -> list[tuple[str, float]]:
    """The three assumptions named in docs/12, each ten times its nominal value. None moves the
    plan of record off the sub-one-percent figure."""
    return [
        ("log write 10x", run_one(replace(base, log_write_s=10 * base.log_write_s), "saturated", True, horizon)["stall_pct"]),
        ("merkle root 10x", run_one(replace(base, merkle_s=10 * base.merkle_s), "saturated", True, horizon)["stall_pct"]),
        ("heartbeat 10x", run_one(replace(base, heartbeat_s=10 * base.heartbeat_s), "saturated", True, horizon)["stall_pct"]),
    ]


def main() -> None:
    p = PLAN_OF_RECORD
    r = measure(p)
    print(f"{p.governors} governors x {SLOTS_PER_CHIP} slots = {p.governors*SLOTS_PER_CHIP} GPUs; "
          f"signature {SIGN_S*1e3:.1f} ms; edition change with revocation at mid-run")
    print(f"plan of record ({p.label()}), serviceable={p.serviceable}")
    print(f"  throughput lost (measured)      {r['overhead_pct']:.4f} %  "
          f"(governed {r['tokens_governed']:,} vs baseline {r['tokens_baseline']:,} tokens)")
    print(f"  cross-check: stall share        {r['stall_pct']:.4f} %")
    print(f"  p99 added latency               {r['p99_added_s']*1e3:.1f} ms  "
          f"(p99 {r['p99_latency_s']*1e3:.0f} ms vs {r['p99_latency_base_s']*1e3:.0f} ms without the governor)")
    print(f"  p99 receipt wait                {r['p99_receipt_wait_s']*1e3:.1f} ms "
          f"(idle-core bound {(p.window_s+SIGN_S)*1e3:.0f} ms; max seen {r['max_receipt_wait_s']*1e3:.1f} ms)")
    print(f"  busiest engine / firmware core  {r['engine_util_pct']:.1f} % / {r['fw_util_pct']:.3f} %")
    ed = edition_firmware_s()
    print(f"  one edition change              {ed*1e3:.0f} ms of firmware per chip; "
          f"one a second is {ed*100:.1f} % of the core")
    pts = sweep_actions()
    print("policy sweep 1, mailbox calls per response (plan of record otherwise, 10 s):")
    for a, o in pts:
        print(f"  actions/response={a:>6g}  overhead={o:.4f} %")
    c = crossing(pts)
    if c is not None:
        mult = round(c / p.actions_per_response / 100) * 100
        print(f"  crosses 1 percent at about {c:.0f} mailbox calls per response (about {mult:,}x the reference)")
    else:
        print("  never crosses 1 percent on this axis")
    held = sweep_window_held()
    print("policy sweep 2, the slot held until the receipt, by batch window (10 s):")
    for w, o in held:
        print(f"  window={w*1e3:>4.0f} ms  serviceable={replace(p, window_s=w).serviceable!s:5}  overhead={o:.2f} %")
    ok = [w for w, o in held if o < ONE_PERCENT and replace(p, window_s=w).serviceable]
    print("  slot-held release stays under 1 percent at: " + (", ".join(f"{w*1e3:g} ms" for w in ok) if ok
          else "no serviceable window (above 1 percent at every serviceable policy)"))
    sens = sensitivity()
    print("sensitivity, each named assumption 10x (plan of record otherwise, 10 s):")
    for name, o in sens:
        print(f"  {name:16s}  overhead={o:.4f} %")
    moved = [n for n, o in sens if o >= ONE_PERCENT]
    print("  none moves the plan of record off the sub-one-percent figure"
          if not moved else f"  {', '.join(moved)} move it off the figure")


if __name__ == "__main__":
    main()
