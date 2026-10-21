"""M1: quantile baseline with conformal calibration, evaluated rolling-origin (retrained each day with data known up to midnight)."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor as HGB


def _fit(X, y, q, cfg):
    return HGB(loss="quantile", quantile=q, **cfg.gbm).fit(X, y)


def rolling_origin(y, X, Xn, test_days, cfg):
    """For each test day D: train on rows before D, predict the day. Xn is the neutral-weather feature matrix (thermal counterfactual)."""
    idx = y.index
    ok = X.notna().all(axis=1)
    rows = []
    for D in test_days:
        tr = ok & (idx < D)
        te = (idx >= D) & (idx < D + pd.Timedelta(days=1)) & ok
        if tr.sum() < 24 * 14 or te.sum() == 0:
            continue
        out = pd.DataFrame(index=idx[te])
        out["actual"] = y[te]
        for q in cfg.quantiles:
            m = _fit(X[tr], y[tr], q, cfg)
            out[f"q{q}"] = m.predict(X[te])
            if q == 0.5:
                out["thermal"] = out["q0.5"] - m.predict(Xn[te])
        rows.append(out)
    return pd.concat(rows)


def conformal_calibrate(R, cfg):
    """Widen the raw [q_lo, q_hi] band by the calibration quantile of past nonconformity scores (only earlier days, window cfg.calib_days)."""
    lo = np.minimum(R[f"q{cfg.quantiles[0]}"], R[f"q{cfg.quantiles[2]}"])
    hi = np.maximum(R[f"q{cfg.quantiles[0]}"], R[f"q{cfg.quantiles[2]}"])
    s = np.maximum(lo - R["actual"], R["actual"] - hi)
    R = R.copy()
    R["raw_lo"], R["raw_hi"], R["cq"] = lo, hi, np.nan
    day = R.index.normalize()
    for D in pd.unique(day):
        past = s[(R.index < D) & (R.index >= D - pd.Timedelta(days=cfg.calib_days))]
        if len(past) >= cfg.calib_min_samples:
            R.loc[day == D, "cq"] = np.quantile(past, cfg.calib_quantile)
    R["cal_lo"], R["cal_hi"] = lo - R["cq"], hi + R["cq"]
    return R
