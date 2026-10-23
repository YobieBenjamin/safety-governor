# The plugs, in plain English

This is the version for someone who has never held a circuit board. The engineering versions are `01` to `04` in this folder, and the one-page scorecard is `COMPLIANCE-MATRIX.md`.

The governor is my chip that says no. It sits outside the AI model, next to the GPUs that run it, and it can stop them. For that it has to plug into servers that already exist. A server maker or an NVIDIA engineer will ask two questions: where does it plug in, and does it speak the languages our parts already speak? This work answers both, as far as public documents let anyone answer them.

## The words

**DC-SCM (Datacenter Secure Control Module).** Many new servers have a slot for a small card that holds the server's caretaker computer, the one that watches temperatures and lets an admin reboot the box remotely. The Open Compute Project (OCP) made that card a standard so any vendor's card fits any vendor's server.
*Everyday version:* the standard-size slot for a car radio. Any radio that follows the standard fits any car that follows it. I want the governor to be a radio that fits the slot.

**DC-SCI (the connector on that card).** The 168 gold fingers on the card's edge, each with a job: power, ground, data buses, a few control wires.
*Everyday version:* the pins on the radio's plug. Each pin is a wire to something in the car: power, speakers, the antenna.

**LTPI.** A fast two-way serial link on that connector. Instead of one wire per signal, it packs dozens of on/off signals into a stream and unpacks them on the motherboard.
*Everyday version:* a pneumatic tube in an old department store. You do not run a separate string to every counter; you put the notes in a canister and send it down the one tube.

**PCIe PERST#.** One wire on a PCIe card's edge that holds the card in reset while it is pulled low.
*Everyday version:* holding down the reset button on a game console. While you hold it, nothing runs. Let go too early, before the power has settled, and the console can boot into a mess.

**PWRBRK# (the power brake).** Another wire on the card's edge. Pull it and the card slows itself down hard to save power. NVIDIA GPUs honour it.
*Everyday version:* the speed limiter a rental company fits to a van. The driver can floor it; the van still will not go fast.

**SMBus.** A slow, two-wire management bus. The GPU has a little mailbox on it where a caretaker computer can read temperatures and set a power cap.
*Everyday version:* the service hatch on a vending machine. Not how you buy a snack, but how the technician checks the machine and changes its settings.

**SPDM.** A public standard for one chip to prove to another who it is and what software it booted, with signatures.
*Everyday version:* a bouncer checking ID, and then asking a question only the real person could answer. The ID is the certificate. The question is a fresh random number that the chip has to sign with a key that never leaves it. A photocopy of yesterday's answer does not work.

**nvtrust.** NVIDIA's public toolkit for checking a GPU's signed report about itself, with a real sample report included.
*Everyday version:* the manufacturer publishing the hologram guide for its own banknotes, plus one genuine note to practise on.

**NDA and members-only.** Some of the documents that decide the details are not public. NVIDIA's board design guide is under non-disclosure agreement. The PCIe card rulebook is sold to members.
*Everyday version:* the building code is public, but the landlord's wiring diagram for this particular building is in a locked drawer.

## What I designed and tested

1. **Where every pin goes.** All 85 of the governor's pins have a row in a table that says which gold finger it lands on, or which LTPI channel, or that it stays on the governor's own card, with the public document for each. A checker program refuses the table if a pin is used twice, a voltage does not match, a control wire is missing, or a row has no source. I planted 18 different mistakes in copies of the table and the checker caught every one.
2. **The reset and brake timing.** I took the governor's real reset logic (the hardware description that becomes the chip) and ran it in a simulator against the public timing numbers. It broke three rules: it let go of reset at the same instant it turned power on, it could let go of reset after only 3 microseconds instead of 100, and it had no way to notice the GPU's power failing on its own. I wrote a small add-on block that fixes all three, without slowing the brake by even one clock tick, and five deliberately broken versions of the add-on were each caught.
3. **The halt time.** Pulling the brake reaches the wire in about 0.34 milliseconds even when the signal travels over LTPI, inside my 1 millisecond promise.
4. **SPDM.** I wrote the governor's side of the SPDM conversation and tied it to the governor's real boot measurements and boot-derived keys. Then I built DMTF's own reference software from source and made them talk, both directions, in two versions of the standard. DMTF's official test suite for this exact job ran 781 checks against it: all pass. I also flipped single bits in the governor's signatures on purpose, and DMTF's code rejected them, which is how I know the passes are real.
5. **NVIDIA's report.** The governor now reads NVIDIA's real GPU report format. On NVIDIA's own public sample it agrees with NVIDIA's own checker on every field, on the signatures, on a tampered copy, and even on the list of 20 places where the sample does not match NVIDIA's own reference files.

## What I could not do, and exactly why

- **The DC-SCI pin spreadsheet.** OCP keeps the official pin list in a spreadsheet. Every way I tried to open it from here showed only the cover page and the change log. I took the pin numbers from a public spec by Lenovo and Cloudflare that says it follows that spreadsheet exactly. Someone needs to check them against the spreadsheet itself.
- **The opencompute.org files from the command line.** The network here blocks that site for downloads (an HTTP 403 from the proxy). I could read the PDFs as text through a web reader, which is why some answers are section-level, not quote-level.
- **The PCIe card rulebook (CEM).** Members only. Every number I used comes from a public place that quotes it, mainly the Linux kernel, and I name each one. How fast a GPU actually slows down after the brake is not public anywhere; the only number I found is from a server maker's patent, 5 milliseconds. So my 1 millisecond promise is about the wire, not the GPU.
- **NVIDIA's HGX board design guide and its SMBus command book.** Under NDA. I did not read them and I claim nothing against them. They decide, for NVIDIA's own 8-GPU boards, whether each GPU has its own reset and brake wire. Public documents say the reset wires come in at most three groups and the brake is one wire for the whole board.
- **LTPI's rule for a broken link.** The standard says that when the link drops, the far end keeps the last values. For a governor that is the wrong way round: a dead governor would leave its GPU running. I wrote the rule the motherboard has to follow instead, and showed the difference in a model, but it needs the server maker's logic on the motherboard. That is open.
- **Four of the governor's pins have no public home on the connector:** the two wires for one kind of switch management (MDIO), and the two for the network card's own management port. They are flagged in the table, with the workaround.
- **The governor is missing three kinds of pins this plan needs:** a reset input for its own PCIe link, a power-good input per GPU slot, and the eight wires for its own LTPI link. They are proposed, not added, so nobody's existing work changes under them.
- **The fix is not in the chip yet.** The reset add-on is written and tested on its own but not wired into the governor's top-level design. Other people are proving properties of that exact part of the design right now, and changing it under them would waste their work. It is the next step.
- **NVIDIA's full check.** NVIDIA's checker wants to ask NVIDIA's servers whether a certificate was revoked. No network route here, so it stops. The governor itself never has that network either; it relies on a signed revocation list. NVIDIA's own reference files that come with the sample carry a signing certificate that had already expired on the day I ran this, so even NVIDIA's code rejects them offline.
- **SPDM over real wires.** On a real board SPDM rides another standard (MCTP over SMBus, or PCIe DOE). I did not model those. The encrypted-session half of SPDM is not implemented either, which is why 48 of DMTF's test cases did not run.

## What didn't work along the way

| What I tried | What happened | What I did instead |
|---|---|---|
| Download the DC-SCM PDFs with the command line | proxy said 403 for opencompute.org | read them as text with a web reader |
| Open the OCP pin spreadsheets (four different URLs) | only the cover tab and change log came back | used the Argus spec's transcription; flagged as open |
| Read the PCIe power-sequencing table in OCP NIC 3.0 | the text reader stopped before that chapter | used the Linux kernel and LKML quotes of the CEM |
| Find a public PWRBRK# response time | none from NVIDIA or PCI-SIG; a Dell patent had only design examples | recorded the Inspur patent's 5 ms as the only public figure |
| Search GitHub for the pin list | the GitHub search API is not open to this session | none needed once Argus was found |
| Install NVIDIA's verifier | its pinned lxml would not build on Python 3.13; a newer signxml clashed with its cryptography pin | installed with the pins loosened, logged in the oracle script |
| Run NVIDIA's verifier end to end | it stops at the OCSP revocation check, no network | drove NVIDIA's classes directly |
| Check NVIDIA's test reference files' signatures | NVIDIA's own code: "certificate has expired" | recorded; golden-value matching shown only against the sample itself and as a mismatch against NVIDIA's files |
| First SPDM run against DMTF's test suite | 5 failures in one test case: my responder accepted forbidden option combinations | fixed; second run 781 pass, 0 fail; the failing log is kept |
| Measure the CEM timing with a cycle-by-cycle Python testbench | four minutes per run on this shared machine | moved the power model into the simulated hardware; about 8 seconds of CPU per run |
| My first hand-made "bad" timing trace for the checker's self-test | it was not actually bad, so the checker rightly passed it and my test failed | fixed the trace, so the test checks what it says |
| Trust spdm-emu's exit code | it exits 0 even when the chain matches no trusted root | the harness reads its log for the no-authority line, and a run proves it |
