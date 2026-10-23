# From Verilog to a chip drawing, in plain English

This is the story of taking the governor's logic (`rtl/gen/governor_core.v`) and turning it into
a GDS file: the drawing a fab turns into photomasks. The industry calls it "RTL to GDS". Then
"signoff", which is the set of checks that say the drawing is safe to send. I wrote it for
someone who has never seen a chip layout. The numbers are real and come from the runs in this
folder. `SIGNOFF.md` has the same results in checklist form; `TOOLCHAIN.md` has the gory
details of getting the tools to run.

## The steps, each with an everyday picture

**1. Synthesis.** The Verilog says what the circuit does ("if the heartbeat expires, start the
halt"). Synthesis turns that into a parts list of real logic gates from the sky130 library:
this many AND gates, this many flip-flops, wired like so.
*Picture:* a recipe ("make a cake") turned into a shopping list and a wiring of steps ("2 eggs,
whisk, then fold into flour"). Nothing has a place yet, only parts and connections.

**2. Floorplan.** Pick the size of the chip, where the edge pins go, and lay down the power
rails.
*Picture:* buying the plot of land for a house, deciding where the doors are, and running the
water mains before any furniture arrives.

**3. Placement.** Put each of the ~28,000 gates at a spot on the silicon. Gates that talk to
each other a lot go near each other.
*Picture:* seating guests at a wedding. The people who talk most sit closest, and nobody sits
in the aisle.

**4. Clock tree (CTS).** Every flip-flop listens to the same 50 MHz clock tick. The clock tree is a
branching set of buffers that delivers the tick to all 5,200 flip-flops at nearly the same
instant.
*Picture:* a conductor's beat reaching every musician in a huge orchestra at the same moment,
using assistant conductors in each section so the back row is not late.

**5. Routing.** Draw the actual metal wires between gates, on five metal layers stacked like
floors in a building.
*Picture:* laying the plumbing and electrical in a house after the furniture is in, without any
two pipes crossing in the same wall.

**6. Antenna repair.** During manufacturing, long metal wires collect static charge that can zap
the tiny transistor gate they end on. Little diodes are added as lightning rods.
*Picture:* grounding straps on a long fence so a lightning strike does not fry the gate at the
end.

**7. Extraction and timing signoff (STA).** Measure the real resistance and capacitance of every
wire, then check that every signal arrives in time, at three "corners": typical silicon
(tt), slow silicon on a hot day at low voltage (ss), fast silicon on a cold day at high voltage
(ff). "Setup" means a signal gets there before the clock tick; "hold" means it does not get
there so fast that it overwrites the previous value.
*Picture:* checking a train timetable for every connection, on a normal day, in a snowstorm,
and on a day with a tailwind. The snowstorm catches late trains; the tailwind catches trains
that leave before passengers have boarded.

**8. DRC (design rule check), with Magic and KLayout.** The fab publishes thousands of rules:
minimum wire width, minimum spacing, how far a via must overlap metal. Two independent tools
check every polygon against them.
*Picture:* the building inspector with the building code, twice, by two different inspectors.

**9. LVS (layout versus schematic), with Netgen.** Read the drawing back, work out what circuit
it actually is, and compare it with the netlist from synthesis.
*Picture:* after the house is built, walk it room by room and compare it with the architect's
plans. A missing door or an extra wall is a failure.

**10. Fill and density.** Add dummy metal in empty areas so every layer is evenly covered, which
the polishing step in the fab needs.
*Picture:* adding packing peanuts so the box does not collapse in the middle when it is pressed
flat.

**11. IR drop.** Check that the power grid delivers close to the full 1.8 V everywhere, not
1.6 V in the far corner.
*Picture:* water pressure on the top floor of a tall building when everyone showers at once.

**12. Stream out the GDS.** Write the final drawing.
*Picture:* the final blueprint, stamped.

On top of the standard flow I added one check of my own: **netlist versus RTL**. LVS proves the
drawing matches the netlist, but who proves the netlist still does what the Verilog says?
Synthesis tools have bugs. So I simulate the RTL and the final routed netlist side by side,
feed both the same random inputs every clock, and compare every output bit, every cycle. Then I
plant a deliberate bug in a copy of the netlist and show the comparison catches it.
*Picture:* two translators read the same speech; you check line by line that they agree, and
you slip a deliberate mistranslation into one copy to prove you are actually reading.

## What happened at each step here

The run used the governor_core Verilog as it stood at commit `ecab712`, before the 23 October fixes (halt
priority, lifecycle, counter, meter, heartbeat clock) and without the SMBus and CEM blocks. So these numbers
describe that older circuit. The next run has to use the current one.

It got as far as **detailed routing** (step 41 of the flow) and was stopped there: the container was restarted
in the middle of the router, and the run was not restarted. Everything before it ran:

| Step | What came out |
|---|---|
| Lint, synthesis | 0 errors, **0 latches**, every cell mapped to the sky130 library |
| Size | 117,929 standard cells (2,512 of them hold buffers added later), 0.52 mm2 of cells on a 1.8 mm x 1.8 mm die, 16 percent used. Plenty of room |
| Floorplan, power grid, placement, clock tree | done |
| Timing, typical corner (25 C, 1.80 V) | met: worst setup slack +4.1 ns at 50 MHz, hold +0.25 ns |
| Timing, slow corner (100 C, 1.60 V) | **not met**: worst setup slack -65.7 ns |
| Timing, fast corner (-40 C, 1.95 V) | **not met**: worst setup slack -42.9 ns. A fast corner failing setup while the typical one passes is not what physics usually does, so I don't trust this number yet; it points at a constraint or path problem to investigate, not at a slow circuit |
| Antenna check before routing | **1,037 violations** on 393 nets. Long wires collect charge during manufacturing and can blow the gates they connect to; the fix is diodes, which the flow's next steps insert |
| Detailed routing | started, killed by the restart, never finished |

Not reached: DRC, LVS, fill, IR drop, GDS. So no box on the tape-out checklist that needs a finished layout is
ticked. What this run does show: the design synthesizes cleanly to a real foundry library with no latches,
fits with room to spare, and meets timing at the typical corner. What it also shows: two corners fail and
antenna repair is a real job.

## What did not work

Every path I tried, in order, with the error it hit. `TOOLCHAIN.md` has the same list as a
table.

- Docker: the daemon starts but no container registry is reachable through this machine's proxy.
- Nix: no binary cache is reachable; building every tool from source on 2 cores would take days.
- Current LibreLane 3 from pip: needs 2025 tool versions; the newest prebuilt OpenROAD reachable here is from
  February 2024.
- volare, the usual PDK downloader: refused by the proxy. Worked around by downloading the PDK release
  tarballs straight from GitHub.
- Four fixes to get the tools themselves to start (a missing library for OpenROAD, a Yosys data path, KLayout
  needing its own environment, the wrong program called netgen on conda-forge). All in `TOOLCHAIN.md`.
- Run 4 hit an antenna error that stopped the flow; settings were changed and it was rerun (logs kept).
- The final attempt was stopped mid-routing by a container restart and, by Yobie's call, not restarted.

## What machine would finish the job

Any Mac or Linux machine with Docker and an open internet connection. The current LibreLane runs the same
`config.json` unchanged (`TOOLCHAIN.md` has the two commands). On the M4 Max Mac that is about an hour, not
the day it takes here. First update `config.json` to read the current `rtl/gen/governor_core.v`, then chase
the corner timing and the antenna count before anything else.
