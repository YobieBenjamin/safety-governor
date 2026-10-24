# Bench plan: the governor on an FPGA, a Raspberry Pi as the host

The goal: the day the parts arrive, I wire them as below, flash one file, and run one command. Everything a person
has to do with their hands is marked **HANDS**. Everything else is a script.

```
hw/fpga/build.sh                                   # on any machine: builds the bitstream, writes REPORT.md
openFPGALoader -b ulx3s hw/fpga/build/30mhz/governor_ulx3s_85f_30mhz.bit   # HANDS: board on USB; add -f for flash
python3 hw/fpga/host_test.py all --hours 168       # on the Pi: CSR checks, levers, firmware chain, EXCLUDE, one-week soak
```

Results land in `hw/fpga/results/*.json` (and a CSV for the soak), pass or fail, with the numbers.

## Read this first: what will happen on day one

`rtl/tests/test_smbus.py` found a halt-path bug before any hardware (finding RTL-CORE-HALTS-AFTER-REACHING-RUN in `REPORT.md`): with the loop sense
strobe running from power-on, the first RUN cycle sees a stale loop-lost and halts with cause LOOP. The bitstream
carries the RTL as it is, so until `halt.py` or `halt_loop.py` is fixed, `host_test.py levers` and `soak` will fail
at "reach RUN" and record it. That is the bench doing its job early. The fix is a one-line change proposed in
`REPORT.md`; the strict-xfail test turns red the moment it lands, and then this bench runs end to end.

## Bill of materials

Prices only where I looked them up, with the source and the date. Everything else: buy the part named, from anyone.

| # | Part | Qty | Why | Price (source, date) |
|---|---|---|---|---|
| 1 | Radiona ULX3S, ECP5 **85F** variant (LFE5U-85F-6BG381C) | 1 | The FPGA. The build uses 17,306 LUT4 and 12,831 flip-flops (see REPORT.md). The 12F variant is rated for 12,288 LUTs; the open tools place the design on it anyway (it is a 25F die), but that is untested on a board and outside Lattice's rating | US$275, in stock ([Crowd Supply](https://crowdsupply.com/radiona/ulx3s), 23 Oct 2026). The 12F listed at US$155, pre-order (see the note on the 12F) |
| 2 | Raspberry Pi 4 Model B or Pi 5, any RAM, with Raspberry Pi OS, power supply, SD card | 1 | The SMBus host and the firmware stand-in: I2C1 for the bus, SPI0 for the chain, GPIO for the halt-path pins. Its 3.3 V I/O matches the ULX3S, so no level shifter on the bench | not looked up |
| 3 | 74HC05 hex inverter with open-drain outputs, DIP-14 (TI SN74HC05N or equivalent) | 1 | Makes PERST# and PWRBRK# open drain AND fail-safe: an unconfigured FPGA leaves the inverter inputs pulled up, so both levers stay asserted | not looked up |
| 4 | Resistors: 10 kOhm x 6, 1 kOhm x 1 | | Pull-ups on the 74HC05 inputs (2) and on PERST#/PWRBRK# (2), pull-down on PWR_EN (1), spare (1); 1 k in the one-governor loop | not looked up |
| 5 | PCIe CEM slot breakout exposing PERST# (A11), PWRBRK# (B30), SMCLK (B5), SMDAT (B6), +3.3 V and GND on headers | 1 | Phase 2: proves the levers on the real connector. Phase 1 does not need it (the Pi reads the lever wires directly). I have not verified a specific product; check the pin labels on whatever you buy against PCI-SIG CEM | not looked up |
| 6 | PCA9306 I2C level translator breakout | 1 | Only when the SMBus side is not 3.3 V (a 1.8 V BMC or DC-SCM management bus). Not needed on the Pi bench | not looked up |
| 7 | Solderless breadboard, female-female and male-female jumper wires (about 30), micro-USB cable for the ULX3S | | Wiring | not looked up |
| 8 | Optional: a USB logic analyser or scope | 1 | The real lever latency (HALT pin to PERST# low). The Pi's polled number is only a ceiling | not looked up |

A USB-to-I2C adapter (any one with a Linux i2c-dev driver) works in place of the Pi for the `check` step only;
the other steps need the Pi's GPIO and SPI.

## Wiring (phase 1: Pi and ULX3S only)

ULX3S pins are the J1 header names from the board's constraint file (`gp[n]`/`gn[n]`). Pi pins are physical header
numbers with the BCM GPIO in brackets. **HANDS** for every row: check each against the ULX3S silkscreen and the Pi
pinout before power-up.

| Signal | ULX3S | Goes through | Raspberry Pi | Notes |
|---|---|---|---|---|
| GND | GND | | pin 6 | common ground first |
| SMB_SCL | gp[0] | | pin 5 (BCM3, SCL1) | the Pi has 1.8 kOhm pull-ups to 3.3 V on these two |
| SMB_SDA | gn[0] | | pin 3 (BCM2, SDA1) | |
| PERST_ASSERT | gp[1] | 74HC05 pin 1 (input A), 10 k to 3.3 V on pin 1 | | 1 = reset asserted |
| PERST# | | 74HC05 pin 2 (output A), 10 k to 3.3 V | pin 29 (BCM5) | open drain; phase 2: also to the breakout's A11 |
| PWRBRK_ASSERT | gn[1] | 74HC05 pin 3 (input B), 10 k to 3.3 V on pin 3 | | 1 = brake asserted |
| PWRBRK# | | 74HC05 pin 4 (output B), 10 k to 3.3 V | pin 31 (BCM6) | open drain; phase 2: also to B30 |
| 74HC05 power | | pin 14 to 3.3 V (ULX3S 3V3 header pin), pin 7 to GND; inputs 5, 9, 11, 13 to GND | | unused gates tied off |
| PWR_EN | gp[2] | 10 k to GND | pin 33 (BCM13) | push-pull; low when unconfigured |
| LOOP_CLOSED | gn[2] | 1 k resistor to gp[3] | pin 35 (BCM19) | a one-governor loop: our own closed switch is the current we sense |
| LOOP_SENSE | gp[3] | the 1 k from gn[2] | pin 37 (BCM26) | the Pi pulls this low to inject a loop fault (LOOP_BREAK), otherwise its pin floats |
| FW_HB | gn[3] | | pin 11 (BCM17) | firmware stand-in: a valid heartbeat, rising edge |
| FW_CLEAR | gp[4] | | pin 13 (BCM27) | firmware stand-in: an authorized clear |
| FW_HALT | gn[4] | | pin 15 (BCM22) | firmware stand-in: an authorized halt |
| TAMPER_N | gp[5] | | pin 16 (BCM23) | high = enclosure closed; unplugged reads as tripped |
| BENCH_RST | gn[5] | | pin 18 (BCM24) | the Pi can reset the FPGA logic |
| FW_SCK | gp[6] | | pin 23 (BCM11, SCLK) | the firmware chain, SPI mode 0, 1 MHz |
| FW_SDI | gn[6] | | pin 19 (BCM10, MOSI) | |
| FW_CS_N | gp[7] | | pin 24 (BCM8, CE0) | the rising edge applies the vector |
| FW_SDO | gn[7] | | pin 21 (BCM9, MISO) | readback |

The ULX3S LEDs: 0 to 2 the sequencer state (0 HALTED_INITIAL, 1 RUN, 2 THROTTLE, 3 HALT, 4 SAFE), 3 our loop switch
open, 4 power brake asserted, 5 doorbell, 6 an SMBus timeout happened, 7 heartbeat.

The FW_* pins and the chain are the firmware's wires, brought out because this FPGA has no Ibex and no crypto. They
do not exist on the governor module, and nothing on the SMBus side can reach them. The SMBus target is the only
host interface, and it is read-only plus the doorbell (proven in `rtl/formal/smbus.sv`).

## Phase 2: the levers on a real PCIe connector

**HANDS.** Wire PERST# and PWRBRK# (the 74HC05 outputs) and GND to the CEM breakout, with the 10 k pull-ups to the
breakout's 3.3 V. Rerun `host_test.py levers`: the Pi reads the same nets, now at the connector. For a GPU in the
loop, the host's own PERST# must be combined with the governor's (the governor can only pull it low, never release a
reset the host holds), which needs an interposer with the host's PERST# cut and re-driven through an AND. That
interposer is not designed yet; it is the next hardware item.

## Steps on the Pi

1. **HANDS**: flash Raspberry Pi OS, then `sudo raspi-config nonint do_i2c 0 && sudo raspi-config nonint do_spi 0`,
   `python3 -m pip install smbus2 spidev` (gpiozero ships with the OS), clone this repo.
2. **HANDS**: wire as above, plug the ULX3S into a computer by USB, and load the timing-clean bitstream that
   `REPORT.md` names (today `hw/fpga/build/30mhz/governor_ulx3s_85f_30mhz.bit`, because 50 MHz does not close on this
   part, finding RTL-FPGA-MISSES-50-MHZ) with `openFPGALoader -b ulx3s <file>`. `openFPGALoader` is in most Linux package managers and
   Homebrew. The bitstream comes from `hw/fpga/build.sh`, run anywhere.
3. `i2cdetect -y 1` should show 0x58. Then `python3 hw/fpga/host_test.py all --hours 168`.

What each step proves on hardware:

| Step | What | Pass means |
|---|---|---|
| `selftest` | the script's PEC and frames against known vectors | the script is sane (no hardware) |
| `check` | reads ID, STATE, LEVERS, MBOX_STATUS and every static CSR with PEC; sends 23 malformed writes; rings the doorbell | malformed writes change no register, the doorbell reaches the mailbox (status 4: no firmware behind it), CSR read time recorded |
| `levers` | reset, heartbeat to RUN, halt command, clear, tamper, injected loop break, heartbeat expiry | every rung shows up in STATE, and PERST#, PWRBRK#, PWR_EN as wires agree with the LEVERS register every time |
| `fwchain` | meter increment, CAUSE firmware code, alarm bit, ticket burn and replay | the chain reaches the core and SMBus reads the result |
| `exclude` | reset with no heartbeat: the loop stays open and, after the 5 s boot window, ALARMS bit 31 and CAUSE bit 3 name it (NO_FIRST_HEARTBEAT); an EXCLUDE strobe on the firmware chain then closes the loop switch while PERST#, PWRBRK# and PWR_EN stay asserted (ALARMS bit 30, CAUSE bit 4); a heartbeat then arms it to RUN | each of those reads true on the pins and in the registers (Yobie's call 2, docs/26; added 23 October 2026) |
| `soak` | heartbeats at 1 Hz, STATE/CAUSE/LOOP/LEVERS/ALARMS polled 5 times a second for `--hours` | zero halts and zero SMBus errors; every halt is logged with time and cause and counted |

WAVE-FPGA-BESIDE-REAL-GPU (docs/20) asks for three cost numbers and the false-halt rate. This bench measures the false-halt rate of the
hardware halt path (sequencer, loop debounce, levers, heartbeat timer, a real loop wire) and the host-visible
latencies. It cannot measure the firmware share, the crypto engine utilisation or the record latency, because the
bitstream carries no firmware and no crypto engines. The soak's JSON says so in `not_measured_here`.
