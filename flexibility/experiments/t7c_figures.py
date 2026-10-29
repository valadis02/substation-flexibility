"""T7c: our analogue of Ponocko & Milanovic (2018), Fig. 6 (CDF of AWFE of the controllable load for several
sub-metering coverages) and Fig. 7 (load composition of one day, actual vs estimated with 5% coverage), with our
method added.

Fairness: CREST has no weather input (space heating follows the month), so our M2 cannot find it. In real data M2
estimates the weather-dependent load, so here space heating ("Other electric space heating", "Storage heaters") is
given to our method as known: it is removed from each home's load before M3 (as M2 is in the pipeline) and added to
our controllable estimate. Cold appliances and water heaters do not depend on weather and are not given.
Their method is run as in the paper (no weather, P and Q only).

Step 1 (fits, can be split over processes):  python experiments/t7c_figures.py run --test-days 24 28 32 36
Step 2 (figures and table):                   python experiments/t7c_figures.py plot
"""
import argparse, glob, os, sys, time
import numpy as np
import pandas as pd
from flexsub import ponocko as pm
from flexsub.shiftable import events_home

ap = argparse.ArgumentParser()
ap.add_argument("step", choices=["run", "plot"])
ap.add_argument("--data", default="data/crest")
ap.add_argument("--indep", default="data/crest_indep")
ap.add_argument("--coverage", type=float, nargs="+", default=[0.05, 0.10, 0.20, 0.50, 1.0])
ap.add_argument("--test-days", type=int, nargs="+", default=[24, 28, 32, 36, 40, 44, 48, 52])
ap.add_argument("--fig-day", type=int, default=40)
ap.add_argument("--out", default="outputs/t7c")
a = ap.parse_args()
M = 1440
HEAT = ["Other electric space heating", "Storage heaters"]
CAT = ["CTIM1", "QTIM1", "RC", "RUC", "SMPS", "Lighting"]
os.makedirs(a.out, exist_ok=True)

if a.step == "run":
    files = sorted(glob.glob(os.path.join(a.data, "home_*_1min.npz")))
    N = len(files)
    rs = np.random.default_rng(2026)
    subsets = {c: (np.arange(N) if c >= 1 else rs.choice(N, int(round(c * N)), replace=False)) for c in a.coverage}
    agg = {c: 0 for c in subsets}; ALL = 0; Ph, Hh = [], []
    for i, f in enumerate(files):
        z = np.load(f)
        x = np.vstack([z["P"][None], z["Q"][None], z["per_cat"]]).astype(np.float64) / 1000.0
        ALL = ALL + x
        for c, idx in subsets.items():
            if i in set(idx.tolist()) if c < 1 else True:
                agg[c] = agg[c] + x
        hc = pd.read_csv(f.replace("_1min.npz", ".csv.gz"))
        Hh.append(hc[[c for c in HEAT if c in hc]].sum(axis=1).to_numpy() if any(c in hc for c in HEAT) else np.zeros(len(hc)))
        Ph.append(x[0].reshape(-1, 60).mean(axis=1))
    ind = sorted(glob.glob(os.path.join(a.indep, "home_*_1min.npz")))
    if ind:
        IND = 0
        for f in ind:
            z = np.load(f)
            IND = IND + np.vstack([z["P"][None], z["Q"][None], z["per_cat"]]).astype(np.float64) / 1000.0
        agg[0.0] = IND
    P, Q = ALL[0], ALL[1]
    days = len(P) // M
    idx = pd.date_range("2026-01-01", periods=days * 24, freq="h", tz="UTC")
    heat = np.sum(Hh, axis=0)
    wet = 0
    for p, h in zip(Ph, Hh):   # M3 after removing the (known) weather-dependent part
        wet = wet + events_home(pd.Series(p - h, index=idx)).fillna(0).to_numpy()
    np.savez_compressed(os.path.join(a.out, "truth_ours.npz"), P=P, C=ALL[2:], heat_h=heat, wet_h=wet)
    for d in a.test_days:
        tr, te = slice((d - 7) * M, d * M), slice(d * M, (d + 1) * M)
        mon = slice(max(0, d - 29) * M, (d + 1) * M)
        for c, S in agg.items():
            t0 = time.time()
            X = pm.inputs(S[0][tr], S[1][tr], S[0][mon].max())
            T = pm.shares(S[2:].T[tr], S[0][tr]); ok = np.isfinite(T).all(1)
            net = pm.PMNet(seed=d).fit(X[ok], T[ok])
            W = net.predict(pm.inputs(P[te], Q[te], P[mon].max()))
            np.save(os.path.join(a.out, f"W_{c:.2f}_d{d}.npy"), W.astype(np.float32))
            print(d, c, f"{time.time() - t0:.0f}s", flush=True)
    sys.exit()

# ---------------- plot ----------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

Z = np.load(os.path.join(a.out, "truth_ours.npz"))
P, C, heat_h, wet_h = Z["P"], Z["C"], Z["heat_h"], Z["wet_h"]
H = lambda v: v.reshape(-1, 60).mean(axis=-1)
covs = sorted({float(os.path.basename(f).split("_")[1]) for f in glob.glob(os.path.join(a.out, "W_*.npy"))})
targets = {"controllable": lambda X: X[0] + X[1] + X[2], "wet": lambda X: X[0]}
rows, cdf = [], {t: {} for t in targets}
for d in a.test_days:
    te = slice(d * M, (d + 1) * M); mon = slice(max(0, d - 29) * M, (d + 1) * M); pmean = P[mon].mean()
    ours = {"wet": wet_h[d * 24:(d + 1) * 24], "controllable": wet_h[d * 24:(d + 1) * 24] + heat_h[d * 24:(d + 1) * 24]}
    for t, f in targets.items():
        true_h = H(f(C[:, te]))
        e = pm.awfe(ours[t], true_h, pmean)
        cdf[t].setdefault("ours", []).append(e); rows.append(dict(day=d, target=t, method="ours (0%)", awfe_p90=np.quantile(e, .9)))
        e0 = pm.awfe(0 * true_h, true_h, pmean)
        cdf[t].setdefault("zero", []).append(e0); rows.append(dict(day=d, target=t, method="zero", awfe_p90=np.quantile(e0, .9)))
        for c in covs:
            fp = os.path.join(a.out, f"W_{c:.2f}_d{d}.npy")
            if not os.path.exists(fp):
                continue
            W = np.load(fp).astype(np.float64).T
            est_h = H(f(W) * P[te])
            e = pm.awfe(est_h, true_h, pmean)
            name = "Ponocko 0% (indep. CREST)" if c == 0 else f"Ponocko {int(round(c * 100))}%"
            cdf[t].setdefault(name, []).append(e); rows.append(dict(day=d, target=t, method=name, awfe_p90=np.quantile(e, .9)))
R = pd.DataFrame(rows)
S = R.groupby(["target", "method"]).awfe_p90.agg(["median", "min", "max"]).round(3)
print(S.to_string())
with open("experiments/results/t7c_figures.md", "w") as fh:
    fh.write("# T7c: AWFE p90 (hourly, p.u. of average monthly load) per method, 8 test days; space heating known to ours\n\n"
             + S.to_markdown() + "\n")

order = ["Ponocko 100%", "Ponocko 50%", "Ponocko 20%", "Ponocko 10%", "Ponocko 5%", "Ponocko 0% (indep. CREST)", "zero"]
blues = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#8a8a8a"]
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, (t, title) in zip(axs, [("controllable", "Controllable (wet + cold + water/space heating)"), ("wet", "Wet appliances (CTIM1)")]):
    for name, col in zip(order, blues):
        if name in cdf[t]:
            v = np.sort(np.concatenate(cdf[t][name])); ax.plot(v, np.arange(1, len(v) + 1) / len(v), color=col, lw=1.6, label=name, ls="--" if name == "zero" else "-")
    v = np.sort(np.concatenate(cdf[t]["ours"])); ax.plot(v, np.arange(1, len(v) + 1) / len(v), color="#eb6834", lw=2.6, label="Ours, 0% sub-metering")
    ax.axhline(0.9, color="#888", lw=0.8, ls=":"); ax.set_xlim(0, 0.5); ax.set_title(title, fontsize=10)
    ax.set_xlabel("AWFE (p.u. of average monthly load)"); ax.grid(alpha=0.25)
axs[0].set_ylabel("CDF (hours of 8 test days)"); axs[1].legend(fontsize=8, loc="lower right")
fig.tight_layout(); fig.savefig(os.path.join(a.out, "fig6_cdf.png"), dpi=170)

d = a.fig_day; te = slice(d * M, (d + 1) * M)
W5 = np.load(os.path.join(a.out, f"W_0.05_d{d}.npy")).astype(np.float64).T
hrs = np.arange(24)
true_c = [H(C[k, te]) for k in range(6)]
est_c = [H(W5[k] * P[te]) for k in range(6)]
cols = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
fig, axs = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
axs[0].stackplot(hrs, true_c, colors=cols, labels=CAT, edgecolor="white", linewidth=0.6); axs[0].set_title(f"Actual (day {d})", fontsize=10)
axs[1].stackplot(hrs, est_c, colors=cols, edgecolor="white", linewidth=0.6); axs[1].set_title("Ponocko, 5% sub-metered (50 homes)", fontsize=10)
ow = wet_h[d * 24:(d + 1) * 24]; oh = heat_h[d * 24:(d + 1) * 24]; tot = H(P[te])
axs[2].stackplot(hrs, [ow, oh, np.clip(tot - ow - oh, 0, None)], colors=[cols[0], cols[2], "#d9d9d9"], edgecolor="white", linewidth=0.6,
                 labels=["wet (estimated)", "space heating (known)", "rest (not separated)"])
axs[2].plot(hrs, true_c[0], color="k", lw=1.2, ls="--", label="actual wet")
axs[2].set_title("Ours, no sub-metering", fontsize=10)
for ax in axs:
    ax.set_xlabel("hour"); ax.grid(alpha=0.25)
axs[0].set_ylabel("kW (1,000 homes)"); axs[0].legend(fontsize=7, loc="upper left"); axs[2].legend(fontsize=7, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(a.out, "fig7_composition.png"), dpi=170)
print("saved", a.out)
