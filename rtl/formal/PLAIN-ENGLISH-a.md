# What we proved about six parts of the chip, in plain English

For each part: write down its rules, have a solver check them against every state the circuit can ever reach, then
break the circuit on purpose and watch the check fail. If the check didn't fail, it wasn't a check.

- **Mailbox** (a bank's night deposit slot). The only way in is the slot. Every envelope needs a newer serial number
  and a valid signature, and the signature has to be for this exact instruction, so a signed "I'm alive" note can't
  be passed off as "release the brakes". Broken 9 ways on purpose, including removing that last check, which was the
  bug from 22 October. All 9 caught.
- **Capability table** (a prepaid transit card). It works only at the gate it was issued for, only before it
  expires, only in the current fare season, and never for more than its balance. No card exists without the
  issuer's stamp. 9 breaks, 9 caught.
- **Ticket store** (a cloakroom that tears each ticket in half when it's used). A torn ticket never works again, and
  when the rack is full it refuses new tickets rather than throwing an old one out. 5 breaks, 5 caught.
- **Epoch register** (the locked board showing which rulebook is in force). Only a quorum of keyholders can change
  it; the public pen on a string isn't connected to anything. 5 breaks, 5 caught.
- **Monotonic counter** (a car's odometer). It only goes up, it stops at the top instead of rolling over, and after
  a power cut it starts from the last reading burned into fuses. The proof found it could roll over; fixed.
  5 breaks, 5 caught.
- **Lifecycle** (a factory door that gets bricked up when the car ships). Once in production, the debug door never
  opens again. The proof found the door stood open for a moment after every restart; fixed. 5 breaks, 5 caught.

Every block also ran 20,000 random cycles against a separate model written from the spec (two people doing the same
sum on separate sheets), and five were re-proven by a second solver.

What's still open, in one picture: three of the open findings (F3, F5, F8) are the circuit forgetting on restart
what the spec says firmware and non-volatile memory must remember. A bouncer who forgets every face when the lights
flicker. The spec puts the memory in firmware, the firmware isn't written yet, and the tests that will hold it to
account are already here.

## What didn't work

- Yosys accepted references to signals inside a block, then silently treated them as free inputs. Any proof using
  them would have been meaningless, a lock tested with the door already off its hinges. Switched to pasting the
  rules into the block itself, and the runner now refuses any yosys warning.
- The lifecycle proof failed at first for want of a helper rule: before any fuse read, the remembered fuse value is
  zero.
- The mailbox proof failed at first because a clocked assumption applies one cycle late in yosys. Rewritten.
- A search-and-replace broke two names in the ticket store property file. The run flagged it as a tool error, not as
  a catch, which is exactly what that rule is for. Fixed.
- The findings check crashed on a stray period after a block name. Fixed.
- The capability table at depth 25 ran over 8 minutes and was stopped. Depth 5 is enough, because its induction
  closes at depth 2.
- cvc5 and bitwuzla from pip ship only Python libraries with no program the checker can call, and there is no
  yowasp-yices. A third-party yices package worked (Linux x86-64 only; no Mac wheel).
- yices couldn't finish the ticket store in 15 minutes, so that block has one solver plus the simulation, and the run
  prints NOT RUN for it rather than pretending.
- Making the stricter planted-bug rule global broke an existing halt sequencer bug that needs 300,000 ticks to show,
  so the stricter rule applies only to these six blocks.
- A wait loop never finished because its search pattern matched its own command line. Stopped.
- The agent couldn't write this file or FINDINGS-a.md itself: the environment blocked subagents from writing report
  documents. It didn't route around that; it handed the text back and the coordinator committed it.
