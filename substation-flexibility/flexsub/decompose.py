"""M3: split the load into base / thermal / shiftable events / meal events / routine, without NILM. Parts sum to the actual load."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor as HGB
from .features import calendar_features, weather_features


def _house_features(s, w, cfg):
    idx = s.index
    F = calendar_features(idx, cfg)[["hour", "dow", "is_weekend"]].copy()
    for k in (1, 7, 14):
        F[f"l{k}"] = s.shift(24 * k)
    F["m4"] = pd.concat([s.shift(24 * 7 * k) for k in (1, 2, 3, 4)], axis=1).median(axis=1)
    return pd.concat([F, weather_features(w, cfg)[["temp", "temp_day_mean", "cdd", "rad", "cloud", "is_day"]]], axis=1)


def _is_meal(loc, cfg):
    m = np.zeros(len(loc), dtype=bool)
    for a, b in cfg.meal_hours:
        m |= (loc.hour >= a) & (loc.hour < b)
    return m & (loc.dayofweek < 5) if cfg.meal_weekdays_only else m


def house_parts(s, w, cfg):
    """Per-house: base (always-on level), discrete events above the expected load, split by meal hours."""
    idx = s.index
    loc = idx.tz_convert(cfg.tz)
    F = _house_features(s, w, cfg)
    ok = F.notna().all(axis=1)
    pred = pd.Series(np.nan, index=idx)
    pred[ok] = HGB(loss="quantile", quantile=0.5, **cfg.gbm).fit(F[ok], s[ok]).predict(F[ok])
    a, b = cfg.night_hours
    night = s[(loc.hour >= a) & (loc.hour < b)]
    nd = night.index.tz_convert(cfg.tz).normalize()
    base_d = night.groupby(nd).quantile(cfg.base_quantile).rolling(cfg.base_roll_days, min_periods=3).median()
    base = pd.Series(base_d.reindex(loc.normalize()).values, index=idx).bfill()
    exc = s - pred
    ev = exc.where(exc > cfg.event_threshold_kw, 0.0)
    meal = _is_meal(loc, cfg)
    return pd.DataFrame({"actual": s, "base": np.minimum(base, s), "ev_shift": ev.where(~meal, 0.0),
                         "ev_meal": ev.where(meal, 0.0), "ok": ok})


def decompose_substation(W, w, thermal, cfg):
    """Sum house-level parts, take the thermal part from the aggregate model, allocate sequentially so that the parts sum to the load."""
    parts = [house_parts(W[h], w, cfg) for h in W.columns]
    ok = parts[0]["ok"]
    S = sum(p[["actual", "base", "ev_shift", "ev_meal"]] for p in parts)
    S = S[ok & thermal.reindex(S.index).notna()]
    th = thermal.reindex(S.index)
    out = pd.DataFrame(index=S.index)
    rem = S["actual"].copy()
    for name, val in (("base", S["base"]), ("thermal", th), ("ev_shift", S["ev_shift"]), ("ev_meal", S["ev_meal"])):
        a = np.minimum(val.clip(lower=0), rem)
        out[name] = a
        rem = rem - a
    out["routine"] = rem
    out["actual"] = S["actual"]
    return out
