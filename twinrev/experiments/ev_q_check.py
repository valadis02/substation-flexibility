"""EV detection against the car circuits, for several reference quantiles of flexsub.ev.ev_home (development data only).
  python3 -W ignore ev_q_check.py --data-dir ../../flexibility/data pecan_austin pecan_newyork
Reports per dataset and q: EV homes found, false homes (found, no car), and estimated / true EV energy over those homes."""
import argparse, json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "flexibility"))
from flexsub import decompose, ev as m6                                  # noqa: E402
from flexsub.appliances import category                                  # noqa: E402
from flexsub.config import Config                                        # noqa: E402
from flexsub.data import load_processed                                  # noqa: E402

TZ = {"pecan_austin": "America/Chicago", "pecan_newyork": "America/New_York", "pecan_california": "America/Los_Angeles"}


two_group_reference = m6.two_group_reference


def ev_home_auto(y, k, gate, max_cv, weather_load, tz, min_runs=5, min_rate_ratio=0.5):
    """flexsub.ev.ev_home with the reference above and two tests against air conditioning. Days are ranked per home by
    their weather-dependent load, in thirds:
    1. A car charges about as often when the weather load is low as when it is high: the home needs sessions on the low
       third, at a rate of at least min_rate_ratio (the only added number) of the rate on the high third.
    2. The charger's step comes from the sessions on the low third (no air conditioning on top). Only sessions within its
       10-90 % range count, on any day, and no hour counts for more than the top of that range."""
    wl = weather_load.reindex(y.index).fillna(0)
    y = y - wl
    ref = two_group_reference(y, k)
    exc = y - ref
    core = (exc > k) & ref.notna()
    none = exc.clip(lower=0).where(core & False, 0.0).where(ref.notna()), core & False
    rid = (core != core.shift()).cumsum()
    runs = [g for _, g in exc[core].groupby(rid[core])]
    cvs = [g.std() / g.mean() for g in runs if len(g) >= 2]
    if core.mean() < gate or len(cvs) < min_runs or np.median(cvs) > max_cv:
        return none
    day = pd.Series(y.index.tz_convert(tz).date, index=y.index)
    load = wl.groupby(day.values).sum()
    rank = load.rank(method="first", pct=True)
    low, high = set(rank.index[rank <= 1 / 3]), set(rank.index[rank > 2 / 3])
    step = np.array([g.median() for g in runs])
    start = np.array([day[g.index[0]] for g in runs])
    in_low, in_high = np.array([d in low for d in start]), np.array([d in high for d in start])
    if in_low.sum() < min_runs or in_low.sum() / max(len(low), 1) < min_rate_ratio * in_high.sum() / max(len(high), 1):
        return none
    lo, hi = np.quantile(step[in_low], [0.1, 0.9])
    keep = pd.Series(False, index=y.index)
    for g, m in zip(runs, step):
        if lo <= m <= hi:
            keep[g.index] = True
    mask = keep | ((exc > k / 2) & (keep.shift(1, fill_value=False) | keep.shift(-1, fill_value=False)))
    return exc.clip(lower=0, upper=hi).where(mask, 0.0).where(ref.notna()), mask


def check(data_dir, ds, qs, site_dir=None):
    d = load_processed(site_dir or os.path.join(data_dir, "processed", ds))
    W, w, A = d["W"], d["weather"], d["appliances"]
    split = {}
    if not site_dir:
        split = json.load(open(os.path.join(data_dir, "splits.json")))["datasets"].get(ds, {})
    homes = [h for h in W.columns if h in A and h not in split.get("held_out_homes", []) and h not in split.get("excluded", [])]
    cfg = Config(tz=TZ.get(ds, "America/Chicago"))
    rows, data = [], {}
    for h in homes:
        s = W[h]
        cut = split.get("time_cut", {}).get(h)
        if cut:
            s = s[s.index < pd.Timestamp(cut)]
        cars = [c for c in A[h].columns if c == "ev" or category(c, ds) == "ev"]
        t = A[h][cars].sum(axis=1).reindex(s.index).fillna(0.0).clip(lower=0) if cars else 0.0 * s
        data[h] = (s, t, decompose._home_weather_load(s, w.reindex(s.index), cfg.tz))
    for q in qs:
        found = false = miss = 0
        est = true = 0.0
        for h, (s, t, wl) in data.items():
            if q == "auto":
                kw, mask = ev_home_auto(s, cfg.ev_k, cfg.ev_gate, cfg.ev_max_cv, wl, cfg.tz)
            else:
                kw, mask = m6.ev_home(s, k=cfg.ev_k, gate=cfg.ev_gate, max_cv=cfg.ev_max_cv, weather_load=wl, q=q)
            has, got = t.mean() > 0.05, bool(mask.any())
            found += has and got
            miss += has and not got
            false += got and not has
            if has:
                est += float(kw.fillna(0).sum())
                true += float(t.sum())
        rows.append(dict(dataset=ds, q=q, homes=len(data), ev_homes=int(found + miss), found=int(found), false_homes=int(false),
                         energy_ratio=round(est / true, 3) if true else None))
        print(rows[-1], flush=True)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("datasets", nargs="+")
    ap.add_argument("--data-dir", default=os.path.join(HERE, "..", "..", "flexibility", "data"))
    ap.add_argument("--site-dir")
    ap.add_argument("--q", nargs="+", default=["0.6"], help="gate quantile of flexsub.ev.ev_home, or auto (older test)")
    a = ap.parse_args()
    a.q = [x if x == "auto" else float(x) for x in a.q]
    for ds in a.datasets:
        check(a.data_dir, ds, a.q, a.site_dir)
