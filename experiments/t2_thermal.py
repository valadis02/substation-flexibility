"""T2 (development data only): thermal part (M2) vs measured AC, and the choice of the neutral temperature.

For every development home of Plegma (homes without AC act as a negative control):
  * M2 thermal = prediction with actual weather - prediction with the same day at a neutral temperature T0,
    out-of-sample by leave-one-week-out (the method uses leave-one-day-out; weeks are used for speed);
  * T0 swept over a grid; the model does not depend on T0, so one fit per fold serves every T0;
  * two model variants: "full" (method features incl. load lags) and "nolag" (calendar + weather only). The lags
    carry yesterday's AC use, so the full model may attribute part of the weather effect to them;
  * balance point estimated from the aggregate alone (daily mean load vs daily mean temperature, one-break V fit,
    as in PRISM-type degree-day methods) and from the measured AC, to see if T0 can be set from data.
Metrics against measured AC (sum of ac_* circuits): hourly and daily correlation, error in the thermal share of
energy, daily energy error relative to mean daily AC; all hours and by season (cooling May-Sep, heating Nov-Mar).

    python experiments/t2_thermal.py [--t0 16 26 0.5]
Output: outputs/t2/plegma_sweep.csv, outputs/t2/plegma_balance.csv, summary appended to experiments/results/t2_dev.md
"""
import argparse, os, time
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor as HGB
from flexsub import Config, features, splits
from flexsub.data import load_processed

ap = argparse.ArgumentParser()
ap.add_argument("--t0", type=float, nargs=3, default=[16, 26, 0.5])
ap.add_argument("--dataset", default="plegma")
a = ap.parse_args()
cfg = Config(tz="Europe/Athens")
T0S = np.round(np.arange(a.t0[0], a.t0[1] + 1e-9, a.t0[2]), 2)

d = load_processed(os.path.join("data", "processed", a.dataset))
Wd = splits.development(d["W"], a.dataset)


def season(idx):
    m = idx.month
    return np.where(np.isin(m, [5, 6, 7, 8, 9]), "cooling", np.where(np.isin(m, [11, 12, 1, 2, 3]), "heating", "mild"))


def v_fit(temp_daily, y_daily, grid=np.arange(12, 28.01, 0.25)):
    """One-break V fit y = a + b*max(Tb - T, 0) + c*max(T - Tb, 0); returns the Tb with the smallest SSE."""
    ok = temp_daily.notna() & y_daily.notna()
    t, v = temp_daily[ok].to_numpy(), y_daily[ok].to_numpy()
    best = (np.inf, np.nan)
    for tb in grid:
        A = np.c_[np.ones_like(t), np.maximum(tb - t, 0), np.maximum(t - tb, 0)]
        coef, *_ = np.linalg.lstsq(A, v, rcond=None)
        sse = float(((A @ coef - v) ** 2).sum())
        if sse < best[0]:
            best = (sse, tb)
    return best[1]


rows, bal = [], []
for h in Wd.columns:
    y = Wd[h]
    if y.notna().sum() < 24 * 60:
        continue
    y = y[y.first_valid_index():y.last_valid_index()].asfreq("1h")
    w = d["weather"].reindex(y.index)
    A = d["appliances"][h].reindex(y.index)
    ac_cols = [c for c in A.columns if c.startswith("ac")]
    truth = A[ac_cols].sum(axis=1, min_count=len(ac_cols)) if ac_cols else pd.Series(0.0, index=y.index)
    truth[y.isna()] = np.nan
    y.index = y.index.tz_convert(cfg.tz); w.index = w.index.tz_convert(cfg.tz); truth.index = y.index

    X = features.build(y, w, cfg)
    Xn = {t0: features.build(y, w, cfg.__class__(**{**cfg.__dict__, "neutral_temp": float(t0)}), neutral=True)[X.columns] for t0 in T0S}
    cal_cols = [c for c in X.columns if c in ("hour_sin", "hour_cos", "hour", "dow", "is_weekend", "holiday")]
    wx_cols = [c for c in X.columns if c in ("temp", "rh", "cloud", "rad", "is_day", "temp_day_mean", "temp_day_max",
                                             "temp_prevday_mean", "cdd", "hdd", "temp_lag3h")]
    variants = {"full": list(X.columns), "nolag": cal_cols + wx_cols}
    ok = (y.notna() & X["lag7d"].notna()).to_numpy()
    week = ((y.index.tz_localize(None).normalize() - y.index[0].tz_localize(None).normalize()).days // 7).to_numpy()
    t_start = time.time()
    est = {(v, t0): np.full(len(y), np.nan) for v in variants for t0 in T0S}
    for k in np.unique(week[ok]):
        te = ok & (week == k); tr = ok & (week != k)
        if tr.sum() < 24 * 14:
            continue
        for v, cols in variants.items():
            m = HGB(loss="quantile", quantile=0.5, **cfg.gbm).fit(X.loc[tr, cols], y[tr])
            p_act = m.predict(X.loc[te, cols])
            for t0 in T0S:
                est[(v, t0)][te] = np.maximum(p_act - m.predict(Xn[t0].loc[te, cols]), 0)
    secs = time.time() - t_start

    seas = pd.Series(season(y.index), index=y.index)
    day = y.index.normalize()
    for (v, t0), e in est.items():
        e = pd.Series(e, index=y.index)
        valid = e.notna() & truth.notna() & y.notna()
        for sname in ("all", "cooling", "heating"):
            m = valid & ((seas == sname) if sname != "all" else True)
            if m.sum() < 24 * 14:
                continue
            ed, td, yd = e[m].groupby(day[m]).sum(), truth[m].groupby(day[m]).sum(), y[m].groupby(day[m]).sum()
            rows.append(dict(home=h, has_ac=bool(ac_cols), variant=v, t0=t0, season=sname, hours=int(m.sum()),
                             corr_hourly=float(np.corrcoef(e[m], truth[m])[0, 1]) if truth[m].std() > 0 else np.nan,
                             corr_daily=float(np.corrcoef(ed, td)[0, 1]) if td.std() > 0 else np.nan,
                             share_est=float(e[m].sum() / y[m].sum()), share_true=float(truth[m].sum() / y[m].sum()),
                             daily_err_rel=float((ed - td).abs().mean() / max(td.mean(), 1e-6))))
    tdaily = w["temp"].groupby(day).mean()
    bal.append(dict(home=h, has_ac=bool(ac_cols), tb_aggregate=v_fit(tdaily, y.groupby(day).mean()),
                    tb_ac=v_fit(tdaily, truth.groupby(day).mean()) if ac_cols else np.nan, secs=round(secs)))
    print(bal[-1], flush=True)

R = pd.DataFrame(rows); R["share_err"] = R.share_est - R.share_true
B = pd.DataFrame(bal)
os.makedirs("outputs/t2", exist_ok=True)
R.to_csv(f"outputs/t2/{a.dataset}_sweep.csv", index=False); B.to_csv(f"outputs/t2/{a.dataset}_balance.csv", index=False)

ac = R[R.has_ac]
summ = (ac.groupby(["variant", "season", "t0"])[["corr_hourly", "corr_daily", "share_err", "daily_err_rel"]]
        .median().reset_index())
best = summ.loc[summ.groupby(["variant", "season"])["daily_err_rel"].idxmin()]
ctrl = R[~R.has_ac & (R.season == "all")].groupby(["variant", "t0"])["share_est"].median().unstack(0)
os.makedirs("experiments/results", exist_ok=True)
with open(f"experiments/results/t2_dev.md", "a") as f:
    f.write(f"\n## {a.dataset} (development split; leave-one-week-out; T0 grid {T0S[0]}-{T0S[-1]} step {a.t0[2]})\n\n")
    f.write("Homes with AC; medians over homes. share_err = estimated - true thermal share of energy; daily_err_rel = "
            "mean |daily thermal - daily AC| / mean daily AC.\n\n")
    for t0 in (18, 20, 22):
        f.write(f"### T0 = {t0}\n\n" + summ[summ.t0 == t0].drop(columns="t0").round(3).to_markdown(index=False) + "\n\n")
    f.write("### Best T0 by daily_err_rel\n\n" + best.round(3).to_markdown(index=False) + "\n\n")
    f.write("### Balance point (one-break V fit on daily means)\n\n" + B.round(2).to_markdown(index=False) + "\n\n")
    f.write("### Negative control (homes without AC): estimated thermal share, by T0\n\n" + ctrl.round(3).to_markdown() + "\n")
print(best.round(3).to_string()); print(B.round(2).to_string())
