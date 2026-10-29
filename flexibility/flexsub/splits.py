"""Locked development / final-test split (docs/test_plan.pdf, section 6).

Two parts, both frozen in data/splits.json and never changed after the first commit:
  * held-out homes: a fixed random subset of each dataset's homes is used only in the final test;
  * time: for every home, the last `final_share` of its hours (by count of hours with data) is final-test only.
All tuning happens on the remaining development data. The final test is run once, after the method is frozen.
"""
import json, os
import numpy as np
import pandas as pd

SPLIT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "splits.json")


def make(W_by_dataset, held_out_counts, exclude=None, final_share=0.2, seed=2026):
    exclude = exclude or {}
    rng = np.random.default_rng(seed)
    out = {"seed": seed, "final_share": final_share, "datasets": {}}
    for name, W in W_by_dataset.items():
        homes = [h for h in W.columns if h not in exclude.get(name, [])]
        k = held_out_counts.get(name, 0)
        held = sorted(rng.choice(homes, size=k, replace=False).tolist()) if k else []
        cuts = {}
        for h in homes:
            t = W[h].dropna().index
            cuts[h] = str(t[int(np.floor(len(t) * (1 - final_share)))])
        out["datasets"][name] = {"excluded": sorted(exclude.get(name, [])), "held_out_homes": held, "time_cut": cuts}
    return out


def load(path=SPLIT_FILE):
    with open(path) as f:
        return json.load(f)


def development(W, dataset, split=None):
    """Development view: drop excluded and held-out homes, blank every home's hours at/after its time cut."""
    s = (split or load())["datasets"][dataset]
    keep = [h for h in W.columns if h not in s["excluded"] and h not in s["held_out_homes"]]
    D = W[keep].copy()
    for h in keep:
        D.loc[D.index >= pd.Timestamp(s["time_cut"][h]), h] = np.nan
    return D


def final_test(W, dataset, split=None):
    """Final-test view (use once): all non-excluded homes; for development homes only hours at/after the cut,
    held-out homes in full."""
    s = (split or load())["datasets"][dataset]
    keep = [h for h in W.columns if h not in s["excluded"]]
    F = W[keep].copy()
    for h in keep:
        if h not in s["held_out_homes"]:
            F.loc[F.index < pd.Timestamp(s["time_cut"][h]), h] = np.nan
    return F
