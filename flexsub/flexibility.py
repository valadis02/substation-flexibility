"""M5 + M6 (v0.10): one flexibility envelope per hour of day for all flexible categories, then participation.

M2 (weather), M3 (appliances, in the decomposition) and M4 (EV, flexsub.ev) estimate the flexible categories.
M5 turns each category into kW down and kW up per hour of an average day:
  weather + appliances (short cycles): Down(h) = mean flexible load at h; Up(h) = min(E, C), with E the flexible
      energy of the S hours before and after a d-hour block starting at h, and C the q90 extra draw seen at h and
      its two neighbouring hours (pooled, v0.11: T14).
  EV (sessions with a plug-in window, flexsub.ev): every session of the period is a scenario of weight 1/days, at its
      own clock hour, plugged for max(dwell_h, its length) hours; Down = charging that has room later in its window,
      Up = plugged cars not charging at that hour that still have energy to deliver (flexsub.ev.envelope, folded
      onto the 24 hours of the day). ev_rule="same" uses the short-cycle rule for EV too (tested in T12, not default).
M6 multiplies every column by the participation factor (enrolment x response), EV included.
"""
import numpy as np
import pandas as pd
from . import ev as m6

SCALED = ("down_kw", "down_thermal_kw", "down_ev_kw", "up_energy_kw", "up_cap_kw", "up_nonev_kw", "up_ev_kw", "up_kw")


def _short_cycle(D, cols, cfg):
    """Down, Up energy, Up cap per hour of day for the sum of `cols` (short-cycle rule)."""
    h = D.index.hour
    f = D[list(cols)].sum(axis=1)
    sh = f.groupby(h).mean().reindex(range(24)).fillna(0).values
    S, dur = cfg.shift_window_h, cfg.request_duration_h
    up_e = np.array([sum(sh[(x + k) % 24] for k in list(range(-S, 0)) + list(range(dur, dur + S))) / dur for x in range(24)])
    # cap per hour: extra draw (q - mean) of the flexible load, pooled over the hour and its two neighbours, so that one
    # day more or less in the window does not move it much (v0.11; per-hour q90 from ~35 values was noisy)
    hv = np.asarray(h)
    cap = np.zeros(24)
    for x in range(24):
        v = f.values[np.isin(hv, [(x - 1) % 24, x, (x + 1) % 24])]
        v = v[~np.isnan(v)]
        if len(v):
            cap[x] = max(np.quantile(v, cfg.cap_quantile) - v.mean(), 0.0)
    return sh, up_e, cap


def ev_mean_day(S_by_home, index, cfg):
    """EV down/up per hour of an average day from all sessions inside `index` (weight 1 / number of days)."""
    days = max(1, index.normalize().nunique())
    t0, t1 = index.min(), index.max()
    rows = []
    for h, S in S_by_home.items():
        for r in S[(S.start >= t0) & (S.start <= t1)].itertuples():
            st = int(r.start.hour)
            rows.append(dict(home=h, p=1.0 / days, start_hour=st, win_end=st + max(int(cfg.ev_dwell_h), int(r.hours)),
                             energy_kwh=float(r.energy_kwh), power_kw=float(max(r.power_kw, 1e-3))))
    T = pd.DataFrame(rows, columns=["home", "p", "start_hour", "win_end", "energy_kwh", "power_kw"])
    horizon = 24 + max(cfg.ev_dwell_h, 24) + 1
    E = m6.envelope(T, horizon=horizon)
    E = E.groupby(E.index % 24).sum().reindex(range(24)).fillna(0)
    return E


def flexibility_by_hour(D, cfg, ev_rule="sessions"):
    """D: decomposition (M3, EV from M4) with columns actual, base, thermal, ev, shiftable, routine; D.attrs["ev_sessions"] holds
    the EV sessions per home (set by decompose_substation). Returns per hour of the average day: down_kw and up_kw
    (all flexible categories), their weather / EV parts, and the short-cycle energy and cap terms."""
    D = D.copy()
    D.index = D.index.tz_convert(cfg.tz)
    g = D.groupby(D.index.hour).mean()
    if ev_rule == "same":
        down, up_e, cap = _short_cycle(D, ("thermal", "shiftable", "ev"), cfg)
        up_nonev = np.minimum(up_e, cap)
        down_ev = g["ev"].reindex(range(24)).fillna(0).values
        up_ev = np.zeros(24)
        up = up_nonev
    else:
        down_ne, up_e, cap = _short_cycle(D, ("thermal", "shiftable"), cfg)
        up_nonev = np.minimum(up_e, cap)
        S = D.attrs.get("ev_sessions") or {}
        E = ev_mean_day(S, D.index, cfg) if S else pd.DataFrame(0.0, index=range(24), columns=["down_kw", "up_kw"])
        down_ev, up_ev = E["down_kw"].values, E["up_kw"].values
        down, up = down_ne + down_ev, up_nonev + up_ev
    out = pd.DataFrame({"load_kw": g["actual"].reindex(range(24)).values, "down_kw": down,
                        "down_thermal_kw": g["thermal"].reindex(range(24)).fillna(0).values, "down_ev_kw": down_ev,
                        "up_energy_kw": up_e, "up_cap_kw": cap, "up_nonev_kw": up_nonev, "up_ev_kw": up_ev,
                        "up_kw": up}, index=range(24))
    out.index.name = "hour"
    return out


def apply_participation(F, p):
    """M6: every flexible category, EV included, times the participation factor (enrolment x response)."""
    G = F.copy()
    for c in SCALED:
        if c in G:
            G[c] = F[c] * p
    return G
