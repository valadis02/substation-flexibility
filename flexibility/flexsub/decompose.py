"""M3: split the substation load into base / weather-dependent / shiftable / routine, without NILM.
Parts sum to the actual load.

Per home (smart-meter data of that home only):
  base       always-on level: low quantile of the home's load in its own lowest-load hours of the day
  ev         EV charging (M4, `ev.ev_home`): long high-power runs, after removing the home's weather load
  shiftable  discrete appliance events found from the data only (`shiftable.events_home`, T3 v2 design A), after
             removing the home's weather-dependent load (M2 fitted on the home); EV hours excluded
Substation:
  weather-dependent load from the aggregate (M2), allocated after the base; then EV; then shiftable; the rest is routine.
"""
import numpy as np
import pandas as pd
from . import features, thermal_dd, shiftable, ev as m6


def _home_weather_load(s, w, tz):
    ok = (s.notna() & w["temp"].notna()).to_numpy()
    out = pd.Series(0.0, index=s.index)
    if ok.sum() < 24 * 28:
        return out
    day = s.index.tz_convert(tz).normalize()
    band = features.balance_points(w["temp"].groupby(day).mean(), s.groupby(day).mean())
    if not np.isnan(band[0]):
        out[ok] = thermal_dd.fit_predict(s, w, tz, band, ok, ok, gate=True)
    return out


def house_parts(s, w, cfg):
    """Per-house parts: base (always-on level) and shiftable appliance events."""
    idx = s.index
    loc = idx.tz_convert(cfg.tz)
    hourly_mean = s.groupby(loc.hour).mean()
    low_hours = hourly_mean.nsmallest(cfg.base_hours).index                  # the home's own quietest hours
    night = s[np.isin(loc.hour, low_hours)]
    nd = night.index.tz_convert(cfg.tz).normalize()
    base_d = night.groupby(nd).quantile(cfg.base_quantile).rolling(cfg.base_roll_days, min_periods=3).median()
    base = pd.Series(base_d.reindex(loc.normalize()).values, index=idx).bfill()
    wl = _home_weather_load(s, w, cfg.tz)
    ev, ev_mask = m6.ev_home(s, k=cfg.ev_k, gate=cfg.ev_gate, max_cv=cfg.ev_max_cv, weather_load=wl)
    sh = shiftable.events_home(s, weather_load=wl).where(~ev_mask, 0.0)       # an EV hour is not also an appliance event
    ok = s.notna() & sh.notna() & ev.notna()
    return pd.DataFrame({"actual": s, "base": np.minimum(base, s), "ev": ev.fillna(0.0), "shiftable": sh.fillna(0.0), "ok": ok,
                         "ev_mask": ev_mask.fillna(False).astype(bool)})


def decompose_substation(W, w, thermal, cfg):
    """Sum house-level parts, take the weather-dependent part from the aggregate model, allocate sequentially so that
    the parts sum to the load."""
    parts = [house_parts(W[h], w, cfg) for h in W.columns]
    ok = pd.concat([p["ok"] for p in parts], axis=1).all(axis=1)
    S = sum(p[["actual", "base", "ev", "shiftable"]] for p in parts)
    S = S[ok & thermal.reindex(S.index).notna()]
    th = thermal.reindex(S.index)
    out = pd.DataFrame(index=S.index)
    rem = S["actual"].copy()
    for name, val in (("base", S["base"]), ("thermal", th), ("ev", S["ev"]), ("shiftable", S["shiftable"])):
        a = np.minimum(val.clip(lower=0), rem)
        out[name] = a
        rem = rem - a
    out["routine"] = rem
    out["actual"] = S["actual"]
    # EV sessions per home, for the EV part of the envelope (M5, flexsub.flexibility)
    out.attrs["ev_sessions"] = {h: m6.sessions(p["ev"], p["ev_mask"], cfg.tz) for h, p in zip(W.columns, parts) if p["ev_mask"].any()}
    return out
