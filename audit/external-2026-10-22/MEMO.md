# External audit memo, 22 October 2026 (verbatim)

What follows is the audit as the reviewer sent it, unedited: every word, every link, every
objection, including the ones about the research and the ones we have not answered yet. It is
kept here because a program that only publishes the reviews it survived is not doing science.

- **Who:** an independent reviewer who had not seen the work being written.
- **What he audited:** safety-governor at `dccc1e0`, hardware-and-silicon at `11eb119`,
  autonomic-graph-regulation at `4c1374d` (public snapshots, 22 October 2026).
- **Our answer:** [RESPONSE.md](RESPONSE.md) in this folder, finding by finding, with the
  reproductions, the fixes and the tests. The account in the design record is section 9 of
  [docs/REVIEW-2026-10-22-fact-check.md](../../docs/REVIEW-2026-10-22-fact-check.md).
- **How the findings were handled depends on their kind** (the reviewer's distinction, adopted):
  - *Implementation findings* (an unauthorized operation accepted): reproduced on his snapshot
    before anything was changed (the scripts are in this folder), corrected, and each regression
    shown to fail for the intended security reason when the fix is reverted, while the legitimate
    operation still works ([EVIDENCE.md](EVIDENCE.md)).
  - *The formal-model finding:* the model and properties revised; their link to the implementation
    is still open.
  - *Research findings:* the numbers recomputed (all matched); the corrected claims drafted but not
    yet applied in autonomic-graph-regulation; the missing comparison and the nested rerun not run.
  - *Physical and deployment findings:* open; no software change addresses them.
- **Status, finding by finding:** [STATUS.md](STATUS.md) keeps implemented, locally tested,
  propagated, rechecked and still open apart for every finding.

---

**Yes. I found five concrete implementation failures, with specific code paths and locally reproduced behavior. Two break authorization in `safety-governor`. Three break the reference security model in `hardware-and-silicon`.**

The research findings are different: some hypotheses lost decisively, some conclusions exceed the evidence, and some deployment questions remain unanswered.

**Your overall mitigation direction makes sense. The current implementations have serious trust failures.** A governor that accepts an unsigned policy or clears a halt using a heartbeat is failing at the basic job you built it to do.

Here is the evidence.

## What I actually checked

I inspected these public snapshots:

| Repository | Audited commit |
|---|---|
| `safety-governor` | [`dccc1e0`](https://github.com/YobieBenjamin/safety-governor/tree/dccc1e028caa0dfc4fa5798112dc6e22262a03c5) |
| `hardware-and-silicon` | [`11eb119`](https://github.com/YobieBenjamin/hardware-and-silicon/tree/11eb1199debd833abfa3ec9840f719af9c816087) |
| `autonomic-graph-regulation` | [`4c1374d`](https://github.com/YobieBenjamin/autonomic-graph-regulation/tree/4c1374d99e58497d7d0e2afacc8743579c5216f7) |

The governor’s **200 model tests and 20 RTL tests passed**. The hardware reference’s **56 tests passed**. The two Z3 proof scripts and the graph-check script also passed.

Then the additional checks below failed.

These were local checks against the functional models and simulated endpoints. I did not test fabricated silicon or real GPU control. For the research, I reproduced the latest analysis from committed scores and checked its labels against the recorded episodes; I did not regenerate model inference or every large telemetry array.

# 1. The governor accepts a policy with zero signatures

**Severity: Critical in the functional model. Reproduced.**

### Where it fails

In [`govsim/policy.py`, lines 119–137, `verify_policy()`](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/govsim/policy.py#L119-L137).

The verifier reads the required signature threshold from the policy it is currently trying to authenticate:

```python
threshold = int(image["threshold"])
```

It counts valid signatures and rejects only when:

```python
if len(good) < threshold:
    return False, reasons.POLICY_QUORUM
```

With a threshold of zero and no signatures, that rejection never happens.

The fused governance-key hashes constrain which keys may appear. **They do not establish the minimum quorum required to authorize the incoming policy.**

### What I reproduced

Using an otherwise unchanged policy, I incremented its version, set its threshold to zero, and removed its signatures.

The model returned:

```text
Policy verification: accepted
POLICY_PROPOSE: accepted
POLICY_COMMIT: accepted
Installed threshold: 0
```

The mailbox paths rely on that same verifier. Neither adds an independent authorization requirement that repairs the problem: [`govsim/governor.py`, lines 1106–1140](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/govsim/governor.py#L1106-L1140).

### Why this matters

**The policy being judged gets to decide how many signatures are needed to judge it.**

That destroys the intended governance boundary. The question is no longer whether three authorized people approved a change. The incoming document can declare that nobody needs to approve it.

Rejecting zero alone is insufficient. If the incoming document can lower an existing three-signature requirement to one, a single authorized signer can still defeat the intended quorum.

### What fixes it

The authorization rule must come from **already trusted state**:

- Provision the initial governance keys and minimum quorum through a trusted bootstrap.
- Authorize policy changes under the current governance configuration.
- Require the current quorum to approve changes to that configuration.
- Validate threshold type and bounds explicitly.

This needs a regression test at the complete propose-and-commit path, not merely a unit test showing that a normal signed policy verifies.

# 2. A signed heartbeat can clear a halt

**Severity: High. Reproduced across the four-governor model.**

### Where it fails

In [`govsim/governor.py`, lines 312–327, `_check_signed()`](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/govsim/governor.py#L312-L327).

The function checks:

1. Sequence number.
2. Policy epoch.
3. Signature against an authorized key.

It **does not check that the signed payload authorizes the command being executed**.

`CLEAR` calls that generic verifier and then proceeds with clearing the halt: [`_cmd_clear()`, lines 1084–1103](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/govsim/governor.py#L1084-L1103).

Heartbeats use a separate sequence tracker, `hb_last_seq`, rather than the generic mailbox sequence tracker. Consequently, accepting a heartbeat does not consume it in the sequence space subsequently consulted by `CLEAR`: [`_heartbeat()`, lines 940–973](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/govsim/governor.py#L940-L973).

### What I reproduced

In a normally initialized four-node rack:

- A legitimate heartbeat was accepted.
- A legitimate halt put all four governor state machines into `HALT`.
- The normal neighbor checkpoint exchange satisfied the logging acknowledgment requirement.
- The same signed heartbeat was presented to the `CLEAR` command.

The result:

```text
Before:     HALT, HALT, HALT, HALT
CLEAR:      accepted on all four
After:      RUN, RUN, RUN, RUN
```

**No clear-halt instruction had been signed.**

This demonstrates unauthorized clearing of the model’s halt state. It does not establish what physical GPUs would do.

### Why this matters

A valid signature establishes who signed particular bytes. It does not magically authorize whatever command a caller attaches to those bytes.

Here, “the authority says the heartbeat is alive” is being treated as “the authority says clear the halt.”

That is a fundamental authorization failure.

### What fixes it

Sign and verify the complete authorization context: protocol purpose, command, relevant arguments, intended recipient or domain, policy epoch, sequence, and validity window.

A message signed for `HEARTBEAT` must be unusable as `CLEAR`, regardless of whether the signer is authorized for both operations. Replay protection must also match the explicitly defined message domains.

# 3. The reference gate’s signing key is derivable from public information

**Severity: Critical to the reference model’s cryptographic guarantees. Reproduced.**

### Where it fails

In [`hardware_ref/system.py`, lines 236–239](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833abfa3ec9840f719af9c816087/hardware_ref/system.py#L236-L239).

The gate’s signing seed is derived from the CPU and GPU alias **public keys**:

```python
gate_key = SigningKey.from_seed(
    hkdf(cpu_alias_public + gpu_alias_public, ...)
)
```

Those public keys are included in the certificate chains returned by ordinary attestation quotes: [`hardware_ref/root.py`, lines 183–193](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833abfa3ec9840f719af9c816087/hardware_ref/root.py#L183-L193).

### What I reproduced

I obtained the two alias public keys from public quote fields, applied the documented derivation, and compared the resulting signing key’s public key with the gate’s public key.

```text
Publicly derived key matches gate key: True
```

I did not need to inspect the gate’s private-key attribute.

### Why this matters

The code comment explicitly calls this a simulation shortcut. I saw that.

**This shortcut removes the secrecy on which the simulated authorization system depends.** It is therefore unsuitable for demonstrating resistance to forged gate signatures.

A software model can abstract away fabrication, voltage glitches, and transistor behavior. It still needs to preserve the logical fact that an attacker cannot calculate the signing secret from public evidence.

Running public bytes through HKDF does not make them secret.

### What fixes it

Use a secret-rooted derivation in the model, or use a generated private gate key stored within the modeled trusted boundary.

You can model DICE’s interface without exposing a real chip secret. What you cannot do is substitute publicly available identities for secret derivation material and retain the same security claim.

# 4. An old human approval bypasses a stricter current policy

**Severity: High. Reproduced through the simulated endpoint.**

### Where it fails

In [`hardware_ref/gate.py`, lines 206–228, `_approve()`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833ab3ec9840f719af9c816087/hardware_ref/gate.py#L206-L228).

**Correction to the link above:** the exact source is [`hardware_ref/gate.py`, lines 206–228](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833abfa3ec9840f719af9c816087/hardware_ref/gate.py#L206-L228).

After validating the approval and looking up the pending hold, the code retrieves a current rule with the stored rule ID and calls `_allow()`.

It does not rerun the held request through the current rule’s constraints.

### What I reproduced

The sequence was:

1. Submit a simulated **$5,000** payment under a policy that permits that amount with human approval.
2. Leave it pending.
3. Install a properly signed new policy lowering that rule’s maximum to **$2,000**.
4. Confirm that a fresh $5,000 request is denied.
5. Approve the old hold.

The result:

```text
Current policy maximum:       $2,000
Fresh $5,000 request:          denied
Old $5,000 hold:               approved
Endpoint result:              simulated $5,000 transfer
```

The stale request received a ticket under the current policy even though that policy rejects the same request when evaluated normally.

### Why this matters

A human approval is supposed to satisfy an additional condition on an eligible action. Here it allows a request to escape a policy change.

If you intend humans to override current constraints, that needs a distinct, explicitly authorized override mechanism. The ordinary approval path cannot silently acquire that power.

### What fixes it

Bind holds to the policy epoch and invalidate them when that epoch changes, or fully reevaluate them under the new policy before approval can produce a ticket.

This is especially concrete because the governor implementation already clears pending holds on a policy change in [`_accept_policy()`, lines 218–229](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/govsim/governor.py#L218-L229). The reference hardware gate does not enforce the same behavior.

# 5. An old signed epoch rolls the endpoint backward

**Severity: High. Reproduced through the simulated endpoint.**

### Where it fails

In [`hardware_ref/endpoints.py`, lines 81–86, `set_policy_epoch()`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833abfa3ec9840f719af9c816087/hardware_ref/endpoints.py#L81-L86).

The endpoint verifies that an epoch message was signed by the gate, then installs the supplied policy ID.

It does not establish that the message is newer than the currently installed epoch. A policy hash identifies content; it provides no ordering.

### What I reproduced

I obtained a legitimate ticket for a small simulated payment, then installed a new policy removing payment permissions.

The old ticket initially failed correctly:

```text
ticket.policy_stale
```

After presenting the previous, legitimately signed epoch message, the endpoint accepted that old ticket and executed the simulated payment.

The gate’s commit path also failed to stop this because it does not compare the ticket’s policy ID with its current policy before committing: [`hardware_ref/gate.py`, lines 321–337](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833abfa3ec9840f719af9c816087/hardware_ref/gate.py#L321-L337).

### Why this matters

**Authenticity is not freshness.**

The endpoint knows the gate signed that epoch at some point. It does not know that the epoch is still current.

This defeats the intended invalidation of outstanding permissions after a policy change.

### What fixes it

Use a signed, monotonically increasing epoch number with a durable high-water mark. Reject older epochs. Also check the current epoch at the gate’s commit point, so endpoint state alone cannot resurrect a revoked permission.

# 6. Why the passing tests and proofs did not catch this

The existing suites establish that their tested cases work. They do not establish the missing authorization properties above.

The formal model illustrates the gap particularly clearly.

In [`proofs/core_invariants.py`, lines 94–110](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/proofs/core_invariants.py#L94-L110), the abstract `execute` transition checks heartbeat, ticket epoch, and whether the ticket was spent. It does **not** require the machine to be unhalted.

I asked the solver whether this sequence was possible:

1. Issue a valid ticket.
2. Halt.
3. Execute that ticket while remaining halted.

The solver returned **SAT**, meaning the abstract machine permits it.

Meanwhile, property P5 only establishes that the `halted` flag stays set without a quorum. It does not establish that no action executes while the flag is set: [`lines 160–172](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/proofs/core_invariants.py#L160-L172).

There is a crucial qualification: **the functional implementation does check `state == RUN` at commit**, so this particular abstract trace is not evidence of an additional runtime bypass. See [`commit_from_endpoint()`, lines 697–711](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/govsim/governor.py#L697-L711).

The finding is that the proven properties and the implemented security contract are not yet fully connected.

Likewise, a proof that assumes a Boolean `quorum` cannot discover that the implementation lets an unsigned document manufacture its own quorum requirement. You need a demonstrated correspondence between the authentication code and that abstract assumption.

Your own program lists implementation-to-proof conformance as open. That limitation needs to stay attached to every statement about what is “proven.” [Source: `START-HERE.md`, lines 99–108.](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/START-HERE.md#L99-L108)

## Existing disclosed failures also remain blockers

Your gap register already identifies:

- Revocations are stored but never enforced.
- `CAP_REQUEST` ignores the sandbox setting.
- Hazard budgets are per governor, allowing a distributed session more than one budget.
- Workload-token fingerprints survive policy changes.

I am **not presenting those as my discoveries**. They are your own documented findings. They nevertheless remain failures of the controls someone could reasonably expect those fields to provide. [Source: gap register G1–G5.](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/docs/REVIEW-2026-10-22-fact-check.md#L202-L214)

# 7. Where the research actually lost

The research repository deserves a precise reading. It contains meaningful negative results and a later positive result. Flattening all of that into “it works” or “it is bullshit” would misrepresent your own evidence.

## YB-0050: the layered system lost to self-consistency

At the reported 10% false-alarm budget:

| Method | Errors caught out of 530 |
|---|---:|
| Self-consistency alone | **498** |
| Layered system | **469** |
| Non-LLM stack | **360** |

The layered system was **5.5 percentage points worse** than self-consistency, with a reported interval of **−7.8 to −3.2 points**.

The stack without the self-consistency signal was approximately **26 points worse**.

Those are substantive negative findings. On this benchmark, the proposed combination spent alarm budget less effectively than the stronger component alone. More layers did not automatically produce better detection. [Source: YB-0050 results, lines 27–44.](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0050-powered-decider/README.md#L27-L44)

The same experiment found a probe advantage over a trained text monitor on answered episodes, but that advantage disappeared when never-answered episodes were included as failures. Population definitions materially change the result.

## YB-0051: the newer positive result reproduces

On the later test set:

| Method | Errors caught out of 541 | False alarms among 5,922 correct answers |
|---|---:|---:|
| Probe alone | 204 | 59 |
| Self-consistency, four samples | 296 | 50 |
| C2 combined detector | **339** | **59** |

The independent analysis reproduced the headline counts and all three published bootstrap intervals to their reported rounding. The packed labels and disagreement scores also matched the corresponding recorded episodes.

**C2 beating the probe is supported by these data.** That is a useful result. [Source: YB-0051 results and comparisons.](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0051-low-false-alarm-precision/README.md#L15-L50)

The unresolved question is how much of that improvement requires internal telemetry.

## A cheaper missing baseline nearly matches the headline count

I ran an **exploratory, post hoc** comparison using:

- Four-sample self-consistency.
- The trained text-monitor score.
- The same logistic-regression regularization used by C2.
- Fitting on the prior reference seeds and evaluation on the published later test seeds.

At the same retrospective operating point of **59 false alarms**:

| Combination | Errors caught |
|---|---:|
| Published full C2 | **339** |
| Exploratory self-consistency plus text | **336** |

This comparison used the committed reference and test scores and the published C2 modeling convention. [Source: C2 definition](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0051-low-false-alarm-precision/tests/candidates.py#L18-L30) and [committed score artifacts](https://github.com/YobieBenjamin/autonomic-graph-regulation/tree/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0051-low-false-alarm-precision/data).

**This does not prove equivalence.** I chose the comparison after the published results existed, and its threshold was calibrated using test labels in the same manner as the published operating-point analysis.

But 336 versus 339 makes this baseline essential before attributing the result to internal-state access or using it to justify specialized telemetry hardware.

The current evidence supports “this combination beats the probe.” It does not yet settle “activation access provides enough additional value to justify its integration cost.”

# 8. The pooled 1% false-alarm rate hides a 13.1% subgroup rate

**This is a newly computed result from the committed YB-0051 scores.**

At the published C2 operating point:

| Population | Correct answers incorrectly flagged | False-alarm rate |
|---|---:|---:|
| All tasks pooled | 59 / 5,922 | **0.996%** |
| Modular exponentiation | 46 / 352 | **13.07%** |

One task family accounts for **46 of the 59 false alarms**. The calculation uses the committed task labels and C2 scores at the published threshold. [Source data.](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0051-low-false-alarm-precision/data/test_scores.npz)

The pooled arithmetic is correct. **The operational interpretation is fragile.**

A deployment with more modular-exponentiation-like tasks could experience a much higher alarm burden without any change to the detector.

For a system that may hold actions or halt compute, an average across a convenient task mixture is insufficient. You need false alarms, missed errors, and uncertainty by task and action class, followed by validation on the intended deployment mixture.

The claimed precision at a hypothetical 1% error prevalence is also a projection. It assumes the measured detection and false-alarm behavior remains applicable as prevalence changes. It is not observed precision from a deployment whose actual error prevalence was 1%.

# 9. Three specific methodological problems

## A. The operating threshold is selected using test labels

The scoring code chooses its threshold using the correct answers in the evaluation sample. The bootstrap repeats that threshold selection within each resample: [`decider.py`, lines 12–23 and 47–67](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0051-low-false-alarm-precision/src/decider.py#L12-L67).

That is a legitimate way to estimate a retrospective ROC operating point. **It is not a demonstration that a threshold frozen before deployment achieves the same false-alarm rate.**

The distinction was already raised for earlier experiments in your corrections ledger. I am not treating it as newly discovered secret training leakage. [Source: CORRECTIONS B6.](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/CORRECTIONS.md#L76-L85)

There is encouraging sensitivity evidence: fixing C2’s threshold using the previous reference data produced **307 catches and 44 false alarms** on the later test set, or a **0.743% false-alarm rate**.

The signal survives. However, that reference data also fitted C2, so this still does not replace a separate calibration split and prospective test.

## B. “Leave one task out” still uses that task during model selection

In YB-0047, the code selects the probe layer and regularization using the full derivation mixture. It then removes one task category for weight fitting while retaining those selections.

The exact locations are:

- Full-mixture selection: [`experiment.py`, lines 52–56](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0047-text-baseline-transfer/tests/experiment.py#L52-L56).
- Task-held-out refit with those same hyperparameters: [`lines 75–85`](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0047-text-baseline-transfer/tests/experiment.py#L75-L85).

The held-out task’s derivation labels therefore influence model selection.

This is not direct fitting on the final evaluation labels, and I have not quantified its numerical impact. But it weakens the claim of transfer to a task excluded from training decisions.

**Fix:** redo layer and hyperparameter selection inside each outer task holdout.

## C. A nonsignificant result is turned into an unsupported negative conclusion

YB-0051 estimates a **7.4-point recall improvement** from eight samples versus four, with an interval spanning approximately **−5.8 to +16.8 points**.

The README then concludes that the tie-break, rather than more samples, supplies the resolution. That conclusion does not follow. The interval includes both no improvement and a substantial improvement. [Source: H3 and its interpretation, lines 18–24.](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0051-low-false-alarm-precision/README.md#L18-L24)

Keeping four samples as the default on cost grounds is reasonable. Claiming the experiment established that more samples do not add useful resolution is not.

Preregistering that interpretation does not repair the inference.

# 10. The research detector and the runtime observer are different things

The runtime observer scores request strings and context using pattern families and hand-chosen weights. Its README explicitly says those weights are judgment rather than measurement and require a labeled evaluation set. [Source: observer scoring documentation.](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/observer/README.md#L22-L58)

It is not the activation probe or C2 combination evaluated in YB-0051.

The hardware reference also instantiates a `StubObserver` in its normal construction path. [Source: `hardware_ref/system.py`, lines 230–245.](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833abfa3ec9840f719af9c816087/hardware_ref/system.py#L230-L245)

Consequently, three separate questions remain:

1. Does the detector recognize the relevant dangerous behavior?
2. Does the signed assertion accurately bind that judgment to the proposed action?
3. Does the actual endpoint enforce the resulting decision?

Passing an envelope-format test answers part of question two. It does not answer question one or establish the complete chain.

The research also evaluates actual model runs on generated arithmetic, counting, and calendar tasks. Those are valid error-detection experiments, but correctness on those tasks is not the same outcome as unauthorized actions, deception, or harmful planning. [Source: task generator and recorder.](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/agr/recorder.py#L23-L39)

A model can execute a harmful objective coherently. A harmless difficult task can look anomalous. The detector has to demonstrate the distinction relevant to the action gate.

# 11. The hardware claims still depend on unresolved physical access

Your own board-interface register records that:

- HGX H100 reset signals exposed at the connector are grouped.
- Public evidence for the power brake is at board level.
- Per-GPU power enable remains unknown from the public documentation examined.

Those are your register’s B2–B4 findings, not assumptions I am inventing. [Source: board-lever register.](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/docs/research/board-lever-register.md#L23-L26)

Your README also clearly says the chip is not taped out and the cryptographic engines are specified integrated IP. I am taking those qualifications seriously. [Source: implementation status.](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/README.md#L124-L135)

The engineering question is therefore specific: **on one named server configuration, can the governor independently prevent the relevant effect, within a measured deadline, despite hostile host behavior?**

A GPIO assertion, a simulated state transition, and prevention of an external effect are different measurements. The physical prototype needs the last one.

The tiny reported probe cost also needs careful labeling. The experiment times scoring over already recorded inputs, while the inference denominator includes telemetry-tap overhead. That is disclosed in the protocol. It does not measure the complete cost of acquiring, transporting, authenticating, and evaluating live telemetry. [Source: timing protocol, lines 57–63.](https://github.com/YobieBenjamin/autonomic-graph-regulation/blob/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0050-powered-decider/docs/PREREGISTRATION.md#L57-L63)

# What I would do with this project now

**Keep pursuing the external action gate, explicit permissions, bounded budgets, revocable authority, and independent enforcement. Those are coherent mitigation mechanisms.**

But I would change the work order.

1. **Fix the five reproduced failures first.** Each should become a regression that fails on the audited snapshot and passes only after the intended authorization property is restored.

2. **Close the disclosed control gaps.** Revocation, sandbox restrictions, policy transitions, and distributed budgets need enforceable semantics. A schema field that gets stored but never consulted is dead weight in a security claim.

3. **Validate one complete action path.** Choose a narrow workflow with an explicit policy, a real observer implementation, and an endpoint that cannot perform the effect without authorization. Test policy changes, delayed approvals, replay, restart, partitions, and revocation through that entire path.

4. **Run the missing scientific comparison.** Preregister internal telemetry against self-consistency plus trained text, with separate training, calibration, and untouched test data. Measure prevented bad actions, false holds, completion rates, review burden, and total latency.

5. **Prove one physical enforcement configuration before expanding the chip story.** Name the board, interface, control authority, protected effect, and measured deadline. Resolve the vendor dependencies against that configuration.

My assessment is blunt: **the architecture is worth continuing; the current authorization implementations are not ready to be trusted.** The research contains a reproducible detection signal, but the incremental value of internal telemetry and its relevance to harmful agent behavior still need to be established.

The most damaging findings here are ordinary security engineering failures: self-authorized policy changes, signatures accepted for the wrong purpose, a signing secret derived from public data, and stale authority surviving policy changes. Those are fixable. Until they are fixed, “the tests pass” provides far less assurance than the project needs.