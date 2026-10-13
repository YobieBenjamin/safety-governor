"""H6: the comparator holds with every layer above it compromised. The red team holds the
host, the broker and the runtime. Falsified if a release succeeds."""
from govsim import reasons
from govsim.cluster import PROTECTED_SITES
from conftest import strike

SCHOOL = PROTECTED_SITES[0]
FIELD = [37.0, -122.0]


def test_strike_on_a_protected_site_is_denied_at_the_gate(rack1):
    node = rack1.nodes[0]
    r = strike(rack1, node, SCHOOL)
    assert not r["ok"] and r["why"].startswith(reasons.GATE_CONSTRAINT) and "denied_list" in r["why"]


def test_strike_on_an_open_field_passes_the_gate_and_the_comparator(rack1):
    node = rack1.nodes[0]
    r = strike(rack1, node, FIELD)
    assert r["ok"], r
    rack1.clock.advance(3)               # the rule's delay
    rack1.heartbeat()
    ep = rack1.endpoints["strike-guidance"]
    ok, why = ep.execute(r["ticket"], "strike", {"target": FIELD, "munition": "gbu-39"})
    assert ok, why


def test_compromised_broker_lies_about_the_target(rack1):
    """The request says 'field'; the aircraft is over the school. The comparator checks the
    device's own navigation against its own list, not the request."""
    node = rack1.nodes[0]
    r = strike(rack1, node, FIELD)
    assert r["ok"]
    rack1.clock.advance(3)
    rack1.heartbeat()
    ep = rack1.endpoints["strike-guidance"]
    ep.sensors["nav_gnss"] = tuple(SCHOOL)
    ep.sensors["nav_inertial"] = tuple(SCHOOL)
    ok, why = ep.execute(r["ticket"], "strike", {"target": FIELD, "munition": "gbu-39"})
    assert not ok and why == reasons.ENDPOINT_TARGET_PROTECTED
    assert ep.state == "no_release"


def test_spoofed_navigation_disagrees_and_is_denied(rack1):
    node = rack1.nodes[0]
    r = strike(rack1, node, FIELD)
    rack1.clock.advance(3)
    rack1.heartbeat()
    ep = rack1.endpoints["strike-guidance"]
    ep.sensors["nav_gnss"] = (37.0, -122.0)
    ep.sensors["nav_inertial"] = (37.4, -122.3)          # inertial says somewhere else
    ok, why = ep.execute(r["ticket"], "strike", {"target": FIELD, "munition": "gbu-39"})
    assert not ok and why == reasons.ENDPOINT_SENSOR_CONFLICT


def test_stale_list_at_the_device_is_a_denial(rack1):
    node = rack1.nodes[0]
    r = strike(rack1, node, FIELD)
    rack1.clock.advance(3)
    rack1.heartbeat()
    ep = rack1.endpoints["strike-guidance"]
    ep.sensors["lists"]["protected-sites"]["stale"] = True
    ok, why = ep.execute(r["ticket"], "strike", {"target": FIELD, "munition": "gbu-39"})
    assert not ok and why == reasons.ENDPOINT_LIST_STALE


def test_release_before_the_delay_is_refused(rack1):
    node = rack1.nodes[0]
    r = strike(rack1, node, FIELD)
    ep = rack1.endpoints["strike-guidance"]
    ok, why = ep.execute(r["ticket"], "strike", {"target": FIELD, "munition": "gbu-39"})
    assert not ok and why == reasons.TICKET_NOT_YET_VALID


def test_no_witness_no_ticket(rack1):
    node = rack1.nodes[0]
    r = rack1.request(node, "strike", {"target": FIELD, "munition": "gbu-39"})
    assert not r["ok"] and r["why"] == reasons.GATE_WITNESS_MISSING


def test_witness_too_risky_no_ticket(rack1):
    node = rack1.nodes[0]
    r = strike(rack1, node, FIELD, risk=0.9)
    assert not r["ok"] and r["why"] == reasons.GATE_WITNESS_RISK


def test_endpoint_with_dead_heartbeat_refuses_everything(rack1):
    node = rack1.nodes[0]
    r = strike(rack1, node, FIELD)
    rack1.clock.advance(10)             # no heartbeat reaches the endpoint
    ep = rack1.endpoints["strike-guidance"]
    ok, why = ep.execute(r["ticket"], "strike", {"target": FIELD, "munition": "gbu-39"})
    assert not ok and why == reasons.ENDPOINT_HEARTBEAT_EXPIRED
