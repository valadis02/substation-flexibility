"""Figures for T8 (run experiments/t8_real_figures.py first).
fig_t8_cdf.png: CDF of hourly AWFE (p.u. of 30-day mean load), ours (solid) vs zero estimate (dashed), per dataset.
fig_t8_days.png: per dataset, one week of flexible load (true vs estimated) and the composition of one day (actual vs
estimated). The day is the one at the 75th percentile of true flexible energy (not chosen by error)."""
import glob, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "experiments/results/figures"
os.makedirs(OUT, exist_ok=True)
S = pd.read_pickle("outputs/t8/series.pkl")
LAB = {"refit": "REFIT, 13 homes", "pecan_austin": "Pecan Austin, 16 homes", "pecan_newyork": "Pecan New York, 15 homes",
       "ukdale": "UK-DALE, single homes"}
TZ = {"refit": "Europe/London", "pecan_austin": "America/Chicago", "pecan_newyork": "America/New_York", "ukdale": "Europe/London"}
COL = {"refit": "#2a78d6", "pecan_austin": "#eb6834", "pecan_newyork": "#1baf7a", "ukdale": "#e87ba4"}
PART = {"flexible": "Flexible (weather-dependent + shiftable)", "shiftable": "Shiftable appliances", "weather": "Weather-dependent"}

fig, axs = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
for ax, (p, title) in zip(axs, PART.items()):
    for ds in LAB:
        if ds not in S:
            continue
        D = pd.concat(S[ds][p])
        for col, ls, lw in (("e", "-", 2.0), ("z", "--", 1.1)):
            v = np.sort(D[col].dropna().to_numpy())
            ax.plot(v, np.arange(1, len(v) + 1) / len(v), color=COL[ds], ls=ls, lw=lw,
                    label=(LAB[ds] if col == "e" else None))
    ax.axhline(0.9, color="#888", lw=0.8, ls=":")
    ax.set_xlim(0, 0.6); ax.set_title(title, fontsize=10); ax.grid(alpha=0.25)
    ax.set_xlabel("AWFE (p.u. of 30-day mean load)")
axs[0].set_ylabel("CDF (hours)")
axs[2].plot([], [], color="#555", ls="-", lw=2, label="ours (solid)"); axs[2].plot([], [], color="#555", ls="--", lw=1.1, label="zero estimate (dashed)")
axs[2].legend(fontsize=8, loc="lower right")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "t8_fig_cdf.png"), dpi=170)

files = {"refit": "outputs/t8/refit.csv.gz", "pecan_austin": "outputs/t8/pecan_austin.csv.gz",
         "pecan_newyork": "outputs/t8/pecan_newyork.csv.gz"}
uk = sorted(glob.glob("outputs/t8/ukdale_*.csv.gz"), key=os.path.getsize)
if uk:
    files["ukdale"] = uk[-1]
fig, axs = plt.subplots(len(files), 3, figsize=(15, 3.1 * len(files)), gridspec_kw=dict(width_ratios=[2.2, 1, 1]))
axs = np.atleast_2d(axs)
for r, (ds, f) in enumerate(files.items()):
    X = pd.read_csv(f, index_col=0, parse_dates=True)
    X.index = pd.DatetimeIndex(X.index).tz_convert(TZ[ds])
    day = X.index.normalize()
    daily = X["true_flexible"].groupby(day).sum()
    d0 = daily.sort_values().index[int(0.75 * (len(daily) - 1))]
    wk = X[(day >= d0 - pd.Timedelta(days=3)) & (day <= d0 + pd.Timedelta(days=3))]
    ax = axs[r, 0]
    ax.plot(wk.index, wk["actual"], color="#bbbbbb", lw=1, label="total load")
    ax.plot(wk.index, wk["true_flexible"], color="#222", lw=1.4, label="flexible, true")
    ax.plot(wk.index, wk["est_flexible"], color=COL[ds], lw=1.8, label="flexible, estimated")
    ax.set_title(f"{LAB[ds]} - week around {d0.date()}", fontsize=10); ax.set_ylabel("kW"); ax.grid(alpha=0.25)
    ax.legend(fontsize=7, loc="upper left"); ax.tick_params(axis="x", labelsize=7)
    Dd = X[day == d0]; h = Dd.index.hour
    for c, (kind, title) in enumerate((("true", "actual"), ("est", "estimated"))):
        wthr, shf = Dd[f"{kind}_weather"].clip(lower=0), Dd[f"{kind}_shiftable"].clip(lower=0)
        rest = (Dd["actual"] - wthr - shf).clip(lower=0)
        axs[r, c + 1].stackplot(h, [wthr, shf, rest], colors=["#1baf7a", "#2a78d6", "#d9d9d9"], edgecolor="white", linewidth=0.6,
                                labels=["weather-dependent", "shiftable", "rest"])
        axs[r, c + 1].set_title(f"{d0.date()}, {title}", fontsize=10); axs[r, c + 1].grid(alpha=0.25)
        axs[r, c + 1].set_xlabel("hour")
    axs[r, 1].legend(fontsize=7, loc="upper left")
    lim = max(axs[r, 1].get_ylim()[1], axs[r, 2].get_ylim()[1]); axs[r, 1].set_ylim(0, lim); axs[r, 2].set_ylim(0, lim)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "t8_fig_days.png"), dpi=150)
print("saved")
