# Safety Governor (SG)

**A chip that says no. One per NVIDIA GPU, added through the rack's own boards, changing
nothing in the GPU or in CUDA.**

This is the chip-design project behind the blog series
[*The Chip That Says No*](https://github.com/YobieBenjamin/hardware-and-silicon/tree/main/blog)
and the reference stack in [hardware-and-silicon](https://github.com/YobieBenjamin/hardware-and-silicon).
That repository proves the *protocol* (every action authorized, tickets, budgets, holds,
epochs). This one is the *silicon*: a small, dumb, tamper-resistant governor for each GPU,
living on the system board and the GPU baseboard of a rack, with physical authority over
that GPU and over the switches the GPU's traffic already passes through, and a private,
fail-safe link to every other governor in the rack.

The design constraint that shapes everything: NVIDIA has most of the market, and nothing in
this project asks NVIDIA for new silicon or touches CUDA. The governor is added where a rack
already accepts add-on control hardware (the motherboard's management module slot, the
baseboard's management buses) and it governs through hooks that already exist: the GPU's
out-of-band management bus, the power-brake and reset pins, the slot power enable, the
NVSwitch and PCIe switch management interfaces, the BlueField DPU's filter tables, and the
GPU's confidential-computing attestation. The only asks to NVIDIA are firmware and software,
and the design works without them.

The name is the oldest analogy in engineering. James Watt's governor was two brass balls on a
spinning shaft. When the engine ran too fast the balls flew out and closed the steam valve. No
operator could talk it out of its job, it understood nothing about the factory, and it never
slept. That is the whole idea. A model can think anything. The governor decides what leaves.

## What is in here

| Directory | What it is | Run it |
|---|---|---|
| [`docs/`](docs/) | The design: objectives, architecture, the safety fabric, interfaces to the GPU and the rack, the specification, the threat model, the assumptions register, the verification plan, and the plan to put it on silicon through lithography | read |
| [`govsim/`](govsim/) | A functional model of the governor, the rack's switches as enforcement points, the halt loop and the message fabric, across a simulated rack of GPUs | `./run.sh` |
| [`tests/`](tests/) | One test file per hypothesis, H0 to H16. A hypothesis is a claim the blog makes; a test is what would knock it down | `./run.sh` |
| [`rtl/`](rtl/) | The hard-core digital blocks in [Amaranth HDL](https://amaranth-lang.org/), simulated, with generated Verilog in `rtl/gen/` | `make rtl` |
| [`hw/`](hw/) | The OpenLane flow for a SkyWater sky130 shuttle run, the pinout, and the rack integration reference (module, baseboard signals, switch management) | `make gds` on a machine with OpenLane |
| [`results/`](results/) | The last sweep: which hypotheses hold at which tier of the design | `./run.sh` writes it |

One command, under a minute, no hardware:

```bash
git clone https://github.com/YobieBenjamin/safety-governor
cd safety-governor && ./run.sh
```

It creates a virtual environment, installs the two dependencies, runs the hypothesis suite
against the tiers of the design, simulates the RTL, regenerates the Verilog, and writes
`results/report.md`.

## The design in one paragraph

Each GPU slot on the baseboard gets a governor. The governor holds its own fused identity,
its own copy of the signed rulebook, and its own log. It verifies the GPU's
confidential-computing attestation locally against pinned reference values, releases the
model's decryption key only to a verified enclave, mints the one-time tickets that endpoints
demand before they act, keeps the budgets, counts the tokens, and signs what the verified
runtime presents. It has three physical levers over its GPU that need nothing from the GPU
vendor: the power-brake pin, the reset pin, and the slot's power enable. It has authority
over the three places on the board where the GPU's traffic already passes a switch: the
NVSwitch ports (NVLink to other GPUs), the PCIe switch ports and ACS (the host, peers,
storage), and the DPU's filter tables (RDMA across nodes). All governors in a rack share two
wires: a **halt loop**, a dumb current loop that any governor can open and that halts every
GPU when it opens or breaks, and a **message fabric**, an authenticated out-of-band network
for rosters, epochs, heartbeats, budgets and log checkpoints. Nothing in the GPU changes.
Nothing in CUDA changes.

## Plain-language guide to every feature

| Feature | What it is for | In plain words |
|---|---|---|
| One governor per GPU slot, on the board | Authority has to be local and physical | A lifeguard per pool, not one for the whole water park |
| Added through the rack's boards | It has to fit the hardware that exists | The security office rents the room next door; it does not ask the landlord to rebuild the building |
| Fused identity and DICE key | The chip's key is derived from what it booted | A house key cut from the shape of the house. Change the house and the key stops fitting |
| Local attestation verifier | The governor checks the GPU's signed report itself, against values it was given | The bouncer carries the photo book; he does not phone head office for every face |
| Policy image and epoch | The rules are signed by several people; every edition has a number | A rulebook with an edition number. Tickets printed under an old edition are void |
| Ticket minting and budgets | Every action gets a one-time permission bound to its exact fields; shared allowances are reserved before use | One seat, one show, torn at the door; one cashier per cash drawer |
| Heartbeat | The policy authority has to keep saying "still here" | The dead man's switch on a train. Let go and the brakes come on |
| Halt loop | A physical circuit through every governor in the rack | The fire-alarm loop. Pull any station and every bell rings. Cut the wire and every bell rings too |
| Message fabric | Governors talk to each other over a private network with signed messages | The building's intercom, separate from the Wi-Fi the tenants use |
| Roster | GPUs and governors verify each other before a job starts | Roll call with ID badges before the bus leaves |
| Power brake, reset, slot power | Three ways to stop a GPU that need nothing from the GPU vendor | The circuit breaker in your house. The appliance does not get a vote |
| Switch-port authority | The governor decides which NVSwitch, PCIe switch and NIC ports are open, and to whom | The doors between buildings only unlock for people on the roll; the switch is the door, and the governor holds the key |
| Output signing | What the verified runtime presents is hashed and signed with the chip's key | The courier signs for the package. It proves who handled it, not what is inside |
| Metering | Tokens, cycles and bytes per model | The taxi meter |
| Signed log | Every decision is appended to a hash chain with signed checkpoints, cross-linked between governors | The flight recorder, and each governor keeps a copy of its neighbors' last page |
| Fused-off debug | JTAG and scan are permanently disabled before the chip ships | The service hatch is welded shut after the factory |

The full table, with the reason behind each feature and what it does not do, is in
[`docs/09-analogies.md`](docs/09-analogies.md).

## What it does not do

It does not understand the model's words, and it does not try to. It does not stop a harmful
sentence over an allowed channel. From the board it governs traffic at the *link* level (which
ports are open, to whom) rather than at the *descriptor* level inside the GPU; the residual
that leaves is a legitimate peer on an open port doing something the rulebook did not
anticipate, and the design says so rather than hiding it. Its guarantee holds inside a
declared boundary and exactly as far as the [assumptions register](docs/06-assumptions-register.md)
holds. Read [`docs/00-objectives.md`](docs/00-objectives.md) for the full list of non-goals.

## Status

Design and functional model: complete for the rack tier (plan of record) and the board-only
fallback; the integrated tier (governor hooks inside the GPU) is specified as a future ask and
not required. RTL: the hard-core control blocks, simulated and emitted as Verilog; the crypto
engines are specified as integrated IP (OpenTitan-class SHA-256, HMAC, AES, ECDSA P-256 on
OTBN, TRNG) and not re-implemented here. Silicon: flow configured for a sky130
multi-project-wafer shuttle; not yet taped out. The honest state of every claim is in
[`results/report.md`](results/report.md).

## License

Documentation: CC BY-NC 4.0. Code and RTL: PolyForm Noncommercial 1.0.0. Attribution required;
commercial use needs a separate license. Contact: yobie AT ieee DOT org.
