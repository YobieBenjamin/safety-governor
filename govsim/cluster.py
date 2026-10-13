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
from .endpoints import ActionEndpoint, strike_checks
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
WORKLOAD_70B = digest([GPU_FW, HOST_FW, digest(["model-70b", 1])])            # the shipped model's workload measurement


def governor_meas1(firmware_digest: str = GOV_FW) -> str:
    r = MeasurementRegister()
    return r.extend(firmware_digest)


class Node:
    def __init__(self, name: str, gpu: GPU, governor: Governor, host_key: SigningKey, host_cert: dict):
        self.name, self.gpu, self.governor, self.host_key, self.host_cert = name, gpu, governor, host_key, host_cert
        self.host_seq = 0
        self.token: dict | None = None
        self.model_digest: str | None = None

    def host_sign(self, payload: dict, epoch: str) -> dict:
        self.host_seq += 1
        return self.host_key.sign({"seq": self.host_seq, "epoch": epoch, **payload})


class Rack:
    def __init__(self, n: int = 4, tier: str = "rack", clock: SimClock | None = None, direct_nvlink: bool = False,
                 levers: dict | None = None, store_dir: str | None = None, policy_kw: dict | None = None):
        self.clock = clock or SimClock()
        self.tier = tier
        self.policy_kw = dict(policy_kw or {})
        # parties
        self.governance = [SigningKey.generate() for _ in range(5)]
        self.threshold = 3
        self.heartbeat_key = SigningKey.generate()
        self.approvers = {"strike": [SigningKey.generate() for _ in range(3)], "payments.transfer.large": [SigningKey.generate() for _ in range(3)],
                          "alarms": [SigningKey.generate()]}
        self.publisher = SigningKey.generate()
        self.observer = SigningKey.generate()
        self.gpu_vendor = SigningKey.generate()
        self.cpu_vendor = SigningKey.generate()
        self.gov_vendor = SigningKey.generate()
        self.endpoint_keys = {"strike-guidance": SigningKey.generate(), "payment-switch": SigningKey.generate()}
        self.hb_seq = 0
        self.authority_seq = 0
        self.approver_seq: dict[str, int] = {}
        self.endpoint_seq: dict[str, int] = {}
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
            fuses = Fuses(chip_id=f"gov{i:02d}", governance_key_hashes=gov_hashes)
            store = Store(f"{store_dir}/gov{i:02d}.json" if store_dir else None)
            g = Governor(f"governor{i}", self.clock, tier=tier, fuses=fuses, store=store,
                         loader_digest=GOV_LOADER, firmware_digest=GOV_FW, firmware_version=GOV_FW_VERSION)
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
                          output_queries: int = 50, output_bytes: int = 200_000, unpresented_bytes: int = 1 << 20) -> dict:
        now = self.clock.now()
        refs = [
            {"device_class": "gpu", "vendor_key": self.gpu_vendor.public.hex, "firmware_digest": GPU_FW, "valid_until": now + 365 * 86400},
            {"device_class": "host", "vendor_key": self.cpu_vendor.public.hex, "firmware_digest": HOST_FW, "valid_until": now + 365 * 86400},
            {"device_class": "governor", "vendor_key": self.gov_vendor.public.hex, "meas1": governor_meas1(), "valid_until": now + 365 * 86400},
        ]
        rules = [
            make_rule("strike", "strike", mode=strike_mode, observers=[self.observer.key_id], max_risk=0.5, approvers_quorum=2,
                      constraints={"target": {"not_in_list": "protected-sites"}, "munition": {"in": ["gbu-39", "hellfire"]}},
                      endpoint="strike-guidance", inputs=["protected-sites", "navigation-fix", "observer-verdict"], delay_s=2.0),
            make_rule("payments.transfer.small", "payments.transfer", constraints={"amount": {"min": 0, "max": 1000}, "currency": {"in": ["USD"]}},
                      budget={"key": "pay-usd-hourly", "param": "amount", "limit": pay_small_limit, "window_s": 3600},
                      rate={"max": 100, "window_s": 60}, endpoint="payment-switch", inputs=["beneficiary-registry"]),
            make_rule("payments.transfer.large", "payments.transfer", mode="human", approvers_quorum=2,
                      constraints={"amount": {"min": 1000, "max": 1_000_000}}, endpoint="payment-switch", inputs=["beneficiary-registry"]),
            make_rule("model.output", "model.output", inputs=[],
                      output_budget={"queries": output_queries, "bytes": output_bytes, "window_s": 3600, "unpresented_bytes": unpresented_bytes}),
            make_rule("model.export.70b", "model.export", measurement=WORKLOAD_70B),              # exact workload: auto
            make_rule("model.export.any", "model.export", mode="human", approvers_quorum=2),      # any other workload: humans
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
        ]
        if drop_register_row:
            rows = [r for r in rows if r["input"] != drop_register_row]
        return make_policy(
            version=version, issued_at=now, expires_at=now + expires_in_s,
            governance_keys=[k.public for k in self.governance], threshold=self.threshold,
            approver_keys={rid: [k.public for k in ks] for rid, ks in self.approvers.items()},
            heartbeat_key=self.heartbeat_key.public, publisher_keys=[self.publisher.public], observer_keys=[self.observer.public],
            reference_values=refs,
            endpoints=[{"name": "strike-guidance", "pubkey": self.endpoint_keys["strike-guidance"].public.hex, "safe_transition": "no_release", "inputs": ["protected-sites", "navigation-fix"]},
                       {"name": "payment-switch", "pubkey": self.endpoint_keys["payment-switch"].public.hex, "safe_transition": "decline", "inputs": ["beneficiary-registry"]}],
            budget_owners={"pay-usd-hourly": "gov00"},
            rules=rules, assumptions=rows, override_floor_s=override_floor_s,
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
        for ep in (strike, pay):
            ep.commit = self._commit_route
            ep.set_epoch(g0.signed_epoch())
            self.endpoints[ep.name] = ep
            g0.endpoints[ep.name] = ep

    def _commit_route(self, ticket: dict) -> bool:
        """The endpoint commits to the governor whose key signed the ticket."""
        g = self.by_key.get(ticket.get("signer"))
        return g.commit_from_endpoint(ticket) if g is not None else False

    # ------------------------------------------------------------------ the authority
    def _authority_env(self, payload: dict) -> dict:
        self.authority_seq += 1
        return self.heartbeat_key.sign({"seq": self.authority_seq, "epoch": self.epoch, **payload})

    def heartbeat(self, window_s: float = 5.0, to: Governor | None = None) -> dict:
        """The authority's heartbeat enters at one governor and fans out over the fabric."""
        self.hb_seq += 1
        now = self.clock.now()
        env = self.heartbeat_key.sign({"type": "heartbeat", "seq": self.hb_seq, "epoch": self.epoch, "window_start": now - 1.0, "window_end": now + window_s})
        r = (to or self.entry).command("HEARTBEAT", {}, env)
        self.loop.propagate()                   # one sense period: armed governors see the closed loop and run
        return r

    def bring_up(self, job_id: str = "job-1") -> None:
        """Heartbeat, attest every node, load the model, form the roster. The normal start."""
        self.heartbeat()
        for node in self.nodes:
            node.governor.install_list("protected-sites", self.signed_list("protected-sites", PROTECTED_SITES))
            self.attest(node)
            self.load_model(node)
        self.form_roster(job_id)
        self.heartbeat()
        self.exchange_checkpoints()

    def recover(self, node: Node) -> None:
        """What the host does after a governor restart: heartbeat, re-attest, reload the model."""
        self.heartbeat()
        node.governor.install_list("protected-sites", self.signed_list("protected-sites", PROTECTED_SITES))
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

    def manifest(self, model_name: str = "model-70b", version: int = 1) -> dict:
        return self.publisher.sign({"type": "manifest", "model_digest": digest([model_name, version]), "name": model_name})

    def load_model(self, node: Node, manifest: dict | None = None) -> dict:
        g = node.governor
        env = node.host_sign({"manifest": manifest or self.manifest()}, g.epoch)
        r = g.command("BEGIN_MODEL", {}, env)
        if r["ok"]:
            node.token = r["token"]
            node.model_digest = (manifest or self.manifest())["payload"]["model_digest"]
            node.gpu.load(node.model_digest)
        return r

    def form_roster(self, job_id: str, members: list[Node] | None = None) -> dict | None:
        """Each host asks its governor to join through the mailbox; the lowest chip id leads."""
        members = members or self.nodes
        for node in members:
            node.governor.command("ROSTER_JOIN", {}, node.host_sign({"job_id": job_id}, node.governor.epoch))
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
        return g.command("REQUEST", {}, node.host_sign(body, g.epoch))

    def cap_request(self, node: Node, **fields) -> dict:
        g = node.governor
        return g.command("CAP_REQUEST", {}, node.host_sign(fields, g.epoch))

    def end_model(self, node: Node) -> dict:
        g = node.governor
        return g.command("END_MODEL", {}, node.host_sign({"model_digest": node.model_digest}, g.epoch))

    def commit_via_mailbox(self, governor: Governor, endpoint_name: str, ticket: dict) -> dict:
        key = self.endpoint_keys[endpoint_name]
        n = self.endpoint_seq.get(endpoint_name, 0) + 1
        self.endpoint_seq[endpoint_name] = n
        return governor.command("COMMIT", {}, key.sign({"seq": n, "epoch": governor.epoch, "ticket": ticket}))

    def witness(self, request_hash: str, risk: float = 0.1, ttl_s: float = 30.0) -> dict:
        return self.observer.sign({"type": "observer-verdict", "request_hash": request_hash, "risk": risk, "expires_at": self.clock.now() + ttl_s})

    def request_hash_for(self, node: Node, request_id: str, action: str, params: dict) -> str:
        return digest([request_id, node.token["payload"]["fingerprint"], action, params])

    def request_with_witness(self, node: Node, action: str, params: dict, risk: float = 0.1, governor: Governor | None = None) -> dict:
        g = governor or node.governor
        rid = random_id(8)
        rhash = digest([rid, node.token["payload"]["fingerprint"], action, params])
        body = {"request_id": rid, "measurement_token": node.token, "action": action, "params": params, "witnesses": [self.witness(rhash, risk)]}
        return g.command("REQUEST", {}, node.host_sign(body, g.epoch))

    def approve(self, governor: Governor, hold_id: str, request_hash: str, approver: SigningKey, reason: str = "reviewed") -> dict:
        n = self.approver_seq.get(approver.key_id, 0) + 1
        self.approver_seq[approver.key_id] = n
        env = approver.sign({"seq": n, "epoch": governor.epoch, "hold_id": hold_id, "request_hash": request_hash, "reason": reason})
        return governor.command("APPROVE", {}, env)

    def sign_output(self, node: Node, stream: str, data: bytes) -> dict:
        g = node.governor
        env = node.host_sign({"stream": stream, "claimed_prompt_hash": digest("prompt"), "nonce": random_id(8), "data_hex": data.hex()}, g.epoch)
        return g.command("SIGN_OUTPUT", {}, env)

    def clear(self, governor: Governor) -> dict:
        return governor.command("CLEAR", {}, self._authority_env({"type": "clear"}))

    def halt(self, governor: Governor, rung: str = "HALT") -> dict:
        return governor.command("HALT", {}, self._authority_env({"type": "halt", "rung": rung}))

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
        fuses = Fuses(chip_id="rogue", governance_key_hashes=[digest(k.public.hex) for k in self.governance])
        g = Governor("rogue", self.clock, tier=self.tier, fuses=fuses)
        g.device_cert = SigningKey.generate().sign({"type": "governor-device-cert", "chip_id": "rogue", "pub": g.device_key.public.hex})
        g.load_policy(self.policy)
        g.fabric = self.fabric
        self.fabric.join(g)          # on the wire, never on the loop (a rogue cannot open the loop from outside)
        return g

    def rogue_governor_with_bad_firmware(self) -> Governor:
        """A genuine chip (valid vendor certificate) running firmware that is not in the reference values."""
        fuses = Fuses(chip_id="gov-badfw", governance_key_hashes=[digest(k.public.hex) for k in self.governance])
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
