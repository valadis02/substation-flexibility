"""Units for the thermal tests (T2): (dataset, unit, kind, load, true thermal, weather, Config).
kind: 'ac' / 'heater' = has a measured thermal circuit; 'control' = has none. Groups = all development homes summed
(hours with enough homes present, scaled)."""
import numpy as np
import pandas as pd
from flexsub import Config, splits
from flexsub.data import load_processed


def season(idx):
    m = idx.month
    return np.where(np.isin(m, [5, 6, 7, 8, 9]), "cooling", np.where(np.isin(m, [11, 12, 1, 2, 3]), "heating", "mild"))


PECAN = {"pecan_austin": ("America/Chicago", 30.27, True), "pecan_newyork": ("America/New_York", 42.44, True),
         "pecan_california": ("America/Los_Angeles", 32.72, False)}   # tz, latitude, homes overlap in time (group)


def pecan_units(name):
    tz, lat, group = PECAN[name]
    cfg = Config(tz=tz, latitude=lat)
    d = load_processed(f"data/processed/{name}"); W = splits.development(d["W"], name)
    out, truth_all = [], {}
    for h in W.columns:
        A = d["appliances"][h].reindex(W.index)
        th = [c for c in ("ac", "furnace", "heater") if c in A.columns]   # electric heating/cooling circuits
        t = A[th].sum(axis=1, min_count=1) if th else pd.Series(0.0, index=W.index)
        t[W[h].isna()] = np.nan
        truth_all[h] = t
        out.append((name, h, "ac" if "ac" in th else "control", W[h], t, d["weather"], cfg))
    if group:
        T = pd.DataFrame(truth_all); present = W.notna() & T.notna(); n = present.sum(axis=1)
        keep = n >= 0.8 * W.shape[1]
        yg = (W.where(present).sum(axis=1) * W.shape[1] / n).where(keep)
        tg = (T.where(present).sum(axis=1) * W.shape[1] / n).where(keep)
        out.append((name, f"group({W.shape[1]} homes)", "ac", yg, tg, d["weather"], cfg))
    return out


def units(which):
    out = []
    for name in which:
        if name.startswith("pecan"):
            out += pecan_units(name)
    if "plegma" not in which:
        return out
    # Plegma
    cfgP = Config(tz="Europe/Athens", latitude=37.98)
    d = load_processed("data/processed/plegma"); W = splits.development(d["W"], "plegma")
    truth_all = {}
    import os
    wide = os.environ.get("T2_TRUTH") == "weather_sensitive"     # AC + water heater + fridges (diagnostic for T2 v3)
    for h in W.columns:
        A = d["appliances"][h].reindex(W.index)
        ac = [c for c in A.columns if c.startswith(("ac", "boiler", "fridge")) if wide or c.startswith("ac")]
        truth_all[h] = A[ac].sum(axis=1, min_count=len(ac)) if ac else pd.Series(0.0, index=W.index)
        truth_all[h][W[h].isna()] = np.nan
        out.append(("plegma", h, "ac" if ac else "control", W[h], truth_all[h], d["weather"], cfgP))
    T = pd.DataFrame(truth_all)
    present = W.notna() & T.notna()
    n = present.sum(axis=1)
    keep = n >= 6
    yg = (W.where(present).sum(axis=1) * W.shape[1] / n).where(keep)
    tg = (T.where(present).sum(axis=1) * W.shape[1] / n).where(keep)
    out.append(("plegma", "group(>=6 homes)", "ac", yg, tg, d["weather"], cfgP))
    if "refit" not in which:
        return out
    # REFIT
    cfgR = Config(tz="Europe/London", latitude=52.77)
    d = load_processed("data/processed/refit"); W = splits.development(d["W"], "refit")
    truths = {}
    for h in W.columns:
        A = d["appliances"][h].reindex(W.index)
        hc = [c for c in A.columns if "Heater" in c]
        t = A[hc].sum(axis=1, min_count=len(hc)) if hc else pd.Series(0.0, index=W.index)
        t[W[h].isna()] = np.nan
        truths[h] = t
    T = pd.DataFrame(truths); present = W.notna() & T.notna(); n = present.sum(axis=1)
    keep = n >= 0.8 * W.shape[1]
    out.append(("refit", f"group({W.shape[1]} homes)", "heater", (W.where(present).sum(axis=1) * W.shape[1] / n).where(keep),
                (T.where(present).sum(axis=1) * W.shape[1] / n).where(keep), d["weather"], cfgR))
    for h in ("H1", "H9", "H16", "H3", "H5"):
        A = d["appliances"][h].reindex(W.index)
        hc = [c for c in A.columns if "Heater" in c]
        t = A[hc].sum(axis=1, min_count=len(hc)) if hc else pd.Series(0.0, index=W.index)
        t[W[h].isna()] = np.nan
        out.append(("refit", h, "heater" if hc else "control", W[h], t, d["weather"], cfgR))
    return out


