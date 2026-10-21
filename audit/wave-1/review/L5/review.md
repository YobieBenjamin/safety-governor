## Review of `exp/l5`: **revise**

Verifier: clean; model review on ?: 2 blocking, 7 warnings, 6 unsupported claim(s) of 15; estimated $0.33, 8 turns.

### Reviewer's summary

The acceptance command passes (verify.json), but it tests less than the brief says. Only 20 of 87 catalogue entries are compared; 67 sit in NOT_COMPARED, several with a bare label such as "L0" and no reason.
The brief's acceptance also requires each disagreement to be filed as its own issue. G1 to G5 are only written up in results/l5-disagreements.md, and the agent says so.
The reason-code table collapses classes (attestation.*, observer.*, min and max) and only the first reason is compared. The sweep accepts any outcome pair that matches a GAPS signature.
The "pinned checkout" comment at test line 497 is unsupported: requirements-differential.txt uses an unpinned editable sibling path.
Question for the design owner: for G3, govsim/governor.py:513 reads witnesses only in observer mode. The comment at governor.py:509 ("a human lane parks it unread") suggests that is deliberate. The agent's "ambiguous" label is softened correctly but still rests on docstrings only.
Not found: evidence that the 31-test count is computed by any test, or that test_h13_shared_budget.py covers TX.concurrent_overspend (line 463 asserts it).

### Reviewer findings

- [block] test_integrity at `tests/test_h21_differential.py:469`: The brief asks for the test to pass on the whole catalogue (75 attacks, 12 baselines). REPLAYED covers 20 entries and 67 are excluded through NOT_COMPARED (line 442). Several excluded entries are not shown by any test, for example L0.*, EP.*, AU.*, NV.*, L2.provenance_*, L5.*. Their reasons are one-word labels such as "L0". Some of them (L4.token_missing style token checks, TX.budget_exhausted) are gate decisions that were replayed, but entries such as TX.ticket_after_policy_change and TX.commit_* are excluded on the agent's say-so only. The acceptance passes by testing about a quarter of the catalogue.
- [block] protocol at `results/l5-disagreements.md:54`: The brief's acceptance says every disagreement found is filed as its own issue with the input that produced it. G1 to G5 are written up in one file and not filed (lines 54 to 55). The agent says it is open, but the acceptance is not met.
- [warn] test_integrity at `tests/test_h21_differential.py:159`: The reason-code table maps several distinct codes to one class (attestation.* to not_attested; observer.signature, subject_mismatch and not_registered to witness_missing; HW_KINDS max/min to range at line 177). Only res.reasons[0] is compared (line 238). The brief asks for equivalent reason codes; this checks a coarser equivalence. A mismatch in the observer subject-swap case would not be seen.
- [warn] test_integrity at `tests/test_h21_differential.py:580`: The sweep passes whenever gap_of() matches a signature. G3's signature (line 379) accepts any hw witness-class deny against govsim hold or allow in the large amount range. G1 and G5 (lines 390 and 412) accept a disagreement if a corrected input agrees, which can hide a second cause. The sweep cannot fail on these classes; it is run with only 120 derandomized examples.
- [warn] unsupported_claim at `tests/test_h21_differential.py:497`: The comment says the catalogue at the pinned checkout has 75 and 12. Nothing is pinned: tests/requirements-differential.txt line 2 is an editable ../hardware-and-silicon path, not a commit or git URL.
- [warn] unsupported_claim at `tests/test_h21_differential.py:463`: The reason says govsim's own H13 covers the concurrent form of TX.concurrent_overspend. The summary admits this was not checked. The brief names only govsim/policy.py, governor.py and reasons.py, so the exclusion has no evidence. tests/test_h13_shared_budget.py:19 has a concurrent-request test, but the diff does not connect it to the attack.
- [warn] unsupported_claim at `results/l5-disagreements.md:42`: G3 is labelled a hypothesis, which is right, but the design question is left open. reference policy.py:22 says a human rule may still set an observer threshold checked first. govsim/governor.py:513 reads witnesses only for observer mode, and governor.py:509 says a human lane parks the request unread. That points to an intentional difference. The Disproof clause (ambiguous policy is a design finding) is reached from docstrings only, with no check of docs/LANES.md, which the brief names.
- [warn] unsupported_claim at `EXPERIMENTS.md:14`: The document says 31 tests and 'the random sweep agrees except for five pinned disagreements'. No test asserts the test count or that the sweep actually hits each of G1 to G5. The 17 of 20 count is computed by test_replayed_agreement_count (test line 660); 67 and 31 are only prose.
- [warn] scope at `tests/requirements-differential.txt:1`: The brief owns only the test file. The requirements file and results/l5-disagreements.md were added, and EXPERIMENTS.md was edited with a success write-up although the brief only asks for failure notes there. This is reasonable support but unrequested; the summary states it.

### Claims

- supported (document): The two gates agree on 17 of 20 replayed catalogue entries (evidence: tests/test_h21_differential.py:660 asserts (len(REPLAYED), agree, len(gaps)) == (20, 17, 3))
- supported (document): The other 67 of 87 catalogue entries are listed in NOT_COMPARED with reasons (evidence: 87 = 75 + 12 is asserted at line 498; 67 is not computed but follows from the classification test at line 495. Several reasons are one-word labels.)
- NOT SUPPORTED (document): The gates agree on the random sweep except for five pinned disagreements (evidence: test_random_typed_requests_agree accepts any signature-matching gap; no test shows all five occur in the sweep; the sweep is 120 derandomized examples)
- supported (document): The file now has 31 tests and the acceptance command passes (evidence: verify.json acceptance exit 0; test count is 20+5+6 functions by reading, not asserted by a test)
- supported (document): G1: govsim allows a bad destination where the reference denies constraint.destination.pattern (evidence: GAP_CASES line 541 pins it; govsim/policy.py has no regex kind)
- supported (document): G2: govsim raises TypeError on a non-numeric amount (evidence: GAP_CASES line 542 pins crash:TypeError; govsim/policy.py:212 compares v < c['min'])
- NOT SUPPORTED (document): G3: govsim ignores the observer on a human-mode rule, and the policy text does not settle which is right (evidence: Pinned at line 543 and governor.py:513 reads witnesses only for observer mode; the 'ambiguous' part rests on docstrings only, with governor.py:509 suggesting intent)
- supported (document): G4: the reference marks a request seen before deciding, govsim only after deciding (evidence: Pinned at line 544; governor.py:529 marks after the checks and policy-level seen check at line 489 (reference side not re-read))
- supported (document): G5: the reference reports the first candidate's violation and govsim the last (evidence: govsim/policy.py:197-203 returns the last violation; pinned at line 545; reference side not re-read)
- NOT SUPPORTED (code): The 67 excluded entries are not gate decisions in govsim (evidence: Per-entry reasons at lines 443-466; shown by test only for http, token_wrong_workload and the approval attacks; the rest are asserted by label)
- NOT SUPPORTED (code): TX.concurrent_overspend is covered by govsim's H13 (evidence: Line 463; summary admits it was not checked; tests/test_h13_shared_budget.py:19 has a concurrent test but the diff does not link it)
- NOT SUPPORTED (code): The catalogue at the pinned checkout has 75 and 12 (evidence: Asserted at line 498, but no pin exists in requirements-differential.txt)
- NOT SUPPORTED (document): The disagreements are filed as issues (evidence: Not filed; the document and the summary both say so)
- supported (code): The reference stack behaves as the catalogue says before it is used as an oracle (evidence: test_the_reference_catalogue_holds_on_its_own runs all 87 entries against the reference node)
- supported (code): The two rulebooks say the same thing (except for regex and type, which govsim cannot express) (evidence: test_the_two_rulebooks_say_the_same_thing, lines 512-523)

### suite in a clean checkout: exit 0

```
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
...............                                                          [100%]
231 passed in 6.83s

```

### acceptance in a clean checkout: exit 0

```
...............................                                          [100%]

```
