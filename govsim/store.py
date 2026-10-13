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
import tempfile
from typing import Any


class Store:
    """Authenticated NVM. In memory by default; optionally backed by a JSON file."""

    def __init__(self, path: str | None = None):
        self.path = path
        self._nvm: dict[str, Any] = {}
        self.data: dict[str, Any] = {}
        self.writes = 0
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self._nvm = json.load(fh)
        self.data = copy.deepcopy(self._nvm)

    def save(self) -> None:
        """Commit the working copy to NVM atomically."""
        self._nvm = copy.deepcopy(self.data)
        self.writes += 1
        if self.path:
            d = os.path.dirname(self.path) or "."
            fd, tmp = tempfile.mkstemp(dir=d, prefix=".store-", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._nvm, fh)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)

    def power_loss(self) -> None:
        """Drop everything not yet saved."""
        self.data = copy.deepcopy(self._nvm)

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self.data:
            self.data[key] = copy.deepcopy(default) if default is not None else None
        return self.data[key]
