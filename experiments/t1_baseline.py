"""T1 (development data only): coverage and sharpness of the M1 band vs group size.

For each dataset and group size N, draw random groups of development homes (fixed seed), sum them into a
'substation' (an hour counts only if every home in the group has data), run M1 rolling-origin with conformal
calibration, and score every test day after a 42-day warm-up (28-day lags + 14-day calibration window).

    python experiments/t1_baseline.py refit   [--sizes 1 2 5 10] [--groups 5] [--retrain 7] [--weather path.csv]
Results: outputs/t1/<dataset>_groups.csv (per group) and a summary printed / appended to experiments/results/t1_dev.md
"""
import argparse, os, time
import numpy as np
import pandas as pd
from flexsub import Config, features, baseline, metrics, splits
from flexsub.data import load_processed

ap = argparse.ArgumentParser()
ap.add_argument("dataset")
ap.add_argument("--sizes", type=int, nargs="+", default=[1, 2, 5, 10])
ap.add_argument("--groups", type=int, default=5)
ap.add_argument("--retrain", type=int, default=7)
ap.add_argument("--no-weather", action="store_true")
ap.add_argument("--tz", default=None)
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()

TZ = {"plegma": "Europe/Athens", "refit": "Europe/London", "ukdale": "Europe/London"}
cfg = Config(tz=a.tz or TZ[a.dataset], retrain_days=a.retrain)
d = load_processed(os.path.join("data", "processed", a.dataset))
W = splits.development(d["W"], a.dataset)
weather = None if (a.no_weather or d["weather"] is None) else d["weather"]
rng = np.random.default_rng(a.seed)
homes = list(W.columns)
rows = []
for N in a.sizes:
    if N > len(homes):
        continue
    from itertools import combinations
    from math import comb
    if comb(len(homes), N) <= a.groups:
        groups = [sorted(c) for c in combinations(homes, N)]
    else:
        seen = set()
        while len(seen) < a.groups:
            seen.add(tuple(sorted(rng.choice(homes, size=N, replace=False).tolist())))
        groups = [list(c) for c in sorted(seen)]
    for g, members in enumerate(groups):
        y = W[members].sum(axis=1, min_count=N)
        y = y[y.first_valid_index():y.last_valid_index()].asfreq("1h")
        w = None if weather is None else weather.reindex(y.index)
        y.index = y.index.tz_convert(cfg.tz)
        if w is not None:
            w.index = w.index.tz_convert(cfg.tz)
        X = features.build(y, w, cfg)
        Xn = features.build(y, w, cfg, neutral=True) if w is not None else X
        loc_days = pd.date_range(y.index[0].date() + pd.Timedelta(days=42), y.index[-1].date(), freq="D").tz_localize(cfg.tz)
        t0 = time.time()
        R = baseline.conformal_calibrate(baseline.rolling_origin(y, X, Xn, loc_days, cfg), cfg).dropna(subset=["cal_lo"])
        m = R["actual"].mean()
        rows.append(dict(dataset=a.dataset, N=N, group=g, members=" ".join(members), hours=len(R), days=R.index.normalize().nunique(),
                         mean_kw=m,
                         cov_raw=metrics.coverage(R.actual, R.raw_lo, R.raw_hi),
                         cov_cal=metrics.coverage(R.actual, R.cal_lo, R.cal_hi),
                         width_cal_rel=float((R.cal_hi - R.cal_lo).mean() / m),
                         is_cal_rel=metrics.interval_score(R.actual, R.cal_lo, R.cal_hi) / m,
                         nmae_median=metrics.mae(R.actual, R["q0.5"]) / m,
                         secs=round(time.time() - t0)))
        print({k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v) for k, v in rows[-1].items() if k != "members"}, flush=True)

res = pd.DataFrame(rows)
os.makedirs("outputs/t1", exist_ok=True)
res.to_csv(f"outputs/t1/{a.dataset}_groups.csv", index=False)
summ = res.groupby("N")[["hours", "mean_kw", "cov_raw", "cov_cal", "width_cal_rel", "is_cal_rel", "nmae_median"]].median().round(3)
summ.insert(0, "groups", res.groupby("N").size())
print(summ.to_string())
os.makedirs("experiments/results", exist_ok=True)
with open("experiments/results/t1_dev.md", "a") as f:
    f.write(f"\n## {a.dataset} (development split, weather={'yes' if weather is not None else 'no'}, retrain every {a.retrain} d, seed {a.seed})\n\n")
    f.write("Medians over groups. cov = share of hours inside the band (target 0.90 after calibration); width/IS/nMAE relative to mean load.\n\n")
    f.write(summ.to_markdown() + "\n")
