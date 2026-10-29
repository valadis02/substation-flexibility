"""Flexibility envelope service (OpenAIFlex, SOGNO-style): job API over the flexsub method.

Inputs are read from InfluxDB, outputs are written back to it:
  meter,site=<site>,home=<id>  kw=<hourly kW>
  weather,site=<site>          temp=,rh=,cloud=,rad=,is_day=
  -> substation,site=<site>    load_kw, forecast_*, base/routine/thermal/appliances_kw, down/up_kw_avgday
  -> envelope,site=<site>      one point per hour of the average day (time = hour on 1970-01-01), all M5 columns
  -> dayahead,site=<site>      24 hours of the target day: forecast_kw, forecast_lo/hi_kw, down_kw, up_kw (+ actual_kw
                               afterwards, for evaluation only, when the day is already in the database)
"""
import os, threading, traceback, uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from flexsub import Config, pipeline
from influx import Influx, to_lines
import dayahead as DA

INFLUX = Influx(os.environ.get("INFLUX_URL", "http://influxdb.sogno:8086"), os.environ.get("INFLUX_DB", "openaiflex"))
WEATHER_COLS = ["temp", "rh", "cloud", "rad", "is_day"]

app = FastAPI(title="OpenAIFlex flexibility envelope", version="0.2.0",
              description="Substation flexibility (kW down / up) from hourly smart-meter data and weather only (flexsub v0.10).")
_pool = ThreadPoolExecutor(max_workers=1)   # one method run at a time; jobs queue up
_jobs, _lock = {}, threading.Lock()


class EnvelopeRequest(BaseModel):
    site: str = Field(..., examples=["plegma-dev"])
    start: str = Field(..., description="first day to evaluate (local date)", examples=["2023-06-15"])
    end: str = Field(..., description="last day to evaluate (local date)", examples=["2023-07-20"])
    history_days: int = Field(75, ge=14, description="days of data before `start` used for training")
    tz: str = "Europe/Athens"
    participation: Optional[float] = Field(None, ge=0, le=1, description="enrolment share; omit for technical maximum")
    response: float = Field(1.0, ge=0, le=1)
    write: bool = Field(True, description="write results to InfluxDB")


def _set(jid, **kw):
    with _lock:
        _jobs[jid].update(kw)


def _load(req):
    t0 = pd.Timestamp(req.start).tz_localize(req.tz) - pd.Timedelta(days=req.history_days)
    t1 = pd.Timestamp(req.end).tz_localize(req.tz) + pd.Timedelta(days=1)
    return _load_range(req.site, t0, t1)


def _load_range(site, t0, t1, meters_until=None):
    """Meters on [t0, meters_until or t1), weather on [t0, t1); hourly UTC index."""
    m1 = meters_until if meters_until is not None else t1
    rng_m = f"time >= '{t0.tz_convert('UTC'):%Y-%m-%dT%H:%M:%SZ}' AND time < '{m1.tz_convert('UTC'):%Y-%m-%dT%H:%M:%SZ}'"
    rng = f"time >= '{t0.tz_convert('UTC'):%Y-%m-%dT%H:%M:%SZ}' AND time < '{t1.tz_convert('UTC'):%Y-%m-%dT%H:%M:%SZ}'"
    site = site.replace("'", "")
    meters = INFLUX.query(f"SELECT kw FROM meter WHERE site='{site}' AND {rng_m} GROUP BY home")
    if not meters:
        raise ValueError(f"no meter data for site '{site}' in {t0.date()}..{t1.date()}")
    W = pd.concat({t["home"]: df["kw"] for t, df in meters}, axis=1).sort_index()
    W = W.reindex(pd.date_range(W.index.min(), m1.tz_convert("UTC"), freq="1h", inclusive="left"))
    wx = INFLUX.query(f"SELECT {','.join(WEATHER_COLS)} FROM weather WHERE site='{site}' AND {rng}")
    if not wx:
        raise ValueError(f"no weather data for site '{site}'")
    widx = pd.date_range(W.index.min(), t1.tz_convert("UTC"), freq="1h", inclusive="left")
    w = wx[0][1].reindex(columns=WEATHER_COLS).reindex(widx).astype(float)
    w["temp"] = w["temp"].interpolate(limit=3)
    return W, w


def _outputs(res, tz):
    R, D, F = res["baseline"], res["decomposition"], res["flexibility"]
    out = pd.DataFrame(index=R.index)
    out["load_kw"], out["forecast_kw"] = R["actual"], R["q0.5"]
    out["forecast_lo_kw"], out["forecast_hi_kw"] = R["cal_lo"], R["cal_hi"]
    for c, n in [("base", "base_kw"), ("routine", "routine_kw"), ("thermal", "thermal_kw"), ("shiftable", "appliances_kw"), ("ev", "ev_kw")]:
        out[n] = D[c].reindex(out.index)
    h = out.index.tz_convert(tz).hour
    out["down_kw_avgday"] = F["down_kw"].reindex(h).values
    out["up_kw_avgday"] = F["up_kw"].reindex(h).values
    out.index = out.index.tz_convert("UTC")
    env = F.copy()
    env.index = pd.to_datetime(env.index, unit="h", utc=True)
    return out, env


def _run(jid, req):
    try:
        _set(jid, status="loading data")
        W, w = _load(req)
        _set(jid, status="running method", homes=list(W.columns), hours=len(W))
        cfg = Config(tz=req.tz)
        days = pd.date_range(req.start, req.end, freq="D", tz=cfg.tz)
        res = pipeline.run(W, w, cfg, days, participation=req.participation, response=req.response)
        out, env = _outputs(res, req.tz)
        out["temp_c"] = w["temp"].reindex(out.index)
        n = 0
        if req.write:
            _set(jid, status="writing results")
            n = INFLUX.write(to_lines("substation", out, {"site": req.site}) + to_lines("envelope", env, {"site": req.site}))
        R = res["baseline"].dropna(subset=["cal_lo"])
        cov = float(((R["actual"] >= R["cal_lo"]) & (R["actual"] <= R["cal_hi"])).mean()) if len(R) else None
        F = res["flexibility_participation"]
        _set(jid, status="done", finished=datetime.now(timezone.utc).isoformat(), points_written=n,
             band_coverage=None if cov is None else round(cov, 3),
             envelope=[{"hour": int(h), **{k: round(float(v), 3) for k, v in r.items()}} for h, r in F.iterrows()])
    except Exception as e:
        _set(jid, status="failed", error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])


class DayAheadRequest(BaseModel):
    site: str = Field(..., examples=["refit"])
    day: Optional[str] = Field(None, description="target day (local date); default = last complete day of meter data",
                               examples=["2015-01-26"])
    history_days: int = Field(120, ge=35, description="days of meter data before the target day used for training")
    envelope_days: int = Field(35, ge=14, description="recent days whose average day gives the envelope")
    tz: str = "Europe/London"
    participation: Optional[float] = Field(None, ge=0, le=1, description="enrolment x response; omit for technical maximum")
    evaluate_with: Optional[str] = Field(None, description="research dataset with sub-metering to compare against "
                                         "(e.g. 'refit'); evaluation only, never used for the prediction", examples=["refit"])
    write: bool = True


def _last_complete_day(site, tz):
    homes = INFLUX.query(f"SELECT last(kw) FROM meter WHERE site='{site.replace(chr(39), '')}' GROUP BY home")
    if not homes:
        raise ValueError(f"no meter data for site '{site}'")
    last = min(df.index.max() for _, df in homes)                 # every home must have reached that day
    d = last.tz_convert(tz).normalize()
    return d if last.tz_convert(tz) >= d + pd.Timedelta(hours=23) else d - pd.Timedelta(days=1)


def _run_dayahead(jid, req):
    try:
        _set(jid, status="loading data")
        d0 = (pd.Timestamp(req.day).tz_localize(req.tz) if req.day else _last_complete_day(req.site, req.tz))
        d1 = d0 + pd.Timedelta(days=1)
        W, w = _load_range(req.site, d0 - pd.Timedelta(days=req.history_days), d1, meters_until=d0)
        _set(jid, status="running method", homes=list(W.columns))
        out, info = DA.run(W, w, Config(tz=req.tz), d0.tz_localize(None), req.envelope_days, req.participation,
                           truth_dataset=req.evaluate_with, data_dir=os.environ.get("DATA_DIR", "data"))
        # evaluation only, after the prediction: the real load of the target day if it is already in the database
        try:
            Wd, _ = _load_range(req.site, d0, d1)
            out["actual_kw"] = Wd.reindex(columns=W.columns).sum(axis=1, min_count=W.shape[1]).reindex(out.index)
        except ValueError:
            pass
        out["temp_c"] = w["temp"].reindex(out.index)
        n = INFLUX.write(to_lines("dayahead", out, {"site": req.site})) if req.write else 0
        rows = out.copy(); rows.index = rows.index.tz_convert(req.tz).strftime("%Y-%m-%d %H:%M")
        _set(jid, status="done", finished=datetime.now(timezone.utc).isoformat(), points_written=n, **info,
             hours=[{"time": t, **{k: (None if pd.isna(v) else round(float(v), 3)) for k, v in r.items()}} for t, r in rows.iterrows()])
    except Exception as e:
        _set(jid, status="failed", error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])


@app.post("/dayahead", status_code=202)
def create_dayahead(req: DayAheadRequest):
    jid = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[jid] = dict(id=jid, kind="dayahead", status="queued", request=req.model_dump(), created=datetime.now(timezone.utc).isoformat())
    _pool.submit(_run_dayahead, jid, req)
    return {"id": jid, "status": "queued"}


@app.get("/dayahead/{jid}")
def get_dayahead(jid: str):
    return get(jid)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/envelope", status_code=202)
def create(req: EnvelopeRequest):
    jid = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[jid] = dict(id=jid, status="queued", request=req.model_dump(), created=datetime.now(timezone.utc).isoformat())
    _pool.submit(_run, jid, req)
    return {"id": jid, "status": "queued"}


@app.get("/envelope")
def list_jobs():
    with _lock:
        return [{k: j.get(k) for k in ("id", "status", "created", "finished")} for j in _jobs.values()]


@app.get("/envelope/{jid}")
def get(jid: str):
    with _lock:
        if jid not in _jobs:
            raise HTTPException(404, "unknown job id")
        return _jobs[jid]


@app.delete("/envelope/{jid}")
def delete(jid: str):
    with _lock:
        if _jobs.pop(jid, None) is None:
            raise HTTPException(404, "unknown job id")
    return {"deleted": jid}
