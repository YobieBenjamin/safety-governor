# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The definitions engine: one defined meaning for every value a rule looks at.

Why this exists (GOAL.md, requirement 2, "Know what the words mean"): a persistent AI attacker does not need to beat
the cryptography if it can write the same forbidden thing in a way the rule does not recognise. Adversarial audit 3
(2026-10-26) did exactly that: a protected site written with an altitude ([lat, lon, alt]), as text ("lat,lon") or
as a mapping ({"lat": .., "lon": ..}) was not "in" the protected-site list, so the chip authorized a strike on it.

The rule engine therefore never compares raw request bytes against a list. It first reduces the value to its
canonical meaning with the definition the rule names (or, for a list check, the kind of thing the list holds):

* ``geo``: a place on Earth, reduced to (latitude, longitude) in degrees. Altitude is dropped, because a protected
  site is protected at every altitude. Accepted spellings: a list or tuple of 2 or 3 numbers, text "lat,lon[,alt]",
  and a mapping with lat/latitude and lon/lng/long/longitude keys. Out-of-range values are not places.
* ``text``: a name, account or identifier, reduced by Unicode NFKC, removal of invisible characters, case folding
  and collapsing of white space, so look-alike spellings of the same word are the same word.

The rule that keeps this fail-safe: a value that cannot be reduced to a defined meaning is refused, never guessed at.
Callers treat ``None`` from :func:`canonical` as "not understood" and deny.
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

from .crypto import finite_number

GEO = "geo"
TEXT = "text"
KINDS = (GEO, TEXT)

EARTH_RADIUS_M = 6_371_000.0
METRES_PER_DEGREE = math.pi * EARTH_RADIUS_M / 180.0           # about 111 km of great circle per degree

# Keys a mapping may use for each coordinate. Anything else in the mapping is ignored only if it is altitude-like;
# an unknown key makes the mapping "not understood" so that no extra field can smuggle a second meaning in.
_LAT_KEYS = ("lat", "latitude")
_LON_KEYS = ("lon", "lng", "long", "longitude")
_ALT_KEYS = ("alt", "altitude", "elevation", "height", "z")

# Characters that render as nothing (zero-width space, joiners, word joiner, byte-order mark, soft hyphen).
_INVISIBLE = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)


def _place(lat: Any, lon: Any) -> tuple[float, float] | None:
    """A (lat, lon) pair if both are finite numbers in range, else None. Longitude is wrapped into [-180, 180)."""
    if not (finite_number(lat) and finite_number(lon)):
        return None
    lat, lon = float(lat), float(lon)
    if not -90.0 <= lat <= 90.0 or not -540.0 <= lon <= 540.0:
        return None
    lon = ((lon + 180.0) % 360.0) - 180.0
    return lat, lon


def canonical_geo(v: Any) -> tuple[float, float] | None:
    """Reduce any accepted spelling of a place to (lat, lon) degrees, or None when it is not a place."""
    if isinstance(v, (list, tuple)):
        if len(v) in (2, 3) and all(finite_number(x) for x in v):
            return _place(v[0], v[1])
        return None
    if isinstance(v, str):
        parts = [p for p in re.split(r"[\s,;]+", unicodedata.normalize("NFKC", v).translate(_INVISIBLE).strip()) if p]
        if len(parts) not in (2, 3):
            return None
        try:
            nums = [float(p) for p in parts]
        except ValueError:
            return None
        return _place(nums[0], nums[1])
    if isinstance(v, dict):
        keys = {str(k).strip().casefold(): val for k, val in v.items()}
        if len(keys) != len(v):
            return None                                           # two keys that fold to the same name: ambiguous
        lat = [keys[k] for k in _LAT_KEYS if k in keys]
        lon = [keys[k] for k in _LON_KEYS if k in keys]
        known = set(_LAT_KEYS) | set(_LON_KEYS) | set(_ALT_KEYS)
        if len(lat) != 1 or len(lon) != 1 or any(k not in known for k in keys):
            return None
        return _place(lat[0], lon[0])
    return None


def canonical_text(v: Any) -> str | None:
    """Reduce a string to its canonical form, or None when it is not a string."""
    if not isinstance(v, str):
        return None
    s = unicodedata.normalize("NFKC", v).translate(_INVISIBLE).casefold()
    return " ".join(s.split())


def canonical(kind: str, v: Any) -> Any:
    """The canonical meaning of ``v`` under definition ``kind``; None means not understood (deny)."""
    if kind == GEO:
        return canonical_geo(v)
    if kind == TEXT:
        return canonical_text(v)
    return None                                                   # an undefined kind is not understood either


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in metres between two canonical places (haversine)."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def list_kind(entries: Any) -> str | None:
    """What kind of thing a signed list holds, judged from its entries: places, text, or (None) something else.
    A list that mixes kinds is judged as places if any entry is a place, so a protected site is never missed."""
    entries = list(entries or [])
    if any(canonical_geo(e) is not None and not isinstance(e, str) for e in entries):
        return GEO
    if entries and all(isinstance(e, str) for e in entries):
        return TEXT
    return None
