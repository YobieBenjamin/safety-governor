#!/usr/bin/env python3
"""Helpers for tools/agents/run_wave.sh: the bits that are easier in Python than in bash 3.2.

    wave_lib.py issues SPEC WAVE REPO [ID]   the wave's issues for one repository, as TSV: id, title, accept command, backend
    wave_lib.py brief SPEC ID                 the issue body
    wave_lib.py summarize LOG.jsonl           one JSON object: what the agent run did (turns, cost, limits, errors)
    wave_lib.py status LOGDIR                 STATUS.md: one line per agent, from the logs, for the ticker
    wave_lib.py report LOGDIR                 REPORT.md: the wave's table
    wave_lib.py version_ok HAVE MIN           exit 0 if version HAVE >= MIN
    wave_lib.py sleep_until RESETS_AT         seconds from now until the unix time (plus a margin), at least 60
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time

LIMIT_RE = re.compile(r"(usage limit|rate limit|rate_limit|hit your limit|limit reached|too many requests|\b429\b|resets at)", re.I)


def load_spec(path: str) -> dict:
    return json.load(open(path, encoding="utf-8"))


def issues(spec: str, wave: str, repo: str, only: str = "") -> None:
    for i in load_spec(spec)["issues"]:
        if str(i.get("wave")) != wave or i["repo"] != repo:
            continue
        if only and i["id"] != only:
            continue
        print(i["id"], i["title"], i.get("accept", ""), i.get("backend", "cloud+local"), sep="\t")


def brief(spec: str, ident: str) -> None:
    for i in load_spec(spec)["issues"]:
        if i["id"] == ident:
            sys.stdout.write(i["body"].rstrip() + "\n")
            return
    sys.exit(f"no issue {ident} in {spec}")


def read_events(path: str) -> list[dict]:
    rows = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except FileNotFoundError:
        pass
    return rows


def summarize_events(rows: list[dict]) -> dict:
    out = {"turns": 0, "cost_usd": 0.0, "duration_s": 0, "is_error": None, "subtype": None, "result": "",
           "denials": 0, "limit_hit": False, "five_hour": None, "seven_day": None, "resets_at": None,
           "session_id": None, "finished": False}
    results = [r for r in rows if r.get("type") == "result"]
    assistant_turns = sum(1 for r in rows if r.get("type") == "assistant")
    out["turns"] = assistant_turns
    for r in rows:
        if r.get("session_id") and not out["session_id"]:
            out["session_id"] = r["session_id"]
        if r.get("type") == "rate_limit_event":
            info = r.get("rate_limit_info") or {}
            win = info.get("unifiedWindows") or {}
            fh, sd = win.get("five_hour") or {}, win.get("seven_day") or {}
            out["five_hour"] = fh.get("utilization")
            out["seven_day"] = sd.get("utilization")
            out["resets_at"] = fh.get("resetsAt") or info.get("resetsAt")
            if info.get("status") not in (None, "allowed"):
                out["limit_hit"] = True
        if r.get("type") == "system" and r.get("subtype") == "api_retry" and r.get("error") == "rate_limit":
            out["limit_hit"] = True
        if r.get("type") == "system" and r.get("subtype") == "permission_denied":
            out["denials"] += 1
    if results:
        res = results[-1]   # the last run decides the outcome; turns, cost and time add up over all runs
        out["finished"] = True
        out["turns"] = sum(int(r.get("num_turns") or 0) for r in results) or assistant_turns
        out["cost_usd"] = round(sum(float(r.get("total_cost_usd") or 0.0) for r in results), 4)
        out["duration_s"] = int(sum(float(r.get("duration_ms") or 0) for r in results) / 1000)
        out["is_error"] = bool(res.get("is_error"))
        out["subtype"] = res.get("subtype")
        text = res.get("result")
        if not isinstance(text, str):
            text = json.dumps(text) if text is not None else ""
        out["result"] = text.strip()[:400]
        out["denials"] = max(out["denials"], len(res.get("permission_denials") or []))
        if res.get("is_error") and LIMIT_RE.search(text or ""):
            out["limit_hit"] = True
        if (res.get("subtype") or "").startswith("error") and LIMIT_RE.search(json.dumps(res)):
            out["limit_hit"] = True
    return out


def summarize(path: str) -> None:
    print(json.dumps(summarize_events(read_events(path))))


def fmt_pct(x) -> str:
    return "?" if x is None else f"{int(round(x * 100))}%"


def agents_in(logdir: str) -> list[str]:
    ids = []
    for name in sorted(os.listdir(logdir)):
        if name.endswith(".jsonl") and not name.startswith("."):
            ids.append(name[:-6])
    return ids


def state_of(logdir: str, ident: str) -> dict:
    st = {"id": ident, "phase": "unknown"}
    try:
        st.update(json.load(open(os.path.join(logdir, ident + ".state.json"), encoding="utf-8")))
    except (FileNotFoundError, ValueError):
        pass
    runs = sorted(n for n in os.listdir(logdir) if n.startswith(ident + ".") and n.endswith(".jsonl"))
    rows = []
    for n in runs:
        rows.extend(read_events(os.path.join(logdir, n)))
    st.update({k: v for k, v in summarize_events(rows).items() if k != "session_id"})
    st["attempts"] = len(runs)
    return st


def status(logdir: str) -> None:
    ids = sorted({n.split(".")[0] for n in os.listdir(logdir) if n.endswith(".state.json")})
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# Wave status at {now}", "", "| issue | phase | attempts | turns | est. cost | 5h window | 7d window | last words |", "|---|---|---|---|---|---|---|---|"]
    latest_fh = latest_sd = None
    for ident in ids:
        st = state_of(logdir, ident)
        last = (st.get("result") or "").replace("\n", " ")[:80]
        lines.append(f"| {ident} | {st.get('phase')} | {st.get('attempts')} | {st.get('turns')} | ${st.get('cost_usd', 0):.2f} | {fmt_pct(st.get('five_hour'))} | {fmt_pct(st.get('seven_day'))} | {last} |")
        if st.get("five_hour") is not None:
            latest_fh, latest_sd = st["five_hour"], st["seven_day"]
    lines.append("")
    if latest_fh is not None:
        lines.append(f"Subscription windows as last reported by an agent: five-hour {fmt_pct(latest_fh)}, seven-day {fmt_pct(latest_sd)}.")
    print("\n".join(lines))


def report(logdir: str) -> None:
    ids = sorted({n.split(".")[0] for n in os.listdir(logdir) if n.endswith(".state.json")})
    lines = ["# Wave report", "", f"Generated {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} from `{logdir}`.", "",
             "| issue | backend | outcome | acceptance | pull request | turns | est. cost | wall time | attempts |", "|---|---|---|---|---|---|---|---|---|"]
    total = 0.0
    for ident in ids:
        st = state_of(logdir, ident)
        total += float(st.get("cost_usd") or 0)
        mins = int(st.get("wall_s") or st.get("duration_s") or 0) // 60
        lines.append(f"| {ident} | {st.get('backend', 'cloud')} | {st.get('phase')} | {st.get('acceptance', 'not run')} | {st.get('pr', 'none')} | {st.get('turns')} | ${st.get('cost_usd', 0):.2f} | {mins} min | {st.get('attempts')} |")
    lines += ["", f"Estimated API-equivalent spend for the wave: ${total:.2f} (Claude Code's client-side estimate; a subscription is billed by its windows, not by this figure).", ""]
    for ident in ids:
        st = state_of(logdir, ident)
        if st.get("result"):
            lines += [f"## {ident}: the agent's last words", "", st["result"], ""]
    print("\n".join(lines))


def version_ok(have: str, need: str) -> None:
    def parse(v: str) -> tuple:
        m = re.search(r"(\d+)\.(\d+)\.(\d+)", v)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
    sys.exit(0 if parse(have) >= parse(need) else 1)


def sleep_until(resets_at: str) -> None:
    try:
        target = int(float(resets_at))
    except ValueError:
        print(3600)
        return
    print(max(60, target - int(time.time()) + 120))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"issues": issues, "brief": brief, "summarize": summarize, "status": status, "report": report,
     "version_ok": version_ok, "sleep_until": sleep_until}[cmd](*args)
