"""T12 (development data only, T9 cache outputs/t9/cache_v2.pkl): v0.10 restructure.

v0.9: M4 envelope = weather + appliances; EV was a separate module (M6) and participation scaled M4 only.
v0.10: M4 = EV estimate, M5 = one envelope for weather + appliances + EV, M6 = participation for all of it.

1. Hourly flexible load (weather + appliances + EV) and its AWFE: must be unchanged (the decomposition is unchanged).
2. Envelope accuracy per hour of the average day, groups INCLUDING EV homes (T4 excluded them):
     estimated envelope from the estimated decomposition vs the same rule applied to the true decomposition
     (same base; weather = AC/heating circuits, EV = car circuits, appliances = sub-metered appliances; allocated in
     the same order). True EV sessions: car circuit > 0.3 kW. err = mean |est - true| over 24 h / mean load;
     ratio = est / true over the day.
     variants: v0.9 M4 alone (no EV in the envelope; what M4 reported), v0.10 sessions rule (default; at
     participation 1 this equals v0.9 M4 + EV), v0.10 same rule (EV treated as a short-cycle load).
     Truth for "up" uses the same plug-in assumption (dwell 10 h) as the estimate: plug-in time is not observable.
3. Participation 0.1 (enrolment 0.2 x response 0.5): v0.9 total (0.1 x M4 + unscaled EV) vs v0.10 (0.1 x all),
     against 0.1 x true.

    python experiments/t12_envelope_ev.py
"""
import os, pickle
import numpy as np
import pandas as pd
from flexsub import ev as m6, flexibility
from flexsub.decompose import decompose_substation

C = pickle.load(open("outputs/t9/cache_v2.pkl", "rb"))
A, B, P = [], [], []
for ds, Dd in C.items():
    cfg, tz = Dd["cfg"], Dd["cfg"].tz
    X = decompose_substation(Dd["W"], Dd["w"], Dd["thermal"], cfg)
    tru = sum(Dd["truth"][h] for h in Dd["W"].columns).reindex(X.index)
    # 1. hourly flexible load
    m30 = X.actual.rolling(720, min_periods=168, center=True).mean()
    est_f, tru_f = X.thermal + X.ev + X.shiftable, tru.weather + tru.ev + tru.shiftable
    A.append(dict(dataset=ds, homes=Dd["W"].shape[1], ev_homes_true=sum(Dd["truth"][h]["ev"].mean() > 0.05 for h in Dd["W"].columns),
                  ev_homes_found=len(X.attrs["ev_sessions"]),
                  flexible_awfe_p90=((est_f - tru_f).abs() / m30).dropna().quantile(0.9), energy_ratio=est_f.sum() / tru_f.sum()))
    # 2. true decomposition, same base and order
    T = X[["actual", "base"]].copy()
    rem = T.actual - T.base
    for name, val in (("thermal", tru.weather), ("ev", tru.ev), ("shiftable", tru.shiftable)):
        T[name] = np.minimum(val.fillna(0).clip(lower=0), rem); rem = rem - T[name]
    T["routine"] = rem
    TS = {}
    for h in Dd["W"].columns:
        e = Dd["truth"][h]["ev"].reindex(X.index).fillna(0)
        if e.mean() > 0.05:
            TS[h] = m6.sessions(e, e > 0.3, tz)
    T.attrs["ev_sessions"] = TS
    Xn = X.assign(ev=0.0); Xn.attrs = {}                                   # v0.9 M4: no EV in the envelope
    Fe = {"v0.9 M4 alone": flexibility.flexibility_by_hour(Xn, cfg),
          "v0.10 sessions": flexibility.flexibility_by_hour(X, cfg),
          "v0.10 same rule": flexibility.flexibility_by_hour(X, cfg, ev_rule="same")}
    Ft = {"v0.9 M4 alone": flexibility.flexibility_by_hour(T, cfg),          # truth = everything flexible, sessions rule
          "v0.10 sessions": flexibility.flexibility_by_hour(T, cfg),
          "v0.10 same rule": flexibility.flexibility_by_hour(T, cfg, ev_rule="same")}
    load = Fe["v0.10 sessions"].load_kw.mean()
    for v in Fe:
        e, t = Fe[v], Ft[v]
        row = dict(dataset=ds, variant=v)
        for c in ("down_kw", "up_kw", "down_ev_kw", "up_ev_kw"):
            if v == "v0.10 same rule" and c == "up_ev_kw":
                continue
            row[f"{c}_err"] = (e[c] - t[c]).abs().mean() / load
            row[f"{c}_ratio"] = e[c].sum() / t[c].sum() if t[c].sum() > 1e-9 else np.nan
        row["down_true_mean"] = t.down_kw.mean() / load; row["up_true_mean"] = t.up_kw.mean() / load
        B.append(row)
    # 3. participation 0.1
    p = 0.1
    e, t = Fe["v0.10 sessions"], Ft["v0.10 sessions"]
    for c in ("down_kw", "up_kw"):
        ev_c = "down_ev_kw" if c == "down_kw" else "up_ev_kw"
        v09 = p * (e[c] - e[ev_c]) + e[ev_c]
        v10 = flexibility.apply_participation(e, p)[c]
        P.append(dict(dataset=ds, column=c, true_kw_day=p * t[c].sum(), v09_ratio=v09.sum() / (p * t[c].sum()),
                      v10_ratio=v10.sum() / (p * t[c].sum())))
    print(ds, "done", flush=True)
A, B, P = pd.DataFrame(A), pd.DataFrame(B), pd.DataFrame(P)
print(A.round(3).to_string()); print(B.round(3).to_string()); print(P.round(3).to_string())
os.makedirs("experiments/results", exist_ok=True)
with open("experiments/results/t12_envelope_ev.md", "w") as f:
    f.write("# T12 - v0.10: EV inside the M5 envelope, participation (M6) for all (development data)\n\n"
            "## 1. Hourly flexible load (weather + appliances + EV): unchanged decomposition\n\n" + A.round(3).to_markdown(index=False) +
            "\n\n## 2. Envelope per hour of the average day vs the same rule on the true decomposition\n\n"
            "err = mean |est - true| / mean load; ratio = est / true over the day; true_mean = true envelope / mean load. "
            "'v0.9 M4 alone' is compared with the true envelope of all flexible load (EV included).\n\n" + B.round(3).to_markdown(index=False) +
            "\n\n## 3. Participation 0.1: est / true\n\n" + P.round(3).to_markdown(index=False) + "\n")
