"""SYNTHETIC stand-in for the processed Pecan Street Austin data (25 homes, 2018), for tests only.

Same files and columns as flexibility/scripts/prepare_data.py pecan_austin writes (hourly kW, UTC index):
  mains.csv.gz              timestamp, P<id> ...      consumption = grid + solar (gross load, kW)
  appliances_P<id>.csv.gz   timestamp, ac, ev, solar, dryer, ...   circuits (kW)
The numbers are invented (daily/seasonal shapes, AC with temperature, EV evening charging, PV bell curve); they are
NOT Austin results. Real data: build it with flexibility/scripts/prepare_data.py from the Dataport file (not in git).
    python3 make_synthetic_austin.py <out_dir>
"""
import os, sys
import numpy as np, pandas as pd

def main(out, n_homes=25, n_ev=8, n_pv=12, seed=7):
    rng = np.random.default_rng(seed)
    os.makedirs(out, exist_ok=True)
    idx = pd.date_range("2018-01-01", "2019-01-01", freq="1h", tz="America/Chicago", inclusive="left")
    h, doy = idx.hour.values, idx.dayofyear.values
    temp = 20 + 9 * np.sin(2 * np.pi * (doy - 110) / 365) + 6 * np.sin(2 * np.pi * (h - 9) / 24) + rng.normal(0, 1.5, len(idx))
    clear = np.clip(np.sin(np.pi * (h - 6.5) / 13), 0, None) * (0.75 + 0.25 * np.sin(2 * np.pi * (doy - 80) / 365))
    cloud = np.clip(rng.normal(0.8, 0.25, len(idx) // 24 + 1), 0.1, 1.0).repeat(24)[: len(idx)]
    homes = [f"P{1000 + 37 * i}" for i in range(n_homes)]
    ev_homes, pv_homes = set(homes[:n_ev]), set(homes[n_ev // 2: n_ev // 2 + n_pv])
    W = {}
    for k, hid in enumerate(homes):
        base = 0.35 + 0.1 * rng.random()
        daily = 0.6 * np.exp(-((h - 19) ** 2) / 8) + 0.35 * np.exp(-((h - 8) ** 2) / 4)
        other = base + daily * (0.8 + 0.6 * rng.random()) + rng.gamma(1.2, 0.15, len(idx))
        ac = np.clip(temp - 24, 0, None) * (0.25 + 0.15 * rng.random()) * (0.6 + 0.4 * rng.random(len(idx)))
        heat = np.clip(10 - temp, 0, None) * 0.15 * rng.random()
        dryer = (rng.random(len(idx)) < 0.02) * rng.uniform(2.5, 4.5, len(idx))
        ev = np.zeros(len(idx))
        if hid in ev_homes:
            for d0 in range(0, len(idx), 24):
                if rng.random() < 0.55:
                    st = d0 + int(np.clip(rng.normal(19, 2), 15, 23)); dur = int(rng.integers(2, 6)); pw = rng.choice([3.3, 6.6, 7.2])
                    ev[st: st + dur] = pw
        solar = np.zeros(len(idx))
        if hid in pv_homes:
            kwp = rng.uniform(4, 8)
            solar = kwp * 0.8 * clear * cloud * (0.9 + 0.1 * rng.random(len(idx)))
        cons = other + ac + heat + dryer + ev
        W[hid] = cons
        A = pd.DataFrame({"ac": ac, "heater": heat, "dryer": dryer, "ev": ev, "solar": solar}, index=idx.tz_convert("UTC"))
        A.index.name = "timestamp"
        A.round(4).to_csv(os.path.join(out, f"appliances_{hid}.csv.gz"))
    M = pd.DataFrame(W, index=idx.tz_convert("UTC")); M.index.name = "timestamp"
    M.round(4).to_csv(os.path.join(out, "mains.csv.gz"))
    open(os.path.join(out, "SYNTHETIC_NOT_REAL_DATA.txt"), "w").write("Synthetic stand-in for tests. Not Pecan Street data.\n")
    print(f"wrote {n_homes} synthetic homes ({n_ev} EV, {n_pv} PV) to {out}")

if __name__ == "__main__":
    main(sys.argv[1])
