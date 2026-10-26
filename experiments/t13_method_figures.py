"""Explanatory figures for the method slides (v0.10), Pecan Austin development group (T9 cache, 20 homes, 4 with EV).

m2_weather.png    M2: daily load vs temperature with the balance temperatures found from the data, and one week of
                  estimated weather-dependent load against the AC/heating circuits.
m3_home.png       M3: one REFIT home (no AC, no EV) over three days: base, weather, appliance events and routine, the "usual"
                  same-hour reference, and the sub-metered appliances.
m4_ev.png         M4: one EV home over four days: reference + 2.5 kW, hours found as charging, and the car circuit.
m5_envelope.png   M5/M6: the envelope of the group per hour (down / up by category) against the same rule on the true
                  decomposition, and the envelope at participation 0.5.

Days are chosen by use (M3: most appliance events found; M4: most true EV energy; M2: the week at the 75th percentile of
AC energy), not by error.

    python experiments/t13_method_figures.py      (needs outputs/t9/cache_v2.pkl)
"""
import os, pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flexsub import ev as m6, flexibility, features
from flexsub.decompose import decompose_substation, house_parts

OUT = "experiments/results/figures"; os.makedirs(OUT, exist_ok=True)
C = pickle.load(open("outputs/t9/cache_v2.pkl", "rb"))
D = C["pecan_austin"]; cfg, tz = D["cfg"], D["cfg"].tz
COL = dict(base="#b8bfcc", weather="#1baf7a", shiftable="#2a78d6", ev="#eb6834", routine="#e6e3dc", ink="#1f2a44")
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
W, w = D["W"].copy(), D["w"].copy()
W.index = W.index.tz_convert(tz); w.index = w.index.tz_convert(tz)
truth = {h: D["truth"][h].tz_convert(tz) for h in D["W"].columns}
info = []

# ---------------- M2
y = W.sum(axis=1)
day = y.index.normalize()
ld, td = y.groupby(day).mean(), w["temp"].groupby(day).mean()
th, tc = features.balance_points(td, ld)
A = np.c_[np.ones(len(td)), np.maximum(th - td, 0), np.maximum(td - tc, 0)]
ok = ld.notna().to_numpy() & td.notna().to_numpy()
coef, *_ = np.linalg.lstsq(A[ok], ld.to_numpy()[ok], rcond=None)
tt = np.linspace(td.min(), td.max(), 200)
fit = coef[0] + coef[1] * np.maximum(th - tt, 0) + coef[2] * np.maximum(tt - tc, 0)
thm = D["thermal"].copy(); thm.index = thm.index.tz_convert(tz)
tw = sum(truth[h]["weather"] for h in truth).reindex(y.index)
wk = tw.groupby(day).sum()
d75 = wk.index[(wk - wk.quantile(0.75)).abs().argmin()]
s0 = d75 - pd.Timedelta(days=3); s1 = s0 + pd.Timedelta(days=7)
fig, axs = plt.subplots(1, 2, figsize=(14, 4.6), gridspec_kw=dict(width_ratios=[1, 1.6]))
ax = axs[0]
ax.axvspan(th, tc, color="#eef3ec", lw=0)
ax.scatter(td, ld, s=12, color="#7a8296", alpha=0.7, label="one day")
ax.plot(tt, fit, color=COL["weather"], lw=2.4, label="fit with balance temperatures")
for v, lab in ((th, f"Th = {th:.1f} °C"), (tc, f"Tc = {tc:.1f} °C")):
    ax.axvline(v, color=COL["ink"], lw=1, ls="--"); ax.text(v, ax.get_ylim()[1], lab, ha="center", va="bottom", fontsize=10)
ax.text((th + tc) / 2, ld.min(), "neutral zone", ha="center", va="bottom", fontsize=10, color="#4a6b45")
ax.set_xlabel("daily mean temperature (°C)"); ax.set_ylabel("daily mean load, 20 homes (kW)"); ax.legend(fontsize=9, frameon=False, loc="upper left")
ax = axs[1]
S = slice(s0, s1)
ax.plot(y[S].index, y[S], color="#b8bfcc", lw=1.2, label="total load")
ax.plot(thm[S].index, thm[S], color=COL["weather"], lw=2, label="estimated weather-dependent (M2)")
ax.plot(tw[S].index, tw[S], color=COL["ink"], lw=1.4, ls="--", label="true: AC / heating circuits")
ax.set_ylabel("kW"); ax.legend(fontsize=9, frameon=False, loc="upper left", ncol=3); ax.grid(alpha=0.2)
ax.set_title(f"one week, {s0:%d %b} – {(s1 - pd.Timedelta(days=1)):%d %b %Y}", fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "m2_weather.png"), dpi=170); plt.close(fig)
info.append(f"M2: Th {th}, Tc {tc}, week from {s0.date()}")


# ---------------- M3 and M4: per-home parts
def parts(h, DD=None):
    DD = DD or D
    tz_ = DD["cfg"].tz
    s = DD["W"][h].copy(); s.index = s.index.tz_convert(tz_)
    ww = DD["w"].copy(); ww.index = ww.index.tz_convert(tz_)
    P = house_parts(s, ww, DD["cfg"])
    wl = DD["home_weather"][h].copy(); wl.index = wl.index.tz_convert(tz_); wl = wl.reindex(s.index).fillna(0)
    ref = (s - wl).groupby(s.index.hour).transform(lambda x: x.rolling(14, min_periods=7).quantile(0.6).shift(1))
    out = pd.DataFrame(index=s.index); rem = s.copy()
    for name, val in (("base", P["base"]), ("weather", wl), ("ev", P["ev"]), ("shiftable", P["shiftable"])):
        a = np.minimum(val.fillna(0).clip(lower=0), rem); out[name] = a; rem = rem - a
    out["routine"] = rem; out["actual"] = s; out["usual"] = ref + wl
    return out, P


def stack(ax, X, names):
    bottom = np.zeros(len(X))
    for n in names:
        ax.fill_between(X.index, bottom, bottom + X[n].to_numpy(), step="post", color=COL[n], lw=0,
                        label={"base": "base (always on)", "weather": "weather-dependent", "ev": "EV charging",
                               "shiftable": "appliance events", "routine": "routine"}[n])
        bottom = bottom + X[n].to_numpy()


R = C["refit"]                                   # appliance cycles are clearest in REFIT (no AC, no EV)
h3 = max(R["W"].columns, key=lambda h: R["truth"][h]["shiftable"].sum())
X3, _ = parts(h3, R)
ts = R["truth"][h3]["shiftable"].tz_convert(R["cfg"].tz).reindex(X3.index)
d = X3["shiftable"].groupby(X3.index.normalize()).sum().rolling(3).sum()      # the 3 days with most events found
e3 = d.idxmax() + pd.Timedelta(days=1); s3 = e3 - pd.Timedelta(days=3)
Z = X3[s3:e3 - pd.Timedelta(hours=1)]
fig, ax = plt.subplots(figsize=(14, 4.6))
stack(ax, Z, ["base", "shiftable", "routine"])
ax.step(Z.index, Z.actual, where="post", color=COL["ink"], lw=1.3, label="home’s hourly load")
ax.step(Z.index, Z.usual, where="post", color="#7a8296", lw=1.2, ls="--", label="usual: same hour, 14-day 60th percentile")
ax.step(Z.index, ts[Z.index], where="post", color="#0b3d91", lw=1.2, ls=":", label="true appliances (sub-metered)")
ax.set_ylabel("kW"); ax.grid(alpha=0.2); ax.legend(fontsize=9, frameon=False, ncol=4, loc="upper left")
ax.set_ylim(0, Z.actual.max() * 1.35)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "m3_home.png"), dpi=170); plt.close(fig)
info.append(f"M3: REFIT home {h3}, days {s3.date()} - {e3.date()}")

ev_homes = [h for h in truth if truth[h]["ev"].mean() > 0.05]
h4 = max(ev_homes, key=lambda h: truth[h]["ev"].sum())
X4, P4 = parts(h4)
te = truth[h4]["ev"].reindex(X4.index)
d = te.groupby(X4.index.normalize()).sum().rolling(4).sum()
e4 = d.idxmax() + pd.Timedelta(days=1); s4 = e4 - pd.Timedelta(days=4)
Z = X4[s4:e4 - pd.Timedelta(hours=1)]
ev, mask = m6.ev_home(W[h4], k=cfg.ev_k, gate=cfg.ev_gate, max_cv=cfg.ev_max_cv, weather_load=X4["weather"])
S = m6.sessions(ev, mask, tz)
exc = ev[mask & (ev > cfg.ev_k)]
fig, ax = plt.subplots(figsize=(14, 4.6))
stack(ax, Z, ["base", "weather", "ev", "shiftable", "routine"])
ax.step(Z.index, Z.actual, where="post", color=COL["ink"], lw=1.3, label="home’s hourly load")
ax.step(Z.index, Z.usual, where="post", color="#7a8296", lw=1.2, ls="--", label="usual: same hour, 14-day 60th pct")
ax.step(Z.index, Z.usual + cfg.ev_k, where="post", color="#7a8296", lw=1.0, ls=":", label="usual + 2.5 kW (charging threshold)")
ax.step(Z.index, te[Z.index], where="post", color="#8a2c06", lw=1.4, ls=":", label="true: car circuit")
ax.set_ylabel("kW"); ax.grid(alpha=0.2); ax.legend(fontsize=9, frameon=False, ncol=4, loc="upper left")
ax.set_ylim(0, Z.actual.max() * 1.35)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "m4_ev.png"), dpi=170); plt.close(fig)
info.append(f"M4: home {h4}, days {s4.date()} - {e4.date()}, sessions {len(S)}, median power {S.power_kw.median():.1f} kW")

# ---------------- M5 / M6: envelope of the group
Xg = decompose_substation(D["W"], D["w"], D["thermal"], cfg)
tru = sum(D["truth"][h] for h in D["W"].columns).reindex(Xg.index)
T = Xg[["actual", "base"]].copy(); rem = T.actual - T.base
for name, val in (("thermal", tru.weather), ("ev", tru.ev), ("shiftable", tru.shiftable)):
    T[name] = np.minimum(val.fillna(0).clip(lower=0), rem); rem = rem - T[name]
T["routine"] = rem
T.attrs["ev_sessions"] = {h: m6.sessions(D["truth"][h]["ev"].reindex(Xg.index).fillna(0), D["truth"][h]["ev"].reindex(Xg.index).fillna(0) > 0.3, tz)
                          for h in D["W"].columns if D["truth"][h]["ev"].mean() > 0.05}
Fe, Ft = flexibility.flexibility_by_hour(Xg, cfg), flexibility.flexibility_by_hour(T, cfg)
Fp = flexibility.apply_participation(Fe, 0.5)
hrs = np.arange(24)
fig, axs = plt.subplots(1, 2, figsize=(14, 4.6), sharey=True)
for ax, kind in zip(axs, ("down", "up")):
    if kind == "down":
        parts_ = [("weather", Fe.down_thermal_kw), ("shiftable", Fe.down_kw - Fe.down_thermal_kw - Fe.down_ev_kw), ("ev", Fe.down_ev_kw)]
        labels = {"weather": "weather", "shiftable": "appliances", "ev": "EV"}
    else:
        parts_ = [("shiftable", Fe.up_nonev_kw), ("ev", Fe.up_ev_kw)]
        labels = {"shiftable": "weather + appliances", "ev": "EV"}
    b = np.zeros(24)
    for n, v in parts_:
        ax.bar(hrs, v.to_numpy(), bottom=b, color=COL[n], width=0.85, label=f"estimated: {labels[n]}"); b = b + v.to_numpy()
    ax.step(hrs, Ft[f"{kind}_kw"], where="mid", color=COL["ink"], lw=1.8, label="true (same rule, sub-metering)")
    ax.step(hrs, Fp[f"{kind}_kw"], where="mid", color="#7a8296", lw=1.4, ls="--", label="estimated × participation 0.5 (M6)")
    ax.set_title("kW down: can be cut or shifted away" if kind == "down" else "kW up: can be added (2-hour block)", fontsize=11)
    ax.set_xlabel("hour of the day"); ax.set_xticks(range(0, 24, 3)); ax.grid(alpha=0.2, axis="y")
    ax.legend(fontsize=9, frameon=False, loc="upper left")
axs[0].set_ylabel("kW, 20 homes (average day)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "m5_envelope.png"), dpi=170); plt.close(fig)
info.append(f"M5: down est/true {Fe.down_kw.sum() / Ft.down_kw.sum():.2f}, up {Fe.up_kw.sum() / Ft.up_kw.sum():.2f}")
print("\n".join(info))
