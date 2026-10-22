"""Convert raw public datasets to hourly kW in data/processed/<dataset>/ (gzipped CSV, UTC).

Run once per dataset on the machine that has the raw files, then commit data/processed/.
    python scripts/prepare_data.py plegma  C:\\path\\to\\Clean_Dataset
    python scripts/prepare_data.py refit   C:\\path\\to\\CLEAN_REFIT_081116
    python scripts/prepare_data.py ukdale  C:\\path\\to\\ukdale.h5
Licences: Plegma, REFIT and UK-DALE are CC BY 4.0 (cite them; see data/README.md).
"""
import sys, os, time
from flexsub import data

name, path = sys.argv[1], sys.argv[2]
loader = {"plegma": data.load_plegma, "refit": data.load_refit, "ukdale": data.load_ukdale}[name]
t = time.time()
d = loader(path)
out = os.path.join(os.path.dirname(__file__), "..", "data", "processed", name)
data.save_processed(d, out)
W = d["W"]
print(f"{name}: {W.shape[1]} homes, {W.index.min()} .. {W.index.max()}, {time.time() - t:.0f} s")
print("hours with data per home:")
print(W.notna().sum().to_string())
size = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
print(f"written to {os.path.abspath(out)} ({size / 1e6:.1f} MB)")
