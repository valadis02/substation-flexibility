"""Day-ahead run for one substation: forecast band (M1) and flexibility envelope (M2-M5) for the target day,
from meter data strictly before that day and the weather of that day (in operation: a weather forecast).

  forecast  quantile models trained on all usable hours before the day; conformal widening from the scores of the
            previous cfg.calib_days days, each predicted day-ahead in the same way (as in flexsub.baseline)
  envelope  decomposition of the last `envelope_days` days before the day, kW down / up per hour of their average
            day (flexsub.flexibility), placed on the hours of the target day
"""
import numpy as np
import pandas as pd
from flexsub import baseline, decompose, features, flexibility, thermal


def run(W, w, cfg, day, envelope_days=35, participation=None, truth_dataset=None, data_dir=None):
    """W: hourly kW per home (UTC index) with no rows on or after `day`; w: weather on W's index + the target day.
    Returns (DataFrame on the 24 target hours, info dict)."""
    tz = cfg.tz
    d0 = pd.Timestamp(day).tz_localize(tz)
    d1 = d0 + pd.Timedelta(days=1)
    idx = pd.date_range(W.index.min(), d1.tz_convert("UTC"), freq="1h", inclusive="left")
    W = W.reindex(idx)
    W.loc[W.index >= d0] = np.nan                                  # nothing from the target day is used
    w = w.reindex(idx)
    y = W.sum(axis=1, min_count=W.shape[1])                       # substation load: hours with every home metered
    X = features.build(y, w, cfg)

    # M1: past days day-ahead (for conformal scores), then the target day
    past = [d0 - pd.Timedelta(days=k) for k in range(cfg.calib_days, 0, -1)]
    R = baseline.conformal_calibrate(baseline.rolling_origin(y, X, past, cfg), cfg)
    lo_q, mid_q, hi_q = cfg.quantiles
    s = np.maximum(R["raw_lo"] - R["actual"], R["actual"] - R["raw_hi"]).dropna()
    if len(s) < cfg.calib_min_samples:
        raise ValueError(f"not enough recent hours to calibrate the band ({len(s)} < {cfg.calib_min_samples})")
    cq = float(np.quantile(s, cfg.calib_quantile))
    tr = baseline.usable_rows(y, X) & (y.index < d0)
    te = (y.index >= d0) & (y.index < d1)
    cols = X.columns[X[tr].nunique() >= 2]
    pred = {q: baseline._fit(X.loc[tr, cols], y[tr], q, cfg).predict(X.loc[te, cols]) for q in cfg.quantiles}
    out = pd.DataFrame(index=y.index[te])
    lo, hi = np.minimum(pred[lo_q], pred[hi_q]), np.maximum(pred[lo_q], pred[hi_q])
    out["forecast_kw"], out["forecast_lo_kw"], out["forecast_hi_kw"] = pred[mid_q], lo - cq, hi + cq

    # M2-M5: envelope from the recent days
    hist = W.index < d0
    days = pd.date_range(d0 - pd.Timedelta(days=envelope_days), d0 - pd.Timedelta(days=1), freq="D")
    th = thermal.thermal_dd_loo(y[hist], w[hist], days, cfg)
    D = decompose.decompose_substation(W[hist], w[hist], th, cfg)
    D = D[D.index >= days[0]]
    F = flexibility.flexibility_by_hour(D, cfg)
    h = out.index.tz_convert(tz).hour
    ev_info = None
    if truth_dataset:                                              # evaluation only (sub-metered research data)
        from evaluate import truth, true_envelope
        tru = truth(truth_dataset, list(W.columns), idx, data_dir)
        Ft = true_envelope(D, tru, cfg)
        out["true_down_kw"], out["true_up_kw"] = Ft["down_kw"].reindex(h).values, Ft["up_kw"].reindex(h).values
        ev_info = dict(dataset=truth_dataset,
                       down_ratio=round(float(F.down_kw.sum() / Ft.down_kw.sum()), 3),
                       up_ratio=round(float(F.up_kw.sum() / Ft.up_kw.sum()), 3))
        out["realised_flexible_kw"] = (tru.weather + tru.ev + tru.shiftable).reindex(out.index)
    if participation is not None:
        F = flexibility.apply_participation(F, participation)
    for c in ("down_kw", "up_kw", "down_thermal_kw", "down_ev_kw", "up_ev_kw"):
        out[c] = F[c].reindex(h).values
    info = dict(target_day=str(d0.date()), homes=list(W.columns), train_hours=int(tr.sum()),
                band_widening_kw=round(cq, 3), envelope_days_used=int(D.index.tz_convert(tz).normalize().nunique()),
                recent_band_coverage=round(float(((R["actual"] >= R["cal_lo"]) & (R["actual"] <= R["cal_hi"]))[R["cal_lo"].notna()].mean()), 3)
                if R["cal_lo"].notna().any() else None)
    if ev_info:
        info["evaluation"] = ev_info
    return out, info
