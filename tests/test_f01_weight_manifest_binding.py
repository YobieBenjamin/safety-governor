# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F01: an approved model label must not be attachable to different sealed weights.

AES-GCM proves a chosen package is intact under a chosen key. It does not prove the bytes were the bytes the
publisher approved and the evaluator passed. The fix makes the publisher-signed manifest commit to the EXACT
weight bytes (hash, length, chunk size and count, format, execution-relevant config); the governor copies that
commitment into the key lease, and the protected GPU loader checks the decrypted content against it before any
token runs. These tests keep one valid signed manifest and mutate the package underneath its approved label; a
genuine package must still run, every substitution must leave execution disabled.

Each mutation re-seals a chosen plaintext (or swaps a committed field) under the SAME approved label, the way a
host with the governor's public key can. Before the fix the GPU runs whatever decrypts; after it, only the bytes
the manifest named. These checks fail on the pre-fix source (the swap runs) and pass after it.
"""
import os

import pytest

from govsim import origin_gate, reasons
from govsim.crypto import digest, sha256
from govsim.sealing import seal_weights

CHUNK = 4096
CONFIG = {"dtype": "fp16", "layers": 80, "context": 8192}


def _commitment(weights, chunk=CHUNK, fmt="safetensors", config=None):
    """The publisher's binding commitment, built with only primitives the pre-fix source already has, so these
    tests exercise the security property rather than any new helper."""
    data_len = len(weights)
    n = len(range(0, max(data_len, 1), chunk))
    return {"sha256": sha256(weights), "length": data_len, "chunk": chunk, "n": n,
            "format": fmt, "config": config or {}}


def _package(weights, model, kek, chunk=CHUNK, fmt="safetensors", config=None):
    """Seal a plaintext under ``model`` and record the commitment and packaging fields the publisher would sign."""
    s = seal_weights(weights, model, kek, chunk=chunk)
    s["format"], s["config"] = fmt, dict(config or {})
    s["weights"] = _commitment(weights, chunk, fmt, config)
    return s


def _manifest(r, commitment, model_name="model-70b", version=1):
    """A genuine publisher-signed manifest committing to ``commitment`` (built without the new manifest kwarg)."""
    return r.publisher.sign({"type": "manifest", "model_digest": digest([model_name, version]),
                             "name": model_name, "weights": commitment})


def _begin(r, node, commitment):
    assert r.load_model(node, manifest=_manifest(r, commitment))["ok"]
    node.gpu.sealed = True


def _release(r, node, package):
    return origin_gate._release(r, node, package)


def _fresh():
    r, node, model = origin_gate._rack()
    return r, node, model, node.governor.kek_public


# ---------------------------------------------------------------- the genuine package still runs (control)
def test_a_genuine_committed_package_runs():
    r, node, model, kek = _fresh()
    w = os.urandom(3 * CHUNK + 123)
    good = _package(w, model, kek, config=CONFIG)
    _begin(r, node, good["weights"])
    rel = _release(r, node, good)
    assert rel["ok"], rel
    assert node.gpu.install_key(rel["key_box"], rel["lease"])
    assert node.gpu.load_sealed(good)
    assert node.gpu.run_tokens(10) == 10
    assert node.gpu.weights_plain == w


# ---------------------------------------------------------------- whole-package replacement under the approved label
def test_substituted_weights_under_the_approved_label_never_run():
    r, node, model, kek = _fresh()
    w1 = os.urandom(3 * CHUNK + 123)
    good = _package(w1, model, kek, config=CONFIG)
    _begin(r, node, good["weights"])              # the manifest commits to w1
    w2 = os.urandom(3 * CHUNK + 123)
    evil = _package(w2, model, kek, config=CONFIG)  # different bytes, new DEK, same label, its own plaintext hash
    rel = _release(r, node, evil)
    if rel["ok"]:
        node.gpu.install_key(rel["key_box"], rel["lease"])
    assert not node.gpu.load_sealed(evil)
    assert node.gpu.weights_plain is None
    assert node.gpu.run_tokens(10) == 0


# ---------------------------------------------------------------- another evaluated model's weights, relabelled
def test_another_models_weights_relabelled_never_run():
    r, node, model, kek = _fresh()
    w1 = os.urandom(2 * CHUNK + 9)
    good = _package(w1, model, kek, config=CONFIG)
    _begin(r, node, good["weights"])
    other_weights = os.urandom(2 * CHUNK + 9)      # a different, itself-valid model's bytes
    relabelled = _package(other_weights, model, kek, config=CONFIG)   # sealed under this model's approved label
    rel = _release(r, node, relabelled)
    if rel["ok"]:
        node.gpu.install_key(rel["key_box"], rel["lease"])
    assert not node.gpu.load_sealed(relabelled)
    assert node.gpu.run_tokens(10) == 0


# ---------------------------------------------------------------- truncation of the committed object
def test_truncated_weights_never_run():
    r, node, model, kek = _fresh()
    w1 = os.urandom(4 * CHUNK)
    good = _package(w1, model, kek, config=CONFIG)
    _begin(r, node, good["weights"])
    rel = _release(r, node, good)                 # release the genuine key, then feed a truncated package
    assert rel["ok"] and node.gpu.install_key(rel["key_box"], rel["lease"])
    cut = dict(good, chunks=good["chunks"][:-1], n=good["n"] - 1)
    cut["plain_sha256"] = sha256(w1[:(good["n"] - 1) * CHUNK])   # self-consistent so it decrypts
    assert not node.gpu.load_sealed(cut)
    assert node.gpu.run_tokens(10) == 0


# ---------------------------------------------------------------- chunk duplication of the committed object
def test_duplicated_chunk_weights_never_run():
    r, node, model, kek = _fresh()
    w1 = os.urandom(4 * CHUNK)
    good = _package(w1, model, kek, config=CONFIG)
    _begin(r, node, good["weights"])
    dup_plain = w1[:2 * CHUNK] + w1[CHUNK:2 * CHUNK] + w1[2 * CHUNK:]   # one chunk's bytes repeated
    evil = _package(dup_plain, model, kek, config=CONFIG)              # re-sealed so it decrypts cleanly
    rel = _release(r, node, evil)
    if rel["ok"]:
        node.gpu.install_key(rel["key_box"], rel["lease"])
    assert not node.gpu.load_sealed(evil)
    assert node.gpu.run_tokens(10) == 0


# ---------------------------------------------------------------- execution-relevant config substitution
def test_config_substitution_never_runs():
    r, node, model, kek = _fresh()
    w1 = os.urandom(2 * CHUNK + 5)
    good = _package(w1, model, kek, config=CONFIG)
    _begin(r, node, good["weights"])              # the manifest commits to the approved config
    rel = _release(r, node, good)
    assert rel["ok"] and node.gpu.install_key(rel["key_box"], rel["lease"])
    swapped = dict(good, config={"dtype": "fp16", "layers": 80, "context": 1 << 20})   # same bytes, different config
    assert not node.gpu.load_sealed(swapped)
    assert node.gpu.run_tokens(10) == 0


# ---------------------------------------------------------------- a label with no weight commitment gets no key
def test_a_manifest_that_commits_to_no_weight_bytes_gets_no_key():
    r, node, model, kek = _fresh()
    w = os.urandom(2 * CHUNK)
    good = _package(w, model, kek, config=CONFIG)
    assert r.load_model(node, manifest=r.manifest())["ok"]   # the plain name/version manifest, no weight commitment
    node.gpu.sealed = True
    rel = _release(r, node, good)
    assert not rel["ok"] and rel["why"] == reasons.KEY_WEIGHTS_UNBOUND
    assert "key_box" not in rel
