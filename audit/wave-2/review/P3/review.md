## Review of `exp/p3`: **revise**

Verifier: clean; model review on ?: 1 blocking, 8 warnings, 3 unsupported claim(s) of 15; estimated $0.26, 10 turns.

### Reviewer's summary

Acceptance command passes and the figure (208,078 B/h, pin 208,100) is computed from the policy image; the component numbers are pinned by test.
The brief asked for the tightest serviceable policy and a peer-choice channel. The model uses the default image, has no peer term and has no tightness search; the doc says so honestly.
The doc's burst claim ("bounded by the slack, not a rate") is not shown. The only test emits 2 MB, twice the slack, before any tick and never measures how many bytes got out.
The H5 alarm-clearing claim is not shown, and the doc leaves out the payments hourly amount budget.
Disproof test and docstring overclaim next to the doc's "not shown to be unmet".
Question: does the pcie switch cap bytes between ticks? I did not find a cap in the diff.

### Reviewer findings

- [block] unsupported_claim at `docs/05-threat-model.md:68`: The doc says the unpresented burst is 'bounded by the slack, not a rate'. The alarm in govsim/governor.py:817-827 runs only from tick (governor.py:1080), so bytes emitted between ticks are not bounded by the 1 MiB slack. The supporting test (tests/test_covert_budget.py:136-138) emits 2 MB (200x10 KB, twice the slack) before the first tick and never measures how many bytes crossed. The bound on the burst is not shown. The doc also leaves out that CLEAR (governor.py:1084-1099) resets output_blocked, so the burst can repeat after each clearance.
- [warn] unsupported_claim at `docs/05-threat-model.md:68`: 'unless a rule or an approver key clears the alarm (H5)': the test checks only that the alarm persists. Nothing in the diff shows what clears OUTPUT_UNPRESENTED or ties it to H5. governor.py:_cmd_clear requires the 'authority' signer, not an 'approver key'. Not found.
- [warn] test_integrity at `tests/test_covert_budget.py:149`: test_weights_do_not_leave_in_practical_time is named and docstringed as the disproof ('cannot be exfiltrated ... under a policy that still serves'), but it only divides sizes by the modelled-channel figure. The doc says the disproof is 'not shown to be unmet' because of the open channels. The test and docstring overclaim relative to the doc, and the test passes with the unmodelled channels open.
- [warn] correctness at `tests/test_covert_budget.py:72`: _tightest() returns the default image (make_policy_image(1)) and is used in every pinned test, but the brief's model is the 'tightest serviceable policy'. The name implies tightness that no code shows. The doc admits the model does not search for a tighter image, so the brief's core ask (tightest serviceable) is unmet.
- [warn] correctness at `tests/test_covert_budget.py:123`: 'Serviceable' is grounded only by sign_output(node,'s',b'x'*10_000) returning ok. That does not show the rack serves a normal workload under the 50-query/200 KB budget. Weak evidence for the doc's statement that the default image 'serves a normal response'.
- [warn] unsupported_claim at `docs/05-threat-model.md:70`: The doc lists a payment's amount as 'unquantized' and unbounded but does not mention the pay-usd-hourly budget (pay_small_limit=2000 per hour, govsim/cluster.py:135) on the same rule. test_unmodelled_channels_are_still_open (test line 209) pins only the constraint keys, not that budget, so the open-channel description is incomplete and the test would not notice a change to it.
- [warn] scope at `tests/test_covert_budget.py:54`: The brief asks for a model that covers choice among allowed peers and asks to extend tests/test_h10_leakage.py. The peer channel is dropped on the argument that payments go to the payment-switch endpoint (cluster.py:136, supported). Other peer-addressed traffic (model.export, weights.write destinations, recipient choice) is not modelled or bounded. The model lives in a new file, and test_h10_leakage.py got only a 3-value pin (line ~109).
- [warn] unsupported_claim at `docs/05-threat-model.md:64`: 'a finer resolution only raises the timing term, not the 200,000 B/h that dominates' is not tested at any other resolution. The 1 ms resolution is an assumption and the timing terms (63,743 + 875 bits) depend on it.
- [warn] test_integrity at `tests/test_covert_budget.py:65`: The brief's acceptance is 'fails if a policy change raises it'. Only three knobs (output bytes, output window/queries, payments rate) are read. A change that raises real leakage, such as loosening the message rule, the hourly payments budget or the pcie switch, leaves the figure and the test unchanged.

### Claims

- supported (document): The modelled-channel figure is at most 208,078 B/h, pinned at 208,100 (evidence: tests/test_covert_budget.py model() and test_component_figures_match_the_threat_model assert total == 208_078 and the pin)
- supported (document): Timing adds about 8 KB/h (63,743 bits payments, 875 bits output) and response length is 654 bits inside the byte budget (evidence: test_component_figures_match_the_threat_model asserts the rounded values and 7.9-8.1 KB)
- supported (document): The 70B model takes about 673,000 h (77 years) and 1 TB about 4.8M h, through the modelled channels only (evidence: test_weight_times_match_the_threat_model)
- supported (document): A 100 MB delta leaves in about 20 days and a 1 GB student in about 200 days (evidence: test_small_payloads_are_the_caveat)
- NOT SUPPORTED (document): The unpresented burst is bounded by the 1 MiB slack, not a rate, and the block holds across ticks and a full window (evidence: The slack value and the persistence of the alarm and block are tested (lines 127-145). The bound on bytes leaked before the alarm is not measured, and the alarm is checked only at tick)
- NOT SUPPORTED (document): A rule or an approver key clears the alarm (H5) (evidence: Nothing in the diff shows it; _cmd_clear needs the authority signer)
- supported (document): Payments go to the payment-switch endpoint, not a rack peer (evidence: govsim/cluster.py:136 endpoint="payment-switch")
- supported (document): message.send.listed has no length limit or rate, and the payment destination has no limit; the test fails when the image gains one (evidence: test_unmodelled_channels_are_still_open checks rate/budget/output_budget absence and the constraint keys. It does not cover the pay-usd-hourly budget)
- supported (document): The test fails if a policy change raises the figure (evidence: Holds for the output bytes, window/queries and payments rate knobs (tests at lines 77-86 and 182-197), not for other loosenings)
- supported (document): The default image serves a normal response (evidence: test_default_image_serves_a_response signs 10 KB once)
- NOT SUPPORTED (document): A finer timing resolution only raises the timing term (evidence: Not tested, though it follows from the formula)
- supported (document): The disproof condition is not shown to be unmet (evidence: The open channels are pinned by test_unmodelled_channels_are_still_open)
- supported (summary): Revision 2 removed all em dashes (evidence: Not found in the added lines of the diff)
- supported (summary): The new test in tests/test_h10_leakage.py pins the 50 queries, 200,000 bytes and 3,600 s budget the covert model reads (evidence: The added test asserts the values from the governor's output rule. The pin is the value of the image, not a link to the model's read)
- supported (summary): The agent did not search for a tighter serviceable image (evidence: _tightest() is the default image (test line 72))

### suite in a clean checkout: exit 0

```
........................................................................ [ 34%]
........................................................................ [ 68%]
...................................................................      [100%]
211 passed in 2.80s

```

### acceptance in a clean checkout: exit 0

```
..........                                                               [100%]

```
