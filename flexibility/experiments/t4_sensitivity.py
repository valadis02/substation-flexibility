"""T4 (development data only): sensitivity of the flexibility envelope (M4) to the settings that are still fixed.

For a group of development homes (all homes of the dataset that overlap in time):
  estimated decomposition: M2 (thermal_dd_loo on the group) + M3 (decompose_substation, design A events)
  "true" decomposition: same base, but weather-dependent = measured AC/heating circuits and shiftable = measured
  washing machine, dryer, dishwasher, electric water heater; allocated in the same order.
Both go through M4 (`flexibility_by_hour`) with each setting; error = mean |estimated - true| over the 24 hours of the
envelope (down_kw, up_kw), relative to mean load, and the ratio of their daily sums. A setting matters if changing it
moves the error or the envelope itself a lot.
Settings: shift_window_h, request_duration_h, cap_quantile, base_hours, base_quantile.

    python experiments/t4_sensitivity.py --datasets pecan_austin pecan_newyork refit
"""
import argparse, os
import numpy as np
import pandas as pd
from dataclasses import replace
from flexsub import Config, splits, thermal, decompose, flexibility
from flexsub.appliances import category
from flexsub.data import load_processed

TZ = {"refit": ("Europe/London", 52.77), "pecan_austin": ("America/Chicago", 30.27),
      "pecan_newyork": ("America/New_York", 42.44)}
GRID = {"shift_window_h": [1, 2, 3, 4, 6], "request_duration_h": [1, 2, 3, 4], "cap_quantile": [0.8, 0.9, 0.95],
        "base_hours": [2, 4, 6], "base_quantile": [0.05, 0.1, 0.2]}
ap = argparse.ArgumentParser()
ap.add_argument("--datasets", nargs="+", default=list(TZ))
a = ap.parse_args()
rows = []
for ds in a.datasets:
    tz, lat = TZ[ds]
    cfg0 = Config(tz=tz, latitude=lat)
    d = load_processed(os.path.join("data", "processed", ds))
    W = splits.development(d["W"], ds)
    th_t, sh_t, homes = {}, {}, []
    for h in W.columns:
        A = d["appliances"][h].reindex(W.index)
        if "ev" in A.columns and A["ev"].mean() > 0.05:
            continue
        thc = [c for c in A.columns if category(c, ds) == "thermal" or c in ("ac", "furnace", "heater") or c.startswith("ac_")]
        shc = [c for c in A.columns if category(c, ds) == "shiftable"]
        if not shc:
            continue
        homes.append(h)
        th_t[h] = A[thc].sum(axis=1, min_count=1) if thc else pd.Series(0.0, index=W.index)
        sh_t[h] = A[shc].sum(axis=1, min_count=len(shc))
    Wg = W[homes]
    m = Wg.notna().all(axis=1) & pd.DataFrame(sh_t).notna().all(axis=1)
    Wg = Wg[m].asfreq("1h")
    Wg.index = Wg.index.tz_convert(tz)
    w = d["weather"].reindex(Wg.index.tz_convert("UTC")); w.index = Wg.index
    y = Wg.sum(axis=1, min_count=len(homes))
    days = pd.date_range(y.index[0].date() + pd.Timedelta(days=28), y.index[-1].date(), freq="D").tz_localize(tz)
    print(ds, len(homes), "homes,", int(y.notna().sum()), "hours", flush=True)
    th_est = thermal.thermal_dd_loo(y, w, days, cfg0)
    TT = pd.DataFrame(th_t).reindex(W.index)[m].sum(axis=1); TT.index = TT.index.tz_convert(tz); TT = TT.reindex(y.index)
    ST = pd.DataFrame(sh_t).reindex(W.index)[m].sum(axis=1); ST.index = ST.index.tz_convert(tz); ST = ST.reindex(y.index)
    cache = {}
    for name, values in GRID.items():
        for v in values:
            cfg = replace(cfg0, **{name: v})
            bkey = (cfg.base_hours, cfg.base_quantile)
            if bkey not in cache:
                D_est = decompose.decompose_substation(Wg, w, th_est, cfg)
                D_true = D_est[["actual", "base"]].copy()
                rem = D_true["actual"] - D_true["base"]
                D_true["thermal"] = np.minimum(TT.reindex(D_true.index).clip(lower=0), rem); rem = rem - D_true["thermal"]
                D_true["shiftable"] = np.minimum(ST.reindex(D_true.index).clip(lower=0), rem); rem = rem - D_true["shiftable"]
                D_true["routine"] = rem
                cache[bkey] = (D_est, D_true)
            D_est, D_true = cache[bkey]
            Fe, Ft = flexibility.flexibility_by_hour(D_est, cfg), flexibility.flexibility_by_hour(D_true, cfg)
            load = Fe["load_kw"].mean()
            row = dict(dataset=ds, setting=name, value=v)
            for col in ("down_kw", "up_kw"):
                row[f"{col}_err"] = float((Fe[col] - Ft[col]).abs().mean() / load)
                row[f"{col}_ratio"] = float(Fe[col].sum() / Ft[col].sum()) if Ft[col].sum() > 0 else np.nan
                row[f"{col}_est_mean"] = float(Fe[col].mean() / load)
            rows.append(row)
        print(ds, name, "done", flush=True)
R = pd.DataFrame(rows)
os.makedirs("outputs/t4", exist_ok=True)
R.to_csv("outputs/t4/sensitivity.csv", index=False)
with open("experiments/results/t4_dev.md", "w") as f:
    f.write("# T4 sensitivity of the flexibility envelope (development)\n\nerr = mean |estimated - true| over 24 h / mean load; "
            "ratio = estimated / true daily sum; est_mean = estimated envelope / mean load.\n")
    for name in GRID:
        f.write(f"\n## {name}\n\n" + R[R.setting == name].drop(columns="setting").round(3).to_markdown(index=False) + "\n")
print(open("experiments/results/t4_dev.md").read())
