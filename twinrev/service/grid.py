"""The digital twin side: IEEE European LV test feeder as TWIN-REV cell 3, power flows by TWIN-REV's DSO pipeline.

Homes are placed on the feeder's load points (lod_01 ... lod_55, renamed by twinrev/cim/make_lv_zip.py); load points
without a home get zero. Profiles go to TWIN-REV's table dso_power_profiles_data_cel3 and each run is
POST /dso/dpsim/run-pipeline (its DPsim service simulates). Results: LV voltages (pu of 400 V), transformer loading
(% of 800 kVA, the feeder's rating), largest line current (A; the CIM export has no line ratings).
"""
import json, urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

N_LOAD_POINTS = 55
LV_BASE_V = 400.0
TRAFO_KVA = 800.0
TRAFO = "TR1"
REPLACE_MAP = {"lod_": "LOD_lod_"}
RUN_DAY = datetime(2030, 1, 1)           # placeholder date of the profiles in TWIN-REV's table (overwritten per run)


def placement(homes, n_points=N_LOAD_POINTS):
    """Homes spread evenly along the feeder's load points (lod_01 ... lod_55)."""
    k = len(homes)
    if k > n_points:
        raise ValueError(f"{k} homes but the feeder has {n_points} load points")
    pts = [int(round(i * (n_points - 1) / max(k - 1, 1))) + 1 for i in range(k)]
    return {h: f"lod_{p:02d}" for h, p in zip(homes, pts)}


def profile_rows(P, Q, place, n_points=N_LOAD_POINTS):
    """Rows for TWIN-REV (MW, Mvar); every load point gets a value so that no CIM default (1 kW) remains."""
    rows = []
    for i in range(24):
        ts = RUN_DAY + timedelta(hours=i)
        for p in range(1, n_points + 1):
            lod = f"lod_{p:02d}"
            homes = [h for h, l in place.items() if l == lod]
            pv = sum(float(P[h].iloc[i]) for h in homes) / 1000.0
            qv = sum(float(Q[h].iloc[i]) for h in homes) / 1000.0
            rows.append((ts, lod, lod, "LOAD", "active", pv))
            rows.append((ts, lod, lod, "LOAD", "reactive", qv))
    return rows


def write_profiles(engine, rows):
    from sqlalchemy import text
    with engine.begin() as c:
        c.execute(text("DELETE FROM dso_power_profiles_data_cel3 WHERE ts >= :a AND ts < :b"),
                  {"a": RUN_DAY, "b": RUN_DAY + timedelta(days=1)})
        c.execute(text("INSERT INTO dso_power_profiles_data_cel3 (ts, bus, component_id, profile_type, power_type, value) "
                       "VALUES (:ts, :bus, :cid, :pt, :pw, :v)"),
                  [dict(ts=r[0], bus=r[1], cid=r[2], pt=r[3], pw=r[4], v=float(r[5])) for r in rows])


def run_pipeline(twinrev_url, timeout=180):
    body = dict(cell=3, date=RUN_DAY.date().isoformat(), duration=24, timestep=1, freq=50, solver="NRP", domain="SP",
                opf=False, replace_map=REPLACE_MAP, load_scale=1.0, gen_scale=1.0)
    req = urllib.request.Request(f"{twinrev_url.rstrip('/')}/dso/dpsim/run-pipeline", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read().decode())
    if "result" not in out:
        raise RuntimeError(f"TWIN-REV pipeline: {str(out)[:500]}")
    return out["result"]


def grid_state(result):
    """Per hour: lowest / highest LV voltage (pu), worst node, transformer loading (%), largest line current (A)."""
    res = {k: np.asarray(v, dtype=float) for k, v in result.items() if isinstance(v, list) and k != "time"}
    nodes = sorted(k[:-5] for k in res if k.endswith("_V.re"))
    V = pd.DataFrame({n: np.hypot(res[f"{n}_V.re"], res[f"{n}_V.im"]) for n in nodes})
    V = V.loc[:, V.mean() < 1000] / LV_BASE_V                        # LV nodes only (the 11 kV side is excluded)
    lines = sorted({k[:-7] for k in res if k.endswith("_I_0.re")} - {TRAFO})
    I = pd.DataFrame({l: np.hypot(res[f"{l}_I_0.re"], res[f"{l}_I_0.im"]) for l in lines})
    s_kva = np.hypot(res[f"{TRAFO}_P_0"], res[f"{TRAFO}_Q_0"]) / 1000.0
    return pd.DataFrame({"vmin_pu": V.min(axis=1), "vmax_pu": V.max(axis=1), "worst_low_node": V.idxmin(axis=1),
                         "worst_high_node": V.idxmax(axis=1), "trafo_loading_pct": 100 * s_kva / TRAFO_KVA,
                         "max_line_current_a": I.max(axis=1), "busiest_line": I.idxmax(axis=1)})


def violations(state, lim):
    v = []
    if state.vmin_pu.min() < lim["v_min_pu"]:
        v.append(f"undervoltage {state.vmin_pu.min():.3f} pu at {int(state.vmin_pu.idxmin())}:00 ({state.worst_low_node[state.vmin_pu.idxmin()]})")
    if state.vmax_pu.max() > lim["v_max_pu"]:
        v.append(f"overvoltage {state.vmax_pu.max():.3f} pu at {int(state.vmax_pu.idxmax())}:00 ({state.worst_high_node[state.vmax_pu.idxmax()]})")
    if state.trafo_loading_pct.max() > lim["trafo_max_pct"]:
        v.append(f"transformer {state.trafo_loading_pct.max():.0f}% at {int(state.trafo_loading_pct.idxmax())}:00")
    return v
