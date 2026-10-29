"""T9: EV charging and water heaters as flexible load (v0.9 candidates), development data only.

Question: v0.8 counts as flexible only weather-dependent load and short appliance cycles (<= 3 h). EV charging
(long runs) and water heaters are missed. Does a separate long-run (EV) detector recover them without creating
false flexible load in homes that have no EV?

Groups: ALL development homes with a weather series that are present together (EV homes included, unlike T8):
Pecan Austin, Pecan New York, REFIT, Plegma. Truth: weather = AC/furnace/heaters; shiftable = wet appliances +
electric water heaters; ev = car circuits; flexible = all three.

Variants (per home, after removing the home's own weather load as in v0.8):
  v08   short events only (current method)
  long  v08 + every run > 3 h above the same 3-sigma threshold counted as EV / long flexible load
  ev_k  v08 + EV detector: hours with excess over the same-hour 14-day reference > k kW (k = physical, level-1/2
        charger), any run length, run extended by adjacent hours > k/2 (partial first/last hour); EV hours are removed
        from the short events. Optional home gate: the home must show such hours on >= g of hours.

    python experiments/t9_ev.py            (first run caches the weather parts in outputs/t9/)
"""
import os, sys, pickle
import numpy as np
import pandas as pd
from flexsub import Config, splits
from flexsub.appliances import category
from flexsub.data import load_processed
from flexsub.decompose import _home_weather_load, house_parts
from flexsub.thermal import thermal_dd_loo
from flexsub import shiftable

DS = {"pecan_austin": ("America/Chicago", 30.27), "pecan_newyork": ("America/New_York", 42.44),
      "refit": ("Europe/London", 52.77), "plegma": ("Europe/Athens", 37.98)}
THERMAL = lambda c, ds: category(c, ds) == "thermal" or c in ("ac", "furnace", "heater") or c.startswith("ac_")
os.makedirs("outputs/t9", exist_ok=True)
CACHE = "outputs/t9/cache_v2.pkl"     # v2: P950 excluded, heat-pump water heaters separate


def build_cache():
    C = {}
    for ds, (tz, lat) in DS.items():
        cfg = Config(tz=tz, latitude=lat)
        d = load_processed(os.path.join("data", "processed", ds))
        if d["weather"] is None:
            continue
        W = splits.development(d["W"], ds)
        homes, T = [], {}
        for h in W.columns:
            Ap = d["appliances"][h].reindex(W.index)
            sh = [c for c in Ap.columns if category(c, ds) == "shiftable"]
            if not sh:
                continue
            # heat-pump water heaters (~0.4 kW when on) are their own category, not shiftable appliances (T9b);
            # a water-heater circuit is a heat pump if it draws < 1.5 kW when on (resistive elements: 1.2-4.5 kW, but
            # Greek 1.2 kW resistive heaters are in Plegma, where all are resistive)
            hp = [c for c in sh if "waterheater" in c and ds.startswith("pecan") and Ap[c][Ap[c] > 0.2].median() < 1.5]
            sh = [c for c in sh if c not in hp]
            z = 0 * W[h]
            th = [c for c in Ap.columns if THERMAL(c, ds)]
            ev = [c for c in Ap.columns if category(c, ds) == "ev"]
            T[h] = pd.DataFrame({"shiftable": Ap[sh].sum(axis=1, min_count=len(sh)),
                                 "hp_water_heater": Ap[hp].sum(axis=1) if hp else z,
                                 "weather": Ap[th].sum(axis=1) if th else z, "ev": Ap[ev].sum(axis=1) if ev else z})
            homes.append(h)
        # largest set of homes present together on >= 60 days
        ok = W[homes].notna().all(axis=1) & pd.concat([T[h]["shiftable"].notna() for h in homes], axis=1).all(axis=1)
        while ok.sum() < 24 * 60 and len(homes) > 2:
            cov = {h: W[h].notna().mean() for h in homes}
            homes.remove(min(cov, key=cov.get))
            ok = W[homes].notna().all(axis=1) & pd.concat([T[h]["shiftable"].notna() for h in homes], axis=1).all(axis=1)
        idx = W.index[ok]
        Wg, w = W.loc[idx, homes], d["weather"].reindex(idx)
        y = Wg.sum(axis=1)
        days = [pd.Timestamp(x).tz_convert("UTC") for x in pd.Index(idx.tz_convert(tz).normalize().unique())]
        th_est = thermal_dd_loo(y, w, days, cfg)
        hw = {h: _home_weather_load(Wg[h], w, tz) for h in homes}
        C[ds] = dict(cfg=cfg, W=Wg, w=w, thermal=th_est, home_weather=hw, truth={h: T[h].reindex(idx) for h in homes})
        print(ds, len(homes), "homes", int(ok.sum() / 24), "days,", sum(T[h]["ev"].mean() > 0.05 for h in homes), "EV homes", flush=True)
    pickle.dump(C, open(CACHE, "wb"))
    return C


def ev_detect(y, k, window_days=14, q=0.6, gate=0.0):
    """EV-like hours: excess over the same-hour reference > k kW (any run length), extended to adjacent hours > k/2."""
    ref = y.groupby(y.index.hour).transform(lambda s: s.rolling(window_days, min_periods=7).quantile(q).shift(1))
    exc = (y - ref)
    core = (exc > k) & ref.notna()
    ext = core | ((exc > k / 2) & (core.shift(1, fill_value=False) | core.shift(-1, fill_value=False)))
    if gate > 0 and core.mean() < gate:
        ext[:] = False
    return exc.clip(lower=0).where(ext, 0.0).where(ref.notna()), ext


def run_variant(D, name):
    cfg, Wg, w, tz = D["cfg"], D["W"], D["w"], D["cfg"].tz
    sh_sum, ev_sum, base_sum = 0, 0, 0
    for h in Wg.columns:
        s = Wg[h]
        yw = s - D["home_weather"][h].reindex(s.index).fillna(0)
        loc = s.index.tz_convert(tz)
        low = s.groupby(loc.hour).mean().nsmallest(cfg.base_hours).index
        night = s[np.isin(loc.hour, low)]
        bd = night.groupby(night.index.tz_convert(tz).normalize()).quantile(cfg.base_quantile).rolling(cfg.base_roll_days, min_periods=3).median()
        base = np.minimum(pd.Series(bd.reindex(loc.normalize()).values, index=s.index).bfill(), s)
        ev = 0 * s
        if name == "long":
            short = shiftable.events_home(s, weather_load=D["home_weather"][h])
            allr = shiftable.events_home(s, weather_load=D["home_weather"][h], max_run_h=10_000)
            ev = (allr - short).clip(lower=0)
        elif name.startswith("ev_"):
            _, k, g = name.split("_")
            ev, mask = ev_detect(yw, float(k), gate=float(g))
            short = shiftable.events_home(s.where(~mask, np.nan).fillna(yw.where(~mask)).fillna(s), weather_load=D["home_weather"][h])
            short = short.where(~mask, 0.0)
        else:
            short = shiftable.events_home(s, weather_load=D["home_weather"][h])
        sh_sum = sh_sum + short.fillna(0); ev_sum = ev_sum + ev.fillna(0); base_sum = base_sum + base
    y = Wg.sum(axis=1)
    th = D["thermal"].reindex(y.index)
    ok = th.notna()
    out, rem = pd.DataFrame(index=y.index[ok]), y[ok].copy()
    for nm, v in (("base", base_sum[ok]), ("weather", th[ok]), ("ev", ev_sum[ok]), ("shiftable", sh_sum[ok])):
        a = np.minimum(v.clip(lower=0), rem); out[nm] = a; rem = rem - a
    out["actual"] = y[ok]
    return out


def score(D, est, ds, variant):
    tru = sum(D["truth"][h] for h in D["W"].columns).reindex(est.index)
    y = est["actual"]
    m30 = y.rolling(24 * 30, min_periods=24 * 7, center=True).mean()
    est = est.assign(flexible=est.weather + est.ev + est.shiftable)
    tru = tru.assign(flexible=tru.weather + tru.ev + tru.shiftable)
    rows = []
    for p in ("flexible", "ev", "shiftable"):
        e = ((est[p] - tru[p]).abs() / m30).dropna()
        rows.append(dict(dataset=ds, variant=variant, part=p, awfe_p90=float(e.quantile(0.9)),
                         zero_p90=float((tru[p].abs() / m30).dropna().quantile(0.9)),
                         energy_ratio=float(est[p].sum() / tru[p].sum()) if tru[p].sum() > 0 else np.nan,
                         est_kwh_day=float(est[p].mean() * 24), true_kwh_day=float(tru[p].mean() * 24),
                         corr=float(np.corrcoef(est[p], tru[p])[0, 1]) if tru[p].std() > 0 and est[p].std() > 0 else np.nan))
    return rows


if __name__ == "__main__":
    C = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else build_cache()
    variants = sys.argv[1:] or ["v08", "long", "ev_1.5_0", "ev_2.5_0", "ev_1.5_0.02", "ev_2.5_0.02"]
    R = []
    for ds, D in C.items():
        for v in variants:
            R += score(D, run_variant(D, v), ds, v)
            print(ds, v, flush=True)
    R = pd.DataFrame(R)
    R.to_csv("outputs/t9/variants.csv", index=False)
    print(R.round(3).to_string())
