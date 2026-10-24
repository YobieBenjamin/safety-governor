# 23. There is no kill switch for AI. There is one at the exits.

> **Plain words first.** The most talked-about "solution" to AI safety is the kill switch: a big red button that turns the AI off. There is no such button, and there cannot be one, and the reason is not politics. It is the shape of the thing. The capability is copied across thousands of independent systems, and the network between them and the world was built, on purpose, to have no single point you can cut. Any switch you try to put in the middle of that network either does not exist or has to be installed next to every single machine, which is the same job as putting a gate in the machine, only bigger and with everyone else's traffic as collateral. The only cuts that are small, complete and local are at the two ends: the chip the model runs on, and the device that does the thing. That is where this design puts its gates. This document says that precisely, says which part of the popular argument is wrong, and backs the rest with a theorem that is nearly a century old and a check you can run.
>
> **Backed by:** `../proofs/no_global_kill_switch.py` (the graph model, minimum cuts by max-flow, cross-checked by brute force; `make proof` runs it), Menger's theorem (1927) and the max-flow min-cut theorem, `19` for claim L, the gate inside the separator, `18` questions 1 and 14 for the two limits that no theorem removes.

## 1. The argument people make, and the part of it that is wrong

The argument goes: all the models share one provenance, they were all trained on the same Internet; agents and bots roam that Internet and take what they need; the Internet was designed to survive a nuclear war and has no switch; therefore a kill switch for AI would mean killing the Internet, cables, satellites, telcos and all, which nobody will do; therefore there is no kill switch.

Three corrections before I defend the conclusion, because the conclusion deserves a better argument than that.

First, shared training data does not make the models interconnected. It makes them *replicated*. Every frontier lab has a model that can write the same exploit and plan the same fraud, open-weight copies sit on hundreds of thousands of private machines, and none of them needs any other one to run. That matters, and it matters more than interconnection would: it means the number of sources is large, growing, and has no owner. Removing any one source changes nothing. Keep that in mind, because it decides which end of the graph to gate.

Second, "kill switch means kill the Internet" is too strong, and anyone who has watched a government switch off a country's Internet for a week knows it. The precise statement, which the model below bears out, is this: there is no switch in the *deep* network, and the cheapest network-side switch is in the *access layer*, right next to every machine you want to cut off. That switch is possible in principle. It is also the same job as gating the machine itself, done several times over, with other people's traffic as collateral, and it needs a complete list of every machine, which nobody has.

Third, a network kill does not even do the job. A model on a laptop wired to a motor controller does not care about the Internet. The switch in the middle is too much and too little at the same time.

With those corrections the conclusion stands, and it is stronger: the only cuts that are small, complete, and local are at the ends. So that is where the gate goes.

## 2. The graph

Draw it as a graph, because the claim is a claim about cuts in a graph.

- **Sources.** Model instances, many of them, independent. Each runs on some compute, which is where its bytes leave: a GPU, a laptop, a phone.
- **The middle.** The network: access links, carriers, exchanges, clouds. Built to be k-connected, which is to say that between any two points there are at least k paths that share no node, for some k that is large in the core and smallest at the edge.
- **Effectors.** The devices whose actions change the world and cannot be undone: the payment switch that moves the money, the weapon's release line, the motor controller, the relay in the substation, the storage controller that holds the weights. Each has a controller through which every command passes.
- **Bystanders.** Everyone else: people and services that use the same network and have nothing to do with AI.

A kill switch is a *separator*: a set of nodes whose removal leaves no path from any source to any effector. The questions are where the smallest separators are, what they cost, and whom they take with them.

## 3. The theorem

Menger's theorem (1927): for two non-adjacent nodes, the smallest set of other nodes whose removal separates them equals the largest number of paths between them that share no node. The max-flow min-cut theorem turns that into something a computer can calculate: give every node a capacity of one, push flow from the sources to the effectors, and the maximum flow is the size of the smallest separator, and the residual graph tells you where it is.

Two consequences follow with no further assumptions.

**A separator is at least as large as the number of disjoint paths it has to cross.** In the deep network that number is k and more, by design. At an end it is one: every command to an actuator passes through its controller, and every byte from a model instance passes through the compute it runs on. So no separator anywhere is smaller than the smaller end's count of machines, provided the network carries that many disjoint paths between the two sides (which assumption 2 does not promise on its own and which the model checks directly, K4c below), and the ends achieve exactly that.

**The smallest separators sit at the smaller end.** You can cut at the sources, one per instance, or at the effectors, one per effector. By the first correction above, the sources are the larger and faster-growing set and nobody owns the list. The effectors that cannot be undone are a smaller, slower, better-known set: there are far fewer wire-transfer switches, release lines and motor drivers in the world than model instances, and they do not multiply when someone uploads a weight file. That is why the design gates the exits and treats the compute-side gate as the second lock, not the only one. It is also why the governor at the compute matters where it can be had: a source-side gate catches an action before it ever reaches the network, and does so with the levers to stop the machine.

### 3a. The same thing as three claims

Stated so they can be checked line by line, with the three assumptions the whole argument rests on: (1) replication, many sources, no complete list; (2) no middle, at least k vertex-disjoint paths through the network between any source's access node and any target's, k at least two; (3) local loops, at least one source joined to a target by a path that never enters the network.

- **Claim 1. No network-only kill switch exists.** Any set K of network vertices leaves the local path of assumption 3 intact, so some source still reaches some target, so K is not a separator. Assumption 3 alone is enough.
- **Claim 2. Under the aggregate-connectivity assumption, a network-only separator costs more vertices than there are machines at either end, and takes bystanders with it.** For any one source and one target, assumption 2 and Menger give at least k vertices to separate that pair. That per-pair bound does not by itself make the whole cut large, and I have to be careful here for the same reason Claim 3 is careful. If many sources funnel through a few shared vertices, those few vertices separate every pair at once, and the per-pair count of k says nothing against it. Twelve sources joined to the targets through two shared hubs are the counterexample: every source-target pair has two vertex-disjoint paths, so pairwise k is two, yet the two hubs are a separator of size two, far below the twenty-two machines, and the sources and targets lose nothing of their own so there is barely a bystander either. The script builds that graph and checks it (INVARIANT-TWO-HUB-NO-KILL), and a single shared controller does the same with one vertex (INVARIANT-SHARED-CONTROLLER-NO-KILL). So the large-separator conclusion needs the stronger assumption Claim 3 also names, that the network carries min(|S|, |T|) disjoint paths between the two whole sides, not merely k between each pair. A well-connected core, the kind you build when you design for no single point of failure, carries that many; under it, separating every pair at once costs more than one vertex per machine, because the access nodes are shared (measured: 43 vertices against 12 instances and 10 effectors, under two per machine and not k per machine, since the script asserts only that the cut is at least k and larger than either end), and the vertices are network vertices, so every bystander path through them is cut too. Measured: 43 of 60 core nodes, 19 percent of bystander pairs. The two shared hubs and the single controller fail that assumption, and are exactly the graphs the claim now excludes rather than overpromises about.
- **Claim 3. Every separator has at least min(|sources|, |targets|) vertices, and the smaller end achieves it.** Vertex-disjoint source-to-target paths use distinct sources and distinct targets, so there are at most min(|S|, |T|) of them. The step that needs care: assumption 2 promises k disjoint paths per pair, which does not by itself give min(|S|, |T|) disjoint paths between the two whole sides (a 2-connected core with a two-node waist between the source side and the target side has a two-node separator). The claim needs the stronger assumption that the network carries min(|S|, |T|) disjoint paths between the sides, which a well-connected core does and which the script checks on the instance rather than assumes (K4c: the smallest separator anywhere outside the bystanders is 11, the device end's count). With that, by Menger the minimum separator has exactly that size; the compute nodes and the controllers are separators of sizes |S| and |T|.

Together: there is no switch, only a gate per machine, and the gates go to the smaller, better-known end, the devices that act, with a second gate on the compute wherever it can be had. Part 6 of the blog carries this proof for a general reader.

## 4. The check you can run

`../proofs/no_global_kill_switch.py` builds a graph in exactly that shape, a random 6-regular core of 60 nodes (expander-like, the kind of network you get when you design for no single point of failure; the script checks that it is simple and connected, not its expansion), 12 instances and 10 effectors each attached to 6 core nodes through their own compute node or controller, 20 users and 20 services as bystanders, and one local pair, a model wired to its actuator with no network between them. It computes minimum separators by max-flow over split nodes, cross-checks the smallest instance by brute force, and asserts:

| | What holds in the model | What it means |
|---|---|---|
| K1a | No separator exists that stays out of the access nodes one hop from the ends | There is no switch in the deep network. A thin check on this instance: 57 of the 60 core nodes sit one hop from some end, so the deep layer the check runs on is three nodes, and three nodes of a 6-regular graph cannot separate anything. Assumption 2 carries the claim; a larger core is on the list to rebuild |
| K1b | The cheapest network-side separator has 43 nodes, every one an access node next to an end, against 12 instances and 10 effectors | The only network switch is the edge, one hop from the machine, more nodes than machines (43 against 22, under two per machine), and it needs the same list of machines as an end cut |
| K2 | That separator removes 72 percent of the core and severs 19 percent of user-to-service pairs that had nothing to do with AI | The network switch takes bystanders with it; the end cuts take none |
| K3 | Removing the entire core leaves the local model wired to its local actuator | Killing the network is too little as well as too much |
| K4 | Cutting at the effector controllers separates everything with 11 nodes, one per effector; cutting at the compute does it with 13, one per instance; bystanders are untouched | The gates belong at the ends, and one node per end is the floor Menger allows |
| K4c | Letting the cut fall anywhere except on the bystanders, the smallest separator in the whole graph is still 11, the smaller end's count | Nothing anywhere beats one per machine at the smaller end; this is Claim 3 checked on the instance |
| K5 | Gating only the irreversible effectors needs 6 nodes, their own controllers | "Can you undo it" shrinks the separator to the exits that matter |
| INVARIANT-TWO-HUB-NO-KILL | Twelve sources reaching ten targets through two shared hubs have two vertex-disjoint paths per pair, yet two nodes separate everything | The per-pair bound does not imply a large cut; this is why Claim 2 and Claim 3 need the aggregate-connectivity assumption, and the corrected Claim 2 excludes this graph (its sides carry only two disjoint paths, below min(\|S\|,\|T\|)) |
| INVARIANT-SHARED-CONTROLLER-NO-KILL | A single shared controller separates all twelve sources from all ten targets with one node, though every pair is connected | The sharpest form of INVARIANT-TWO-HUB-NO-KILL: a shared vertex beats any per-pair count, and the corrected Claim 2 excludes this graph too |

The numbers are the model's, not the Internet's, and the script says so in its own docstring. What transfers is the shape: a highly connected middle has no small separator, the cheapest cuts are at the degree-one ends, and reversibility shrinks the set of ends you have to hold.

## 5. From the cut to the chip

Claim L in `19` is the other half of the design, the gate inside the separator; `19` proves it with the reference-monitor argument and the Z3 proofs, not with cuts. A separator stops traffic. A *gate* in the separator lets through exactly what a signed rule allows and nothing else; that is the reference monitor, Anderson 1972, and the Z3 proofs in `../proofs/core_invariants.py` show the gate's logic has the always-invoked half of that property in every reachable state of the abstract machine: nothing executes without a ticket, no ticket without a rule and its witnesses, no replay, no stale edition, fail closed when the heartbeat dies, halt absorbing without a quorum. Tamper-proof and small enough to check are claims about the silicon and the implementation, which the proofs do not touch (`19` section 3 says what covers them and what does not).

Put the two together and the design is a sentence. *The only small, complete separators between models and the world are at the ends; put a reference monitor in each end node; let the monitor's rules be signed by people the model cannot reach; check the ticket again in the device that acts.* The governor is the monitor at the compute end, with the levers to stop the machine. The endpoint comparator is the monitor at the effector end. Everything above them, the classifiers, the watchers, the runtime sandboxes, lives in the middle, where there is no small cut, which is why the design treats them as witnesses and never as the lock.

## 6. What the theorem does not give you

Two things, and they are the two open questions in `18` that no chip moves.

**Coverage.** The separator is complete only if every irreversible effector has its comparator and every piece of governed compute has its governor. A device nobody wired through a gate is not in the cut. That is a deployment fact (question 1), and it is the reason the design asks for nothing from NVIDIA that would stop an OEM from shipping the module tomorrow, and the reason the effector side matters more than the source side: it is the end you can finish.

**People.** A person is an effector no chip gates. A model that persuades a person to wire the money has routed around every separator in this document (question 14). The log shows what was and was not ticketed, and the witnesses can flag the attempt. That is all the hardware can do, and the document says so rather than pretending otherwise.

## 7. The sentence to say when someone says "kill switch"

There is no button, because the capability is in a thousand places and the network between them and the world has no middle to cut. The only places a cut is small and complete are the chip that runs the model and the device that does the deed. We can build gates there. We are building them. Everything else is a classifier with a press release.
