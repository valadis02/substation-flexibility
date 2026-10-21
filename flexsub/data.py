"""Loading and harmonising data. Everything is converted to hourly kW on a tz-aware index.

No raw data is stored in the repository (see data/README.md).
"""
import glob
import pandas as pd


def load_long_csv(pattern, ts_col="timestamp", house_col="house_id", value_col="consumption", divisor=1000.0):
    """Long-format CSVs (timestamp, house_id, consumption[W]) -> hourly kW DataFrame (index UTC, columns = house ids)."""
    df = pd.concat([pd.read_csv(f) for f in glob.glob(pattern)])
    df[ts_col] = pd.to_datetime(df[ts_col], utc=True)
    W = df.pivot_table(index=ts_col, columns=house_col, values=value_col, aggfunc="mean")
    return W.sort_index().interpolate(limit_direction="both") / divisor


def to_hourly_kw(df, freq_minutes=None, unit="W"):
    """Resample a high-resolution wide DataFrame (index = timestamps, columns = houses) to hourly mean kW."""
    out = df.resample("1h").mean()
    return out / 1000.0 if unit == "W" else out


def load_openmeteo_csv(path, index):
    """Open-Meteo archive CSV (3 header lines; time, temp, rh, cloud, shortwave radiation, is_day) reindexed to `index` (UTC)."""
    w = pd.read_csv(path, skiprows=3)
    w.columns = ["time", "temp", "rh", "cloud", "rad", "is_day"]
    w.index = pd.to_datetime(w["time"]).dt.tz_localize("UTC")
    return w.drop(columns="time").reindex(index)


# ---- adapters for public datasets with ground truth (to be implemented when data is obtained; see docs/test_plan.pdf)
def load_pecan_street(path):  # pragma: no cover
    raise NotImplementedError("Needs Dataport access. Expected output: hourly kW per home + per-circuit ground truth (HVAC, EV, water heater, ...)")


def load_refit(path):  # pragma: no cover
    raise NotImplementedError("REFIT: mains + per-appliance at 7 s -> hourly kW + appliance ground truth")


def load_ukdale(path):  # pragma: no cover
    raise NotImplementedError("UK-DALE: mains + per-appliance -> hourly kW + appliance ground truth")
