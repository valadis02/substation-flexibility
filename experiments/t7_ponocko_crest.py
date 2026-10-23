"""T7: Ponocko & Milanovic (2018) reproduced on synthetic CREST households, and compared with our M3 (shiftable, design
A) on the same households.

Data (scripts/crest_generate.py): N homes, 1-minute P, Q and the six load categories of the paper (Table I).
Ponocko: for each test day d, the ANN is trained on days d-7..d-1 of the sub-metered homes (coverage c: a random
c x N subset; c = 0: an independent CREST population, i.e. "statistical" training data from another population of
the same model - the most favourable version of their 0% case) and applied to the aggregate P, Q of all N homes on
day d. AWFE (eq. 9) in p.u. of the average monthly active load; the paper reports the 90th percentile over the
1440 minutes of the test day.
Ours (M3 design A; needs ~21 days of history per home, hence test days from day 24): per home, from its hourly total load only (no sub-metering, no reactive power), `events_home`;
summed over the homes. CREST has no weather input (space heating follows the month), so M2 has nothing to find and
is not used. Hourly only.
Common target: CTIM1 (washing machine, tumble dryer, washer dryer, dish washer, vacuum) - the paper's
"cycle-type" category and the closest to our "shiftable". The paper's headline (controllable = CTIM1 + QTIM1 + RC) is
reported for Ponocko only, because our method does not estimate cold appliances or space heating from CREST.

    python experiments/t7_ponocko_crest.py --data data/crest --indep data/crest_indep
"""
import argparse, glob, os, time
import numpy as np
import pandas as pd
from flexsub import ponocko as pm
from flexsub.shiftable import events_home

ap = argparse.ArgumentParser()
ap.add_argument("--data", default="data/crest")
ap.add_argument("--indep", default="data/crest_indep", help="independent population for the 0%% case")
ap.add_argument("--coverage", type=float, nargs="+", default=[0.05, 0.10, 0.20, 1.0])
ap.add_argument("--draws", type=int, default=3, help="random sub-metered subsets per coverage (< 100%%)")
ap.add_argument("--test-days", type=int, nargs="+", default=[24, 28, 32, 36, 40, 44, 48, 52])
ap.add_argument("--n-homes", type=int, default=None, help="use the first n homes (default all)")
ap.add_argument("--out", default="experiments/results/t7_ponocko_crest")
ap.add_argument("--sampling", choices=["random", "stratified"], default="random",
                help="stratified: sub-metered homes drawn with the population's mix of household sizes")
ap.add_argument("--epochs", type=int, default=300)
ap.add_argument("--restarts", type=int, default=1, help="random initialisations; the one with the lowest training error is kept")
ap.add_argument("--no-indep", action="store_true")
ap.add_argument("--seed", type=int, default=2026)
a = ap.parse_args()
CAT = ["CTIM1", "QTIM1", "RC", "RUC", "SMPS", "Lighting"]
M = 1440

files = sorted(glob.glob(os.path.join(a.data, "home_*_1min.npz")))[: a.n_homes]
N = len(files)
rs = np.random.default_rng(a.seed)
occ = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(a.data, "homes_*.csv")))]).set_index("home").occupants
occ = occ.reindex([int(os.path.basename(f)[5:9]) for f in files]).to_numpy()


def draw(n):
    if a.sampling == "random":
        return rs.choice(N, n, replace=False)
    out = []                                   # proportional allocation by household size, largest remainder
    sizes = np.unique(occ); quota = np.array([(occ == s).mean() * n for s in sizes])
    k = np.floor(quota).astype(int); k[np.argsort(quota - k)[::-1][: n - k.sum()]] += 1
    for s, m in zip(sizes, k):
        out += rs.choice(np.flatnonzero(occ == s), m, replace=False).tolist()
    return np.array(out)


subsets = {(c, k): (np.arange(N) if c >= 1 else draw(int(round(c * N))))
           for c in a.coverage for k in range(1 if c >= 1 else a.draws)}
member = {key: np.zeros(N, bool) for key in subsets}
for key, idx in subsets.items():
    member[key][idx] = True


def load_pop(paths, groups=None, hourly=False):
    """Sum P, Q, categories over all homes and over each group (dict name -> bool mask); hourly P per home."""
    agg = {"all": None}
    agg.update({g: None for g in (groups or {})})
    Ph = []
    for i, f in enumerate(paths):
        z = np.load(f)
        x = np.vstack([z["P"][None].astype(np.float64), z["Q"][None].astype(np.float64), z["per_cat"].astype(np.float64)]) / 1000.0
        for g in agg:
            if g == "all" or groups[g][i]:
                agg[g] = x.copy() if agg[g] is None else agg[g] + x
        if hourly:
            Ph.append(x[0].reshape(-1, 60).mean(axis=1))
    return agg, (np.array(Ph) if hourly else None)


t0 = time.time()
agg, Ph = load_pop(files, member, hourly=True)
print(f"loaded {N} homes in {time.time() - t0:.0f}s", flush=True)
ind_files = sorted(glob.glob(os.path.join(a.indep, "home_*_1min.npz")))
if ind_files and not a.no_indep:
    agg_ind, _ = load_pop(ind_files)
    agg[("indep", 0)] = agg_ind["all"]
    subsets[("indep", 0)] = None
A = agg["all"]
P, Q, C = A[0], A[1], A[2:].T
days = len(P) // M
idx = pd.date_range("2026-01-01", periods=days * 24, freq="h", tz="UTC")   # CREST runs in local time; UTC = no DST

# ---- ours: M3 design A per home, hourly ----
t0 = time.time()
ours_h = np.zeros(days * 24)
for i in range(N):
    e = events_home(pd.Series(Ph[i], index=idx)).fillna(0).to_numpy()
    ours_h += e
print(f"ours: {time.time() - t0:.0f}s", flush=True)

rows = []
hour = lambda v: v.reshape(-1, 60).mean(axis=1)
for d in a.test_days:
    tr, te = slice((d - 7) * M, d * M), slice(d * M, (d + 1) * M)
    mon = slice(max(0, d - 29) * M, (d + 1) * M)                 # the "month": up to 30 days ending with the test day
    pmean, pmax = P[mon].mean(), P[mon].max()
    true_min = {"CTIM1": C[te, 0], "controllable": C[te, :3].sum(1)}
    # reference: zero estimate
    for tgt, tv in true_min.items():
        rows.append(dict(day=d, method="zero", coverage=np.nan, draw=0, target=tgt,
                         awfe_p90_min=np.quantile(pm.awfe(0 * tv, tv, pmean), .9),
                         awfe_p90_hour=np.quantile(pm.awfe(0 * hour(tv), hour(tv), pmean), .9)))
    # ours (hourly)
    oh = ours_h[d * 24:(d + 1) * 24]
    rows.append(dict(day=d, method="ours_M3_A", coverage=0.0, draw=0, target="CTIM1",
                     awfe_p90_hour=np.quantile(pm.awfe(oh, hour(true_min["CTIM1"]), pmean), .9),
                     energy_ratio=oh.sum() / hour(true_min["CTIM1"]).sum()))
    # Ponocko
    for key in subsets:
        S = agg[key]
        Ps, Qs, Cs = S[0], S[1], S[2:].T
        X = pm.inputs(Ps[tr], Qs[tr], Ps[mon].max())
        T = pm.shares(Cs[tr], Ps[tr])
        ok = np.isfinite(T).all(1)
        t1 = time.time()
        nets = [pm.PMNet(seed=d * 100 + r, epochs=a.epochs).fit(X[ok], T[ok]) for r in range(a.restarts)]
        net = min(nets, key=lambda n_: n_.sse)
        W = net.predict(pm.inputs(P[te], Q[te], pmax))
        est = {"CTIM1": W[:, 0] * P[te], "controllable": W[:, :3].sum(1) * P[te]}
        cov = 0.0 if key[0] == "indep" else key[0]
        for tgt, tv in true_min.items():
            rows.append(dict(day=d, method="ponocko" if key[0] != "indep" else "ponocko_0pct_indep", coverage=cov, draw=key[1],
                             target=tgt, awfe_p90_min=np.quantile(pm.awfe(est[tgt], tv, pmean), .9),
                             awfe_p90_hour=np.quantile(pm.awfe(hour(est[tgt]), hour(tv), pmean), .9),
                             energy_ratio=est[tgt].sum() / tv.sum(), epochs=net.epochs_run, fit_s=time.time() - t1))
        print(d, key, {r["target"]: (round(r["awfe_p90_min"], 3), round(r["awfe_p90_hour"], 3)) for r in rows[-2:]},
              f"{time.time() - t1:.0f}s", flush=True)
    pd.DataFrame(rows).to_csv(a.out + ".csv", index=False)

R = pd.DataFrame(rows)
R.to_csv(a.out + ".csv", index=False)
S = R.groupby(["target", "method", "coverage"], dropna=False)[["awfe_p90_min", "awfe_p90_hour", "energy_ratio"]].median().round(3)
print(S.to_string())
with open(a.out + ".md", "w") as f:
    f.write(f"# T7: Ponocko & Milanovic (2018) vs ours on CREST ({N} homes, {len(a.test_days)} test days)\n\n"
            "Median over test days (and sub-metered draws) of the 90th-percentile AWFE (p.u. of the average monthly load).\n\n"
            + S.to_markdown() + "\n")
