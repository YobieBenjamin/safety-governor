"""A small stand-in for the parts of simpy that ``deploy.py`` uses (Environment, process, timeout,
event, Resource), so the model also runs on a host where simpy is not installed. ``deploy.py``
imports the real simpy first and falls back to this only when that import fails. Same semantics
for the calls used: FIFO resources, generators that yield events, events that carry a value."""
from __future__ import annotations

import heapq
import itertools


class Event:
    def __init__(self, env):
        self.env, self.triggered, self.value, self._cbs = env, False, None, []

    def succeed(self, value=None):
        if not self.triggered:
            self.triggered, self.value = True, value
            self.env._schedule(0.0, self)
        return self


class Environment:
    def __init__(self):
        self.now, self._q, self._n = 0.0, [], itertools.count()

    def _schedule(self, delay, ev):
        heapq.heappush(self._q, (self.now + delay, next(self._n), ev))

    def event(self):
        return Event(self)

    def timeout(self, delay):
        ev = Event(self)
        ev.triggered = True
        self._schedule(delay, ev)
        return ev

    def process(self, gen):
        done = Event(self)

        def step(value=None):
            try:
                ev = gen.send(value)
            except StopIteration as stop:
                done.succeed(getattr(stop, "value", None))
                return
            if ev.triggered and ev._cbs is None:      # already fired and dispatched
                step(ev.value)
            else:
                ev._cbs.append(lambda e: step(e.value))

        start = self.event()
        start._cbs.append(lambda e: step(None))
        start.succeed()
        return done

    def run(self, until):
        while self._q and self._q[0][0] <= until:
            self.now, _, ev = heapq.heappop(self._q)
            cbs, ev._cbs = ev._cbs, None
            for cb in cbs:
                cb(ev)
        self.now = until


class _Request(Event):
    pass


class Resource:
    def __init__(self, env, capacity=1):
        self.env, self.capacity, self.users, self.waiting = env, capacity, 0, []

    def request(self):
        req = _Request(self.env)
        if self.users < self.capacity:
            self.users += 1
            req.succeed()
        else:
            self.waiting.append(req)
        return req

    def release(self, req):
        if self.waiting:
            self.waiting.pop(0).succeed()
        else:
            self.users -= 1
