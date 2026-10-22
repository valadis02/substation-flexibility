"""T2 v4 (development data only): does a significance gate help M2?

M2 (v0.5) = degree-day component above/below data-driven balance points (dd_linear). The gate keeps the cooling and/or
heating terms only if the daily load rises significantly with degree-days (Newey-West t > 2 on the training data);
otherwise that side is set to zero. Expected: fewer false weather-dependent loads where there is none (controls,
small heaters), no loss where the response is real (Pecan AC). Same units and folds as T2 v3.

    python experiments/t2_thermal_v4.py --datasets pecan_austin pecan_newyork pecan_california plegma refit
"""
import argparse, os, sys, time
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from flexsub import features, thermal_dd
import t2_units as U

ap = argparse.ArgumentParser()
ap.add_argument("--datasets", nargs="+", default=["pecan_austin"])
ap.add_argument("--block-days", type=int, default=28)
a = ap.parse_args()
rows = []
for ds, name, kind, y, truth, wx, cfg in U.units(a.datasets):
    if y.notna().sum() < 24 * 60:
        continue
    y = y[y.first_valid_index():y.last_valid_index()].asfreq("1h")
    w = wx.reindex(y.index); truth = truth.reindex(y.index)
    y.index = y.index.tz_convert(cfg.tz); w.index = w.index.tz_convert(cfg.tz); truth.index = y.index
    ok = (y.notna() & w["temp"].notna() & y.shift(24 * 7).notna()).to_numpy()
    day = y.index.normalize()
    block = ((y.index.tz_localize(None).normalize() - y.index[0].tz_localize(None).normalize()).days // a.block_days).to_numpy()
    tdaily, ydaily = w["temp"].groupby(day).mean(), y.groupby(day).mean()
    est = {m: np.full(len(y), np.nan) for m in ("dd_linear", "dd_gated")}
    gates = []
    for k in np.unique(block[ok]):
        te, tr = ok & (block == k), ok & (block != k)
        if tr.sum() < 24 * 28:
            continue
        trd = pd.Index(day[tr]).unique()
        band = features.balance_points(tdaily.reindex(trd), ydaily.reindex(trd))
        if np.isnan(band[0]):
            continue
        est["dd_linear"][te] = thermal_dd.fit_predict(y, w, cfg.tz, band, tr, te)
        est["dd_gated"][te] = thermal_dd.fit_predict(y, w, cfg.tz, band, tr, te, gate=True)
        gates.append(thermal_dd.significance(y, w, cfg.tz, band, tr))
    G = np.array(gates) if gates else np.zeros((0, 2))
    for m, e in est.items():
        e = pd.Series(e, index=y.index)
        sel = e.notna() & truth.notna() & y.notna()
        if sel.sum() < 24 * 14:
            continue
        ed, td = e[sel].groupby(day[sel]).sum(), truth[sel].groupby(day[sel]).sum()
        rows.append(dict(dataset=ds, unit=name, kind=kind, model=m, hours=int(sel.sum()),
                         cooling_kept=float(G[:, 0].mean()) if len(G) else np.nan, heating_kept=float(G[:, 1].mean()) if len(G) else np.nan,
                         corr_daily=float(np.corrcoef(ed, td)[0, 1]) if td.std() > 0 and ed.std() > 0 else np.nan,
                         share_est=float(e[sel].sum() / y[sel].sum()), share_true=float(truth[sel].sum() / y[sel].sum()),
                         abs_share_err=float(abs(e[sel].sum() - truth[sel].sum()) / y[sel].sum()),
                         daily_err_rel=float((ed - td).abs().mean() / td.mean()) if td.mean() > 0 else np.nan))
    print(ds, name, kind, {r["model"]: (round(r["share_est"], 3), round(r["share_true"], 3)) for r in rows[-2:]},
          "kept c/h:", np.round(G.mean(axis=0), 2) if len(G) else None, flush=True)

R = pd.DataFrame(rows)
os.makedirs("outputs/t2", exist_ok=True)
tag = "_".join(a.datasets)
R.to_csv(f"outputs/t2/v4_metrics_{tag}.csv", index=False)
S = R.groupby(["dataset", "kind", "model"])[["share_est", "share_true", "abs_share_err", "corr_daily", "daily_err_rel", "cooling_kept", "heating_kept"]].median().round(3)
print(S.to_string())
with open("experiments/results/t2_v4_dev.md", "a") as f:
    f.write(f"\n## {', '.join(a.datasets)}: dd_linear vs significance-gated (medians over units)\n\n" + S.to_markdown() + "\n")
