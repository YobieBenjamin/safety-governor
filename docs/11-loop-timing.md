# 11 · The halt loop as a circuit

**In plain words.** The halt loop is one wire of current threaded through every governor in a
domain; any governor that opens its switch, and any break in the wire, stops the current for
everyone. This document asks the only timing question that wire has to answer: when the
current stops somewhere, how long until every governor has pulled its halt output, and does
that fit inside the 1 ms the design promises? The answer, from an ngspice circuit simulation
of up to 72 governors on up to 213 m of twisted pair, is that the electrical part takes at
most 6 µs. The budget is spent almost entirely in the governor's own clock: sampling the sense
line every 100 µs and asking for two missing samples in a row before declaring the loop lost.
Worst case, 317 µs from the switch opening to the last halt output, against a bound of 1 ms.

> **Plain-English version:** `10-plain-english-walkthrough.md` §6.
> **Backed by:** generator `hw/loop/loop_netlist.py`, sweep `hw/loop/run_loop.py` (`make loop`),
> generated results `hw/loop/results.md`; tests `hw/loop/test_loop.py` (ngspice, skipped when
> ngspice is absent) and `tests/test_contract_halt_reaches_every_gpu.py` (functional model); the loop's rules in
> `02-safety-fabric.md` §1, the wiring in `hw/pcb/rack-integration.md` §4, the timing row in
> `04-specification.md` §9. The bench measurement in Phase 2 replaces every number here.

## 1. What was simulated, and why the wire is not where the time goes

The loop is a supervised series current loop with a live-zero current, the 4 to 20 mA idea:
20 mA flowing means "run", no current means "stop", and a dead wire reads the same as a
deliberate stop. Each governor has a loop-in pin, a fail-open switch, a sense element and a
loop-out pin. The simulation builds that loop as a SPICE netlist for N governors, opens one
governor's switch (or breaks one hop of cable) at a known instant, and records the moment
every other governor's sense voltage falls through its comparator threshold. The sweep covers
N of 8, 36 and 72; the opener at the first, middle and last position; 1 m and 3 m of cable
per tray-to-tray hop; 0 C and 85 C; and a wire break at the middle hop for each N.

A series circuit has one current. When any switch opens, the same current stops at every
governor at once; nothing propagates along the chain the way a message would. What delays the
reading at a distant governor is only the charge stored in the cable's capacitance, which has
to drain through the loop's own resistances before the sense voltage there falls. With 50 pF
per metre and at most 71 hops of 3 m, that is about 10 nF, and the time constants are a few
microseconds. The slowest reading in every run is at one end of the chain: the governor next
to the driver when the far end opens (the driver's series resistor keeps feeding the cable
capacitance until it charges up to the compliance voltage), or the governor at the far end when
the head opens (the whole cable discharges through it). Temperature moves the copper and the
resistors by a few percent and the result by a few nanoseconds.

So the end-to-end time is dominated by the digital path, which is the same at every governor:
the comparator's delay, up to one sense period before the next sample, two sense periods of
debounce, and the lever driver. That is why `02-safety-fabric.md` §1 says the bound is set by
the slowest sense period plus debounce, and why this simulation is a check on the wire rather
than the place where the margin is decided.

## 2. The circuit

One governor's loop stage, as modelled:

```
      LOOP_IN                                                       LOOP_OUT
      ---o------[ S_k ]------+------[ R_sense  10 ohm ]------+------o--->  hop k to the next tray:
          fail-open series   |                               |             R 0.1 ohm/m per conductor,
          switch: open at    |     +---------------------+   |             C 50 pF/m as a pi section
          power-on, opened   +-----| +                   |   |             (C/2 to the return
          by a loop-opening        |   comparator        |---+---> loop_present   conductor at each end)
          cause, Ron 1 ohm   +-----| -   V(+) - V(-)     |         (1 = 20 mA flows)
          Roff 1 Mohm        |     |     > V_th 100 mV ? |                 |
                             |     +---------------------+                 v
          (control: 1 V = closed; a PULSE to 0 V        sampled every 100 us (the sense period);
           at t_open opens governor k's switch)         two consecutive 0 samples = loop_lost
                                                         -> halt output, PWRBRK# driver, 10 us
```

The chain, driver to jumper plug:

```
   loop driver at the supervisor's position: 24 V, series resistor sized for 20 mA at 25 C
   +24 V --[ R_src ]--> gov 1 --hop 1-- gov 2 --hop 2-- ... --hop N-1-- gov N --+ jumper plug
                                                                                |  at the last tray
   return conductor of the same pair, lumped as one resistor  <-----------------+
```

The driver is a voltage source with a series resistor rather than a current regulator. A real
4 to 20 mA driver regulates current up to a compliance voltage; the resistor is the simplest
model that opens and discharges the same way, and it is listed below as an assumption. The
comparator is a behavioural source (an ideal threshold at 50 percent of the nominal sense
voltage, no offset, no delay); its delay is added in the digital path. Every resistor carries
a temperature coefficient and the deck sets `.temp`, so the loop current and the sense voltage
move with temperature (198.8 mV at 85 C against 200 mV at 25 C). A wire break is a second
switch in series with the chosen hop. The transient runs with a 1 µs print step and a 100 ns
maximum internal step; one `.measure` line per governor finds the threshold crossing.

## 3. Parameters and assumptions

| Parameter | Value | Status |
|---|---|---|
| Loop current, live zero | 20 mA flowing = run, 0 mA = stop | from the spec (`02` §1) |
| Sense period | 100 µs | from the spec (`04` §9) |
| Debounce | loss declared after two sense periods | from the spec (`04` §9) |
| End-to-end halt bound | 1 ms for a 72-GPU domain | from the spec (`02` §1) |
| Largest domain | 72 governors | from the spec (`02` §1) |
| Cable | one twisted pair tray to tray, jumper plug at the last tray | from the spec (`hw/pcb/rack-integration.md` §4) |
| Driver | 24 V behind a series resistor sized for 20 mA at 25 C (365 ohm at N=72 with 3 m hops, 1111 ohm at N=8 with 1 m hops) | assumed |
| Switch | ngspice `SW` model, Ron 1 ohm, Roff 1 Mohm, control edge 100 ns | assumed |
| Sense element | 10 ohm, 200 mV at 20 mA | assumed |
| Comparator threshold | 100 mV, 50 percent of the nominal sense voltage; ideal, no offset | assumed |
| Cable resistance | 0.1 ohm/m per conductor (24 AWG class), forward conductor per hop, return conductor lumped | assumed |
| Cable capacitance | 50 pF/m, pi section with C/2 at each end of every hop | assumed |
| Cable inductance | 0 by default; 0.6 µH/m was tried and changed the result by under 0.1 µs | assumed |
| Hop length | 1 m and 3 m (one hop per tray, 71 hops at N=72) | assumed |
| Temperature coefficients | copper 3930 ppm/K, driver resistor 200 ppm/K, sense resistor 100 ppm/K, nominal at 25 C | assumed |
| Temperatures | 0 C and 85 C | assumed |
| Comparator latency | 1 µs | assumed |
| Sampling phase uncertainty | up to one sense period (the loss lands just after a sample) | assumed, worst case |
| Lever assertion | 10 µs for the PWRBRK# driver, from loop_lost to the pin | assumed |
| Digital path, total | 1 + 100 + 200 + 10 = 311 µs | derived from the rows above |

## 4. Results

Copied from `hw/loop/results.md`, which `python3 hw/loop/run_loop.py` regenerates (39 ngspice
runs, about 4 s). Electrical propagation is the time from the switch opening or wire break to
the slowest governor's threshold crossing; digital detection is the 311 µs path above.

| N | Opens | Hop (m) | Temp (C) | Last to see loss | Electrical propagation (us) | Digital detection (us) | Total (us) | Margin to 1 ms (us) | Result |
|---|---|---|---|---|---|---|---|---|---|
| 8 | governor 1 (first) | 1 | 0 | governor 8 | 0.07 | 311.00 | 311.07 | 688.93 | pass |
| 8 | governor 1 (first) | 1 | 85 | governor 8 | 0.07 | 311.00 | 311.07 | 688.93 | pass |
| 8 | governor 1 (first) | 3 | 0 | governor 8 | 0.09 | 311.00 | 311.09 | 688.91 | pass |
| 8 | governor 1 (first) | 3 | 85 | governor 8 | 0.09 | 311.00 | 311.09 | 688.91 | pass |
| 8 | governor 4 (middle) | 1 | 0 | governor 1 | 0.17 | 311.00 | 311.17 | 688.83 | pass |
| 8 | governor 4 (middle) | 1 | 85 | governor 1 | 0.17 | 311.00 | 311.17 | 688.83 | pass |
| 8 | governor 4 (middle) | 3 | 0 | governor 1 | 0.41 | 311.00 | 311.41 | 688.59 | pass |
| 8 | governor 4 (middle) | 3 | 85 | governor 1 | 0.41 | 311.00 | 311.41 | 688.59 | pass |
| 8 | governor 8 (last) | 1 | 0 | governor 1 | 0.34 | 311.00 | 311.34 | 688.66 | pass |
| 8 | governor 8 (last) | 1 | 85 | governor 1 | 0.34 | 311.00 | 311.34 | 688.66 | pass |
| 8 | governor 8 (last) | 3 | 0 | governor 1 | 0.90 | 311.00 | 311.90 | 688.10 | pass |
| 8 | governor 8 (last) | 3 | 85 | governor 1 | 0.90 | 311.00 | 311.90 | 688.10 | pass |
| 8 | wire break, hop 4 | 3 | 85 | governor 1 | 0.47 | 311.00 | 311.47 | 688.53 | pass |
| 36 | governor 1 (first) | 1 | 0 | governor 36 | 0.33 | 311.00 | 311.33 | 688.67 | pass |
| 36 | governor 1 (first) | 1 | 85 | governor 36 | 0.33 | 311.00 | 311.33 | 688.67 | pass |
| 36 | governor 1 (first) | 3 | 0 | governor 36 | 0.90 | 311.00 | 311.90 | 688.10 | pass |
| 36 | governor 1 (first) | 3 | 85 | governor 36 | 0.92 | 311.00 | 311.92 | 688.08 | pass |
| 36 | governor 18 (middle) | 1 | 0 | governor 1 | 0.59 | 311.00 | 311.59 | 688.41 | pass |
| 36 | governor 18 (middle) | 1 | 85 | governor 1 | 0.59 | 311.00 | 311.59 | 688.41 | pass |
| 36 | governor 18 (middle) | 3 | 0 | governor 1 | 1.64 | 311.00 | 312.64 | 687.36 | pass |
| 36 | governor 18 (middle) | 3 | 85 | governor 1 | 1.65 | 311.00 | 312.65 | 687.35 | pass |
| 36 | governor 36 (last) | 1 | 0 | governor 1 | 1.30 | 311.00 | 312.30 | 687.70 | pass |
| 36 | governor 36 (last) | 1 | 85 | governor 1 | 1.30 | 311.00 | 312.30 | 687.70 | pass |
| 36 | governor 36 (last) | 3 | 0 | governor 1 | 3.75 | 311.00 | 314.75 | 685.25 | pass |
| 36 | governor 36 (last) | 3 | 85 | governor 1 | 3.76 | 311.00 | 314.76 | 685.24 | pass |
| 36 | wire break, hop 18 | 3 | 85 | governor 1 | 1.70 | 311.00 | 312.70 | 687.30 | pass |
| 72 | governor 1 (first) | 1 | 0 | governor 72 | 1.15 | 311.00 | 312.15 | 687.85 | pass |
| 72 | governor 1 (first) | 1 | 85 | governor 72 | 1.16 | 311.00 | 312.16 | 687.84 | pass |
| 72 | governor 1 (first) | 3 | 0 | governor 72 | 3.49 | 311.00 | 314.49 | 685.51 | pass |
| 72 | governor 1 (first) | 3 | 85 | governor 72 | 3.55 | 311.00 | 314.55 | 685.45 | pass |
| 72 | governor 36 (middle) | 1 | 0 | governor 1 | 0.81 | 311.00 | 311.81 | 688.19 | pass |
| 72 | governor 36 (middle) | 1 | 85 | governor 1 | 0.81 | 311.00 | 311.81 | 688.19 | pass |
| 72 | governor 36 (middle) | 3 | 0 | governor 1 | 2.23 | 311.00 | 313.23 | 686.77 | pass |
| 72 | governor 36 (middle) | 3 | 85 | governor 1 | 2.23 | 311.00 | 313.23 | 686.77 | pass |
| 72 | governor 72 (last) | 1 | 0 | governor 1 | 2.13 | 311.00 | 313.13 | 686.87 | pass |
| 72 | governor 72 (last) | 1 | 85 | governor 1 | 2.15 | 311.00 | 313.15 | 686.85 | pass |
| 72 | governor 72 (last) | 3 | 0 | governor 1 | 6.15 | 311.00 | 317.15 | 682.85 | pass |
| 72 | governor 72 (last) | 3 | 85 | governor 1 | 6.15 | 311.00 | 317.15 | 682.85 | pass |
| 72 | wire break, hop 36 | 3 | 85 | governor 1 | 2.27 | 311.00 | 313.27 | 686.73 | pass |

**Worst case:** N=72, the last governor opens, 3 m hops, 85 C: electrical propagation 6.15 µs,
total 317.15 µs, margin 682.85 µs to the 1 ms bound. **Every configuration passes.** The
electrical term is at most 2 percent of the total; a sense period of 300 µs would still fit.

## 5. What the simulation proves, and what it does not

**It proves** that, in a lumped model with the assumptions in §3, loss of current anywhere on
the loop reaches every governor's comparator within microseconds, that the time scales with
cable length and loop position as a distributed RC line should (and not with temperature), and
that the published budget of 100 µs sense period plus two periods of debounce leaves more than
two thirds of the 1 ms bound in hand at 72 governors. It also fixes the arithmetic of the
digital path in one place (`run_loop.py`) so that a change to the sense period or the debounce
count is a one-line change with a pass/fail answer.

**It does not prove** anything about the physical rack. The model is lumped (one RC section per
hop), the cable parameters are assumed rather than measured, the switch is ideal (no charge
injection, no driver current limit), the driver is a resistor rather than a regulator, and the
comparator has no offset, hysteresis or noise. It does not model EMI pickup on the pair,
connector resistance and its variation across 72 mated pairs, ground offsets between trays,
supply droop, or a switch that fails short. A comparator offset or a noisy pair could make a
governor sample "current present" during a real loss or "lost" during a real run; the
debounce exists for the second case and the threshold margin (100 mV below nominal, 100 mV
above zero) for both, and neither margin is validated here. The functional model's
`tests/test_contract_halt_reaches_every_gpu.py` checks the rules of the loop, not its electronics. The bench
measurement of the prototype rack in Phase 2 (`04-specification.md` §9: "design targets
measured in Phase 2") replaces this document's numbers; until then they are design targets
with a simulation behind them, not results.

## 6. Running it

```
make loop                                   # the sweep: writes hw/loop/results.md, exit 1 on any miss
python3 hw/loop/loop_netlist.py --n 72 --open 72 --hop 3 --temp 85 --run   # one configuration
python3 hw/loop/loop_netlist.py --n 8 --open 4 > deck.cir                   # just the netlist
python -m pytest -q hw/loop/test_loop.py    # N=8 under 100 us electrical, under 1 ms total
```

The sweep needs ngspice on the PATH (version 42 was used, `ngspice -b`); the pytest skips its
electrical cases without it and still checks the netlist's shape and the digital arithmetic.
