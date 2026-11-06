"""EV detection by charger rate (test, the method's code is not changed): find each home's charger step first, then the charging
periods that fit it, then recompute the reference without those periods; repeat. Idea after Pu & Zhao 2022.
  python3 -W ignore ev_rate.py pecan_austin                                    # hourly
  python3 -W ignore ev_rate.py pecan_austin --raw 15minute_data_austin.csv     # also 15-minute
Prints one line per home (development homes only) so that the separation EV / no EV can be read before any gate is fixed."""
import argparse, json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "flexibility"))
from flexsub import decompose                                            # noqa: E402
from flexsub.appliances import category                                  # noqa: E402
from flexsub.config import Config                                        # noqa: E402
from flexsub.data import load_processed                                  # noqa: E402

TZ = {"pecan_austin": "America/Chicago", "pecan_newyork": "America/New_York", "pecan_california": "America/Los_Angeles"}
K0 = 1.0           # kW: smallest step looked at (level-1 chargers draw about 1.4 kW)
TOL = 0.2          # a slot fits the charger if within +-20 % of its rate


def slot_reference(y, per_hour, mask=None, q=0.6, days=14):
    v = y if mask is None else y.where(~mask)
    key = y.index.hour * per_hour + y.index.minute // (60 // per_hour)
    return v.groupby(key).transform(lambda s: s.rolling(days, min_periods=4).quantile(q).shift(1).ffill())


def charger_rate(e):
    x = e[e > K0].dropna().values
    if len(x) < 20:
        return np.nan
    h, b = np.histogram(x, bins=np.arange(K0, 12.25, 0.25), weights=x)   # by energy: small frequent bumps do not win
    h = np.convolve(h, [1, 2, 1], "same")
    return b[int(np.argmax(h))] + 0.125


def detect(y, per_hour, weather, tz, iters=3):
    """y: load minus weather-dependent load. Returns kW estimate and scores."""
    empty = dict(rate=np.nan, fit=0.0, sessions=0, low_high=0.0)
    ref, sess = slot_reference(y, per_hour), None
    for _ in range(iters):
        e = y - ref
        R = charger_rate(e)
        if np.isnan(R):
            return 0.0 * y, empty
        above = e > max(K0, 0.5 * R)
        fits = (e - R).abs() <= TOL * R
        rid = (above != above.shift()).cumsum()
        hit = fits[above].groupby(rid[above]).transform("any")
        sess = pd.Series(False, index=y.index)
        sess.loc[hit[hit].index] = True
        ref = slot_reference(y, per_hour, sess)
    e = y - ref
    above = e > K0
    fit = float(((e - R).abs() <= TOL * R)[above].mean()) if above.any() else 0.0
    kw = e.clip(lower=0, upper=(1 + TOL) * R).where(sess, 0.0).fillna(0.0)
    rid = (sess != sess.shift()).cumsum()
    starts = [g.index[0] for _, g in sess[sess].groupby(rid[sess])]
    day = pd.Series(y.index.tz_convert(tz).date, index=y.index)
    load = weather.groupby(day.reindex(weather.index).values).sum()
    rank = load.rank(method="first", pct=True)
    low, high = set(rank.index[rank <= 1 / 3]), set(rank.index[rank > 2 / 3])
    sd = [day[t] for t in starts]
    rl, rh = sum(d in low for d in sd) / max(len(low), 1), sum(d in high for d in sd) / max(len(high), 1)
    return kw, dict(rate=round(float(R), 2), fit=round(fit, 2), sessions=len(starts), low_high=round(rl / rh, 2) if rh else 0.0)


def read_raw(path, tz):
    d = pd.read_csv(path, usecols=lambda c: c in ("dataid", "local_15min", "grid", "solar", "solar2"))
    d.index = pd.to_datetime(d["local_15min"], utc=True)
    out = {}
    for hid, g in d.groupby("dataid"):
        g = g.sort_index()
        g = g[~g.index.duplicated()]
        c = g["grid"] + g[[x for x in ("solar", "solar2") if x in g]].sum(axis=1, min_count=1).fillna(0)
        c[c < -0.05] = np.nan
        out[f"P{hid}"] = c.resample("15min").mean()
    return out


def run(ds, data_dir, site_dir=None, raw=None):
    d = load_processed(site_dir or os.path.join(data_dir, "processed", ds))
    W, w, A = d["W"], d["weather"], d["appliances"]
    sp = {} if site_dir else json.load(open(os.path.join(data_dir, "splits.json")))["datasets"][ds]
    tz = TZ[ds]
    R15 = read_raw(raw, tz) if raw else None
    rows = []
    for h in W.columns:
        if h in sp.get("held_out_homes", []) or h in sp.get("excluded", []) or h not in A:
            continue
        cut = sp.get("time_cut", {}).get(h)
        s = W[h][W.index < pd.Timestamp(cut)] if cut else W[h]
        a = A[h].reindex(s.index).fillna(0).clip(lower=0)
        ev = a[[c for c in a if c == "ev" or category(c, ds) == "ev"]].sum(axis=1)
        wl = decompose._home_weather_load(s, w.reindex(s.index), tz).reindex(s.index).fillna(0)
        kw, sc = detect(s - wl, 1, wl, tz)
        row = dict(home=h, ev=bool(ev.mean() > 0.05), true_kWh=round(float(ev.sum())), h60=sc, est60=round(float(kw.sum())))
        if R15 is not None and h in R15:
            x = R15[h]
            x = x[(x.index >= s.index[0]) & (x.index <= s.index[-1])]
            wl15 = wl.reindex(x.index, method="ffill").fillna(0)
            kw, sc = detect(x - wl15, 4, wl, tz)
            row.update(h15=sc, est15=round(float(kw.sum()) / 4))
        rows.append(row)
        print(row, flush=True)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("--data-dir", default=os.path.join(HERE, "..", "..", "flexibility", "data"))
    ap.add_argument("--site-dir")
    ap.add_argument("--raw")
    a = ap.parse_args()
    run(a.dataset, a.data_dir, a.site_dir, a.raw)
