# What I proved about six parts of the chip, in plain English

This is the non-engineer's version of L7, work stream b. The engineer's version is `FINDINGS-b.md` and the
property files (`*.sv`) in this folder. One command checks all of it: `python -m rtl.formal`.

## How "proven" works here, in one paragraph

The chip is described in a hardware language, and a tool turns that description into a circuit file (Verilog).
I write down rules the circuit must always follow, and a solver, a program that searches every possible input
on every clock tick, tries to break them. First it tries every sequence up to 25 steps long (that is the
"bounded" check). Then it does induction, which is the domino argument: if the rule holds now, it must hold on the
next tick, whatever the inputs. When both pass, the rule holds forever, not just for 25 steps. I run that with three
different solvers (yices, z3, boolector) so one solver's bug cannot carry a result alone. Then I break the chip on
purpose, a line at a time (a "mutant"), and the proof must fail on every broken version. A proof that still passes
on a broken chip was not checking anything. Last, a separate simulator throws thousands of random inputs at each
part and compares it, tick by tick, with a little model I wrote straight from the spec, not from the chip.

## The heartbeat timer

**What it does.** The authority that is allowed to keep a GPU running sends a signed "you may keep going for N
milliseconds" message. This timer counts that down. At zero the chip starts shutting the GPU down.

**Analogy.** A parking meter that only takes coins minted by the city. Nobody else's coin fits, it ticks down one
minute at a time, and when it reads zero the boot goes on the car.

**What I proved.** Without a valid heartbeat the time left never goes up. A heartbeat sets it to exactly the time it
signed, no more. It counts down one per millisecond and reads "expired" exactly at zero, so N milliseconds means N,
not N+1 and not never.

**How I tried to break it.** Four planted bugs: a timer that refills itself when it hits zero; one that stops at one
and never expires; one that gives twice the signed time; one that hides "expired" on tick cycles. All four caught.

## The meter

**What it does.** Counts what each model used: tokens, compute cycles, bytes in, bytes out. The rules engine
compares these against budgets.

**Analogy.** A car's odometer. It only goes up, and the dealer cannot wind it back.

**What I found and fixed.** The old meter rolled over like an old five-digit odometer going from 99999 to 00000.
One big enough add made a counter smaller than it was, so a job could spend past its budget and then look like it
was under. That is the oldest trick in the used-car business. The meter now sticks at its maximum instead of
rolling over, which reads as "over every budget", the safe way to fail.

**What I proved.** Every counter in every slot only goes up, changes only when the meter is told to count for that
slot, by exactly the amount counted (or sticks at the top), and the host computer cannot write to it at all, and is
flagged when it tries.

**How I tried to break it.** Five planted bugs, the old rollover among them; a version where the host's choice of
which slot to read steers which slot gets charged; a host write that zeroes a counter; a host write that is not
flagged; a counter that is overwritten instead of added to. All five caught.

## The alarms

**What it does.** A row of 32 alarm bits. Anything can raise one. Only an approved, signed clear can lower one.

**Analogy.** A smoke detector that stays latched, beeping, until the fire marshal resets it with a key. Pulling
the battery does nothing.

**What I proved.** A raised alarm stays raised unless that exact alarm is cleared with authorization. A new alarm
always lands, even if a clear arrives at the same moment (raise beats clear). Nothing but a raise turns a bit on. The
"any alarm" light and the "someone tried to clear without permission" flag are exact.

**How I tried to break it.** Five planted bugs: clearing without authorization; one authorized clear wiping all 32;
a clear racing a new alarm and swallowing it; the "any alarm" light watching only alarm 0; the unauthorized-clear
flag never set. All five caught.

## The measurement register

**What it does.** Records what software the chip booted, as a running fingerprint (a hash). Each new piece of
software is folded into the fingerprint together with everything before it.

**Analogy.** A notary's logbook with numbered, glued pages. You can only add a line at the end, and every new line
is stamped together with the whole page before it, so you cannot tear a page out or rewrite one.

**What I proved.** The register changes only when the hash engine answers a request this register made, and then to
exactly what the engine said. The old value is always part of what gets hashed. One request at a time; an answer
nobody asked for is ignored. There is no write path.

**How I tried to break it.** Five planted bugs: accepting an engine answer nobody asked for; writing the data straight
in; leaving the old value out of the hash (no chain); latching before the engine answers; asking the engine twice.
All five caught.

## The loop driver (halt_loop.py)

**What it does.** Every governor in a rack sits on one shared wire loop with a little current flowing through it.
Any governor can open its switch and break the loop, and every governor watches for the current to stop. No current
means someone halted, so everyone halts.

**Analogy.** An old string of Christmas lights wired in series: pull one bulb and the whole string goes dark. The
box watching the string does not panic at one flicker, but two dark checks in a row means a bulb is out.

**What I proved.** The switch on the pin does exactly what the sequencer says, every tick. Two checks in a row with no
current always raise "loop lost", whatever happens between checks. One dark check alone does not. "Loop lost" stays
up until a check sees current again.

**How I tried to break it.** Five planted bugs: a switch that opens only while current flows (so it can never open a
dead loop); a debounce that forgets between checks, so a loss is never declared; a threshold one past where the
counter stops; a third dark check that clears the loss; a debounce that counts current instead of its absence. All
five caught.

## The whole core (top.py), all the parts wired together

**What it does.** Wires the parts together, drives the real pins (the brake, the reset, the GPU power, the loop
switch), and gives the host computer a window of read-only status registers plus one doorbell to ring when it has
dropped off a signed message.

**Analogy.** A building's control room behind glass. The front desk can read every gauge through the window and
can drop letters through one mail slot. It cannot reach a single switch.

**What I proved.** The pins follow the sequencer exactly. The chip powers up with everything off and the loop open.
A halt from any cause (tamper, a signed halt, the loop going dark, the heartbeat running out) reaches the pins on the
next tick. A halted chip never runs again without a signed clear. The heartbeat cannot be stretched without a valid
heartbeat. The loop, once opened, stays open until a clear and re-arming. And the host's reads, and its write port
to the policy register, touch no state at all, and its doorbell touches only the mailbox. The host part is proven on
the real, full-size chip; the rest on a scaled-down copy of the same design (short timers, fewer table entries), with
the reasons that the scaling does not matter written at the top of `governor_core.sv`.

**What I found and fixed.** The millisecond clock that drives the heartbeat and the shutdown timers was read off the
low digits of the chip's master counter. That counter has a "load a saved value at boot" input which, nothing
stopped, could be pulsed every tick to keep those low digits frozen. Frozen digits meant the millisecond clock never
ticked, so the heartbeat never ran out, with no heartbeat. Like a parking meter whose clock you can stop by tapping
the coin slot. The millisecond clock now has its own counter that nothing else can touch.

**How I tried to break it.** Seven planted bugs: the old frozen-clock design; a status read that resets the
millisecond clock; a doorbell that hides a heartbeat expiry; a brake that lets go whenever the heartbeat is alive; a
SAFE state that closes the loop switch again; a loop loss that is ignored until the heartbeat also runs out; the
host's read address choosing which meter slot gets charged. Every one must fail; the run prints "caught" for each.

**The open question, answered from this side.** If one chip loses its heartbeat, it climbs to SAFE and cuts its
GPU's power, but it never opens the loop, so the rest of the rack keeps running. That is what the design says, and
the proof confirms the chip does exactly that. Two things nobody had written down: a signed HALT sent to a chip that
is already in SAFE does not open the loop either, so it cannot stop the rack through that chip; and a chip that
never gets its first heartbeat holds the whole loop open, so at boot one missing heartbeat stops everyone, while
later it stops only one. Whether that is what we want is Yobie's call.

**Yobie's call, 23 October 2026.** "Silently failing is a bullshit feature." Both are now decided and proven. A
HALT to a chip in SAFE opens its loop (pulling the fire alarm rings on every floor, even one whose sprinklers already
went off); the chip stays in SAFE with its power off. A chip that never gets its first heartbeat still holds the rack,
but after five seconds its hardware raises a named alarm, NO_FIRST_HEARTBEAT, that anyone can read over the
management bus, and the authority can sign an EXCLUDE that closes that one chip's loop switch while its own GPUs stay
braked, in reset and unpowered (bypassing one faulty smoke detector needs the building manager's signature, and the
bypass is logged). The old "fact" that HALT in SAFE does nothing is gone; in its place are proven rules and planted
bugs that put the old behaviour back and get caught.

## What didn't work (every dead end, in order)

1. **Second solvers.** `yowasp-yices`, `yowasp-bitwuzla` and `pybitwuzla` do not exist on pip. The `bitwuzla` and
   `cvc5` pip wheels are Python libraries only, with no program yosys-smtbmc can talk to, so they are no use here.
   What worked: `yices-solver` (a real yices program in a wheel, Linux x86-64 only, no Mac wheel) and
   `yowasp-boolector` (runs everywhere, in WebAssembly). Boolector's first run prints a "preparing" banner that
   smtbmc read as a solver error; the runner now warms it up first. smtbmc calls it "boolector", so a two-line shim
   with that name points at the wheel. On a Mac, only z3 and boolector will run; the output says which ran.
2. **The meter rule failed on the first try.** Not a wrong rule: a real bug (the rollover above). Fixed, and the old
   code kept as a mutant.
3. **The meter proof was slow in z3**: about 100 seconds for the bounded check at 10 steps against 10 seconds in
   yices. Every meter rule is about one tick, so I set its bounded depth to 6 (induction still proves it forever)
   and run yices first.
4. **A property file used `$past` outside a clocked block**, which yosys does not allow. Moved inside before running.
5. **First host-isolation proof, attempt one:** yosys's own `miter` command on two copies of the core. It silently
   left out the registers whose names contain dots (the mailbox state, for one), so induction failed on states that
   can never happen. Also, yosys threw away my two wrapper copies because the core file marks itself as the top
   module. Replaced by a miter I generate myself, which compares every register by name.
6. **Attempt two:** that two-copy miter on the full-size core. z3 took about a minute where yices took a second on
   the broken version; on the fixed one, yices was still going after 26 minutes on this shared machine and I stopped
   it. Two copies of 256-bit registers and 8-entry tables is a lot of solver work.
7. **Attempt three, which is what runs now:** a structural proof on the full-size netlist. Yosys follows every wire
   the host can drive, through every gate, to the end, and asserts that no register (and no pin but the read data)
   is on that path. That holds forever at any size and takes seconds. The two-copy miter still runs, on the small
   build, as a second proof of the same rule (about two minutes each), on the original and on the three host-path
   mutants.
8. **My first parser of yosys's output read the internal helper functions' inputs as ports** (a port named "s"), so
   the miter failed with a tool error. Those were reported as MISSED, not as caught, which is exactly what the rule
   about tool errors is for. Fixed by skipping function bodies.
9. **Scheduling.** Six agents share two cores; a full run of my six blocks takes about 22 minutes, 18 of them the
   core. The core's main proof runs in all three solvers; its design facts and the small-build miters run in yices
   only, because they take minutes there and much longer in the other two.
10. **The random simulation missed two core mutants at first.** It never touched the counter's "load a saved value"
   input, so it could not see the frozen-clock bug, and it does not model the meter. I made it pulse that input half
   the time; it now catches the frozen clock too. It still misses two: the meter-slot one, and a status read with a
   side effect, because a random read lands on that one address only about once in 4096 ticks. The proof catches
   both. The
   simulation is a second opinion, not the judge, and the run says per mutant whether it agreed.

## Left at "small build" and why

The core's functional rules (pins, causes, heartbeat clock, loop) are proven on a scaled-down copy of the same
`top.py`, because at full size the shutdown timers are 30 000 and 300 000 milliseconds and the solver would have to
walk hundreds of millions of ticks to reach the top rungs. The timer comparisons themselves are proven at full size
in the sequencer's own proof (`halt_seq.sv`), and the host-isolation rules are proven on the full-size chip. Nothing
in this set is "bounded only": every rule above was closed by induction.
