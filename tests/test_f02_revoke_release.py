# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F02: revocation must stop a fresh key release, not only a renewal.

An edition that keeps a model but revokes the GPU it was running on used to zeroize the live key yet leave the
GPU's cached attestation in place; a fresh host-signed KEY_RELEASE under the new epoch was then accepted, because
the release path checked the model allowlist but not the current GPU revocations, and the attestation predicate
checked only that a cache entry existed and had not expired. Releasing again and again could carry operation
through the one-hour attestation cache. Separately, replaying an old authentic key box and lease before its
original expiry restored execution, because the GPU checked signature, type and identity but kept no revocation
floor; and an idle lease never expired, because expiry was only ever checked inside ``run_tokens``.

The fix routes every attestation-dependent key operation through one current-policy validity predicate (the GPU
must not be revoked under the edition in force), invalidates the revoked chip's cached attestation on the policy
change, advances a protected revocation floor on the GPU before the key is wiped so an older lease or box is
refused, and expires the lease on a trusted timer whether or not any token runs. These checks fail on the pre-fix
source (the fresh release, the replay and the idle lease all keep the model alive) and pass after it.
"""
import os

import pytest

from govsim import origin_gate, reasons
from govsim.cluster import build_rack
from govsim.crypto import digest, sha256
from govsim.policy import sign_policy
from govsim.sealing import seal_weights

CHUNK = 4096
MODEL_NAME, MODEL_VERSION = "model-70b", 1


def _sealed_rack(n=1, lease_s=30.0):
    r = build_rack(n, "rack")
    model = r.manifest()["payload"]["model_digest"]
    r.policy_kw = {**getattr(r, "policy_kw", {}), "sealed_models": [model], "key_lease_s": lease_s}
    r.bring_up()
    assert r.change_epoch(r.new_policy())["committed"], "the edition with sealed_models did not commit"
    return r, model


def _commitment(weights, chunk=CHUNK):
    n = len(range(0, max(len(weights), 1), chunk))
    return {"sha256": sha256(weights), "length": len(weights), "chunk": chunk, "n": n, "format": "raw", "config": {}}


def _committing_manifest(r, commitment):
    return r.publisher.sign({"type": "manifest", "model_digest": digest([MODEL_NAME, MODEL_VERSION]),
                             "name": MODEL_NAME, "weights": commitment})


def _start(r, node, weights):
    """BEGIN_MODEL with a committing manifest, KEY_RELEASE, install, decrypt; the sealed model is running."""
    model = digest([MODEL_NAME, MODEL_VERSION])
    sealed = seal_weights(weights, model, node.governor.kek_public, chunk=CHUNK)
    sealed["format"], sealed["config"], sealed["weights"] = "raw", {}, _commitment(weights)
    assert r.load_model(node, manifest=_committing_manifest(r, sealed["weights"]))["ok"]
    node.gpu.sealed = True
    rel = origin_gate._release(r, node, sealed)
    assert rel["ok"], rel
    assert node.gpu.install_key(rel["key_box"], rel["lease"])
    assert node.gpu.load_sealed(sealed)
    return sealed, rel


def _revoke_gpu(r, chip_id):
    image = r.make_policy_image(r.policy_version + 1, **r.policy_kw)   # keeps sealed_models, so the model stays allowed
    image["revocations"] = [chip_id]
    r.policy_version += 1
    assert r.change_epoch(sign_policy(image, r.governance[: r.threshold]))["committed"]


# ---------------------------------------------------------------- a fresh release after revocation is denied
def test_a_revoked_gpu_gets_no_fresh_key_release():
    r, model = _sealed_rack(2, lease_s=30.0)
    a, b = r.nodes
    sealed_a, rel_a = _start(r, a, os.urandom(2 * CHUNK))
    assert a.gpu.run_tokens(10) == 10
    gpu_a = a.governor.verified["gpu"]["chip_id"]

    _revoke_gpu(r, gpu_a)                                   # the model is still allowed; only this GPU is revoked
    assert a.gpu.dek is None                                # the live key was taken back on the commit

    fresh = origin_gate._release(r, a, sealed_a)            # new sequence, current epoch, authentic envelope, live cache
    assert not fresh["ok"]
    assert "key_box" not in fresh and "lease" not in fresh  # denied with no key material of any kind

    # a non-revoked GPU under the very same edition still gets its key (the control)
    sealed_b, _ = _start(r, b, os.urandom(2 * CHUNK))
    assert b.gpu.run_tokens(10) == 10


# ---------------------------------------------------------------- replaying an old box/lease after revocation is denied
def test_a_replayed_old_box_and_lease_after_revocation_is_denied():
    r, model = _sealed_rack(1, lease_s=30.0)
    node = r.nodes[0]
    sealed, rel = _start(r, node, os.urandom(2 * CHUNK))
    assert node.gpu.run_tokens(10) == 10
    gpu_id = node.governor.verified["gpu"]["chip_id"]

    _revoke_gpu(r, gpu_id)
    assert node.gpu.dek is None

    # the original lease and key box are still well before their expiry, but they are below the revocation floor
    assert not node.gpu.install_key(rel["key_box"], rel["lease"])
    assert node.gpu.dek is None
    assert node.gpu.run_tokens(10) == 0


# ---------------------------------------------------------------- an idle lease expires on a trusted timer
def test_an_idle_lease_expires_without_running_tokens():
    r, model = _sealed_rack(1, lease_s=4.0)
    node = r.nodes[0]
    _start(r, node, os.urandom(2 * CHUNK))
    assert node.gpu.dek is not None and node.gpu.weights_plain is not None

    r.clock.advance(5.0)       # past the lease, with no renewal and no run_tokens call at all
    r.heartbeat()              # the authority stays live: only the key lease timer is under test
    r.tick()
    assert node.gpu.dek is None and node.gpu.weights_plain is None


# ---------------------------------------------------------------- a non-revoked session is untouched (control)
def test_a_non_revoked_edition_change_keeps_the_key():
    r, model = _sealed_rack(1, lease_s=30.0)
    node = r.nodes[0]
    _start(r, node, os.urandom(2 * CHUNK))
    assert r.change_epoch(r.new_policy())["committed"]   # a benign new edition that revokes nothing
    # the lease is still live and nothing was revoked, so the running key survives and the model keeps running
    assert node.gpu.dek is not None
    assert node.gpu.run_tokens(10) == 10
