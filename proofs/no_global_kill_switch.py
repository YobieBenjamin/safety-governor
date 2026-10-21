#!/usr/bin/env python3
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

  K1  There is no switch in the deep network: a separator that stays out of the access nodes next
      to the ends does not exist in the instance built here (the core is too connected). The cheapest
      network-side separator lies entirely in that access layer, one hop from the ends, and is at
      least k vertices per end: it needs the same list of every instance or every effector that an
      end cut needs, and several times as many cuts.
  K2  Cutting the network takes bystanders with it: the access-layer cut removes most of the core and
      severs a share of ordinary user-to-service pairs that have nothing to do with AI; the end cuts
      sever none.
  K3  A network cut does not reach an instance wired straight to its effector (a local model driving
      a local actuator). Killing the network is too much and too little at once.
  K4  The effector ends form a separator of size one per effector, and the compute ends a separator
      of size one per instance; both leave every other flow intact. Those are the comparator and the
      governor. By Menger's theorem no separator is smaller than the number of disjoint paths, and
      an end with one controller has exactly one.
  K5  Only the irreversible effectors need to be in the separator; reversible ones can be left out
      and audited afterwards, and the separator shrinks to their controllers.

What this is not: a statement about the real Internet's exact connectivity (it has regional
chokepoints and it has been switched off in countries; it has never been switched off everywhere,
and doing so would be K2), nor a proof that every effector is governed (coverage is a deployment
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
        cap.setdefault(u, {}).setdefault(v, 0)
        cap.setdefault(v, {}).setdefault(u, 0)
        cap[u][v] += c

    for v in adj:
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


def main() -> int:
    ok = True

    def report(tag: str, passed: bool, text: str) -> None:
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
    report("K0", f == b, f"max-flow min cut ({f}) equals the brute-force min cut ({b}) on the tiny instance")

    n_i, n_e, core, k = 12, 10, 60, 6
    g = build(n_instances=n_i, n_effectors=n_e, core=core, k=k, n_users=20, n_services=20)
    S = {v for v in g if v.startswith("m")}           # every instance, the local one included
    T = {v for v in g if v.startswith("a")}           # every actuator
    computes = {v for v in g if v.startswith("g")}
    controllers = {v for v in g if v.startswith("e")}
    users = {v for v in g if v.startswith("u")}
    services = {v for v in g if v.startswith("v")}

    # K1: a middle-only switch
    net_S = S - {"m_local"}
    net_T = T - {"a_local"}
    ends = computes | controllers
    first_hop = {c for e in ends for c in g[e] if c.startswith("c")}
    deep_flow, _ = min_vertex_cut(g, net_S, net_T, protected=ends | users | services | first_hop)
    report("K1a", deep_flow >= INF, "no separator exists that stays out of the access nodes next to the ends: there is no switch in the deep network")
    mid_flow, mid_cut = min_vertex_cut(g, net_S, net_T, protected=ends | users | services)
    report("K1b", mid_cut <= first_hop and mid_flow >= k and mid_flow > max(n_i, n_e),
           f"the cheapest network-side separator has {mid_flow} vertices, all of them access nodes one hop from an end (k={k}; {n_i} instances, {n_e} effectors)")

    # K2: that cut takes bystanders with it; the end cuts do not
    pairs = [(u, v) for u in sorted(users) for v in sorted(services)]
    severed = sum(1 for u, v in pairs if separated(g, {u}, {v}, mid_cut))
    report("K2", len(mid_cut) / core >= 0.5 and severed > 0,
           f"that separator removes {len(mid_cut)} of {core} core nodes ({len(mid_cut) / core:.0%}) and severs {severed} of {len(pairs)} user-to-service pairs ({severed / len(pairs):.0%}) that had nothing to do with AI")

    # K3: the local pair does not care about the network
    k3 = not separated(g, {"m_local"}, {"a_local"}, {v for v in g if v.startswith("c")})
    report("K3", k3, "removing the entire core still leaves the local instance wired to its local actuator")

    # K4: the ends
    e_flow, e_cut = min_vertex_cut(g, S, T, protected=users | services | computes)
    g_flow, g_cut = min_vertex_cut(g, S, T, protected=users | services | controllers)
    report("K4a", e_flow == len(controllers) and e_cut == controllers and not separated(g, users, services, e_cut),
           f"cutting at the effector controllers separates every instance from every actuator with {e_flow} vertices, one per effector, and users still reach services")
    report("K4b", g_flow == len(computes) and g_cut == computes and not separated(g, users, services, g_cut),
           f"cutting at the compute separates them with {g_flow} vertices, one per instance, and users still reach services")

    # K5: only irreversible effectors need the gate
    irreversible = {f"a{j}" for j in range(n_e) if j % 2 == 0} | {"a_local"}
    r_flow, r_cut = min_vertex_cut(g, S, irreversible, protected=users | services | computes)
    report("K5", r_flow == len(irreversible) and r_cut == {f"e{a[1:]}" for a in irreversible},
           f"gating only the {len(irreversible)} irreversible effectors needs {r_flow} vertices, their own controllers; the reversible ones are audited instead")

    print()
    print("All checks hold." if ok else "A check failed.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
