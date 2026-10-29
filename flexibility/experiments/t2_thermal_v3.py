"""HISTORICAL: ran with method v0.3-v0.4 (gradient-boosting M2 with a neutral-temperature counterfactual), which was
removed in v0.5. Results are in experiments/RESULTS.md; to rerun, check out the commit that added this script.
"""
"""T2 v3 (development data only): fixing the underestimation of the thermal part.

Compares, on the same units and folds (leave-one-4-week-block-out; balance points from the training block only):
  gbm_v2    : method v0.4 (gradient boosting with load lags + seasonal features, counterfactual = temperature in band)
  gbm_nolag : same without load-history features (lags carry yesterday's AC)
  dd_linear : hour x day-type profile + annual harmonics + degree-day terms (ridge); thermal = degree-day part
  dd_hybrid : boosting on calendar/season/non-temperature weather + ridge degree-day part, fitted by backfitting
Metrics as T2 v2; the key one is share_ratio = estimated / true thermal energy (1 = no bias).

    python experiments/t2_thermal_v3.py --datasets pecan_austin pecan_newyork pecan_california plegma refit
"""
import argparse, os, sys, time
import numpy as np
import pandas as pd
from dataclasses import replace
from sklearn.ensemble import HistGradientBoostingRegressor as HGB
sys.path.insert(0, os.path.dirname(__file__))
from flexsub import features, thermal_dd
import t2_units as U

ap = argparse.ArgumentParser()
ap.add_argument("--datasets", nargs="+", default=["pecan_austin"])
ap.add_argument("--units", nargs="*", default=None, help="restrict to these unit names (e.g. groups only)")
ap.add_argument("--block-days", type=int, default=28)
ap.add_argument("--models", nargs="+", default=["gbm_v2", "gbm_nolag", "dd_linear", "dd_hybrid"])
a = ap.parse_args()
tag = "_".join(a.datasets) + ("_" + "_".join(a.units).replace("(", "").replace(")", "").replace(">=", "").replace(" ", "") if a.units else "")

rows = []
for ds, name, kind, y, truth, wx, cfg0 in U.units(a.datasets):
    if a.units and name not in a.units:
        continue
    if y.notna().sum() < 24 * 60:
        continue
    y = y[y.first_valid_index():y.last_valid_index()].asfreq("1h")
    w = wx.reindex(y.index); truth = truth.reindex(y.index)
    y.index = y.index.tz_convert(cfg0.tz); w.index = w.index.tz_convert(cfg0.tz); truth.index = y.index
    cfg = replace(cfg0, seasonal_features=True)
    X = features.build(y, w, cfg)
    lagcols = [c for c in X.columns if c.startswith(("lag", "mean4w", "max4w", "min4w", "std4w", "mean7d", "prevday"))]
    ok = (y.notna() & X["lag7d"].notna() & w["temp"].notna()).to_numpy()
    day = y.index.normalize()
    block = ((y.index.tz_localize(None).normalize() - y.index[0].tz_localize(None).normalize()).days // a.block_days).to_numpy()
    tdaily, ydaily = w["temp"].groupby(day).mean(), y.groupby(day).mean()
    est = {m: np.full(len(y), np.nan) for m in a.models}
    t0 = time.time()
    for k in np.unique(block[ok]):
        te, tr = ok & (block == k), ok & (block != k)
        if tr.sum() < 24 * 28:
            continue
        trdays = pd.Index(day[tr]).unique()
        band = features.balance_points(tdaily.reindex(trdays), ydaily.reindex(trdays))
        if np.isnan(band[0]):
            continue
        Xn = features.build(y, w, replace(cfg, neutral_band=band), neutral=True)[X.columns]
        for m in a.models:
            if m in ("gbm_v2", "gbm_nolag"):
                cols = list(X.columns) if m == "gbm_v2" else [c for c in X.columns if c not in lagcols]
                g = HGB(loss="quantile", quantile=0.5, **cfg.gbm).fit(X.loc[tr, cols], y[tr])
                est[m][te] = g.predict(X.loc[te, cols]) - g.predict(Xn.loc[te, cols])
            else:
                base, _, opt = m.partition("+")         # e.g. dd_linear+margin2, dd_linear+nosolar
                kw = {}
                if opt.startswith("margin"):
                    kw["margin"] = float(opt[6:])
                if opt == "nosolar":
                    kw["solar"] = False
                est[m][te] = thermal_dd.fit_predict(y, w, cfg.tz, band, tr, te, model=base, gbm=cfg.gbm, **kw)
    secs = time.time() - t0
    seas = pd.Series(U.season(y.index), index=y.index)
    for m, e in est.items():
        e = pd.Series(e, index=y.index)
        valid = e.notna() & truth.notna() & y.notna()
        for sname in ("all", "cooling", "heating"):
            sel = valid & ((seas == sname) if sname != "all" else True)
            if sel.sum() < 24 * 14:
                continue
            ed, td = e[sel].groupby(day[sel]).sum(), truth[sel].groupby(day[sel]).sum()
            st = float(truth[sel].sum() / y[sel].sum())
            rows.append(dict(dataset=ds, unit=name, kind=kind, model=m, season=sname, hours=int(sel.sum()),
                             corr_hourly=float(np.corrcoef(e[sel], truth[sel])[0, 1]) if truth[sel].std() > 0 else np.nan,
                             corr_daily=float(np.corrcoef(ed, td)[0, 1]) if td.std() > 0 else np.nan,
                             share_est=float(e[sel].sum() / y[sel].sum()), share_true=st,
                             share_ratio=float(e[sel].sum() / truth[sel].sum()) if truth[sel].sum() > 0 else np.nan,
                             daily_err_rel=float((ed - td).abs().mean() / td.mean()) if td.mean() > 0 else np.nan))
    print(ds, name, kind, f"{secs:.0f}s", {m: round(r["share_ratio"], 2) for m in a.models for r in rows[-len(a.models) * 3:]
                                               if r["model"] == m and r["unit"] == name and r["season"] == "all"}, flush=True)

R = pd.DataFrame(rows)
os.makedirs("outputs/t2", exist_ok=True)
R.to_csv(f"outputs/t2/v3_metrics_{tag}.csv", index=False)
print(R[R.season == "all"].groupby(["dataset", "kind", "model"])[["corr_daily", "corr_hourly", "share_ratio", "daily_err_rel"]].median().round(3).to_string())
