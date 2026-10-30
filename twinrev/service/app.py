"""TWIN-REV scenario service (OpenAIFlex Task 1.1): what-if EV / PV adoption on a digital twin of an LV substation.

Twin: IEEE European LV test feeder (public CIM) inside TWIN-REV, power flows by TWIN-REV's DSO pipeline (DPsim).
Homes: the 25 Pecan Street Austin homes (mounted, never in git); the feeder's 55 customer points are filled with the
real homes on the studied day plus the same homes on other weeks (scenarios.units), one unit per load point.
Outputs (InfluxDB, Grafana):  lv_scenario,site,day_type,scenario  vmin_pu, vmax_pu, trafo_loading_pct,
max_line_loading_pct, max_line_current_a, net_load_kw (24 h on 2030-01-01, local hours of the studied day);  lv_hosting,site  max_ev_homes,
max_pv_homes (out of 55 units), max_pv_scale_all_homes.
"""
import json, os, threading, traceback, uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import grid as G
import scenarios as SC
from influx import Influx, to_lines

INFLUX = Influx(os.environ.get("INFLUX_URL", "http://influxdb.sogno:8086"), os.environ.get("INFLUX_DB", "openaiflex"))
DATA_DIR = os.environ.get("AUSTIN_DATA_DIR", "/data/austin")
SHOW_DAY = pd.Timestamp("2030-01-01", tz="UTC")       # hours of every studied day are written on this date

app = FastAPI(title="OpenAIFlex - TWIN-REV scenarios", version="0.1.0",
              description="What-if EV / PV adoption on a digital twin of an LV substation (TWIN-REV + DPsim).")
_pool = ThreadPoolExecutor(max_workers=1)
_jobs, _lock = {}, threading.Lock()
_site = {}
_twinrev_lock = threading.Lock()        # one write + power flow at a time: TWIN-REV's profile table is shared
_grid_cache = {}
HERE = os.path.dirname(os.path.abspath(__file__))


class Scenario(BaseModel):
    name: str = Field(..., examples=["ev10"])
    n_ev: Optional[int] = Field(None, ge=0, description="homes with an EV; omit = as in the data")
    n_pv: Optional[int] = Field(None, ge=0, description="homes with PV; omit = as in the data")
    pv_scale: float = Field(1.0, ge=0, description="multiplier of every PV system")


class ScenarioRequest(BaseModel):
    site: str = "austin"
    days: List[str] = Field(["peak", "pv"], description="'peak' (highest net load), 'pv' (lowest net load) or dates YYYY-MM-DD")
    scenarios: Optional[List[Scenario]] = Field(None, description="omit for: today, 2x EV homes, EV in every home, "
                                                "2x PV homes, 2x EV + 2x PV homes")
    n_units: int = Field(55, ge=1, le=G.N_LOAD_POINTS, description="homes on the feeder (one per load point)")
    hosting: List[str] = Field(["ev", "pv", "pv_scale"], description="hosting capacity searches: 'ev' = most EV homes "
                               "(peak day), 'pv' = most PV homes (PV day), 'pv_scale' = with PV on every home, the largest "
                               "PV size multiplier (PV day)")
    v_min_pu: float = Field(0.95, description="planning limit: 5 % drop budget for the LV network (EN 50160 band is 0.90)")
    v_max_pu: float = Field(1.05, description="planning limit (EN 50160 band is 1.10)")
    trafo_max_pct: float = 100.0
    line_max_pct: float = Field(100.0, description="% of the cable's thermal rating")
    seed: int = 0
    write: bool = True


def site():
    if "S" not in _site:
        S = SC.load_site(DATA_DIR)
        S["days"] = SC.extreme_days(S)
        _site["S"] = S
    return _site["S"]


def _twinrev():
    from sqlalchemy import create_engine
    url, db = os.environ.get("TWINREV_URL"), os.environ.get("TWINREV_DB_URL")
    if not url or not db:
        raise RuntimeError("TWINREV_URL and TWINREV_DB_URL must be set")
    return url, create_engine(db, pool_pre_ping=True)


def _set(jid, **kw):
    with _lock:
        _jobs[jid].update(kw)


def _defaults(S, n_units):
    share = lambda k: len(S[k]) / len(S["homes"])
    ev2 = min(round(2 * share("ev_homes") * n_units), n_units)
    pv2 = min(round(2 * share("pv_homes") * n_units), n_units)
    return [Scenario(name="today"), Scenario(name="ev_x2", n_ev=ev2), Scenario(name="ev_all", n_ev=n_units),
            Scenario(name="pv_x2", n_pv=pv2), Scenario(name="ev_x2_pv_x2", n_ev=ev2, n_pv=pv2)]


def _run(jid, req):
    try:
        _set(jid, status="loading data")
        S = site()
        url, engine = _twinrev()
        lim = dict(v_min_pu=req.v_min_pu, v_max_pu=req.v_max_pu, trafo_max_pct=req.trafo_max_pct,
                   line_max_pct=req.line_max_pct)
        days = {d: (S["days"][d] if d in S["days"] else pd.Timestamp(d, tz=SC.TZ)) for d in req.days}
        runs = {"n": 0}

        def simulate(day, sc):
            runs["n"] += 1
            _set(jid, status=f"power flow {runs['n']} ({day.date()}, {sc.name})")
            P, Q, info = SC.scenario(S, day, sc.n_ev, sc.n_pv, sc.pv_scale, req.seed, req.n_units)
            with _twinrev_lock:
                G.write_profiles(engine, G.profile_rows(P, Q, G.placement(list(P.columns))))
                st = G.grid_state(G.run_pipeline(url))
            st["net_load_kw"] = P.sum(axis=1).values
            return st, info

        results, lines = {}, []
        for dname, day in days.items():
            results[dname] = {}
            for sc in (req.scenarios or _defaults(S, req.n_units)):
                st, info = simulate(day, sc)
                results[dname][sc.name] = dict(**info, vmin_pu=round(float(st.vmin_pu.min()), 4),
                                               vmax_pu=round(float(st.vmax_pu.max()), 4),
                                               trafo_loading_max_pct=round(float(st.trafo_loading_pct.max()), 1),
                                               max_line_loading_pct=round(float(st.max_line_loading_pct.max()), 1),
                                               max_line_current_a=round(float(st.max_line_current_a.max()), 1),
                                               hours_over_limit=G.binding(st, lim),
                                               violations=G.violations(st, lim))
                df = st[["vmin_pu", "vmax_pu", "trafo_loading_pct", "max_line_loading_pct", "max_line_current_a",
                         "net_load_kw"]].copy()
                df.index = pd.date_range(SHOW_DAY, periods=24, freq="1h")
                lines += to_lines("lv_scenario", df, {"site": req.site, "day_type": dname, "scenario": sc.name})
        hosting = {}
        for kind, dname in (("ev", "peak"), ("pv", "pv")):
            if kind not in req.hosting:
                continue
            day = S["days"][dname]
            ok = lambda n: not G.violations(simulate(day, Scenario(name=f"hc_{kind}{n}", **{f"n_{kind}": n}))[0], lim)
            lo, hi = 0, req.n_units
            if not ok(lo):
                hosting[f"max_{kind}_homes"] = None
                continue
            if ok(hi):
                lo = hi
            while hi - lo > 1:
                mid = (lo + hi) // 2
                lo, hi = (mid, hi) if ok(mid) else (lo, mid)
            hosting[f"max_{kind}_homes"] = lo
        if "pv_scale" in req.hosting:
            day, n = S["days"]["pv"], req.n_units
            ok = lambda x: not G.violations(simulate(day, Scenario(name=f"hc_pvscale{x:g}", n_pv=n, pv_scale=x))[0], lim)
            lo, hi = 1.0, 8.0
            if not ok(lo):
                hosting["max_pv_scale_all_homes"] = None
            elif ok(hi):
                hosting["max_pv_scale_all_homes"] = hi
            else:
                while hi - lo > 0.125:
                    mid = (lo + hi) / 2
                    lo, hi = (mid, hi) if ok(mid) else (lo, mid)
                hosting["max_pv_scale_all_homes"] = lo
        if hosting:
            hc = {k: [v] for k, v in hosting.items() if v is not None}
            if hc:
                lines += to_lines("lv_hosting", pd.DataFrame(hc, index=[SHOW_DAY]), {"site": req.site})
        n = INFLUX.write(lines) if req.write else 0
        _set(jid, status="done", finished=datetime.now(timezone.utc).isoformat(), power_flows=runs["n"], points_written=n,
             days={k: str(v.date()) for k, v in days.items()}, scenarios=results, hosting_capacity=hosting,
             homes_in_data=len(S["homes"]), units_on_feeder=req.n_units, ev_homes_in_data=len(S["ev_homes"]), pv_homes_in_data=len(S["pv_homes"]),
             grid=dict(trafo_kva=G.TRAFO_KVA, cable_rating_a=G.CABLE_A, limits=lim),
             note="IEEE European LV test feeder (public), DPsim via TWIN-REV; 55 units = the 25 Austin homes on the day + the same homes on other weeks")
    except Exception as e:
        _set(jid, status="failed", error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/site")
def site_info():
    try:
        S = site()
    except Exception as e:
        raise HTTPException(500, f"cannot read {DATA_DIR}: {e}")
    return dict(data_dir=DATA_DIR, homes=len(S["homes"]), ev_homes=S["ev_homes"], pv_homes=S["pv_homes"],
                days={k: str(v.date()) for k, v in S["days"].items()},
                units_on_peak_day={lod: u for u, lod in
                                   G.placement([u for u, _, _ in SC.units(S, S["days"]["peak"])]).items()},
                synthetic=os.path.exists(os.path.join(DATA_DIR, "SYNTHETIC_NOT_REAL_DATA.txt")))


class GridRequest(BaseModel):
    day: str = Field("peak", description="'peak', 'pv' or a date YYYY-MM-DD (2018)")
    n_ev: Optional[int] = Field(None, ge=0, description="homes with an EV; omit = as in the data")
    n_pv: Optional[int] = Field(None, ge=0, description="homes with PV; omit = as in the data")
    pv_scale: float = Field(1.0, ge=0)
    seed: int = 0
    v_min_pu: float = 0.95
    v_max_pu: float = 1.05


@app.post("/grid")
def grid_day(req: GridRequest):
    """One scenario, one day: the state of every node, cable and the transformer for each hour (network view)."""
    key = req.model_dump_json()
    if key in _grid_cache:
        return _grid_cache[key]
    try:
        S = site()
        day = S["days"][req.day] if req.day in S["days"] else pd.Timestamp(req.day, tz=SC.TZ)
        P, Q, info = SC.scenario(S, day, req.n_ev, req.n_pv, req.pv_scale, req.seed)
    except Exception as e:
        raise HTTPException(400, f"{type(e).__name__}: {e}")
    url, engine = _twinrev()
    place = G.placement(list(P.columns))
    try:
        with _twinrev_lock:
            G.write_profiles(engine, G.profile_rows(P, Q, place))
            result = G.run_pipeline(url)
    except Exception as e:
        raise HTTPException(502, f"TWIN-REV power flow failed: {type(e).__name__}: {e}")
    out = dict(request=req.model_dump(), **info, **G.grid_detail(result),
               loads={lod: dict(unit=u, kw=[round(float(x), 2) for x in P[u].values]) for u, lod in place.items()},
               net_kw=[round(float(x), 2) for x in P.sum(axis=1).values],
               limits=dict(v_min_pu=req.v_min_pu, v_max_pu=req.v_max_pu, trafo_max_pct=100.0, line_max_pct=100.0))
    if len(_grid_cache) > 50:
        _grid_cache.clear()
    _grid_cache[key] = out
    return out


@app.get("/grid/layout")
def grid_layout():
    return json.load(open(os.path.join(HERE, "lv_layout.json")))


@app.get("/grid/lines")
def grid_lines():
    return {name: v["cls"] for name, v in G._LINES.items()}


@app.get("/view", response_class=HTMLResponse)
def view():
    return open(os.path.join(HERE, "view.html"), encoding="utf-8").read()


@app.post("/scenarios", status_code=202)
def create(req: ScenarioRequest):
    jid = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[jid] = dict(id=jid, status="queued", request=req.model_dump(), created=datetime.now(timezone.utc).isoformat())
    _pool.submit(_run, jid, req)
    return {"id": jid, "status": "queued"}


@app.get("/scenarios/{jid}")
def get(jid: str):
    with _lock:
        if jid not in _jobs:
            raise HTTPException(404, "unknown job id")
        return _jobs[jid]
