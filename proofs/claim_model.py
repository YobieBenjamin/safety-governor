#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Experiment A of docs/29: the claim of GOAL.md as theorems, on one model of server, rack and data center.

    python3 proofs/claim_model.py            # every proof, every control, every non-vacuity check
    python3 proofs/claim_model.py --json OUT # the same, and a machine-readable record of each result

`proofs/core_invariants.py` proves the logic of ONE governor. This file proves the claim for MANY: any number of
sites (data centers), governors (one per GPU, in racks), endpoints (the devices that carry out effects), tickets,
actions and budget keys. Each is an uninterpreted sort, so the proofs hold for every size, not for a size that was
tried. Think of the difference between checking that one lock works and proving that a building with any number of
doors, keys and guards cannot be entered without a key.

The attacker controls everything except the trusted base (docs/29 section 2.1). It chooses every step, in any
order, with any inputs, at any time: it writes the requests, picks the actions, delays or drops any message
(editions, heartbeats), halts any governor (tamper, a cut cable), lets time pass, and holds fewer than the
threshold of keys in each site's governance group. It cannot: forge a signature or a ticket (cryptography is
modelled as unforgeable); change the governor silicon, its fused floor, the endpoint's ticket check, or the timing of
the hardware halt path (the heartbeat timer, the halt loop, the GPU levers, measured in hw/loop/results.md).

The state. Rigid facts (they never change during a run):
  site_c(c), site_e(e)       the data center each governor chip and each endpoint belongs to
  allows(s, ed, a)           whether edition ed of site s's rulebook allows action a (the content of the signed rulebook)
  expiry(s, ed)              when edition ed of site s expires on the endpoints' clocks
  cap(s, b)                  the data-center-wide cap of budget key b at site s (a fleet budget: counted once per site)
  n_hon(s), att_keys(s)      how many governance keys at site s the honest holders and the attacker hold
  kfloor(s)                  the threshold fused at manufacture; the attacker holds fewer keys than it (trusted base)
  H, L                       the heartbeat expiry and the hardware halt time (the halt loop, and a lever after a halt)
Per site s:   epoch (edition in force), ep_time (when it last changed), committed_ed (editions ever committed),
              kfuse (threshold in force), honest_all (every edition change so far had honest approval),
              stop (a stop is ordered), stop_time
Per chip c:   chip_ed (edition installed), halted, halted_at, hb_exp (heartbeat expiry), gpu_run (its GPU is running)
Per endpoint: ep_ed (edition installed on the endpoint itself)
Per ticket t: minted, spent, the chip, endpoint, action, budget key, amount and edition it carries, n_eff (effects it
              produced), and two ghosts: the endpoint's edition when it executed (exec_ed) and whether the edition had
              not expired then (exec_in_date)
Per site and budget key: reserved, committed (the fleet ledger's two counts)
Global:       now

The theorems (docs/29 section 2.2):
  T1  Property 1. Every effect comes from exactly one ticket, minted by a governor that was running, from a rule of the
      edition in force at the endpoint that allowed exactly that action, at the same site, executed while that edition
      was in date; and the committed total of every budget key at every site never exceeds its cap.
  T2  Property 2. A GPU runs only while its governor's heartbeat is current, or within L of the halt: so within H + L of
      the last heartbeat, within 2L of a stop order, within H + L of its site moving to an edition the governor does
      not have; and a halt is left only by a clear signed by the threshold of the site's keys, never while a stop
      stands.
  T3  Condition 3. Every edition change at every site had honest approval, the threshold in force never falls below the
      fused floor, and it never rises above what the honest holders can meet: recovery is always possible.
  T4  The boundary. A step signed by one site's keys changes nothing at any other site, and a ticket minted at one site
      cannot execute at another.

How the proofs work: as in core_invariants.py, each invariant is stated for ONE arbitrary element (a ticket, a chip, a
site, a site and budget key), and induction is checked step by step assuming the invariant only at that element and at
the elements the step touches. Each step touches one entry of each array, so this is sound, and it keeps every query
free of quantifiers.

The controls (docs/29 R5): every theorem is also checked on deliberately broken machines, and each must FAIL with a
counterexample. A proof that cannot fail proves nothing.

What this model does not cover, stated so that nobody reads more into a PASS than there is:
  * The physics and the wiring: that every path out of the machine passes an endpoint is condition 1, taken from the exit
    register (docs/research/exit-register.md). Its open rows are listed at the end of the run as assumptions.
  * The content of the rules: an allowed action may still be harmful. Condition 2 is Experiment B.
  * The link to the code is checked separately, by replaying govsim traces (the L4 trace conformance).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from z3 import (And, ArraySort, BoolSort, BoolVal, Const, Consts, DeclareSort, Function, If, Implies, Int, IntSort, IntVal,
                Not, Or, Select, Solver, Store, sat, unknown, unsat)

ROOT = Path(__file__).resolve().parent.parent

# ---- sorts and rigid facts ---------------------------------------------------------------------------------------
Site = DeclareSort("Site")
Chip = DeclareSort("Chip")
Ep = DeclareSort("Endpoint")
Tk = DeclareSort("Ticket")
Act = DeclareSort("Action")
BK = DeclareSort("BudgetKey")

site_c = Function("site_c", Chip, Site)
site_e = Function("site_e", Ep, Site)
allows = Function("allows", Site, IntSort(), Act, BoolSort())
expiry = Function("expiry", Site, IntSort(), IntSort())
cap = Function("cap", Site, BK, IntSort())
n_hon = Function("n_hon", Site, IntSort())
att_keys = Function("att_keys", Site, IntSort())
kfloor = Function("kfloor", Site, IntSort())
H, L = Int("H"), Int("L")


def rigid_assumptions(*sites, keys=()):
    """What the trusted base guarantees about the rigid facts, at the given sites and (site, budget key) pairs: the floor
    is at least one, the attacker holds fewer keys than the floor (docs/29 section 2.1), caps are not negative, and the
    two hardware times are positive."""
    out = [H > 0, L > 0]
    for s in sites:
        out += [kfloor(s) >= 1, att_keys(s) >= 0, att_keys(s) < kfloor(s), n_hon(s) >= kfloor(s)]
    for s, b in keys:
        out += [cap(s, b) >= 0]
    return out


# ---- the state -----------------------------------------------------------------------------------------------------
FIELDS = {
    # per site
    "epoch": ArraySort(Site, IntSort()), "ep_time": ArraySort(Site, IntSort()),
    "committed_ed": ArraySort(Site, ArraySort(IntSort(), BoolSort())), "kfuse": ArraySort(Site, IntSort()),
    "honest_all": ArraySort(Site, BoolSort()), "stop": ArraySort(Site, BoolSort()), "stop_time": ArraySort(Site, IntSort()),
    # per chip
    "chip_ed": ArraySort(Chip, IntSort()), "halted": ArraySort(Chip, BoolSort()), "halted_at": ArraySort(Chip, IntSort()),
    "hb_exp": ArraySort(Chip, IntSort()), "gpu_run": ArraySort(Chip, BoolSort()),
    # per endpoint
    "ep_ed": ArraySort(Ep, IntSort()),
    # per ticket
    "minted": ArraySort(Tk, BoolSort()), "spent": ArraySort(Tk, BoolSort()), "t_chip": ArraySort(Tk, Chip),
    "t_ep": ArraySort(Tk, Ep), "t_act": ArraySort(Tk, Act), "t_bk": ArraySort(Tk, BK), "t_amt": ArraySort(Tk, IntSort()),
    "t_ed": ArraySort(Tk, IntSort()), "n_eff": ArraySort(Tk, IntSort()), "exec_ed": ArraySort(Tk, IntSort()),
    "exec_in_date": ArraySort(Tk, BoolSort()), "lapsed": ArraySort(Tk, BoolSort()),
    # per site and budget key: the fleet ledger
    "reserved": ArraySort(Site, ArraySort(BK, IntSort())), "committed": ArraySort(Site, ArraySort(BK, IntSort())),
    # global
    "now": IntSort(),
}


class State:
    """The machine's state at one moment: one Z3 constant per field in FIELDS, named with ``tag`` so that the states
    before and after a step can appear in one formula."""
    def __init__(self, tag: str):
        for name, sort in FIELDS.items():
            setattr(self, name, Const(f"{name}_{tag}", sort))


def unchanged(s: State, t: State, *changed: str):
    """``t`` equals ``s`` on every field except the ones named."""
    return And(*[getattr(s, n) == getattr(t, n) for n in FIELDS if n not in changed])


def init(s: State, site, chip, ep, tk, bk):
    """The initial state, at one arbitrary element of each sort: edition 0 committed and installed everywhere, no ticket
    minted, nothing reserved or committed, no stop, every governor running with a current heartbeat."""
    return And(
        s.now >= 0,
        s.epoch[site] == 0, s.ep_time[site] == 0, s.committed_ed[site][0], s.kfuse[site] == kfloor(site),
        s.honest_all[site], Not(s.stop[site]), s.stop_time[site] == 0,
        s.chip_ed[chip] == 0, Not(s.halted[chip]), s.halted_at[chip] == 0, s.hb_exp[chip] == s.now + H, s.gpu_run[chip],
        s.ep_ed[ep] == 0,
        Not(s.minted[tk]), Not(s.spent[tk]), s.n_eff[tk] == 0, Not(s.exec_in_date[tk]), Not(s.lapsed[tk]),
        s.reserved[site][bk] == 0, s.committed[site][bk] == 0,
    )


def committed_eds_init(s: State, site, x):
    """Initially the only committed edition is 0."""
    return s.committed_ed[site][x] == (x == 0)


# ---- inputs and the steps ------------------------------------------------------------------------------------------
def make_inputs(tag="i"):
    """The attacker's free choices for one step. Each is an unknown for the solver, so every value is covered."""
    i = {}
    i["site"] = Const(f"site_{tag}", Site)
    i["key_site"] = Const(f"key_site_{tag}", Site)     # the site whose keys signed this step's message
    i["chip"] = Const(f"chip_{tag}", Chip)
    i["ep"] = Const(f"ep_{tag}", Ep)
    i["tk"] = Const(f"tk_{tag}", Tk)
    i["act"] = Const(f"act_{tag}", Act)
    i["bk"] = Const(f"bk_{tag}", BK)
    i["amt"], i["ed"], i["d"], i["sigs_att"], i["sigs_hon"], i["claimed_k"] = Consts(
        f"amt_{tag} ed_{tag} d_{tag} sigs_att_{tag} sigs_hon_{tag} claimed_k_{tag}", IntSort())
    i["wit"], i["honest_ok"] = Consts(f"wit_{tag} honest_ok_{tag}", BoolSort())
    return i


def quorum(s: State, i, site):
    """A message signed by the threshold in force at ``site``: the attacker contributes at most the keys it holds, the
    honest holders at most theirs and only if they approve, and together they reach the threshold."""
    return And(i["key_site"] == site, i["sigs_att"] >= 0, i["sigs_att"] <= att_keys(site), i["sigs_hon"] >= 0,
               i["sigs_hon"] <= n_hon(site), Implies(i["sigs_hon"] > 0, i["honest_ok"]),
               i["sigs_att"] + i["sigs_hon"] >= s.kfuse[site])


# Each mutant switches off one guard of the honest machine. The controls run every theorem on each mutant and require
# a counterexample: the proof must be able to see the defect.
MUTANTS = {
    "replay": "execute does not require an unspent ticket",
    "stale_edition": "the endpoint does not compare the ticket's edition with its own",
    "expired_edition": "the endpoint does not check its edition's expiry",
    "no_ledger_commit": "execute does not commit at the fleet ledger (only the reservation at mint is counted, and a "
                        "reservation can lapse and be made again)",
    "cross_site_ticket": "a governor may mint a ticket for an endpoint at another site",
    "cross_site_heartbeat": "a governor accepts a heartbeat signed by another site's keys",
    "soft_halt": "time may pass beyond a governor's heartbeat expiry without the hardware halting it",
    "no_lever": "a halted governor's GPU may keep running indefinitely (no hardware lever)",
    "clear_without_quorum": "a halt can be cleared without the threshold of the site's keys",
    "threshold_from_image": "an edition may set the threshold below the fused floor",
    "heartbeat_after_stop": "the heartbeat signers keep signing after a stop is ordered",
    "halted_commit": "the endpoint does not require the minting governor to be running at commit",
    "unsigned_stop": "a stop may be ordered at a site without that site's keys",
}


def step_list(s: State, t: State, i, mutant: str | None = None):
    """The named transitions. ``mutant`` names one guard from MUTANTS to switch off."""
    m = mutant
    site, chip, ep, tk, bk = i["site"], i["chip"], i["ep"], i["tk"], i["bk"]
    sc, se = site_c(chip), site_e(ep)
    on = lambda guard, name: BoolVal(True) if m == name else guard        # a guard that the named mutant removes

    # An edition change at a site: the next number, signed by the threshold in force, which the new edition may reset
    # but never below the fused floor; the honest holders approve only a threshold they can meet.
    edition = And(
        quorum(s, i, site), i["ed"] == s.epoch[site] + 1,
        on(i["claimed_k"] >= kfloor(site), "threshold_from_image"), i["claimed_k"] >= 1,
        Implies(i["honest_ok"], i["claimed_k"] <= n_hon(site)),
        t.epoch == Store(s.epoch, site, i["ed"]), t.ep_time == Store(s.ep_time, site, s.now),
        t.committed_ed == Store(s.committed_ed, site, Store(s.committed_ed[site], i["ed"], True)),
        t.kfuse == Store(s.kfuse, site, i["claimed_k"]),
        t.honest_all == Store(s.honest_all, site, And(s.honest_all[site], i["honest_ok"])),
        unchanged(s, t, "epoch", "ep_time", "committed_ed", "kfuse", "honest_all"))
    # A governor or an endpoint installs a committed, newer edition of its own site (the attacker may delay this
    # forever; it cannot deliver an edition that was never committed, or an older one).
    chip_install = And(s.committed_ed[sc][i["ed"]], i["ed"] > s.chip_ed[chip],
                       t.chip_ed == Store(s.chip_ed, chip, i["ed"]), unchanged(s, t, "chip_ed"))
    ep_install = And(s.committed_ed[se][i["ed"]], i["ed"] > s.ep_ed[ep],
                     t.ep_ed == Store(s.ep_ed, ep, i["ed"]), unchanged(s, t, "ep_ed"))
    # A heartbeat: signed by the threshold of the governor's own site's heartbeat signers, over the edition in force,
    # never after a stop is ordered. A current governor renews its timer; a governor that finds the site has moved to an
    # edition it does not have halts at once (the straggler halt).
    hb_ok = And(on(i["key_site"] == sc, "cross_site_heartbeat"),
                on(Not(s.stop[sc]), "heartbeat_after_stop"), i["ed"] == s.epoch[i["key_site"]])
    hb_renew = And(hb_ok, Not(s.halted[chip]), i["ed"] == s.chip_ed[chip],
                   t.hb_exp == Store(s.hb_exp, chip, s.now + H), unchanged(s, t, "hb_exp"))
    hb_straggler = And(hb_ok, Not(s.halted[chip]), i["ed"] > s.chip_ed[chip],
                       t.halted == Store(s.halted, chip, True), t.halted_at == Store(s.halted_at, chip, s.now),
                       unchanged(s, t, "halted", "halted_at"))
    # Minting: a running governor, for an endpoint at its own site, from a rule of its installed edition that allows the
    # action, with the witnesses present, reserving the amount at the fleet ledger within the cap.
    mint = And(Not(s.minted[tk]), Not(s.halted[chip]), on(se == sc, "cross_site_ticket"),
               allows(sc, s.chip_ed[chip], i["act"]), i["wit"], i["amt"] >= 0,
               s.reserved[sc][bk] + i["amt"] <= cap(sc, bk),
               t.minted == Store(s.minted, tk, True), t.t_chip == Store(s.t_chip, tk, chip), t.t_ep == Store(s.t_ep, tk, ep),
               t.t_act == Store(s.t_act, tk, i["act"]), t.t_bk == Store(s.t_bk, tk, bk), t.t_amt == Store(s.t_amt, tk, i["amt"]),
               t.t_ed == Store(s.t_ed, tk, s.chip_ed[chip]),
               t.reserved == Store(s.reserved, sc, Store(s.reserved[sc], bk, s.reserved[sc][bk] + i["amt"])),
               unchanged(s, t, "minted", "t_chip", "t_ep", "t_act", "t_bk", "t_amt", "t_ed", "reserved"))
    # Executing: the endpoint named in the ticket, holding the same edition, in date on its own clock; the minting
    # governor commits it at the fleet ledger within the cap and must be running. One effect, and the ticket is spent.
    tsite = site_e(s.t_ep[tk])
    tbk, tamt = s.t_bk[tk], s.t_amt[tk]
    execute = And(s.minted[tk], on(Not(s.spent[tk]), "replay"), s.t_ep[tk] == ep,
                  on(s.ep_ed[ep] == s.t_ed[tk], "stale_edition"),
                  on(s.now < expiry(se, s.ep_ed[ep]), "expired_edition"),
                  on(Not(s.halted[s.t_chip[tk]]), "halted_commit"),
                  on(And(Not(s.lapsed[tk]), s.committed[tsite][tbk] + tamt <= cap(tsite, tbk)), "no_ledger_commit"),
                  t.spent == Store(s.spent, tk, True), t.n_eff == Store(s.n_eff, tk, s.n_eff[tk] + 1),
                  t.exec_ed == Store(s.exec_ed, tk, s.ep_ed[ep]),
                  t.exec_in_date == Store(s.exec_in_date, tk, s.now < expiry(se, s.ep_ed[ep])),
                  t.committed == Store(s.committed, tsite, Store(s.committed[tsite], tbk, s.committed[tsite][tbk] + tamt)),
                  unchanged(s, t, "spent", "n_eff", "exec_ed", "exec_in_date", "committed"))
    # A reservation lapses (its time to live runs out before the ticket is used): the ledger frees the reserved amount,
    # and the ticket can no longer be committed. The attacker chooses when; this is what makes the commit check matter.
    lapse = And(s.minted[tk], Not(s.spent[tk]), Not(s.lapsed[tk]),
                t.lapsed == Store(s.lapsed, tk, True),
                t.reserved == Store(s.reserved, tsite, Store(s.reserved[tsite], tbk, s.reserved[tsite][tbk] - tamt)),
                unchanged(s, t, "lapsed", "reserved"))
    # A stop ordered at a site: signed by the threshold of that site's keys. (Anyone who controls a host can still halt
    # a governor by withholding its heartbeat or cutting its loop: that is the halt step, a denial of service at the
    # place the attacker already controls. What no one can do is order a stop with another site's keys.)
    stop = And(Not(s.stop[site]), on(quorum(s, i, site), "unsigned_stop"),
               t.stop == Store(s.stop, site, True), t.stop_time == Store(s.stop_time, site, s.now),
               unchanged(s, t, "stop", "stop_time"))
    # Any governor may be halted at any time (tamper, a cut loop, a signed HALT, its heartbeat running out).
    halt = And(Not(s.halted[chip]), t.halted == Store(s.halted, chip, True), t.halted_at == Store(s.halted_at, chip, s.now),
               unchanged(s, t, "halted", "halted_at"))
    # The lever: a halted governor's GPU stops (throttle, reset or power), without the GPU's cooperation.
    lever = And(s.halted[chip], t.gpu_run == Store(s.gpu_run, chip, False), unchanged(s, t, "gpu_run"))
    # A clear: signed by the threshold of the governor's own site's keys, for a governor on the edition in force, never
    # while a stop stands. The clear carries a fresh heartbeat.
    clear_auth = on(quorum(s, i, sc), "clear_without_quorum")
    clear = And(s.halted[chip], clear_auth, Not(s.stop[sc]), s.chip_ed[chip] == s.epoch[sc],
                t.halted == Store(s.halted, chip, False), t.gpu_run == Store(s.gpu_run, chip, True),
                t.hb_exp == Store(s.hb_exp, chip, s.now + H), unchanged(s, t, "halted", "gpu_run", "hb_exp"))
    # Lifting a stop: the threshold of the site's keys.
    lift = And(s.stop[site], quorum(s, i, site), t.stop == Store(s.stop, site, False), unchanged(s, t, "stop"))
    # Time passes, but never past a hardware deadline (these are the trusted timers: the heartbeat timer halts the
    # governor, the halt loop halts every governor of a stopped site within L, the lever stops a halted GPU within L).
    # The guard is stated here for the chip the step names; an instance of a guard that holds for every chip, which is
    # sound for the induction (a weaker assumption about the step).
    c, d = chip, i["d"]
    tick_guard = And(d >= 0,
                     on(Implies(Not(s.halted[c]), s.now + d <= s.hb_exp[c]), "soft_halt"),
                     Implies(And(s.stop[sc], Not(s.halted[c])), s.now + d <= s.stop_time[sc] + L),
                     on(Implies(And(s.halted[c], s.gpu_run[c]), s.now + d <= s.halted_at[c] + L), "no_lever"))
    tick = And(tick_guard, t.now == s.now + d, unchanged(s, t, "now"))
    return [("edition", edition), ("chip installs an edition", chip_install), ("endpoint installs an edition", ep_install),
            ("heartbeat renews", hb_renew), ("heartbeat halts a straggler", hb_straggler), ("mint", mint),
            ("execute", execute), ("reservation lapses", lapse), ("stop ordered", stop), ("halt", halt), ("lever", lever), ("clear", clear),
            ("stop lifted", lift), ("time passes", tick), ("nothing happens", unchanged(s, t))]


def steps(s, t, i, mutant=None):
    return Or(*[tr for _, tr in step_list(s, t, i, mutant)])


# ---- the invariants, one element at a time -------------------------------------------------------------------------
def inv_ticket(s: State, k):
    """For one ticket k. T1's per-ticket core."""
    ksite = site_e(s.t_ep[k])
    return And(
        s.n_eff[k] >= 0, s.n_eff[k] <= 1,                                   # T1: at most one effect per ticket
        s.spent[k] == (s.n_eff[k] == 1),
        Implies(s.spent[k], s.minted[k]),
        Implies(Not(s.minted[k]), s.n_eff[k] == 0),
        Implies(s.minted[k], And(allows(ksite, s.t_ed[k], s.t_act[k]),       # T1: from a rule that allowed exactly it
                                 site_c(s.t_chip[k]) == ksite,               # T4: minted and executed at one site
                                 s.t_amt[k] >= 0, s.committed_ed[ksite][s.t_ed[k]])),
        Implies(s.n_eff[k] == 1, And(s.exec_ed[k] == s.t_ed[k], s.exec_in_date[k])),   # T1: the edition in force, in date
    )


def inv_budget(s: State, site, b):
    """For one site and budget key: the fleet ledger's counts. T1's budget part."""
    return And(s.committed[site][b] >= 0, s.committed[site][b] <= cap(site, b))


def inv_site(s: State, site):
    """For one site. T3, and what T2 needs from the site."""
    return And(
        s.epoch[site] >= 0, s.committed_ed[site][s.epoch[site]], s.ep_time[site] <= s.now,
        s.kfuse[site] >= kfloor(site), s.kfuse[site] <= n_hon(site),          # T3: never below the floor, always meetable
        s.honest_all[site],                                                   # T3: every edition change had honest approval
        Implies(s.stop[site], s.stop_time[site] <= s.now),
    )


def inv_edition(s: State, site, x):
    """For one site and one edition number: an edition is committed only if it is between 0 and the one in force."""
    return Implies(s.committed_ed[site][x], And(x >= 0, x <= s.epoch[site]))


def inv_chip(s: State, c):
    """For one governor chip. T2's core: the heartbeat timer and the halt path bound how long its GPU can run."""
    sc = site_c(c)
    return And(
        s.hb_exp[c] <= s.now + H,
        Implies(Not(s.halted[c]), s.now <= s.hb_exp[c]),                     # a running governor has a current heartbeat
        Implies(s.halted[c], And(s.halted_at[c] <= s.now, s.halted_at[c] <= s.hb_exp[c])),
        Implies(s.gpu_run[c], Or(Not(s.halted[c]), s.now <= s.halted_at[c] + L)),   # a halted governor's GPU stops within L
        s.chip_ed[c] >= 0, s.chip_ed[c] <= s.epoch[sc], s.committed_ed[sc][s.chip_ed[c]],
        Implies(s.chip_ed[c] < s.epoch[sc], s.hb_exp[c] <= s.ep_time[sc] + H),   # a straggler's heartbeat runs out
        Implies(s.stop[sc], s.hb_exp[c] <= s.stop_time[sc] + H),             # no heartbeat after a stop
        Implies(And(s.stop[sc], Not(s.halted[c])), s.now <= s.stop_time[sc] + L),   # the loop halts every chip within L
        Implies(And(s.stop[sc], s.halted[c]), s.halted_at[c] <= s.stop_time[sc] + L),
    )


def inv_ep(s: State, e):
    """For one endpoint: it holds a committed edition of its own site."""
    se = site_e(e)
    return And(s.ep_ed[e] >= 0, s.ep_ed[e] <= s.epoch[se], s.committed_ed[se][s.ep_ed[e]])


# ---- the theorems as statements ------------------------------------------------------------------------------------
def theorems(s: State, k, c, site, b):
    """T1 to T3 as plain statements about one state, at an arbitrary ticket k, chip c, site and budget key. They are
    proved by showing the invariants imply them; the invariants are proved by induction."""
    sc = site_c(c)
    return {
        "T1 Property 1: every effect comes from exactly one ticket, minted from a rule that allowed exactly that action, "
        "under the edition in force at the endpoint, in date, at the same site":
            Implies(s.n_eff[k] >= 1, And(s.n_eff[k] == 1, s.minted[k], allows(site_e(s.t_ep[k]), s.t_ed[k], s.t_act[k]),
                                         s.exec_ed[k] == s.t_ed[k], s.exec_in_date[k],
                                         site_c(s.t_chip[k]) == site_e(s.t_ep[k]))),
        "T1 Property 1: the committed total of every budget key at every site stays within its cap":
            s.committed[site][b] <= cap(site, b),
        "T2 Property 2: a GPU runs only within H + L of its last heartbeat":
            Implies(s.gpu_run[c], s.now <= s.hb_exp[c] + L),
        "T2 Property 2: after a stop order, every GPU of the site stops within 2L":
            Implies(And(s.stop[sc], s.gpu_run[c]), s.now <= s.stop_time[sc] + 2 * L),
        "T2 Property 2: a governor on an old edition stops its GPU within H + L of the site's change":
            Implies(And(s.chip_ed[c] < s.epoch[sc], s.gpu_run[c]), s.now <= s.ep_time[sc] + H + L),
        "T3 Condition 3: every edition change had honest approval; the threshold stays between the floor and what the "
        "honest holders can meet":
            And(s.honest_all[site], s.kfuse[site] >= kfloor(site), s.kfuse[site] <= n_hon(site)),
    }


# ---- running the proofs ----------------------------------------------------------------------------------------------
TIMEOUT_MS = 120_000
BMC_DEPTH = 5          # steps; each depth is checked separately


def check(assumptions, claim, timeout_ms=None):
    """'proved' if the claim follows from the assumptions, 'counterexample' if Z3 finds a state where it does not,
    'unknown' on a timeout (recorded as inconclusive, never as a pass)."""
    sol = Solver()
    sol.set("timeout", timeout_ms or TIMEOUT_MS)
    sol.add(*assumptions)
    sol.add(Not(claim))
    r = sol.check()
    return "proved" if r == unsat else "counterexample" if r == sat else "unknown"


def satisfiable(assumptions):
    sol = Solver()
    sol.set("timeout", TIMEOUT_MS)
    sol.add(*assumptions)
    r = sol.check()
    return "sat" if r == sat else "unsat" if r == unsat else "unknown"


class Run:
    def __init__(self):
        self.records = []

    def note(self, group, name, result, want):
        ok = result == want
        self.records.append({"group": group, "name": name, "result": result, "expected": want, "pass": ok})
        print(f"{'PASS' if ok else 'FAIL'}  [{group}] {name}: {result}")
        return ok


def induction(run: Run, mutant=None, quiet=False):
    """Prove every invariant by induction on the honest machine (or a mutant). Returns True if every case is proved."""
    s, t = State("s"), State("t")
    i = make_inputs()
    k = Const("k", Tk); c = Const("c", Chip); e = Const("e", Ep); site = Const("site", Site); b = Const("b", BK)
    x = Int("x")
    # The elements the step may touch, and the arbitrary element the conclusion is about.
    touched_sites = [site, i["site"], site_c(c), site_c(i["chip"]), site_e(e), site_e(i["ep"]), i["key_site"],
                     site_e(s.t_ep[k]), site_e(s.t_ep[i["tk"]]), site_c(s.t_chip[i["tk"]]), site_c(s.t_chip[k])]
    rigid = rigid_assumptions(*touched_sites, keys=[(site, b), (site_c(i["chip"]), i["bk"]), (site_e(s.t_ep[i["tk"]]), s.t_bk[i["tk"]])])
    hyp_common = rigid + [inv_site(s, z) for z in touched_sites]
    goals = {
        "ticket": (lambda st: inv_ticket(st, k), [inv_ticket(s, k), inv_ticket(s, i["tk"]),
                                                  inv_chip(s, s.t_chip[i["tk"]]), inv_chip(s, i["chip"]), inv_ep(s, i["ep"]),
                                                  inv_edition(s, site_e(s.t_ep[k]), s.t_ed[k]),
                                                  inv_edition(s, site_c(i["chip"]), i["ed"])]),
        "budget": (lambda st: inv_budget(st, site, b), [inv_budget(s, site, b), inv_budget(s, site_c(i["chip"]), i["bk"]),
                                                        inv_budget(s, site_e(s.t_ep[i["tk"]]), s.t_bk[i["tk"]]),
                                                        inv_ticket(s, i["tk"])]),
        "site": (lambda st: inv_site(st, site), [inv_edition(s, site, i["ed"])]),
        "edition": (lambda st: inv_edition(st, site, x), [inv_edition(s, site, x), inv_edition(s, i["site"], x)]),
        "chip": (lambda st: inv_chip(st, c), [inv_chip(s, c), inv_chip(s, i["chip"]),
                                              inv_edition(s, site_c(c), i["ed"]), inv_edition(s, site_c(i["chip"]), i["ed"])]),
        "endpoint": (lambda st: inv_ep(st, e), [inv_ep(s, e), inv_ep(s, i["ep"]),
                                                inv_edition(s, site_e(e), i["ed"]), inv_edition(s, site_e(i["ep"]), i["ed"])]),
    }
    all_ok = True
    broken = []                       # for a mutant: which invariant, under which step, the defect breaks
    for gname, (concl, extra) in goals.items():
        for sname, tr in step_list(s, t, i, mutant):
            # for the tick step, the guard is instantiated at the chip the conclusion is about
            if sname == "time passes":
                tr = And(tr, i["chip"] == c) if gname == "chip" else tr
            r = check(hyp_common + extra + [tr], concl(t))
            if mutant is None:
                all_ok &= run.note("induction", f"invariant[{gname}] preserved by: {sname}", r, "proved")
            else:
                if r != "proved":
                    broken.append(f"{gname}/{sname}: {r}")
                all_ok &= r == "proved"
    return all_ok if mutant is None else broken


def one_step_checks(mutant=None) -> dict:
    """The theorems that relate one state to the next, checked on the honest machine (or a mutant): from any state that
    satisfies the invariants at the elements involved, every step keeps them."""
    s, t = State("s"), State("t")
    i = make_inputs()
    c = Const("c", Chip)
    k = Const("k", Tk)
    sc = site_c(c)
    kc = s.t_chip[k]
    rig = rigid_assumptions(sc, i["site"], i["key_site"], site_c(i["chip"]), site_c(kc))
    hyp = rig + [inv_chip(s, c), inv_site(s, sc), inv_ticket(s, k), inv_chip(s, kc), steps(s, t, i, mutant)]
    claims = {
        "T2 Property 2: a halted governor leaves the halt only by a clear signed by the threshold of its own site's keys, "
        "never while a stop stands":
            Implies(And(s.halted[c], Not(t.halted[c])), And(quorum(s, i, sc), Not(s.stop[sc]))),
        "T1 Property 1: nothing executes while the governor that minted its ticket is halted":
            Implies(s.halted[kc], t.n_eff[k] == s.n_eff[k]),
        "T4 boundary: no step signed by another site's keys extends this site's heartbeats, clears its governors, orders "
        "it a stop, or changes its edition or threshold":
            Implies(i["key_site"] != sc,
                    And(t.hb_exp[c] <= s.hb_exp[c], Implies(s.halted[c], t.halted[c]),
                        Implies(Not(s.stop[sc]), Not(t.stop[sc])), t.epoch[sc] == s.epoch[sc], t.kfuse[sc] == s.kfuse[sc])),
    }
    return {name: check(hyp, claim) for name, claim in claims.items()}



def bmc(depth: int, mutant=None, timeout_ms=None) -> dict:
    """The bounded cross-check (docs/29 section 2.3, step 2): every execution of up to ``depth`` steps from the initial
    state, with no induction and no invariant, is searched for a state that breaks a theorem. It does not depend on the
    invariants being right, so it checks them from the other side. A result per theorem: 'proved' (no execution of that
    length breaks it), 'counterexample', or 'unknown'."""
    from z3 import ForAll
    st = [State(f"b{n}") for n in range(depth + 1)]
    ins = [make_inputs(f"b{n}") for n in range(depth)]
    s0 = st[0]
    zs, zc, ze, zk, zb, zx = Const("zs", Site), Const("zc", Chip), Const("ze", Ep), Const("zk", Tk), Const("zb", BK), Int("zx")
    rig = [H > 0, L > 0,
           ForAll([zs], And(kfloor(zs) >= 1, att_keys(zs) >= 0, att_keys(zs) < kfloor(zs), n_hon(zs) >= kfloor(zs))),
           ForAll([zs, zb], cap(zs, zb) >= 0)]
    init_all = [s0.now >= 0,
                ForAll([zs], And(s0.epoch[zs] == 0, s0.ep_time[zs] == 0, s0.kfuse[zs] == kfloor(zs), s0.honest_all[zs],
                                 Not(s0.stop[zs]), s0.stop_time[zs] == 0)),
                ForAll([zs, zx], s0.committed_ed[zs][zx] == (zx == 0)),
                ForAll([zc], And(s0.chip_ed[zc] == 0, Not(s0.halted[zc]), s0.halted_at[zc] == 0, s0.hb_exp[zc] == s0.now + H,
                                 s0.gpu_run[zc])),
                ForAll([ze], s0.ep_ed[ze] == 0),
                ForAll([zk], And(Not(s0.minted[zk]), Not(s0.spent[zk]), s0.n_eff[zk] == 0, Not(s0.exec_in_date[zk]),
                                 Not(s0.lapsed[zk]))),
                ForAll([zs, zb], And(s0.reserved[zs][zb] == 0, s0.committed[zs][zb] == 0))]
    trans = []
    for n in range(depth):
        tr = steps(st[n], st[n + 1], ins[n], mutant)
        # the tick's urgency guard holds for EVERY chip and site in the bounded run (the real hardware deadline)
        c2 = Const(f"ct{n}", Chip)
        s, d = st[n], ins[n]["d"]
        urgent = ForAll([c2], And(
            Implies(Not(s.halted[c2]), s.now + d <= s.hb_exp[c2]) if mutant != "soft_halt" else BoolVal(True),
            Implies(And(s.stop[site_c(c2)], Not(s.halted[c2])), s.now + d <= s.stop_time[site_c(c2)] + L),
            Implies(And(s.halted[c2], s.gpu_run[c2]), s.now + d <= s.halted_at[c2] + L) if mutant != "no_lever" else BoolVal(True)))
        trans.append(And(tr, Implies(st[n + 1].now != s.now, urgent)))
    last = st[depth]
    k, c, site, b = Const("bk_", Tk), Const("bc_", Chip), Const("bs_", Site), Const("bb_", BK)
    out = {}
    for name, claim in theorems(last, k, c, site, b).items():
        out[name] = check(rig + init_all + trans, claim, timeout_ms)
    return out



def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = argv[argv.index("--json") + 1] if "--json" in argv else None
    run = Run()
    ok = True
    print("Experiment A (docs/29): the claim of GOAL.md on a model of server, rack and data center\n")

    # 1. the invariants hold initially
    s = State("s"); k = Const("k", Tk); c = Const("c", Chip); e = Const("e", Ep); site = Const("site", Site)
    b = Const("b", BK); x = Int("x")
    rig = rigid_assumptions(site, site_c(c), site_e(e), site_e(s.t_ep[k]), keys=[(site, b)])
    base = [init(s, site, c, e, k, b), init(s, site_c(c), c, e, k, b), init(s, site_e(e), c, e, k, b),
            init(s, site_e(s.t_ep[k]), c, e, k, b),
            committed_eds_init(s, site, x), committed_eds_init(s, site_c(c), s.chip_ed[c]),
            committed_eds_init(s, site_e(e), s.ep_ed[e]), committed_eds_init(s, site, IntVal(0))]
    for name, inv in [("ticket", inv_ticket(s, k)), ("budget", inv_budget(s, site, b)), ("site", inv_site(s, site)),
                      ("edition", inv_edition(s, site, x)), ("chip", inv_chip(s, c)), ("endpoint", inv_ep(s, e))]:
        ok &= run.note("initial", f"invariant[{name}] holds in the initial state", check(rig + base, inv), "proved")

    # 2. the invariants are preserved by every step (induction)
    ok &= induction(run)

    # 3. the theorems follow from the invariants
    s = State("s"); k = Const("k", Tk); c = Const("c", Chip); site = Const("site", Site); b = Const("b", BK)
    rig = rigid_assumptions(site, site_c(c), site_e(s.t_ep[k]), keys=[(site, b)])
    invs = rig + [inv_ticket(s, k), inv_budget(s, site, b), inv_site(s, site), inv_site(s, site_c(c)), inv_chip(s, c)]
    for name, claim in theorems(s, k, c, site, b).items():
        ok &= run.note("theorem", name, check(invs, claim), "proved")

    # 4. the one-step theorems (T2's halt rule, T1's running governor, T4's boundary)
    for name, r in one_step_checks().items():
        ok &= run.note("theorem", name, r, "proved")
    k = Const("k", Tk)
    ok &= run.note("theorem", "T4 boundary: a ticket minted at one site never executes at an endpoint of another",
                   check(rigid_assumptions(site_e(s.t_ep[k])) + [inv_ticket(s, k)],
                         Implies(s.n_eff[k] >= 1, site_c(s.t_chip[k]) == site_e(s.t_ep[k]))), "proved")

    # 4b. the bounded cross-check: every execution of up to BMC_DEPTH steps from the start, no invariants used
    print()
    for depth in range(1, BMC_DEPTH + 1):
        for name, r in bmc(depth).items():
            ok &= run.note("bounded", f"depth {depth}: {name.split(':')[0]}: {name.split(':', 1)[1].strip()[:70]}", r, "proved")

    # 5. the controls: every mutant must break the induction (the proof can see each defect)
    print()
    for mname, what in MUTANTS.items():
        broken = induction(run, mutant=mname, quiet=True)
        broken += [f"one-step/{n.split(':')[0]}: {r}" for n, r in one_step_checks(mname).items() if r != "proved"]
        # informational: a short search; the induction above is the control the protocol counts
        bres = bmc(BMC_DEPTH, mname, timeout_ms=20_000)
        seen = [n.split(':')[0] for n, r in bres.items() if r == "counterexample"]
        timed_out = sum(r == "unknown" for r in bres.values())
        summary = (f"counterexample in {', '.join(seen)}" if seen else "no counterexample found") + \
                  (f"; {timed_out} of {len(bres)} searches timed out (inconclusive)" if timed_out else "")
        run.records.append({"group": "control-bounded", "name": mname, "result": summary,
                            "expected": "informational", "pass": True})
        where = "; ".join(broken[:3]) if broken else ""
        ok &= run.note("control", f"mutant '{mname}' ({what}) is caught" + (f" at {where}" if where else ""),
                       "caught" if broken else "not caught", "caught")

    # 6. non-vacuity: the honest machine can do the things the theorems talk about
    print()
    s, t, u = State("s"), State("t"), State("u")
    i1, i2 = make_inputs("1"), make_inputs("2")
    site0, c0, e0, k0, b0 = Const("site0", Site), Const("c0", Chip), Const("e0", Ep), Const("k0", Tk), Const("b0", BK)
    rig = rigid_assumptions(site0, keys=[(site0, b0)])
    start = [init(s, site0, c0, e0, k0, b0), site_c(c0) == site0, site_e(e0) == site0,
             committed_eds_init(s, site0, IntVal(0))]
    mint1 = dict(step_list(s, t, i1))["mint"]
    exec2 = dict(step_list(t, u, i2))["execute"]
    ok &= run.note("non-vacuity", "an allowed action can be minted and executed (one effect)",
                   satisfiable(rig + start + [mint1, i1["chip"] == c0, i1["ep"] == e0, i1["tk"] == k0, i1["bk"] == b0,
                                              exec2, i2["tk"] == k0, i2["ep"] == e0, u.n_eff[k0] == 1]), "sat")
    stop1 = dict(step_list(s, t, i1))["stop ordered"]
    ok &= run.note("non-vacuity", "a stop can be ordered", satisfiable(rig + start + [stop1, i1["site"] == site0]), "sat")
    ed1 = dict(step_list(s, t, i1))["edition"]
    ok &= run.note("non-vacuity", "an edition can change with honest approval",
                   satisfiable(rig + start + [ed1, i1["site"] == site0, t.epoch[site0] == 1]), "sat")
    halt1 = dict(step_list(s, t, i1))["halt"]
    clear2 = dict(step_list(t, u, i2))["clear"]
    ok &= run.note("non-vacuity", "a halted governor can be cleared by the threshold of its site's keys",
                   satisfiable(rig + start + [halt1, i1["chip"] == c0, clear2, i2["chip"] == c0, Not(u.halted[c0])]), "sat")

    # 7. the assumptions a PASS rests on: the trusted base, and the exit register's open rows
    print()
    assumptions = [
        "A1 cryptography: signatures, tickets and receipts cannot be forged",
        "A2 the governor silicon, its fused floor and its heartbeat timer behave as specified",
        "A3 the endpoint's ticket check (edition, expiry, single use, fleet-ledger commit) behaves as specified",
        "A4 the halt loop halts every governor of a stopped site within L, and a lever stops a halted GPU within L "
        "(hw/loop/results.md: 317 us simulated worst case against L = 1 ms)",
        "A5 the attacker holds fewer governance keys at each site than the fused floor; the honest holders can meet the floor",
        "A6 at least one replica of each site's fleet ledger is honest (all replicas are required, so lying ones can only refuse)",
        "A7 every path by which an effect can leave the machine passes an endpoint (condition 1), except as listed below",
    ]
    register = ROOT / "docs" / "research" / "exit-register.md"
    open_rows = []
    if register.exists():
        for line in register.read_text().splitlines():
            m = re.match(r"\| (X\d+) \| (.+?) \|.*\| unaccounted \(NDA\) \|", line)
            if m:
                open_rows.append(f"{m.group(1)} {m.group(2)[:90]}")
    else:
        open_rows.append("the exit register is not in this checkout (docs/research/exit-register.md); see experiment P2")
    print("A PASS is 'proved, assuming':")
    for a in assumptions:
        print("  " + a)
    print("  open exit-register rows (condition 1 rests on these until a board document settles them):")
    for r in open_rows:
        print("    " + r)

    verdict = "PASS" if ok else "FAIL"
    print(f"\nEXPERIMENT A: {verdict} ({sum(r['pass'] for r in run.records)} of {len(run.records)} checks as expected)")
    if out:
        Path(out).write_text(json.dumps({"verdict": verdict, "checks": run.records, "assumptions": assumptions,
                                         "open_exit_rows": open_rows}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
