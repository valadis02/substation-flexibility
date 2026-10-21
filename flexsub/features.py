import numpy as np
import pandas as pd


def _loc(idx, cfg):
    return idx.tz_convert(cfg.tz)


def calendar_features(idx, cfg):
    loc = _loc(idx, cfg)
    F = pd.DataFrame(index=idx)
    F["hour_sin"] = np.sin(2 * np.pi * loc.hour / 24)
    F["hour_cos"] = np.cos(2 * np.pi * loc.hour / 24)
    F["hour"] = loc.hour
    F["dow"] = loc.dayofweek
    F["is_weekend"] = (loc.dayofweek >= 5).astype(int)
    hol = pd.to_datetime(list(cfg.holidays)).date if cfg.holidays else []
    F["holiday"] = np.isin(loc.date, hol).astype(int)
    return F


def load_features(y, cfg):
    """History features. Everything is known at 00:00 of the target day (lags >= 1 day)."""
    idx = y.index
    day = _loc(idx, cfg).normalize()
    lag = lambda s, k: s.shift(24 * k)
    F = pd.DataFrame(index=idx)
    for k in (1, 2, 3, 7, 14, 21, 28):
        F[f"lag{k}d"] = lag(y, k)
    L4 = F[["lag7d", "lag14d", "lag21d", "lag28d"]]
    F["mean4w"], F["max4w"], F["min4w"], F["std4w"] = L4.mean(axis=1), L4.max(axis=1), L4.min(axis=1), L4.std(axis=1)
    F["mean7d_samehour"] = F[[f"lag{k}d" for k in (1, 2, 3, 7)]].mean(axis=1)
    g = pd.Series(y.values, index=day)
    dmean = pd.Series(g.groupby(level=0).transform("mean").values, index=idx)
    dmax = pd.Series(g.groupby(level=0).transform("max").values, index=idx)
    dmin = pd.Series(g.groupby(level=0).transform("min").values, index=idx)
    F["prevday_mean"], F["prevday_max"], F["prevday_min"] = lag(dmean, 1), lag(dmax, 1), lag(dmin, 1)
    return F


def weather_features(w, cfg, temp_override=None):
    """Weather features. `temp_override` (e.g. a constant 20 deg C) builds the counterfactual 'neutral weather' used for the thermal part."""
    idx = w.index
    day = _loc(idx, cfg).normalize()
    t = w["temp"] if temp_override is None else pd.Series(float(temp_override), index=idx)
    tg = pd.Series(t.values, index=day)
    F = pd.DataFrame(index=idx)
    F["temp"], F["rh"], F["cloud"], F["rad"], F["is_day"] = t, w["rh"], w["cloud"], w["rad"], w["is_day"]
    F["temp_day_mean"] = pd.Series(tg.groupby(level=0).transform("mean").values, index=idx)
    F["temp_day_max"] = pd.Series(tg.groupby(level=0).transform("max").values, index=idx)
    F["temp_prevday_mean"] = F["temp_day_mean"].shift(24)
    F["cdd"] = np.maximum(t - cfg.cdd_base, 0)
    F["hdd"] = np.maximum(cfg.hdd_base - t, 0)
    F["temp_lag3h"] = t.shift(3)
    return F


def build(y, w, cfg, neutral=False):
    return pd.concat([calendar_features(y.index, cfg), load_features(y, cfg),
                      weather_features(w, cfg, temp_override=cfg.neutral_temp if neutral else None)], axis=1)
