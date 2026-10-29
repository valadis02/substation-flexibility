"""M4 (v0.10): EV charging - detection, sessions, plug-in windows, EV envelope and a day-ahead plan used for validation.

v0.10: EV is one flexible category like weather and appliances. M4 estimates it (`ev_home`, used inside the M3
decomposition, and `sessions`), M5
turns its sessions into kW down / up per hour (`envelope`, via flexsub.flexibility.ev_mean_day) in the same envelope
as weather and appliances, and M6 applies participation to all of it. (v0.9 had EV as a separate module M6.)

0. `ev_home`: EV charging per home from its hourly load (below).
1. `sessions`: each run of EV hours is a charging session: start, number of hours, energy (kWh), charger power
   (kW, the 90th percentile of its hourly EV load - full hours draw the charger's rated power).
2. Plug-in window. Hourly meters do not show when the car is plugged in or leaves, so the window can only be bounded:
     'observed' (safe lower bound): hours at which this home's car has been charging on >= `min_days` of the last
               `presence_days` days are hours at which the car is known to be at home and plugged. A session's window
               is the run of such hours that starts at the session (at least the session itself). The plan never asks a
               car to charge at an hour at which it has not been seen charging (T9d).
     'dwell'   (default): `dwell_h` hours from the session start (10 h, overnight). In T9d the reduce plan with
               'dwell' recovered 0.87 (Austin) / 0.79 (New York) of the charging really there, 'observed' 0.55 / 0.33
               (too short: it rarely extends past the session itself).
   Household presence (morning departure from the home's load profile) was tried and does not tell where the car is
   (T9d: 9-62% of true charging fell in the "away" hours).
3. `typical_day`: for the day ahead, every session of the last `window_days` days is a scenario of weight
   1/window_days, at its own clock hour, with its window. Uncontrolled charging = start at the session's hour at full
   power until its energy is delivered.
4. `envelope`: per hour of the day ahead (0..35 from local midnight), expected
     ev_kw    uncontrolled EV charging,
     plugged  EVs plugged in (inside their window),
     down_kw  charging that can be postponed (its window has room after it),
     up_kw    plugged EVs not charging at that hour that still have energy to deliver in their window (energy is moved
              from their usual hours, so every increase has a matching decrease elsewhere and vice versa).
5. `plan`: for a DSO request (reduce or increase, a block of hours, optionally a kW target) one instruction per home,
   e.g. "no charging 18-21, finish later", with the aggregate before / after per hour. Postponed energy is placed in
   the hours of the window with the lowest expected substation load (valley filling on `base_kw`, the expected
   non-EV load of the substation, e.g. the same-hour mean of the last 14 days), so the rebound does not form a new
   peak right after the block (T9d: days with a new peak after a reduce request 27% -> 0% in Austin).
"""
import numpy as np
import pandas as pd


def ev_home(y, k=2.5, gate=0.02, max_cv=0.14, min_runs=5, window_days=14, q=0.6, weather_load=None, session_cv=False):
    # session_cv=True (also drop non-flat runs one by one) was tested in T9c and rejected: EV energy x0.22
    """EV charging (kW) for one home from its own hourly load, after removing its weather-dependent load.

    An hour is EV-like if the load exceeds the same-hour reference (q-quantile of the previous window_days, as in
    events_home) by more than k kW. k = 2.5 kW is physical: a level-2 charger draws 3.3-7.2 kW, so even a partly
    charging hour stands out; level-1 charging (~1.4 kW) is not detectable this way. Unlike appliance events there is
    no limit on the run length (charging lasts hours). The first and last hour of a session are usually partial, so
    adjacent hours above k/2 are added. Home gate: the home is treated as an EV home only if EV-like hours are at least
    `gate` of its hours (2% ~ half an hour a day) AND the power inside its runs is flat, as a charger's is: median over
    runs of >= 2 hours of the coefficient of variation of the hourly excess <= max_cv, over at least min_runs runs.
    Residual air conditioning and dryers cycle and fail this test (T9b: CV 0.15-0.22 vs <= 0.13 for EV homes;
    max_cv set on Austin, checked on New York).
    Returns (ev_kw, mask)."""
    if weather_load is not None:
        y = y - weather_load.reindex(y.index).fillna(0)
    ref = y.groupby(y.index.hour).transform(lambda s: s.rolling(window_days, min_periods=7).quantile(q).shift(1))
    exc = y - ref
    core = (exc > k) & ref.notna()
    mask = core | ((exc > k / 2) & (core.shift(1, fill_value=False) | core.shift(-1, fill_value=False)))
    rid = (core != core.shift()).cumsum()
    cvs = [g.std() / g.mean() for _, g in exc[core].groupby(rid[core]) if len(g) >= 2]
    if core.mean() < gate or len(cvs) < min_runs or np.median(cvs) > max_cv:
        mask = mask & False
    elif session_cv:                                      # also per session: drop runs that are not flat / only 1 h
        keep = pd.Series(False, index=core.index)
        for _, g in exc[core].groupby(rid[core]):
            if len(g) >= 2 and g.std() / g.mean() <= max_cv:
                keep[g.index] = True
        core = keep
        mask = core | ((exc > k / 2) & (core.shift(1, fill_value=False) | core.shift(-1, fill_value=False)))
    return exc.clip(lower=0).where(mask, 0.0).where(ref.notna()), mask


def sessions(ev_kw, mask, tz):
    """Charging sessions of one home: DataFrame(start (local), hours, energy_kwh, power_kw)."""
    m = mask.fillna(False).astype(bool)
    if not m.any():
        return pd.DataFrame(columns=["start", "hours", "energy_kwh", "power_kw"])
    rid = (m != m.shift()).cumsum()
    g = ev_kw[m].groupby(rid[m])
    S = pd.DataFrame({"start": g.apply(lambda s: s.index[0]), "hours": g.size(), "energy_kwh": g.sum(),
                      "power_kw": g.quantile(0.9)}).reset_index(drop=True)
    S["start"] = pd.to_datetime(S["start"]).dt.tz_convert(tz)
    return S


def presence_hours(S, asof, presence_days=28, min_days=2):
    """Clock hours at which this home's car has been charging on >= min_days of the last presence_days days."""
    S = S[(S.start < asof) & (S.start >= asof - pd.Timedelta(days=presence_days))]
    seen = {}
    for r in S.itertuples():
        for k in range(int(r.hours)):
            t = r.start + pd.Timedelta(hours=k)
            seen.setdefault(t.hour, set()).add(t.normalize())
    return {h for h, d in seen.items() if len(d) >= min_days}


def typical_day(S_by_home, asof, window_days=14, mode="dwell", dwell_h=10, presence_days=28, min_days=2):
    """Scenarios for the day starting at `asof` (local midnight): every session of the last `window_days` days at its
    own clock start hour, weight 1/window_days, with its plug-in window end (hours from midnight, exclusive)."""
    rows = []
    for h, S in S_by_home.items():
        P = presence_hours(S, asof, presence_days, min_days) if mode == "observed" else None
        S = S[(S.start < asof) & (S.start >= asof - pd.Timedelta(days=window_days))]
        for r in S.itertuples():
            st = int(r.start.hour)
            if mode == "observed":
                end = st + int(r.hours)
                while end < st + 24 and (end % 24) in P:
                    end += 1
            else:
                end = st + max(int(dwell_h), int(r.hours))
            rows.append(dict(home=h, p=1.0 / window_days, start_hour=st, win_end=end,
                             energy_kwh=float(r.energy_kwh), power_kw=float(max(r.power_kw, 1e-3))))
    return pd.DataFrame(rows, columns=["home", "p", "start_hour", "win_end", "energy_kwh", "power_kw"])


def _profile(start, energy, power, horizon):
    """kW per hour (0..horizon-1, hours from local midnight) of a session charging at full power from `start`."""
    x = np.zeros(horizon)
    left, t = energy, start
    while left > 1e-9 and t < horizon:
        x[t] = min(power, left); left -= x[t]; t += 1
    return x


def _window(r, horizon):
    w = np.zeros(horizon, bool)
    w[r.start_hour:min(horizon, r.win_end)] = True
    return w


def envelope(T, horizon=36):
    """Per hour from local midnight of the day ahead (0..horizon-1; >23 = the next morning)."""
    out = pd.DataFrame(0.0, index=range(horizon), columns=["ev_kw", "plugged", "down_kw", "up_kw"])
    for r in T.itertuples():
        base = _profile(r.start_hour, r.energy_kwh, r.power_kw, horizon)
        win = _window(r, horizon)
        slack = win.sum() - int(np.ceil(r.energy_kwh / r.power_kw))         # plugged hours not needed for charging
        out["ev_kw"] += r.p * base
        out["plugged"] += r.p * win
        if slack > 0:
            out["down_kw"] += r.p * base
            out["up_kw"] += r.p * np.where(win & (base == 0), min(r.power_kw, r.energy_kwh), 0.0)
    out.index.name = "hour_from_midnight"
    return out


def plan(T, hours, direction, target_kw=None, base_kw=None, stagger=True, horizon=36):
    """One instruction per home for a request in hours [h0, h1) (from local midnight of the day ahead).
    direction 'down': EVs charging in the block stop there and finish later inside their window.
    direction 'up':   plugged EVs move energy from their usual hours (latest first) into the block.
    stagger: postponed energy goes to the window hours with the lowest expected load (base_kw + EV so far);
             otherwise to the first free hours after the block (simple, makes a rebound peak).
    Homes are taken in order of expected contribution until target_kw (mean over the block) is met.
    Returns (per_home DataFrame, aggregate DataFrame per hour: before_kw, after_kw, change_kw [, base_kw, total_*])."""
    h0, h1 = hours
    blk = np.zeros(horizon, bool); blk[h0:h1] = True
    base = np.zeros(horizon) if base_kw is None else np.resize(np.asarray(base_kw, float), horizon)
    # expected uncontrolled EV load of everyone (homes that are not instructed keep charging as usual)
    agg_before = np.zeros(horizon)
    for r in T.itertuples():
        agg_before += r.p * _profile(r.start_hour, r.energy_kwh, r.power_kw, horizon)
    # expected block contribution per home, to choose who is instructed
    contrib = {}
    for r in T.itertuples():
        b = _profile(r.start_hour, r.energy_kwh, r.power_kw, horizon); w = _window(r, horizon)
        if direction == "down":
            ok = b[blk].sum() > 0 and (w & ~blk & (np.arange(horizon) >= h1)).sum() * r.power_kw >= b[blk].sum() - 1e-9
            c = r.p * b[blk].mean() if ok else 0.0
        else:
            room = (w & blk).sum()
            c = r.p * min(room * r.power_kw, b[~blk].sum()) / (h1 - h0) if room else 0.0
        contrib[r.home] = contrib.get(r.home, 0.0) + c
    chosen, got = [], 0.0
    for home, c in sorted(contrib.items(), key=lambda kv: -kv[1]):
        if c <= 0 or (target_kw is not None and got >= target_kw):
            break
        chosen.append(home); got += c
    after = agg_before.copy()
    rows = []
    for home in chosen:
        hb, ha = np.zeros(horizon), np.zeros(horizon)
        for r in T[T.home == home].itertuples():
            b = _profile(r.start_hour, r.energy_kwh, r.power_kw, horizon); w = _window(r, horizon)
            a = b.copy()
            if direction == "down":
                moved = a[blk].sum(); a[blk] = 0
                cand = [t for t in range(h1, horizon) if w[t]]
                left, trial = moved, after.copy()
                while left > 1e-9:
                    free = [t for t in cand if a[t] < r.power_kw - 1e-9]
                    if not free:
                        break
                    t = min(free, key=lambda t: base[t] + trial[t]) if stagger else free[0]
                    add = min(r.power_kw - a[t], left); a[t] += add; left -= add
                    trial[t] += r.p * add
                if left > 1e-6:                                    # does not fit: this scenario charges as usual
                    a = b.copy()
                else:
                    trial[blk] -= r.p * b[blk]
                    after = trial
            else:
                room = [t for t in range(h0, h1) if w[t]]
                if not room:
                    continue
                outside = b.copy(); outside[blk] = 0
                take = min(outside.sum(), sum(r.power_kw - b[t] for t in room))
                left = take
                for t in reversed(range(horizon)):
                    if outside[t] > 0 and left > 0:
                        d = min(outside[t], left); a[t] -= d; left -= d
                left = take
                for t in sorted(room, key=lambda t: base[t] + after[t]):
                    add = min(r.power_kw - a[t], left); a[t] += add; left -= add
                after += r.p * (a - b)
            hb += r.p * b; ha += r.p * a
        hrs = lambda x: ",".join(f"{t % 24:02d}" for t in np.flatnonzero(x > 0.05))
        rows.append(dict(home=home, scenarios=int((T.home == home).sum()), usual_hours=hrs(hb), new_hours=hrs(ha),
                         instruction=(f"no charging {h0 % 24:02d}-{h1 % 24:02d}, finish later" if direction == "down"
                                      else f"charge {h0 % 24:02d}-{h1 % 24:02d}"),
                         expected_block_change_kw=round(float((ha - hb)[blk].mean()), 2)))
    agg = pd.DataFrame({"before_kw": agg_before, "after_kw": after, "change_kw": after - agg_before}, index=range(horizon))
    if base_kw is not None:
        agg["base_kw"] = base
        agg["total_before_kw"], agg["total_after_kw"] = base + agg_before, base + after
    agg.index.name = "hour_from_midnight"
    return pd.DataFrame(rows), agg
