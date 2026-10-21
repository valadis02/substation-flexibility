"""Synthetic households with KNOWN components, to sanity-check the pipeline (not a substitute for real validation)."""
import numpy as np
import pandas as pd


def make(n_houses=12, days=60, start="2026-07-01", tz="Europe/Athens", seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=24 * days, freq="h", tz=tz).tz_convert("UTC")
    loc = idx.tz_convert(tz)
    d = np.arange(len(idx)) / 24.0
    temp = 28 - 0.12 * d + 6 * np.sin(2 * np.pi * (loc.hour - 9) / 24) + rng.normal(0, 1.2, len(idx))
    w = pd.DataFrame({"temp": temp, "rh": 50 + rng.normal(0, 5, len(idx)), "cloud": rng.uniform(0, 60, len(idx)),
                      "rad": np.clip(800 * np.sin(np.pi * (loc.hour - 6) / 12), 0, None), "is_day": ((loc.hour >= 6) & (loc.hour < 20)).astype(int)}, index=idx)
    comp = {k: pd.DataFrame(0.0, index=idx, columns=range(n_houses)) for k in ("base", "thermal", "shift", "routine")}
    for h in range(n_houses):
        comp["base"][h] = rng.uniform(0.08, 0.2)
        has_ac = rng.random() < 0.7
        if has_ac:
            comp["thermal"][h] = 0.25 * np.clip(temp - 24, 0, None) * (loc.hour >= 12) * rng.uniform(0.6, 1.2)
        comp["routine"][h] = 0.1 + 0.15 * np.exp(-((loc.hour - 20) ** 2) / 8) + rng.normal(0, 0.02, len(idx)).clip(-0.04, 0.04)
        ev = np.zeros(len(idx))
        for day in range(days):
            if rng.random() < 0.5:                       # a dishwasher/washer-like event, 1-2 h, 1.5 kW
                s = day * 24 + rng.choice([9, 10, 13, 19, 20, 21]); L = rng.integers(1, 3)
                ev[s:s + L] += 1.5
        comp["shift"][h] = ev
    W = sum(comp.values())
    truth = {k: v.sum(axis=1) for k, v in comp.items()}
    return W, w, truth
