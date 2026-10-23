"""T8: final method (v0.8) on real sub-metered data, real vs estimated, development data only.

Groups: all development homes of a dataset that are present together (REFIT 13, Pecan Austin 16, Pecan New York 15;
EV homes and PV-only REFIT homes excluded as in the split). UK-DALE homes never overlap in time, so each is a group of
one home. The group load is the sum over the homes; the method sees only the hourly total of each home and weather.

Estimates: weather-dependent (M2, aggregate degree-day model, leave-one-day-out) and shiftable (M3 design A per home
after removing the home's own weather load), allocated as in `decompose.decompose_substation`.
Truth: weather-dependent = AC / furnace / heaters (as in T4); shiftable = washing machine, dryer, dishwasher and
electric storage water heaters; flexible = both.
Error: AWFE (Ponocko & Milanovic, eq. 9) = |estimate - truth| in p.u. of the 30-day mean load of the group, hourly.

Also (numbers only, `--ponocko`): their ANN adapted to what these datasets have - hourly active power only (no Q, no
1-minute data), trained on the 7 days before each test day on the sub-metered homes of the group (1 home, 20%, 50%),
targets = shares of shiftable / weather-dependent / rest, applied to the group total.

    python experiments/t8_real_figures.py [--ponocko]
"""
import argparse, os
import numpy as np
import pandas as pd
from flexsub import Config, splits, ponocko as pm
from flexsub.appliances import category
from flexsub.data import load_processed
from flexsub.decompose import decompose_substation
from flexsub.thermal import thermal_dd_loo

ap = argparse.ArgumentParser()
ap.add_argument("--ponocko", action="store_true")
ap.add_argument("--out", default="experiments/results/t8_real")
a = ap.parse_args()
DS = {"refit": ("Europe/London", 52.77, "REFIT (13 homes)"), "pecan_austin": ("America/Chicago", 30.27, "Pecan Austin (16 homes)"),
      "pecan_newyork": ("America/New_York", 42.44, "Pecan New York (15 homes)"), "ukdale": ("Europe/London", 51.5, "UK-DALE (single homes)")}
THERMAL = lambda c, ds: category(c, ds) == "thermal" or c in ("ac", "furnace", "heater") or c.startswith("ac_")
os.makedirs("outputs/t8", exist_ok=True)
res, series, prow = [], {}, []


def evaluate(name, ds, y, est, tru, tz):
    m30 = y.rolling(24 * 30, min_periods=24 * 7, center=True).mean()
    for part in ("flexible", "shiftable", "weather"):
        e = (est[part] - tru[part]).abs() / m30
        z = tru[part].abs() / m30
        day = y.index.tz_convert(tz).normalize()
        dp90 = e.groupby(day).quantile(0.9)
        res.append(dict(group=name, dataset=ds, part=part, hours=int(e.notna().sum()), awfe_p90_all=float(e.quantile(0.9)),
                        awfe_p90_daily_median=float(dp90.median()), zero_p90_all=float(z.quantile(0.9)),
                        energy_ratio=float(est[part].sum() / tru[part].sum()) if tru[part].sum() > 0 else np.nan,
                        corr=float(np.corrcoef(est[part], tru[part])[0, 1]) if tru[part].std() > 0 else np.nan))
        series.setdefault(ds, {}).setdefault(part, []).append(pd.DataFrame({"e": e, "z": z}))


for ds, (tz, lat, label) in DS.items():
    cfg = Config(tz=tz, latitude=lat)
    d = load_processed(os.path.join("data", "processed", ds))
    W = splits.development(d["W"], ds)
    homes, TS, TT = [], {}, {}
    for h in W.columns:
        Ap = d["appliances"][h].reindex(W.index)
        if "ev" in Ap.columns and Ap["ev"].mean() > 0.05:
            continue
        sh = [c for c in Ap.columns if category(c, ds) == "shiftable"]
        if not sh:
            continue
        th = [c for c in Ap.columns if THERMAL(c, ds)]
        TS[h] = Ap[sh].sum(axis=1, min_count=len(sh))
        TT[h] = Ap[th].sum(axis=1) if th else 0 * TS[h]
        homes.append(h)
    groups = [[h] for h in homes] if ds == "ukdale" else [homes]
    for g in groups:
        ok = W[g].notna().all(axis=1) & pd.DataFrame({h: TS[h] for h in g}).notna().all(axis=1)
        if ok.sum() < 24 * 60:
            continue
        idx = W.index[ok]
        Wg = W.loc[idx, g]
        y = Wg.sum(axis=1)
        w = d["weather"].reindex(idx)
        days = pd.Index(idx.tz_convert(tz).normalize().unique())
        days = [pd.Timestamp(x).tz_convert("UTC") for x in days]
        th_est = thermal_dd_loo(y, w, days, cfg)
        D = decompose_substation(Wg, w, th_est, cfg)
        name = f"{ds}:{g[0]}" if ds == "ukdale" else ds
        y = D["actual"]
        est = pd.DataFrame({"weather": D["thermal"], "shiftable": D["shiftable"]})
        tru = pd.DataFrame({"weather": sum(TT[h].reindex(y.index) for h in g), "shiftable": sum(TS[h].reindex(y.index) for h in g)})
        est["flexible"], tru["flexible"] = est.sum(axis=1), tru.sum(axis=1)
        evaluate(name, ds, y, est, tru, tz)
        pd.concat({"actual": y, **{f"est_{k}": v for k, v in est.items()}, **{f"true_{k}": v for k, v in tru.items()}}, axis=1) \
            .to_csv(f"outputs/t8/{name.replace(':', '_')}.csv.gz")
        print(name, len(g), "homes", int(ok.sum() / 24), "days", flush=True)

        if a.ponocko and ds != "ukdale":
            rs = np.random.default_rng(7)
            Tsh = pd.DataFrame({h: TS[h].reindex(y.index) for h in g}); Tth = pd.DataFrame({h: TT[h].reindex(y.index) for h in g})
            Y = Wg.reindex(y.index)
            loc_days = y.index.tz_convert(tz).normalize()
            ud = pd.Index(loc_days.unique())
            m30 = y.rolling(24 * 30, min_periods=24 * 7, center=True).mean()
            for cov_name, k in (("1 home", 1), ("20%", max(1, round(0.2 * len(g)))), ("50%", max(1, round(0.5 * len(g))))):
                for draw in range(3):
                    sub = rs.choice(g, k, replace=False).tolist()
                    ys, ss, ts = Y[sub].sum(axis=1), Tsh[sub].sum(axis=1), Tth[sub].sum(axis=1)
                    E = {p: [] for p in ("flexible", "shiftable", "weather")}
                    for i in range(7, len(ud), 7):
                        trm = (loc_days >= ud[i - 7]) & (loc_days < ud[i]); tem = loc_days == ud[i]
                        if trm.sum() < 24 * 6 or tem.sum() < 24:
                            continue
                        mon = (loc_days > ud[max(0, i - 30)]) & (loc_days <= ud[i])
                        X = (ys[trm] / ys[mon].max()).to_numpy()[:, None]
                        T = np.column_stack([ss[trm] / ys[trm], ts[trm] / ys[trm], 1 - (ss[trm] + ts[trm]) / ys[trm]])
                        okr = np.isfinite(T).all(1) & np.isfinite(X).all(1)
                        net = pm.PMNet(seed=i).fit(X[okr], T[okr])
                        Wt = net.predict((y[tem] / y[mon].max()).to_numpy()[:, None])
                        es = {"shiftable": Wt[:, 0] * y[tem].to_numpy(), "weather": Wt[:, 1] * y[tem].to_numpy()}
                        es["flexible"] = es["shiftable"] + es["weather"]
                        for p in E:
                            E[p].append(np.abs(es[p] - tru[p][tem].to_numpy()) / m30[tem].to_numpy())
                    for p in E:
                        v = np.concatenate(E[p]) if E[p] else np.array([np.nan])
                        ours = (est[p] - tru[p]).abs() / m30
                        tdays = ud[7::7]
                        ours_same = ours[np.isin(loc_days, tdays)]
                        prow.append(dict(dataset=ds, coverage=cov_name, homes=k, draw=draw, part=p, test_days=len(E[p]),
                                         ponocko_awfe_p90=float(np.nanquantile(v, 0.9)), ours_awfe_p90_same_days=float(ours_same.quantile(0.9))))
                    print(ds, cov_name, draw, {r["part"]: round(r["ponocko_awfe_p90"], 3) for r in prow[-3:]}, flush=True)

R = pd.DataFrame(res)
R.to_csv(a.out + ".csv", index=False)
S = R.groupby(["dataset", "part"])[["hours", "awfe_p90_all", "zero_p90_all", "awfe_p90_daily_median", "energy_ratio", "corr"]] \
    .agg({"hours": "sum", "awfe_p90_all": "median", "zero_p90_all": "median", "awfe_p90_daily_median": "median",
          "energy_ratio": "median", "corr": "median"}).round(3)
print(S.to_string())
txt = "# T8: final method (v0.8) on real data, development period\n\nAWFE in p.u. of the 30-day mean load (UK-DALE: median over single homes).\n\n" + S.to_markdown() + "\n"
if prow:
    P = pd.DataFrame(prow)
    P.to_csv(a.out + "_ponocko.csv", index=False)
    PS = P.groupby(["dataset", "part", "coverage"])[["homes", "ponocko_awfe_p90", "ours_awfe_p90_same_days"]].median().round(3)
    print(PS.to_string())
    txt += "\n## Ponocko-style ANN adapted to hourly P only (numbers only)\n\n" + PS.to_markdown() + "\n"
with open(a.out + ".md", "w") as f:
    f.write(txt)
pd.to_pickle(series, "outputs/t8/series.pkl")
