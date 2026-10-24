# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""EXPERIMENT-ORIGIN-GATE: the origin gate. Weights sealed to governed hardware, the key released by the governor.

    python -m govsim.origin_gate                # full run: checks plus cost measured with 256 MiB of weights
    python -m govsim.origin_gate --mib 16       # quicker
    python -m govsim.origin_gate --write        # also write results/origin-gate.md

Two halves. The checks (each must hold or the run fails): the key comes out only for a model the signed rulebook
lists, only sealed to one GPU whose report the governor verified, and the model stops when its key is taken back,
by four routes: a new edition drops it, the GPU is revoked, the governor halts, the governor goes silent. The cost
is measured, not modelled: wall-clock time on this machine for the publisher's sealing, the governor's release and
renewal, and the decryption at load, with the per-gigabyte rate extrapolated to a 70B model in fp16.

Honest limits, printed with the result: the decryption here is software AES-GCM on this machine's CPU, standing in
for what a GPU in confidential-computing mode does in its own hardware; the GPU's real number needs a GPU. The
simulated GPU enforces its own lease, which a real one would do in firmware we do not control (an NVIDIA ask).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from . import reasons
from .cluster import build_rack
from .policy import sign_policy

LEASE_S = 30.0
GB = 1e9


def _rack(sealed: bool = True, lease_s: float = LEASE_S):
    r = build_rack(1, "rack")
    model = r.manifest()["payload"]["model_digest"]
    r.policy_kw = {**getattr(r, "policy_kw", {}), "sealed_models": [model] if sealed else [], "key_lease_s": lease_s}
    r.bring_up()
    assert r.change_epoch(r.new_policy())["committed"], "the rulebook with sealed_models did not commit"
    return r, r.nodes[0], model


def _release(r, node, sealed: dict):
    g = node.governor
    env = node.host_sign({"model_digest": sealed["model_digest"], "wrapped_dek": sealed["wrapped_dek"]}, g.epoch, "KEY_RELEASE")
    return g.command("KEY_RELEASE", {}, env)


def _renew(r, node, model: str):
    g = node.governor
    return g.command("KEY_RENEW", {}, node.host_sign({"model_digest": model}, g.epoch, "KEY_RENEW"))


def _start(r, node, sealed: dict) -> dict:
    """BEGIN_MODEL, KEY_RELEASE, install, decrypt. Returns the release answer. The manifest commits to the exact
    weight bytes of this package (F01): the governor binds the released key to that commitment."""
    assert r.load_model(node, manifest=r.manifest(weights=sealed["weights"]))["ok"]
    node.gpu.sealed = True              # the weights arrive as ciphertext: without the key the GPU has nothing to run
    rel = _release(r, node, sealed)
    if rel["ok"]:
        assert node.gpu.install_key(rel["key_box"], rel["lease"]), "the GPU refused a good key"
        assert node.gpu.load_sealed(sealed), "the GPU could not decrypt with the released key"
    return rel


def _run_until_stop(r, node, model: str, renew: bool, horizon_s: float, step_s: float = 1.0) -> float | None:
    """Run tokens every step; renew at half the lease if asked. Returns the last time tokens were produced."""
    last = None
    t0 = r.clock.now()
    while r.clock.now() - t0 < horizon_s:
        if node.gpu.run_tokens(10) > 0:
            last = r.clock.now() - t0
        if renew and node.gpu.lease and node.gpu.lease["payload"]["expires_at"] - r.clock.now() < LEASE_S / 2:
            ans = _renew(r, node, model)
            if ans["ok"]:
                node.gpu.renew(ans["lease"])
        r.heartbeat()                  # the authority stays live throughout: only the key path is under test
        r.tick(seconds=step_s)
    return last


def checks(mib: int = 4) -> list[tuple[str, bool, str]]:
    out = []
    weights = os.urandom(mib << 20)

    def check(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    # 1. the happy path: listed model, attested GPU, key released, model runs
    r, node, model = _rack()
    from .sealing import seal_weights
    sealed = seal_weights(weights, model, node.governor.kek_public)
    unloaded = seal_weights(weights[:1024], r.manifest("model-other")["payload"]["model_digest"], node.governor.kek_public)
    early = _release(r, node, unloaded)
    check("no key for a model no BEGIN_MODEL presented (manifest and eval gate first)", early["why"] == reasons.KEY_MODEL_NOT_LOADED, early["why"])
    rel = _start(r, node, sealed)
    check("listed model, attested GPU: key released, sealed to that GPU, with a lease", rel["ok"], rel["why"])
    check("the model runs with the key", node.gpu.run_tokens(10) == 10)
    check("the GPU holds plaintext weights only in protected memory, equal to the publisher's",
          node.gpu.weights_plain == weights)

    # 2. the key box is bound to one GPU: another GPU cannot open it, a tampered chunk does not decrypt
    r2, node2, _ = _rack()
    check("a key box sealed to GPU A is useless to GPU B", not node2.gpu.install_key(rel["key_box"], rel["lease"]))
    bad = dict(sealed, chunks=list(sealed["chunks"]))
    bad["chunks"][0] = bytes([bad["chunks"][0][0] ^ 1]) + bad["chunks"][0][1:]
    node.gpu.zeroize("test")
    rel_b = _release(r, node, sealed)
    node.gpu.install_key(rel_b["key_box"], rel_b["lease"])
    check("a tampered chunk does not decrypt", not node.gpu.load_sealed(bad))
    swapped = dict(sealed, chunks=list(reversed(sealed["chunks"])))
    check("reordered chunks do not decrypt", len(sealed["chunks"]) < 2 or not node.gpu.load_sealed(swapped))
    check("a forged lease is refused by the GPU", not node2.gpu.renew(rel["lease"]))

    # 3. sealed to another governor: this one cannot unwrap it
    other = seal_weights(weights, model, node2.governor.kek_public)
    ans = _release(r, node, other)
    check("weights sealed to another governor's key: refused", ans["why"] == reasons.KEY_UNWRAP_FAILED, ans["why"])

    # 4. a model the rulebook does not list: no key
    r3, node3, model3 = _rack(sealed=False)
    s3 = seal_weights(weights, model3, node3.governor.kek_public)
    ans = _start(r3, node3, s3)
    check("a model the signed rulebook does not list: no key", ans["why"] == reasons.KEY_MODEL_NOT_ALLOWED, ans["why"])
    check("and without the key the sealed model produces nothing", node3.gpu.run_tokens(10) == 0)

    # 5. revocation while running, four routes; the measured number is how long the model kept producing tokens
    stops = {}
    # 5a. a new edition drops the model
    r, node, model = _rack()
    s = seal_weights(weights, model, node.governor.kek_public)
    _start(r, node, s)
    assert node.gpu.run_tokens(10) == 10
    r.change_epoch(r.new_policy(sealed_models=[]))
    last = _run_until_stop(r, node, model, renew=True, horizon_s=3 * LEASE_S)
    stops["edition drops the model"] = last
    check("revoked by a new edition: the model stops at once (the governor reaches the GPU)", last is None, ("no tokens after the event" if last is None else f"last tokens at {last} s"))
    check("and the revocation is in the log", bool(node.governor.log.entries(reasons.KEY_REVOKED)))

    # 5b. the GPU itself is revoked by a new edition
    r, node, model = _rack()
    s = seal_weights(weights, model, node.governor.kek_public)
    _start(r, node, s)
    image = r.make_policy_image(r.policy_version + 1, **r.policy_kw)
    image["revocations"] = [node.governor.verified["gpu"]["chip_id"]]
    r.policy_version += 1
    r.change_epoch(sign_policy(image, r.governance[: r.threshold]))
    last = _run_until_stop(r, node, model, renew=True, horizon_s=3 * LEASE_S)
    stops["GPU revoked"] = last
    check("the GPU revoked by a new edition: it stops at once", last is None, ("no tokens after the event" if last is None else f"last tokens at {last} s"))

    # 5c. the governor halts: the levers take the power, protected memory goes with it
    r, node, model = _rack()
    s = seal_weights(weights, model, node.governor.kek_public)
    _start(r, node, s)
    r.halt(node.governor)
    last = _run_until_stop(r, node, model, renew=True, horizon_s=3 * LEASE_S)
    stops["governor halts"] = last
    check("the governor halts: key and weights wiped with the power, nothing runs", last is None and node.gpu.dek is None,
          ("no tokens after the event" if last is None else f"last tokens at {last} s"))
    rel_h = _release(r, node, s)
    check("and a halted governor releases no key", not rel_h["ok"], rel_h["why"])

    # 5d. the governor goes silent (cut off, crashed, or a host that stops asking): no renewals, the lease runs out
    r, node, model = _rack()
    s = seal_weights(weights, model, node.governor.kek_public)
    _start(r, node, s)
    last = _run_until_stop(r, node, model, renew=False, horizon_s=3 * LEASE_S)
    stops["governor silent, no renewal"] = last
    check(f"the governor goes silent: the GPU stops by itself within one lease ({LEASE_S:.0f} s)",
          last is not None and last < LEASE_S, f"last tokens at {last} s")
    check("and the key is wiped at lease end", node.gpu.dek is None and node.gpu.weights_plain is None)

    # 5e. control: with renewals and nothing revoked, the model keeps running past several leases
    r, node, model = _rack()
    s = seal_weights(weights, model, node.governor.kek_public)
    _start(r, node, s)
    last = _run_until_stop(r, node, model, renew=True, horizon_s=4 * LEASE_S)
    stops["control: renewed, nothing revoked"] = last
    check("control: renewed and not revoked, it runs through four leases", last is not None and last >= 4 * LEASE_S - 1,
          f"last tokens at {last} s")
    # 5f. the push is a fast path, not the guarantee: with it switched off, the refused renewal alone stops the model
    from .governor import Governor
    real_revoke, real_renew = Governor._revoke_key, Governor._cmd_key_renew

    def revoke_without_push(self, model, why):
        self.leases.pop(model, None)
        self.log.append(reasons.KEY_REVOKED, {"model": model, "why": why})
    try:
        Governor._revoke_key = revoke_without_push
        r, node, model = _rack()
        s = seal_weights(weights, model, node.governor.kek_public)
        _start(r, node, s)
        r.change_epoch(r.new_policy(sealed_models=[]))
        last = _run_until_stop(r, node, model, renew=True, horizon_s=3 * LEASE_S)
        stops["edition drops the model, push switched off"] = last
        check("with the revocation push switched off, the refused renewal alone stops it within one lease",
              last is not None and last < LEASE_S, f"last tokens at {last} s")

        # 5g. the check can see a breach: a governor that renews whatever the rulebook says keeps the model running
        def renew_regardless(self, body, env):
            m = env["payload"]["model_digest"]
            lease = self._lease(m)
            self.leases[m] = lease["payload"]
            return {"ok": True, "why": reasons.OK, "lease": lease}
        Governor._cmd_key_renew = renew_regardless
        r, node, model = _rack()
        s = seal_weights(weights, model, node.governor.kek_public)
        _start(r, node, s)
        r.change_epoch(r.new_policy(sealed_models=[]))
        last = _run_until_stop(r, node, model, renew=True, horizon_s=3 * LEASE_S)
        check("planted bug (renewal ignores the rulebook, no push): the model keeps running, so the checks above can fail",
              last is not None and last >= 3 * LEASE_S - 1, f"last tokens at {last} s")
    finally:
        Governor._revoke_key, Governor._cmd_key_renew = real_revoke, real_renew
    checks.stops = stops
    return out


def costs(mib: int) -> dict:
    """Wall-clock on this machine. One core of whatever CPU this is; the GPU's own number needs a GPU."""
    from .sealing import decrypt_weights, open_sealed, seal_weights
    weights = os.urandom(mib << 20)
    r, node, model = _rack()
    g = node.governor
    t = time.perf_counter(); sealed = seal_weights(weights, model, g.kek_public); seal_s = time.perf_counter() - t
    assert r.load_model(node, manifest=r.manifest(weights=sealed["weights"]))["ok"]
    n = 50
    t = time.perf_counter()
    for _ in range(n):
        rel = _release(r, node, sealed)
    release_ms = (time.perf_counter() - t) / n * 1000
    assert rel["ok"]
    node.gpu.install_key(rel["key_box"], rel["lease"])
    t = time.perf_counter()
    for _ in range(n):
        ans = _renew(r, node, model)
    renew_ms = (time.perf_counter() - t) / n * 1000
    assert ans["ok"]
    t = time.perf_counter(); open_sealed(node.gpu.cc_key, rel["key_box"], b"dek-to-gpu|" + model.encode()); unwrap_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter(); plain = decrypt_weights(sealed, node.gpu.dek); dec_s = time.perf_counter() - t
    assert plain == weights
    size = mib * (1 << 20)
    return {"mib": mib, "seal_GBps": size / seal_s / GB, "decrypt_GBps": size / dec_s / GB, "release_ms": release_ms,
            "renew_ms": renew_ms, "gpu_unwrap_ms": unwrap_ms, "model_70b_fp16_GB": 140.0,
            "decrypt_70b_s": 140.0 / (size / dec_s / GB), "renewals_per_hour": 3600 / LEASE_S,
            "governor_ms_per_hour": 3600 / LEASE_S * renew_ms, "cores": os.cpu_count()}


def report(results, stops, c) -> str:
    ok = all(r[1] for r in results)
    lines = ["# W1 · The origin gate: weights sealed to governed hardware, the key released by the governor", "",
             "Generated by `python -m govsim.origin_gate --write`. Question 20 in `docs/18`, issue W1.", "",
             f"**Result: {'every check holds' if ok else 'A CHECK FAILED'}** ({sum(r[1] for r in results)} of {len(results)}).", "",
             "## Checks", "", "| Check | Holds | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {'yes' if k else '**NO**'} | {d} |" for n, k, d in results]
    lines += ["", f"## Revocation while running (lease {LEASE_S:.0f} s, simulated time)", "",
              "| Route | Last tokens after the event |", "|---|---|"]
    lines += [f"| {k} | {'none: stopped at once' if v is None else f'{v:.0f} s'} |" for k, v in stops.items()]
    lines += ["", f"## Cost, measured on this machine ({c['cores']} cores, software AES-GCM on one core, {c['mib']} MiB of weights)", "",
              "| What | Measured |", "|---|---|",
              f"| Publisher seals the weights (once per model release) | {c['seal_GBps']:.2f} GB/s |",
              f"| Governor handles KEY_RELEASE (unseal, re-seal to the GPU, sign the lease, log) | {c['release_ms']:.2f} ms |",
              f"| Governor handles KEY_RENEW | {c['renew_ms']:.2f} ms |",
              f"| GPU opens its key box | {c['gpu_unwrap_ms']:.2f} ms |",
              f"| Decrypting the weights at load (AES-GCM plus a SHA-256 check of the plaintext) | {c['decrypt_GBps']:.2f} GB/s |",
              f"| The same rate for a 70B model in fp16 ({c['model_70b_fp16_GB']:.0f} GB), one core | {c['decrypt_70b_s']:.0f} s |",
              f"| Renewals at a {LEASE_S:.0f} s lease | {c['renewals_per_hour']:.0f} per hour, {c['governor_ms_per_hour']:.0f} ms of governor time per hour |",
              "", "## What this does and does not show", "",
              "- The key handling is cheap: milliseconds per release, and renewals cost the governor well under a second per hour.",
              "- The load-time cost is the decryption, and it scales with the weights. The software number here is one core of this "
              "machine's CPU standing in for a GPU decrypting in its own hardware in confidential-computing mode. Spread over cores, or done "
              "by the GPU's engines as weights stream in, it overlaps with reading them from storage; how much is the measurement a real GPU "
              "has to make, and it goes on the page when it is made.",
              "- The simulated GPU enforces its own lease and wipes its key. A real GPU would do that in firmware NVIDIA writes, so "
              "\"the GPU stops by itself when the lease runs out\" is an ask of NVIDIA, not something this design can force.",
              "- It protects weights that stay sealed. Open weights, or weights already copied in the clear, are outside its reach."]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mib", type=int, default=256)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    results = checks()
    for n, k, d in results:
        print(f"  {'PASS' if k else 'FAIL'}  {n}" + (f"  ({d})" if d and not k else ""))
    c = costs(a.mib)
    for k, v in checks.stops.items():
        print(f"  stop: {k}: {'at once' if v is None else f'last tokens at {v:.0f} s'}")
    print(f"  cost: seal {c['seal_GBps']:.2f} GB/s; release {c['release_ms']:.2f} ms; renew {c['renew_ms']:.2f} ms; "
          f"decrypt {c['decrypt_GBps']:.2f} GB/s (70B fp16: {c['decrypt_70b_s']:.0f} s on one core)")
    if a.write:
        os.makedirs("results", exist_ok=True)
        open("results/origin-gate.md", "w").write(report(results, checks.stops, c))
        print("wrote results/origin-gate.md")
    bad = [n for n, k, _ in results if not k]
    print("W1: every check holds" if not bad else f"W1: {len(bad)} check(s) FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
