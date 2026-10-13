# Governor Program Console

A one-page live console for the Safety Governor program: which agents are running on what,
the work items and their status, and a timestamped event log. It is published on claude.ai
as an artifact (private to the project owner) and reads its rows from the artifact's own
store, so the page itself holds no data and never needs republishing when the status changes.

## What is on the page

| Section | Store path | Fields |
|---|---|---|
| Status strip | `status/now` | `phase` (one sentence), `updated` (ISO time) |
| Agents | `agents/<id>` | `name`, `task`, `status` (running, waiting, done, failed, idle), `started`, `finished`, `summary`, `tokens` |
| Work items | `work/<id>` | `title`, `detail`, `status` (pending, in_progress, done, blocked), `order` |
| Event log | `log/events` | `entries`: a list of `{t, text, kind}` (kind: agent, done, warn, or empty), newest first, capped at 200 |

The page subscribes to those four paths once and re-renders on every change; it marks the
status as stale when nothing has been written for twenty minutes. Times are shown in the
viewer's local time zone.

## How it is updated

The session that runs the program writes the rows (through the artifact data tool) when an
agent is spawned or finishes, when a work item changes state, and at least every ten minutes
with a status line. Nothing on the page is typed by a viewer; it is read-only by design.

## Republishing

The HTML here is the source. To change the page, edit it and publish it again to the same
artifact; the store and its rows survive a republish. The page declares the `db` capability
and nothing else. It needs no library and loads two Google Fonts (IBM Plex Sans and Mono)
with system fallbacks.
