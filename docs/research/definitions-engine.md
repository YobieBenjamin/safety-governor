# The definitions engine: one meaning for every value a rule reads

Adversarial audit 3 (26 October 2026), catalog row 1 (CATASTROPHIC) and row 40 (CLAIM). GOAL.md requirement 2,
"Know what the words mean".

## The problem

The protected-site list held places as `[lat, lon]`. The rule engine compared the request's target with the list by
container shape. A target written with an altitude (`[34.052, -118.244, 0.0]`), as text (`"34.052,-118.244"`) or as a
mapping (`{"lat": 34.052, "lon": -118.244}`) was not "in" the list, so the chip minted a strike ticket on a protected
site and the strike endpoint, which used the same comparison, executed it. A persistent AI does not need to break the
cryptography if it can write the same forbidden thing another way.

## The design

The rule engine never compares raw request values with a list. `govsim/definitions.py` first reduces a value to its
canonical meaning under a named definition:

- `geo`: a place on Earth, reduced to (latitude, longitude) in degrees. Altitude is dropped (a protected site is
  protected at every altitude). Accepted spellings: a list or tuple of 2 or 3 finite numbers, text `"lat,lon[,alt]"`
  with commas, semicolons or spaces, and a mapping with `lat`/`latitude` and `lon`/`lng`/`long`/`longitude` keys (an
  altitude key is allowed; any other key makes the mapping not understood). Longitude is wrapped into [-180, 180).
  Out-of-range or non-finite values are not places. Places match within a great-circle distance (default 1e-3 degree,
  about 111 m).
- `text`: names, accounts, identifiers, reduced by Unicode NFKC, removal of invisible characters, case folding and
  collapsing of white space, so look-alike spellings are the same word.

The rule that keeps it fail-safe: **a value that cannot be reduced to a defined meaning is refused, never guessed at.**
A rule may name a field's definition (`"type": "geo"`), and then a value that does not parse is refused before any list
check. A denylist check uses the definition the list's entries imply, and a value that cannot be read as that kind of
thing counts as a hit. Allow-lists (`in`, `in_list`) compare with types respected, so `True` is not `1` and `"1"` is not
`1`.

## What the code does now

`govsim/definitions.py`; `govsim/policy.py` `denylist_hit` and `check_constraints`; the strike endpoint's own
`not_protected` check (`govsim/endpoints.py`) uses the same definitions and refuses a missing or unreadable target. The
model rack's strike rule declares `"type": "geo"`, and the fused rule floor (`docs/research/capture-defences.md`) keeps
that declaration in every future edition. Tests: `tests/test_adversarial_audit_3.py` (nine spellings of a protected site,
nine unreadable targets, the endpoint's own check, type-respecting allow lists).

## In silicon

A typed field decoder in the gate core and in the endpoint comparator: the request's fields are decoded to the declared
type in hardware before the list match, and the match runs on decoded fields only. The definitions are part of the
signed edition, so every governor and endpoint decodes the same way.

## What is still open

- Only two definitions exist (`geo`, `text`). Amounts with units and currencies, account numbers in their national
  formats, and identifiers with check digits each need their own definition before a rule may depend on them.
- A request split into several harmless parts (reaching a protected site in steps) is a rule-design problem, handled by
  budgets and rates, not by definitions.
