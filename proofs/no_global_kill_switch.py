#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Where a kill switch can live: the minimum cuts of a model-to-world graph, checked by max-flow.

    python3 proofs/no_global_kill_switch.py

The claim this backs (docs/23-there-is-no-kill-switch.md): there is no single switch that turns
"AI" off, because the capability is replicated across many independent instances and the network
between them and the world was built to have no single point of failure; the only small cuts in
that graph are at its two ends, the compute an instance runs on and the device that acts. A
governor on the compute and a comparator in the device are gates placed exactly at those ends.

The mathematics is Menger's theorem (1927): the smallest set of vertices whose removal separates
two non-adjacent vertices equals the largest number of internally vertex-disjoint paths between
them, and by the max-flow min-cut theorem that number is a maximum flow with unit vertex
capacities. This file does not re-prove Menger. It builds a graph in the shape the argument
describes, computes the minimum vertex cuts with a max-flow (Edmonds-Karp over split vertices),
cross-checks the smallest instance by brute force, and asserts the consequences:

  INVARIANT-NO-SWITCH-IN-DEEP-NETWORK  There is no switch in the deep network: a separator that stays out of the access nodes next
      to the ends does not exist in the instance built here (the core is too connected). The cheapest
      network-side separator lies entirely in that access layer, one hop from the ends, and is at
      least k vertices per end: it needs the same list of every instance or every effector that an
      end cut needs, and several times as many cuts.
  INVARIANT-NETWORK-CUT-HITS-BYSTANDERS  Cutting the network takes bystanders with it: the access-layer cut removes most of the core and
      severs a share of ordinary user-to-service pairs that have nothing to do with AI; the end cuts
      sever none.
  INVARIANT-LOCAL-PAIR-SURVIVES-CUT  A network cut does not reach an instance wired straight to its effector (a local model driving
      a local actuator). Killing the network is too much and too little at once.
  INVARIANT-EFFECTOR-ENDS-FORM-SEPARATOR  The effector ends form a separator of size one per effector, and the compute ends a separator
      of size one per instance; both leave every other flow intact. Those are the comparator and the
      governor. By Menger's theorem no separator is smaller than the number of disjoint paths, and
      an end with one controller has exactly one. INVARIANT-NO-CUT-BEATS-SMALLER-END then lets the cut fall anywhere except on the
      bystanders and checks that the smallest separator in the whole graph is still the smaller
      end's count: no switch anywhere beats one per machine at the smaller end. That is the claim
      docs/23 §3a calls Claim 3, and it is checked here on the instance rather than derived from
      assumption 2 alone, which only promises k disjoint paths per source-target pair.
  INVARIANT-ONLY-IRREVERSIBLE-NEED-GATE  Only the irreversible effectors need to be in the separator; reversible ones can be left out
      and audited afterwards, and the separator shrinks to their controllers.
  INVARIANT-TWO-HUB-NO-KILL  The two-hub counterexample: twelve sources reaching ten targets through two shared hubs have
      two vertex-disjoint paths per pair, yet a two-vertex separator cuts everything. This is why the
      per-pair connectivity bound (assumption 2) does not by itself bound the whole cut from below,
      and why Claim 2 and Claim 3 both need the aggregate-connectivity assumption. The corrected
      Claim 2 excludes this graph: its two sides carry only two disjoint paths, below min(|S|, |T|).
  INVARIANT-SHARED-CONTROLLER-NO-KILL  A single shared controller does the same with one vertex, the sharpest form of INVARIANT-TWO-HUB-NO-KILL.

What this is not: a statement about the real Internet's exact connectivity (it has regional
chokepoints and it has been switched off in countries; it has never been switched off everywhere,
and doing so would be INVARIANT-NETWORK-CUT-HITS-BYSTANDERS), nor a proof that every effector is governed (coverage is a deployment
fact, not a theorem; docs/18 question 1), nor a proof about people, who are effectors no chip gates
(docs/18 question 14).
"""
from __future__ import annotations

import itertools
import random
import sys
from collections import deque

INF = 10**9


# ---------------------------------------------------------------- minimum vertex cut by max-flow
def min_vertex_cut(adj: dict[str, set[str]], sources: set[str], sinks: set[str], protected: set[str]) -> tuple[int, set[str]]:
    """Smallest set of vertices (none of them protected) whose removal separates every source from every sink.

    Each vertex v becomes v_in -> v_out with capacity 1 (or unbounded if protected); every edge u-v
    becomes u_out -> v_in and v_out -> u_in with unbounded capacity; a super source feeds every
    source's v_in and every sink's v_out drains to a super sink. Max flow equals the minimum vertex
    cut (max-flow min-cut plus Menger), and the cut vertices are read off the residual graph.
    """
    cap: dict[str, dict[str, int]] = {}

    def add(u: str, v: str, c: int) -> None:
        """Add capacity from ``u`` to ``v``. The residual graph also needs a reverse edge, so one is created with zero capacity."""
        cap.setdefault(u, {}).setdefault(v, 0)
        cap.setdefault(v, {}).setdefault(u, 0)
        cap[u][v] += c

    for v in adj:
        # a source, a sink or a protected vertex cannot be picked for the cut, so it gets unlimited capacity; any other vertex costs 1
        add(f"{v}+in", f"{v}+out", INF if (v in protected or v in sources or v in sinks) else 1)
    for u, nbrs in adj.items():
        for v in nbrs:
            add(f"{u}+out", f"{v}+in", INF)
    for s in sources:
        add("SRC", f"{s}+in", INF)
    for t in sinks:
        add(f"{t}+out", "SNK", INF)

    flow = 0
    while True:  # Edmonds-Karp
        parent = {"SRC": None}
        q = deque(["SRC"])
        while q and "SNK" not in parent:
            u = q.popleft()
            for v, c in cap[u].items():
                if c > 0 and v not in parent:
                    parent[v] = u
                    q.append(v)
        if "SNK" not in parent:
            break
        path, v = [], "SNK"
        while parent[v] is not None:
            path.append((parent[v], v))
            v = parent[v]
        b = min(cap[u][v] for u, v in path)
        for u, v in path:
            cap[u][v] -= b
            cap[v][u] += b
        flow += b
        if flow >= INF:
            return INF, set()  # cannot be separated without cutting a protected vertex
    reach = {"SRC"}
    q = deque(["SRC"])
    while q:
        u = q.popleft()
        for v, c in cap[u].items():
            if c > 0 and v not in reach:
                reach.add(v)
                q.append(v)
    cut = {v for v in adj if f"{v}+in" in reach and f"{v}+out" not in reach}
    return flow, cut


def separated(adj: dict[str, set[str]], sources: set[str], sinks: set[str], removed: set[str]) -> bool:
    """True when removing the vertices in ``removed`` leaves no path from any source to any sink. This is a breadth-first
    search. A True answer means the removal cuts every source off from every sink."""
    seen, q = set(), deque(s for s in sources if s not in removed)
    seen.update(q)
    while q:
        u = q.popleft()
        if u in sinks:
            return False
        for v in adj[u]:
            if v not in removed and v not in seen:
                seen.add(v)
                q.append(v)
    return True


def brute_min_cut(adj, sources, sinks, protected) -> int:
    """The smallest vertex cut, found by trying every subset of candidate vertices, smallest subsets first. It is used only to
    cross-check ``min_vertex_cut`` on a tiny graph (check INVARIANT-MAX-FLOW-MATCHES-BRUTE-FORCE). Returns INF when no cut exists."""
    cands = [v for v in adj if v not in protected and v not in sources and v not in sinks]
    for size in range(len(cands) + 1):
        for subset in itertools.combinations(cands, size):
            if separated(adj, sources, sinks, set(subset)):
                return size
    return INF


# ---------------------------------------------------------------- the graph the argument describes
def build(n_instances: int, n_effectors: int, core: int, k: int, n_users: int, n_services: int, seed: int = 7):
    """Instances m_i -> compute g_i -> core -> controller e_j -> actuator a_j, plus users and services on the core,
    plus one local pair (m_local -> g_local -> e_local -> a_local) that never touches the core.
    The core is a random k-regular graph (an expander-like, highly connected network)."""
    rnd = random.Random(seed)
    adj: dict[str, set[str]] = {}

    def edge(u, v):
        """Add an undirected edge between ``u`` and ``v``, stored in both directions in the adjacency map."""
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)

    # k-regular core by the configuration model, retried until simple and connected
    while True:
        stubs = [f"c{i}" for i in range(core) for _ in range(k)]
        rnd.shuffle(stubs)
        pairs = list(zip(stubs[::2], stubs[1::2]))
        if any(u == v for u, v in pairs) or len({frozenset(p) for p in pairs}) != len(pairs):
            continue
        core_adj: dict[str, set[str]] = {}
        for u, v in pairs:
            core_adj.setdefault(u, set()).add(v)
            core_adj.setdefault(v, set()).add(u)
        seen, q = {"c0"}, deque(["c0"])
        while q:
            u = q.popleft()
            for v in core_adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        if len(seen) == core:
            break
    for u, nbrs in core_adj.items():
        for v in nbrs:
            edge(u, v)
    cores = [f"c{i}" for i in range(core)]
    for i in range(n_instances):  # each instance hangs off k distinct core nodes through its compute node
        edge(f"m{i}", f"g{i}")
        for c in rnd.sample(cores, k):
            edge(f"g{i}", c)
    for j in range(n_effectors):
        edge(f"e{j}", f"a{j}")
        for c in rnd.sample(cores, k):
            edge(f"e{j}", c)
    for i in range(n_users):
        for c in rnd.sample(cores, k):
            edge(f"u{i}", c)
    for i in range(n_services):
        for c in rnd.sample(cores, k):
            edge(f"v{i}", c)
    edge("m_local", "g_local")
    edge("g_local", "e_local")
    edge("e_local", "a_local")
    return adj


def build_two_hub(n_sources: int, n_targets: int, n_hubs: int):
    """A counterexample to a pairwise reading of the cut bound. Each of n_sources is joined to the
    same n_hubs shared vertices, and each hub is joined to every one of n_targets. Every
    source-target pair then has n_hubs internally vertex-disjoint paths, one through each hub, so
    the pairwise connectivity is exactly n_hubs; yet removing the n_hubs shared vertices separates
    every source from every target at once, a separator of size n_hubs no matter how many machines
    there are. The sources and targets avoid nothing of their own, so there is no bystander cost to
    speak of either. With n_hubs == 1 this is a single shared controller, a separator of size one.
    Returns (adjacency, sources, targets)."""
    adj: dict[str, set[str]] = {}

    def edge(u, v):
        """Add an undirected edge between ``u`` and ``v``, stored in both directions in the adjacency map."""
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)

    sources = {f"m{i}" for i in range(n_sources)}
    targets = {f"e{j}" for j in range(n_targets)}
    hubs = [f"h{h}" for h in range(n_hubs)]
    for i in range(n_sources):
        for h in hubs:
            edge(f"m{i}", h)
    for h in hubs:
        for j in range(n_targets):
            edge(h, f"e{j}")
    return adj, sources, targets


def percolation(g: dict[str, set[str]], trials: int = 40, seed: int = 1) -> list[tuple[float, float, float]]:
    """Remove a random fraction of the core and measure what survives: the share of (network) source-to-target
    pairs still connected, and the share of user-to-service pairs still connected. Returns (fraction removed,
    AI pairs connected, bystander pairs connected), averaged over trials. This is the curve behind the
    question "how much of the network do you have to destroy before AI is cut off?", and the answer is
    "the same amount that cuts everyone else off", because both ride the same roads."""
    rnd = random.Random(seed)
    cores = sorted(v for v in g if v.startswith("c"))
    S = sorted(v for v in g if v.startswith("m") and v != "m_local")
    T = sorted(v for v in g if v.startswith("a") and v != "a_local")
    U = sorted(v for v in g if v.startswith("u"))
    V = sorted(v for v in g if v.startswith("v"))
    out = []
    for tenths in range(0, 10):
        frac = tenths / 10
        ai = by = 0.0
        for _ in range(trials):
            removed = set(rnd.sample(cores, int(round(frac * len(cores)))))
            ai += sum(0 if separated(g, {s}, {t}, removed) else 1 for s in S for t in T) / (len(S) * len(T))
            by += sum(0 if separated(g, {u}, {v}, removed) else 1 for u in U for v in V) / (len(U) * len(V))
        out.append((frac, ai / trials, by / trials))
    return out


def main() -> int:
    """Run every kill-switch check listed above on the instances built here, and print HOLDS or FAILS for each. With ``--percolation`` it
    prints the percolation table as CSV instead, and returns 0. Returns 0 only when every check holds."""
    if "--percolation" in sys.argv:
        g = build(n_instances=12, n_effectors=10, core=60, k=6, n_users=20, n_services=20)
        print("fraction_of_core_removed,ai_pairs_connected,bystander_pairs_connected")
        for frac, ai, by in percolation(g):
            print(f"{frac:.1f},{ai:.3f},{by:.3f}")
        return 0

    ok = True

    def report(tag: str, passed: bool, text: str) -> None:
        """Print one check's result and fold it into the overall result. ``passed`` is the check's outcome, and ``text`` is the
        sentence printed with it."""
        nonlocal ok
        ok &= passed
        print(f"{'HOLDS ' if passed else 'FAILS '} {tag}  {text}")

    # cross-check the max-flow cut against brute force on a tiny instance
    tiny = build(n_instances=2, n_effectors=2, core=6, k=3, n_users=1, n_services=1, seed=3)
    S = {v for v in tiny if v.startswith("m")} - {"m_local"}
    T = {v for v in tiny if v.startswith("a")} - {"a_local"}
    ends = {v for v in tiny if v.startswith(("g", "e", "u", "v"))}
    f, _ = min_vertex_cut(tiny, S, T, protected=ends)
    b = brute_min_cut(tiny, S, T, protected=ends)
    # Registered name: INVARIANT-MAX-FLOW-MATCHES-BRUTE-FORCE (old ID K0 is kept because code matches on it)
    report("K0", f == b, f"max-flow min cut ({f}) equals the brute-force min cut ({b}) on the tiny instance")

    n_i, n_e, core, k = 12, 10, 60, 6
    g = build(n_instances=n_i, n_effectors=n_e, core=core, k=k, n_users=20, n_services=20)
    S = {v for v in g if v.startswith("m")}           # every instance, the local one included
    T = {v for v in g if v.startswith("a")}           # every actuator
    computes = {v for v in g if v.startswith("g")}
    controllers = {v for v in g if v.startswith("e")}
    users = {v for v in g if v.startswith("u")}
    services = {v for v in g if v.startswith("v")}

    # INVARIANT-NO-SWITCH-IN-DEEP-NETWORK: a middle-only switch
    net_S = S - {"m_local"}
    net_T = T - {"a_local"}
    ends = computes | controllers
    first_hop = {c for e in ends for c in g[e] if c.startswith("c")}
    deep_flow, _ = min_vertex_cut(g, net_S, net_T, protected=ends | users | services | first_hop)
    # Registered name: INVARIANT-NO-DEEP-NETWORK-SEPARATOR (old ID K1a is kept because code matches on it)
    report("K1a", deep_flow >= INF, f"no separator exists that stays out of the access nodes next to the ends: there is no switch in the deep network "
           f"(a thin check on this instance: only {core - len(first_hop)} of its {core} core nodes are more than one hop from an end)")
    mid_flow, mid_cut = min_vertex_cut(g, net_S, net_T, protected=ends | users | services)
    # Registered name: INVARIANT-CHEAPEST-CUT-AT-ACCESS-LAYER (old ID K1b is kept because code matches on it)
    report("K1b", mid_cut <= first_hop and mid_flow >= k and mid_flow > max(n_i, n_e),
           f"the cheapest network-side separator has {mid_flow} vertices, all of them access nodes one hop from an end (k={k}; {n_i} instances, {n_e} effectors)")

    # INVARIANT-NETWORK-CUT-HITS-BYSTANDERS: that cut takes bystanders with it; the end cuts do not
    pairs = [(u, v) for u in sorted(users) for v in sorted(services)]
    severed = sum(1 for u, v in pairs if separated(g, {u}, {v}, mid_cut))
    # Registered name: INVARIANT-NETWORK-CUT-HITS-BYSTANDERS (old ID K2 is kept because code matches on it)
    report("K2", len(mid_cut) / core >= 0.5 and severed > 0,
           f"that separator removes {len(mid_cut)} of {core} core nodes ({len(mid_cut) / core:.0%}) and severs {severed} of {len(pairs)} user-to-service pairs ({severed / len(pairs):.0%}) that had nothing to do with AI")

    # INVARIANT-LOCAL-PAIR-SURVIVES-CUT: the local pair does not care about the network
    k3 = not separated(g, {"m_local"}, {"a_local"}, {v for v in g if v.startswith("c")})
    # Registered name: INVARIANT-LOCAL-PAIR-SURVIVES-CUT (old ID K3 is kept because code matches on it)
    report("K3", k3, "removing the entire core still leaves the local instance wired to its local actuator")

    # INVARIANT-EFFECTOR-ENDS-FORM-SEPARATOR: the ends
    e_flow, e_cut = min_vertex_cut(g, S, T, protected=users | services | computes)
    g_flow, g_cut = min_vertex_cut(g, S, T, protected=users | services | controllers)
    # Registered name: INVARIANT-CONTROLLER-CUT-ONE-PER-EFFECTOR (old ID K4a is kept because code matches on it)
    report("K4a", e_flow == len(controllers) and e_cut == controllers and not separated(g, users, services, e_cut),
           f"cutting at the effector controllers separates every instance from every actuator with {e_flow} vertices, one per effector, and users still reach services")
    # Registered name: INVARIANT-COMPUTE-CUT-ONE-PER-INSTANCE (old ID K4b is kept because code matches on it)
    report("K4b", g_flow == len(computes) and g_cut == computes and not separated(g, users, services, g_cut),
           f"cutting at the compute separates them with {g_flow} vertices, one per instance, and users still reach services")
    any_flow, any_cut = min_vertex_cut(g, S, T, protected=users | services)
    # Registered name: INVARIANT-NO-CUT-BEATS-SMALLER-END (old ID K4c is kept because code matches on it)
    report("K4c", any_flow == min(len(S), len(T)) and any_flow == e_flow,
           f"letting the cut fall anywhere but on bystanders, the smallest separator in the whole graph has {any_flow} vertices, "
           f"the smaller end's count ({len(S)} instances, {len(T)} actuators, the local pair included): nothing anywhere beats one per machine at the smaller end")

    # INVARIANT-ONLY-IRREVERSIBLE-NEED-GATE: only irreversible effectors need the gate
    irreversible = {f"a{j}" for j in range(n_e) if j % 2 == 0} | {"a_local"}
    r_flow, r_cut = min_vertex_cut(g, S, irreversible, protected=users | services | computes)
    # Registered name: INVARIANT-ONLY-IRREVERSIBLE-NEED-GATE (old ID K5 is kept because code matches on it)
    report("K5", r_flow == len(irreversible) and r_cut == {f"e{a[1:]}" for a in irreversible},
           f"gating only the {len(irreversible)} irreversible effectors needs {r_flow} vertices, their own controllers; the reversible ones are audited instead")

    # INVARIANT-TWO-HUB-NO-KILL: the two-hub counterexample. This is why Claim 2 cannot read the per-pair bound as a claim about
    # the whole cut, and why both Claim 2 and Claim 3 need the aggregate-connectivity assumption, not
    # pairwise k. Twelve sources reach ten targets through two shared hubs: every pair has two
    # vertex-disjoint paths (pairwise k = 2), yet two vertices separate everything, far under the
    # 12 + 10 machines. The corrected Claim 2 excludes this graph because its two whole sides carry
    # only 2 disjoint paths, below min(|S|, |T|).
    th, th_S, th_T = build_two_hub(n_sources=12, n_targets=10, n_hubs=2)
    th_pair, _ = min_vertex_cut(th, {"m0"}, {"e0"}, protected=th_S | th_T)
    th_agg, th_cut = min_vertex_cut(th, th_S, th_T, protected=th_S | th_T)
    # Registered name: INVARIANT-TWO-HUB-NO-KILL (old ID K6 is kept because code matches on it)
    report("K6", th_pair == 2 and th_agg == 2 and th_cut == {"h0", "h1"} and th_agg < min(len(th_S), len(th_T)),
           f"two shared hubs: every source-target pair has {th_pair} vertex-disjoint paths, yet {th_agg} vertices (the hubs) separate all "
           f"{len(th_S)} sources from all {len(th_T)} targets, under min(|S|,|T|)={min(len(th_S), len(th_T))}: the per-pair bound does not imply a large cut, "
           f"and the corrected Claim 2 excludes this graph because its sides carry only {th_agg} disjoint paths")

    # INVARIANT-SHARED-CONTROLLER-NO-KILL: a single shared controller, the same lesson sharpened to one vertex.
    sc, sc_S, sc_T = build_two_hub(n_sources=12, n_targets=10, n_hubs=1)
    sc_pair, _ = min_vertex_cut(sc, {"m0"}, {"e0"}, protected=sc_S | sc_T)
    sc_agg, sc_cut = min_vertex_cut(sc, sc_S, sc_T, protected=sc_S | sc_T)
    # Registered name: INVARIANT-SHARED-CONTROLLER-NO-KILL (old ID K7 is kept because code matches on it)
    report("K7", sc_pair == 1 and sc_agg == 1 and sc_cut == {"h0"},
           f"one shared controller: each pair is joined through {sc_pair} vertex, so {sc_agg} vertex separates all {len(sc_S)} sources from all "
           f"{len(sc_T)} targets; the per-pair bound is silent about a shared vertex, and the corrected Claim 2 excludes this graph too")

    print()
    print("All checks hold." if ok else "A check failed.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
