"""T14 (development data only, T9 cache outputs/t9/cache_v2.pkl): stability of the M5 up cap.

The up cap at hour h was q90 - mean of the flexible load at h over the window. With a 35-day window that is ~35 values,
so q90 is about the 4th largest: one day more or less moves it, and the day-ahead envelope jumped from hour to hour
(REFIT 26 Jan 2015: up 3.9 kW at 12:00, true 1.6). Candidates, each compared with the SAME rule on the true
(sub-metered) decomposition, over rolling 35-day windows (step 7 days):
  per_hour   v0.10: q90 - mean at h
  pool3      v0.11: q90 - mean over h-1, h, h+1 (3x the values)
  bag        mean of 200 bootstrap resamples of the per-hour cap
  longwin    per-hour cap from the last 90 days (energy still from 35)
  q80, pool_q80  lower quantile (changes what "up" means; truth changes too, so error is not comparable)
Metrics per window: up err = mean |est - true| / mean load; up ratio = est / true over the day; peak = max est / max
true; rough = mean |hour-to-hour change| / mean up (jumpiness).

    python experiments/t14_up_cap.py
"""
import os, pickle
import numpy as np
import pandas as pd
from flexsub.decompose import decompose_substation

C = pickle.load(open("outputs/t9/cache_v2.pkl", "rb"))
KINDS = ["per_hour", "pool3", "bag", "longwin", "q80", "pool_q80"]


def cap(f, h, kind):
    g = pd.DataFrame({"f": np.asarray(f), "h": np.asarray(h)}).dropna()
    hours = (lambda x: [(x - 1) % 24, x, (x + 1) % 24]) if kind.startswith("pool") else (lambda x: [x])
    q = 0.8 if kind in ("q80", "pool_q80") else 0.9
    out = np.zeros(24)
    for x in range(24):
        v = g.f[g.h.isin(hours(x))].to_numpy()
        if not len(v):
            continue
        if kind == "bag":
            rng = np.random.default_rng(x)
            c = np.mean([np.quantile(s, q) - s.mean() for s in (rng.choice(v, len(v)) for _ in range(200))])
        else:
            c = np.quantile(v, q) - v.mean()
        out[x] = max(c, 0.0)
    return out


def up(D, Dlong, cfg, kind, S=3, dur=2):
    loc, locl = D.index.tz_convert(cfg.tz), Dlong.index.tz_convert(cfg.tz)
    f, fl = D.thermal + D.shiftable, Dlong.thermal + Dlong.shiftable
    sh = f.groupby(loc.hour).mean().reindex(range(24)).fillna(0).to_numpy()
    up_e = np.array([sum(sh[(x + k) % 24] for k in list(range(-S, 0)) + list(range(dur, dur + S))) / dur for x in range(24)])
    c = cap(fl, locl.hour, "per_hour") if kind == "longwin" else cap(f, loc.hour, kind)
    return np.minimum(up_e, c)


rows = []
for ds, Dd in C.items():
    cfg = Dd["cfg"]
    X = decompose_substation(Dd["W"], Dd["w"], Dd["thermal"], cfg)
    tru = sum(Dd["truth"][h] for h in Dd["W"].columns).reindex(X.index)
    T = X[["actual", "base"]].copy(); rem = T.actual - T.base
    for name, val in (("thermal", tru.weather), ("ev", tru.ev), ("shiftable", tru.shiftable)):
        T[name] = np.minimum(val.fillna(0).clip(lower=0), rem); rem = rem - T[name]
    days = pd.Index(X.index.tz_convert(cfg.tz).normalize().unique())
    for i in range(0, len(days) - 34, 7):
        d0, d1 = days[i], days[i + 34] + pd.Timedelta(days=1)
        sel, sell = (X.index >= d0) & (X.index < d1), (X.index >= d1 - pd.Timedelta(days=90)) & (X.index < d1)
        load = X.actual[sel].mean()
        for k in KINDS:
            ue, ut = up(X[sel], X[sell], cfg, k), up(T[sel], T[sell], cfg, k)
            rows.append(dict(dataset=ds, window=i, rule=k, up_err=np.abs(ue - ut).mean() / load, up_ratio=ue.sum() / ut.sum(),
                             peak=ue.max() / ut.max(), rough=np.abs(np.diff(ue)).mean() / max(ue.mean(), 1e-9),
                             up_true=ut.mean() / load))
    print(ds, "done", flush=True)
R = pd.DataFrame(rows)
S = R.groupby(["dataset", "rule"]).agg(windows=("window", "count"), up_err=("up_err", "mean"), ratio_median=("up_ratio", "median"),
                                        ratio_p10=("up_ratio", lambda s: s.quantile(.1)), ratio_p90=("up_ratio", lambda s: s.quantile(.9)),
                                        peak_median=("peak", "median"), rough=("rough", "mean"), up_true=("up_true", "mean")).reset_index()
print(S.round(3).to_string())
os.makedirs("experiments/results", exist_ok=True)
with open("experiments/results/t14_up_cap.md", "w") as f:
    f.write("# T14 - stability of the M5 up cap (development data, rolling 35-day windows, step 7 days)\n\n"
            "up_err = mean |est - true| / mean load; ratio = est / true over the day; peak = max est / max true; "
            "rough = mean |hour-to-hour change| / mean up; up_true = true up / mean load. q80 rules change the truth too.\n\n"
            + S.round(3).to_markdown(index=False) + "\n")
