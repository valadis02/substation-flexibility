"""Store an Open-Meteo archive CSV as data/processed/<dataset>/weather.csv.gz (hourly, UTC), next to the load data.

Download the CSV in a browser (the URL for each dataset is in data/README.md), then:
    python scripts/add_weather.py refit  C:\\Users\\...\\open-meteo-refit.csv
"""
import os, sys
import pandas as pd
from flexsub.data import load_openmeteo_csv, load_processed

name, path = sys.argv[1], sys.argv[2]
out = os.path.join(os.path.dirname(__file__), "..", "data", "processed", name)
W = load_processed(out)["W"]
w = load_openmeteo_csv(path, W.index)
print(w.describe().T[["count", "mean", "min", "max"]].round(2))
assert w["temp"].notna().mean() > 0.95, "weather does not cover the load period: check dates/timezone=GMT in the URL"
w.round(3).to_csv(os.path.join(out, "weather.csv.gz"), index_label="timestamp")
print("written", os.path.abspath(os.path.join(out, "weather.csv.gz")))
