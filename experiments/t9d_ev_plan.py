"""T9d: M6 day-ahead EV plan - plug-in windows and staggered rebound. Development data, T9 cache (outputs/t9/cache_v2.pkl).

For every development day D with >= 14 days of history, EV homes found by M6 (flexsub.ev.ev_home), scenarios from
their sessions before D. Windows: 'observed' (hours the car has been seen charging on >= 2 of the last 28 days) vs
'dwell' (10 h from the start). Requests: reduce the 3 busiest expected EV hours; increase 01-04.
  predicted = expected change of the plan over the block (kW);
  real      = reduce: true EV charging of the instructed homes in the block on D (car circuits);
              increase: their true EV energy on D outside the block, per block hour (upper bound: plugging unknown).
  outside_window = share of the instructed homes' true charging on D that falls outside the windows the plan used
                   (charging where the plan thinks the car may not be: lower is safer).
Rebound: expected substation load (non-EV same-hour mean of the last 14 days + EV) after a reduce request, peak in the
hours after the block vs the peak before the request, simple (first free hours) vs staggered (valley filling).

    python experiments/t9d_ev_plan.py
"""
import pickle
import numpy as np
import pandas as pd
from flexsub import ev as m6

C = pickle.load(open("outputs/t9/cache_v2.pkl", "rb"))
rows = []
for ds, D in C.items():
    cfg, tz = D["cfg"], D["cfg"].tz
    W = D["W"].tz_convert(tz)
    S, evs = {}, {}
    for h in W.columns:
        ev, m = m6.ev_home(D["W"][h], k=cfg.ev_k, gate=cfg.ev_gate, max_cv=cfg.ev_max_cv, weather_load=D["home_weather"][h])
        evs[h] = ev.fillna(0).tz_convert(tz)
        if m.any():
            S[h] = m6.sessions(ev, m, tz)
    if not S:
        continue
    TE = pd.DataFrame({h: D["truth"][h]["ev"].tz_convert(tz) for h in W.columns})
    non_ev = W.sum(axis=1) - pd.DataFrame(evs).sum(axis=1)
    days = pd.Index(W.index.normalize().unique())
    for d0 in days[28:-1]:
        idx = pd.date_range(d0, periods=36, freq="h")
        if TE.reindex(idx).notna().sum().sum() < 24:
            continue
        tru = TE.reindex(idx).fillna(0)
        hist = non_ev[(non_ev.index < d0) & (non_ev.index >= d0 - pd.Timedelta(days=14))]
        base = np.resize(hist.groupby(hist.index.hour).mean().reindex(range(24)).ffill().bfill().to_numpy(), 36)
        for mode in ("observed", "dwell"):
            T = m6.typical_day(S, d0, 14, mode=mode, dwell_h=cfg.ev_dwell_h)
            if len(T) == 0:
                continue
            env = m6.envelope(T)
            pk = max(0, int(pd.Series(env.ev_kw.values[:24]).rolling(3).sum().idxmax()) - 2)
            for kind, blk in (("reduce", (pk, pk + 3)), ("increase", (25, 28))):
                for stag in ((False, True) if kind == "reduce" else (True,)):
                    P, A = m6.plan(T, blk, "down" if kind == "reduce" else "up", base_kw=base, stagger=stag)
                    b0, b1 = blk
                    if len(P) == 0:
                        continue
                    hs = list(P.home)
                    pred = abs(A.change_kw.values[b0:b1].mean())
                    if kind == "reduce":
                        real = tru[hs].iloc[b0:b1].sum(axis=1).mean()
                    else:
                        o = tru[hs].copy(); o.iloc[b0:b1] = 0
                        real = o.sum().sum() / (b1 - b0)
                    # windows used for the instructed homes on this day (union over their scenarios)
                    win = np.zeros((36, len(hs)), bool)
                    for j, h in enumerate(hs):
                        for r in T[T.home == h].itertuples():
                            win[r.start_hour:min(36, r.win_end), j] = True
                    tv = tru[hs].to_numpy()
                    outside = tv[~win].sum() / tv.sum() if tv.sum() > 0 else np.nan
                    post = A.total_after_kw.values[b1:min(36, b1 + 8)]
                    rows.append(dict(dataset=ds, day=d0, mode=mode, request=kind, stagger=stag, homes=len(hs),
                                     predicted_kw=pred, real_kw=real, outside_window=outside,
                                     peak_before=A.total_before_kw.values[:30].max(), peak_after_block=post.max(),
                                     rebound_over_peak=post.max() - A.total_before_kw.values[:30].max()))
R = pd.DataFrame(rows)
R.to_csv("outputs/t9/t9d.csv", index=False)
G = R.groupby(["dataset", "request", "mode", "stagger"]).agg(days=("day", "nunique"), homes=("homes", "mean"),
        predicted_kw=("predicted_kw", "mean"), real_kw=("real_kw", "mean"), outside_window=("outside_window", "mean"),
        rebound_over_peak_kw=("rebound_over_peak", "mean"), days_new_peak=("rebound_over_peak", lambda x: float((x > 0.01).mean())))
G["ratio"] = G.predicted_kw / G.real_kw
print(G.round(3).to_string())
open("experiments/results/t9d_ev_plan.md", "w").write("# T9d: M6 day-ahead EV plan\n\n" + G.round(3).to_markdown() + "\n")
