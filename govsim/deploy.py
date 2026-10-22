"""N1: the whole-deployment overhead (docs/12). ``bench.py`` prices one chip's operations; this
module runs 72 governors with eight GPU slots each as a discrete-event simulation and
measures what the one-percent claim needs: throughput lost and tail latency added, with the
queues the per-chip arithmetic leaves out.

What is simulated, per governor chip: one firmware core (a FIFO queue) that serves mailbox
commands, ticket mints, log appends, the per-window Merkle root, heartbeats and the port
programming of an edition change; one signing engine (17 ms per ECDSA P-384 signature, one
signature per batch window over the records that finished in it); eight GPU slots, each
serving requests one at a time. The figures are ``bench.py``'s and docs/04 §9's; the log-write
and heartbeat fan-out costs are assumptions named in docs/12.

Two runs per policy, both with common random numbers against a no-governor baseline:

* saturated: every slot always has a request waiting, as in bench.py's "the GPU is busy
  throughout". Throughput lost is the share of slot time spent stalled on the governor.
* open: Poisson arrivals at 70 percent of slot capacity. Tail latency added is the p99 of
  the request latency minus the baseline's, and the p99 wait for the provenance receipt.

The model is not a measurement. Phase 2 on real hardware replaces it.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace

try:
    import simpy
except ImportError:                                  # host without simpy: same calls, small stand-in
    from . import _minisim as simpy

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

    @property
    def serviceable(self) -> bool:
        """docs/04 §9: the window is longer than the signature and the engine stays under 50 percent."""
        return self.window_s > SIGN_S and SIGN_S / self.window_s < 0.5

    def label(self) -> str:
        return (f"window={self.window_s*1e3:g} ms gate={'on' if self.gate else 'off'} "
                f"hold_slot={'yes' if self.hold_slot else 'no'} actions/response={self.actions_per_response:g}")


PLAN_OF_RECORD = Policy()


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
                self.env.process(self._seal(batch))             # the next window opens on schedule
            yield self.env.timeout(self.pol.window_s)

    def _seal(self, batch):
        yield from self.fw_do(MERKLE_S)
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
            yield from self.fw_do(HEARTBEAT_FANOUT_S)

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
            released_at = done_gpu
            if self.governed:
                t0 = env.now
                yield from self.fw_do(LOG_WRITE_S)             # the record is appended to the log
                ready = env.now
                if pol.gate or pol.hold_slot:
                    ev = env.event()
                    self.pending.append((ev, ready))
                    if pol.hold_slot:
                        yield ev
                        self.stall_s += env.now - t0
                    else:
                        self.stall_s += ready - t0
                    slot.release(req)
                    if not pol.hold_slot:
                        yield ev
                    released_at = env.now
                    self.receipt_waits.append(env.now - done_gpu)
                else:
                    self.stall_s += ready - t0
                    self.pending.append((env.event(), ready))
                    slot.release(req)
                    released_at = ready
            else:
                slot.release(req)
            lat.append(released_at - arrived)
            added.append(released_at - done_gpu)

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
    """Throughput lost and tail latency added for one policy."""
    sat = run_one(pol, "saturated", True, horizon, seed)
    open_g = run_one(pol, "open", True, open_horizon, seed)
    open_b = run_one(pol, "open", False, open_horizon, seed)
    return {
        "policy": pol,
        "overhead_pct": sat["stall_pct"],
        "tokens_governed": sat["tokens"],
        "engine_util_pct": sat["engine_util_pct"],
        "fw_util_pct": sat["fw_util_pct"],
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


def main() -> None:
    p = PLAN_OF_RECORD
    r = measure(p)
    print(f"{p.governors} governors x {SLOTS_PER_CHIP} slots = {p.governors*SLOTS_PER_CHIP} GPUs; "
          f"signature {SIGN_S*1e3:.1f} ms; edition change with revocation at mid-run")
    print(f"plan of record ({p.label()}), serviceable={p.serviceable}")
    print(f"  overhead (throughput lost)      {r['overhead_pct']:.4f} %")
    print(f"  p99 added latency               {r['p99_added_s']*1e3:.1f} ms  "
          f"(p99 {r['p99_latency_s']*1e3:.0f} ms vs {r['p99_latency_base_s']*1e3:.0f} ms without the governor)")
    print(f"  p99 receipt wait                {r['p99_receipt_wait_s']*1e3:.1f} ms (bound {(p.window_s+SIGN_S)*1e3:.0f} ms; "
          f"max seen {r['max_receipt_wait_s']*1e3:.1f} ms)")
    print(f"  busiest engine / firmware core  {r['engine_util_pct']:.1f} % / {r['fw_util_pct']:.3f} %")
    pts = sweep_actions()
    print("policy sweep 1, mailbox calls per response (plan of record otherwise):")
    for a, o in pts:
        print(f"  actions/response={a:>6g}  overhead={o:.4f} %")
    c = crossing(pts)
    print(f"  crosses 1 percent at about {c:.0f} mailbox calls per response" if c is not None
          else "  never crosses 1 percent on this axis")
    held = sweep_window_held()
    print("policy sweep 2, the slot held until the receipt, by batch window:")
    for w, o in held:
        print(f"  window={w*1e3:>4.0f} ms  serviceable={replace(p, window_s=w).serviceable!s:5}  overhead={o:.2f} %")
    ok = [w for w, o in held if o < ONE_PERCENT and replace(p, window_s=w).serviceable]
    print("  slot-held release stays under 1 percent at: " + (", ".join(f"{w*1e3:g} ms" for w in ok) if ok
          else "no serviceable window (above 1 percent at every serviceable policy)"))


if __name__ == "__main__":
    main()
