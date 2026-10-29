"""Low Carbon London (LCL) smart-meter data -> hourly group sums for T1 (and later T6).

The raw data (5,567 homes, half-hourly kWh, ~10 GB) is too large for git, and T1 only needs substation-size
sums, so this script builds the groups on the machine that has the raw CSV and commits only the sums.

    python scripts/prepare_lcl.py C:\\Users\\...\\LCL-FullData

Steps
1. Read every CSV in the folder in chunks (columns by position: id, tariff Std/ToU, DateTime, kWh/half-hour).
2. Hourly energy per home = sum of the two half-hours (kWh in one hour = mean kW); hours with a missing half are NaN.
3. Split (fixed seed 2026): 20% of homes held out for the final test; the last 20% of time (by home-hours) is final only.
4. Groups of N = 50, 150, 500 homes drawn separately from Std homes (no price signal: used for T1) and from ToU homes
   (dynamic tariff in 2013: kept for T6). An hour of a group is kept if >= 90% of its members have data; the sum is
   scaled by N / (members with data).
Output: data/processed/lcl/groups.csv.gz (hourly kW, UTC), groups_meta.json (members, cut, counts).
Timestamps are GMT without BST adjustment (TU Delft refactored-LCL notes), i.e. UTC. Repeated rows are dropped
(within a chunk); hours that still have more than two readings are discarded.
"""
import glob, json, os, sys, time
import numpy as np
import pandas as pd

SEED, HELD_OUT, FINAL_SHARE, MIN_PRESENT = 2026, 0.2, 0.2, 0.9
SIZES = {50: 5, 150: 5, 500: 3}          # N -> number of groups
T0 = pd.Timestamp("2011-11-01", tz="UTC")
T1 = pd.Timestamp("2014-03-01", tz="UTC")
NH = int((T1 - T0) / pd.Timedelta("1h"))

src = sys.argv[1]
files = sorted(f for f in glob.glob(os.path.join(src, "**", "*.csv"), recursive=True) if "tariff" not in f.lower())
print("files:", len(files), files[:3])
with open(files[0]) as f:
    print("header + first rows:\n" + "".join(next(f) for _ in range(3)))

ids, tariff = {}, {}
S = None; C = None
dup_homes = set()
t = time.time(); rows = 0
for fn in files:
    for ch in pd.read_csv(fn, usecols=[0, 1, 2, 3], header=0, names=["id", "tariff", "dt", "kwh"], chunksize=5_000_000,
                          dtype={"id": str, "tariff": str, "dt": str, "kwh": str}):
        ch["kwh"] = pd.to_numeric(ch["kwh"].str.strip(), errors="coerce")
        ch = ch.dropna(subset=["kwh"]).drop_duplicates(subset=["id", "dt"])   # LCL has repeated rows
        ts = pd.to_datetime(ch["dt"].str[:19], format="%Y-%m-%d %H:%M:%S", errors="coerce").dt.tz_localize("UTC")
        ok = ts.notna() & (ts >= T0) & (ts < T1)
        ch, ts = ch[ok], ts[ok]
        for i, tr in zip(ch["id"].unique(), ch.groupby("id", sort=False)["tariff"].first()):
            if i not in ids:
                ids[i] = len(ids); tariff[i] = str(tr).strip()
        if S is None or len(ids) > S.shape[0]:
            n = max(len(ids), 6000)
            S2 = np.zeros((n, NH), np.float32); C2 = np.zeros((n, NH), np.int8)
            if S is not None:
                S2[:S.shape[0]] = S; C2[:C.shape[0]] = C
            S, C = S2, C2
        hi = ch["id"].map(ids).to_numpy()
        # half-hour stamp -> hour index (00:00 and 00:30 belong to hour 00)
        ti = ((ts - T0) // pd.Timedelta("1h")).to_numpy()
        np.add.at(S, (hi, ti), ch["kwh"].to_numpy(np.float32))
        np.add.at(C, (hi, ti), 1)
        rows += len(ch)
        print(f"{rows/1e6:.0f}M rows, {len(ids)} homes, {time.time()-t:.0f} s", flush=True)

H = len(ids)
S, C = S[:H], C[:H]
dup_homes = int((C > 2).any(axis=1).sum())
print(f"homes with >2 readings in some hour (repeated timestamps): {dup_homes}")
X = np.where(C == 2, S, np.nan).astype(np.float32)        # hourly kWh = mean kW
del S, C
names = np.array(sorted(ids, key=ids.get))
tar = np.array([tariff[i] for i in names])
idx = pd.date_range(T0, periods=NH, freq="h")

rng = np.random.default_rng(SEED)
held = set(rng.choice(names, size=int(round(HELD_OUT * H)), replace=False))
dev = np.array([n not in held for n in names])
have = ~np.isnan(X[dev])
cum = np.cumsum(have.sum(axis=0)); cut = idx[int(np.searchsorted(cum, (1 - FINAL_SHARE) * cum[-1]))]
print("tariffs:", dict(zip(*np.unique(tar, return_counts=True))), "| held out:", len(held), "| time cut:", cut)

out, meta = {}, {"seed": SEED, "time_cut": str(cut), "held_out_share": HELD_OUT, "min_present": MIN_PRESENT,
                 "homes": int(H), "tariff_counts": {k: int(v) for k, v in zip(*np.unique(tar, return_counts=True))},
                 "repeated_timestamp_homes": dup_homes, "groups": {}}
for part, mask_part in (("dev", dev), ("final", ~dev)):
    for tclass in ("Std", "ToU"):
        pool = np.where(mask_part & (tar == tclass))[0]
        for N, k in SIZES.items():
            if len(pool) < N:
                continue
            for g in range(k):
                mem = rng.choice(pool, size=N, replace=False)
                M = X[mem]
                present = (~np.isnan(M)).sum(axis=0)
                tot = np.nansum(M, axis=0) * N / np.maximum(present, 1)
                tot[present < MIN_PRESENT * N] = np.nan
                col = f"{part}_{tclass}_N{N}_g{g}"
                out[col] = tot
                meta["groups"][col] = {"members": names[mem].tolist(), "hours": int(np.isfinite(tot).sum())}
                print(col, "hours with >=90% members:", int(np.isfinite(tot).sum()), flush=True)

od = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "lcl")
os.makedirs(od, exist_ok=True)
G = pd.DataFrame(out, index=idx).dropna(how="all")
G.round(4).to_csv(os.path.join(od, "groups.csv.gz"), index_label="timestamp")
with open(os.path.join(od, "groups_meta.json"), "w") as f:
    json.dump(meta, f, indent=1)
print("written", os.path.abspath(od), f"{sum(os.path.getsize(os.path.join(od, x)) for x in os.listdir(od))/1e6:.1f} MB")
