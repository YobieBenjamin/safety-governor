# 29. The claim experiments: protocol, pre-registered

*Status: APPROVED by Yobie Benjamin on 28 October 2026: the pass and fail rules (sections 2.4 and 3.4), the four
exit-register rows (Appendix A) and the trusted base (section 2.1). Nothing in this document had been run when it was
approved. It is binding from that approval; its SHA-256 is written in the first line of every run's log. Any change
from now on is an amendment: dated, with its reason, added at the end, never an edit of the text above it.*

The claim is in `GOAL.md` (https://github.com/YobieBenjamin/hardware-and-silicon/blob/main/goals/GOAL.md): two
properties, held under three conditions. Two experiments test it.

- **Experiment A, the formal model.** One mathematical model of a server, a rack and a data center, with Property 1
  and Property 2 as theorems, against an attacker who controls everything except the chip. It answers: if the parts
  behave as specified, can the claim be broken at all?
- **Experiment B, the attacker simulation.** A large population of cooperating attacking agents, run against the
  rulebook in `govsim`, measuring how much harm gets through in steps the rules allow. It answers condition 2: do many
  harmless-looking steps add up to a harmful act, and by how much?

Think of A as the structural engineer's calculation and B as the crash test. A shows the frame cannot fail if the steel
is as specified; B drives cars into it and measures the damage. Neither alone is enough, and each catches what the
other misses.

## 1. What must be in place before either experiment runs

A result is only evidence if the test could have failed and someone other than its author can check it. Every item
below is a prerequisite; the first run does not start until each one is marked done.

| # | Prerequisite | Why | Status |
|---|---|---|---|
| R1 | **A frozen target.** The experiments test one named commit of `main` in each repository, recorded by full hash in every log. | A result about moving code is a result about nothing. | `main` is `e207208` (safety-governor) today; freeze at start |
| R2 | **`main` protected.** | No one, person or agent, can change the target under the experiment. | DONE (28 Oct, PROTECT: PASS) |
| R3 | **This protocol approved before any run.** Pass and fail rules fixed in advance, approved by Yobie, committed, hash in the first log. | So a result cannot be reinterpreted after it is seen. No AI is the final judge. | DONE (approved 28 Oct) |
| R4 | **The exit register complete for the model's exits** (condition 1). Every exit in `govsim/gpu.py` `EXITS` has a register row, and the register test understands the host-side exits. | Property 1 is only as strong as the list of exits. The formal model takes the register as input: every `unaccounted (NDA)` row becomes a named assumption of the theorem. | rows checked by Yobie 28 Oct; on exp/p2, P2 to rerun |
| R5 | **Controls that must fail.** Each theorem is also run on deliberately broken models (a removed guard, a lowered threshold, a missing exit) and must produce a counterexample. Each simulation metric is also run with a deliberate leak (fleet budgets off, definitions engine off) and must detect it. | A test that cannot fail proves nothing. These controls show the instrument works. | to build with each experiment |
| R6 | **Pinned environment.** Python version, z3 version (5.3.x), every package by hash, random seeds, machine (Mac mini, External_4TB). Logged in every run. | So anyone can rerun and get the same numbers. | to do at freeze |
| R7 | **Every result recorded, pass or fail.** Each run writes a dated folder (inputs with hashes, outputs, verdict) under `work/overnight/` and a hash-pinned copy under `archive/claim/`; each result is appended to `EXPERIMENTS.md` with its date. Failed and abandoned runs are kept. | Nothing is hidden. | standing rule |
| R8 | **Independent check.** Before any result is called a result, a fresh reviewer who has not seen this work checks the model and the harness against `GOAL.md`. Later, the OpenAI audit. | The builder is not the judge. | after first results |
| R9 | **Responsible disclosure.** A failing result that is a working attack stays private (`DISCLOSURE.md`) until its fix is merged; the fact that it failed is recorded at once. | A found hole is an attack plan. | standing rule |
| R10 | **Stop rules and budgets.** Each run has a time limit and a heartbeat; a run that hits its limit is recorded as "did not finish", never as a pass. | So a hang is never mistaken for a result (as L4's loop was). | built into the launchers |

## 2. Experiment A: the formal model of server, rack and data center

### 2.1 What is modelled

- **Scale is a parameter, not a number.** Servers, GPUs, racks, sites, actions, keys and budget keys are uninterpreted
  sorts, as in `proofs/core_invariants.py`, so the proof covers any number of each. Small fixed instances are checked
  separately as a cross-check (bounded model checking).
- **The parts.** Governor chips; the endpoints that carry out effects (their ticket check); the levers (throttle,
  reset, power cut); the halt loop; the fabric between chips; the per-site heartbeat signers; the fleet ledger
  replicas; the key holders and their quorum; the rulebook editions; the exits of each GPU (from the exit register).
- **The trusted base, stated plainly.** The attacker controls everything except: the governor silicon and its fused
  keys; the endpoint's ticket check; the lever wiring; and fewer than the threshold of key holders. If any of these is
  wrong in practice, the theorem does not apply, and the model says which assumption failed.
- **The attacker.** Controls every host, GPU, model, GPU firmware, BMC, DPU and operator console; the network between
  chips (it can drop, delay, reorder and replay any message, but not forge a signature or a MAC); any number of
  requests, sessions, workloads and accounts; any timing; up to threshold minus one of the key holders in any
  governance group; any number of fleet ledger replicas (which, with all replicas required, can only refuse).

### 2.2 The theorems

| # | Theorem | In words |
|---|---|---|
| T1 | **Property 1.** Every effect at every endpoint, at every site, corresponds one-to-one to a ticket minted by a governor under the edition in force at that endpoint, from a rule that allowed exactly that action with exactly those parameters, and the sum of effects per budget key across the whole data center never exceeds its cap. | No consequential effect without authorization, and budgets hold across the fleet. |
| T2 | **Property 2.** If a stop is ordered or a stop condition occurs (lost heartbeat, broken loop, tamper, straggler on old rules), every governed GPU in scope is stopped within the stated time and stays stopped until an authorized clear, whatever the attacker does. | The stop cannot be prevented. |
| T3 | **Condition 3.** With fewer than the threshold of key holders, no edition change, no lowering of a floor, no clear and no switch-off can happen; with at least the threshold of honest key holders, recovery is always possible. | Keys and people cannot be captured singly. |
| T4 | **Boundary.** A failure or a capture in one data center cannot stop or capture another. | It is not a global kill switch. |

The stated time in T2 is written in the model as named constants taken from the evidence: the halt loop (simulated
worst case 317 microseconds against a 1 millisecond budget, `hw/loop/results.md`), the heartbeat expiry, and the
straggler window. The theorem is proved for symbols, then evaluated with those numbers.

### 2.3 Method

1. Safety parts (T1, T3, T4): inductive invariants proved with z3, as the existing proofs are.
2. The timed part (T2): a clock variable per stop condition, and an invariant that bounds "time since the stop
   condition" until the GPU is stopped. Proved by induction, cross-checked by bounded model checking on small
   instances.
3. The link to the code: `govsim` traces from the whole test suite are replayed through the new model (extending
   L4's trace conformance), so the model and the simulator are checked against each other.
4. The controls (R5): each theorem is rerun on at least five broken models and must fail each with a counterexample.

### 2.4 Pass and fail

- **PASS:** T1 to T4 proved for any size, the small instances agree, the trace replay is clean (except the declared
  fault injections), and every broken model produces a counterexample. The result is stated as "proved, assuming"
  the trusted base and the open register rows, listed by id.
- **FAIL:** any counterexample on the real model. The counterexample is recorded the same day. It is then classed as
  a model error (the model is wrong about the code) or a design flaw (the design allows it). A design flaw goes
  through the fix pipeline (failing test first, fix, full suites, proof again).
- **INCONCLUSIVE:** a solver timeout. Recorded as such, never as a pass.

## 3. Experiment B: cooperating attackers against the rulebook (condition 2)

### 3.1 The setting

A `govsim` fleet: several sites, racks per site, servers per rack, the shared fleet budgets and the definitions
engine on, with a rulebook that covers four kinds of harm:

| Harm kind | Measured as | Example harm |
|---|---|---|
| Money | value moved to destinations outside the allow-list, or above per-destination caps | many small payments to one account |
| Data out | bytes leaving through any exit (all of `EXITS`, the host-side exits included) | weights or data out in small pieces |
| Commands to machines | count and size of commands to an actuator class | many small valve or grid changes |
| Rule changes | any change to the rulebook, the budgets or the lists | the attacker loosening its own limits |

### 3.2 The attackers

`K` agents that share one plan and pool what they learn. `K` runs 1, 10, 100, 1,000, 10,000 and 100,000. They control
hosts, models, sessions, workloads, accounts and destinations across servers, racks and sites. The strategy library,
each one a separate, named, seeded generator:

1. **Splitting**: one harmful act cut into many allowed pieces, across sessions, servers, racks and sites.
2. **Rewording**: the same place, account, amount or target written another way (extra coordinates, text for numbers,
   another unit, another encoding, Unicode look-alikes), aimed at the definitions engine.
3. **Timing**: requests at the edges of rate windows, during edition changes, across clock skew, and as concurrent
   races.
4. **Pooling and identities**: many workloads, accounts and destinations that each stay under their own limit.
5. **Cover traffic**: harmful pieces mixed into large volumes of honest traffic.
6. **Probing**: an adaptive search that learns from every refusal which requests pass, and spends its effort there.
7. **Every exit**: data pushed through every exit in `EXITS`, including NVLink-C2C, the host NICs and the BMC NIC.
8. **Retry and replay**: refused requests resubmitted, tickets replayed, partial failures exploited.

An honest population runs alongside to measure the cost side: how often legitimate work is refused.

### 3.3 What is measured

For each harm kind, for each `K` and each run length: the total harm that got through (`L`), the ratio to the
rulebook's cap for that harm, how `L` grows as `K` grows, the time until the first alarm, and the false refusal rate
for honest users. Each run has a fixed seed; each point is repeated with at least five seeds.

**Scale, honestly stated.** The Mac can simulate perhaps millions of requests per run, not trillions of tokens. The
result therefore has two parts: what was measured (up to the largest `K` and run length that finished), and an
extrapolation to the GOAL.md scale (millions of users, trillions of tokens) stated as a model with its assumptions,
never presented as a measurement.

### 3.4 Pass and fail

- **PASS for a harm kind:** for every `K` and run length, `L` stays at or below the cap that kind's fleet budget sets,
  and `L` does not grow with `K` (cooperating attackers get no more than one attacker). Zero rewordings bypass the
  definitions engine.
- **FAIL for a harm kind:** any run where `L` exceeds the cap, or where `L` grows with `K`. The measured growth is
  reported (for example, "each additional attacker adds X"), with the strategy that caused it.
- **Leakage within the cap is reported, not hidden.** A harm kind can pass (the cap holds) while the cap itself lets
  through more than anyone would want. The report gives the number either way, so a person can judge whether the
  rulebook's caps are right. The chip does not make an allowed act harmless (`GOAL.md`).
- **Controls (R5):** with the fleet budgets switched off, the harness must measure `L` growing with `K`; with the
  definitions engine switched off, rewording must get through. If the controls do not show the leak, the instrument is
  broken and no result is reported.

### 3.5 If it fails

Every failure is recorded the day it is found and comes with its remedy class: a missing definition (add it to the
definitions engine), a budget that is per-server where it should be fleet-wide (move its owner to `fleet`), a rate
window that resets at an edge (switch to a sliding window), a missing exit (add the row and the lever), or a rulebook
cap set too high (a decision for a person, not a code fix). Each fix goes through the fix pipeline and the experiment
is rerun on the fixed commit.

## 4. Exit paths: yes, more tests are needed, in three places

1. **The register (P2, condition 1).** The three host-side exits added by the audit 3 fixes (`nvlink_c2c`, `host_nic`,
   `bmc_nic`) have no register rows, so experiment P2 fails. Appendix A drafts them from NVIDIA's public documents for
   Yobie to check. P2's test also needs one change (Appendix B): it treats the new "host" kind of exit as if it were
   "bricked by policy", which is wrong.
2. **The formal model (Experiment A).** Exits enter the model as a set taken from the register. A `governed` row is a
   lever the model may use; an `unaccounted (NDA)` row becomes a named assumption of T1. So the result says exactly
   which exits it rests on.
3. **The simulation (Experiment B).** Strategy 7 pushes data through every exit, alone and in combination, at fleet
   scale, to measure that the one shared host allowance holds when the host-side exits are used together and
   concurrently.

## 5. Order of work

1. Yobie checks Appendix A and approves this protocol (R3, R4).
2. P2 rerun with the three rows and the test change; P2 must pass before A starts.
3. Freeze the target and pin the environment (R1, R6).
4. Experiment A: model, controls, proofs, trace replay. Results recorded.
5. Experiment B: harness and controls first, then the `K` sweep, smallest first. Results recorded.
6. Fresh independent review (R8), then the OpenAI audit.

---

## Appendix A. Exit-register rows X31 to X34 (P2), checked by Yobie on 28 October 2026

Drafted 28 October 2026 from NVIDIA's public documents by a research pass; every claim below names its source. Each
row is in the register's format (`docs/research/exit-register.md`). The BMC NIC is split in two rows because one part
is governed by a public lever and the other is not settled publicly. Please check especially the status column: it is
the judgment that matters.

| id | path | tray | direction | carries | status | lever_or_how | model_exit | class | from_module | undo_paths | evidence | source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X31 | GPU to the Grace CPU over NVLink-C2C inside the GB200 superchip: coherent CPU loads and stores to GPU HBM, GPU access to Grace LPDDR5X, ATS address translation | NVL72 | both | Host-memory traffic, unified memory migration, copy-engine bulk transfers of pageable memory: anything the Grace operating system can reach | unaccounted (NDA) | No public lever stops, throttles or encrypts C2C. `nvidia-smi c2c` (status, error counters, power state), NVML `nvmlDeviceGetC2cModeInfoV` (`isC2cEnabled`) and the NVML C2C field values only read it; the Grace NVLINK-C2C0 and C2C1 performance counters meter it. The Grace SMMU (`iommu.passthrough=0`) covers only the ATS-translated part (C2C0); the non-ATS part (C2C1) is not shown to pass it. No NVIDIA document says confidential computing covers C2C. The model stands in with one shared host allowance and output sealed to the egress endpoint (design, `docs/research/host-side-exits.md`) | nvlink_c2c | witness | NDA | Host kernel (SMMU mode on the kernel command line); GPU and Grace firmware | VERIFIED (link, meters), UNKNOWN (any stop lever) | S22 S23 S24 S25 S26 S27 |
| X32 | NIC or DPU reading or writing GPU memory directly: GPUDirect RDMA, GPUDirect Storage, PCIe peer-to-peer through the GPU's BARs, bypassing host memory | both | both | Tensors, gradients, activations, weights, checkpoints, any registered buffer | governed | No GPUDirect path exists without `nvidia-peermem` or DMA-BUF registration; NVIDIA states GPUDirect RDMA is incompatible with an IOMMU doing any translation other than 1:1, so IOMMU translation on stops it; PCIe ACS peer-to-peer request redirect sends peer traffic up to the root complex and its IOMMU; BlueField zero-trust (`mlxprivhost`) stops the host taking port ownership; the PCIe switch port (X03) and the DPU OOB port (X05) are the external levers. Every one is a host-side setting the governor must attest (measured boot), not own | host_nic | witness | NDA | Host root (`modprobe nvidia-peermem`, `iommu.passthrough=1`, GPU Operator `driver.rdma.enabled`); BIOS (ACS and IOMMU defaults); the BlueField Arm OS or BMC (`mlxprivhost` back to privileged); NIC firmware over NC-SI | VERIFIED (mechanism, IOMMU, peermem, zero-trust), PARTIAL (ACS) | S28 S29 S30 S31; X03 X05 |
| X33 | The BMC's dedicated management port: one 1 GbE RJ45 per compute tray, plus two BlueField-3 BMC ports per GB200 tray; one per HGX server | both | both | Redfish, IPMI, SNMP, KVM video, virtual media into the host, GPU telemetry read over SMBPBI, firmware images (Redfish UpdateService), log dumps | governed | Isolate the port on a dedicated, firewalled management network (NVIDIA's recommendation); the BMC's Services, Media Redirection and System Firewall settings; "Redfish Disable Host Interface" closes the operating-system-to-BMC path. A lever on the network, not on the board | bmc_nic | witness | NDA | Anyone holding BMC admin credentials; the operator; the host through the Redfish host interface or in-band IPMI if left on; a BMC firmware update | VERIFIED (port, services, isolation guidance) | S32 S33 S34 S35; X28 |
| X34 | The BMC reaching the network through a host NIC over NC-SI sideband, and any BMC read of host or GPU memory | both | both | The same as X33, by a path that does not appear on the management network | unaccounted (NDA) | The DC-SCM specification carries two NC-SI interfaces on the DC-SCI connector, and ConnectX-7 accepts BMC-set protections (NC-SI "Set Protection Options"), but no public document says whether DGX, HGX or GB200 boards wire NC-SI to their NICs, or how to turn it off; no public document says whether the AST2600's PCIe endpoint can read host or GPU memory on these boards (the public ASPEED flaw, CVE-2019-6260, runs the other way, host into BMC, on older parts) | bmc_nic | witness | NDA | The BMC; NIC firmware; the board vendor's CPLD and BMC images | UNKNOWN (wiring, DMA) | S36 S37 S38 S39; X21 X28 |

**What would settle the open rows.** X31: NVIDIA under NDA, on what `isC2cEnabled=false` means and whether a C2C
firewall or meter with a governor-written budget exists (already a listed NVIDIA dependency in
`docs/research/host-side-exits.md`); a search of NVIDIA's open GPU kernel modules for C2C controls is a cheap public
check still to do. X34: the HGX design guide DG-10333-001 and the GB200 tray design guide (NDA); NVIDIA's OpenBMC
device tree for GB200 (public, still to check for `ncsi` and `xdma` nodes).

**Counts after these rows:** `governed` 16, `recorded-gap` 2, `bricked` 2, `unaccounted (NDA)` 14, `unaccounted` 0.

Sources to add to the register's key:

- S22 NVIDIA, Grace Hopper Superchip architecture in depth: https://developer.nvidia.com/blog/nvidia-grace-hopper-superchip-architecture-in-depth/
- S23 NVIDIA Grace performance tuning guide, hardware counters (NVLINK-C2C0 and C2C1): https://docs.nvidia.com/dccpu/grace-perf-tuning-guide/measuring-performance.html
- S24 NVIDIA Grace performance tuning guide, OS settings (`iommu.passthrough`): https://docs.nvidia.com/dccpu/grace-perf-tuning-guide/os-settings.html
- S25 nvidia-smi documentation (`nvidia-smi c2c`): https://docs.nvidia.com/deploy/nvidia-smi/index.html
- S26 NVML device queries (`nvmlDeviceGetC2cModeInfoV`) and field values: https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html , https://docs.nvidia.com/deploy/nvml-api/group__nvmlFieldValueEnums.html
- S27 NVIDIA Trusted Computing Solutions release notes R590 (CC support list, no GH200 or GB200): https://docs.nvidia.com/590trd1-trusted-computing-solutions-release-notes.pdf
- S28 NVIDIA GPUDirect RDMA documentation (root complex, IOMMU, nvidia-peermem, security): https://docs.nvidia.com/cuda/gpudirect-rdma/
- S29 NVIDIA GPU Operator, GPUDirect RDMA and Storage (DMA-BUF or nvidia-peermem): https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/24.6.2/gpu-operator-rdma.html
- S30 NVIDIA BlueField modes of operation (zero-trust): https://docs.nvidia.com/networking/display/bluefieldbsp480/modes+of+operation
- S31 NVIDIA MFT `mlxprivhost`: https://networking-docs.nvidia.com/mftswum/4.36.0/mlxprivhost-nic-configuration-by-the-host-restriction-tool-zero-trust-mode
- S32 DGX H100/H200 user guide, security (dedicated BMC port, isolated network): https://docs.nvidia.com/dgx/dgxh100-user-guide/security.html
- S33 DGX H100/H200 user guide, using the BMC (Services, Media Redirection, System Firewall): https://docs.nvidia.com/dgx/dgxh100-user-guide/bmc.html
- S34 DGX H100/H200 firmware changes ("Redfish Disable Host Interface"): https://docs.nvidia.com/dgx/dgxh100-fw-update-guide/firmware-changes.html
- S35 DGX GB rack scale systems user guide, hardware (BMC and BlueField-3 BMC ports per tray): https://docs.nvidia.com/dgx/dgxgb200-user-guide/hardware.html
- S36 OCP DC-SCM 2.0 (NC-SI on the DC-SCI): https://www.opencompute.org/documents/ocp-dc-scm-2-0-ver-1-0-pdf
- S37 NVIDIA ConnectX-7 firmware 28.36.2050 (NC-SI Set Protection Options): https://docs.nvidia.com/networking/display/ConnectX7Firmwarev28362050/Changes+and+New+Features
- S38 NVD CVE-2019-6260 (ASPEED AHB bridges, host into BMC): https://nvd.nist.gov/vuln/detail/cve-2019-6260
- S39 HPE GB200 NVL72 QuickSpecs (AST2600, NVIDIA OpenBMC): https://www.hpe.com/us/en/collaterals/collateral.a50009224enw.html

## Appendix B. The change to P2's test

`tests/test_h20_exits.py` `test_register_matches_the_models_enumeration` knows three kinds of exit (True governed,
False recorded gap, None bricked by policy). The audit 3 fixes added a fourth, `"host"`: no switch of its own, metered
against the one host allowance and sealed to the egress endpoint. Today the test sends `"host"` down the `None` branch
and demands `bricked`, which is wrong. The change adds a branch: a host-side exit must have at least one row; each row
is `governed` (with VERIFIED or PARTIAL evidence) or `unaccounted (NDA)`; and an NDA row is reported as an assumption
the model's host allowance stands in for, the same way the bricked-by-policy exits are reported today. The test is not
weakened: every existing branch is unchanged, and a host-side exit with no row still fails.

---

## Amendment 1, 28 October 2026, approved by Yobie Benjamin

*Made before any attacker run of Experiment B; only its controls had run. Approved by Yobie Benjamin on 28 October 2026
at about 22:20 UTC ("Stop it and rerun with a recorded fix").*

**What happened.** The official run (overnight `claim-20261028T190518Z`) started Experiment B at 19:23 UTC. Its
controls ran first, one after another. The control with the fleet budgets off at K = 100,000 took about 140 minutes on
one Mac mini core and showed the leak it must show (7,995 dollars an hour against a 2,000-dollar cap). The code then
would have run the sweep largest K first: 95 runs at K = 100,000, each about 2.5 hours, before any smaller K. At that
rate the 14-hour limit would have stopped the sweep with about half the K = 100,000 runs done and no run at any smaller
K, so most strategies would have had no result at all.

**What changes.**

1. **Smallest K first.** Section 5 of this protocol already says the K sweep runs smallest first. The code ran it
   largest first; that was a deviation from the approved text, now corrected. `planned_jobs` in
   `govsim/claim_attack_sim.py` orders the runs by K, smallest first.
2. **One seed at K = 100,000.** Section 3.3 asks for at least five seeds per point. At K = 100,000 each run takes
   about 2.5 hours on the Mac, so that point runs one seed (seed 1) per strategy: 19 runs. Every other K keeps five
   seeds. Five seeds at K = 100,000 are to be run later on larger hardware, and the report says plainly that this
   point rests on one seed.
3. **Controls at K = 1 and K = 10,000.** The controls run at K = 1 and at the largest K up to 10,000, instead of at
   K = 100,000. The K = 100,000 control from the stopped run is kept in its record and reported as extra evidence.

**What does not change.** The harm kinds, the strategies, the caps, the run length (3 simulated hours), the pass and
fail rules of section 3.4, the requirement that the controls leak, and the 14-hour limit.

**The stopped run.** Its `B.json` (controls only) stays in its overnight folder, marked as stopped by this amendment.
Experiment A's official result from that run (166 of 166) stands: nothing in this amendment touches the formal model,
and A is run again on the new target as a check.

**Expected time.** 494 runs: about 1.5 to 3.5 hours for K up to 10,000 on 13 workers, then about 5 to 6 hours for the
19 runs at K = 100,000. About 7 to 9 hours in all.

---

## Amendment 2, drafted 29 October 2026, NOT YET APPROVED

*A clarification of section 3.4, drafted after the amendment 1 run finished and after its data had been seen, which is
why it is recorded here as a draft for the independent review (R8) and for Yobie Benjamin, and is not applied by the
code.*

Section 3.4 fails a harm kind when `L` grows with `K`. The code's `grows_with_k` fails a kind only when the growth also
ends above the cap. In the amendment 1 run money rose from 1,499 to 1,995 dollars and data out from 2 MiB to 8 MiB,
both under their caps and both flat from K = 1,000 (money) and K = 10 (data) on; under the text both fail, under the
code both pass. The draft rule: a harm kind fails if any run is over its cap, or if harm is still rising between the
two largest K (within a tolerance the review fixes before looking again), or if harm at any K exceeds what the rulebook
would let one requester with the same total number of requests do. Under a 1 percent tolerance the data-out probing
strategy still fails (a 2.8 percent rise between K = 10,000 and 100,000, towards the ceiling four other strategies
reach exactly). The tolerance is not to be tuned to the data. Until this is approved, every record reports both the
code's reading and the text's reading, and no reading is called the result.

---

## Amendment 3, 30 October 2026, approved by Yobie Benjamin by running the rerun

*Made after an adversarial audit of the amendment 1 record, before any result was called a result.*

**What happened.** The attacker harness attested every GPU once, at bring-up, and never again. The governor's workload
token and attestation live one hour (`TOKEN_TTL_S`), and the design's only renewal path is for the host to re-attest
and begin the model again. The harness did neither, so from the second simulated hour on every request, honest or
attacking, was refused as `gate.not_attested`. Reproduced on 30 October: with no attacker at all, 60 of 60 honest
payments succeed in hour one and 0 of 120 in hours two and three. Consequences for the amendment 1 record
(`claim-rerun-20261028T223006Z`): each three-hour run was in effect a one-hour run with about one request per attacker;
the honest success rates it recorded (32.8 percent at K = 1 falling to 9.6 percent at K = 100,000) are artefacts, the
estimate within the governed hour being about 98 percent falling to about 29 percent; the timing strategy lost three of
its five window edges; and the caps it reports as held were held within one hour, not three. No run went over its cap,
and the controls leaked as required, so the instrument itself was not broken; the run was shorter than it said.

**What changes.**

1. **The honest host keeps the workload attested.** Every 50 simulated minutes the harness re-attests every GPU and
   begins the same model again on it, as a real host must before the one-hour token expires (`REATTEST_S` in
   `govsim/claim_attack_sim.py`). Verified: with no attacker, 180 of 180 honest payments succeed over three hours.
2. **The record carries its provenance.** Each sweep record now carries the harness commit, the interpreter, the z3
   version and the machine (section 1, rules R1 and R6), which the amendment 1 record lacked.
3. **The harness states section 3.4 as written.** Its docstring misquoted the rule ("beyond the cap"); it now quotes
   the text and names the code's narrower reading as a reading, with amendment 2 pending.
4. **A renewal command is an open design item.** A workload token that can only be renewed by beginning the model
   again is a gap in the design, recorded here for the design log; it is not fixed by this amendment.

**What does not change.** The harm kinds, the strategies, the caps, the run length (3 simulated hours, now governed for
all 3), the order (smallest K first), the seeds (five per point, one at K = 100,000), the controls at K = 1 and
10,000, the pass and fail rules of section 3.4 (with amendment 2 pending), and the 14-hour limit.

**The amendment 1 record.** `B.json` of `claim-rerun-20261028T223006Z` and its partial completion stay in their
folders, marked as superseded by this amendment; its Experiment A result (166 of 166, 13 broken models, 153 falsifiable
checks) stands and A is run again on the new target as a check.
