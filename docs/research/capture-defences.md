# Capture by signed editions: the floor, the delay, the step and the recovery quorum

Adversarial audit 3, catalog rows 7 (CATASTROPHIC), 14 and 18 (SERIOUS). GOAL.md requirement 7: no single government,
vendor, operator or insider can use the chip to do harm; and a persistent AI may capture or deceive the signers.

## The problems

- Row 14: the chip accepted any edition the governance quorum signed, including one that dropped the protected-site
  constraint and made strikes automatic. Whoever holds or deceives the quorum needs nothing more.
- Row 7: a stolen quorum signed one edition that rotated governance to the thief's keys at version 10^9. The legitimate
  quorum could never sign for that chip again.
- Row 18: the policy anti-rollback fuses are 256 one-time bits, but the model counted versions without limit.

## The design

1. **A fused rule floor.** Rules no edition may remove or weaken, fused at manufacture (`Fuses.rule_floor`). The model
   rack fuses: every strike rule keeps the typed protected-site check and may not run in automatic mode. An edition
   below the floor is refused at staging and at commit (POLICY_BELOW_FLOOR). No number of signatures changes fuses.
2. **A public delay before loosening.** An edition that loosens the rules in force (new rules, weaker modes, fewer
   approvers, wider limits, larger budgets or rates, different governance keys, withdrawn revocations; see
   `policy.loosenings`) acts only from its own `effective_at`, which must be at least the fused delay after its
   `issued_at`. It is public before it can act, and the recovery quorum can answer it. Tightening needs no delay. The
   model racks fuse a delay of 0 so the existing tests run; production fuses set it (a week is the working figure).
3. **A version step bound.** An edition may advance the version by at most 16, so one edition cannot burn the
   anti-rollback range.
4. **A fused recovery quorum.** A separate set of keys (5 in the model, 4 needed), fused at manufacture and held apart
   from governance, can always sign an edition over whatever governance is in force. A stolen governance quorum that
   rotates a chip to its own keys loses it to the recovery edition, and the endpoints accept that edition too.
5. **Fuses that fit.** The exact version lives in an NVM monotonic counter; the fuses burn one bit per 64 versions, so
   a rollback below the fused floor is impossible even if the NVM counter is attacked, and with the step bound 256 bits
   cover more than 16,000 editions.

## What the code does now

`govsim/fuses.py`, `govsim/policy.py` (`floor_violations`, `loosenings`, `verify_recovery`), `govsim/governor.py`
(`_check_edition`, used by both POLICY_PROPOSE and POLICY_COMMIT), `govsim/endpoints.py` (recovery at endpoints),
`govsim/cluster.py` (`STRIKE_RULE_FLOOR`, `recovery_policy`). Tests in `tests/test_adversarial_audit_3.py`.

## What is still open

- The floor protects what is fused. Choosing the floor (which actions, which checks) is a decision for the standards
  body and regulators, and it must be right at manufacture.
- The public log: the delay makes a loosening visible only if the edition is published. A transparency log with
  inclusion proofs checked on chip is the silicon plan; the model checks the delay only.
- `loosenings` covers rules, budgets, rates, governance keys and revocations, not reference values, endpoints, buffer
  policy or timers; those changes are not delayed by the chip.
- A recovery quorum is itself a capture target. It must be held by different institutions than governance, offline.
