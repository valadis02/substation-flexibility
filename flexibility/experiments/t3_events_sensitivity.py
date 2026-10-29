"""T3 v3 / T4 for design A (development data only): sensitivity of the data-only shiftable events to their settings.

Settings of `shiftable.events_home`: max_run_h (longest run counted as an appliance cycle), k (robust SDs above the
home's usual load), window_days (history for the usual load). The home's weather-dependent load is removed first (A2).
Shiftable truth = washing machine, dryer, dishwasher, electric storage water heater (T3 v2 definition).
Groups: all development homes of each dataset and random groups of 5. Metrics as T3 v2.

    python experiments/t3_events_sensitivity.py
"""
import os
import numpy as np
import pandas as pd
from flexsub import Config, splits, metrics, shiftable
from flexsub.appliances import category
from flexsub.data import load_processed
from flexsub.decompose import _home_weather_load

TZ = {"refit": ("Europe/London", 52.77), "plegma": ("Europe/Athens", 37.98),
      "pecan_austin": ("America/Chicago", 30.27), "pecan_newyork": ("America/New_York", 42.44)}
RUNS = [1, 2, 3, 4, 6, 8, 12, 999]
KS = [2.0, 2.5, 3.0, 4.0]
WINDOWS = [7, 14, 28]
rng = np.random.default_rng(0)
rows = []
for ds, (tz, lat) in TZ.items():
    d = load_processed(os.path.join("data", "processed", ds))
    W = splits.development(d["W"], ds)
    Y, T, WL = {}, {}, {}
    for h in W.columns:
        A = d["appliances"][h].reindex(W.index)
        if "ev" in A.columns and A["ev"].mean() > 0.05:
            continue
        sh = [c for c in A.columns if category(c, ds) == "shiftable"]
        if not sh or W[h].notna().sum() < 24 * 60:
            continue
        y = W[h][W[h].first_valid_index():W[h].last_valid_index()].asfreq("1h")
        t = A[sh].sum(axis=1, min_count=len(sh)).reindex(y.index); t[y.isna()] = np.nan
        Y[h], T[h] = y, t
        WL[h] = _home_weather_load(y, d["weather"].reindex(y.index), tz)
    homes = sorted(Y)
    groups = [homes] + [sorted(rng.choice(homes, size=5, replace=False).tolist()) for _ in range(5)]
    print(ds, len(homes), "homes", flush=True)
    settings = [("run", r, 3.0, 14) for r in RUNS] + [("k", 3, k, 14) for k in KS] + [("window", 3, 3.0, wd) for wd in WINDOWS]
    for kind, run, k, wd in settings:
        E = pd.DataFrame({h: shiftable.events_home(Y[h], k=k, max_run_h=run, window_days=wd, weather_load=WL[h]).reindex(W.index) for h in homes})
        Yd, Td = pd.DataFrame(Y).reindex(W.index), pd.DataFrame(T).reindex(W.index)
        for gi, mem in enumerate(groups):
            m = Yd[mem].notna().all(axis=1) & Td[mem].notna().all(axis=1) & E[mem].notna().all(axis=1)
            if m.sum() < 24 * 30:
                continue
            y, tt, e = Yd.loc[m, mem].sum(axis=1), Td.loc[m, mem].sum(axis=1), E.loc[m, mem].sum(axis=1)
            key = shiftable._key(y.index, tz)
            aw0 = metrics.awfe_p90(0 * y / y, tt / y)
            aw = metrics.awfe_p90(e / y, tt / y)
            rows.append(dict(dataset=ds, setting=kind, max_run_h=run, k=k, window_days=wd, group="all" if gi == 0 else f"g{gi}",
                             energy_ratio=float(e.sum() / tt.sum()), awfe_skill=1 - aw / aw0,
                             corr_profile=float(np.corrcoef(e.groupby(key).mean(), tt.groupby(key).mean())[0, 1]) if e.std() > 0 else np.nan))
R = pd.DataFrame(rows)
os.makedirs("outputs/t3", exist_ok=True)
R.to_csv("outputs/t3/events_sensitivity.csv", index=False)
with open("experiments/results/t3_events_sensitivity_dev.md", "w") as f:
    f.write("# Design A sensitivity (development; truth incl. electric water heaters)\n\nAWFE skill (1 - AWFE/AWFE_zero), "
            "energy ratio and profile correlation; group = all development homes; g = median over 5 groups of 5.\n")
    for kind, col in (("run", "max_run_h"), ("k", "k"), ("window", "window_days")):
        sub = R[R.setting == kind]
        allg = sub[sub.group == "all"].pivot_table(index=col, columns="dataset", values=["awfe_skill", "energy_ratio"]).round(2)
        g5 = sub[sub.group != "all"].groupby([col, "dataset"]).awfe_skill.median().unstack().round(2)
        f.write(f"\n## {col}\n\nAll homes:\n\n" + allg.to_markdown() + "\n\nGroups of 5 (median AWFE skill):\n\n" + g5.to_markdown() + "\n")
print(open("experiments/results/t3_events_sensitivity_dev.md").read())
