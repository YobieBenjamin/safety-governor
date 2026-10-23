# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""H17: no governed action initiates without a ticket, and no governed response leaves the rack
without a release ticket. A response leaving the rack is the action ``response.release``: the
runtime presents it, the gate decides the lane, the egress at the DPU holds the bytes until a
ticket for exactly that response is admitted. Falsified if bytes leave, or an endpoint acts,
on anything other than a fresh ticket bound to that exact thing."""
import pytest

from govsim import reasons
from govsim.cli import usecase_hazard, usecase_oversight, usecase_plot, usecase_strike
from govsim.cluster import MODEL_70B, build_rack
from govsim.crypto import SigningKey, digest

MB = 1 << 20
BIG = {"output_queries": 10 ** 6, "output_bytes": 10 ** 12}
NO_SAMPLING = {**BIG, "audit": {"sample_rate": 0.0, "escrow_classes": ["hazard"], "store": "audit-store"}}


def rack_with(**kw):
    r = build_rack(1, "rack", policy_kw={**NO_SAMPLING, **kw})
    r.bring_up()
    return r, r.nodes[0]


def release_rule(g):
    return next(x for x in g.policy["rules"] if x["id"] == "response.release")


# ---------------------------------------------------------------- 1. response release as a governed action
def test_release_needs_a_verdict_from_an_observer_key_and_then_the_egress_delivers():
    r, node = rack_with()
    res = r.respond(node, "s", b"a clean response")
    assert res["request"]["why"] == reasons.GATE_WITNESS_MISSING and not res["released"][0] and node.egress.bytes_delivered == 0
    res = r.respond(node, "s", b"a clean response", observer={"hazard_class": "none", "legibility": 0.9})
    t = res["request"]["ticket"]["payload"]
    assert t["action"] == "response.release" and t["endpoint"] == "egress" and t["rule"] == "response.release"
    assert res["released"] == (True, reasons.OK) and node.egress.bytes_delivered == len(b"a clean response")
    assert node.egress.delivered["s"] == [b"a clean response"]
    assert node.governor.log.has("release.verdict", response_id=res["response_id"], hazard_class="none")


def test_release_lane_is_set_by_the_rule_auto_observer_or_human():
    r, node = rack_with(release_mode="auto")
    assert r.respond(node, "s", b"x")["released"][0]                                         # auto: no verdict needed
    r, node = rack_with(release_mode="human")
    res = r.respond(node, "s", b"x", observer={"hazard_class": "none"})
    assert res["request"]["why"] == reasons.GATE_HELD and node.egress.bytes_delivered == 0     # human: parked whatever the verdict
    hid, rh = res["request"]["hold_id"], res["request"]["request_hash"]
    r.clock.advance(61)
    r.heartbeat()
    for k in r.approvers["response.release"]:
        out = r.approve(node.governor, hid, rh, k)
    assert out["ok"] and node.egress.release(out["ticket"])[0] and node.egress.bytes_delivered == 1


def test_hazard_class_is_refused_or_parked_as_the_rule_says():
    r, node = rack_with()
    res = r.respond(node, "s", b"r", observer={"hazard_class": "hazard", "category": "class-a"})
    assert res["request"]["why"] == reasons.RELEASE_HAZARD and node.egress.bytes_delivered == 0
    assert node.governor.log.has("deny.request", why=reasons.RELEASE_HAZARD, response_id=res["response_id"])
    r, node = rack_with(on_hazard="human")
    res = r.respond(node, "s", b"r", observer={"hazard_class": "hazard", "category": "class-a"})
    assert res["request"]["why"] == reasons.GATE_HELD and res["request"]["cause"] == reasons.RELEASE_HAZARD
    assert node.governor.holds[res["request"]["hold_id"]]["cause"] == reasons.RELEASE_HAZARD and node.egress.bytes_delivered == 0
    req = release_rule(node.governor)["requirement"]
    assert req["allowed_hazard_classes"] == ["none"] and req["min_legibility"] == 0.0            # the defaults


def test_legibility_floor_is_refused_or_parked_as_the_rule_says():
    r, node = rack_with(min_legibility=0.5)
    res = r.respond(node, "s", b"r", observer={"hazard_class": "none", "legibility": 0.2})
    assert res["request"]["why"] == reasons.RELEASE_ILLEGIBLE and node.egress.bytes_delivered == 0
    assert r.respond(node, "s", b"r2", observer={"hazard_class": "none", "legibility": 0.7})["released"][0]
    r, node = rack_with(min_legibility=0.5, on_illegible="human")
    res = r.respond(node, "s", b"r", observer={"hazard_class": "none", "legibility": 0.2})
    assert res["request"]["why"] == reasons.GATE_HELD and res["request"]["cause"] == reasons.RELEASE_ILLEGIBLE


def test_verdict_from_a_key_outside_the_observer_set_or_stale_or_too_risky_is_refused():
    r, node = rack_with()
    pres = r.present(node, "s", "r1", b"bytes")
    h, sh = pres["response_hash"], pres["stream_hashes"]
    forged = r.verdict(h, key=SigningKey.generate())
    assert r.request_release(node, "s", "r1", h, sh, [forged])["why"] == reasons.GATE_WITNESS_MISSING
    other = r.verdict(digest("some other response"))
    assert r.request_release(node, "s", "r1", h, sh, [other])["why"] == reasons.GATE_WITNESS_MISSING
    stale = r.verdict(h, ttl_s=-1)
    assert r.request_release(node, "s", "r1", h, sh, [stale])["why"] == reasons.GATE_WITNESS_STALE
    r2, n2 = rack_with()
    release_rule(n2.governor)["requirement"]["max_risk"] = 0.5          # a rule with a risk ceiling
    pres = r2.present(n2, "s", "r1", b"bytes")
    risky = r2.verdict(pres["response_hash"], risk=0.9)
    assert r2.request_release(n2, "s", "r1", pres["response_hash"], pres["stream_hashes"], [risky])["why"] == reasons.GATE_WITNESS_RISK
    assert node.egress.bytes_delivered == 0 and n2.egress.bytes_delivered == 0


# ---------------------------------------------------------------- 2. the egress endpoint
def test_egress_without_a_ticket_never_delivers():
    r, node = rack_with()
    eg = node.egress
    eg.hold("s", "r1", b"held bytes")
    assert eg.bytes_held == len(b"held bytes")
    assert eg.release(None) == (False, reasons.TICKET_MISSING) and eg.state == "hold"
    assert eg.bytes_delivered == 0 and eg.delivered == {} and ("s", "r1") in eg.held


def test_forged_replayed_wrong_session_and_wrong_hash_tickets_never_deliver():
    r, node = rack_with()
    eg = node.egress
    res = r.respond(node, "s", b"first", observer={"hazard_class": "none"})
    good = res["request"]["ticket"]
    assert res["released"][0] and eg.bytes_delivered == 5
    eg.hold("s", "r-again", b"first")                                                       # same bytes, a new response id
    assert eg.release(good)[1] == reasons.TICKET_PARAMS_MISMATCH                               # the ticket names the old response id
    pres = r.present(node, "s", "r2", b"second")
    params = {"session": "s", "response_id": "r2", "response_hash": pres["response_hash"], "stream_hashes": pres["stream_hashes"]}
    forged = SigningKey.generate().sign({**good["payload"], "params_digest": digest(params)})
    assert eg.release(forged)[1] == reasons.TICKET_BAD_SIGNATURE
    req = r.request_release(node, "s", "r2", pres["response_hash"], pres["stream_hashes"], [r.verdict(pres["response_hash"])])
    assert req["ok"]
    wrong_session = {**req["ticket"], "payload": {**req["ticket"]["payload"], "params_digest": digest({**params, "session": "other"})}}
    assert eg.release(wrong_session)[1] == reasons.TICKET_PARAMS_MISMATCH                      # and its signature no longer matches anyway
    wrong_hash = r.request_release(node, "s", "r2", digest("not the response"), pres["stream_hashes"], [r.verdict(digest("not the response"))])
    assert wrong_hash["why"] == reasons.RELEASE_HASH_MISMATCH                                 # the governor never mints for a hash it did not record
    assert eg.release(req["ticket"])[0] and eg.bytes_delivered == 11
    assert eg.release(req["ticket"])[1] == reasons.TICKET_PARAMS_MISMATCH                      # the bytes are gone: nothing left to match
    eg.hold("s", "r2", b"second")                                                             # the runtime queues the same response again
    assert eg.release(req["ticket"])[1] == reasons.TICKET_REPLAY and eg.bytes_delivered == 11


def test_refused_release_leaves_delivery_unchanged_with_record_and_refusal_in_the_log():
    r, node = rack_with()
    g = node.governor
    res = r.respond(node, "s", b"r", observer={"hazard_class": "hazard", "category": "c"})
    assert not res["request"]["ok"] and node.egress.bytes_delivered == 0 and node.egress.bytes_held == 1
    assert res["presented"]["records"]["response"]["ok"]
    assert g.log.has("output.signed", response_id=res["response_id"], stream="response")
    assert g.log.has("deny.request", why=reasons.RELEASE_HAZARD, response_id=res["response_id"])
    assert g.log.verify_chain()


# ---------------------------------------------------------------- 3. hazard budgets per session
def test_session_hazard_budget_parks_the_session_and_raises_a_scoped_alarm():
    r, node = rack_with(on_hazard="human", hazard_budget={"max": 2, "window_s": 600})
    g = node.governor
    outs = [r.respond(node, "sess", f"h{i}".encode(), observer={"hazard_class": "hazard", "category": "c"}) for i in range(3)]
    assert [o["request"]["cause"] for o in outs] == [reasons.RELEASE_HAZARD, reasons.RELEASE_HAZARD, reasons.SESSION_HAZARD_BUDGET]
    assert g.alarms[reasons.SESSION_HAZARD_BUDGET]["session"] == "sess"
    assert g.log.has("release.session_hazard_budget", session="sess", count=3, max=2)
    clean = r.respond(node, "sess", b"clean", observer={"hazard_class": "none"})
    assert clean["request"]["why"] == reasons.GATE_HELD and clean["request"]["cause"] == reasons.SESSION_HAZARD_BUDGET   # regardless of class
    other = r.respond(node, "other-session", b"clean", observer={"hazard_class": "none"})
    assert other["released"][0]                                                              # the alarm is scoped to the session
    assert node.egress.delivered == {"other-session": [b"clean"]}
    r.clock.advance(601)
    r.heartbeat()
    assert r.respond(node, "sess", b"later", observer={"hazard_class": "none"})["released"][0]   # the window has passed


# ---------------------------------------------------------------- 5. required streams
def test_release_needs_every_required_stream():
    r, node = rack_with(streams_required=["response", "cot"])
    res = r.respond(node, "s", b"answer", observer={"hazard_class": "none"})
    assert res["request"]["why"] == reasons.RELEASE_STREAM_MISSING and node.egress.bytes_delivered == 0
    res = r.respond(node, "s", b"answer", cot_bytes=b"reasoning", observer={"hazard_class": "none"})
    assert res["released"][0] and node.egress.bytes_delivered == len(b"answer")
    assert node.governor.responses[res["response_id"]]["streams"].keys() == {"response", "cot"}
    assert r.request_release(node, "s", "never-presented", digest("x"), {}, [r.verdict(digest("x"))])["why"] == reasons.RELEASE_STREAM_MISSING


def test_stream_hashes_in_the_request_must_match_what_was_presented():
    r, node = rack_with(streams_required=["response", "cot"])
    pres = r.present(node, "s", "r1", b"answer", b"reasoning")
    lie = {**pres["stream_hashes"], "cot": digest("a different reasoning")}
    req = r.request_release(node, "s", "r1", pres["response_hash"], lie, [r.verdict(pres["response_hash"])])
    assert req["why"] == reasons.RELEASE_HASH_MISMATCH


# ---------------------------------------------------------------- 7a. training governance: where the weights may go
def test_weights_go_to_the_models_own_storage_and_nowhere_else_without_a_human_ticket():
    r = build_rack(2, "rack")
    r.bring_up()
    node = r.nodes[0]
    own = r.request(node, "weights.write", {"model_digest": MODEL_70B, "destination": MODEL_70B})
    assert own["ok"] and own["ticket"]["payload"]["rule"] == "weights.write.own"
    assert node.gpu.transfer("storage", MODEL_70B, "out", MB, buffer_class="weights") == (True, reasons.OK)
    for dest in ("bucket-x", r.nodes[1].gpu.chip_id, "host"):
        req = r.request(node, "weights.write", {"model_digest": MODEL_70B, "destination": dest})
        assert req["why"] == reasons.GATE_HELD and node.governor.holds[req["hold_id"]]["rule"] == "weights.write.any", dest
        assert node.gpu.transfer("storage", dest, "out", MB, buffer_class="weights") == (False, reasons.EP_NO_CAPABILITY), dest
    r.load_model(node, r.manifest("model-other", 1))                        # another workload: even its own digest needs humans
    req = r.request(node, "weights.write", {"model_digest": node.model_digest, "destination": node.model_digest})
    assert req["why"] == reasons.GATE_HELD


# ---------------------------------------------------------------- 8. the sandbox for model organisms
def test_sandbox_organism_reaches_the_audit_store_and_nothing_else():
    r = build_rack(2, "rack", policy_kw={"sandbox": True, **NO_SAMPLING})
    r.bring_up()
    node, other = r.nodes
    g = node.governor
    res = r.respond(node, "org", b"organism output", observer={"hazard_class": "none"}, egress=r.audit_store)
    assert res["released"][0] and r.audit_store.delivered == {"org": [b"organism output"]}
    assert node.egress.release(res["request"]["ticket"])[1] == reasons.TICKET_WRONG_ENDPOINT and node.egress.bytes_delivered == 0
    for action, params in (("payments.transfer", {"amount": 5, "currency": "USD", "destination": "a"}), ("model.export", {"target": "x"}),
                           ("weights.write", {"model_digest": MODEL_70B, "destination": MODEL_70B}), ("message.send", {"recipient": "recipient-a"}),
                           ("compute.extend", {}), ("shipment.order", {"item": "i"})):
        req = r.request(node, action, params)
        assert req["why"] == reasons.GATE_HELD, action
        assert g.policy["rules"][[x["id"] for x in g.policy["rules"]].index(g.holds[req["hold_id"]]["rule"])]["requirement"]["approvers_quorum"] == 2
    for exit_name in ("nvswitch", "pcie", "dpu"):
        assert node.gpu.transfer(exit_name, other.gpu.chip_id, "out", MB) == (False, reasons.EP_NO_CAPABILITY), exit_name
    assert g.switches["dpu"].table == {} and all(k[0] == "host" for k in g.switches["pcie"].table)
    assert g.policy["buffer_policy"] == {"weights": "none", "kv_cache": "none", "activations": "none", "outputs": "host"}
    r2 = build_rack(2, "integrated", policy_kw={"sandbox": True, **NO_SAMPLING})
    r2.bring_up()
    n2, o2 = r2.nodes
    assert n2.gpu.transfer("copy_engine", o2.gpu.chip_id, "out", MB, buffer_class="activations") == (False, reasons.EP_NO_CAPABILITY)
    assert n2.gpu.transfer("copy_engine", "host", "out", MB, buffer_class="outputs") == (True, reasons.OK)


# ---------------------------------------------------------------- 11 and 12. the narrated use cases
@pytest.mark.parametrize("name", ["strike", "hazard", "plot", "oversight"])
def test_usecase_narrations_run_and_no_bad_action_initiates(name):
    lines = []
    out = {"strike": usecase_strike, "hazard": usecase_hazard, "plot": usecase_plot, "oversight": usecase_oversight}[name](out=lines.append)
    assert len(lines) > 5 and all(l[0].isdigit() or l.startswith("   bypass") or l.startswith("     governor") for l in lines)
    if name == "strike":
        assert out["endpoint"].executed == [] and out["endpoint"].state == "no_release"
    if name == "hazard":
        eg = out["egress"]
        assert all(b not in out["hazard_bytes"] for items in eg.delivered.values() for b in items)
        assert eg.bytes_held > 0
    if name == "plot":
        rack = out["rack"]
        assert all(ep.executed == [] for ep in (rack.endpoints["messaging"], rack.endpoints["fulfilment"], rack.endpoints["payment-switch"]))
        assert out["egress"].bytes_delivered == 0
    if name == "oversight":
        assert out["egress"].bytes_delivered == 0 and out["audit_store"].bytes_delivered == len(b"[organism output]")
        assert out["compute"].nodes[0].governor.state == "THROTTLE"
