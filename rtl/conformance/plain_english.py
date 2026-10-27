# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The plain-English page. ``python -m rtl.conformance --write`` renders it to PLAIN-ENGLISH.md."""

TEXT = """# Conformance testing, in plain English

## What this is

The chip's specification (docs/04) and its verification plan (docs/07) are a list of rules: "the counter never
goes backwards", "a debug port is dead on a production part", "a halt opens the loop". The hardware design (the
Amaranth code in `rtl/governor_rtl/`) is supposed to obey every one of them. Conformance testing checks that it
does, one rule at a time, by running the design in a simulator and comparing what it does with what the rule says.

It is the normal way chip teams verify a design before tape-out. It is not attacking the chip. Nobody here tried to
break in. We read the rulebook and checked the building against it.

## The analogies

**The building inspector.** An inspector walks in with the code book. Room by room, rule by rule: is the outlet
within six feet of the sink grounded, is the stair rail the right height, does the fire door close on its own. Each
check is small and boring. The value is that every rule gets checked, and every failure is written down with the
room and the rule it broke. `REQUIREMENTS.md` is the code book with a checkbox per rule; `FINDINGS.md` is the list
of violations, each with the room number.

**Two clocks that should agree.** The project has two versions of the same governor: the chip design (RTL) and a
software model of it (govsim). Differential testing feeds both the exact same messages and compares the answers.
Where they differ, at least one of them is wrong, or the rulebook never said. It is like setting two watches to the
same time and checking them at random moments: one of them drifting tells you something even before you know which.

**Planting a mistake to test the inspector.** How do you know the inspector actually checks the stair rail and is
not just ticking boxes? You lower one rail on purpose and see if they catch it. That is mutation testing: make a
one-line mistake in the chip design and confirm the test for that rule now fails. A test that still passes with the
mistake in place was not really testing anything.

## What I ran

One command, `python -m rtl.conformance`. It:

- checks that every rule quoted in the table really appears, word for word, in docs/04 or docs/07 (125 rules);
- runs 174 conformance tests against the chip design, block by block (counter, measurement registers, epoch,
  lifecycle, capability table, ticket store, heartbeat, the halt sequencer, the loop, the meter, the mailbox, the
  alarm register, and the whole core wired together);
- sends 4,000 random mailbox messages, plus fourteen hand-written ones taken straight from the spec, into both the
  chip design and the software model and compares every answer;
- does the same for the capability table (1,280 random lookups);
- maps every row of the existing 87-row attack and baseline catalogue to the rules it exercises;
- plants 32 one-line mistakes in the design, at least one per rule (30 rules), and confirms each is caught;
- writes the report to `results/rtl-conformance.md`.

## What passed

Most of it. The counter, the measurement registers, the epoch register, the ticket store, the alarm register, the
loop sense and the read-only register window all do what the spec says. The halt sequencer climbs on every cause
the spec lists, never comes back down on its own across 5,000 random cycles, and drives the three levers exactly as
the spec and the model both say. The chip boots stopped, with the loop open. On the mailbox, the chip design and the
model agree on all fourteen spec examples, including the 22 October case where a heartbeat was presented as a CLEAR.
Every one of the 30 planted mistakes was caught by a failing check.

## What disagreed

Fifteen findings, all written up with a test that reproduces each one. The two that matter most:

- **Tamper can be lost (CONFORMANCE-CLEAR-BEATS-TAMPER).** If an authorized CLEAR and a tamper signal land in the same clock cycle, the chip
  handles the CLEAR first and forgets the tamper. If the tamper was a one-cycle pulse (a glitch detector), the chip
  goes back to running. The spec says tamper means SAFE, full stop. The fix is to swap two lines and make tamper
  sticky.
- **Debug is open for a moment on a production part (CONFORMANCE-DEBUG-BEFORE-FUSE-LOAD).** The lifecycle register starts at "test" after reset
  and only reads the fuses when the firmware tells it to. Until then, a production chip will grant a debug request.
  The spec says production silicon has no debug path, ever. Real designs start in the most locked-down state.

The others are smaller: a signed HALT to a governor already in SAFE did not open the loop (and the software model
got the same case wrong in a different way; closed on 23 October 2026 when Yobie decided a HALT opens the loop on
every rung), the "millisecond" timer tick is really 1.024 ms, the capability table
can hold two entries for the same port, the usage meter wraps at 48 bits, the mailbox reports a different reason
than the model in a few double-fault cases, and the spec contradicts itself in one table. None of them was fixed
here; fixing is the next job, with each reproducer becoming the regression test.

The catalogue mapping says something worth saying out loud: all 87 catalogue rows run against the reference
software stack, not the chip. They count toward the 150 the brief asked for (87 + 174 = 261), but they are not
evidence about the hardware. The 174 conformance tests are.

## What didn't work

- **The first approach was stopped.** An earlier agent on this branch was asked to write new attack recipes
  against the chip and was stopped by Anthropic's safety system. I did not try to rephrase around that. The user
  approved this approach instead, which checks the design against its own rulebook. No attack recipes or bypass
  techniques are in this branch.
- **The lead on the mailbox was only half right.** The brief said the chip and the model check in a different
  order. They mostly don't: the model's signature check runs in the chip's order. What differs is where the
  "is the governor running" check sits, and the heartbeat path in the model. The finding says exactly that.
- **My first capability-table comparison drifted.** Once the two tables disagreed about a duplicate entry, every
  later answer diverged too, and the test reported nonsense. I split it: the random run now keeps entries from
  overlapping and agrees exactly, and the duplicate case has its own reproducer (CONFORMANCE-DUPLICATE-CAPABILITY-ENTRIES).
- **One of my own tests was wrong.** The LOOP register test expected the switch to close one clock cycle too
  early. The chip was right; I fixed the test.
- **This page and FINDINGS.md are generated.** The tool I write files with refused to write report-style
  Markdown directly, so the text lives in `findings.py` and `plain_english.py` and the one command renders it. The
  default run fails if the rendered files are out of date, which is the behaviour I want anyway.
- **Not tested here:** anything physical (the 1 ms halt bound on a real loop, levers on a real GPU, power loss),
  the crypto engines (the RTL takes their answer on a wire), and the firmware itself, which does not exist yet. The
  firmware-owned rules are checked against the software model where it implements them, and the table says so.
"""
