# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""EXPERIMENT-CUSTOMER-CONFIRMATION: the wire the customer never meant. A payment rule whose witness must be the payer's own key.

    python -m govsim.customer_confirm            # the checks
    python -m govsim.customer_confirm --write     # also results/customer-confirm.md

Prompted by a reader's comment on Part 6: a gate on the device end stops a wire that breaks the rules, but it will
also ticket a wire for an approved amount to an approved payee that the customer never meant to send. The gate checks
the form, not the intent behind it. This tests the one thing the chip can add without judging intent: require the
payer's own signature, bound to this exact request, so the agent cannot speak for the customer.

Writing the reply showed the design could not express this yet: a rule in observer mode accepts a verdict from ANY
observer key, so the lab's classifier could stand in for the customer. The fix is a request-bound witness: the only
key that counts is the one a signed customer registry lists for the paying account. This run exercises that fix
against intended and unintended wires and the stand-ins that must all fail.
"""
from __future__ import annotations

import argparse
import os
import sys

from . import reasons
from .cluster import build_rack


def _rack():
    r = build_rack(1, "rack")
    r.policy_kw = {**getattr(r, "policy_kw", {}), "payer_confirm_payments": True}
    r.bring_up()
    node = r.nodes[0]
    # the policy signed at construction had the flag off; commit the edition that carries the payer-confirm rule
    assert r.change_epoch(r.new_policy())["committed"], "the payer-confirm rulebook did not commit"
    r.load_model(node)                                   # the epoch change retires the workload token; mint a fresh one
    # install the signed customer registry the rule names (bring_up installs the other lists)
    assert node.governor.install_list("customer-registry", r.customer_registry_list()), "customer registry refused"
    return r, node


def checks():
    out = []

    def check(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    r, node = _rack()

    # 1. intended wire: the paying customer's own key confirms this request -> ticket
    res = r.pay(node, 100, "alice-123", confirm_as="alice-123")
    check("intended wire: the customer's own key confirms -> ticket issued", res["ok"], res["why"])

    # 2. unintended wire: amount, payee and rule all allowed, no confirmation at all -> refused
    res = r.pay(node, 100, "alice-123", confirm_as=None)
    check("unintended wire: allowed in every other way, but no confirmation -> refused",
          not res["ok"] and res["why"] == reasons.GATE_PAYER_UNCONFIRMED, res["why"])

    # 3. stand-ins that must all fail
    res = r.pay(node, 100, "alice-123", confirm_as="__observer__")   # the lab's classifier / some other key
    check("a non-customer key (the classifier's) cannot stand in for the payer",
          not res["ok"] and res["why"].startswith(reasons.GATE_PAYER_UNCONFIRMED), res["why"])

    res = r.pay(node, 100, "alice-123", confirm_as="bob-456")        # another customer's key
    check("another customer's key does not confirm Alice's wire",
          not res["ok"] and res["why"].startswith(reasons.GATE_PAYER_UNCONFIRMED), res["why"])

    res = r.pay(node, 100, "alice-123", confirm_as="alice-123", confirm_ttl_s=-1)   # already expired
    check("a stale confirmation is refused",
          not res["ok"] and res["why"] == reasons.GATE_PAYER_UNCONFIRMED, res["why"])

    res = r.pay(node, 100, "alice-123", confirm_as="alice-123", confirm_request_id="some-other-request")
    check("a confirmation signed for a different request does not move this one",
          not res["ok"] and res["why"] == reasons.GATE_PAYER_UNCONFIRMED, res["why"])

    res = r.pay(node, 100, "carol-789", confirm_as="alice-123")      # payer not in the registry
    check("a paying account not in the signed registry is refused",
          not res["ok"] and res["why"].endswith("account_not_registered"), res["why"])

    # 4. the intended path still works after all the refusals (the gate did not wedge)
    res = r.pay(node, 250, "bob-456", confirm_as="bob-456")
    check("the intended path still works for another customer after the refusals", res["ok"], res["why"])

    # 5. control: with the rule OFF (the reference rulebook), a payment needs no customer confirmation, so nothing
    #    here changes the default behaviour
    r2 = build_rack(1, "rack"); r2.bring_up(); n2 = r2.nodes[0]
    res = r2.request(n2, "payments.transfer", {"amount": 100, "currency": "USD", "destination": "recipient-a"})
    check("control: the reference rulebook (no payer-confirm) still tickets a small wire with no customer key", res["ok"], res["why"])

    return out


def report(results) -> str:
    ok = all(r[1] for r in results)
    L = ["# I1 · The wire the customer never meant", "",
         "Generated by `python -m govsim.customer_confirm --write`. Question 22 in `docs/18`, issue I1.", "",
         f"**Result: {'every check holds' if ok else 'A CHECK FAILED'}** ({sum(r[1] for r in results)} of {len(results)}).", "",
         "The gate checks the form, not the intent. The one thing the chip can add without judging intent is to make a "
         "wire need the payer's own signature, bound to this exact request, so the agent cannot speak for the customer. "
         "The only key that counts is the one a signed customer registry lists for the paying account.", "",
         "| Check | Holds | Detail |", "|---|---|---|"]
    L += [f"| {n} | {'yes' if k else '**NO**'} | {d} |" for n, k, d in results]
    L += ["", "## What this shows, and what it cannot", "",
          "- An unintended wire (right amount, right payee, right rule, no confirmation) is refused, and so is every "
          "stand-in: the classifier's key, another customer's key, a stale confirmation, a confirmation for a different "
          "request, a payer not in the registry. Only the payer's own key, over this request, issues the ticket.",
          "- This is opt-in: the reference rulebook is unchanged, so a deployment turns it on for the accounts and "
          "rules that warrant it.",
          "- What it cannot cover, as the thread conceded: a customer who confirms a mistake, or who is talked into "
          "confirming. That stays a person, the door `docs/23` concedes. The chip ensures the person was asked and "
          "that the agent could not answer for them; it cannot ensure the person was right."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    results = checks()
    for n, k, d in results:
        print(f"  {'PASS' if k else 'FAIL'}  {n}" + (f"  ({d})" if d and not k else ""))
    if a.write:
        os.makedirs("results", exist_ok=True)
        open("results/customer-confirm.md", "w").write(report(results))
        print("wrote results/customer-confirm.md")
    bad = [n for n, k, _ in results if not k]
    print("I1: every check holds" if not bad else f"I1: {len(bad)} check(s) FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
