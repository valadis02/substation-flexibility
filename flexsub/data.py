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


def _read_plegma_month(path, cols=None):
    df = pd.read_csv(path, usecols=cols, low_memory=False)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df.dropna(subset=["timestamp"]).set_index("timestamp")


def load_plegma(root, tz="Europe/Athens", min_coverage=0.8):
    """Plegma (Greece, 13 homes, 10 s). `root` = folder `Clean_Dataset`.

    Returns dict:
      W          hourly kW whole-house (P_agg), index tz-aware UTC, columns = house ids
      appliances {house_id: hourly kW DataFrame of the monitored appliances}
      weather    hourly DataFrame(temp, rh, cloud, rad, is_day); temp/rh = median of the homes' external sensors,
                 cloud and rad are NaN (not measured in Plegma). Replace with Open-Meteo if needed.
    An hour is kept only if >= `min_coverage` of its 10-s samples exist (the cleaned data leave gaps > 30 s as NaN).
    """
    import os
    W, apps, wx = {}, {}, []
    for h in sorted(os.listdir(root)):
        hdir = os.path.join(root, h)
        if not os.path.isdir(hdir):
            continue
        hid = h.replace("House_", "H")
        files = sorted(glob.glob(os.path.join(hdir, "Electric_data", "20??-??.csv")))
        parts = [_read_plegma_month(f) for f in files]
        e = pd.concat(parts).sort_index()
        e = e[~e.index.duplicated()]
        keep = [c for c in e.columns if c not in ("V", "A", "issues", "Issues")]
        e = e[keep].apply(pd.to_numeric, errors="coerce")
        e.index = e.index.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
        e = e[e.index.notna()].tz_convert("UTC")
        hr = e.resample("1h").mean() / 1000.0
        cnt = e.notna().resample("1h").mean()
        hr = hr.where(cnt >= min_coverage)
        W[hid] = hr["P_agg"]
        apps[hid] = hr.drop(columns="P_agg")
        envf = sorted(glob.glob(os.path.join(hdir, "Environmental_data", "20??-??.csv")))
        if envf:
            ev = pd.concat([_read_plegma_month(f) for f in envf]).sort_index()
            ev = ev[~ev.index.duplicated()]
            tcol = [c for c in ev.columns if c.startswith("external_temp")]
            hcol = [c for c in ev.columns if c.startswith("external_hum")]
            ev.index = ev.index.tz_localize(tz, ambiguous="NaT", nonexistent="shift_forward")
            ev = ev[ev.index.notna()].tz_convert("UTC")
            wx.append(pd.DataFrame({"temp": pd.to_numeric(ev[tcol[0]], errors="coerce"),
                                    "rh": pd.to_numeric(ev[hcol[0]], errors="coerce")}).resample("1h").mean())
    W = pd.DataFrame(W)
    wxm = pd.concat(wx, keys=range(len(wx))).groupby(level=1).median().reindex(W.index)
    wxm["cloud"] = float("nan"); wxm["rad"] = float("nan")
    # crude day flag (06-20 local); Plegma has no sun data
    loc = W.index.tz_convert(tz)
    wxm["is_day"] = ((loc.hour >= 6) & (loc.hour < 20)).astype(int)
    return dict(W=W, appliances=apps, weather=wxm[["temp", "rh", "cloud", "rad", "is_day"]])


# ---- adapters for public datasets with ground truth (to be implemented when data is obtained; see docs/test_plan.pdf)
def load_pecan_street(path):  # pragma: no cover
    raise NotImplementedError("Needs Dataport access. Expected output: hourly kW per home + per-circuit ground truth (HVAC, EV, water heater, ...)")


def load_refit(path, houses=None, min_rows_per_hour=250, chunksize=2_000_000):
    """REFIT cleaned (CLEAN_REFIT_081116): 20 homes, ~8 s, mains + 9 appliance monitors.

    `path` = folder with CLEAN_House<N>.csv. Returns dict:
      W          hourly kW mains, index UTC, columns = 'H<N>'
      appliances {'H<N>': hourly kW DataFrame, columns named from appliances.REFIT_APPLIANCES}
      meta       {'H<N>': {'pv': bool}}  (houses 11 and 21: mains affected by solar panels)
    Data are forward-filled by the dataset authors (gaps > 2 min filled with 0), so a 0 is not always a real 0.
    Hours with fewer than `min_rows_per_hour` rows are dropped.
    """
    import os
    from .appliances import REFIT_APPLIANCES, REFIT_PV_HOUSES
    houses = houses or sorted(REFIT_APPLIANCES)
    W, apps, meta = {}, {}, {}
    for h in houses:
        f = os.path.join(path, f"CLEAN_House{h}.csv")
        names = REFIT_APPLIANCES[h]
        sums, cnts = [], []
        for ch in pd.read_csv(f, usecols=["Unix", "Aggregate"] + [f"Appliance{i}" for i in range(1, 10)], chunksize=chunksize):
            ch.index = pd.to_datetime(ch["Unix"], unit="s", utc=True)
            ch = ch.drop(columns="Unix")
            g = ch.resample("1h")
            sums.append(g.sum()); cnts.append(g.size())
        s = pd.concat(sums).groupby(level=0).sum()
        c = pd.concat(cnts).groupby(level=0).sum()
        hourly = s.div(c, axis=0) / 1000.0
        hourly = hourly[c >= min_rows_per_hour]
        hourly = hourly.rename(columns={f"Appliance{i+1}": names[i] for i in range(9)})
        hid = f"H{h}"
        W[hid] = hourly["Aggregate"]
        apps[hid] = hourly.drop(columns="Aggregate")
        meta[hid] = {"pv": h in REFIT_PV_HOUSES}
    return dict(W=pd.DataFrame(W), appliances=apps, meta=meta)


def _hourly_from_hdf(store, key, chunk=4_000_000, min_rows_per_hour=300):
    sums, cnts, start = [], [], 0
    while True:
        try:
            ch = pd.read_hdf(store, key=key, start=start, stop=start + chunk)
        except (IndexError, KeyError):
            break
        if len(ch) == 0:
            break
        s = ch.iloc[:, 0].astype(float)
        g = s.resample("1h")
        sums.append(g.sum()); cnts.append(g.count())
        start += chunk
        if len(ch) < chunk:
            break
    S = pd.concat(sums).groupby(level=0).sum(); C = pd.concat(cnts).groupby(level=0).sum()
    return (S / C / 1000.0)[C >= min_rows_per_hour]


def load_ukdale(path, buildings=(1, 2, 3, 4, 5)):
    """UK-DALE in NILMTK HDF5 (ukdale.h5): meter1 = mains of each building, meterN = channel N (names from appliances.UKDALE_CHANNELS).

    Only appliances useful for flexibility are loaded (washing machine, dishwasher, washer dryer, electric heater, fridge).
    The mains of building 1 are apparent power (VA), the appliances are active power; treat the mains as approximate.
    Returns dict(W, appliances) like load_refit (columns 'B<n>'). UK-DALE has no AC, EV or heat pump.
    """
    from .appliances import UKDALE_CHANNELS
    W, apps = {}, {}
    for b in buildings:
        bid = f"B{b}"
        W[bid] = _hourly_from_hdf(path, f"/building{b}/elec/meter1")
        apps[bid] = pd.DataFrame({name: _hourly_from_hdf(path, f"/building{b}/elec/meter{ch}")
                                  for ch, name in UKDALE_CHANNELS[b].items()})
    return dict(W=pd.DataFrame(W), appliances=apps)




# ---- processed hourly data (committed in data/processed/<dataset>/) ----
def save_processed(d, out_dir):
    """Write a loader's output (dict W, appliances, optional weather) as gzipped hourly CSVs (kW, UTC)."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    d["W"].round(5).to_csv(os.path.join(out_dir, "mains.csv.gz"), index_label="timestamp")
    for h, A in d["appliances"].items():
        A.round(5).to_csv(os.path.join(out_dir, f"appliances_{h}.csv.gz"), index_label="timestamp")
    if d.get("weather") is not None:
        d["weather"].round(3).to_csv(os.path.join(out_dir, "weather.csv.gz"), index_label="timestamp")


def load_processed(dataset_dir):
    """Read what save_processed wrote. Returns dict(W, appliances, weather or None)."""
    import os
    rd = lambda f: pd.read_csv(f, index_col="timestamp", parse_dates=["timestamp"])
    W = rd(os.path.join(dataset_dir, "mains.csv.gz"))
    apps = {os.path.basename(f)[len("appliances_"):-len(".csv.gz")]: rd(f)
            for f in sorted(glob.glob(os.path.join(dataset_dir, "appliances_*.csv.gz")))}
    wf = os.path.join(dataset_dir, "weather.csv.gz")
    return dict(W=W, appliances=apps, weather=rd(wf) if os.path.exists(wf) else None)
