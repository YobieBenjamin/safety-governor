# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""A simulated rack: GPUs, governors, the host enclaves, the switches, the loop, the fabric,
the action endpoints, and the keys of the parties outside the rack (governance root,
approvers, heartbeat authority, publishers, observers, vendors).

``build_rack`` is the one entry point the tests and the harness use. The ``Rack`` object is
also the "policy authority" and the "untrusted host": it holds the keys the authority holds
and it can call any governor's mailbox the way a host can.
"""
from __future__ import annotations

from typing import Any

from . import reasons
from .clock import SimClock
from .crypto import SigningKey, VerifyKey, digest, random_id
from .endpoints import ActionEndpoint, AuditStore, EgressEndpoint, strike_checks
from .fabric import HaltLoop, MessageFabric
from .fuses import Fuses, PRODUCTION
from .governor import Governor, RUN
from .gpu import GPU
from .policy import make_policy, make_register_row, make_rule, policy_epoch, sign_policy
from .root import MeasurementRegister
from .store import Store

GPU_FW = "nvidia-gpu-fw-2026.10"
HOST_FW = "host-enclave-fw-1"
GOV_LOADER, GOV_FW, GOV_FW_VERSION = digest("loader-v1"), digest("governor-fw-v1"), 1
PROTECTED_SITES = [[34.052, -118.244], [48.857, 2.351], [31.769, 35.216]]   # schools, in the model's world
MODEL_70B = digest(["model-70b", 1])                                            # the shipped model's manifest digest
WORKLOAD_70B = digest([GPU_FW, HOST_FW, MODEL_70B])                            # the shipped model's workload measurement
LISTED_RECIPIENTS = ["recipient-a", "recipient-b"]                              # the signed recipient registry, in the model's world


def governor_meas1(firmware_digest: str = GOV_FW) -> str:
    r = MeasurementRegister()
    return r.extend(firmware_digest)


class Node:
    def __init__(self, name: str, gpu: GPU, governor: Governor, host_key: SigningKey, host_cert: dict):
        self.name, self.gpu, self.governor, self.host_key, self.host_cert = name, gpu, governor, host_key, host_cert
        self.host_seq = 0
        self.token: dict | None = None
        self.model_digest: str | None = None
        self.egress = None                     # the DPU's egress endpoint for this node (set by the rack)

    def host_sign(self, payload: dict, epoch: str, cmd: str) -> dict:
        """The host's signature over one command: the payload names the command it is for."""
        self.host_seq += 1
        return self.host_key.sign({"seq": self.host_seq, "epoch": epoch, **payload, "type": cmd.lower()})


class Rack:
    def __init__(self, n: int = 4, tier: str = "rack", clock: SimClock | None = None, direct_nvlink: bool = False,
                 levers: dict | None = None, store_dir: str | None = None, policy_kw: dict | None = None, rng_seed: int | None = None):
        self.clock = clock or SimClock()
        self.tier = tier
        self.policy_kw = dict(policy_kw or {})
        self.rng_seed = rng_seed
        # parties
        self.governance = [SigningKey.generate() for _ in range(5)]
        self.threshold = 3
        self.heartbeat_key = SigningKey.generate()
        self.authority_key = SigningKey.generate()      # HALT and CLEAR; never the heartbeat key
        self.approvers = {"strike": [SigningKey.generate() for _ in range(3)], "payments.transfer.large": [SigningKey.generate() for _ in range(3)],
                          "alarms": [SigningKey.generate()], "sandbox": [SigningKey.generate() for _ in range(2)],
                          "response.release": [SigningKey.generate() for _ in range(2)], "weights.write.any": [SigningKey.generate() for _ in range(2)],
                          "message.send.any": [SigningKey.generate() for _ in range(2)], "shipment.order": [SigningKey.generate() for _ in range(2)]}
        self.publisher = SigningKey.generate()
        self.observer = SigningKey.generate()
        # I1: a couple of customers, each with their own key, as a signed customer registry would hold them
        self.customers = {"alice-123": SigningKey.generate(), "bob-456": SigningKey.generate()}
        self.evaluator = SigningKey.generate()           # signs that a model passed its evaluations
        self.licensor = SigningKey.generate()            # signs compute licenses
        self.gpu_vendor = SigningKey.generate()
        self.cpu_vendor = SigningKey.generate()
        self.gov_vendor = SigningKey.generate()
        self.endpoint_keys = {"strike-guidance": SigningKey.generate(), "payment-switch": SigningKey.generate(),
                              "egress": SigningKey.generate(), "audit-store": SigningKey.generate(),
                              "messaging": SigningKey.generate(), "fulfilment": SigningKey.generate()}
        self.hb_seq = 0
        self.authority_seq = 0
        self.approver_seq: dict[str, int] = {}
        self.endpoint_seq: dict[str, int] = {}
        self.response_seq = 0
        # fabric
        self.loop = HaltLoop()
        self.fabric = MessageFabric()
        # policy
        self.policy_version = 1
        self.policy = sign_policy(self.make_policy_image(self.policy_version, **self.policy_kw), self.governance[: self.threshold])
        self.epoch = policy_epoch(self.policy)
        # nodes
        self.nodes: list[Node] = []
        gov_hashes = [digest(k.public.hex) for k in self.governance]
        for i in range(n):
            gpu = GPU(f"gpu{i}", self.clock, self.gpu_vendor, GPU_FW, levers=levers, direct_nvlink=direct_nvlink)
            fuses = Fuses(chip_id=f"gov{i:02d}", governance_key_hashes=gov_hashes, governance_threshold=self.threshold)
            store = Store(f"{store_dir}/gov{i:02d}.json" if store_dir else None)
            g = Governor(f"governor{i}", self.clock, tier=tier, fuses=fuses, store=store,
                         loader_digest=GOV_LOADER, firmware_digest=GOV_FW, firmware_version=GOV_FW_VERSION,
                         rng_seed=None if rng_seed is None else rng_seed + i)
            g.provision(self.gov_vendor, PRODUCTION)
            ok, why = g.load_policy(self.policy)
            assert ok, why
            g.attach_gpu(gpu)
            g.join(self.loop, self.fabric)
            hk = SigningKey.generate()
            hc = self.cpu_vendor.sign({"type": "host-enclave-cert", "pub": hk.public.hex})
            self.nodes.append(Node(f"node{i}", gpu, g, hk, hc))
        # endpoints, one of each; they hold every governor's key and commit to the governor that minted
        self.by_key = {n.governor.key.key_id: n.governor for n in self.nodes}
        self.endpoints: dict[str, ActionEndpoint] = {}
        self._make_endpoints()
        self.entry = self.nodes[0].governor      # where the authority's messages enter the fabric
        # the budget owner for the shared payments key is governor 0 (policy says so)

    # ------------------------------------------------------------------ policy
    def make_policy_image(self, version: int, *, pay_small_limit: float = 2000.0, strike_mode: str = "observer",
                          override_floor_s: float = 60.0, drop_register_row: str | None = None, expires_in_s: float = 30 * 86400,
                          output_queries: int = 50, output_bytes: int = 200_000, unpresented_bytes: int = 1 << 20,
                          buffer_classes: list[str] | None = None, buffer_policy: dict[str, str] | None = None,
                          release_mode: str = "observer", on_hazard: str = "refuse", on_illegible: str = "refuse",
                          min_legibility: float = 0.0, hazard_budget: dict | None = None, streams_required: list[str] | None = None,
                          audit: dict | None = None, deployment_gate: bool = False, compute_cycles: int | None = None,
                          sandbox: bool = False, extra_refs: list[dict] | None = None,
                          sealed_models: list[str] | None = None, key_lease_s: float = 60.0,
                          payer_confirm_payments: bool = False) -> dict:
        now = self.clock.now()
        refs = [
            {"device_class": "gpu", "vendor_key": self.gpu_vendor.public.hex, "firmware_digest": GPU_FW, "valid_until": now + 365 * 86400},
            {"device_class": "host", "vendor_key": self.cpu_vendor.public.hex, "firmware_digest": HOST_FW, "valid_until": now + 365 * 86400},
            {"device_class": "governor", "vendor_key": self.gov_vendor.public.hex, "meas1": governor_meas1(), "valid_until": now + 365 * 86400},
        ] + list(extra_refs or [])      # e.g. NVIDIA-format GPU references (govsim/hardware_ref/nvtrust.py)
        human = {"mode": "human", "approvers_quorum": 2}
        rules = [
            make_rule("strike", "strike", mode=strike_mode, observers=[self.observer.key_id], max_risk=0.5, approvers_quorum=2,
                      constraints={"target": {"not_in_list": "protected-sites"}, "munition": {"in": ["gbu-39", "hellfire"]}},
                      endpoint="strike-guidance", inputs=["protected-sites", "navigation-fix", "observer-verdict"], delay_s=2.0),
            make_rule("payments.transfer.small", "payments.transfer", constraints={"amount": {"min": 0, "max": 1000}, "currency": {"in": ["USD"]}},
                      budget={"key": "pay-usd-hourly", "param": "amount", "limit": pay_small_limit, "window_s": 3600},
                      rate={"max": 100, "window_s": 60}, endpoint="payment-switch", inputs=["beneficiary-registry"],
                      payer_confirm=({"registry": "customer-registry", "account_param": "from_account"} if payer_confirm_payments else None),
                      **(human if sandbox else {})),
            make_rule("payments.transfer.large", "payments.transfer", mode="human", approvers_quorum=2,
                      constraints={"amount": {"min": 1000, "max": 1_000_000}}, endpoint="payment-switch", inputs=["beneficiary-registry"]),
            make_rule("model.output", "model.output", inputs=[],
                      output_budget={"queries": output_queries, "bytes": output_bytes, "window_s": 3600, "unpresented_bytes": unpresented_bytes}),
            make_rule("model.export.70b", "model.export", measurement=WORKLOAD_70B, **(human if sandbox else {})),   # exact workload: auto
            make_rule("model.export.any", "model.export", mode="human", approvers_quorum=2),                           # any other workload: humans
            # a response leaving the rack is an action; in the sandbox its only destination is the audit store
            make_rule("response.release", "response.release", mode="auto" if sandbox else release_mode, observers=[self.observer.key_id],
                      max_risk=1.0, approvers_quorum=2, endpoint="audit-store" if sandbox else "egress", inputs=["observer-verdict"],
                      on_hazard=on_hazard, on_illegible=on_illegible, min_legibility=min_legibility, hazard_budget=hazard_budget,
                      streams_required=streams_required),
            # training governance: a model writes its weights to its own storage flow and nowhere else without humans
            make_rule("weights.write.own", "weights.write", measurement=WORKLOAD_70B, constraints={"destination": {"in": [MODEL_70B]}},
                      **(human if sandbox else {})),
            make_rule("weights.write.any", "weights.write", mode="human", approvers_quorum=2),
            make_rule("compute.extend", "compute.extend", **(human if sandbox else {})),          # carries a compute license
            # an agent acting in the world: each action is its own rule and its own endpoint
            make_rule("message.send.listed", "message.send", constraints={"recipient": {"in_list": "recipient-registry"}},
                      endpoint="messaging", inputs=["recipient-registry"], **(human if sandbox else {})),
            make_rule("message.send.any", "message.send", mode="human", approvers_quorum=2, endpoint="messaging"),
            make_rule("shipment.order", "shipment.order", mode="human", approvers_quorum=2, endpoint="fulfilment"),
        ]
        rows = [
            make_register_row("protected-sites", "deconfliction authority list, countersigned by the governance root", "per-entry expiry; stale is a denial",
                              "any source saying protected wins", "deconfliction authority and governance root are different bodies", "whether the list is complete"),
            make_register_row("navigation-fix", "two sources (satellite plus inertial) agreeing within a bound", "per-fix timestamp from the device clock",
                              "disagreement is a denial", "different physics", "coordinated spoofing of both"),
            make_register_row("observer-verdict", "keys anchored in the policy image", "seconds; bound to one request hash", "missing or stale is a denial",
                              "observers run on isolated compute", "whether the observer is right"),
            make_register_row("beneficiary-registry", "sanctions and beneficiary registries, signed", "registry version in the epoch", "new beneficiary is a hold",
                              "registries run by different bodies", "whether an entry is correct"),
            make_register_row("pay-usd-hourly", "the policy image (budget limit and window)", "epoch", "old epoch is a denial",
                              "as for the policy", "whether the limit is the right limit"),
            make_register_row("recipient-registry", "the operator's signed recipient list", "per-list expiry; stale is a denial",
                              "unlisted recipient is a hold", "the list is signed outside the rack", "whether a listed recipient should be"),
        ]
        if drop_register_row:
            rows = [r for r in rows if r["input"] != drop_register_row]
        if sandbox:
            buffer_policy = {"weights": "none", "kv_cache": "none", "activations": "none", "outputs": "host"}
        approver_keys = {rid: [k.public for k in ks] for rid, ks in self.approvers.items()}
        if sandbox:
            approver_keys.update({r["id"]: [k.public for k in self.approvers["sandbox"]] for r in rules if r["requirement"]["mode"] == "human"})
        endpoints = [{"name": "strike-guidance", "pubkey": self.endpoint_keys["strike-guidance"].public.hex, "safe_transition": "no_release", "inputs": ["protected-sites", "navigation-fix"]},
                     {"name": "payment-switch", "pubkey": self.endpoint_keys["payment-switch"].public.hex, "safe_transition": "decline", "inputs": ["beneficiary-registry"]},
                     {"name": "egress", "pubkey": self.endpoint_keys["egress"].public.hex, "safe_transition": "hold", "inputs": []},
                     {"name": "audit-store", "pubkey": self.endpoint_keys["audit-store"].public.hex, "safe_transition": "hold", "inputs": []},
                     {"name": "messaging", "pubkey": self.endpoint_keys["messaging"].public.hex, "safe_transition": "hold", "inputs": ["recipient-registry"]},
                     {"name": "fulfilment", "pubkey": self.endpoint_keys["fulfilment"].public.hex, "safe_transition": "hold", "inputs": []}]
        return make_policy(
            version=version, issued_at=now, expires_at=now + expires_in_s,
            governance_keys=[k.public for k in self.governance], threshold=self.threshold,
            approver_keys=approver_keys,
            heartbeat_key=self.heartbeat_key.public, authority_keys=[self.authority_key.public], publisher_keys=[self.publisher.public], observer_keys=[self.observer.public],
            reference_values=refs, endpoints=endpoints,
            budget_owners={"pay-usd-hourly": "gov00", "hazard": "gov00"},
            rules=rules, assumptions=rows, override_floor_s=override_floor_s,
            buffer_classes=buffer_classes, buffer_policy=buffer_policy,      # None: the defaults in govsim/policy.py
            audit=audit, streams_required=streams_required, eval_keys=[self.evaluator.public], deployment_gate=deployment_gate,
            compute_budget={"cycles": compute_cycles, "license_keys": [self.licensor.public.hex]}, sandbox=sandbox,
            sealed_models=sealed_models, key_lease_s=key_lease_s,
        )

    def signed_list(self, list_id: str, entries: list, expires_in_s: float = 86400.0) -> dict:
        return self.governance[0].sign({"type": "list", "list_id": list_id, "entries": entries, "expires_at": self.clock.now() + expires_in_s})

    def _make_endpoints(self) -> None:
        g0 = self.nodes[0].governor
        keys = {kid: g.key.public for kid, g in self.by_key.items()}
        protected = {"entries": [tuple(e) for e in PROTECTED_SITES], "stale": False}
        strike = ActionEndpoint("strike-guidance", self.clock, keys, safe_transition="no_release",
                                sensors={"nav_gnss": (37.0, -122.0), "nav_inertial": (37.0, -122.0), "lists": {"protected-sites": protected}})
        strike.checks = strike_checks()
        pay = ActionEndpoint("payment-switch", self.clock, keys, safe_transition="decline")
        messaging = ActionEndpoint("messaging", self.clock, keys, safe_transition="hold")
        fulfilment = ActionEndpoint("fulfilment", self.clock, keys, safe_transition="hold")
        self.audit_store = AuditStore("audit-store", self.clock, keys, self.endpoint_keys["audit-store"])
        for ep in (strike, pay, messaging, fulfilment, self.audit_store):
            ep.commit = self._commit_route
            ep.set_epoch(g0.signed_epoch())
            self.endpoints[ep.name] = ep
            g0.endpoints[ep.name] = ep
        for node in self.nodes:                      # the DPU's egress to the user: one per node
            node.egress = EgressEndpoint("egress", self.clock, keys)
            node.egress.commit = self._commit_route
            node.egress.set_epoch(node.governor.signed_epoch())
            node.governor.endpoints["egress"] = node.egress
        self.endpoints["egress"] = self.nodes[0].egress

    def _commit_route(self, ticket: dict) -> bool:
        """The endpoint commits to the governor whose key signed the ticket."""
        g = self.by_key.get(ticket.get("signer"))
        return g.commit_from_endpoint(ticket) if g is not None else False

    # ------------------------------------------------------------------ the authority
    def _authority_env(self, payload: dict, governor: Governor, ttl_s: float = 30.0) -> dict:
        """A HALT or CLEAR names its command, the one chip it is for and when it stops being good."""
        self.authority_seq += 1
        return self.authority_key.sign({"seq": self.authority_seq, "epoch": self.epoch, "chip_id": governor.chip_id,
                                        "expires_at": self.clock.now() + ttl_s, **payload})

    def loop_beacon(self) -> dict:
        """The LOOP_BEACON body: the loop the authority wired and who it expects on it. It rides inside the
        signed heartbeat, so it has the authority's signature, sequence, window and epoch for free."""
        return {"loop_id": self.loop.loop_id, "expected_members": [m.chip_id for m in self.loop.members], "seq": self.hb_seq}

    def heartbeat(self, window_s: float = 5.0, to: Governor | None = None, beacon: bool = True) -> dict:
        """The authority's heartbeat enters at one governor and fans out over the fabric. Every heartbeat
        carries the loop beacon (a lower rate is a policy choice; ``beacon=False`` shows the loop alone)."""
        self.hb_seq += 1
        now = self.clock.now()
        payload = {"type": "heartbeat", "seq": self.hb_seq, "epoch": self.epoch, "window_start": now - 1.0, "window_end": now + window_s}
        if beacon:
            payload["loop_beacon"] = self.loop_beacon()
        env = self.heartbeat_key.sign(payload)
        r = (to or self.entry).command("HEARTBEAT", {}, env)
        self.loop.propagate()                   # one sense period: armed governors see the closed loop and run
        return r

    def install_lists(self, node: Node) -> None:
        node.governor.install_list("protected-sites", self.signed_list("protected-sites", PROTECTED_SITES))
        node.governor.install_list("recipient-registry", self.signed_list("recipient-registry", LISTED_RECIPIENTS))

    def bring_up(self, job_id: str = "job-1") -> None:
        """Heartbeat, attest every node, load the model, form the roster. The normal start."""
        self.heartbeat()
        for node in self.nodes:
            self.install_lists(node)
            self.attest(node)
            self.load_model(node)
        self.form_roster(job_id)
        self.heartbeat()
        self.exchange_checkpoints()

    def recover(self, node: Node) -> None:
        """What the host does after a governor restart: heartbeat, re-attest, reload the model."""
        self.heartbeat()
        self.install_lists(node)
        self.attest(node)
        self.load_model(node)
        self.heartbeat()

    def reload_jobs(self) -> None:
        """After a reset the GPU has no job; the host reloads the model on every running governor."""
        for node in self.nodes:
            if node.governor.state == RUN and node.gpu.job is None:
                self.load_model(node)

    def attest(self, node: Node) -> dict:
        g = node.governor
        nonce = g.nonce()
        rep = node.gpu.attestation_report(nonce, self.tier)
        r1 = g.command("VERIFY_GPU", rep)
        nonce2 = g.nonce()
        host_report = node.host_key.sign({"type": "host-report", "firmware_digest": HOST_FW, "nonce": nonce2})
        r2 = g.command("VERIFY_HOST", {"report": host_report, "cert": node.host_cert})
        return {"gpu": r1, "host": r2}

    def manifest(self, model_name: str = "model-70b", version: int = 1, weights: dict | None = None) -> dict:
        """The publisher's signed manifest. For a sealed model it commits to the exact weight bytes through
        ``weights`` (a ``sealing.weights_commitment`` descriptor); the origin gate binds the released key to it (F01)."""
        payload = {"type": "manifest", "model_digest": digest([model_name, version]), "name": model_name}
        if weights is not None:
            payload["weights"] = weights
        return self.publisher.sign(payload)

    def load_model(self, node: Node, manifest: dict | None = None, eval_attestation: dict | None = None, license: dict | None = None) -> dict:
        g = node.governor
        manifest = manifest or self.manifest()
        if eval_attestation is None and g.policy.get("deployment_gate"):
            eval_attestation = self.eval_attestation(manifest["payload"]["model_digest"])
        body = {k: v for k, v in {"eval_attestation": eval_attestation, "license": license}.items() if v}   # False: send none
        env = node.host_sign({"manifest": manifest}, g.epoch, "BEGIN_MODEL")
        r = g.command("BEGIN_MODEL", body, env)
        if r["ok"]:
            node.token = r["token"]
            node.model_digest = manifest["payload"]["model_digest"]
            node.gpu.load(node.model_digest)
        return r

    def eval_attestation(self, model_digest: str, passed: bool = True, key: SigningKey | None = None) -> dict:
        """The evaluator's signed statement that this exact digest passed its evaluations."""
        return (key or self.evaluator).sign({"type": "eval-attestation", "model_digest": model_digest, "evals_passed": passed,
                                             "report_digest": digest(["eval-report", model_digest])})

    def license(self, model_digest: str, cycles_allowed: int, key: SigningKey | None = None) -> dict:
        """A compute license: the licensor's signature over the digest and the cycles it may run."""
        return (key or self.licensor).sign({"type": "compute-license", "model_digest": model_digest, "cycles_allowed": cycles_allowed})

    def compliance_report(self, governor: Governor, nonce: str | None = None) -> dict:
        """A verifier's view: ATTEST over its own nonce, the quote carrying the compliance block."""
        return governor.command("ATTEST", {"nonce": nonce or random_id(8)})

    def form_roster(self, job_id: str, members: list[Node] | None = None) -> dict | None:
        """Each host asks its governor to join through the mailbox; the lowest chip id leads."""
        members = members or self.nodes
        for node in members:
            node.governor.command("ROSTER_JOIN", {}, node.host_sign({"job_id": job_id}, node.governor.epoch, "ROSTER_JOIN"))
        leader = min(members, key=lambda n: n.governor.chip_id).governor
        return leader.build_roster(job_id, [n.governor.chip_id for n in members])

    def exchange_checkpoints(self) -> None:
        for node in self.nodes:
            node.governor.publish_checkpoint()

    def tick(self, seconds: float = 0.0, steps: int = 1) -> None:
        """Advance time, then let every governor sense the loop and run its timers."""
        if seconds:
            self.clock.advance(seconds)
        for _ in range(steps):
            for node in self.nodes:
                node.governor.tick()
            self.loop.propagate()

    # ------------------------------------------------------------------ the host side (untrusted)
    def request(self, node: Node, action: str, params: dict, witnesses: list[dict] | None = None, labels: dict | None = None, governor: Governor | None = None) -> dict:
        """A typed request, signed by the node's verified host enclave."""
        g = governor or node.governor
        body = {"request_id": random_id(8), "measurement_token": node.token, "action": action, "params": params, "witnesses": witnesses or []}
        if labels:
            body.update(labels)      # requester-supplied labels; the gate must ignore them (H4)
        return g.command("REQUEST", {}, node.host_sign(body, g.epoch, "REQUEST"))

    def customer_registry_list(self, expires_in_s: float = 86400.0) -> dict:
        """I1: the signed account -> customer-key registry the payer-confirm rule names."""
        entries = [{"account": acct, "key": k.public.hex} for acct, k in self.customers.items()]
        return self.governance[0].sign({"type": "list", "list_id": "customer-registry", "entries": entries,
                                        "expires_at": self.clock.now() + expires_in_s})

    def pay(self, node: Node, amount: float, from_account: str, confirm_as: str | None = None,
            confirm_request_id: str | None = None, confirm_ttl_s: float = 60.0, governor: Governor | None = None) -> dict:
        """A small USD transfer. confirm_as names whose key signs the payer confirmation (the account's own key for an
        intended wire; another account, or None, for an unintended one). confirm_request_id lets a test reuse a
        confirmation signed for a different request (a replay)."""
        g = governor or node.governor
        rid = random_id(8)
        params = {"amount": amount, "currency": "USD", "from_account": from_account, "to": "recipient-a"}
        rhash = digest([confirm_request_id or rid, node.token["payload"]["fingerprint"], "payments.transfer", params])
        witnesses = []
        if confirm_as is not None:
            signer = self.customers.get(confirm_as) or self.observer    # unknown name falls back to a non-customer key
            witnesses.append(signer.sign({"type": "payer-confirm", "request_hash": rhash,
                                          "expires_at": self.clock.now() + confirm_ttl_s}))
        body = {"request_id": rid, "measurement_token": node.token, "action": "payments.transfer", "params": params,
                "witnesses": witnesses}
        return g.command("REQUEST", {}, node.host_sign(body, g.epoch, "REQUEST"))

    def cap_request(self, node: Node, **fields) -> dict:
        g = node.governor
        return g.command("CAP_REQUEST", {}, node.host_sign(fields, g.epoch, "CAP_REQUEST"))

    def end_model(self, node: Node) -> dict:
        g = node.governor
        return g.command("END_MODEL", {}, node.host_sign({"model_digest": node.model_digest}, g.epoch, "END_MODEL"))

    def commit_via_mailbox(self, governor: Governor, endpoint_name: str, ticket: dict) -> dict:
        key = self.endpoint_keys[endpoint_name]
        n = self.endpoint_seq.get(endpoint_name, 0) + 1
        self.endpoint_seq[endpoint_name] = n
        return governor.command("COMMIT", {}, key.sign({"seq": n, "epoch": governor.epoch, "ticket": ticket, "type": "commit"}))

    def witness(self, request_hash: str, risk: float = 0.1, ttl_s: float = 30.0) -> dict:
        return self.observer.sign({"type": "observer-verdict", "request_hash": request_hash, "risk": risk, "expires_at": self.clock.now() + ttl_s})

    def request_hash_for(self, node: Node, request_id: str, action: str, params: dict) -> str:
        return digest([request_id, node.token["payload"]["fingerprint"], action, params])

    def request_with_witness(self, node: Node, action: str, params: dict, risk: float = 0.1, governor: Governor | None = None) -> dict:
        g = governor or node.governor
        rid = random_id(8)
        rhash = digest([rid, node.token["payload"]["fingerprint"], action, params])
        body = {"request_id": rid, "measurement_token": node.token, "action": action, "params": params, "witnesses": [self.witness(rhash, risk)]}
        return g.command("REQUEST", {}, node.host_sign(body, g.epoch, "REQUEST"))

    def approve(self, governor: Governor, hold_id: str, request_hash: str, approver: SigningKey, reason: str = "reviewed") -> dict:
        n = self.approver_seq.get(approver.key_id, 0) + 1
        self.approver_seq[approver.key_id] = n
        env = approver.sign({"seq": n, "epoch": governor.epoch, "hold_id": hold_id, "request_hash": request_hash, "reason": reason, "type": "approve"})
        return governor.command("APPROVE", {}, env)

    def sign_output(self, node: Node, stream: str, data: bytes, response_id: str | None = None, session: str | None = None) -> dict:
        g = node.governor
        env = node.host_sign({"stream": stream, "claimed_prompt_hash": digest("prompt"), "nonce": random_id(8), "data_hex": data.hex(),
                              "response_id": response_id or stream, "session": session}, g.epoch, "SIGN_OUTPUT")
        return g.command("SIGN_OUTPUT", {}, env)

    # ------------------------------------------------------------------ the response path (the verified runtime)
    def verdict(self, response_hash: str, hazard_class: str = "none", category: str = "", risk: float = 0.1,
                legibility: float = 1.0, ttl_s: float = 30.0, key: SigningKey | None = None) -> dict:
        """An observer's assertion over a response hash. Classes are abstract: "none" or "hazard"."""
        return (key or self.observer).sign({"type": "observer-verdict", "response_hash": response_hash, "hazard_class": hazard_class,
                                             "category": category, "risk": risk, "legibility": legibility, "expires_at": self.clock.now() + ttl_s})

    def present(self, node: Node, session: str, response_id: str, response_bytes: bytes, cot_bytes: bytes | None = None) -> dict:
        """SIGN_OUTPUT for each stream of a response, and the bytes held at the DPU's egress. Returns the records and hashes."""
        streams = {"response": response_bytes}
        if cot_bytes is not None:
            streams["cot"] = cot_bytes
        for s, data in streams.items():
            node.gpu.emit(s, data)                   # the bytes leave the GPU for the host (inline-hashed at the integrated tier)
        records = {s: self.sign_output(node, s, data, response_id=response_id, session=session) for s, data in streams.items()}
        hashes = {s: r["record"]["payload"]["output_hash"] for s, r in records.items() if r["ok"]}
        node.egress.hold(session, response_id, response_bytes, hashes)
        return {"records": records, "stream_hashes": hashes, "response_hash": hashes.get("response")}

    def request_release(self, node: Node, session: str, response_id: str, response_hash: str, stream_hashes: dict,
                        witnesses: list[dict] | None = None) -> dict:
        params = {"session": session, "response_id": response_id, "response_hash": response_hash, "stream_hashes": stream_hashes}
        return self.request(node, "response.release", params, witnesses=witnesses or [])

    def respond(self, node: Node, session: str, response_bytes: bytes, cot_bytes: bytes | None = None, observer: dict | None = None,
                escrow: bool = False, response_id: str | None = None, egress=None) -> dict:
        """The verified runtime's whole path: present the streams, ask for release (with the observer's verdict,
        given as its fields, and the escrow receipt when asked), and release at the egress on the ticket."""
        self.response_seq += 1
        response_id = response_id or f"resp-{self.response_seq}"
        egress = egress or node.egress
        pres = self.present(node, session, response_id, response_bytes, cot_bytes)
        if egress is not node.egress:
            egress.hold(session, response_id, response_bytes, pres["stream_hashes"])
        witnesses = []
        if observer is not None and pres["response_hash"]:
            witnesses.append(self.verdict(pres["response_hash"], **observer))
        if escrow and pres["response_hash"]:
            witnesses.append(self.audit_store.receipt(pres["response_hash"]))
        req = self.request_release(node, session, response_id, pres["response_hash"], pres["stream_hashes"], witnesses) \
            if pres["response_hash"] else {"ok": False, "why": pres["records"]["response"]["why"]}
        released = egress.release(req["ticket"]) if req.get("ok") else (False, req["why"])
        return {"response_id": response_id, "response_hash": pres["response_hash"], "presented": pres, "request": req, "released": released}

    def clear(self, governor: Governor) -> dict:
        return governor.command("CLEAR", {}, self._authority_env({"type": "clear"}, governor))

    def exclude(self, governor: Governor) -> dict:
        """EXCLUDE (docs/04 section 3): the authority's signed, logged way past a chip that never got its first heartbeat."""
        return governor.command("EXCLUDE", {}, self._authority_env({"type": "exclude"}, governor))

    def halt(self, governor: Governor, rung: str = "HALT") -> dict:
        return governor.command("HALT", {}, self._authority_env({"type": "halt", "rung": rung}, governor))

    # ------------------------------------------------------------------ epoch change
    def new_policy(self, **kw) -> dict:
        self.policy_version += 1
        image = self.make_policy_image(self.policy_version, **{**self.policy_kw, **kw})
        return sign_policy(image, self.governance[: self.threshold])

    def change_epoch(self, image: dict, silent: list[str] | None = None) -> dict:
        """Two-phase epoch change. The authority proposes to every governor it can reach from its
        entry point; a governor whose host never delivers the proposal (``silent``) or that is cut
        off never acknowledges. When the acknowledging set is the whole roster the authority commits
        everywhere it can; otherwise it commits to the acknowledging set and the stragglers are
        expelled: the new heartbeats carry the new epoch, a governor still on the old epoch refuses
        them, and it halts at its heartbeat expiry (the mechanism tested in H14)."""
        silent = set(silent or [])
        reachable = [n.governor for n in self.nodes if self.fabric.reachable(self.entry.chip_id, n.governor.chip_id) or n.governor is self.entry]
        acks = {}
        for g in reachable:
            if g.chip_id in silent:
                continue
            r = g.command("POLICY_PROPOSE", {"image": image})
            if r["ok"]:
                acks[g.chip_id] = r["ack"]
        stragglers = [n.governor.chip_id for n in self.nodes if n.governor.chip_id not in acks]
        new_epoch = policy_epoch(image)
        committed = []
        for g in reachable:
            if g.chip_id in acks:
                r = g.command("POLICY_COMMIT", {"epoch": new_epoch})
                if r["ok"]:
                    committed.append(g.chip_id)
        if committed:
            self.policy, self.epoch = image, new_epoch
        return {"acks": sorted(acks), "committed": sorted(committed), "stragglers": sorted(stragglers), "epoch": new_epoch}

    # ------------------------------------------------------------------ red team helpers
    def rogue_governor(self) -> Governor:
        """A device on the wire with no vendor certificate: it can send bytes and nothing else."""
        fuses = Fuses(chip_id="rogue", governance_key_hashes=[digest(k.public.hex) for k in self.governance], governance_threshold=self.threshold)
        g = Governor("rogue", self.clock, tier=self.tier, fuses=fuses)
        g.device_cert = SigningKey.generate().sign({"type": "governor-device-cert", "chip_id": "rogue", "pub": g.device_key.public.hex})
        g.load_policy(self.policy)
        g.fabric = self.fabric
        self.fabric.join(g)          # on the wire, never on the loop (a rogue cannot open the loop from outside)
        return g

    def rogue_governor_with_bad_firmware(self) -> Governor:
        """A genuine chip (valid vendor certificate) running firmware that is not in the reference values."""
        fuses = Fuses(chip_id="gov-badfw", governance_key_hashes=[digest(k.public.hex) for k in self.governance], governance_threshold=self.threshold)
        g = Governor("badfw", self.clock, tier=self.tier, fuses=fuses, loader_digest=GOV_LOADER,
                     firmware_digest=digest("governor-fw-patched"), firmware_version=GOV_FW_VERSION)
        g.provision(self.gov_vendor, PRODUCTION)
        g.load_policy(self.policy)
        g.fabric = self.fabric
        self.fabric.join(g)
        return g

    def running(self) -> list[bool]:
        return [n.gpu.running for n in self.nodes]


def build_rack(n: int = 4, tier: str = "rack", **kw) -> Rack:
    return Rack(n=n, tier=tier, **kw)
