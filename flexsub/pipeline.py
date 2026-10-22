import pandas as pd
from . import features, baseline, thermal, decompose, flexibility


def run(W, weather, cfg, test_days, participation=None, response=1.0):
    """W: hourly kW (index tz-aware, columns = houses); weather: DataFrame(temp, rh, cloud, rad, is_day) on the same index.
    participation: known enrolment share of this substation (e.g. from the DSO's flexibility register) and
    response: share of enrolled homes that respond to an event; the effective factor is participation x response.
    If participation is None, the technical maximum (cfg.participation = 1.0) is returned together with the
    scenarios in cfg.participation_scenarios, keyed by (enrolment, response).
    Returns dict with baseline band (M1), thermal part (M2), decomposition (M3) and flexibility per hour (M4)."""
    W = W.copy(); W.index = W.index.tz_convert(cfg.tz)
    weather = weather.copy(); weather.index = weather.index.tz_convert(cfg.tz)
    y = W.sum(axis=1)
    X, Xn = features.build(y, weather, cfg), features.build(y, weather, cfg, neutral=True)
    R = baseline.conformal_calibrate(baseline.rolling_origin(y, X, Xn, test_days, cfg), cfg)
    th = thermal.thermal_loo(y, X, Xn, test_days, cfg)
    D = decompose.decompose_substation(W, weather, th, cfg)
    F = flexibility.flexibility_by_hour(D, cfg)
    return dict(baseline=R, thermal=th, decomposition=D, flexibility=F,
                flexibility_participation=flexibility.apply_participation(F, cfg.participation if participation is None else participation * response),
                scenarios={} if participation is not None else {(e, r): flexibility.apply_participation(F, e * r) for e, r in cfg.participation_scenarios})
