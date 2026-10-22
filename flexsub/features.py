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
    if getattr(cfg, "seasonal_features", False):
        doy = loc.dayofyear.to_numpy()
        F["doy_sin"], F["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
        F["day_length"] = day_length(doy, cfg.latitude)
    return F


def day_length(doy, lat):
    """Hours of daylight (standard astronomical approximation)."""
    decl = np.deg2rad(23.44) * np.sin(2 * np.pi * (284 + doy) / 365)
    x = np.clip(-np.tan(np.deg2rad(lat)) * np.tan(decl), -1, 1)
    return 24 / np.pi * np.arccos(x)


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
    if temp_override is None:
        t = w["temp"]
    elif isinstance(temp_override, (tuple, list)):          # neutral band: remove only what lies outside it
        t = w["temp"].clip(lower=temp_override[0], upper=temp_override[1])
    else:
        t = pd.Series(float(temp_override), index=idx)
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
    """Feature matrix. `y` must be on a complete hourly index (lags are row shifts). `w=None` -> no weather features.
    Columns that are entirely NaN (e.g. cloud/radiation when the dataset has no such data) are dropped."""
    parts = [calendar_features(y.index, cfg), load_features(y, cfg)]
    if w is not None:
        parts.append(weather_features(w, cfg, temp_override=neutral_value(cfg) if neutral else None))
    X = pd.concat(parts, axis=1)
    return X.loc[:, X.notna().any()]


def neutral_value(cfg):
    band = getattr(cfg, "neutral_band", None)
    return tuple(band) if band is not None else cfg.neutral_temp


def balance_points(temp_daily, load_daily, grid=np.arange(10, 30.01, 0.5)):
    """Heating and cooling balance points from daily means: fit load = a + bh*max(Th - T, 0) + bc*max(T - Tc, 0)
    with Th <= Tc (dead band between them); returns (Th, Tc) with the smallest squared error.
    Uses only load and temperature, so it can be run on any substation."""
    ok = temp_daily.notna() & load_daily.notna()
    t, v = temp_daily[ok].to_numpy(), load_daily[ok].to_numpy()
    best = (np.inf, (np.nan, np.nan))
    for th in grid:
        for tc in grid[grid >= th]:
            A = np.c_[np.ones_like(t), np.maximum(th - t, 0), np.maximum(t - tc, 0)]
            coef, *_ = np.linalg.lstsq(A, v, rcond=None)
            if coef[1] < 0 or coef[2] < 0:          # load must not fall when it gets colder below Th / hotter above Tc
                continue
            sse = float(((A @ coef - v) ** 2).sum())
            if sse < best[0]:
                best = (sse, (float(th), float(tc)))
    return best[1]
