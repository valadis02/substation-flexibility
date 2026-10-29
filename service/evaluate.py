"""Evaluation against sub-metering (only for research datasets that have it; never used to make the prediction).

The method sees only each home's total. The truth comes from the dataset's appliance circuits, as in test T12:
  weather   = heating / cooling circuits, ev = car circuits, shiftable = washing machine, dryer, dishwasher, ...
  true envelope = the same M5 rule applied to the true decomposition (same base, same allocation order) over the
                  same recent days -> true_down_kw, true_up_kw per hour of the average day
  realised flexible load on the target day = the sum of those circuits at each hour (what could actually have
                  been reduced that day)
"""
import os
import numpy as np
import pandas as pd
from flexsub import ev as m6, flexibility
from flexsub.appliances import category
from flexsub.data import load_processed

THERMAL = lambda c, ds: category(c, ds) == "thermal" or c in ("ac", "furnace", "heater") or c.startswith("ac_")


def truth(dataset, homes, index, data_dir):
    """Per-hour sum over `homes` of the true weather / ev / shiftable circuits on `index` (UTC)."""
    d = load_processed(os.path.join(data_dir, "processed", dataset))
    parts = []
    for h in homes:
        A = d["appliances"].get(h)
        if A is None:
            raise ValueError(f"no sub-metering for home {h} in {dataset}")
        A = A.reindex(index)
        sh = [c for c in A.columns if category(c, dataset) == "shiftable"]
        th = [c for c in A.columns if THERMAL(c, dataset)]
        ev = [c for c in A.columns if category(c, dataset) == "ev"]
        z = pd.Series(0.0, index=index)
        parts.append(pd.DataFrame({"weather": A[th].sum(axis=1) if th else z, "ev": A[ev].sum(axis=1) if ev else z,
                                   "shiftable": A[sh].sum(axis=1, min_count=len(sh)) if sh else z}))
    return sum(parts)


def true_envelope(X, tru, cfg):
    """M5 rule on the true decomposition, same base and allocation order as the estimate X (T12)."""
    T = X[["actual", "base"]].copy()
    rem = T.actual - T.base
    for name, val in (("thermal", tru.weather), ("ev", tru.ev), ("shiftable", tru.shiftable)):
        T[name] = np.minimum(val.reindex(T.index).fillna(0).clip(lower=0), rem)
        rem = rem - T[name]
    T["routine"] = rem
    T.attrs["ev_sessions"] = {}
    if tru.ev.sum() > 0:
        e = tru.ev.reindex(T.index).fillna(0)
        T.attrs["ev_sessions"] = {"all": m6.sessions(e, e > 0.3, cfg.tz)}
    return flexibility.flexibility_by_hour(T, cfg)
