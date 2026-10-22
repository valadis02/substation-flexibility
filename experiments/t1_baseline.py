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
ap.add_argument("--out", default="experiments/results/t1_dev.md")
a = ap.parse_args()

TZ = {"plegma": "Europe/Athens", "refit": "Europe/London", "ukdale": "Europe/London", "lcl": "Europe/London"}
cfg = Config(tz=a.tz or TZ[a.dataset], retrain_days=a.retrain)
LCL = a.dataset == "lcl"
if LCL:
    # precomputed group sums (scripts/prepare_lcl.py); T1 uses Std-tariff development groups before the time cut
    import json
    ddir = os.path.join("data", "processed", "lcl")
    G = pd.read_csv(os.path.join(ddir, "groups.csv.gz"), index_col="timestamp"); G.index = pd.to_datetime(G.index, utc=True)
    cut = pd.Timestamp(json.load(open(os.path.join(ddir, "groups_meta.json")))["time_cut"])
    G = G[G.index < cut]
    wf = os.path.join(ddir, "weather.csv.gz")
    weather = None
    if os.path.exists(wf) and not a.no_weather:
        weather = pd.read_csv(wf, index_col="timestamp"); weather.index = pd.to_datetime(weather.index, utc=True)
    W = None
else:
    d = load_processed(os.path.join("data", "processed", a.dataset))
    W = splits.development(d["W"], a.dataset)
    weather = None if (a.no_weather or d["weather"] is None) else d["weather"]
rng = np.random.default_rng(a.seed)
homes = [] if LCL else list(W.columns)
rows = []
for N in a.sizes:
    if LCL:
        groups = [[c] for c in G.columns if c.startswith(f"dev_Std_N{N}_g")]
    else:
        groups = None
    if groups is None and N > len(homes):
        continue
    from itertools import combinations
    from math import comb
    if groups is not None:
        pass
    elif comb(len(homes), N) <= a.groups:
        groups = [sorted(c) for c in combinations(homes, N)]
    else:
        seen = set()
        while len(seen) < a.groups:
            seen.add(tuple(sorted(rng.choice(homes, size=N, replace=False).tolist())))
        groups = [list(c) for c in sorted(seen)]
    for g, members in enumerate(groups):
        y = G[members[0]] if LCL else W[members].sum(axis=1, min_count=N)
        y = y[y.first_valid_index():y.last_valid_index()].asfreq("1h")
        w = None if weather is None else weather.reindex(y.index)
        y.index = y.index.tz_convert(cfg.tz)
        if w is not None:
            w.index = w.index.tz_convert(cfg.tz)
        X = features.build(y, w, cfg)
        loc_days = pd.date_range(y.index[0].date() + pd.Timedelta(days=42), y.index[-1].date(), freq="D").tz_localize(cfg.tz)
        t0 = time.time()
        if y.notna().sum() < 24 * 60:
            print(f"skip N={N} {members}: fewer than 60 days with data for all members", flush=True)
            continue
        try:
            R = baseline.conformal_calibrate(baseline.rolling_origin(y, X, loc_days, cfg), cfg).dropna(subset=["cal_lo"])
        except ValueError as e:
            print(f"skip N={N} {members}: {e}", flush=True)
            continue
        if len(R) < 24 * 14:
            print(f"skip N={N} {members}: fewer than 14 scored days", flush=True)
            continue
        m = R["actual"].mean()
        rows.append(dict(dataset=a.dataset, N=N, group=g, members=" ".join(members), hours=len(R), days=R.index.normalize().nunique(),
                         mean_kw=m,
                         cov_raw=metrics.coverage(R.actual, R.raw_lo, R.raw_hi),
                         cov_cal=metrics.coverage(R.actual, R.cal_lo, R.cal_hi),
                         width_cal_rel=float((R.cal_hi - R.cal_lo).mean() / m),
                         is_cal_rel=metrics.interval_score(R.actual, R.cal_lo, R.cal_hi) / m,
                         nmae_median=metrics.mae(R.actual, R["q0.5"]) / m,
                         secs=round(time.time() - t0)))
        os.makedirs("outputs/t1", exist_ok=True)
        pd.DataFrame(rows).to_csv(f"outputs/t1/{a.dataset}_groups_{os.path.basename(a.out)[:-3]}.csv", index=False)
        print({k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v) for k, v in rows[-1].items() if k != "members"}, flush=True)

res = pd.DataFrame(rows)
os.makedirs("outputs/t1", exist_ok=True)
res.to_csv(f"outputs/t1/{a.dataset}_groups_{os.path.basename(a.out)[:-3]}.csv", index=False)
summ = res.groupby("N")[["hours", "mean_kw", "cov_raw", "cov_cal", "width_cal_rel", "is_cal_rel", "nmae_median"]].median().round(3)
summ.insert(0, "groups", res.groupby("N").size())
print(summ.to_string())
os.makedirs("experiments/results", exist_ok=True)
with open(a.out, "a") as f:
    f.write(f"\n## {a.dataset} (development split, weather={'yes' if weather is not None else 'no'}, retrain every {a.retrain} d, seed {a.seed})\n\n")
    f.write("Medians over groups. cov = share of hours inside the band (target 0.90 after calibration); width/IS/nMAE relative to mean load.\n\n")
    f.write(summ.to_markdown() + "\n")
