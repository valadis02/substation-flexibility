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
a = ap.parse_args()
cfg = Config(tz=a.tz)
W = load_long_csv(a.data)
w = load_openmeteo_csv(a.weather, W.index)
days = pd.date_range(a.start, a.end, freq="D", tz=cfg.tz)
res = pipeline.run(W, w, cfg, days)
os.makedirs(a.out, exist_ok=True)
for k, v in res.items():
    v.to_csv(os.path.join(a.out, f"{k}.csv"))
print(res["flexibility"].round(2))
