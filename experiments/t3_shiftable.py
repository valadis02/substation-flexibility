"""HISTORICAL: ran with method v0.5 (old M3 event detection, removed in v0.7). Results in experiments/RESULTS.md."""
"""T3 (development data only): discrete shiftable load (washing machine, dryer, dishwasher) estimated by M3 without
sub-metering, against sub-metered truth, and against Ponocko & Milanovic-style profile transfer from sub-metered homes.

Per home, M3 (`decompose.house_parts`) gives 'ev_shift' (excess over the expected load outside meal hours) and
'ev_meal' (same in meal hours). Groups of homes are summed (hours with all members present). Estimates compared:
  m3_shift       : sum of ev_shift (the method's shiftable events)
  m3_all_events  : ev_shift + ev_meal (all discrete events, incl. cooking)
  transfer_1     : share of shiftable load by hour x day type taken from ONE sub-metered home outside the group
                   (about 5-10% sub-metering, as Ponocko & Milanovic 5%), applied to the group load; median over donors
  transfer_all   : the same share profile from ALL development homes outside the group (generous sub-metering)
  transfer_ext   : share profile from the OTHER datasets only (public sub-metered data from another country; no
                   sub-metering at all in the target network)
'zero' (no shiftable load at all) is the reference that AWFE has to beat.
Metrics: energy ratio (estimate / truth), hourly and hour-of-day-profile correlation, AWFE p90 of the shiftable share
(Ponocko & Milanovic report AWFE for their category shares; their setting is forecasting, ours is estimation).
EV homes of Pecan are excluded here (EV is T3-EV).

    python experiments/t3_shiftable.py --datasets refit plegma pecan_austin pecan_newyork ukdale
"""
import argparse, os
import numpy as np
import pandas as pd
from dataclasses import replace
from flexsub import Config, splits, metrics
from flexsub.appliances import category
from flexsub.data import load_processed
from flexsub.decompose import house_parts

TZ = {"refit": ("Europe/London", 52.77), "ukdale": ("Europe/London", 51.5), "plegma": ("Europe/Athens", 37.98),
      "pecan_austin": ("America/Chicago", 30.27), "pecan_newyork": ("America/New_York", 42.44)}
ap = argparse.ArgumentParser()
ap.add_argument("--datasets", nargs="+", default=["refit"])
ap.add_argument("--sizes", type=int, nargs="+", default=[5, 10])
ap.add_argument("--groups", type=int, default=5)
a = ap.parse_args()
rng = np.random.default_rng(0)
rows = []
DATA = {}
for ds in a.datasets:                       # phase 1: per-home truth and M3 parts
    tz, lat = TZ[ds]
    cfg = Config(tz=tz, latitude=lat)
    d = load_processed(os.path.join("data", "processed", ds))
    W = splits.development(d["W"], ds)
    truth, parts = {}, {}
    for h in W.columns:
        A = d["appliances"][h].reindex(W.index)
        if "ev" in A.columns and A["ev"].mean() > 0.05:
            continue
        sh = [c for c in A.columns if category(c) == "shiftable"]
        if not sh or W[h].notna().sum() < 24 * 60 or d["weather"] is None:
            continue
        t = A[sh].sum(axis=1, min_count=len(sh)); t[W[h].isna()] = np.nan
        y = W[h][W[h].first_valid_index():W[h].last_valid_index()].asfreq("1h")
        w = d["weather"].reindex(y.index)
        P = house_parts(y.tz_convert(tz), w.tz_convert(tz), cfg)
        P.index = P.index.tz_convert("UTC")
        truth[h], parts[h] = t, P.reindex(W.index)
    homes = sorted(truth)
    T, Y = pd.DataFrame(truth), W[homes]
    loc = W.index.tz_convert(tz)
    key = pd.Series(loc.hour * 2 + (loc.dayofweek >= 5), index=W.index)       # hour x day type (local)
    share_home = {h: (T[h].groupby(key).sum() / Y[h].where(T[h].notna()).groupby(key).sum()) for h in homes}
    DATA[ds] = dict(T=T, Y=Y, key=key, parts=parts, homes=homes, share_home=share_home,
                    share_ds=pd.concat(share_home.values(), axis=1).median(axis=1))
    print(ds, "homes with shiftable truth:", len(homes), flush=True)

from itertools import combinations
from math import comb
for ds, D in DATA.items():                  # phase 2: groups
    T, Y, key, parts, homes, share_home = D["T"], D["Y"], D["key"], D["parts"], D["homes"], D["share_home"]
    ext = [DATA[o]["share_ds"] for o in DATA if o != ds]
    share_ext = pd.concat(ext, axis=1).median(axis=1) if ext else None
    sizes = sorted(set([n for n in a.sizes if n < len(homes)] + [len(homes)]))
    for N in sizes:
        if comb(len(homes), N) <= a.groups:
            groups = [list(c) for c in combinations(homes, N)]
        else:
            seen = set()
            while len(seen) < a.groups:
                seen.add(tuple(sorted(rng.choice(homes, size=N, replace=False).tolist())))
            groups = [list(c) for c in sorted(seen)]
        for g, mem in enumerate(groups):
            m = Y[mem].notna().all(axis=1) & T[mem].notna().all(axis=1)
            if m.sum() < 24 * 30:
                continue
            y, tt = Y.loc[m, mem].sum(axis=1), T.loc[m, mem].sum(axis=1)
            ev_s = pd.DataFrame({h: parts[h].loc[m, "ev_shift"] for h in mem}).sum(axis=1)
            ev_m = pd.DataFrame({h: parts[h].loc[m, "ev_meal"] for h in mem}).sum(axis=1)
            k = key[m]
            others = [h for h in homes if h not in mem]
            est = {"zero": 0 * y, "m3_shift": ev_s, "m3_all_events": ev_s + ev_m}
            if share_ext is not None:
                est["transfer_ext"] = y * k.map(share_ext).fillna(0).values
            if others:
                est["transfer_all"] = y * k.map(pd.concat([share_home[h] for h in others], axis=1).median(axis=1)).fillna(0).values

            def score(e):
                c = lambda u, v: float(np.corrcoef(u, v)[0, 1]) if np.std(u) > 0 else np.nan
                return dict(energy_ratio=float(e.sum() / tt.sum()), corr_hourly=c(e, tt),
                            corr_profile=c(e.groupby(k).mean(), tt.groupby(k).mean()),
                            awfe_p90=metrics.awfe_p90(e / y, tt / y))
            for name, e in est.items():
                rows.append(dict(dataset=ds, N=N, group=g, method=name, hours=int(m.sum()), **score(e)))
            if others:
                med = pd.DataFrame([score(y * k.map(share_home[h]).fillna(0).values) for h in others]).median()
                rows.append(dict(dataset=ds, N=N, group=g, method="transfer_1", hours=int(m.sum()), **med.to_dict()))
            print(ds, N, g, {r["method"]: round(r["energy_ratio"], 2) for r in rows[-len(est) - 1:]}, flush=True)

R = pd.DataFrame(rows)
os.makedirs("outputs/t3", exist_ok=True)
tag = "_".join(a.datasets)
R.to_csv(f"outputs/t3/shiftable_{tag}.csv", index=False)
S = R.groupby(["dataset", "N", "method"])[["energy_ratio", "corr_hourly", "corr_profile", "awfe_p90"]].median().round(3)
print(S.to_string())
with open("experiments/results/t3_shiftable_dev.md", "a") as f:
    f.write(f"\n## {', '.join(a.datasets)} (development split; medians over groups)\n\n" + S.to_markdown() + "\n")
