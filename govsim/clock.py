"""A manual clock. Time in the model is the governor's monotonic counter in seconds."""
from __future__ import annotations


class SimClock:
    def __init__(self, start: float = 1_000_000.0):
        self._t = float(start)

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> float:
        if seconds < 0:
            raise ValueError("the clock does not run backwards")
        self._t += float(seconds)
        return self._t

    def set(self, t: float) -> None:
        if t < self._t:
            raise ValueError("the clock does not run backwards")
        self._t = float(t)
