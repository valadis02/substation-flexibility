"""T3-EV (development data only): can EV charging be found from hourly per-home smart-meter data?

Detector (no sub-metering): an hour is "EV-like" if the home's load exceeds its own same-hour median of the previous
14 days by more than k kW (k in K). Ground truth: Pecan circuits car1/car2 (an hour is charging if EV > 1 kW).
  1. which homes have an EV: score = share of EV-like hours; AUC over homes (EV homes vs others);
  2. when they charge: hourly precision / recall in EV homes;
  3. EV energy by hour of day for the group of development homes: estimated (excess load in EV-like hours of homes
     whose score exceeds the cut) vs true EV energy;
  4. what can be shifted: charging start hour and session length (true vs estimated). The time the car stays plugged
     in is not measured by the circuit, so the flexibility window itself still needs an assumption or literature.

    python experiments/t3_ev.py [--datasets pecan_austin pecan_newyork]
Output: outputs/t3/ev_*.csv and a summary appended to experiments/results/t3_ev_dev.md
"""
import argparse, os
import numpy as np
import pandas as pd
from flexsub import splits
from flexsub.data import load_processed

ap = argparse.ArgumentParser()
ap.add_argument("--datasets", nargs="+", default=["pecan_austin", "pecan_newyork"])
a = ap.parse_args()
K = (1.5, 2.5, 3.5)
TZ = {"pecan_austin": "America/Chicago", "pecan_newyork": "America/New_York"}


def auc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    return float(((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()))


def sessions(flag):
    """Runs of consecutive True hours -> DataFrame(start, hours)."""
    f = flag.fillna(False).astype(int)
    start = f.diff().fillna(f.iloc[0]) == 1
    sid = start.cumsum()[f == 1]
    g = pd.Series(sid.index, index=sid.index).groupby(sid.values)
    return pd.DataFrame({"start": g.first().values, "hours": g.size().values})


out_md = []
for ds in a.datasets:
    d = load_processed(os.path.join("data", "processed", ds))
    W = splits.development(d["W"], ds)
    tz = TZ[ds]
    ev_true = {h: d["appliances"][h]["ev"].reindex(W.index) for h in W.columns if "ev" in d["appliances"][h]}
    has_ev = {h: (h in ev_true and ev_true[h].mean() > 0.05) for h in W.columns}
    rows_home, rows_hour, prof_rows, sess_rows = [], [], [], []
    for k in K:
        flags, excess = {}, {}
        for h in W.columns:
            y = W[h]
            base = y.groupby(y.index.hour).transform(lambda s: s.rolling(14, min_periods=7).median().shift(1))
            flags[h] = ((y - base) > k).where(base.notna() & y.notna())
            excess[h] = (y - base).clip(lower=0).where(flags[h] == True, 0.0)
        score = {h: float(flags[h].mean()) for h in W.columns}
        pos = [score[h] for h in W.columns if has_ev[h]]; neg = [score[h] for h in W.columns if not has_ev[h]]
        cut = (np.mean(neg) + np.mean(pos)) / 2 if pos and neg else np.nan     # reported, not tuned per home
        rows_home.append(dict(dataset=ds, k=k, ev_homes=len(pos), other_homes=len(neg), auc=auc(pos, neg),
                              score_ev_median=np.median(pos) if pos else np.nan, score_other_median=np.median(neg)))
        for h in W.columns:
            if not has_ev[h]:
                continue
            tr = ev_true[h] > 1; f = flags[h]; ok = f.notna() & ev_true[h].notna()
            tp, fp, fn = int((f & tr)[ok].sum()), int((f & ~tr)[ok].sum()), int((~f.astype(bool) & tr)[ok].sum())
            rows_hour.append(dict(dataset=ds, k=k, home=h, precision=tp / max(tp + fp, 1), recall=tp / max(tp + fn, 1)))
            if k == 2.5:
                st, se = sessions(tr[ok]), sessions(f[ok].astype(bool))
                for kind, S in (("true", st), ("estimated", se)):
                    if len(S):
                        loc = pd.to_datetime(S.start, utc=True).dt.tz_convert(tz)
                        sess_rows.append(dict(dataset=ds, home=h, kind=kind, sessions=len(S), start_hour_median=float(np.median(loc.dt.hour)),
                                              hours_median=float(S.hours.median()), hours_p90=float(S.hours.quantile(0.9))))
        sel = [h for h in W.columns if score[h] > cut]
        est = pd.DataFrame({h: excess[h] for h in sel}).sum(axis=1) if sel else pd.Series(0.0, index=W.index)
        tru = pd.DataFrame({h: ev_true[h] for h in W.columns if has_ev[h]}).sum(axis=1)
        m = W.notna().all(axis=1)
        e_loc, t_loc = est[m].tz_convert(tz), tru[m].tz_convert(tz)
        pe, pt = e_loc.groupby(e_loc.index.hour).mean(), t_loc.groupby(t_loc.index.hour).mean()
        prof_rows.append(dict(dataset=ds, k=k, homes_selected=len(sel), true_ev_homes_selected=sum(has_ev[h] for h in sel),
                              profile_corr=float(np.corrcoef(pe, pt)[0, 1]), energy_ratio=float(pe.sum() / pt.sum()),
                              true_peak_hour=int(pt.idxmax()), est_peak_hour=int(pe.idxmax())))
    H, R, P, S = map(pd.DataFrame, (rows_home, rows_hour, prof_rows, sess_rows))
    os.makedirs("outputs/t3", exist_ok=True)
    for n, df in (("homes", H), ("hours", R), ("profile", P), ("sessions", S)):
        df.to_csv(f"outputs/t3/ev_{n}_{ds}.csv", index=False)
    out_md.append(f"\n## {ds} (development split; detector: load > same-hour 14-day median + k kW)\n\n"
                  "### 1. Which homes have an EV (score = share of EV-like hours)\n\n" + H.round(3).to_markdown(index=False) +
                  "\n\n### 2. When they charge (EV homes; median over homes)\n\n" +
                  R.groupby("k")[["precision", "recall"]].median().round(2).to_markdown() +
                  "\n\n### 3. EV energy by hour of day, group of development homes\n\n" + P.round(3).to_markdown(index=False) +
                  "\n\n### 4. Sessions (k = 2.5; median over EV homes)\n\n" +
                  S.groupby("kind")[["sessions", "start_hour_median", "hours_median", "hours_p90"]].median().round(1).to_markdown() + "\n")
    print(H.round(3).to_string()); print(P.round(3).to_string())
os.makedirs("experiments/results", exist_ok=True)
with open("experiments/results/t3_ev_dev.md", "a") as f:
    f.write("".join(out_md))
