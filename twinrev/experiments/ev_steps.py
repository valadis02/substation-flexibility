"""EV detection by paired steps in 15-minute data (test, the method's code is not changed): a charge starts with a sharp rise, holds,
and ends with a fall of about the same size, at least an hour later. Prints one line per development home; no gate yet.
  python3 -W ignore ev_steps.py pecan_austin --raw 15minute_data_austin.csv"""
import argparse, json, os
import numpy as np
import pandas as pd
import ev_rate as R

K0, TOL, MIN_SLOTS, MAX_SLOTS = 1.0, 0.25, 4, 48     # kW, fall vs rise, 1 h, 12 h


def pairs(x):
    v = x.interpolate(limit=2).values
    d = np.diff(v, prepend=np.nan)
    out = []
    i, n = 0, len(v)
    while i < n:
        up = d[i]
        if not (up > K0):
            i += 1
            continue
        base = v[i - 1]
        end = None
        for j in range(i + 1, min(n, i + MAX_SLOTS)):
            if np.isnan(v[j]) or v[j] < base + 0.5 * up:
                if d[j] < 0 and abs(-d[j] - up) <= TOL * up and j - i >= MIN_SLOTS:
                    end = j
                break
        if end is None:
            i += 1
            continue
        out.append((i, end - i, float(up)))
        i = end + 1
    return out


def scores(x, wl, tz):
    P = pairs(x)
    days = max(x.notna().sum() / 96, 1)
    if not P:
        return dict(sess_day=0.0, kW=0.0, hours=0.0, kWh_day=0.0, low_high=0.0), 0.0
    up = np.array([p[2] for p in P])
    dur = np.array([p[1] for p in P]) / 4
    day = pd.Series(x.index.tz_convert(tz).date, index=x.index)
    load = wl.groupby(day.reindex(wl.index).values).sum()
    rank = load.rank(method="first", pct=True)
    low, high = set(rank.index[rank <= 1 / 3]), set(rank.index[rank > 2 / 3])
    sd = [day.iloc[p[0]] for p in P]
    rl, rh = sum(d in low for d in sd) / max(len(low), 1), sum(d in high for d in sd) / max(len(high), 1)
    kwh = float((up * dur).sum())
    return dict(sess_day=round(len(P) / days, 2), kW=round(float(np.median(up)), 2), hours=round(float(np.median(dur)), 2),
                kWh_day=round(kwh / days, 2), low_high=round(rl / rh, 2) if rh else 0.0), kwh


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("--raw", required=True)
    ap.add_argument("--data-dir", default=os.path.join(R.HERE, "..", "..", "flexibility", "data"))
    a = ap.parse_args()
    d = R.load_processed(os.path.join(a.data_dir, "processed", a.dataset))
    W, w, A = d["W"], d["weather"], d["appliances"]
    sp = json.load(open(os.path.join(a.data_dir, "splits.json")))["datasets"][a.dataset]
    tz, D = R.TZ[a.dataset], R.read_raw(a.raw, R.TZ[a.dataset])
    for h in W.columns:
        if h in sp["held_out_homes"] or h in sp.get("excluded", []) or h not in A or h not in D:
            continue
        cut = sp["time_cut"].get(h)
        s = W[h][W.index < pd.Timestamp(cut)] if cut else W[h]
        ap_ = A[h].reindex(s.index).fillna(0).clip(lower=0)
        ev = ap_[[c for c in ap_ if c == "ev" or R.category(c, a.dataset) == "ev"]].sum(axis=1)
        wl = R.decompose._home_weather_load(s, w.reindex(s.index), tz).reindex(s.index).fillna(0)
        x = D[h]
        x = x[(x.index >= s.index[0]) & (x.index <= s.index[-1])]
        sc, kwh = scores(x, wl, tz)
        print(h, "EV" if ev.mean() > 0.05 else "no", "true_kWh", round(float(ev.sum())), "est_kWh", round(kwh), sc, flush=True)
