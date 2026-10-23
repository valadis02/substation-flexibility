"""T9b / T9c: v0.9 as implemented in flexsub, development data only (uses the T9 cache, outputs/t9/cache_v2.pkl).

T9b - flexible-load error, v0.8 vs v0.9, and which homes are found as EV homes (flat-power test added).
      P950 (New York, water heater on 98% of hours) is excluded from the data; heat-pump water heaters are reported
      as their own category and are not part of the flexible truth.
T9c - is the EV flexibility actionable the day before? For each development day D with >= 14 days of history:
      typical day per EV home from sessions before D (flexsub.ev_flex), then two DSO requests:
        reduce: the 3 hours of highest expected EV charging,
        increase: 01-04 local (night valley);
      predicted change (expected, kW mean over the block) vs what the instructed homes really had on day D according
      to the car circuits: for reduce, their true EV charging in the block; for increase, their true EV energy that
      day outside the block (energy that existed to be moved; whether the car was plugged in is not observable).
      Also the day-ahead EV profile of the group vs the true EV load of all EV homes (found or not).
      Plug-in window dwell_h = 6 / 10 / 14 h.

    python experiments/t9b_v09.py
"""
import os, pickle
from dataclasses import replace
import numpy as np
import pandas as pd
from flexsub import ev as ev_flex, shiftable
from flexsub.decompose import decompose_substation, _home_weather_load

SESSION = os.environ.get("EV_SESSION_CV") == "1"
TAG = "_session" if SESSION else ""
C = pickle.load(open("outputs/t9/cache_v2.pkl", "rb"))
out = ["# T9b / T9c: v0.9 (EV as flexible load, actionable EV flexibility)\n"]

# ---------------- T9b ----------------
rows, homes_rows = [], []
for ds, D in C.items():
    tru = sum(D["truth"][h] for h in D["W"].columns)
    for name, gate in (("v0.8", 1.1), ("v0.9", D["cfg"].ev_gate)):
        cfg = replace(D["cfg"], ev_gate=gate)
        X = decompose_substation(D["W"], D["w"], D["thermal"], cfg)
        t = tru.reindex(X.index)
        m30 = X.actual.rolling(720, min_periods=168, center=True).mean()
        est_f, tru_f = X.thermal + X.ev + X.shiftable, t.weather + t.ev + t.shiftable
        e = ((est_f - tru_f).abs() / m30).dropna()
        rows.append(dict(dataset=ds, version=name, homes=D["W"].shape[1], flexible_awfe_p90=e.quantile(0.9),
                         zero_p90=(tru_f / m30).dropna().quantile(0.9), flexible_energy_ratio=est_f.sum() / tru_f.sum(),
                         ev_energy_ratio=X.ev.sum() / t.ev.sum() if t.ev.sum() > 0 else np.nan,
                         ev_awfe_p90=((X.ev - t.ev).abs() / m30).dropna().quantile(0.9),
                         hp_water_heater_kwh_day_not_estimated=t.hp_water_heater.mean() * 24))
    cfg = D["cfg"]
    for h in D["W"].columns:
        ev, m = ev_flex.ev_home(D["W"][h], k=cfg.ev_k, gate=cfg.ev_gate, max_cv=cfg.ev_max_cv, weather_load=D["home_weather"][h], session_cv=SESSION)
        has = D["truth"][h]["ev"].mean() > 0.05
        if has or m.any():
            homes_rows.append(dict(dataset=ds, home=h, has_ev=has, found=bool(m.any())))
R, H = pd.DataFrame(rows), pd.DataFrame(homes_rows)
print(R.round(3).to_string()); print(H.to_string())
out += ["\n## T9b - flexible-load error\n\n", R.round(3).to_markdown(index=False), "\n\nEV homes (has = car circuit, found = v0.9):\n\n",
        H.to_markdown(index=False) if len(H) else "none", "\n"]

# ---------------- T9c ----------------
crow, prof_rows = [], []
for ds, D in C.items():
    cfg, tz = D["cfg"], D["cfg"].tz
    S, truth_ev = {}, {}
    for h in D["W"].columns:
        ev, m = ev_flex.ev_home(D["W"][h], k=cfg.ev_k, gate=cfg.ev_gate, max_cv=cfg.ev_max_cv, weather_load=D["home_weather"][h], session_cv=SESSION)
        if m.any():
            S[h] = ev_flex.sessions(ev, m, tz)
        truth_ev[h] = D["truth"][h]["ev"].tz_convert(tz)
    if not S:
        continue
    TE = pd.DataFrame(truth_ev)
    days = pd.Index(TE.index.normalize().unique())
    for dwell in (6, 10, 14):
        for i, d0 in enumerate(days[14:-1], start=14):
            T = ev_flex.typical_day(S, d0)
            if len(T) == 0:
                continue
            idx = pd.date_range(d0, periods=36, freq="h")
            day_true = TE.reindex(idx).fillna(0)
            if TE.reindex(idx).notna().sum().sum() < 24:
                continue
            env = ev_flex.envelope(T, dwell_h=dwell)
            if dwell == 10:
                prof_rows.append(dict(dataset=ds, day=d0, est=env.ev_kw.values[:24], true=day_true.sum(axis=1).values[:24]))
            pk = max(0, int(pd.Series(env.ev_kw.values[:24]).rolling(3).sum().idxmax()) - 2)   # start of the 3 busiest hours
            for kind, blk in (("reduce", (pk, pk + 3)), ("increase", (25, 28))):
                P, A = ev_flex.plan(T, blk, "down" if kind == "reduce" else "up", dwell_h=dwell)
                if len(P) == 0:
                    crow.append(dict(dataset=ds, dwell_h=dwell, request=kind, day=d0, homes=0, predicted_kw=0.0, real_kw=0.0)); continue
                b0, b1 = blk
                pred = abs(A.change_kw.values[b0:b1].mean())
                hs = list(P.home)
                if kind == "reduce":
                    real = day_true[hs].iloc[b0:b1].sum(axis=1).mean()
                else:
                    other = day_true[hs].copy(); other.iloc[b0:b1] = 0
                    cap = T.groupby("home").power_kw.median().reindex(hs)
                    real = min(other.sum().sum(), cap.sum() * (b1 - b0)) / (b1 - b0)
                crow.append(dict(dataset=ds, dwell_h=dwell, request=kind, day=d0, homes=len(hs), predicted_kw=pred, real_kw=real))
CR = pd.DataFrame(crow)
if len(CR):
    G = CR.groupby(["dataset", "request", "dwell_h"]).apply(lambda g: pd.Series(dict(
        days=len(g), homes_mean=g.homes.mean(), predicted_kw_mean=g.predicted_kw.mean(), real_kw_mean=g.real_kw.mean(),
        ratio=g.predicted_kw.sum() / max(g.real_kw.sum(), 1e-9), mae_kw=(g.predicted_kw - g.real_kw).abs().mean(),
        corr_days=np.corrcoef(g.predicted_kw, g.real_kw)[0, 1] if g.predicted_kw.std() > 0 and g.real_kw.std() > 0 else np.nan)))
    print(G.round(2).to_string())
    PR = pd.DataFrame(prof_rows)
    Q = []
    for ds, g in PR.groupby("dataset"):
        est, tru = np.mean(np.stack(g.est), 0), np.mean(np.stack(g.true), 0)
        Q.append(dict(dataset=ds, days=len(g), mean_profile_corr=np.corrcoef(est, tru)[0, 1], energy_ratio=est.sum() / tru.sum(),
                      est_peak_hour=int(est.argmax()), true_peak_hour=int(tru.argmax()),
                      daily_kwh_mae=float(np.mean([abs(a.sum() - b.sum()) for a, b in zip(g.est, g.true)])),
                      daily_kwh_true=float(np.mean([b.sum() for b in g.true]))))
    Q = pd.DataFrame(Q); print(Q.round(2).to_string())
    out += ["\n## T9c - actionable EV flexibility, day ahead\n\nPer request: predicted = expected change of the plan (kW, mean over "
            "the block); real = what the instructed homes really had that day (car circuits).\n\n", G.round(2).to_markdown(),
            "\n\nDay-ahead EV profile of the group (dwell irrelevant):\n\n", Q.round(2).to_markdown(index=False), "\n"]
    CR.to_csv(f"outputs/t9/t9c_requests{TAG}.csv", index=False)
open(f"experiments/results/t9b_v09{TAG}.md", "w").write("".join(out))
