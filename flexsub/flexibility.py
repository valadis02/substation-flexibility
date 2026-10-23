"""M4 + M5: directional flexibility per hour of day from the decomposition, with energy and power limits, then participation scaling."""
import numpy as np
import pandas as pd


def flexibility_by_hour(D, cfg):
    """D: decomposition (index tz-aware local or convertible). Returns per hour-of-day (mean day):
    down_kw (shiftable load running now), up_kw (energy movable in from +-window, capped by observed extra draw)."""
    D = D.copy()
    D.index = D.index.tz_convert(cfg.tz)
    h = D.index.hour
    g = D.groupby(h).mean()
    sh_series = D["thermal"] + D["shiftable"]           # M4 = weather-dependent + appliances; EV is M6 (flexsub.ev)
    sh = (g["thermal"] + g["shiftable"]).reindex(range(24)).fillna(0).values
    S, dur = cfg.shift_window_h, cfg.request_duration_h
    up_e = np.array([sum(sh[(x + k) % 24] for k in list(range(-S, 0)) + list(range(dur, dur + S))) / dur for x in range(24)])
    cap = (sh_series.groupby(h).quantile(cfg.cap_quantile) - sh_series.groupby(h).mean()).clip(lower=0).reindex(range(24)).fillna(0).values
    out = pd.DataFrame({"load_kw": g["actual"].reindex(range(24)).values, "down_kw": sh,
                        "down_thermal_kw": g["thermal"].reindex(range(24)).fillna(0).values,
                        "up_energy_kw": up_e, "up_cap_kw": cap, "up_kw": np.minimum(up_e, cap)}, index=range(24))
    out.index.name = "hour"
    return out


def apply_participation(F, p):
    G = F.copy()
    for c in ("down_kw", "down_thermal_kw", "up_energy_kw", "up_cap_kw", "up_kw"):
        G[c] = F[c] * p
    return G
