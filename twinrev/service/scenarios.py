"""What-if scenarios of EV and PV adoption for one LV substation (Task 1.1, scenario generation on TWIN-REV).

Data: the processed Pecan Street Austin files (flexibility/scripts/prepare_data.py pecan_austin): hourly kW per home,
consumption = grid + solar, plus the circuits ev and solar. Never stored in git or in an image: mounted at run time.

Feeder: the IEEE European LV feeder has 55 customers, the data 25 homes. The feeder is filled with 55 units: the 25
real homes on the studied day, then the same homes again on other days of the same weekday (+-1, +-2 ... weeks),
so every unit is a real metered home-day and the substation sees the load it was designed for.

A scenario sets how many units have an EV and how many have PV:
  EV   homes with a car circuit keep their real charging; homes that get an EV in the scenario draw a real charging
       day of an EV home from the days around the studied day (same weekday/weekend type, seeded), so the added EVs
       charge with the observed timing and diversity; homes that lose their EV have the car circuit removed.
  PV   homes with solar keep their real generation (x pv_scale); homes that get PV get the median system size times
       the day's normalised PV shape of the solar homes.
Net load per home = consumption - solar (+ added EV, - removed EV); reactive power at pf 0.95 for consumption.
"""
import os, glob
import numpy as np
import pandas as pd

PF_TAN = np.tan(np.arccos(0.95))
TZ = "America/Chicago"


def load_site(data_dir):
    def rd(f):
        df = pd.read_csv(f, index_col="timestamp")
        df.index = pd.to_datetime(df.index, utc=True)
        return df
    W = rd(os.path.join(data_dir, "mains.csv.gz"))
    A = {os.path.basename(f)[len("appliances_"):-len(".csv.gz")]: rd(f)
         for f in sorted(glob.glob(os.path.join(data_dir, "appliances_*.csv.gz")))}
    homes = [h for h in W.columns if h in A]
    W = W[homes].tz_convert(TZ)
    col = lambda name: pd.DataFrame({h: (A[h][name] if name in A[h] else 0.0 * W[h]) for h in homes}).reindex(W.index.tz_convert("UTC")).set_axis(W.index).fillna(0.0)
    ev, solar = col("ev"), col("solar")
    return dict(W=W, ev=ev.clip(lower=0), solar=solar.clip(lower=0), homes=homes,
                ev_homes=[h for h in homes if ev[h].mean() > 0.05], pv_homes=[h for h in homes if solar[h].mean() > 0.05])


def complete_days(S):
    W = S["W"]
    n = W.notna().all(axis=1).groupby(W.index.normalize()).sum()
    return n[n == 24].index


def extreme_days(S):
    """Peak day = highest hourly net substation load; PV day = lowest (most negative) hourly net load."""
    days = complete_days(S)
    net = (S["W"] - S["solar"]).sum(axis=1)
    net = net[net.index.normalize().isin(days)]
    return dict(peak=net.idxmax().normalize(), pv=net.idxmin().normalize())


def _day(df, day):
    return df[(df.index >= day) & (df.index < day + pd.Timedelta(days=1))]


def _shift(day, days):
    """Local midnight `days` calendar days away (DST-safe)."""
    return (day.tz_localize(None) + pd.Timedelta(days=days)).tz_localize(day.tz)


def units(S, day, n_units=55):
    """[(unit name, source home, day offset)]: the real homes first, then copies of them from other weeks."""
    homes, out = S["homes"], []
    offsets = [7 * s * k for k in range(1, 9) for s in (1, -1)]
    for i in range(n_units):
        h, c = homes[i % len(homes)], i // len(homes)
        if c == 0:
            out.append((h, h, 0))
            continue
        good = [o for o in offsets if (lambda d: len(d) == 24 and d.notna().all())(_day(S["W"][h], _shift(day, o)))]
        if len(good) < c:
            raise ValueError(f"not enough complete days of {h} around {day.date()} to fill {n_units} units")
        out.append((f"{h}{good[c - 1]:+d}d", h, good[c - 1]))
    return out


def scenario(S, day, n_ev=None, n_pv=None, pv_scale=1.0, seed=0, n_units=55):
    """Hourly net P and Q (kW, kvar) per unit on `day` (local midnight, tz-aware) for the scenario."""
    U, rng = units(S, day, n_units), np.random.default_rng(seed)
    idx = _day(S["W"], day).index
    if len(idx) != 24:
        raise ValueError(f"{day.date()} has no complete hourly data")
    frame = lambda df: pd.DataFrame({u: _day(df[h], _shift(day, o)).values for u, h, o in U}, index=idx)
    W, ev, sol = frame(S["W"]), frame(S["ev"]), frame(S["solar"])
    if W.isna().any().any():
        raise ValueError(f"{day.date()} has no complete hourly data for every home")
    names, src = [u for u, _, _ in U], {u: h for u, h, _ in U}
    base_ev = [u for u in names if src[u] in S["ev_homes"]]
    base_pv = [u for u in names if src[u] in S["pv_homes"]]
    order = list(rng.permutation(names))                       # who gets an EV / PV first (seeded)
    n_ev = len(base_ev) if n_ev is None else int(np.clip(n_ev, 0, len(names)))
    n_pv = len(base_pv) if n_pv is None else int(np.clip(n_pv, 0, len(names)))
    ev_set = (base_ev + [u for u in order if u not in base_ev])[:n_ev]
    pv_set = (base_pv + [u for u in order if u not in base_pv])[:n_pv]
    cons = W.copy()
    for u in base_ev:
        if u not in ev_set:
            cons[u] = cons[u] - ev[u]                          # remove a real car
    added_ev = [u for u in ev_set if u not in base_ev]
    if added_ev:
        if not S["ev_homes"]:
            raise ValueError("no EV home in the data to draw charging days from")
        weekend = day.dayofweek >= 5
        pool = []
        for k in range(-21, 22):
            d = _shift(day, k)
            if (d.dayofweek >= 5) != weekend:
                continue
            e = _day(S["ev"], d)
            if len(e) == 24:
                pool += [e[h].values for h in S["ev_homes"]]
        for u in added_ev:
            cons[u] = cons[u] + pool[rng.integers(len(pool))]
    pv = pd.DataFrame(0.0, index=idx, columns=names)
    for u in base_pv:
        if u in pv_set:
            pv[u] = sol[u] * pv_scale
    added_pv = [u for u in pv_set if u not in base_pv]
    if added_pv:
        if not S["pv_homes"]:
            raise ValueError("no PV home in the data to take the PV shape from")
        kwp = {h: S["solar"][h].quantile(0.995) for h in S["pv_homes"]}
        today = _day(S["solar"], day)
        shape = pd.concat([today[h] / kwp[h] for h in S["pv_homes"] if kwp[h] > 0], axis=1).mean(axis=1).values
        size = float(np.median(list(kwp.values())))
        for u in added_pv:
            pv[u] = shape * size * pv_scale
    P = cons - pv
    Q = cons * PF_TAN
    info = dict(day=str(day.date()), units=len(names), n_ev=n_ev, n_pv=n_pv, pv_scale=pv_scale,
                ev_units_real=len(base_ev), pv_units_real=len(base_pv), added_ev=len(added_ev), added_pv=len(added_pv),
                peak_net_kw=round(float(P.sum(axis=1).max()), 2), min_net_kw=round(float(P.sum(axis=1).min()), 2))
    return P, Q, info
