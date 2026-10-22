"""M2: thermal load = prediction with actual weather minus prediction with neutral weather (leave-one-day-out, so the model never sees the day it explains)."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor as HGB


def thermal_loo(y, X, Xn, days, cfg):
    idx = y.index
    ok = y.notna() & X["lag7d"].notna()
    out = pd.Series(np.nan, index=idx)
    for D in days:
        te = (idx >= D) & (idx < D + pd.Timedelta(days=1)) & ok
        tr = ok & ~((idx >= D) & (idx < D + pd.Timedelta(days=1)))
        if te.sum() == 0 or tr.sum() < 24 * 14:
            continue
        m = HGB(loss="quantile", quantile=0.5, **cfg.gbm).fit(X[tr], y[tr])
        out[te] = m.predict(X[te]) - m.predict(Xn[te])
    return out.clip(lower=0)
