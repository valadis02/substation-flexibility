"""T2 v2 (development data only): thermal part (M2) after the T2 v1 findings.

Changes tested against v1 (see experiments/RESULTS.md, T2):
  * seasonal features (day of year, day length) that stay fixed in the counterfactual, so the temperature effect is
    learnt from hot vs cool days within the same season instead of from the season itself;
  * no clipping of the hourly estimate at 0;
  * counterfactual from data: heating and cooling balance points (Th, Tc) fitted on the training fold's daily means
    (load and temperature only) and temperature clipped into [Th, Tc]; compared with a fixed T0 swept over a grid.
Units: Plegma development homes one by one (2 without AC = negative control), the Plegma development homes as one
group (hours with >= 6 homes present, scaled), and REFIT development homes with electric heaters (1, 9, 16) plus two
REFIT homes without heaters as controls. Out-of-sample by leave-one-week-out.

    python experiments/t2_thermal_v2.py
Output: outputs/t2/v2_metrics.csv, outputs/t2/v2_balance.csv; summary appended to experiments/results/t2_dev.md
"""
import argparse, os, time
import numpy as np
import pandas as pd
from dataclasses import replace
from sklearn.ensemble import HistGradientBoostingRegressor as HGB
from flexsub import Config, features, splits
from flexsub.data import load_processed

T0S = np.round(np.arange(16, 26.01, 0.5), 2)


def season(idx):
    m = idx.month
    return np.where(np.isin(m, [5, 6, 7, 8, 9]), "cooling", np.where(np.isin(m, [11, 12, 1, 2, 3]), "heating", "mild"))


PECAN = {"pecan_austin": ("America/Chicago", 30.27, True), "pecan_newyork": ("America/New_York", 42.44, True),
         "pecan_california": ("America/Los_Angeles", 32.72, False)}   # tz, latitude, homes overlap in time (group)


def pecan_units(name):
    tz, lat, group = PECAN[name]
    cfg = Config(tz=tz, latitude=lat)
    d = load_processed(f"data/processed/{name}"); W = splits.development(d["W"], name)
    out, truth_all = [], {}
    for h in W.columns:
        A = d["appliances"][h].reindex(W.index)
        th = [c for c in ("ac", "furnace", "heater") if c in A.columns]   # electric heating/cooling circuits
        t = A[th].sum(axis=1, min_count=1) if th else pd.Series(0.0, index=W.index)
        t[W[h].isna()] = np.nan
        truth_all[h] = t
        out.append((name, h, "ac" if "ac" in th else "control", W[h], t, d["weather"], cfg))
    if group:
        T = pd.DataFrame(truth_all); present = W.notna() & T.notna(); n = present.sum(axis=1)
        keep = n >= 0.8 * W.shape[1]
        yg = (W.where(present).sum(axis=1) * W.shape[1] / n).where(keep)
        tg = (T.where(present).sum(axis=1) * W.shape[1] / n).where(keep)
        out.append((name, f"group({W.shape[1]} homes)", "ac", yg, tg, d["weather"], cfg))
    return out


def units(which):
    out = []
    for name in which:
        if name.startswith("pecan"):
            out += pecan_units(name)
    if "plegma" not in which:
        return out
    # Plegma
    cfgP = Config(tz="Europe/Athens", latitude=37.98)
    d = load_processed("data/processed/plegma"); W = splits.development(d["W"], "plegma")
    truth_all = {}
    for h in W.columns:
        A = d["appliances"][h].reindex(W.index)
        ac = [c for c in A.columns if c.startswith("ac")]
        truth_all[h] = A[ac].sum(axis=1, min_count=len(ac)) if ac else pd.Series(0.0, index=W.index)
        truth_all[h][W[h].isna()] = np.nan
        out.append(("plegma", h, "ac" if ac else "control", W[h], truth_all[h], d["weather"], cfgP))
    T = pd.DataFrame(truth_all)
    present = W.notna() & T.notna()
    n = present.sum(axis=1)
    keep = n >= 6
    yg = (W.where(present).sum(axis=1) * W.shape[1] / n).where(keep)
    tg = (T.where(present).sum(axis=1) * W.shape[1] / n).where(keep)
    out.append(("plegma", "group(>=6 homes)", "ac", yg, tg, d["weather"], cfgP))
    if "refit" not in which:
        return out
    # REFIT
    cfgR = Config(tz="Europe/London", latitude=52.77)
    d = load_processed("data/processed/refit"); W = splits.development(d["W"], "refit")
    for h in ("H1", "H9", "H16", "H3", "H5"):
        A = d["appliances"][h].reindex(W.index)
        hc = [c for c in A.columns if "Heater" in c]
        t = A[hc].sum(axis=1, min_count=len(hc)) if hc else pd.Series(0.0, index=W.index)
        t[W[h].isna()] = np.nan
        out.append(("refit", h, "heater" if hc else "control", W[h], t, d["weather"], cfgR))
    return out


ap = argparse.ArgumentParser()
ap.add_argument("--datasets", nargs="+", default=["plegma", "refit"])
a = ap.parse_args()
tag = "_".join(a.datasets)
rows, bal = [], []
for ds, name, kind, y, truth, wx, cfg0 in units(a.datasets):
    if y.notna().sum() < 24 * 60:
        continue
    y = y[y.first_valid_index():y.last_valid_index()].asfreq("1h")
    w = wx.reindex(y.index); truth = truth.reindex(y.index)
    y.index = y.index.tz_convert(cfg0.tz); w.index = w.index.tz_convert(cfg0.tz); truth.index = y.index
    t_start = time.time()
    cfg_ns, cfg_s = replace(cfg0, seasonal_features=False), replace(cfg0, seasonal_features=True)
    X = {"v1": features.build(y, w, cfg_ns), "seasonal": features.build(y, w, cfg_s)}
    ok = (y.notna() & X["v1"]["lag7d"].notna()).to_numpy()
    day = y.index.normalize()
    week = ((y.index.tz_localize(None).normalize() - y.index[0].tz_localize(None).normalize()).days // 7).to_numpy()
    tdaily, ydaily = w["temp"].groupby(day).mean(), y.groupby(day).mean()
    XnT = {(model, t0): features.build(y, w, replace(cfgm, neutral_temp=float(t0), neutral_band=None), neutral=True)[X[model].columns]
           for model, cfgm in (("v1", cfg_ns), ("seasonal", cfg_s)) for t0 in T0S}
    est = {}
    bands = []
    for k in np.unique(week[ok]):
        te, tr = ok & (week == k), ok & (week != k)
        if tr.sum() < 24 * 14:
            continue
        # balance points from the training fold only (load + temperature, no ground truth)
        trdays = pd.Index(day[tr]).unique()
        band = features.balance_points(tdaily.reindex(trdays), ydaily.reindex(trdays))
        bands.append(band)
        for model, cfgm in (("v1", cfg_ns), ("seasonal", cfg_s)):
            Xm = X[model]
            m = HGB(loss="quantile", quantile=0.5, **cfgm.gbm).fit(Xm[tr], y[tr])
            pa = m.predict(Xm[te])
            cfs = {f"T0={t0}": XnT[(model, t0)] for t0 in T0S}
            if not np.isnan(band[0]):
                cfs["band"] = features.build(y, w, replace(cfgm, neutral_band=band), neutral=True)[Xm.columns]
            for cname, Xn in cfs.items():
                est.setdefault((model, cname), np.full(len(y), np.nan))[te] = pa - m.predict(Xn[te])
    secs = time.time() - t_start
    seas = pd.Series(season(y.index), index=y.index)
    for (model, cname), e in est.items():
        e = pd.Series(e, index=y.index)
        valid = e.notna() & truth.notna() & y.notna()
        for sname in ("all", "cooling", "heating"):
            m = valid & ((seas == sname) if sname != "all" else True)
            if m.sum() < 24 * 14:
                continue
            ed, td = e[m].groupby(day[m]).sum(), truth[m].groupby(day[m]).sum()
            rows.append(dict(dataset=ds, unit=name, kind=kind, model=model, counterfactual=cname, season=sname,
                             hours=int(m.sum()),
                             corr_hourly=float(np.corrcoef(e[m], truth[m])[0, 1]) if truth[m].std() > 0 else np.nan,
                             corr_daily=float(np.corrcoef(ed, td)[0, 1]) if td.std() > 0 else np.nan,
                             share_est=float(e[m].sum() / y[m].sum()), share_true=float(truth[m].sum() / y[m].sum()),
                             share_est_clipped=float(e[m].clip(lower=0).sum() / y[m].sum()),
                             daily_err_rel=float((ed - td).abs().mean() / max(td.mean(), 1e-6)) if td.mean() > 0 else np.nan))
    B = np.array(bands)
    bal.append(dict(dataset=ds, unit=name, kind=kind, Th_median=float(np.nanmedian(B[:, 0])), Tc_median=float(np.nanmedian(B[:, 1])),
                    Th_iqr=float(np.nanpercentile(B[:, 0], 75) - np.nanpercentile(B[:, 0], 25)),
                    Tc_iqr=float(np.nanpercentile(B[:, 1], 75) - np.nanpercentile(B[:, 1], 25)), secs=round(secs)))
    print(bal[-1], flush=True)

R = pd.DataFrame(rows); R["share_err"] = R.share_est - R.share_true
B = pd.DataFrame(bal)
os.makedirs("outputs/t2", exist_ok=True)
R.to_csv(f"outputs/t2/v2_metrics_{tag}.csv", index=False); B.to_csv(f"outputs/t2/v2_balance_{tag}.csv", index=False)

cols = ["corr_hourly", "corr_daily", "share_est", "share_true", "share_err", "daily_err_rel"]
sel = R.counterfactual.isin(["T0=20.0", "band"])
with open("experiments/results/t2_dev.md", "a") as f:
    f.write(f"\n## v2 ({', '.join(a.datasets)}): seasonal features, no clip, balance-point band (development split, leave-one-week-out)\n\n")
    f.write("Medians over units of each kind. 'v1' = method features as in T2 v1 (now without the clip); 'seasonal' = plus "
            "day of year and day length, fixed in the counterfactual; 'band' = temperature clipped to the balance points "
            "fitted on the training fold.\n\n")
    for (ds, kind), g in R[sel].groupby(["dataset", "kind"]):
        f.write(f"### {ds}, {kind} ({g.unit.nunique()} units)\n\n")
        f.write(g.groupby(["model", "counterfactual", "season"])[cols].median().round(3).to_markdown() + "\n\n")
    G = R[sel & R.unit.str.startswith("group")]
    if len(G):
        f.write("### Groups (all development homes summed), all metrics\n\n")
        f.write(G.drop(columns=["kind"]).round(3).to_markdown(index=False) + "\n\n")
    sweep = R[(R.model == "seasonal") & R.counterfactual.str.startswith("T0=") & (R.season == "all") & (R.kind != "control")]
    f.write("### Sensitivity to fixed T0 (seasonal model, all seasons, AC/heater units): median daily_err_rel and share_err\n\n")
    f.write(sweep.groupby(["dataset", "counterfactual"])[["daily_err_rel", "share_err", "corr_daily"]].median().round(3).unstack(0).to_markdown() + "\n\n")
    f.write("### Balance points from the data (median over folds; IQR = spread across folds)\n\n" + B.round(2).to_markdown(index=False) + "\n")
print(R[sel & (R.season == "all")].groupby(["dataset", "kind", "model", "counterfactual"])[cols].median().round(3).to_string())
