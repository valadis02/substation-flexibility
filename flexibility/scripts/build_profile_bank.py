"""Build the profile bank for M3 design B (flexsub.shiftable): one entry per public sub-metered dataset, with the
shiftable share, shiftable kW per home and load-shape signature by hour x day type (development homes only).

    python scripts/build_profile_bank.py [--with-pecan]
Writes data/profile_bank.json (committed: derived from CC BY 4.0 datasets). With --with-pecan it writes
data/processed/profile_bank_local.json instead (Pecan Street terms: keep local).
"""
import argparse, json, os
import numpy as np
import pandas as pd
from flexsub import splits, shiftable
from flexsub.appliances import category
from flexsub.data import load_processed

TZ = {"refit": "Europe/London", "ukdale": "Europe/London", "plegma": "Europe/Athens",
      "pecan_austin": "America/Chicago", "pecan_newyork": "America/New_York"}
ap = argparse.ArgumentParser(); ap.add_argument("--with-pecan", action="store_true"); a = ap.parse_args()
names = [n for n in TZ if a.with_pecan or not n.startswith("pecan")]
bank = {}
for ds in names:
    d = load_processed(os.path.join("data", "processed", ds))
    W = splits.development(d["W"], ds)
    T = {}
    for h in W.columns:
        A = d["appliances"][h].reindex(W.index)
        if "ev" in A.columns and A["ev"].mean() > 0.05:
            continue
        sh = [c for c in A.columns if category(c, ds) == "shiftable"]
        if sh:
            T[h] = A[sh].sum(axis=1, min_count=len(sh))
    if not T:
        continue
    T = pd.DataFrame(T)
    e = shiftable.bank_entry(W[T.columns], T, TZ[ds])
    bank[ds] = {k: [None if np.isnan(x) else float(x) for x in v.values] for k, v in e.items()}
    bank[ds]["homes"] = int(T.shape[1])
out = "data/processed/profile_bank_local.json" if a.with_pecan else "data/profile_bank.json"
json.dump(bank, open(out, "w"), indent=1)
print("written", out, {k: v["homes"] for k, v in bank.items()})
