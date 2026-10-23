"""Shiftable appliance load (washing machine, tumble dryer, dishwasher) without sub-metering in the target network.

Two alternatives are kept side by side until one is chosen (see experiments/RESULTS.md, T3 v2):

A. `events` - data only. Per home, the expected load is the 60th percentile of the same hour over the previous 14
   days (v0.8; the median until v0.7 counted ordinary activity - cooking, heating - as appliance events); an
   hour is an appliance event if the excess over it is larger than k robust standard deviations of that home's own
   excess (k = 3), and the run of such hours is short (<= max_run_h hours, an appliance cycle; longer runs are AC, EV,
   heating). Shiftable load = the excess in those hours.

B. `profile` - a bank of public sub-metered datasets. For each dataset the bank stores, by hour x day type, the share
   of the load that is shiftable appliances, the shiftable kW per home, and a load-shape signature (mean load per
   home, normalised). For a target substation, the dataset(s) whose signature is closest to the substation's own load
   shape are used: share x substation load ("share"), or kW per home x number of homes ("abs").
"""
import numpy as np
import pandas as pd


def _key(idx, tz):
    loc = idx.tz_convert(tz)
    return pd.Series(loc.hour * 2 + (loc.dayofweek >= 5), index=idx)          # 0..47: hour x (weekday, weekend)


# ---------------- A: events from the data only ----------------
def events_home(y, k=3.0, max_run_h=3, window_days=14, weather_load=None, base_quantile=0.6):
    """Hourly shiftable estimate (kW) for one home from its own hourly load (index tz-aware, complete hourly).
    weather_load: optional weather-dependent load (M2) of the home, removed before looking for events.
    base_quantile: quantile of the same hour over the previous window_days used as the expected load."""
    if weather_load is not None:
        y = y - weather_load.reindex(y.index).fillna(0)
    base = y.groupby(y.index.hour).transform(lambda s: s.rolling(window_days, min_periods=7).quantile(base_quantile).shift(1))
    exc = y - base
    mad = (exc - exc.rolling(24 * window_days, min_periods=24 * 7).median()).abs().rolling(24 * window_days, min_periods=24 * 7).median().shift(1)
    thr = k * 1.4826 * mad
    flag = (exc > thr) & thr.notna()
    run_id = (flag != flag.shift()).cumsum()
    run_len = flag.groupby(run_id).transform("size")
    keep = flag & (run_len <= max_run_h)
    return exc.where(keep, 0.0).clip(lower=0).where(base.notna())


# ---------------- B: profile bank ----------------
def bank_entry(Y, T, tz):
    """Y: hourly load per home (columns), T: hourly true shiftable per home, same index/columns. Pooled over homes."""
    m = Y.notna() & T.notna()
    k = _key(Y.index, tz)
    y, t, n = Y.where(m).sum(axis=1), T.where(m).sum(axis=1), m.sum(axis=1)
    ok = n > 0
    share = t[ok].groupby(k[ok]).sum() / y[ok].groupby(k[ok]).sum()
    kw_home = (t[ok] / n[ok]).groupby(k[ok]).mean()
    sig = (y[ok] / n[ok]).groupby(k[ok]).mean()
    return dict(share=share.reindex(range(48)), kw_home=kw_home.reindex(range(48)), signature=sig.reindex(range(48)) / sig.mean())


def signature(y, tz):
    k = _key(y.index, tz)
    s = y.groupby(k).mean().reindex(range(48))
    return s / s.mean()


def bank_weights(sig, bank, select="shape"):
    names = list(bank)
    if select == "mean":
        return pd.Series(1.0 / len(names), index=names)
    c = pd.Series({n: float(np.corrcoef(sig.fillna(sig.mean()), bank[n]["signature"].fillna(1))[0, 1]) for n in names})
    if select == "shape":                                  # nearest dataset
        return (c == c.max()).astype(float) / (c == c.max()).sum()
    if select == "weighted":                               # similarity-weighted (no tuning constant: squared positive corr)
        w = c.clip(lower=0) ** 2
        return w / w.sum() if w.sum() > 0 else pd.Series(1.0 / len(names), index=names)
    raise ValueError(select)


def profile_estimate(y, n_homes, bank, tz, select="shape", level="share"):
    """Shiftable kW of a substation from its total load y (hourly, tz-aware) and the bank (other datasets only)."""
    wts = bank_weights(signature(y, tz), bank, select)
    col = "share" if level == "share" else "kw_home"
    prof = sum(wts[n] * bank[n][col].fillna(0) for n in wts.index)
    k = _key(y.index, tz)
    p = k.map(prof).astype(float)
    return (y * p) if level == "share" else (p * n_homes), wts


def profile_scaled(y, n_homes, bank, tz, level_energy, select="mean"):
    """Timing from the bank, level from the substation's own data: the bank's kW-per-home profile is rescaled so that
    its daily energy equals `level_energy` (kWh/day, e.g. the daily energy of the data-only events, method A)."""
    e, wts = profile_estimate(y, n_homes, bank, tz, select=select, level="abs")
    day = y.index.tz_convert(tz).normalize()
    scale = float(level_energy) / float(e.groupby(day).sum().mean()) if e.sum() > 0 else 0.0
    return e * scale, wts


def load_bank(path="data/profile_bank.json"):
    import json
    raw = json.load(open(path))
    return {n: {k: pd.Series(v, index=range(48), dtype=float) for k, v in e.items() if k != "homes"} for n, e in raw.items()}
