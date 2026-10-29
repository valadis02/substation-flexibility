"""Run the full method on a dataset.

Example (long-format CSVs with timestamp, house_id, consumption[W]; Open-Meteo archive CSV):
    python scripts/run_pipeline.py --data "data/raw/*.csv" --weather data/weather.csv --start 2026-09-20 --end 2026-10-15 --out outputs/run1
"""
import argparse, os
import pandas as pd
from flexsub import Config, pipeline
from flexsub.data import load_long_csv, load_openmeteo_csv

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True); ap.add_argument("--weather", required=True)
ap.add_argument("--start", required=True); ap.add_argument("--end", required=True); ap.add_argument("--out", default="outputs/run")
ap.add_argument("--tz", default="Europe/Athens")
ap.add_argument("--participation", type=float, default=None, help="known enrolment share of this substation (0-1); omit for maximum + scenarios")
ap.add_argument("--response", type=float, default=1.0, help="share of enrolled homes that respond to an event (0-1)")
a = ap.parse_args()
cfg = Config(tz=a.tz)
W = load_long_csv(a.data)
w = load_openmeteo_csv(a.weather, W.index)
days = pd.date_range(a.start, a.end, freq="D", tz=cfg.tz)
res = pipeline.run(W, w, cfg, days, participation=a.participation, response=a.response)
os.makedirs(a.out, exist_ok=True)
for k, v in res.items():
    if isinstance(v, dict):   # participation scenarios
        for (e, r), df in v.items():
            df.to_csv(os.path.join(a.out, f"{k}_enrol{e}_resp{r}.csv"))
    else:
        v.to_csv(os.path.join(a.out, f"{k}.csv"))
print(res["flexibility"].round(2))
