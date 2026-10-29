"""T3 v2 (development data only): the two candidate M3 designs for shiftable appliance load, side by side.

A (data only): `shiftable.events_home` per home, summed over the group.
B (profile bank): `shiftable.profile_estimate` with a bank built from the OTHER datasets (leave-one-dataset-out);
   dataset choice: mean of the bank / nearest load shape / similarity-weighted; level: share x load / kW per home x homes.
References: zero, and the old M3 events (v0.6 `decompose.house_parts`, ev_shift).
Metrics: energy ratio, hourly and hour-of-day profile correlation, AWFE p90 and AWFE skill = 1 - AWFE / AWFE(zero).

    python experiments/t3_shiftable_v2.py --datasets refit plegma pecan_austin pecan_newyork ukdale
"""
import argparse, os
import numpy as np
import pandas as pd
from itertools import combinations
from math import comb
from flexsub import Config, splits, metrics, shiftable
from flexsub.appliances import category
from flexsub.data import load_processed
from flexsub.decompose import house_parts

TZ = {"refit": ("Europe/London", 52.77), "ukdale": ("Europe/London", 51.5), "plegma": ("Europe/Athens", 37.98),
      "pecan_austin": ("America/Chicago", 30.27), "pecan_newyork": ("America/New_York", 42.44)}
ap = argparse.ArgumentParser()
ap.add_argument("--datasets", nargs="+", default=["refit", "plegma", "pecan_austin", "pecan_newyork", "ukdale"])
ap.add_argument("--sizes", type=int, nargs="+", default=[5, 10])
ap.add_argument("--groups", type=int, default=5)
ap.add_argument("--with-water-heaters", action="store_true", help="count electric storage water heaters as shiftable")
a = ap.parse_args()
rng = np.random.default_rng(0)

DATA = {}
for ds in a.datasets:
    tz, lat = TZ[ds]
    cfg = Config(tz=tz, latitude=lat)
    d = load_processed(os.path.join("data", "processed", ds))
    W = splits.development(d["W"], ds)
    T, A_ev, A_ev2, old = {}, {}, {}, {}
    for h in W.columns:
        Ap = d["appliances"][h].reindex(W.index)
        if "ev" in Ap.columns and Ap["ev"].mean() > 0.05:
            continue
        sh = [c for c in Ap.columns if category(c, ds if a.with_water_heaters else None) == "shiftable"]
        if not sh or W[h].notna().sum() < 24 * 60 or d["weather"] is None:
            continue
        t = Ap[sh].sum(axis=1, min_count=len(sh)); t[W[h].isna()] = np.nan
        y = W[h][W[h].first_valid_index():W[h].last_valid_index()].asfreq("1h")
        T[h] = t
        A_ev[h] = shiftable.events_home(y).reindex(W.index)
        # A2: remove the home's weather-dependent load (M2, gated, fitted on this home's development data) first
        from flexsub import features, thermal_dd
        wy = d["weather"].reindex(y.index)
        okk = (y.notna() & wy["temp"].notna()).to_numpy()
        dd = y.index.tz_convert(tz).normalize()
        band = features.balance_points(wy["temp"].groupby(dd).mean(), y.groupby(dd).mean())
        wl = pd.Series(0.0, index=y.index)
        if not np.isnan(band[0]):
            wl[okk] = thermal_dd.fit_predict(y, wy, tz, band, okk, okk, gate=True)
        A_ev2[h] = shiftable.events_home(y, weather_load=wl).reindex(W.index)
        old[h] = pd.Series(np.nan, index=W.index)   # old M3 events (v0.6) were removed in v0.7; see RESULTS.md T3 v2
    homes = sorted(T)
    T = pd.DataFrame(T)
    DATA[ds] = dict(tz=tz, Y=W[homes], T=T, A=pd.DataFrame(A_ev), A2=pd.DataFrame(A_ev2), old=pd.DataFrame(old), homes=homes,
                    bank=shiftable.bank_entry(W[homes], T, tz) if homes else None)
    print(ds, "homes:", len(homes), flush=True)

rows = []
for ds, D in DATA.items():
    homes, Y, T, tz = D["homes"], D["Y"], D["T"], D["tz"]
    if len(homes) < 3:
        continue
    bank = {o: DATA[o]["bank"] for o in DATA if o != ds and DATA[o]["bank"] is not None}
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
            m = Y[mem].notna().all(axis=1) & T[mem].notna().all(axis=1) & D["A"][mem].notna().all(axis=1)
            if m.sum() < 24 * 30:
                continue
            y, tt = Y.loc[m, mem].sum(axis=1), T.loc[m, mem].sum(axis=1)
            k = shiftable._key(y.index, tz)
            est = {"zero": 0 * y,
                   "A_events": D["A"].loc[m, mem].sum(axis=1), "A2_events_minus_weather": D["A2"].loc[m, mem].sum(axis=1)}
            day = y.index.tz_convert(tz).normalize()
            for sel in ("mean", "weighted"):
                lvl = est["A2_events_minus_weather"].groupby(day).sum().mean()
                est[f"B_{sel}_levelA2"], _ = shiftable.profile_scaled(y, N, bank, tz, lvl, select=sel)
            chosen = {}
            for sel in ("mean", "shape", "weighted"):
                for lev in ("share", "abs"):
                    e, wts = shiftable.profile_estimate(y, N, bank, tz, select=sel, level=lev)
                    est[f"B_{sel}_{lev}"] = e
                    chosen[sel] = wts.idxmax()
            zero_awfe = metrics.awfe_p90(0 * y / y, tt / y)
            # Ponocko-style reference: share profile from ONE sub-metered home outside the group (median over donors)
            others = [h for h in homes if h not in mem]
            if others:
                Yo, To = D["Y"][others], T[others]
                kk = shiftable._key(D["Y"].index, tz)
                aws = []
                for h in others:
                    sh = To[h].groupby(kk).sum() / Yo[h].where(To[h].notna()).groupby(kk).sum()
                    aws.append(metrics.awfe_p90((y * k.map(sh).fillna(0).values) / y, tt / y))
                rows.append(dict(dataset=ds, N=N, group=g, method="transfer_1_submetered_home", hours=int(m.sum()),
                                 awfe_p90=float(np.median(aws)), awfe_skill=1 - float(np.median(aws)) / zero_awfe))
            for name, e in est.items():
                c = lambda u, v: float(np.corrcoef(u, v)[0, 1]) if np.std(u) > 0 else np.nan
                aw = metrics.awfe_p90(e / y, tt / y)
                rows.append(dict(dataset=ds, N=N, group=g, method=name, hours=int(m.sum()),
                                 energy_ratio=float(e.sum() / tt.sum()), corr_hourly=c(e, tt),
                                 corr_profile=c(e.groupby(k).mean(), tt.groupby(k).mean()),
                                 awfe_p90=aw, awfe_skill=1 - aw / zero_awfe, nearest=chosen["shape"]))
            print(ds, N, g, "nearest:", chosen["shape"], {r["method"]: round(r["awfe_skill"], 2) for r in rows[-len(est):]}, flush=True)

R = pd.DataFrame(rows)
os.makedirs("outputs/t3", exist_ok=True)
suffix = "_wh" if a.with_water_heaters else ""
R.to_csv(f"outputs/t3/shiftable_v2{suffix}.csv", index=False)
big = R[R.N == R.groupby("dataset").N.transform("max")]
S = big.groupby(["dataset", "method"])[["energy_ratio", "corr_hourly", "corr_profile", "awfe_p90", "awfe_skill"]].median().round(3)
S2 = R.groupby(["method"])[["energy_ratio", "corr_profile", "awfe_skill"]].median().round(3)
near = big.groupby("dataset").nearest.first()
print(S.to_string()); print(S2.to_string()); print(near.to_string())
with open(f"experiments/results/t3_shiftable_v2{suffix}_dev.md", "w") as f:
    f.write(f"# T3 v2 (development; leave-one-dataset-out bank{'; water heaters counted as shiftable' if suffix else ''})\n\n## Largest group per dataset\n\n" + S.to_markdown() +
            "\n\n## All groups (median)\n\n" + S2.to_markdown() + "\n\n## Nearest dataset chosen by load shape\n\n" + near.to_markdown() + "\n")
