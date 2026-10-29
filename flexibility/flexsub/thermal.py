"""M2: weather-dependent load = the part of the load explained by temperature beyond the substation's balance points
(degree-day component, `flexsub.thermal_dd`). It is a superset of heating/cooling: any load that changes with the
weather is counted (T2). It may be negative hour by hour; sums over hours/days are what is meaningful."""
import numpy as np
import pandas as pd


def thermal_dd_loo(y, w, days, cfg):
    """M2 v0.5: degree-day thermal component (flexsub.thermal_dd, model dd_linear), balance points estimated from the
    substation's own daily load and temperature, out-of-sample by leaving each day out ."""
    from . import features, thermal_dd
    idx = y.index
    loc = idx.tz_convert(cfg.tz)
    day = loc.normalize()
    ok = (y.notna() & w["temp"].notna()).to_numpy()
    out = pd.Series(np.nan, index=idx)
    tdaily, ydaily = w["temp"].groupby(day).mean(), y.groupby(day).mean()
    for D in days:
        te = ok & (idx >= D) & (idx < D + pd.Timedelta(days=1))
        tr = ok & ~((idx >= D) & (idx < D + pd.Timedelta(days=1)))
        if te.sum() == 0 or tr.sum() < 24 * 28:
            continue
        trd = pd.Index(day[tr]).unique()
        band = features.balance_points(tdaily.reindex(trd), ydaily.reindex(trd))
        if np.isnan(band[0]):
            continue
        out[te] = thermal_dd.fit_predict(y, w, cfg.tz, band, tr, te, gate=True)
    return out
