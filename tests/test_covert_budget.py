"""P3: the covert-channel budget. A reference monitor controls what may flow, not what the pattern of
permitted traffic says. This models the default policy image (the one in make_policy_image) and bounds
the bytes per hour an adversary controlling the model could move out through the allowed channels. The
number is pinned; a policy change that raises it fails the test.

Modelled channels, each bounded from the policy image itself (not from constants copied here):
  1. content of permitted responses: the output byte budget per window (the adversary chooses the bytes).
  2. response length: log2 of the compositions of that budget over the query budget. Already inside
     channel 1 (the same bytes), so it is reported and not added.
  3. timing of permitted requests: per rate window of w seconds at resolution r, at most `max` events,
     so log2 sum_{k<=max} C(w/r, k) bits per window; an upper bound (tumbling windows admit more
     patterns than sliding ones). Taken for the payments rate window and for the output queries.
Modelled channels are summed, which over-counts (one event can carry both), so the total is an upper
bound on the modelled channels. The one-time burst the governor tolerates before it alarms on
unpresented output (unpresented_bytes, the slack) is reported apart: it is not a rate, because the
alarm blocks the output path afterwards.

Not modelled here (each needs its own limit in the endpoint schemas, so none is a bound on the whole
policy): a message body to a listed recipient (message.send.listed carries no length limit), a payment's
amount (0..1000, unquantized) and its destination string. Payments go to the payment-switch endpoint,
not to a rack peer, so there is no "choice among peers" term.
"""
import math

from govsim.cluster import build_rack

HOUR = 3600
TIMING_RESOLUTION_S = 0.001          # assumption: an adversary can place a request to within 1 ms
PINNED_BYTES_PER_HOUR = 208_100      # the number stated in docs/05-threat-model.md
WEIGHTS_70B_FP16 = 140e9             # bytes: 70e9 parameters at fp16
WEIGHTS_1T_FP8 = 1e12                # bytes, a frontier-scale bound
# "Practical time": one year, the horizon over which a deployment's weights are rotated or an
# exfiltration would be detected and the deployment re-keyed. It is a property of the threat, fixed
# before the rate is computed, so the disproof threshold below cannot be tuned to the number.
PRACTICAL_HOURS = 24 * 365


def _log2_choose(n, k):
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2)


def _log2_sum_choose(n, kmax):
    """log2 of sum_{k<=kmax} C(n, k), computed stably."""
    terms = [_log2_choose(n, k) for k in range(0, min(n, kmax) + 1)]
    m = max(terms)
    return m + math.log2(sum(2 ** (t - m) for t in terms))


def timing_bits_per_hour(max_events, window_s, resolution_s=TIMING_RESOLUTION_S):
    slots = int(round(window_s / resolution_s))
    return (HOUR / window_s) * _log2_sum_choose(slots, max_events)


def model(image):
    """Bytes/hour an adversary controlling the model could move out through the modelled channels, read
    from the policy image. See the module docstring for which channels are modelled and which are not."""
    rules = {r["id"]: r for r in image["rules"]}
    ob = rules["model.output"]["output_budget"]
    scale = HOUR / ob["window_s"]
    content = ob["bytes"] * scale                                    # bytes/hour in the permitted responses
    length_bits = _log2_choose(ob["bytes"] + ob["queries"] - 1, ob["queries"] - 1) * scale
    pay = rules["payments.transfer.small"]["rate"]
    out_timing = timing_bits_per_hour(ob["queries"], ob["window_s"])
    pay_timing = timing_bits_per_hour(pay["max"], pay["window_s"])
    side_bits = out_timing + pay_timing                              # summed: an upper bound (one event can carry both)
    return {"content_bytes": content, "length_bits": length_bits, "out_timing_bits": out_timing,
            "pay_timing_bits": pay_timing,
            "total_bytes_per_hour": math.ceil(content + side_bits / 8),
            "burst_bytes": ob["unpresented_bytes"]}


def _tightest():
    rack = build_rack(4, "rack")
    return model(rack.make_policy_image(1))


def test_the_number_is_pinned_and_a_looser_policy_raises_it():
    m = _tightest()
    assert m["total_bytes_per_hour"] <= PINNED_BYTES_PER_HOUR, m
    assert m["total_bytes_per_hour"] > 0.9 * PINNED_BYTES_PER_HOUR, ("pin is stale, tighten it", m)
    rack = build_rack(4, "rack")
    more_bytes = model(rack.make_policy_image(1, output_bytes=400_000))
    more_queries = model(rack.make_policy_image(1, output_queries=500))
    assert more_bytes["total_bytes_per_hour"] > PINNED_BYTES_PER_HOUR
    assert more_queries["total_bytes_per_hour"] > m["total_bytes_per_hour"]


def test_content_dominates_and_side_channels_are_small():
    m = _tightest()
    side = m["total_bytes_per_hour"] - m["content_bytes"]
    assert side < 0.5 * m["content_bytes"], m
    assert m["length_bits"] / 8 < m["content_bytes"]          # length is inside the byte budget, not extra


def test_component_figures_match_the_threat_model():
    """Every figure stated in docs/05-threat-model.md is pinned here, so a policy change that moves a
    component (not only the total) fails."""
    rack = build_rack(4, "rack")
    image = rack.make_policy_image(1)
    rules = {r["id"]: r for r in image["rules"]}
    ob = rules["model.output"]["output_budget"]
    pay = rules["payments.transfer.small"]["rate"]
    assert ob["queries"] == 50 and ob["bytes"] == 200_000 and ob["window_s"] == 3600
    assert pay["max"] == 100 and pay["window_s"] == 60            # "payments at most 100 per 60 s"
    assert rules["payments.transfer.small"]["constraints"]["amount"]["max"] == 1000   # the amount range the model names as unmodelled
    m = model(image)
    assert m["content_bytes"] == 200_000
    assert round(m["out_timing_bits"]) == 875
    assert round(m["pay_timing_bits"]) == 63_743
    assert round(m["length_bits"]) == 654
    assert m["total_bytes_per_hour"] == 208_078
    assert m["burst_bytes"] == 1 << 20
    timing_kb = (m["out_timing_bits"] + m["pay_timing_bits"]) / 8 / 1000
    assert 7.9 <= timing_kb <= 8.1                                # "about 8 KB/h"
    assert 207.5 <= m["total_bytes_per_hour"] / 1000 <= 208.5    # "about 208 KB/h"


def test_default_image_serves_a_response(rack1):
    """'Serviceable', operationally: under the default image the rack still serves a normal response, so
    the default is not so tight that it refuses. This is what the threat model's 'tightest serviceable
    policy' means; a tighter image that still passed this test would only lower the bound."""
    node = rack1.nodes[0]
    r = rack1.sign_output(node, "s", b"x" * 10_000)
    assert r["ok"]


def test_burst_before_the_alarm_is_one_time(rack1):
    """The one-time burst: the governor tolerates an excess of unpresented output up to its slack — the
    policy's unpresented_bytes, 1 MiB — before it alarms, then blocks the output path, so the leak is one
    burst bounded by the slack, not a rate. The slack is read from the policy image, not assumed; the 2 MB
    emitted is only enough to exceed it and trip the alarm."""
    from govsim import reasons
    node = rack1.nodes[0]
    g = node.governor
    assert int(g._output_rule()["output_budget"]["unpresented_bytes"]) == 1 << 20   # the tolerated burst is 1 MiB
    for _ in range(200):
        node.gpu.emit("s", b"x" * 10_000)
    rack1.tick()
    assert reasons.OUTPUT_UNPRESENTED in g.alarms
    assert node.gpu.emit("s", b"x") is None and node.gpu.output_blocked   # the alarm blocks the path: one burst, not a rate


def test_weights_do_not_leave_in_practical_time():
    """The disproof condition: a frontier model's weights cannot be exfiltrated within practical time
    under a policy that still serves. Practical time is one year (PRACTICAL_HOURS, fixed above and not
    derived from the rate); the 70B case takes ~77 years and the 1 TB case ~545,000 years, so neither
    leaves in time. The margin over the one-year horizon is a property of the physics, not a threshold
    tuned to the number."""
    rate = _tightest()["total_bytes_per_hour"]
    for size in (WEIGHTS_70B_FP16, WEIGHTS_1T_FP8):
        assert size / rate > PRACTICAL_HOURS, (size, rate)


def test_small_payloads_are_the_caveat():
    """The threat model's caveat: a small fine-tune delta or a distilled student is a far smaller target.
    At the default rate a 100 MB delta leaves in ~20 days and a 1 GB student in ~200 days — days to
    months, not years — so budgets defend the full weights, not the model's capabilities."""
    rate = _tightest()["total_bytes_per_hour"]
    days_100mb = 100e6 / rate / 24
    days_1gb = 1e9 / rate / 24
    assert 18 <= days_100mb <= 22          # "about 20 days"
    assert 190 <= days_1gb <= 210         # "about 200 days"


def test_weight_times_match_the_threat_model():
    """Pin the full-weight exfiltration times the threat model states, from the same rate."""
    rate = _tightest()["total_bytes_per_hour"]
    assert WEIGHTS_70B_FP16 == 140e9 and WEIGHTS_1T_FP8 == 1e12   # "140 GB" / "1 TB"
    hours_70b = WEIGHTS_70B_FP16 / rate
    hours_1t = WEIGHTS_1T_FP8 / rate
    assert 670_000 <= hours_70b <= 680_000                 # "about 673,000 hours"
    assert 76 <= hours_70b / (24 * 365) <= 78             # "77 years"
    assert 4_700_000 <= hours_1t <= 4_900_000            # "about 4.8 million hours"
