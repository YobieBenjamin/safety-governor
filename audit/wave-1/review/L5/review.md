## Review of `exp/l5`: **revise**

Verifier: 1 blocking finding(s); model review on ?: 2 blocking, 7 warnings, 3 unsupported claim(s) of 10; estimated $0.27, 6 turns.

### Reviewer's summary

The test passes, but it compares 21 hand-built scenarios, not the 87 catalogue entries; the other 66 are only listed.
Passing depends on five pinned disagreements, and the G1 and G5 excuse predicates are broad enough to hide real ones.
The design-ambiguity claim (G3, G4, G5) is made in EXPERIMENTS.md without reading docs/LANES.md or govsim's docs.
For G3 the evidence cited points to a govsim bug, not an ambiguity.
The acceptance asks for one filed issue per disagreement; none were filed.
tests/requirements-differential.txt is outside the owned paths (verify.json flags it). It is reasonable for the brief's install step, so I rate it warn.
Not checked: the claims about gate.py and governor internals (G2 'no log line', G4 'marked seen before deciding'). My shell access to the other repositories was denied.
Question: does the brief intend 'cover the catalogue' to mean the actual attack inputs, or analogous scenarios?

### Verifier findings

- [block] a file outside the issue's owned paths changed: `tests/requirements-differential.txt`

### Reviewer findings

- [warn] test_integrity at `tests/test_h21_differential.py:352`: 'Replayed in both gates' is not the catalogue's input: REPLAYED holds hand-written Scn analogues keyed by attack name; the catalogue supplies only the name and the expect flag. L4.token_wrong_workload is replayed as a forged token (line 358), which is a different attack. L4.no_capability and L4.weights_exfiltration use new params. Only test_the_reference_catalogue_holds_on_its_own runs the real entries, and only on the reference.
- [block] test_integrity at `tests/test_h21_differential.py:329`: The brief says feed the catalogue to both gates and pass on the whole catalogue. 66 of 87 entries are in NOT_COMPARED and never reach govsim; some reasons are thin ('L0', 'restart', 'approval protocol'). Several are plausibly gate decisions: the L4 approval cases and L2 provenance. The acceptance therefore tests less than the brief states. The shortfall is disclosed in results/l5-disagreements.md, but the brief's coverage was not met.
- [warn] test_integrity at `tests/test_h21_differential.py:298`: The G5 excuse accepts any deny/deny pair whose reasons both start with 'constraint.'; it does not require the two-rule case it describes. The max/min vs above_max/below_min merge (line 108) makes a swapped bound unobservable. The G1 excuse (line 307) only checks that the corrected request agrees, not that govsim allowed. The sweep can therefore pass over disagreements outside the five documented gaps.
- [warn] test_integrity at `tests/test_h21_differential.py:460`: The property sweep runs 120 examples with derandomize=True, so it is one fixed sample. Only the first reason is compared. No artifact shows how many examples agreed, how many were excused, or that each of G1 to G5 was hit by the sweep. EXPERIMENTS.md says the gates agree 'on the random sweep'; that number is not shown.
- [block] unsupported_claim at `EXPERIMENTS.md:33`: 'G3, G4 and G5 are ambiguities in the policy text, a finding about the design' is asserted in a document. The summary admits govsim's docs were not read, and docs/LANES.md (named in the brief's Read first) was not read. For G3 the cited reference text ('observer threshold ... checked first') and govsim accepting observers/max_risk on a human rule point to a govsim bug, not an ambiguity. The design finding is not shown.
- [warn] unsupported_claim at `results/l5-disagreements.md:17`: Specifics not backed by any test or artifact in the diff: 'no decision, no log line' (G2), and the causes in G4 (hash marked seen before the decision; ledger.mark only on decided requests). The pinned tests show only the outcome pairs.
- [warn] correctness at `tests/test_h21_differential.py:358`: Mapping L4.token_wrong_workload to token='forged' in both rigs can never exercise the reference gate's measurement_mismatch reason, and the mapping table collapses attestation.* reasons into 'not_attested' (line 24 of the file). An implementation that returns the wrong attestation reason would still agree.
- [warn] protocol at `results/l5-disagreements.md:34`: The acceptance requires every disagreement found to be filed as its own issue with its input. None were filed (deferred to the launcher). The inputs are written up, but the acceptance is not met.
- [warn] scope at `tests/requirements-differential.txt:1`: New file outside the owned paths (flagged in verify.json). It serves the brief's install step with a relative editable path, so it is arguably needed; the owner should confirm it. EXPERIMENTS.md gets a new section rather than an update of the H21 row, and the row's status is unchanged.

### Claims

- supported (document): The two gates agree on 18 of 21 replayed catalogue entries (evidence: EXPERIMENTS.md line 33; EXPECT_GAP has 3 entries asserted hw != gov and the rest asserted hw == gov, in test_catalogue_replayed_in_both_gates (test line 417). Supported as to the hand-built scenarios, not the real catalogue inputs.)
- NOT SUPPORTED (document): The gates agree on the random sweep except for five pinned disagreements G1 to G5 (evidence: test_random_typed_requests_agree passes with gap_of excusing any signature match. No artifact shows the sweep hit each gap or how many examples agreed. The G1 and G5 signatures are broad.)
- NOT SUPPORTED (document): G3, G4 and G5 are ambiguities in the policy text (a finding about the design) (evidence: No policy text of govsim or LANES.md was read; the document's own G3 quote favours the reference.)
- supported (summary): All 87 catalogue entries are classified: 21 replayed, 66 listed with a reason (evidence: test_every_catalogue_entry_is_classified (test line 379) pins 75 and 12 and checks REPLAYED and NOT_COMPARED partition the names. The brief's 66 and 10 differ from the checkout, and the test pins the checkout's counts.)
- NOT SUPPORTED (summary): The test covers the catalogue (brief) and covers the whole catalogue (evidence: Only 21 of 87 are compared across the two gates.)
- NOT SUPPORTED (document): G2: non-numeric amount raises TypeError in govsim with no decision and no log line (evidence: GAP_CASES pins crash:TypeError; 'no log line' is not tested.)
- supported (document): G1: govsim has no destination regex so acct-evil is allowed (evidence: GAP_CASES G1 pins deny constraint.destination.pattern vs allow; test_pinned_disagreement.)
- supported (document): G4: the reference marks a request seen before deciding; govsim repeats the original denial (evidence: GAP_CASES G4 pins deny:replay vs deny:witness_missing; the causal mechanism is not in the diff and I could not read the sources.)
- supported (document): All 30 test functions pass (called directly) and the acceptance command passes (evidence: verify.json: acceptance exit 0, suite 230 passed. The count of 30 matches 3+21+5+1.)
- supported (code): One neutral rulebook is rendered into both formats; a test checks they say the same thing (evidence: test_the_two_rulebooks_say_the_same_thing checks the reference side fully and the govsim side for mode, risk, amount, currency, rate and budget. Destination and type are omitted from govsim, by design.)

### suite in a clean checkout: exit 0

```
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
..............                                                           [100%]
230 passed in 6.01s

```

### acceptance in a clean checkout: exit 0

```
..............................                                           [100%]

```
