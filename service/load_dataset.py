"""Load a prepared dataset (data/processed/<name>) into InfluxDB as SOGNO-style measurements for the service.

Development data only: held-out homes are skipped and each home is cut at its locked-test time (data/splits.json).
  python load_dataset.py plegma --site plegma-dev --from 2023-04-01
"""
import argparse, json, os
import pandas as pd
from flexsub.data import load_processed
from influx import Influx, to_lines

ap = argparse.ArgumentParser()
ap.add_argument("dataset"); ap.add_argument("--site", required=True)
ap.add_argument("--from", dest="start", default=None, help="first date to load (UTC)")
ap.add_argument("--data-dir", default=os.environ.get("DATA_DIR", "data"))
a = ap.parse_args()

influx = Influx(os.environ.get("INFLUX_URL", "http://influxdb.sogno:8086"), os.environ.get("INFLUX_DB", "openaiflex"))
d = load_processed(os.path.join(a.data_dir, "processed", a.dataset))
split = json.load(open(os.path.join(a.data_dir, "splits.json")))["datasets"].get(a.dataset, {})
skip = set(split.get("held_out_homes", [])) | set(split.get("excluded", []))
lines = []
for home in d["W"].columns:
    if home in skip:
        continue
    s = d["W"][home]
    cut = split.get("time_cut", {}).get(home)
    if cut:
        s = s[s.index < pd.Timestamp(cut)]
    if a.start:
        s = s[s.index >= pd.Timestamp(a.start, tz="UTC")]
    lines += to_lines("meter", s.dropna().to_frame("kw"), {"site": a.site, "home": home})
w = d["weather"]
if a.start:
    w = w[w.index >= pd.Timestamp(a.start, tz="UTC")]
lines += to_lines("weather", w[["temp", "rh", "cloud", "rad", "is_day"]], {"site": a.site})
print(f"homes skipped (locked test): {sorted(skip)}")
print(f"wrote {influx.write(lines)} points to site '{a.site}'")
