# Response to the 22 October audit of The Chip That Says No

*The reply to [MEMO.md](MEMO.md), sent to the reviewer and kept here beside his memo. Links are pinned to the commits that carry each fix.*

Oct 22, 2026 · @Yobie Benjamin

## You were right, and here is the proof that we listened

Thank you. You found five real failures in the code and a hole in the proofs, and every one of those six reproduced on the exact snapshots you audited. I didn't take a single line of your memo on faith, because you wouldn't want me to and because this project dies the day we start believing things without running them. For each of the five implementation findings, and the code side of the proof finding, I did three things, in this order:

1. **Reproduced it on your snapshot** (`dccc1e0` for the governor, `11eb119` for the reference stack) with a script that prints REPRODUCED or NOT. All six reproduced.
2. **Fixed the cause, not the symptom**, and wrote a regression test for it.
3. **Put the old code back** and ran the test again, to make sure the test actually catches the bug, and catches it *for the security reason*: the failure has to be an assertion that the unauthorized operation was accepted, never an import or interface error, and the legitimate operation has to keep working. [EVIDENCE.md](EVIDENCE.md) is the record, one row per finding. Doing this caught three of my own tests passing or failing for the wrong reason; they're described below and fixed.

Your other findings are a different kind, and I've given them different dispositions instead of pretending a patch closes them. The research objections get recomputed numbers and corrected claims (drafted, not yet applied in that repository); the missing comparison and the nested rerun still have to be run; the physical-enforcement questions stay open until there's a board on a bench. [STATUS.md](STATUS.md) keeps five statuses apart for every finding: implemented, locally tested, propagated to GitHub, rechecked against what was propagated, and what is still open.

While fixing your finding 5 I found two more holes of the same family that you didn't report. They're fixed too.

Let me say the goal plainly, because it decides what matters here. The point of all this is a chip that stops dangerous AI actions from **outside** the model. Not a classifier, not RLHF, not another model grading the first one. A small, dumb, unbribable piece of silicon that only lets an action happen when a rulebook signed by people the model can't reach says yes, and the device doing the action checks that yes for itself. Five of your findings were holes in exactly that outside layer. They are the ones that would have killed the idea, and they are the ones I fixed first. Your research objections are about AI checking AI, which in this design is only ever a witness, never the lock, and section 5 says what your numbers mean for that.

The doomers say this can't be done. Maybe they're right and we fail. But we don't get to find out by hand-waving, and your memo made the thing measurably harder to break. That's the job.

## Where everything lives

Three commits carry the work. Every link below is pinned to its commit hash, so it points at exactly the code I'm describing, forever.

**One honest caveat about the links.** As I write this the commits are packaged and waiting on my Mac; GitHub `main` is still at the snapshots you audited. The links go live the moment I run the publish script. If one 404s, that's why, and it won't for long.

| Repository | Commit | What it carries |
| --- | --- | --- |
| safety-governor | [`c7df7cb`](https://github.com/YobieBenjamin/safety-governor/commit/c7df7cb60bca338da4f023ca15f2d4ce5d03b398) | Findings 1 and 2: the fused quorum, and signatures bound to their command |
| safety-governor | [`6743c9f`](https://github.com/YobieBenjamin/safety-governor/commit/6743c9f8ac951becc1e5fad8c47cf685120ea297) | Finding 6 (the proof), the four disclosed gaps, the review record, the reproduction scripts |
| hardware-and-silicon | [`b36ed52`](https://github.com/YobieBenjamin/hardware-and-silicon/commit/b36ed52fb7b2db6b682ff942b3c2af020642a551) | Findings 3, 4 and 5, plus the two extra holes |

The snapshots you audited, for comparison: [safety-governor `dccc1e0`](https://github.com/YobieBenjamin/safety-governor/tree/dccc1e028caa0dfc4fa5798112dc6e22262a03c5) and [hardware-and-silicon `11eb119`](https://github.com/YobieBenjamin/hardware-and-silicon/tree/11eb1199debd833abfa3ec9840f719af9c816087).

The paperwork:

- **The full record**, with your findings in section 9 and my own same-day findings in section 8: [docs/REVIEW-2026-10-22-fact-check.md](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/docs/REVIEW-2026-10-22-fact-check.md)
- **The reproduction scripts**, so you can rerun your own checks against the fixed code: [audit/external-2026-10-22/](https://github.com/YobieBenjamin/safety-governor/tree/6743c9f8ac951becc1e5fad8c47cf685120ea297/audit/external-2026-10-22) (`repro_sg.py` for findings 1 and 2, `repro_hs.py` for 3 to 5, `repro_rollback.py` for the extra hole, `check_research.py` for the research numbers)
- **The new tests**: [tests/test\_h19\_authorization.py](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/tests/test_h19_authorization.py) (16 tests), [tests/test\_h20\_closed\_gaps.py](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/tests/test_h20_closed_gaps.py) (8 tests), and [hardware-and-silicon tests/test\_audit\_2026\_10\_22.py](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/tests/test_audit_2026_10_22.py) (11 tests)
- **The proof**: [proofs/core\_invariants.py](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/proofs/core_invariants.py), now P0 to P13

The counts after all of it: 248 governor tests (227 model, 21 RTL), 67 reference-stack tests, every proof holds, and the attack catalogue gives the same verdicts as before, 75 attacks blocked and 12 baselines allowed. You ran 200, 20 and 56.

## Your six findings, one at a time

| # | Your finding | Reproduced on your snapshot | Fixed in | Regression tests |
| --- | --- | --- | --- | --- |
| 1 | Policy with zero signatures accepted | Yes: propose ok, commit ok, installed threshold 0 | [`c7df7cb`](https://github.com/YobieBenjamin/safety-governor/commit/c7df7cb60bca338da4f023ca15f2d4ce5d03b398) | 6, plus proof P10 and P11 |
| 2 | Heartbeat clears a halt | Yes: 2 of 4 governors cleared in my run, 4 of 4 in yours | [`c7df7cb`](https://github.com/YobieBenjamin/safety-governor/commit/c7df7cb60bca338da4f023ca15f2d4ce5d03b398) | 9, plus a replay sweep, proof P12, and 1 RTL test |
| 3 | Gate signing key derivable from public data | Yes: the publicly derived key matched | [`b36ed52`](https://github.com/YobieBenjamin/hardware-and-silicon/commit/b36ed52fb7b2db6b682ff942b3c2af020642a551) | 2 |
| 4 | Old approval bypasses a stricter policy | Yes: $5,000 paid after the cap fell to $2,000 | [`b36ed52`](https://github.com/YobieBenjamin/hardware-and-silicon/commit/b36ed52fb7b2db6b682ff942b3c2af020642a551) | 3 |
| 5 | Old signed epoch rolls the endpoint back | Yes: `ticket.policy_stale`, then executed after the replay | [`b36ed52`](https://github.com/YobieBenjamin/hardware-and-silicon/commit/b36ed52fb7b2db6b682ff942b3c2af020642a551) | 2 |
| 6 | The proof lets a ticket execute while halted | Yes: the old abstract `execute` step didn't require RUN | [`6743c9f`](https://github.com/YobieBenjamin/safety-governor/commit/6743c9f8ac951becc1e5fad8c47cf685120ea297) | proof P13, plus 1 code test |

Why finding 2 cleared 2 of 4 for me and 4 of 4 for you: a CLEAR also needs a neighbour to have acknowledged the logged cause, and your checkpoint exchange satisfied all four neighbours while mine satisfied two. Same bug either way.

### Finding 1: the policy decided its own quorum

**What was wrong.** [`verify_policy()` at `dccc1e0`](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/govsim/policy.py#L119-L137) read `k` from the very image it was judging. Threshold 0, no signatures, `len(good) < 0` is false, door open. You nailed it: the fused key hashes said *which* keys could sign, but nothing trusted said *how many* had to.

**The fix, from trusted state, the way you asked.**

1. **The quorum is burned in at manufacture.** [`Fuses.governance_threshold`](https://github.com/YobieBenjamin/safety-governor/blob/c7df7cb60bca338da4f023ca15f2d4ce5d03b398/govsim/fuses.py#L27-L44) sits next to the governance key hashes. Unset, it defaults to a majority of the fused keys, never below one.
2. **An image can raise k, never lower it.** [`verify_policy()` now](https://github.com/YobieBenjamin/safety-governor/blob/c7df7cb60bca338da4f023ca15f2d4ce5d03b398/govsim/policy.py#L120-L149) takes the fused minimum. It refuses a threshold under 1, above the number of distinct keys, or below the fused floor. The k that counts is the larger of the two.
3. **Each key counts once**, however often the image lists it.
4. **The floor ratchets up.** [`_accept_policy()`](https://github.com/YobieBenjamin/safety-governor/blob/c7df7cb60bca338da4f023ca15f2d4ce5d03b398/govsim/governor.py#L218-L226) bumps the fused threshold when an edition asks for more signatures. [`bump_governance_threshold()`](https://github.com/YobieBenjamin/safety-governor/blob/c7df7cb60bca338da4f023ca15f2d4ce5d03b398/govsim/fuses.py#L68-L72) refuses to go down, like the other thermometer counters in silicon.

The core of it:

```python
threshold = int(image["threshold"])
if threshold < 1 or threshold > len(keys):
    return False, reasons.POLICY_QUORUM
if min_threshold is not None:
    if threshold < int(min_threshold):
        return False, reasons.POLICY_QUORUM
    threshold = max(threshold, int(min_threshold))
```

**Tested on the full propose and commit path, as you asked**, not just a unit test of the verifier. In [test\_h19\_authorization.py](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/tests/test_h19_authorization.py#L19-L71):

- `test_unsigned_image_with_threshold_zero_refused`: your exact case, at `POLICY_PROPOSE` and at the boot-load path;
- `test_image_cannot_lower_k_below_the_fused_threshold`: one real governance signature with k claimed as 1, your "rejecting zero alone is insufficient" point;
- `test_threshold_above_the_number_of_keys_refused`;
- `test_a_key_listed_twice_counts_once`;
- `test_an_edition_that_raises_k_raises_the_floor`: raise k to 4, then try to drop back to 3;
- `test_the_fused_threshold_only_goes_up`.

Against your snapshot, the reproduction script prints `propose=True/ok commit=True/ok installed threshold=0 REPRODUCED`. Against the fix, `propose=False/policy.quorum_not_met ... installed threshold=3 NOT reproduced`.

**The restored rule, in full (added in [`28927e3`](https://github.com/YobieBenjamin/safety-governor/commit/28927e386d564160dc018a17a2745ebc2b9a7298) after your follow-up).** Rejecting zero, and even fusing a floor, wasn't your whole criterion: the governance configuration currently trusted has to authorize its own replacement, keys included. Now it does. The chip keeps a protected record of the configuration in force: the keys whose signatures count, the k they must reach, and the edition that set them. A new rulebook needs k distinct signatures from *those* keys, whatever keys and threshold it names itself. So the same quorum can rotate the keys or change k, never below the floor fused at manufacture, and only the very first rulebook on a new chip is admitted by the fused key hashes. This replaces the ratchet I first built (k could only rise), which was stricter than it needed to be and still let the image's own keys do the signing. New tests: k raised to 4 binds the next change, and four in force can lower it to 3; the current quorum rotates to five new keys, after which the old keys authorize nothing, before and after a restart; attacker keys that name and sign themselves are refused; k below the floor is refused. The proof follows: the threshold in force (`kfuse`) is set by each edition and never falls below a fixed floor (`kfloor`).

### Finding 2: a signature authorized whatever command it was stapled to

**What was wrong.** [`_check_signed()` at `dccc1e0`](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/govsim/governor.py#L312-L327) checked sequence, epoch and that a key the rulebook trusted had signed. It never asked what the key had signed *for*. You were dead right about why it got worse: heartbeats live in their own sequence space (`hb_last_seq`), so an already-accepted heartbeat was still fresh as far as `CLEAR` knew.

**The fix: sign the whole authorization context, and split the keys.**

1. **Every signed command names itself.** The payload must carry `"type": "<command in lower case>"`. A good signature over anything else gets `mailbox.wrong_command`, and the sequence number isn't consumed. This now covers all 11 commands that use [`_check_signed()`](https://github.com/YobieBenjamin/safety-governor/blob/c7df7cb60bca338da4f023ca15f2d4ce5d03b398/govsim/governor.py#L317-L344): BEGIN\_MODEL, END\_MODEL, REQUEST, APPROVE, COMMIT, ALARM\_CLEAR, SIGN\_OUTPUT, CAP\_REQUEST, HALT, CLEAR and ROSTER\_JOIN.
2. **HALT and CLEAR name their recipient and expire.** They must carry the target `chip_id` and an `expires_at` that hasn't passed and is no more than [`AUTHORITY_TTL_S` = 60 s](https://github.com/YobieBenjamin/safety-governor/blob/c7df7cb60bca338da4f023ca15f2d4ce5d03b398/govsim/governor.py#L37) ahead. You can't bank a CLEAR and spend it next week, and a CLEAR for chip A doesn't clear chip B.
3. **The heartbeat key can't say stop or go.** HALT and CLEAR are now signed by [`authority_keys`](https://github.com/YobieBenjamin/safety-governor/blob/c7df7cb60bca338da4f023ca15f2d4ce5d03b398/govsim/governor.py#L256-L259), a set the rulebook lists separately from the heartbeat key. The key that says "alive" every second never says "stop" or "go". The heartbeat handler also [checks its own type](https://github.com/YobieBenjamin/safety-governor/blob/c7df7cb60bca338da4f023ca15f2d4ce5d03b398/govsim/governor.py#L961-L962).
4. **The silicon gets the same check.** [The RTL mailbox](https://github.com/YobieBenjamin/safety-governor/blob/c7df7cb60bca338da4f023ca15f2d4ce5d03b398/rtl/governor_rtl/mailbox.py#L54-L63) now compares the command byte inside the verified payload (`signed_cmd`, read out by the crypto core) with the frame's command. A mismatch gets a new status, 7 `wrong command`, and the sequence register isn't advanced. The Verilog is regenerated.

```python
key = verify_any(env, self._keys(cls, rule_id))
if key is None:
    return False, reasons.MBOX_BAD_SIGNATURE
if p.get("type") != cmd.lower():
    return False, reasons.MBOX_WRONG_COMMAND
if cls == "authority":
    if p.get("chip_id") != self.chip_id:
        return False, reasons.MBOX_WRONG_COMMAND
    exp = p.get("expires_at")
    if not isinstance(exp, (int, float)) or exp <= self.clock.now() or exp > self.clock.now() + AUTHORITY_TTL_S:
        return False, reasons.MBOX_EXPIRED
```

**Defence in depth, measured.** I reverted the type check alone, and your exact attack (heartbeat as CLEAR) was *still* refused, because the heartbeat key is no longer an authority key. Each lock stops it by itself.

**Tests** in [test\_h19\_authorization.py](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/tests/test_h19_authorization.py#L75-L200):

- your case, `test_a_heartbeat_does_not_clear_a_halt`;
- `test_the_heartbeat_key_cannot_sign_a_clear`, even typed as a clear and aimed at the right chip;
- `test_a_halt_is_not_a_clear`;
- `test_a_clear_for_another_chip_is_refused`;
- `test_an_expired_clear_is_refused`;
- `test_a_clear_good_for_a_day_is_refused`;
- `test_an_approval_does_not_clear_an_alarm`;
- `test_the_mailbox_names_the_wrong_command`;
- the one I'm proudest of, **`test_no_signed_message_is_accepted_by_a_command_it_was_not_signed_for`**. It records every signed frame a normal run delivers: heartbeats, model loads, requests, approvals, commits, output signing, alarm clears, halts, clears and roster joins. Then it wipes the replay counters, so the sequence check can't hide a missing type check, and fires each frame into every *other* signed command. Zero accepted. That one test would have caught your finding on day one.

The RTL side is pinned by [`test_mailbox_refuses_a_good_signature_over_another_command`](https://github.com/YobieBenjamin/safety-governor/blob/c7df7cb60bca338da4f023ca15f2d4ce5d03b398/rtl/tests/test_blocks.py#L437-L469).

**Three of my tests failed your "for the right reason" test, and I fixed them.** When I reverted each fix and checked *why* each test failed:

- **The CLEAR-for-another-chip test passed for the wrong reason.** On a two-governor rack, a CLEAR also needs a neighbour to have acknowledged the logged cause. My test never gave it one, so it passed even with the chip binding removed. Every CLEAR test now sets up a halt that a legitimate CLEAR would clear, asserts the refusal code `clear.unauthorized`, and then shows the right CLEAR succeeding under the identical setup. That control is what proves the refusal was the authorization.
- **Two finding-1 tests aren't regressions for your finding.** The old code also refused "threshold above the number of keys" and "attacker keys that sign themselves". They're hardening of the new rotation rule, and EVIDENCE.md now lists them as tests that must pass on the fixed tree, not as tests that catch your bug.
- **Your heartbeat attack is stopped by three independent locks:** the command binding, the chip and expiry binding (a heartbeat names no chip), and the separate authority key. Reverting one or two of them didn't reopen it, so the evidence for finding 2 reverts all three, which is what `dccc1e0` actually was.

### Finding 3: the gate's "secret" key was computed from public bytes

**What was wrong.** [`system.py` at `11eb119`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833abfa3ec9840f719af9c816087/hardware_ref/system.py#L236-L239) seeded the gate key from the two alias *public* keys, which every quote hands out. My comment called it "enough for a simulation". It wasn't. Your line is the right one: a model can abstract the transistors, but it can't abstract away the fact that the attacker doesn't know the secret.

**The fix.** [`SiliconRoot.derive_key()`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/root.py#L168-L177) derives a key from the device's secret CDI, which is the fused unique device secret mixed with the digest of what booted. That's real DICE semantics: same chip and same code give the same key after a restart, different code gives a different key, and nothing public goes in. The CDI is held in a [private attribute set at boot](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/root.py#L146-L148), and [the gate now takes its key from the CPU's CDI](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/system.py#L236-L240):

```python
gate_key = cpu.derive_key(b"gate-signing-key")
```

**Tests** in [test\_audit\_2026\_10\_22.py](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/tests/test_audit_2026_10_22.py):

- `test_gate_key_cannot_be_computed_from_public_quotes`: your exact derivation must no longer match;
- `test_gate_key_is_stable_across_restart_and_bound_to_the_chip`: same key after a restart, a different key on a different chip.

The second test is the one that keeps the fix honest: the old shortcut existed to make restart work, and restart still works.

### Finding 4: an approval smuggled a request past a policy change

**What was wrong.** [`_approve()` at `11eb119`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833abfa3ec9840f719af9c816087/hardware_ref/gate.py#L206-L228) found the hold, looked up its rule by id in the *current* policy, and minted, without asking whether the current policy would allow the request at all. The governor already dropped holds on an edition change. The reference gate didn't. Two implementations of one rulebook disagreeing is exactly what experiment L5 exists to catch, and it hadn't caught this.

**The fix: both of your options, belt and braces.**

1. **A hold belongs to its policy.** Every hold [records the `policy_id` it was parked under](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/gate.py#L212).
2. **A new policy drops the old holds.** [`load_policy()`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/gate.py#L115-L140) drops every hold from another policy. The new rules re-decide, the same as the governor.
3. **Approval re-checks anyway.** An approval for a hold whose `policy_id` isn't the current one is [refused with `approval.policy_changed`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/gate.py#L240-L244). That catches a hold that somehow survived, say restored from disk.

You're right that a human overriding current constraints should be a separate, explicitly authorized mechanism. The ordinary approval path no longer has that power. If we ever want an override lane, it gets its own rule, its own quorum and its own reason code.

**Tests:**

- `test_old_hold_cannot_be_approved_after_the_policy_tightens`: your $5,000 and $2,000 sequence, no execution;
- `test_a_hold_under_the_current_policy_still_approves`: the normal path still works;
- `test_a_hold_whose_policy_changed_is_refused_even_if_it_survived`.

### Finding 5: authentic is not fresh

**What was wrong.** [`set_policy_epoch()` at `11eb119`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833abfa3ec9840f719af9c816087/hardware_ref/endpoints.py#L81-L86) accepted any gate-signed epoch. A policy hash says *what*, never *when*. And [`commit()`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/11eb1199debd833abfa3ec9840f719af9c816087/hardware_ref/gate.py#L321-L337) never compared the ticket's policy with its own. "Authenticity is not freshness" is going on a t-shirt.

**The fix, exactly as you specified, two locks.**

1. **A durable high-water mark.** The signed epoch now [carries the policy version](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/gate.py#L141-L146). The endpoint keeps a durable mark in [`DurableState.set_epoch()`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/ledger.py#L142-L153), and [the endpoint passes the version in](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/endpoints.py#L81-L87). An older epoch is refused, and so is a different policy under the same version. The mark survives restart.
2. **The gate checks at commit.** It [refuses to commit a ticket from a policy it has replaced](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/gate.py#L349-L358). An endpoint that's been fooled by any means still can't get the old ticket committed.

**Tests:**

- `test_replayed_old_epoch_is_refused_and_the_old_ticket_stays_dead`: your sequence;
- `test_the_gate_refuses_to_commit_a_ticket_from_a_replaced_policy`: I set the endpoint's epoch back *by hand* to simulate a fooled endpoint, and the gate's lock alone still holds.

### Finding 6: the proof and the code weren't the same machine

**What was wrong.** You asked Z3 for issue, then halt, then execute while halted, and got SAT. The [abstract `execute` step at `dccc1e0`](https://github.com/YobieBenjamin/safety-governor/blob/dccc1e028caa0dfc4fa5798112dc6e22262a03c5/proofs/core_invariants.py#L94-L110) didn't require RUN. The code did, at [`commit_from_endpoint()`](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/govsim/governor.py#L752-L759). And P5 only said the halt flag stays set, not that nothing executes while it's set.

Your sharper point stands too. A proof that takes "a quorum signed" as a given boolean can never find a bug in how the quorum is counted. That is exactly why the proofs missed findings 1 and 2.

**The fix, in [core\_invariants.py](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/proofs/core_invariants.py):**

1. **The proof computes what the chip computes.** The two authorizations are no longer free inputs. [`quorum_of()`](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/proofs/core_invariants.py#L111-L116) counts distinct signatures against a fused threshold `kfuse`, which is state that only rises, whatever threshold the image claims. [`clear_auth_of()`](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/proofs/core_invariants.py#L118-L120) requires a signature over CLEAR, for this chip, in date.
2. **`execute` requires RUN**, [like the code](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/proofs/core_invariants.py#L131-L132).
3. **Four new properties are proved** ([lines 188 to 195](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/proofs/core_invariants.py#L188-L195)):
   - **P10**: an edition change needs at least the fused number of distinct signatures, whatever the image claims;
   - **P11**: the fused threshold never falls;
   - **P12**: nothing but a signature over a CLEAR leaves the halt;
   - **P13**: nothing executes while halted, not even against a ticket issued before the halt.
4. **Regression checks inside the proof.** The file also asks Z3 to break each new property on the old machine, using [`old_rules()`](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/proofs/core_invariants.py#L212-L216) and `execute_needs_run=False`. P10, P12 and P13 all come back SAT there, so the proof would have caught all three. A proof that can't fail on the known-bad version isn't proving anything.

The code side of P13 is pinned by [`test_a_ticket_issued_before_a_halt_does_not_execute_during_it`](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/tests/test_h19_authorization.py#L203-L214).

**What this doesn't fix, and you said so.** Implementation-to-proof conformance is still open. The proof now models the two checks that broke, but there's no mechanical link from `governor.py` to the abstract machine. That link is experiment L4 (trace conformance), and its first attempt was itself sent back for re-encoding the guards instead of driving the machine. It's the next thing on the list, and "proven" stays qualified until it lands.

## Two holes you didn't report, and four you told us to stop tolerating

### 5b and 5c: the same disease as your finding 5, one level up

While fixing your finding 5, I asked the obvious next question: if an old *epoch* can be replayed, what about the documents the epoch comes from? Both failed.

- **5b. The gate reloaded an older governance-signed policy.** Sign a policy, sign a newer one, load the newer one, then load the old one again: accepted. The rollback could start at the gate itself, before any endpoint saw anything. Reproduced on `11eb119` with [`repro_rollback.py`](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/audit/external-2026-10-22/repro_rollback.py).
- **5c. An older revocation list un-revoked a device.** Revoke a GPU, then replay last week's empty list: the GPU is back in good standing. That's a revocation system with an undo button for anyone holding an old document.

**The root cause of 5, 5b and 5c is one sentence:** a signature says who wrote a document, never that it's still the current one. So the fix is one mechanism, not three patches:

1. **Every governance document gets a version.** [`GovernanceRoot.sign()`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/attest.py#L60-L66) now stamps each one with a version, one above the last of its kind: policies, revocation lists, reference values.
2. **Every consumer keeps a high-water mark.** [`newer_or_same()`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/attest.py#L35-L48) refuses an older version, and a different document under the same version. It allows reloading the identical document.
3. **It's wired in everywhere a document lands:**
   - [the verifier's revocation list and reference values](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/attest.py#L128-L140);
   - [the gate's `load_policy()`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/gate.py#L115-L140), whose high-water mark is durable;
   - [`Node.restart()`](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/hardware_ref/system.py#L158), which now reloads the newest policy the gate stored rather than the boot one. Otherwise the fix would have made every restart fail.

**Tests** in [test\_audit\_2026\_10\_22.py](https://github.com/YobieBenjamin/hardware-and-silicon/blob/b36ed52fb7b2db6b682ff942b3c2af020642a551/tests/test_audit_2026_10_22.py):

- `test_gate_refuses_an_older_governance_policy`;
- `test_gate_refuses_a_policy_without_a_version`;
- `test_an_old_revocation_list_cannot_unrevoke_a_device`;
- `test_reloading_the_same_document_is_fine_and_restart_keeps_the_newest_policy`.

The chip model on the governor side already had a fused anti-rollback counter for its own policy image. The reference stack didn't. Now both do.

**The 11 tests in that file, run against your snapshot:** 9 fail, which is the point, and 2 pass. The 2 that pass are the "this should still work" checks: the gate key survives a restart, and a hold under the current policy still approves.

### G1, G2, G3, G5: controls that were written down but not enforced

You were right to refuse the excuse that we'd already listed these. A field in the schema that nothing reads is worse than no field, because it lets a reader believe a control exists. All four had tests written first, on the governor model, and every test failed before the fix ([test\_h20\_closed\_gaps.py](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/tests/test_h20_closed_gaps.py)).

| Gap | What was wrong | Fix | Tests |
| --- | --- | --- | --- |
| **G1** Revocations | `revocations` was stored in the rulebook and never read | [A revoked key counts for nothing in any role](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/govsim/governor.py#L286-L288): observer, approver, endpoint, publisher, authority, host. [A revoked GPU fails `VERIFY_GPU`](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/govsim/governor.py#L405-L408) with the new code `attest.revoked` | `test_a_revoked_observer_key_is_not_a_witness`, `test_a_revoked_gpu_cannot_attest`, `test_a_revoked_approver_cannot_release_a_hold` |
| **G2** Sandbox | The roster path honoured `sandbox`, but a peer port asked for directly through `CAP_REQUEST` was judged by roster membership alone | [`CAP_REQUEST` refuses any peer but the verified host in a sandbox](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/govsim/governor.py#L969-L972) (`ep.sandboxed`), the same rule as the roster path | `test_a_sandboxed_governor_grants_no_peer_capability`, and the control `test_without_the_sandbox_the_same_request_is_granted` |
| **G3** Hazard budget | Each governor counted a session's hazards on its own ledger, so a session spread over N chips got N budgets | [Counted at one hazard owner the rulebook names](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/govsim/governor.py#L677-L698), over the fabric, the way a shared payment budget is. [The loader refuses a rulebook with a hazard budget and no owner](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/govsim/policy.py#L182-L188); there is no default owner. If the owner can't be reached, [the response is parked](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/govsim/governor.py#L590-L601) (fail closed) | `test_a_session_spread_over_two_governors_gets_one_hazard_budget`, `test_the_hazard_owner_unreachable_fails_closed` |
| **G5** Token across an edition | A workload token minted under the old rulebook kept working under the new one | [The commit renews the fingerprint](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/govsim/governor.py#L230-L235), so every old token is refused (`gate.not_attested`) until the host presents its manifest again and the new rules decide whether the model may run at all | `test_a_workload_token_from_the_old_edition_is_refused` |

**Where my own test lied to me.** I reverted each of the four fixes in turn and reran the tests. G1, G2 and G3 were each caught. **G5 was not.** My first token test changed the rulebook through a helper that also reloaded the model, and the reload alone retires the old token. So the test passed with or without the fix, and it was testing nothing. I rewrote it to change the edition while the host does nothing, which is the case an attacker actually uses, and now the reverted code fails it. If I hadn't run the revert, I'd have shipped a green test guarding nothing. That's the discipline your memo was really about.

**G4 stays open, on purpose.** The model reads token counts off the GPU's own counter rather than deriving them from the streams presented for signing. That's a simplification in the model, not a hole an attacker can drive through: the counter isn't host-writable. It stays on the list.

## Your research objections: all reproduced, and they make the case for the chip

I recomputed every research number in your memo from the committed scores, using the published C2 code and nothing else: [`check_research.py`](https://github.com/YobieBenjamin/safety-governor/blob/6743c9f8ac951becc1e5fad8c47cf685120ea297/audit/external-2026-10-22/check_research.py), run against [YB-0051's `data/` at `4c1374d`](https://github.com/YobieBenjamin/autonomic-graph-regulation/tree/4c1374d99e58497d7d0e2afacc8743579c5216f7/algorithms/YB-0051-low-false-alarm-precision/data). Every number matched exactly.

| Quantity | Your number | Mine |
| --- | --- | --- |
| C2 at 1%, threshold set on the test set's correct answers (as published) | 339 caught, 59 false alarms, 0.996% | 339, 59, 0.996% |
| False alarms on modular exponentiation | 46 of 352, 13.07% | 46 of 352, 13.07% |
| Self-consistency plus the text monitor, at the same 59 false alarms | 336 caught | 336 |
| C2 with the threshold frozen on the reference before the test | 307 caught, 44 false alarms, 0.743% | 307, 44, 0.743% |
| Modular exponentiation with that frozen threshold | (not in your memo) | 41 of 352, **11.65%** |

The last row is the one I'd add to your case. Even when the threshold is frozen honestly in advance, one task family alarms on one correct answer in nine. Freezing fixes the method; it doesn't fix the detector.

For completeness, the per-family breakdown at the published operating point:

| Task family | False alarms / correct answers | Errors caught / errors |
| --- | --- | --- |
| modpow | 46 / 352 (13.07%) | 98 / 123 |
| weekday | 8 / 986 (0.81%) | 146 / 212 |
| mul\_hard | 5 / 1,047 (0.48%) | 66 / 144 |
| count | 0 / 1,141 | 28 / 58 |
| mul\_easy | 0 / 1,196 | 1 / 4 |
| add\_hard | 0 / 1,200 | 0 / 0 |

**Your three method points are correct as stated:**

- **A. Threshold chosen on test labels.** It's a retrospective ROC point, not a deployed false-alarm rate. The frozen-threshold rows above are the honest version, and they're worse.
- **B. YB-0047's leave-one-task-out isn't fully out.** Layer and regularisation are selected on the full mixture, so the held-out task leaks into model selection. The fix is nested selection inside each outer fold.
- **C. H3's conclusion outruns its interval.** Plus 7.4 points, with an interval from minus 5.8 to plus 16.8, supports "not shown", not "the tie-break is where the resolution comes from". Keeping k = 4 for cost is fine. Claiming more samples don't help isn't.

These live in the autonomic-graph-regulation repository, which my publishing pipeline can't push to yet. The corrections ledger entries are drafted in the review record. They go into that repo's `CORRECTIONS.md` next, under your name if you'll let me use it.

### What your numbers mean for the thing we're actually building

This is the part I want you to argue with, because it's the thesis.

Everything in YB-0050 and YB-0051 is **AI checking AI**. Self-consistency asks the model the same question again. The probe reads its insides. The text monitor reads its words. Your memo shows, with our own data:

- **The best of them is wrong on 13% of correct answers on one task**, while averaging 1% pooled. A deployment that happens to be heavy on that kind of task lives at 13%.
- **The fancy internal-state signal barely beats the cheap one.** Reading activations got 339. Re-asking the model plus a text score, no internals at all, got 336.
- **And none of it measures what we care about.** As you said, the tasks are arithmetic and calendar errors, not unauthorized actions, deception or harmful plans.

If the only line of defence were one of these detectors, that would be a death sentence for the whole safety argument. Which is exactly why, in this design, **none of them is the lock.** They're witnesses. A witness can yell stop: its signed verdict can hold or deny a request. It can never say go by itself, because the go comes from a rulebook signed by people the model can't reach, turned into a single-use ticket by a chip the model can't write to, and checked by the device that does the deed.

Your five implementation findings were attacks on that outside layer, and they were the dangerous ones. A detector that misfires costs us alarms. A gate that accepts an unsigned rulebook costs us everything. That's why I fixed those first, and why I'm not pouring the next month into making detectors smarter.

**What the rulebook takes from your numbers, starting now:**

1. **A witness's threshold is set per action class, never pooled.** The pooled 1% is a lie of averages, and the rulebook shouldn't repeat it.
2. **An irreversible action never rests on one witness.** It requires a human hold or a second, independent witness. The observer lane already supports both; the default rulebook should require it.
3. **No telemetry in silicon until it beats the output-only baseline**, on a preregistered test with separate training, calibration and untouched test data. Your 336 against 339 says that case isn't made. The chip's job is to enforce, not to read minds, and it stays that way until the data says otherwise.

## What's still open, your work order, and how to check me

**Your memo is on the record, word for word.** It sits in the repositories next to this response, so anyone who reads the project reads your objections too:

- [safety-governor `audit/external-2026-10-22/`](https://github.com/YobieBenjamin/safety-governor/tree/main/audit/external-2026-10-22)
- [hardware-and-silicon `audit/external-2026-10-22/`](https://github.com/YobieBenjamin/hardware-and-silicon/tree/main/audit/external-2026-10-22)

A program that only publishes the reviews it survived isn't doing science. Object as hard as you like; all I ask is that the objections come with a reproduction, like yours did, so we can fix the thing and keep moving.

**I adopted your work order as written:**

| # | Your step | Status |
| --- | --- | --- |
| 1 | Fix the five reproduced failures, each with a regression that fails on the audited snapshot | Done: six with finding 6, plus 5b and 5c. Every regression fails on your snapshot or on the reverted code |
| 2 | Close the disclosed control gaps | Three of four closed: G1, G2, G3 and G5 done; G4 open as a modelling simplification |
| 3 | Validate one complete action path end to end | **Open.** One narrow workflow, a payment, with a real observer implementation, run through a policy change, a delayed approval, a replay, a restart, a partition and a revocation. This is the next build |
| 4 | Run the missing scientific comparison | **Open.** Preregistered internal telemetry against self-consistency plus text, with separate training, calibration and untouched test data, measuring prevented bad actions, false holds, completion, review burden and latency |
| 5 | Prove one physical enforcement configuration first | **Open.** One named board, one interface, one protected effect, one measured deadline. That's stage 3 of the roadmap, and the board-lever register (B2 to B4) says exactly what we don't know yet about per-GPU reset, power brake and power enable |

**Also still open, and I'm not going to pretend otherwise:**

- **Proof-to-code conformance.** The proof now models the checks that broke, but nothing mechanically ties `governor.py` to the abstract machine. That's experiment L4, and "proven" stays qualified until it lands.
- **Changing the governance key set itself** under the current quorum. The threshold is fused and ratchets; adding or retiring a key isn't modelled.
- **The fabric's own messages** (roster, alarm, checkpoint, beacon) and the signed objects inside bodies (verdicts, lists, tickets, tokens, receipts) deserve the same replay-into-everything sweep the mailbox got. That's gap G13 in the record.
- **A seeded concurrency harness** that interleaves commands, timers and crashes across governors. It's the honest way to tell a race from a logic bug before anyone blames hardware (G14). Every failure in your memo was logic, not a race: each one reproduces single-threaded on a simulated clock.
- **Nothing here is silicon.** Every result above is on functional models and simulated endpoints, which is exactly what you said you tested too.

**How to check me.** Clone at the fix commits once they're published, then:

```
git clone https://github.com/YobieBenjamin/safety-governor && cd safety-governor
python3 -m pytest -q tests rtl/tests                               # 248 tests
make proof                                                         # P0 to P13, the regression checks, K0 to K5
PYTHONPATH=. python3 audit/external-2026-10-22/repro_sg.py         # your findings 1 and 2: NOT reproduced

git clone https://github.com/YobieBenjamin/hardware-and-silicon && cd hardware-and-silicon
python3 -m pytest -q tests                                         # 67 tests, 11 of them yours
PYTHONPATH=. python3 ../safety-governor/audit/external-2026-10-22/repro_hs.py   # 3, 4, 5: NOT reproduced
```

Check out `dccc1e0` and `11eb119` and run the same two scripts, and they print REPRODUCED. If you find a way around any of these fixes, send me the reproduction and it goes into the next one of these memos with your name on it.

We might fail at this. The chip might turn out to need vendor cooperation we never get, or the false-halt rate might be one no operator will live with. But every finding like yours turns a hand-wave into a test, and that's how you find out, instead of arguing about it on podcasts. Keep them coming.

Yobie Benjamin · yobie AT ieee DOT org · linkedin.com/in/yobie
