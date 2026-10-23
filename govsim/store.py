# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Durable state.

The governor's NVM is modelled as a dictionary that survives ``Governor.restart()`` while
everything else in the object is rebuilt. ``Store.save()`` is the "written before the call
returns" point; a power loss between a mutation and ``save()`` loses that mutation, which the
tests exploit to check that every durable step saves before it returns.
"""
from __future__ import annotations

import copy
import json
import os
import pickle
import tempfile
from typing import Any


def _snapshot(data: dict[str, Any]) -> bytes:
    """A serialized image of the working copy. pickle is an order of magnitude faster than
    copy.deepcopy for the nested dicts and lists the governor keeps, and the model saves
    after every durable step, so this is the hot path of the whole simulation."""
    return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)


class PowerLoss(Exception):
    """Fault injection: the power failed before this save completed."""


class Store:
    """Authenticated NVM. In memory by default; optionally backed by a JSON file."""

    def __init__(self, path: str | None = None):
        self.path = path
        self.data: dict[str, Any] = {}
        self.writes = 0
        self._fail_in: int | None = None
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self.data = json.load(fh)
        self._nvm: bytes = _snapshot(self.data)

    def fail_after(self, n: int | None) -> None:
        """Make the n-th save from now fail with ``PowerLoss`` (None disarms)."""
        self._fail_in = n

    def save(self) -> None:
        """Commit the working copy to NVM atomically."""
        if self._fail_in is not None:
            self._fail_in -= 1
            if self._fail_in <= 0:
                self._fail_in = None
                raise PowerLoss()
        self._nvm = _snapshot(self.data)
        self.writes += 1
        if self.path:
            d = os.path.dirname(self.path) or "."
            fd, tmp = tempfile.mkstemp(dir=d, prefix=".store-", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)

    def power_loss(self) -> None:
        """Drop everything not yet saved."""
        self.data = pickle.loads(self._nvm)

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self.data:
            self.data[key] = copy.deepcopy(default) if default is not None else None
        return self.data[key]
