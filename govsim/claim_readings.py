# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The three readings of docs/29 section 3.4, computed from a saved Experiment B record without altering it.

    python3 -m govsim.claim_readings RECORD.json                 # print the three readings as JSON
    python3 -m govsim.claim_readings RECORD.json --out READINGS.json   # and write them beside the record

A record of the amendment 3 sweep can be read three ways, and docs/29 amendment 2 says all three are reported beside
the record, with only the approved rule's reading called the result:

  original_text        section 3.4 as approved on 28 October 2026: a harm kind FAILS on any run over its cap, or where
                       L grows with K. The text gives no tolerance, so this reader takes "grows with K" literally: for
                       any strategy, the largest L over seeds at the largest K that finished is above the largest L at
                       the smallest K. The growth is reported as the text asks ("each additional attacker adds X").
  pre_amendment_code   the harness as it ran the amendment 1 and amendment 3 sweeps: a kind FAILS only on a run over
                       its cap. Its grows_with_k clause could only fire when the over-cap clause had already failed
                       the run, so it never decided anything (review panel condition B1).
  approved_rule        amendment 2 (approved 2026-10-30T04:00 UTC): over cap FAILS; L above the one-requester baseline
                       for that strategy, K and seed FAILS for cooperation; otherwise PASS, INCONCLUSIVE when the
                       baselines did not finish, INCOMPLETE on a crashed run. Computed by the harness's own
                       verdict_for_kind, so the reader and the harness cannot disagree about the result.

Under every reading a crashed run makes an otherwise passing kind INCOMPLETE, as the pre-amendment code did. A record
with no baselines (one written before this amendment, or one whose --baselines run has not happened yet) is
INCONCLUSIVE under the approved rule for every kind, never PASS.

The reader opens the record read-only and writes nothing unless --out names a file, which must not be the record.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .claim_attack_sim import HARM_KINDS, PLAN, approved_verdicts, rise_sentence


def _kinds(record):
    return [k for k in HARM_KINDS if any(r["kind"] == k for r in record.get("runs", []))] or list(HARM_KINDS)


def _runs_of(record, kind):
    return [r for r in record.get("runs", []) if r["kind"] == kind and not r.get("baseline")]


def _overall(verdicts, kinds):
    """FAIL if any kind fails; otherwise INCOMPLETE, then INCONCLUSIVE, if any kind is; otherwise PASS."""
    heads = {k: verdicts[k].split()[0].rstrip(":.") for k in kinds}
    for word in ("FAIL", "INCOMPLETE", "INCONCLUSIVE"):
        if word in heads.values():
            return f"{word} ({', '.join(k for k in kinds if heads[k] == word)})"
    return "PASS"


def reading_original_text(record):
    """Section 3.4 as written: over cap, or L grows with K, is FAIL. The growth is reported with its strategy."""
    out = {"rule": "docs/29 section 3.4 as approved 28 October 2026: FAIL on any run over the cap or where L grows with K "
                   "(read literally: the largest L at the largest K finished is above the largest L at the smallest K)"}
    kinds = _kinds(record)
    for kind in kinds:
        mine = _runs_of(record, kind)
        good = [r for r in mine if not r.get("error")]
        crashed = [r for r in mine if r.get("error")]
        fails = []
        for strategy in PLAN.get(kind, ()):
            rs = [r for r in good if r["strategy"] == strategy]
            for r in rs:
                if r["over_cap"]:
                    fails.append(f"over cap: {strategy} K = {r['K']:,} seed {r['seed']}")
            ks = sorted({r["K"] for r in rs})
            if len(ks) >= 2:
                lo = max(r["harm"] for r in rs if r["K"] == ks[0])
                hi = max(r["harm"] for r in rs if r["K"] == ks[-1])
                if hi > lo:
                    per_attacker = (hi - lo) / (ks[-1] - ks[0])
                    fails.append(f"L grows with K: {strategy} {lo:,.2f} at K = {ks[0]:,} to {hi:,.2f} at K = {ks[-1]:,} "
                                 f"(each additional attacker adds {per_attacker:,.4f} on average)")
        if fails:
            out[kind] = "FAIL: " + "; ".join(fails)
        elif crashed:
            out[kind] = f"INCOMPLETE: a run crashed ({len(crashed)} crashed)"
        elif not good:
            out[kind] = "INCONCLUSIVE: no run finished"
        else:
            out[kind] = "PASS"
    out["overall"] = _overall(out, kinds)
    return out


def reading_pre_amendment_code(record):
    """The harness as it ran the amendment 1 and 3 sweeps: FAIL only on a run over its cap; INCOMPLETE on a crash."""
    out = {"rule": "the pre-amendment harness: FAIL on any run over the cap, and nothing else (its growth clause never fired)"}
    kinds = _kinds(record)
    for kind in kinds:
        mine = _runs_of(record, kind)
        good = [r for r in mine if not r.get("error")]
        crashed = [r for r in mine if r.get("error")]
        over = [f"{r['strategy']} K = {r['K']:,} seed {r['seed']}" for r in good if r["over_cap"]]
        if over:
            out[kind] = "FAIL: over cap: " + "; ".join(over)
        elif crashed:
            out[kind] = f"INCOMPLETE (a run crashed; see its error; {len(crashed)} crashed)"
        elif not good:
            out[kind] = "INCONCLUSIVE: no run finished"
        else:
            out[kind] = "PASS"
    out["overall"] = _overall(out, kinds)
    return out


def reading_approved_rule(record):
    """Amendment 2, by the harness's own verdict function, with the per-strategy report."""
    verdicts, report = approved_verdicts(record, _kinds(record))
    return {**verdicts, "report": report}


def side_by_side(record):
    """For every strategy line: L at the two largest K on seed 1, side by side, with the change in units of the cap
    (review panel checklist item M6). The largest K column is labelled with its seed count."""
    rows = []
    for kind in _kinds(record):
        for strategy in PLAN.get(kind, ()):
            rs = [r for r in _runs_of(record, kind) if r["strategy"] == strategy and not r.get("error")]
            on_seed_1 = sorted((r["K"], r["harm"]) for r in rs if r["seed"] == 1)
            if len(on_seed_1) < 2:
                continue
            (k_lo, lo), (k_hi, hi) = on_seed_1[-2], on_seed_1[-1]
            cap = max(r["cap"] for r in rs if r["K"] == k_hi)
            rows.append({"kind": kind, "strategy": strategy, "K_lower": k_lo, "L_lower_seed_1": lo, "K_upper": k_hi,
                         "L_upper_seed_1": hi, "seeds_at_K_upper": len({r["seed"] for r in rs if r["K"] == k_hi}),
                         "cap": cap, "change_in_units_of_cap": ((hi - lo) / cap) if cap else None,
                         "sentence": rise_sentence(strategy, rs)})
    return rows


def readings(record):
    """All three readings and the side-by-side table, from one record. Does not alter the record."""
    return {"record": {"started": record.get("started"), "protocol_sha256": record.get("protocol_sha256"),
                       "runs": len(record.get("runs", [])), "baselines": len(record.get("baseline", [])),
                       "baselines_added_after_sweep": sum(1 for b in record.get("baseline", []) if b.get("added_after_sweep")),
                       "finished": record.get("finished"), "controls": {k: v for k, v in record.get("verdicts", {}).items() if k.startswith("control:")}},
            "result": "the approved_rule reading is the result; the other two are shown beside it (docs/29 amendment 2)",
            "original_text": reading_original_text(record),
            "pre_amendment_code": reading_pre_amendment_code(record),
            "approved_rule": reading_approved_rule(record),
            "two_largest_k_seed_1": side_by_side(record)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("record", metavar="RECORD.json")
    ap.add_argument("--out", metavar="READINGS.json", default=None, help="also write the readings to this file (not the record)")
    a = ap.parse_args(argv)
    if a.out and os.path.abspath(a.out) == os.path.abspath(a.record):
        ap.error("--out must not be the record itself; the record is never altered")
    with open(a.record) as fh:
        record = json.load(fh)
    out = readings(record)
    text = json.dumps(out, indent=1)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
