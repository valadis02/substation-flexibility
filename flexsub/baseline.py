"""M1: quantile baseline with conformal calibration, evaluated rolling-origin (retrained each day with data known up to midnight)."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor as HGB


def _fit(X, y, q, cfg):
    return HGB(loss="quantile", quantile=q, **cfg.gbm).fit(X, y)


def rolling_origin(y, X, test_days, cfg):
    """For each test day D: train on rows before D, predict the day."""
    idx = y.index
    ok = usable_rows(y, X)
    rows, models, last_fit = [], None, None
    for D in test_days:
        te = (idx >= D) & (idx < D + pd.Timedelta(days=1)) & ok
        if te.sum() == 0:
            continue
        if models is None or (D - last_fit).days >= cfg.retrain_days:
            tr = ok & (idx < D)
            if tr.sum() < 24 * 14:
                continue
            cols = X.columns[X[tr].nunique() >= 2]          # features that vary in the training rows
            models = {q: _fit(X.loc[tr, cols], y[tr], q, cfg) for q in cfg.quantiles}
            last_fit = D
        out = pd.DataFrame(index=idx[te])
        out["actual"] = y[te]
        for q, m in models.items():
            out[f"q{q}"] = m.predict(X.loc[te, cols])
        rows.append(out)
    return pd.concat(rows)


def usable_rows(y, X):
    """Rows with a target and a one-week lag; other missing features are left to the model (HGB handles NaN)."""
    if "lag7d" not in X:
        return pd.Series(False, index=y.index)
    return y.notna() & X["lag7d"].notna()


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
