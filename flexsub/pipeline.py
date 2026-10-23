import numpy as np
import pandas as pd
from . import features, baseline, thermal, decompose, flexibility, ev as m6


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
    X = features.build(y, weather, cfg)
    R = baseline.conformal_calibrate(baseline.rolling_origin(y, X, test_days, cfg), cfg)
    th = thermal.thermal_dd_loo(y, weather, test_days, cfg)
    D = decompose.decompose_substation(W, weather, th, cfg)
    F = flexibility.flexibility_by_hour(D, cfg)
    return dict(baseline=R, thermal=th, decomposition=D, flexibility=F,
                flexibility_participation=flexibility.apply_participation(F, cfg.participation if participation is None else participation * response),
                scenarios={} if participation is not None else {(e, r): flexibility.apply_participation(F, e * r) for e, r in cfg.participation_scenarios})


def ev_day_ahead(W, weather, cfg, day, mode="dwell"):
    """M6: actionable EV flexibility for `day` (local date), from data before it only. Returns dict(sessions per EV
    home, scenarios, envelope per hour from local midnight (0..35), base_kw = expected non-EV substation load (same-hour
    mean of the last 14 days, for valley filling), and plan(hours, direction, target_kw=None) -> (per-home
    instructions, aggregate before/after per hour)). Total flexibility of the day = M4 + this envelope."""
    W = W.copy(); W.index = W.index.tz_convert(cfg.tz)
    weather = weather.copy(); weather.index = weather.index.tz_convert(cfg.tz)
    d0 = pd.Timestamp(day).tz_localize(cfg.tz) if pd.Timestamp(day).tzinfo is None else pd.Timestamp(day)
    W, weather = W[W.index < d0], weather[weather.index < d0]
    S, evsum = {}, 0
    for h in W.columns:
        wl = decompose._home_weather_load(W[h], weather, cfg.tz)
        ev, m = m6.ev_home(W[h], k=cfg.ev_k, gate=cfg.ev_gate, max_cv=cfg.ev_max_cv, weather_load=wl)
        evsum = evsum + ev.fillna(0)
        if m.any():
            S[h] = m6.sessions(ev, m, cfg.tz)
    non_ev = (W.sum(axis=1) - evsum)[W.index >= d0 - pd.Timedelta(days=cfg.ev_history_days)]
    hourly = non_ev.groupby(non_ev.index.hour).mean().reindex(range(24)).ffill().bfill().to_numpy()
    base_kw = np.resize(hourly, 36)
    T = m6.typical_day(S, d0, cfg.ev_history_days, mode=mode, dwell_h=cfg.ev_dwell_h)
    return dict(sessions=S, scenarios=T, envelope=m6.envelope(T), base_kw=base_kw,
                plan=lambda hours, direction, target_kw=None, stagger=True:
                    m6.plan(T, hours, direction, target_kw, base_kw=base_kw, stagger=stagger))
