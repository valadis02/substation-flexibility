"""M2 alternatives that can extrapolate the counterfactual (T2 v3).

A tree model cannot predict a July day in Texas at 20 C because it has never seen one, so "prediction at neutral
temperature" still contains AC and the thermal part is underestimated (T2 v2). Here the thermal part is an explicit
degree-day component, linear in the distance of temperature from the balance points, so the counterfactual
(temperature inside the band [Th, Tc]) is simply "degree-days = 0" and needs no extrapolation.

Degree-day design (all relative to the balance points Th, Tc):
  cdd_h  = max(T_t - Tc, 0)            hourly temperature
  cdd_d  = max(Tmean_day - Tc, 0)      daily mean (building inertia, behaviour over the day)
  cdd_d1 = max(Tmean_prev_day - Tc, 0) previous day (heat stored in the building)
  and the same with Th for heating; each interacted with hour of day (24 profiles) so that the response can differ
  between afternoon and night. Optional solar term (shortwave radiation x cdd_h).

Model (dd_linear, adopted in v0.5 after T2 v3): y = hour x day-type profile + annual harmonics + degree-day terms
(ridge). Weather-dependent load = the degree-day terms.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge


def dd_terms(w, tz, band, solar=True):
    loc = w.index.tz_convert(tz)
    t = w["temp"]
    day = loc.normalize()
    tmean = pd.Series(t.groupby(day).transform("mean").values, index=w.index)
    tprev = tmean.shift(24)
    th, tc = band
    base = {"cdd_h": (t - tc).clip(lower=0), "cdd_d": (tmean - tc).clip(lower=0), "cdd_d1": (tprev - tc).clip(lower=0),
            "hdd_h": (th - t).clip(lower=0), "hdd_d": (th - tmean).clip(lower=0), "hdd_d1": (th - tprev).clip(lower=0)}
    if solar and "rad" in w and w["rad"].notna().any():
        base["sol_cdd"] = (w["rad"].fillna(0) / 1000.0) * base["cdd_h"]
    hours = loc.hour
    cols = {}
    for k, v in base.items():
        v = v.fillna(0).to_numpy()
        cols[k] = v                                   # common slope
        for h in range(0, 24, 3):                     # 8 three-hour blocks: shape of the response over the day
            cols[f"{k}_h{h}"] = v * ((hours >= h) & (hours < h + 3))
    return pd.DataFrame(cols, index=w.index)


def base_terms(idx, tz, lat=None):
    loc = idx.tz_convert(tz)
    hours, wk = loc.hour, (loc.dayofweek >= 5)
    cols = {f"h{h}_{d}": ((hours == h) & (wk == (d == "we"))).astype(float) for h in range(24) for d in ("wd", "we")}
    doy = loc.dayofyear.to_numpy()
    for k in (1, 2):
        cols[f"s{k}"], cols[f"c{k}"] = np.sin(2 * np.pi * k * doy / 365.25), np.cos(2 * np.pi * k * doy / 365.25)
    return pd.DataFrame(cols, index=idx)


def significance(y, w, tz, band, train, t_crit=2.0, nw_lags=7):
    """Is there a cooling / heating response at all? Daily mean load on day-of-week dummies, annual harmonics and
    daily cooling/heating degree-days; t-statistics with Newey-West standard errors (days are autocorrelated).
    Returns (cooling_significant, heating_significant). Uses only load and temperature of the training rows."""
    loc = y.index.tz_convert(tz)
    day = loc.normalize()
    df = pd.DataFrame({"y": y.where(train), "t": w["temp"].where(train)}).groupby(day).mean().dropna()
    if len(df) < 28:
        return False, False
    th, tc = band
    di = pd.DatetimeIndex(df.index)
    X = [np.ones(len(df))] + [(di.dayofweek == k).astype(float) for k in range(1, 7)]
    doy = di.dayofyear.to_numpy()
    X += [np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)]
    cdd, hdd = (df.t - tc).clip(lower=0).to_numpy(), (th - df.t).clip(lower=0).to_numpy()
    cols = {}
    if cdd.std() > 0:
        cols["c"] = len(X); X.append(cdd)
    if hdd.std() > 0:
        cols["h"] = len(X); X.append(hdd)
    X = np.column_stack(X)
    v = df.y.to_numpy()
    beta, *_ = np.linalg.lstsq(X, v, rcond=None)
    e = v - X @ beta
    XtXi = np.linalg.pinv(X.T @ X)
    S = (X * e[:, None]).T @ (X * e[:, None])
    for L in range(1, nw_lags + 1):
        wgt = 1 - L / (nw_lags + 1)
        G = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None])
        S += wgt * (G + G.T)
    se = np.sqrt(np.maximum(np.diag(XtXi @ S @ XtXi), 1e-12))
    sig = lambda k: k in cols and beta[cols[k]] / se[cols[k]] > t_crit      # one-sided: load must rise
    return sig("c"), sig("h")


def fit_predict(y, w, tz, band, train, test, alpha=1.0, gate=False):
    """Fit on rows `train` (bool array); return the weather-dependent load (kW) on rows `test`: the degree-day part,
    i.e. actual minus the counterfactual with temperature inside the balance-point band.
    gate=True: drop the cooling and/or heating terms whose daily response is not significant (`significance`)."""
    D = dd_terms(w, tz, band)
    if gate:
        c_ok, h_ok = significance(y, w, tz, band, train)
        drop = [c for c in D.columns if (c.startswith(("cdd", "sol")) and not c_ok) or (c.startswith("hdd") and not h_ok)]
        D = D.drop(columns=drop)
        if D.shape[1] == 0:
            return np.zeros(int(np.sum(test)))
    B = base_terms(y.index, tz)
    X = pd.concat([B, D], axis=1).to_numpy()
    r = Ridge(alpha=alpha, fit_intercept=False).fit(X[train], y.to_numpy()[train])
    return D.to_numpy()[test] @ r.coef_[B.shape[1]:]
