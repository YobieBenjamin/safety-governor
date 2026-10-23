# ASPIRATION

### An independent hardware boundary for AI actions

*Working draft, 23 October 2026. By Yobie Benjamin.*

> Archived vision document. The original with its figures is `ASPIRATION.docx` beside this file.
> This is the destination the software proof is built to earn: our chip inside a real
> NVIDIA-powered server, with the authority to withhold a protected effect even when the host is
> compromised. The section "The promises we would have to prove" is the acceptance contract the
> strict software simulation must establish first, before any hardware.

## The layers of safety

Everyone is talking about AI safety. Training, evaluations, classifiers, guardrails, monitoring, another model checking the first model. Some of this work is useful. But a list of safety techniques still leaves a hard question: who can make a refusal stick when the machine is about to do something it is not authorized to do?

We start with the layers because our chip has a specific job within them. It cannot replace the people who establish policy or the work of deciding which behavior is dangerous. It should make specified authorization rules compulsory at the point where an action becomes an effect. The layers below are our design framework, consistent with treating AI risk across the system lifecycle. [1]

AI can help identify risk. We will not rely on an AI's judgment as the sole final enforcement boundary. The sixth layer checks before the protected effect occurs. It is not an excuse to pull the plug after the damage.

## What the Safety Governor would do

Our destination is a Safety Governor chip on an add-on module inside a selected NVIDIA-powered server, potentially a Supermicro platform. We want an independently governed component that can refuse a precisely defined action even when the AI host is compromised. This is the intended product property. This draft does not claim that our current code or hardware already establishes it. [6, 7]

### Authorize an exact effect

Before the protected endpoint commits an action, the governor would establish that the action possesses the authority required by the current rules. A valid signature is one input to that decision. It is not the whole decision. The authorization contract must bind:

- The complete canonical action and its parameters, including the recipient, resource or destination that gives the action its meaning.
- The subject, tenant, session, endpoint and unique ticket identity, so permission cannot migrate to a different actor or context.
- Current policy, registry, revocation and boot generations, together with explicit expiry and freshness rules.
- Every separately required approval, plus an atomic budget reservation and single-use consumption record where the policy requires them.

The endpoint must execute the authorized action without silently substituting a different one. A log or signature produced after execution cannot provide the missing prior permission.

### An ordinary example with an unforgiving boundary

Suppose a policy permits one payment of up to $1,000 to an approved supplier and requires a finance approval. The model can propose the payment. A classifier can examine it. A person can approve it. The governor should refuse a changed beneficiary, a missing approval, revoked authority or reuse of the same ticket. The authority to execute the payment must be available only through the enforcing endpoint for this claim to hold. This is an illustrative use case, not a claim that a payment integration exists.

### Define exactly what a refusal prevents

An action gate can refuse a protected service call. A key controller can withhold a secret. Platform circuitry may inhibit execution or request a reset. A power limit may reduce performance without stopping computation. These are different functions, with different control paths and timing. We must name the one we implement and measure its effect.

Our intended promise is narrow and strong: without current, valid authorization, the specified protected effect does not proceed. The governor does not establish that every authorized act is harmless. A harmful action can satisfy a badly written policy, and several honest observers can share the same mistake.

## The boundary we have to earn

If the host can ignore the governor, the governor is an advisory device. We need an unavoidable point of enforcement and control over the state that gives permission its meaning. The diagram shows the intended relationship. It is a design requirement, not a completed integration.

![Figure 1. Proposed authority boundary.](figures/image1.png)

*Figure 1. Proposed authority boundary. The compulsory gate may be a protected service endpoint or platform circuitry. The watchdog and gate must remain effective under the declared fault and compromise model.*

### Keep the authority outside the compromised host

If host or BMC compromise is in scope, neither may retain an alternate credential, management writer or override that defeats the check. Putting the chip beside a BMC does not make it independent of BMC software. Policy updates, emergency recovery and key replacement need authenticated procedures and identifiable owners. Multiple signatures do not create independent oversight if the same party controls all the keys.

### Preserve the meaning of permission across failure

The trusted core needs authenticated boot and updates, protected keys, monotonic version floors, durable replay and budget state, and a readiness barrier before it accepts work. Reset must not resurrect revoked authority or make a spent ticket look unused. Torn writes, full storage and an uncertain remote result require explicit recovery rules. A local spent bit alone cannot promise exactly-once effects at an arbitrary remote service.

### Make the loss of the governor enforceable

The platform must detect removal, reset, power loss or loss of communication and apply a defined safe state. A dead card cannot be the only thing expected to assert "stop." An independent interlock or watchdog must withhold the relevant permission. We also need a policy for already accepted work, because revoking future actions does not undo effects that have already occurred.

## A real Supermicro location

This is a top view of Supermicro's G1SMH-G baseboard for a Grace Hopper system. It gives us a concrete reference for an OEM management-module discussion. The Grace Hopper compute module is absent from this bare-board photograph. [2, 3]

![Figure 2. Supermicro G1SMH-G reference motherboard.](figures/image2.jpg)

*Figure 2. Supermicro G1SMH-G reference motherboard, shown without its compute module. Original manufacturer photograph. The empty-looking center is not spare space in an assembled server. [2, 3]*

Look at the long light-colored connector on the left, below the square Intel FPGA. The manual identifies it as JBMC1, the BMC DC-SCM module card connector. That management interface is a candidate for an OEM-designed integration. It is an existing management role, not an unused universal socket for our chip. [3]

The two broad horizontal connectors in the middle, labeled GPU1 and CPU1 in the manual, connect the compute module. Our chip would live on its own carrier or an OEM management board. We would need the vendor to establish the mechanical fit, electrical interface, power domain and binding control path. The photograph establishes none of those approvals.

## A Blackwell server is several boards

NVIDIA's DGX B200 makes the separation easy to see. The CPU and memory tray contains PCIe riser positions; the eight B200 GPUs occupy a different tray. These official top views show the packaging problem our module would have to solve. [4]

![Figure 3. DGX B200 CPU and memory tray.](figures/image3.png)

*Figure 3. DGX B200 CPU and memory tray. The PCIe riser positions are on the left. The illustrated configuration already has cards installed; this is not evidence of a free, compatible slot. [4]*

![Figure 4. Separate DGX B200 GPU tray.](figures/image4.png)

*Figure 4. Separate DGX B200 GPU tray. The GPU and NVSwitch assembly is distinct from the CPU and memory tray above. Original NVIDIA reference illustrations. [4]*

A prototype carrier could target a qualified I/O position in the host tray. GPU inhibition would require a separate, protected platform control path. A PCIe endpoint does not automatically intercept all GPU, NVLink or network traffic. The physical slot gives us a place to connect; the integration must establish authority.

## What our add on module could contain

We envision the governor ASIC on a small carrier in the server's I/O or management area. An FPGA can implement the prototype. The drawing identifies component roles and the connection we must negotiate with an OEM. It is not a proposed pinout, a routed board or a claim of mechanical fit.

![Figure 5. Proposed carrier concept, not to scale.](figures/image5.png)

*Figure 5. Proposed carrier concept, not to scale. The separate control connection represents the compulsory enforcement path. The final implementation may distribute protected storage and fault handling differently.*

The ASIC would be one component of the enforcement system. Its package size, lane count, power consumption, cooling needs and board dimensions remain engineering questions. We should not put invented numbers in a vision document and let them harden into promises.

A slot is a place to mount the board. It is not, by itself, authority over the machine.

## The promises we would have to prove

The acceptance test is whether the protected effect remains governed under the failures we claim to tolerate. A passing unit-test suite, a valid signature or a changing GPIO pin is insufficient evidence on its own. We need observable outcomes at the actual endpoint or machine.

**Every relevant route is accounted for.** Enumerate the ways the effect can occur, including alternate credentials, service endpoints, privileged management interfaces and recovery procedures. Try each route without valid authorization. The evidence must show that no route within the declared deployment bypasses the boundary. If one remains, narrow the claim or close the route.

**A hostile host cannot grant itself authority.** Test a compromised host and, separately, a compromised BMC. Attempt policy replacement, forged context, changed parameters, unauthorized firmware, replay and access to an alternate control writer. The intended result is a denied protected effect and a recoverable, accountable state. We must specify which roots of trust remain trusted in each test.

**Failure does not recreate permission.** Cut power and reset components at transaction boundaries. Exercise torn writes, storage exhaustion, retries and uncertain remote outcomes. A reboot must not roll back policy, restore budget or revive a consumed ticket. Recovery must avoid duplicate effects without silently losing the information needed to reconcile an operation.

**Revocation has a measurable meaning.** Specify when revocation becomes effective, how fresh authority is established and which accepted operations may finish. Test delayed messages, reordered updates, stale registries and unavailable clocks or authority services. "Current" must have a defined implementation and a measured bound, not just a field in a token.

**The platform does the thing we claim.** Remove the card, interrupt its power and stop its communications. Measure the protected effect at the endpoint. For platform control, distinguish a requested reset, reduced power, inhibited execution and actual cessation of the relevant activity. Measure the delay and account for work already in flight. The appropriate safe state depends on the workload.

**The complete system can carry the workload.** Measure throughput and latency from request to committed effect, including approvals, durable state updates, network dependencies and recovery. Record false holds and operational burden. Compare the full design with a credible software gateway, protected controller or existing security hardware. Custom silicon must earn its cost and complexity.

These are proposed acceptance conditions. This document does not report that they have passed, and it does not certify remediation of findings from a prior audit.

## A route from prototype to silicon

We should build toward one useful, defensible guarantee before claiming broad control over an AI server. The first candidate is a consequential tool action through a protected gateway that alone holds the service credential. The host would submit requests without receiving a reusable secret. This makes the effect and its enforcement point concrete.

### Keep the trusted core small enough to examine

The governor should implement explicit checks and controlled state transitions. We should resist turning it into another opaque model or a general-purpose policy engine that nobody can review. Complex judgments can remain outside the core, but their authorized decisions must arrive in a form the core can check, bind and enforce.

### Know what remains outside the promise

The chip cannot repair a bad policy, guarantee that an observer understands an action or stop every authorized insider. It cannot control copies of released weights running outside a governed deployment, or effects that retain an ungoverned route. A physical attacker, a compromised trust root or an OEM override may require additional defenses or an explicitly narrower threat model. We must state those boundaries before selling the guarantee.

## The destination

We want a module an OEM can qualify and a customer can deploy with a documented reason to trust its refusal. The server should expose a defined integration point. The governor should enforce a specific contract. The operator should know who owns policy, what happens on failure and how to restore service without quietly bypassing the system.

That is the aspiration: our chip inside a real NVIDIA-powered server, with the authority to withhold a protected effect. We get there by proving that the refusal survives the hostile conditions we name. A photograph of a board with our logo on it would be easy. A boundary the host cannot talk its way around is the work.

## Sources and image credits

Manufacturer material establishes the reference hardware layouts and interface descriptions below. It does not establish compatibility, available capacity, vendor endorsement or the authority of the proposed Safety Governor. The proposed architecture, requirements and development path are ours.

- **[1]** NIST. *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile.* Published July 2024. General grounding for risk management across design, development, use and evaluation. The six-layer arrangement in this draft is our own.
- **[2]** Supermicro. *G1SMH-G motherboard.* Product description and the original bare-board photograph reproduced in Figure 2. The product page identifies Grace Hopper support, the Intel FPGA and DC-SCM support.
- **[3]** Supermicro. *SuperServer ARS-111GL-NHR user manual MNL-2669.* Motherboard tray top view and board layout. PDF pages 8 and 9, printed pages 14 to 17. The layout identifies JBMC1 as the BMC DC-SCM module card connector and identifies the CPU1 and GPU1 connectors.
- **[4]** NVIDIA. *DGX B200 User Guide: Introduction to DGX B200.* Motherboard Tray Components and GPU Tray Components. Original labeled illustrations reproduced in Figures 3 and 4. The source distinguishes the CPU and memory tray from the GPU tray.
- **[5]** Open Compute Project. *Flex Secure Control Module DC-SCM 2.0 Model SCM202A.* Reference example of the DC-SCM management, security and control module category. It is not a compatibility claim for our design or for the photographed Supermicro board.
- **[6]** Project baseline. *Safety Governor.* Reference snapshot for project context at commit 7ad4615f7ef1f69cc6925ddae9bd242f5f25c2ca. Citing the work does not assert that the acceptance conditions in this document are satisfied.
- **[7]** Project baseline. *Hardware and Silicon.* Reference snapshot for project context at commit 50702701175cfbe41150f2cab67bc60b914199a0. This aspiration describes a proposed destination, not a new verification of the repository.

*Figures 1 and 5 are original conceptual diagrams created for this draft. They show proposed roles and relationships only. No board dimensions, connector pin assignments, routing, throughput, timing, power or silicon area are specified.*

---

*This document is © 2026 Yobie Benjamin, under CC BY-NC 4.0 (see NOTICE and LICENSING.md). Manufacturer images are reproduced under their respective credits for reference and are the property of their owners; their inclusion is not a claim of endorsement, compatibility, or affiliation.*
