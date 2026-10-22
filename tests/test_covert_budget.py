"""P3: the covert-channel budget. A reference monitor controls what may flow, not what the pattern of
permitted traffic says. This models the tightest serviceable policy (the one in make_policy_image)
and bounds the bytes per hour an adversary controlling the model could move out through allowed
channels. The number is pinned; a policy change that raises it fails the test.

Channels, each bounded from the policy image itself (not from constants copied here):
  1. content of permitted responses: the output byte budget per window (the adversary chooses the bytes).
  2. response length: log2 of the compositions of that budget over the query budget. Already inside
     channel 1 (the same bytes), so it is reported and not added.
  3. timing of permitted requests: per rate window of w seconds at resolution r, at most `max` events,
     so log2 sum_{k<=max} C(w/r, k) bits per window; an upper bound (tumbling windows admit more
     patterns than sliding ones). Taken for the payments rule and for the output queries.
  4. choice among allowed peers: log2(peers) bits per permitted peer-addressed event.
Channels 3 and 4 are summed, which over-counts (one event can carry both) and so stays an upper bound.
The one-time burst the governor tolerates before it alarms (unpresented_bytes) is reported apart: it is
not a rate, because the alarm blocks the output path afterwards.
"""
import math

from govsim.cluster import build_rack

HOUR = 3600
TIMING_RESOLUTION_S = 0.001          # assumption: an adversary can place a request to within 1 ms
PINNED_BYTES_PER_HOUR = 209_300      # the number stated in docs/05-threat-model.md
WEIGHTS_70B_FP16 = 140e9             # bytes
WEIGHTS_1T_FP8 = 1e12                # bytes, a frontier-scale bound
PRACTICAL_HOURS = 24 * 365           # "practical time": one year


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


def model(image, peers):
    rules = {r["id"]: r for r in image["rules"]}
    ob = rules["model.output"]["output_budget"]
    scale = HOUR / ob["window_s"]
    content = ob["bytes"] * scale                                    # bytes/hour in the permitted responses
    length_bits = _log2_choose(ob["bytes"] + ob["queries"] - 1, ob["queries"] - 1) * scale
    pay = rules["payments.transfer.small"]["rate"]
    out_timing = timing_bits_per_hour(ob["queries"], ob["window_s"])
    pay_timing = timing_bits_per_hour(pay["max"], pay["window_s"])
    pay_events = pay["max"] * HOUR / pay["window_s"]
    peer_bits = pay_events * math.log2(peers)
    side_bits = out_timing + pay_timing + peer_bits
    return {"content_bytes": content, "length_bits": length_bits, "out_timing_bits": out_timing,
            "pay_timing_bits": pay_timing, "peer_bits": peer_bits,
            "total_bytes_per_hour": math.ceil(content + side_bits / 8),
            "burst_bytes": ob["unpresented_bytes"]}


def _tightest():
    rack = build_rack(4, "rack")
    return model(rack.make_policy_image(1), peers=len(rack.nodes) - 1)


def test_the_number_is_pinned_and_a_looser_policy_raises_it():
    m = _tightest()
    assert m["total_bytes_per_hour"] <= PINNED_BYTES_PER_HOUR, m
    assert m["total_bytes_per_hour"] > 0.9 * PINNED_BYTES_PER_HOUR, ("pin is stale, tighten it", m)
    rack = build_rack(4, "rack")
    more_bytes = model(rack.make_policy_image(1, output_bytes=400_000), peers=3)
    more_queries = model(rack.make_policy_image(1, output_queries=500), peers=3)
    assert more_bytes["total_bytes_per_hour"] > PINNED_BYTES_PER_HOUR
    assert more_queries["total_bytes_per_hour"] > m["total_bytes_per_hour"]


def test_content_dominates_and_side_channels_are_small():
    m = _tightest()
    side = m["total_bytes_per_hour"] - m["content_bytes"]
    assert side < 0.5 * m["content_bytes"], m
    assert m["length_bits"] / 8 < m["content_bytes"]          # length is inside the byte budget, not extra


def test_burst_before_the_alarm_is_one_time(rack1):
    from govsim import reasons
    node = rack1.nodes[0]
    for _ in range(200):
        node.gpu.emit("s", b"x" * 10_000)                     # 2 MB attempted
    rack1.tick()
    assert reasons.OUTPUT_UNPRESENTED in node.governor.alarms
    assert node.gpu.emit("s", b"x") is None                   # no second burst: the path is blocked
    assert _tightest()["burst_bytes"] == 1 << 20


def test_weights_do_not_leave_in_practical_time():
    """The disproof condition: exfiltration in practical time under a policy that still serves."""
    rate = _tightest()["total_bytes_per_hour"]
    for size in (WEIGHTS_70B_FP16, WEIGHTS_1T_FP8):
        assert size / rate > 10 * PRACTICAL_HOURS, (size, rate)
