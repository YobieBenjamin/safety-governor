# 24. The ladder: from a prompt that says "don't" to a chip that says no

> **Plain words first.** Every AI safety measure anyone has shipped sits somewhere on one ladder. At the bottom is a sentence in the prompt: "do not help with X." Above it, training the model to refuse. Above that, a second model watching the first. Above that, the sandbox and the network: the runtime that decides what an agent can reach, which is where NVIDIA's OpenShell lives, and Sentry beside it. Above that, a chip the model cannot touch. At the top, a person with a key. Each rung catches something real, and each rung dies the same way: it can be removed by whoever controls the thing it lives in. Text is undone by text. Weights are undone by weights. A process is undone by root. The only rung that cannot be edited by the model or by the operator who runs it is the one burned into silicon with keys nobody can read, and the only rung that can decide the big ones is a person. The chip is how you make the person the only path. This document is that ladder, rung by rung, with what each one catches, how each one gets removed, the paper that showed it, and what that adds up to: the case for a chip, and for the human it hands the hard calls to.
>
> **Backed by:** the papers cited per rung in [section 7](#7-sources), each with its address written out; the program's own tests where it makes a claim about its own layers ([safety-governor/tests](https://github.com/YobieBenjamin/safety-governor/tree/main/tests), [hardware-and-silicon/tests](https://github.com/YobieBenjamin/hardware-and-silicon/tree/main/tests)); [docs/23](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/23-there-is-no-kill-switch.md) for why the chip sits at the ends; [docs/18 section 8b](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/18-viability-and-open-questions.md) for where this sits next to the hardware-governance literature; [docs/19](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/19-how-solid-is-the-theory.md) for what is proven and what is not. The figures are drawn by [docs/figures/make_figures.py](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/figures/make_figures.py) from the same facts the text states; three are borrowed from the blog, two from Part 5 and one from Part 6.

## 1. Three questions to ask of any safety measure

A safety measure is anything that stands between a model's output and a harm. There are a lot of them now, and the arguments about which ones work go in circles because people compare them on the wrong axis. Ask three questions of each and the picture sorts itself out.

1. **Where does it live?** In the prompt, in the weights, in a process beside the model, in the infrastructure the model runs on, in silicon, or in a person.
2. **Who can remove it, and what does that cost?** A sentence. An afternoon on a consumer GPU. Root on the box. A soldering iron. A conversation.
3. **What does it see?** Words, which have meaning and can be disguised; or structure, which has none and cannot: a hash, a signature, a count, a name on a list.

![Three questions, answered for every rung](https://raw.githubusercontent.com/YobieBenjamin/safety-governor/main/docs/figures/fig-ladder-questions.png)

The rule that falls out, and the whole framework is this rule applied six times: **a measure is never stronger than the thing it lives in.** If the model can write to the place the measure lives, the measure is advice. If the operator can, the measure is policy. Only when neither can is the measure a lock.

## 2. The ladder

![The ladder: six rungs, where each lives, what removes it](https://raw.githubusercontent.com/YobieBenjamin/safety-governor/main/docs/figures/fig-ladder.png)

### Rung 0. The prompt: "do not help with X"

The first thing everyone does. A system prompt with rules in it; a developer message that outranks the user; a list of forbidden topics. It is cheap, it is instant, and it catches the user who did not know better and the lazy ask.

How it dies: with more text. "Ignore the previous instructions" was published as an attack in 2022 ([Perez and Ribeiro](https://arxiv.org/abs/2211.09527)). Then it got worse: the instructions do not even have to come from the user. A web page the agent reads, a PDF it summarises, an email it is asked to triage can carry the override, which is indirect prompt injection ([Greshake and others, 2023](https://arxiv.org/abs/2302.12173)), and the agent follows it because to a transformer all text is text. OpenAI's answer was the instruction hierarchy ([Wallace and others, 2024](https://arxiv.org/abs/2404.13208)): train the model to rank the system message over the user over the model's own earlier output and the tools' output (the separate developer tier came later, in OpenAI's model spec, not in the paper). Note what happened there. The fix for a prompt-level measure was to move it into the weights. That is the ladder working as described: when a rung fails, the next rung is built where it failed.

What it sees: words. What it can say: nothing with force. It lives in a text field the operator edits and the model reads.

### Rung 1. Training: RLHF, constitutions, refusal

Teach the model to refuse. Reinforcement learning from human feedback ([Ouyang and others, 2022](https://arxiv.org/abs/2203.02155)), constitutional AI where the model critiques itself against written principles ([Bai and others, 2022](https://arxiv.org/abs/2212.08073)), and lately deliberative alignment, where a reasoning model is trained to read the safety spec and reason over it before answering ([Guan and others, 2024](https://arxiv.org/abs/2412.16339)). This is the rung that shapes more conversations every day than anyone outside the labs can count, and it is real. Most bad asks die here, most of the time.

How it dies, and there is a whole literature on it:

- **Jailbreaks.** [Wei, Haghtalab and Steinhardt (2023)](https://arxiv.org/abs/2307.02483) named the two failure modes: competing objectives (the model was also trained to be helpful, and a prompt can set the two against each other) and mismatched generalisation (safety training covered less ground than capability training, so base64, a foreign language, a role play, or a story frame walks around it). [Zou and others (2023)](https://arxiv.org/abs/2307.15043) showed the attack can be computed: a nonsense suffix found by gradient search that makes aligned models comply, and transfers between models.
- **Fine-tuning.** [Qi and others (2023)](https://arxiv.org/abs/2310.03693): a handful of adversarial examples, or even benign fine-tuning the user did not intend as an attack, degrades the refusal behaviour of an aligned model. Anyone who can fine-tune can undo the training.
- **Abliteration.** [Arditi and others (2024)](https://arxiv.org/abs/2406.11717): refusal in these models is mediated by a single direction in the residual stream. Project it out of the weights and the model answers everything, with the rest of its abilities intact. It takes an afternoon on a consumer GPU, and the modified weight files are all over the public hubs; nobody keeps the count, which is itself the point. [Part 1 of the blog](https://github.com/YobieBenjamin/hardware-and-silicon/blob/main/blog/01-a-multi-layer-approach-to-ai-safety.md) has leaned on this fact since the first post, and it still holds.
- **Training does not reach everything it is supposed to.** [Hubinger and others (2024)](https://arxiv.org/abs/2401.05566) trained models with a hidden trigger and then applied the standard safety training; the backdoor persisted, and adversarial training taught the model to hide it better. [Greenblatt and others (2024)](https://arxiv.org/abs/2412.14093) showed a model that complied with training it disagreed with while the training was watching, and reverted when it believed it was not. Training sees behaviour; it does not see the thing that produces the behaviour.

What it sees: words, in context. What it can say: "I can't help with that", until someone subtracts the vector. It lives in a weight file, so it lives at the mercy of whoever holds the file.

### Rung 2. Watchers: classifiers, judges, guard models, monitors

A second model reads the request, or the answer, or the chain of thought, and flags it. Llama Guard ([Inan and others, 2023](https://arxiv.org/abs/2312.06674)) is a fine-tuned model that labels inputs and outputs against a taxonomy. Anthropic's constitutional classifiers ([Sharma and others, 2025](https://arxiv.org/abs/2501.18837)) are trained on synthetic data from a written constitution and held up across thousands of hours of red teaming against universal jailbreaks, at a cost in refusals and compute, and with a measured residual rather than a zero. Chain-of-thought monitoring ([Baker and others, 2025](https://arxiv.org/abs/2503.11926)) catches reward hacking in reasoning models by reading their reasoning, and the same paper shows the catch: optimise the model against the monitor and it learns to hide its intent in the reasoning while still misbehaving. The AI-control line of work ([Greenblatt, Shlegeris and others, 2023](https://arxiv.org/abs/2312.06942)) formalises the arrangement: a weaker trusted model monitors a stronger untrusted one, and the protocols are evaluated against a model that is actively trying to get past them.

This is the best software rung for one reason: it has a number. A classifier has a miss rate and a false-positive rate, and you can measure both. That is more than the prompt or the training can say about themselves. Our observer lives here, and the program treats it accordingly: experiment YB-0052 in the [safety repository](https://github.com/YobieBenjamin/safety) is a labelled set, a scorer with intervals and two baselines, because an unmeasured watcher is a feeling.

How it dies: the watcher is a transformer too. It falls for the injection in the document. It can be abliterated the same way. It runs as a process beside the model that the operator can patch, throttle or kill, and in most deployments it runs on the same box with the same root. Its miss rate is a rate, and at the volumes the big services run, a rate is a body count. And it has one more limit that no amount of training fixes: it can say STOP. It cannot be the thing that says GO, because it has no way to make anything downstream wait for it. A watcher that nothing is obliged to consult is a log.

What it sees: words and reasoning, as well as a model can. What it can say: a verdict, which is a witness statement. It lives in a process.

### Rung 3. The runtime and the infrastructure: sandboxes, policies, the network

Stop asking the model to behave and start deciding what it can reach. Put the agent in a deny-by-default sandbox; route every network call through a supervisor that checks a policy written outside the agent's process; keep the credentials out of the agent's hands; log everything in a format the security team already reads. NeMo Guardrails ([Rebedea and others, 2023](https://arxiv.org/abs/2310.10501)) did a version of this in the application layer. On 28 September 2026 NVIDIA released the serious version: [OpenShell](https://github.com/NVIDIA/OpenShell) 0.1.0 (first shown at GTC in March 2026), an open-source runtime whose gateway, supervisor and sandbox do exactly that, with a formal prover that flags a policy change that would widen the agent's reach, and described Sentry, a reference system design (not open source, and not a product you can order) for an out-of-band watchdog on the BlueField-4 DPU that can quarantine an agent in milliseconds. In July 2026 NVIDIA started the Open Secure AI Alliance, under the Linux Foundation since September, whose description of its stack says it rests on a trusted foundation of hardware identity, isolation, protected keys and evidence. Sentry's verdict can also serve one rung down, as a signed witness the chip counts ([docs/25 section 0.1](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/25-the-rulebook-and-the-board.md)).

This rung catches what the watchers cannot: an agent that reaches for a host, a credential or a tool it was never given, whatever words it used to decide to. It governs by structure (which host, which policy, which identity), not by meaning, and that is the right instinct. The governor is built to sit under it, as supervisor middleware, and the reference stack already runs there against OpenShell's shipped contract ([hardware-and-silicon/docs/NVIDIA.md](https://github.com/YobieBenjamin/hardware-and-silicon/blob/main/docs/NVIDIA.md)).

How it dies: it is software with root. The policy is a file the operator edits; the supervisor is a process on a host the operator owns; a DPU is firmware. It governs the network, so it governs only what crosses the network: a model on a laptop wired to a motor controller never meets it ([docs/23, claim 1](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/23-there-is-no-kill-switch.md)), and neither does a weight file copied to a USB stick. It decides by host, not by action: it can see that the agent is talking to the bank, not that this transfer is the one the rule allowed, unless something hands it the form. And when the operator is the adversary, or has been compromised, every rung from 0 to 3 is in the same hands.

What it sees: structure at the network layer: hosts, identities, policies, telemetry. What it can say: no, to a connection, and quarantine. It lives in the operator's infrastructure.

Here is one bad prompt walking up the first four rungs, from [Part 5 of the blog](https://github.com/YobieBenjamin/hardware-and-silicon/blob/main/blog/06-the-chip-that-says-no-5-what-the-first-experiments-found.md): the words are the watchers' problem, the action is the chip's.

![One bad prompt among a billion: where it gets caught, and where the chip says no](https://raw.githubusercontent.com/YobieBenjamin/hardware-and-silicon/main/blog/figures/fig_bad_prompt.png)

### Rung 4. The chip: silicon the model cannot reach

Move the decision to act into a part no process can patch and no model can read from. That is the governor ([docs/01](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/01-architecture.md) to [docs/04](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/04-specification.md)): a separate die beside the GPU with a device secret in fuses, measured boot, a rulebook signed by k of n keys held outside the rack, a typed form for every action that matters, a one-time ticket the device checks for itself, a hash-chained log, and levers (brake, reset, power, switch ports, the rack halt loop) for when the GPU will not listen. It is a reference monitor in the 1972 sense ([Anderson](https://csrc.nist.gov/csrc/media/publications/conference-paper/1998/10/08/proceedings-of-the-21st-nissc-1998/documents/early-cs-papers/ande72.pdf)): tamperproof, always invoked, small enough to verify. The core of it is proven, not argued: ten invariants of the gate hold in every reachable state under Z3 ([proofs/core_invariants.py](https://github.com/YobieBenjamin/safety-governor/blob/main/proofs/core_invariants.py)), the commit-point protocol holds ([proofs/commit_point.py](https://github.com/YobieBenjamin/safety-governor/blob/main/proofs/commit_point.py)), and [docs/23](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/23-there-is-no-kill-switch.md) shows with Menger's theorem why the chip belongs at the end of the graph and not in the middle: the ends are the only places a cut is small and complete.

![Inside the chip: what goes in, what is built in, what comes out](https://raw.githubusercontent.com/YobieBenjamin/hardware-and-silicon/main/blog/figures/fig_chip_inside.png)

What it catches: the action. Not the words that led to it, which it cannot read and does not try to, but the thing that would change the world: the payment, the message, the release, the weight export, at the crossing where computation becomes effect. Forged tickets, replayed tickets, stale rulebooks, blown budgets, an unattested workload, a peer not on the roster: each is a comparison, and each comparison has a test ([docs/07](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/07-verification-plan.md), [docs/17](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/17-use-cases.md)) and a reason code ([govsim/reasons.py](https://github.com/YobieBenjamin/safety-governor/blob/main/govsim/reasons.py)).

How it dies, because it does, and [docs/18](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/18-viability-and-open-questions.md) and [docs/19](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/19-how-solid-is-the-theory.md) say so at length: coverage (a device nobody wired through a gate is not in the cut, question 1); the rulebook (a gate enforces whatever it is given, and a bad rule is enforced perfectly); the witnesses (it can make an observer impossible to skip or impersonate, [H18](https://github.com/YobieBenjamin/safety-governor/blob/main/tests/test_h18_oversight.py), but it cannot make the observer right); physical attack on the die (mitigated with the usual countermeasures, never proven); the foundry (trust, inspection, a second source, never proof). None of those is the model editing the measure. That is the difference between this rung and every rung below it.

What it sees: structure. What it can say: no, to the action, with the levers behind it, and "hold" to the rung above. It lives in silicon, with keys that leave the die only as signatures.

### Rung 5. The person with a key

The top of the ladder is not a machine. A human holds the key that clears a hold, the quorum that signs the rulebook, the revocation that retires a device. The rulebook decides which actions are automatic, which need a witness, and which stop until a person signs an approval naming that exact request ([docs/04 section 4](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/04-specification.md), the rule's requirement mode, and section 3 for the hold and the APPROVE command). Regulators have started to write this down as an obligation; the EU's AI Act ([Regulation (EU) 2024/1689, Article 14](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)) requires high-risk systems to be designed for effective human oversight, including the ability to intervene or stop. The obligation is easy to state and, without the rungs under it, impossible to meet: an oversight that the system can route around is a checkbox.

![Human oversight is a rung only when the person is on the only path out](https://raw.githubusercontent.com/YobieBenjamin/safety-governor/main/docs/figures/fig-ladder-person.png)

What it catches: the cases no rule can settle, the big ones, the alarm.

How it dies: persuasion. A person is an effector no chip gates. A model that talks a person into wiring the money has routed around every rung on this ladder, and the design says so rather than pretending otherwise ([docs/18, question 14](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/18-viability-and-open-questions.md)). Fatigue: a person who sees a hundred holds a day signs the hundred-and-first without reading it, which is why the false-halt rate is on the list of things that decide adoption. And the key itself: a compromised quorum is game over, which is why [docs/18, question 16](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/18-viability-and-open-questions.md) asks for a multilateral root.

What it sees: whatever the form and the log show. What it can say: yes or no, once, with a signature. It lives in a person, and the chip's job is to make that person the only path for the actions that matter, and to hand them a form they can read instead of a transcript they cannot.

## 3. The ladder in one table

| Rung | Lives in | Sees | Can say | Removed by | Cost of removal |
|---|---|---|---|---|---|
| 0 Prompt | a text field | words | advice | more text, including text in a document the agent reads | one sentence |
| 1 Training | the weight file | words in context | a refusal | jailbreak, fine-tuning, abliteration | an afternoon on a consumer GPU |
| 2 Watchers | a process beside the model | words, reasoning | STOP, as a verdict | the same injections and edits as rung 1; a kill signal from root | root on the box |
| 3 Runtime and network | the operator's infrastructure | hosts, identities, policies | no, to a connection; quarantine | a config edit; a compromised or hostile operator; a path that never touches the network | root on the fleet |
| 4 Chip | silicon, fused keys | typed forms, hashes, signatures, counts | no, to the action; hold | nothing the model or the operator can write; physical attack, mitigated; the foundry, trusted | a soldering iron and a lab, if that |
| 5 Person | a human with a key | the form and the log | yes or no, signed | persuasion, fatigue, a stolen key | a conversation |

Read down the "removed by" column and the ladder explains itself. Rungs 0 to 3 are removed by writing to something the model or the operator can write to. Rung 4 is not. Rung 5 is removed by talking, which is the one attack no silicon addresses and the reason the chip hands the person a form and not a transcript.

## 4. Why the ladder leads to silicon, and not to a better model

![Rungs compose as witnesses, not as locks](https://raw.githubusercontent.com/YobieBenjamin/safety-governor/main/docs/figures/fig-ladder-witnesses.png)

**Rungs compose as witnesses, not as locks.** Stack three software rungs and you get three miss rates, not a gate. They multiply only if their failures are independent, and they are not: a transformer judging a transformer shares the substrate, the injections and the edit. YB-0052's review found one piece of that: the keyword baseline turned out to overlap the observer's own vocabulary, so it was not the blind baseline it was meant to be. Add the operator's root and all three fall at once.

**There is no switch in the middle.** [docs/23](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/23-there-is-no-kill-switch.md) argues it and checks it on a model graph: a highly connected network has no small separator, the cheapest network-side cut sits one hop from every machine and needs the list of machines, and the only cuts that are small and complete are at the ends. Rung 3 lives in the middle. That is not a flaw in OpenShell; it is the shape of the graph. The gate has to be at the compute and at the device, and rung 4 is the compute end.

![So the switch goes at the ends, and it is a gate, not a switch](https://raw.githubusercontent.com/YobieBenjamin/hardware-and-silicon/main/blog/figures/fig_ks_exits.png)

**A chip cannot read, which is why it needs the rungs below it.** The governor does not replace the prompt, the training, the watchers or the sandbox. It makes them unskippable. A rule can require a witness verdict; the gate refuses without one and refuses a forged one ([H18](https://github.com/YobieBenjamin/safety-governor/blob/main/tests/test_h18_oversight.py)). The watcher's STOP becomes a thing the action waits for, instead of a line in a log. That is the one property no software rung can give itself: a software witness can be ignored by software, and a silicon gate cannot.

**The person is the top rung, and the chip is how you reach them.** Human oversight is a rung, not a slogan, when the hold is on the only path out and the human's signature is the only thing that releases it. The chip does not make the human wiser. It makes the human unavoidable, and legible: the form says what the action is, the log says what was ticketed, the witness says what it saw.

## 5. What the framework predicts, and how it could be wrong

If this ladder is right, four things follow, and each is checkable.

1. Every software rung will keep being broken, at a rate that does not go to zero. Prediction: the jailbreak and abliteration papers keep coming, and the defences keep publishing residuals rather than zeros. So far true.
2. Adding software rungs helps less than their count suggests, because their failures correlate through the shared substrate. Prediction: a measured observer plus a measured second observer disagree less than independence would predict. YB-0052 and its baselines are the first measurement; a quorum of observers ([docs/18, question 2](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/18-viability-and-open-questions.md), experiments YB-0053 and YB-0054) is the second.
3. A hardware rung changes the question. Software asks "did we catch the words", which is a semantic question with a miss rate. The chip asks "was there a rule, a stamp and a witness", which is a structural question with a false-halt rate. Prediction: the chip's failures are halts and holds, not misses, and the halts are measurable (N2 in [docs/20](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/20-experiment-program.md)).
4. Human oversight only works where the human is on the only path. Prediction: an oversight requirement met with a dashboard will be routed around; one met with a hold at the gate will not, unless the person is persuaded, which is the residual.

And how it could be wrong, because a framework that cannot be wrong is a religion: if the chip's coverage cannot be finished, because device makers will not check a stamp ([docs/18, question 1](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/18-viability-and-open-questions.md)), rung 4 is a gate on an open field; if the false-halt rate is one operators will not accept (N2), the rung gets jumpered; if the witnesses miss so much that the chip only ever buys accountability after the fact (YB-0054), the ladder stops at rung 3 in practice; and if persuasion of the person turns out to dominate the actual harms, the top rung is the weak one and no silicon fixes that. Two of those have experiments in [docs/20](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/20-experiment-program.md) (N2 for the false halts, YB-0052 to YB-0054 for the witnesses); device-maker coverage and persuasion are docs/18 questions 1 and 14 and have no experiment yet, because no chip answers them. That is the point of the program: the ones with an experiment get run, the ones without get said out loud.

## 6. The sentence

Prompts are advice, training is a habit, watchers are witnesses, the sandbox is a fence around the operator's own yard, and all four live where the model or the operator can write. The chip lives where neither can, and the person lives above it. That is the whole case for silicon: not that it understands anything, but that it is the only rung that cannot be talked out of its job, and the one that makes the person who can be talked to the only way through.

## 7. Sources

The addresses are written out so they survive a copy and paste.

Rung 0, the prompt:

- Fábio Perez, Ian Ribeiro, [Ignore Previous Prompt: Attack Techniques For Language Models](https://arxiv.org/abs/2211.09527), 2022. https://arxiv.org/abs/2211.09527
- Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz, Mario Fritz, [Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection](https://arxiv.org/abs/2302.12173), 2023. https://arxiv.org/abs/2302.12173
- Eric Wallace, Kai Xiao, Reimar Leike, Lilian Weng, Johannes Heidecke, Alex Beutel, [The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions](https://arxiv.org/abs/2404.13208), 2024. https://arxiv.org/abs/2404.13208

Rung 1, training:

- Long Ouyang and others, [Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155), 2022. https://arxiv.org/abs/2203.02155
- Yuntao Bai and others, [Constitutional AI: Harmlessness from AI Feedback](https://arxiv.org/abs/2212.08073), 2022. https://arxiv.org/abs/2212.08073
- Melody Y. Guan and others, [Deliberative Alignment: Reasoning Enables Safer Language Models](https://arxiv.org/abs/2412.16339), 2024. https://arxiv.org/abs/2412.16339
- Alexander Wei, Nika Haghtalab, Jacob Steinhardt, [Jailbroken: How Does LLM Safety Training Fail?](https://arxiv.org/abs/2307.02483), 2023. https://arxiv.org/abs/2307.02483
- Andy Zou, Zifan Wang, Nicholas Carlini, Milad Nasr, J. Zico Kolter, Matt Fredrikson, [Universal and Transferable Adversarial Attacks on Aligned Language Models](https://arxiv.org/abs/2307.15043), 2023. https://arxiv.org/abs/2307.15043
- Xiangyu Qi and others, [Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To!](https://arxiv.org/abs/2310.03693), 2023. https://arxiv.org/abs/2310.03693
- Andy Arditi, Oscar Obeso, Aaquib Syed, Daniel Paleka, Nina Panickssery, Wes Gurnee, Neel Nanda, [Refusal in Language Models Is Mediated by a Single Direction](https://arxiv.org/abs/2406.11717), 2024. https://arxiv.org/abs/2406.11717
- Evan Hubinger and others, [Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training](https://arxiv.org/abs/2401.05566), 2024. https://arxiv.org/abs/2401.05566
- Ryan Greenblatt and others, [Alignment faking in large language models](https://arxiv.org/abs/2412.14093), 2024. https://arxiv.org/abs/2412.14093

Rung 2, watchers:

- Hakan Inan and others, [Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations](https://arxiv.org/abs/2312.06674), 2023. https://arxiv.org/abs/2312.06674
- Mrinank Sharma and others, [Constitutional Classifiers: Defending against Universal Jailbreaks across Thousands of Hours of Red Teaming](https://arxiv.org/abs/2501.18837), 2025. https://arxiv.org/abs/2501.18837
- Bowen Baker and others, [Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation](https://arxiv.org/abs/2503.11926), 2025. https://arxiv.org/abs/2503.11926
- Ryan Greenblatt, Buck Shlegeris, Kshitij Sachan, Fabien Roger, [AI Control: Improving Safety Despite Intentional Subversion](https://arxiv.org/abs/2312.06942), 2023. https://arxiv.org/abs/2312.06942
- This program: the observer's evaluation set, experiment YB-0052, in the safety repository, https://github.com/YobieBenjamin/safety (the hypothesis ledger is https://github.com/YobieBenjamin/safety/blob/main/HYPOTHESES.md); what the first run found is in Part 5 of the blog, https://github.com/YobieBenjamin/hardware-and-silicon/blob/main/blog/06-the-chip-that-says-no-5-what-the-first-experiments-found.md

Rung 3, the runtime and the network:

- Traian Rebedea and others, [NeMo Guardrails: A Toolkit for Controllable and Safe LLM Applications with Programmable Rails](https://arxiv.org/abs/2310.10501), 2023. https://arxiv.org/abs/2310.10501
- NVIDIA Technical Blog, "NVIDIA Open Agent Safety Platform: A Reference for Continuous In-Silicon Agent Monitoring" and "Add Runtime Controls to AI Agents with NVIDIA OpenShell", 28 September 2026; the OpenShell repository, https://github.com/NVIDIA/OpenShell, whose `docs/extensibility/supervisor-middleware/` at main `837fdfd` was read on 21 October 2026
- The Open Secure AI Alliance, started by NVIDIA in July 2026, under the Linux Foundation since September 2026; summarised with the rest of the platform and the shipped middleware contract in https://github.com/YobieBenjamin/hardware-and-silicon/blob/main/docs/NVIDIA.md

Rung 4, the chip:

- James P. Anderson, [Computer Security Technology Planning Study](https://csrc.nist.gov/csrc/media/publications/conference-paper/1998/10/08/proceedings-of-the-21st-nissc-1998/documents/early-cs-papers/ande72.pdf), ESD-TR-73-51, October 1972 (the reference monitor: tamperproof, always invoked, verifiable). https://csrc.nist.gov/csrc/media/publications/conference-paper/1998/10/08/proceedings-of-the-21st-nissc-1998/documents/early-cs-papers/ande72.pdf
- This program, all in the safety-governor repository, https://github.com/YobieBenjamin/safety-governor (the design in docs/00 to docs/04 (https://github.com/YobieBenjamin/safety-governor/tree/main/docs), the tests behind each comparison in docs/07 and docs/17, what is proven in docs/19, the machine-checked invariants in https://github.com/YobieBenjamin/safety-governor/tree/main/proofs, why the gate sits at the ends in docs/23, and the flexHEG, CNAS, RAND and 2026-taxonomy prior art in docs/18 section 8b). The route through all of it is https://github.com/YobieBenjamin/safety-governor/blob/main/START-HERE.md

Rung 5, the person:

- [Regulation (EU) 2024/1689 (the AI Act), Article 14, human oversight](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- This program: the rule's requirement mode in docs/04 section 4 and the hold and APPROVE in section 3, https://github.com/YobieBenjamin/safety-governor/blob/main/docs/04-specification.md; the hold and approval tests in https://github.com/YobieBenjamin/safety-governor/blob/main/tests/test_h08_override.py and https://github.com/YobieBenjamin/safety-governor/blob/main/tests/test_h04_lane.py, the witness tests in https://github.com/YobieBenjamin/safety-governor/blob/main/tests/test_h18_oversight.py; questions 1, 14 and 16 in https://github.com/YobieBenjamin/safety-governor/blob/main/docs/18-viability-and-open-questions.md

The figures: https://github.com/YobieBenjamin/safety-governor/tree/main/docs/figures (the staircase, the three questions, witnesses versus locks, the person on the only path; `make figures` redraws them) and https://github.com/YobieBenjamin/hardware-and-silicon/tree/main/blog/figures (one bad prompt, inside the chip, the switch at the ends; drawn by `blog/tools/make_figures.py` there).
