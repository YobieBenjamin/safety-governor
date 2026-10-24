# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F25: min-cut Claim 2 overgeneralized the pairwise connectivity bound.

Audit finding F25. The old Claim 2 in docs/23 said a network separator "costs at least k vertices
for each source-target pair, in total more vertices than there are machines at either end." The
per-pair bound (Menger plus assumption 2, k disjoint paths per pair) does not imply that the whole
cut is large. Connect each of twelve sources to two shared hubs and each hub to all ten targets:
every source-target pair then has two internally vertex-disjoint paths, so pairwise k is two, yet
removing the two hubs separates every source from every target, a size-two separator that beats the
"more vertices than machines" bound and takes no bystanders with it. The executable K-checks only
measured a well-connected instance, not the universal implication the prose stated.

The fix mirrors the already-corrected Claim 3: Claim 2 is now conditioned on the aggregate-
connectivity assumption (the network carries min(|S|, |T|) disjoint paths between the two whole
sides, not merely k between each pair), and the proof constructs the two-hub graph (INVARIANT-TWO-HUB-NO-KILL) and a
single shared controller (INVARIANT-SHARED-CONTROLLER-NO-KILL) as counterexamples it checks directly.

This test is discriminating. On the pre-fix source it cannot import ``build_two_hub`` and the
corrected docs wording is absent, so it fails; on the fixed source it:

  * admits the two-hub graph as a counterexample to the OLD universal Claim 2, computing the cuts
    itself from the module's own max-flow routine (pairwise 2, aggregate 2, below the machine
    counts and below min(|S|, |T|));
  * confirms a single shared controller is a size-one separator;
  * checks the corrected Claim 2 states the aggregate-connectivity assumption and excludes those
    graphs, and that the corrected Claim 3 wording is preserved.

Run: ``python3 -m pytest -q tests/test_f25_mincut.py``.
"""
import importlib.util
import os
import pathlib

PROOFS = pathlib.Path(__file__).resolve().parents[1] / "proofs"
DOCS = pathlib.Path(__file__).resolve().parents[1] / "docs"
_PATH = pathlib.Path(os.environ.get("NO_GLOBAL_KILL_PATH", PROOFS / "no_global_kill_switch.py"))
_DOC = pathlib.Path(os.environ.get("DOC_23_PATH", DOCS / "23-there-is-no-kill-switch.md"))


def _load():
    spec = importlib.util.spec_from_file_location("no_global_kill_under_test", _PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NK = _load()


def test_two_hub_is_a_counterexample_to_the_old_universal_claim_2():
    """Every pair has two vertex-disjoint paths (pairwise k = 2), yet two shared hubs separate the
    whole of both sides. The old Claim 2 (cut larger than the machine count) is false here."""
    adj, S, T = NK.build_two_hub(n_sources=12, n_targets=10, n_hubs=2)
    pair_cut, _ = NK.min_vertex_cut(adj, {"m0"}, {"e0"}, protected=S | T)
    agg_cut, agg_set = NK.min_vertex_cut(adj, S, T, protected=S | T)
    assert pair_cut == 2                       # pairwise connectivity is k = 2
    assert agg_cut == 2 and agg_set == {"h0", "h1"}
    # the old claim said the aggregate cut is larger than the machine count; it is far smaller
    assert agg_cut < len(S) + len(T)
    assert agg_cut < min(len(S), len(T))
    # removing the two hubs really does separate every source from every target
    assert NK.separated(adj, S, T, {"h0", "h1"})


def test_single_shared_controller_is_a_size_one_separator():
    adj, S, T = NK.build_two_hub(n_sources=12, n_targets=10, n_hubs=1)
    pair_cut, _ = NK.min_vertex_cut(adj, {"m0"}, {"e0"}, protected=S | T)
    agg_cut, agg_set = NK.min_vertex_cut(adj, S, T, protected=S | T)
    assert pair_cut == 1
    assert agg_cut == 1 and agg_set == {"h0"}
    assert NK.separated(adj, S, T, {"h0"})


def test_corrected_claim_2_states_the_assumption_and_excludes_the_counterexamples():
    text = _DOC.read_text()
    claim2 = text.split("**Claim 2.")[1].split("**Claim 3.")[0]
    # the corrected Claim 2 is conditioned on aggregate connectivity, not the bare per-pair bound
    assert "aggregate-connectivity assumption" in claim2
    assert "min(|S|, |T|) disjoint paths between the two whole sides" in claim2
    assert "two shared hubs" in claim2
    assert "exclude" in claim2  # it excludes the counterexample graphs rather than overpromising
    # the old unqualified universal sentence is gone
    assert "costs at least k vertices for each source-target pair, in total more vertices than there are machines" not in text


def test_corrected_claim_3_wording_is_preserved():
    text = _DOC.read_text()
    claim3 = text.split("**Claim 3.")[1].split("## 4.")[0]
    # the already-corrected Claim 3 must not regress
    assert "stronger assumption" in claim3
    assert "min(|S|, |T|) disjoint paths between the sides" in claim3
    assert "INVARIANT-NO-CUT-BEATS-SMALLER-END" in claim3


def test_the_well_connected_instance_still_has_a_large_network_cut():
    """The corrected Claim 2 still HOLDS where its assumption holds: the well-connected 6-regular
    core gives a large network-side separator, as the script's INVARIANT-CHEAPEST-CUT-AT-ACCESS-LAYER measures. This guards against
    'fixing' Claim 2 by gutting it."""
    g = NK.build(n_instances=12, n_effectors=10, core=60, k=6, n_users=20, n_services=20)
    S = {v for v in g if v.startswith("m")} - {"m_local"}
    T = {v for v in g if v.startswith("a")} - {"a_local"}
    ends = {v for v in g if v.startswith(("g", "e"))}
    users = {v for v in g if v.startswith("u")}
    services = {v for v in g if v.startswith("v")}
    mid_flow, mid_cut = NK.min_vertex_cut(g, S, T, protected=ends | users | services)
    assert mid_flow >= 6 and mid_flow > (len(S) + len(T))   # more vertices than machines, under the assumption
