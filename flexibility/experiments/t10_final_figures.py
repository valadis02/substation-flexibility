"""Figures for the final method (v0.9, M1-M6), development data, T9 groups (EV homes included, P950 excluded).

final_days.png  per dataset: one week of flexible load (weather + appliances + EV), true vs estimated, and the
                composition of one day (true vs estimated). Day = 75th percentile of true flexible energy.
final_cdf.png   CDF of hourly AWFE of the flexible load (p.u. of 30-day mean load), ours vs zero estimate.
m6_plan.png     M6 on one Austin development day: reduce request on the 3 busiest expected EV hours; expected
                substation load before / after, rebound simple vs staggered; plus the per-home instructions (printed).

    python experiments/t10_final_figures.py      (needs outputs/t9/cache_v2.pkl from experiments/t9_ev.py)
"""
import os, pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flexsub import ev as m6
from flexsub.decompose import decompose_substation

OUT = "experiments/results/figures"; os.makedirs(OUT, exist_ok=True)
C = pickle.load(open("outputs/t9/cache_v2.pkl", "rb"))
LAB = {"pecan_austin": "Pecan Austin", "pecan_newyork": "Pecan New York", "refit": "REFIT"}
COL = {"pecan_austin": "#eb6834", "pecan_newyork": "#1baf7a", "refit": "#2a78d6"}
CMP = {"weather": "#1baf7a", "shiftable": "#2a78d6", "ev": "#eb6834", "rest": "#d9d9d9"}
X, summary = {}, []
for ds in LAB:
    D = C[ds]; tz = D["cfg"].tz
    R = decompose_substation(D["W"], D["w"], D["thermal"], D["cfg"])
    t = sum(D["truth"][h] for h in D["W"].columns).reindex(R.index)
    F = pd.DataFrame({"actual": R.actual, "est_weather": R.thermal, "est_shiftable": R.shiftable, "est_ev": R.ev,
                      "true_weather": t.weather, "true_shiftable": t.shiftable, "true_ev": t.ev})
    F["est_flexible"] = F.est_weather + F.est_shiftable + F.est_ev
    F["true_flexible"] = F.true_weather + F.true_shiftable + F.true_ev
    F.index = F.index.tz_convert(tz)
    m30 = F.actual.rolling(720, min_periods=168, center=True).mean()
    F["e"] = (F.est_flexible - F.true_flexible).abs() / m30
    F["z"] = F.true_flexible.abs() / m30
    X[ds] = F
    summary.append(dict(dataset=ds, homes=D["W"].shape[1], awfe_p90=F.e.quantile(0.9), zero_p90=F.z.quantile(0.9),
                        energy_ratio=F.est_flexible.sum() / F.true_flexible.sum()))
print(pd.DataFrame(summary).round(3).to_string())

# ---- CDF
fig, ax = plt.subplots(figsize=(7.5, 4.6))
for ds, F in X.items():
    for col, ls, lw in (("e", "-", 2.2), ("z", "--", 1.1)):
        v = np.sort(F[col].dropna().to_numpy())
        ax.plot(v, np.arange(1, len(v) + 1) / len(v), color=COL[ds], ls=ls, lw=lw,
                label=f"{LAB[ds]} ({C[ds]['W'].shape[1]} homes)" if col == "e" else None)
ax.axhline(0.9, color="#888", lw=0.8, ls=":")
ax.plot([], [], color="#555", lw=2.2, label="ours, no sub-metering"); ax.plot([], [], color="#555", ls="--", lw=1.1, label="zero estimate")
ax.set_xlim(0, 1.0); ax.set_xlabel("hourly AWFE, flexible load (p.u. of 30-day mean load)"); ax.set_ylabel("share of hours")
ax.grid(alpha=0.25); ax.legend(fontsize=8, loc="lower right")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "final_cdf.png"), dpi=170); plt.close(fig)

# ---- days
fig, axs = plt.subplots(len(X), 3, figsize=(15, 3.2 * len(X)), gridspec_kw=dict(width_ratios=[2.2, 1, 1]))
for r, (ds, F) in enumerate(X.items()):
    day = F.index.normalize()
    daily = F.true_flexible.groupby(day).sum()
    d0 = daily.sort_values().index[int(0.75 * (len(daily) - 1))]
    wk = F[(day >= d0 - pd.Timedelta(days=3)) & (day <= d0 + pd.Timedelta(days=3))]
    ax = axs[r, 0]
    ax.plot(wk.index, wk.actual, color="#bbbbbb", lw=1, label="total load")
    ax.plot(wk.index, wk.true_flexible, color="#222", lw=1.4, label="flexible, true (sub-metered)")
    ax.plot(wk.index, wk.est_flexible, color=COL[ds], lw=1.8, label="flexible, estimated")
    ax.set_title(f"{LAB[ds]}, {C[ds]['W'].shape[1]} homes - week around {d0.date()}", fontsize=10)
    ax.set_ylabel("kW"); ax.grid(alpha=0.25); ax.legend(fontsize=7, loc="upper left"); ax.tick_params(axis="x", labelsize=7)
    Dd = F[day == d0]; h = Dd.index.hour
    for c, kind in enumerate(("true", "est")):
        parts = [Dd[f"{kind}_{p}"].clip(lower=0) for p in ("weather", "shiftable", "ev")]
        rest = (Dd.actual - sum(parts)).clip(lower=0)
        axs[r, c + 1].stackplot(h, parts + [rest], colors=[CMP[k] for k in ("weather", "shiftable", "ev", "rest")],
                                edgecolor="white", linewidth=0.5, labels=["weather-dependent", "appliances", "EV", "rest"])
        axs[r, c + 1].set_title(f"{d0.date()}, {'true' if kind == 'true' else 'estimated'}", fontsize=10)
        axs[r, c + 1].grid(alpha=0.25); axs[r, c + 1].set_xlabel("hour")
    axs[r, 1].legend(fontsize=7, loc="upper left")
    lim = max(axs[r, 1].get_ylim()[1], axs[r, 2].get_ylim()[1]); axs[r, 1].set_ylim(0, lim); axs[r, 2].set_ylim(0, lim)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "final_days.png"), dpi=150); plt.close(fig)

# ---- M6 plan, one Austin day
D = C["pecan_austin"]; cfg, tz = D["cfg"], D["cfg"].tz
S, evs = {}, {}
for h in D["W"].columns:
    ev, m = m6.ev_home(D["W"][h], k=cfg.ev_k, gate=cfg.ev_gate, max_cv=cfg.ev_max_cv, weather_load=D["home_weather"][h])
    evs[h] = ev.fillna(0)
    if m.any():
        S[h] = m6.sessions(ev, m, tz)
W = D["W"].tz_convert(tz)
non_ev = W.sum(axis=1) - pd.DataFrame(evs).tz_convert(tz).sum(axis=1)
days = pd.Index(W.index.normalize().unique())
best = None
for d0 in days[28:-1]:                       # the day with the largest expected EV load in its busiest 3 hours
    T = m6.typical_day(S, d0, 14)
    if len(T) == 0:
        continue
    env = m6.envelope(T)
    v = pd.Series(env.ev_kw.values[:24]).rolling(3).sum().max()
    if best is None or v > best[0]:
        best = (v, d0, T, env)
_, d0, T, env = best
hist = non_ev[(non_ev.index < d0) & (non_ev.index >= d0 - pd.Timedelta(days=14))]
base = np.resize(hist.groupby(hist.index.hour).mean().reindex(range(24)).ffill().bfill().to_numpy(), 36)
pk = max(0, int(pd.Series(env.ev_kw.values[:24]).rolling(3).sum().idxmax()) - 2)
P, A = m6.plan(T, (pk, pk + 3), "down", base_kw=base, stagger=True)
_, A0 = m6.plan(T, (pk, pk + 3), "down", base_kw=base, stagger=False)
print(d0.date(), "block", pk, pk + 3); print(P.to_string(index=False))
P.to_csv("experiments/results/m6_plan_example.csv", index=False)
hrs = np.arange(36)
fig, axs = plt.subplots(1, 2, figsize=(13.5, 4.3))
ax = axs[0]
ax.bar(hrs - 0.2, A.before_kw, width=0.4, color="#bbbbbb", label="EV, usual charging")
ax.bar(hrs + 0.2, A.after_kw, width=0.4, color="#eb6834", label="EV, with the plan")
ax.axvspan(pk - 0.5, pk + 2.5, color="#2a78d6", alpha=0.12, label="DSO request: reduce")
ax.set_title(f"Expected EV charging, {len(P)} EV homes instructed", fontsize=10); ax.set_ylabel("kW")
ax.set_xticks(range(0, 36, 3)); ax.set_xticklabels([f"{h % 24:02d}" for h in range(0, 36, 3)]); ax.set_xlabel("hour (day ahead -> next morning)")
ax.legend(fontsize=8); ax.grid(alpha=0.25)
ax = axs[1]
ax.plot(hrs, A.total_before_kw, color="#222", lw=1.6, label="substation, no request")
ax.plot(hrs, A0.total_after_kw, color="#9aa3b5", lw=1.6, ls="--", label="with request, EVs restart together")
ax.plot(hrs, A.total_after_kw, color="#eb6834", lw=2.2, label="with request, restart staggered (M6)")
ax.axvspan(pk - 0.5, pk + 2.5, color="#2a78d6", alpha=0.12)
ax.set_title("Expected substation load", fontsize=10); ax.set_ylabel("kW")
ax.set_xticks(range(0, 36, 3)); ax.set_xticklabels([f"{h % 24:02d}" for h in range(0, 36, 3)]); ax.set_xlabel("hour")
ax.legend(fontsize=8); ax.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "m6_plan.png"), dpi=170); plt.close(fig)
print("saved")
