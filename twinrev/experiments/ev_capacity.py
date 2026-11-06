"""How many EVs fit before the first limit breaks, and how often limits break: no flexibility, sub-metering, the flexibility method.

Scenario = a study day (24 h from 12:00, so that evening charging can move past midnight) and a seed (who gets a car).
For a number of EVs N, a limit breaks if the transformer, a cable or a voltage is outside its limit in any hour.
  none       the profiles as they are
  submeter   the flexibility is estimated by the M5 rule from the true sub-metered circuits of the 35 days BEFORE the study day:
             what a DSO could do with full sub-metering. It does not know the study day itself
  method     flexsub estimates kW down / up from the meters and weather of the days before the study day
In both, the controller plans on the estimate and the request then meets the true flexibility of the day: only what is really
there is delivered. An overestimate therefore cannot look better than it is.
Scores: (method - none) / (submeter - none), the share of sub-metering's gain in EVs that the method captures; and the same for
the transformer peak with a fixed number of EVs.

True flexibility (same for both, from the sub-metered circuits):
  EV        each charging session keeps its energy and charger power inside max(ev_dwell_h, its length) hours from its start
            (the plug-in window is the method's assumption too: the data has no plug-in times), clipped to the study window
  non-EV    weather circuits + shiftable appliances move within +-shift_window_h hours, energy conserved one to one (no
            rebound losses); at most the load present can leave an hour, at most the q90 extra draw (M5 rule) can enter it
The planner is given the true load in both, so the gap between them is due to the flexibility estimate only.

Participation: only a seeded share p of the homes responds (nested as p grows); the others keep their habits, in both cases.
Both envelopes are scaled by p (M6): neither knows which homes respond. The p values come from Config.participation_scenarios (enrolment x response), placeholders until T6.

Locked test: only development homes and times of data/splits.json are used unless --homes all is given.

  python3 ev_capacity.py sizing --data-dir ../../flexibility/data --participation 0.5
  python3 ev_capacity.py pilot  --data-dir ../../flexibility/data --trafo-kva 160 --url http://localhost:8001
"""
import argparse, json, os, sys, time, urllib.request
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy import sparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "flexibility"))
from flexsub import decompose, flexibility, thermal, ev as m6                     # noqa: E402
from flexsub.appliances import category                                 # noqa: E402
from flexsub.config import Config                                       # noqa: E402
from flexsub.data import load_processed                                 # noqa: E402

TZ, DATASET = "America/Chicago", "pecan_austin"
PF_TAN = np.tan(np.arccos(0.95))
LIM = dict(v_min=0.95, v_max=1.05, trafo=100.0, line=100.0)
HIST_DAYS = 120
MAX_EV = 55         # one car per home (the feeder has 55 units); pick the transformer so that (b) stays below this
FIX_EV = 55         # peak relief is compared at this number of EVs (one per home)


def config():
    return Config(tz=TZ, latitude=30.27)


# ---------------------------------------------------------------------------------------------------- data and units
def load_site(data_dir, homes="dev", site_dir=None):
    d = load_processed(site_dir or os.path.join(data_dir, "processed", DATASET))
    W, A, w = d["W"], d["appliances"], d["weather"]
    if w is None:
        raise SystemExit("no weather.csv.gz: add it with flexibility/scripts/add_weather.py pecan_austin <csv>")
    ids = [h for h in W.columns if h in A]
    cut = None
    if homes == "dev":
        split = json.load(open(os.path.join(data_dir, "splits.json")))["datasets"][DATASET]
        ids = [h for h in ids if h not in split["held_out_homes"]]
        cut = min(pd.Timestamp(split["time_cut"][h]) for h in ids)
        W = W[W.index < cut]
    W = W[ids]
    col = lambda test: pd.DataFrame({h: A[h][[c for c in A[h].columns if test(c)]].sum(axis=1).reindex(W.index).fillna(0.0).clip(lower=0)
                                     for h in ids})
    is_ev = lambda c: category(c, DATASET) == "ev" or c == "ev"
    is_th = lambda c: category(c, DATASET) == "thermal" or c in ("ac", "furnace", "heater") or c.startswith("ac_")
    is_sh = lambda c: category(c, DATASET) == "shiftable" and not is_ev(c) and not is_th(c)
    ev, th, sh, sol = col(is_ev), col(is_th), col(is_sh), col(lambda c: c == "solar")
    return dict(W=W, ev=ev, flex=th + sh, th=th, sh=sh, solar=sol, weather=w, homes=ids, cut=cut,
                ev_homes=[h for h in ids if ev[h].mean() > 0.05])


def local_days(first, last):
    """Local midnights from first to last (calendar dates, DST-safe)."""
    return [d.tz_localize(TZ) for d in pd.date_range(pd.Timestamp(first).tz_localize(None).normalize(),
                                                      pd.Timestamp(last).tz_localize(None).normalize(), freq="D")]


def study_index(day):
    t0 = (day.tz_localize(None) + pd.Timedelta(hours=12)).tz_localize(TZ)
    return pd.date_range(t0, periods=24, freq="1h")


def study_days(S, n):
    """Complete study windows with HIST_DAYS of history, ranked by the peak net load; n of them spread over the top 30."""
    W, net = S["W"].tz_convert(TZ), (S["W"] - S["solar"]).sum(axis=1, min_count=len(S["homes"])).tz_convert(TZ)
    days, peak = [], []
    for d in local_days(W.index.min().tz_localize(None) + pd.Timedelta(days=HIST_DAYS), W.index.max().tz_localize(None) - pd.Timedelta(days=1)):
        x = net.reindex(study_index(d))
        if x.notna().all():
            days.append(d)
            peak.append(x.max())
    order = np.argsort(peak)[::-1][:30]
    pick = [order[int(i)] for i in np.round(np.linspace(0, len(order) - 1, min(n, len(order))))]
    return [(days[pick[i % len(pick)]], i) for i in range(n)]


def make_units(S, day, seed, n_units=55):
    """Units with whole series, shifted by whole weeks: the real homes, then the same homes from other weeks."""
    rng = np.random.default_rng(seed)
    loc = S["W"].tz_convert(TZ)
    win = study_index(day)
    units = []
    for i in range(n_units):
        h, c = S["homes"][i % len(S["homes"])], i // len(S["homes"])
        if c == 0:
            units.append((h, h, 0))
            continue
        ok = [7 * s * k for k in range(1, 9) for s in (1, -1)
              if loc[h].reindex(win + pd.Timedelta(days=7 * s * k)).notna().all()]
        if len(ok) < c:
            raise ValueError(f"not enough complete days of {h} around {day.date()}")
        units.append((f"{h}{ok[c - 1]:+d}d", h, ok[c - 1]))
    names = [u for u, _, _ in units]
    base = [u for u, h, _ in units if h in S["ev_homes"]]
    other = [u for u in names if u not in base]
    order = list(rng.permutation(base)) + list(rng.permutation(other))      # nested: N+1 cars contain the N cars
    # an added car is one real car of an EV home, from a seeded number of weeks away, kept for the whole history
    pick = lambda: (S["ev_homes"][rng.integers(len(S["ev_homes"]))], 7 * int(rng.integers(-8, 9)))
    car = {u: pick() for u in other}
    resp = list(rng.permutation(names))                                    # who responds first
    return dict(units=units, names=names, base_ev=set(base), order=order, car=car, resp=resp, day=day, seed=seed)


def _shifted(df, h, o, idx):
    """Series of home h, o days away from idx (local time, DST-safe by calendar shift)."""
    s = df[h].tz_convert(TZ)
    key = idx.tz_localize(None) + pd.Timedelta(days=o)
    s = s[~s.index.tz_localize(None).duplicated()]
    s.index = s.index.tz_localize(None)
    return pd.Series(s.reindex(key).values, index=idx)


def series(S, U, n_ev, idx):
    """cons (gross kW per unit, as the method's meters), ev, flex (true non-EV flexible), th, sh, solar on idx."""
    ev_set = set(U["order"][:n_ev])
    out = {k: {} for k in ("cons", "ev", "flex", "th", "sh", "solar")}
    for u, h, o in U["units"]:
        c = _shifted(S["W"], h, o, idx)
        e = _shifted(S["ev"], h, o, idx).fillna(0.0)
        if u in U["base_ev"] and u not in ev_set:
            c, e = c - e, 0.0 * e
        elif u in ev_set and u not in U["base_ev"]:
            k, j = U["car"][u]
            e = _shifted(S["ev"], k, o + j, idx).fillna(0.0)
            c = c + e
        out["cons"][u], out["ev"][u] = c, e
        for k, df in (("flex", S["flex"]), ("th", S["th"]), ("sh", S["sh"]), ("solar", S["solar"])):
            out[k][u] = _shifted(df, h, o, idx).fillna(0.0)
    return {k: pd.DataFrame(v) for k, v in out.items()}


# ---------------------------------------------------------------------------------------------------- flexibility
def estimate_envelope(S, U, n_ev, cfg):
    """The method (M2-M5) from data strictly before the study day. Returns down, up on the 24 study hours."""
    day = U["day"]
    idx = pd.date_range(day - pd.Timedelta(days=HIST_DAYS), day, freq="1h", inclusive="left")
    X = series(S, U, n_ev, idx)["cons"]
    X.index = X.index.tz_convert("UTC")
    w = S["weather"].reindex(X.index)
    y = X.sum(axis=1, min_count=X.shape[1])
    days = local_days(day.tz_localize(None) - pd.Timedelta(days=35), day.tz_localize(None) - pd.Timedelta(days=1))
    th = thermal.thermal_dd_loo(y, w, days, cfg)
    D = decompose.decompose_substation(X, w, th, cfg)
    D = D[D.index >= days[0]]
    F = flexibility.flexibility_by_hour(D, cfg)
    h = study_index(day).hour
    get = lambda c: F[c].reindex(h).values
    return dict(down_ev=get("down_ev_kw"), up_ev=get("up_ev_kw"), down_ne=get("down_kw") - get("down_ev_kw"), up_ne=get("up_nonev_kw"))


def submeter_envelope(S, U, n_ev, cfg):
    """The M5 rule on the true circuits of the 35 days before the study day (no decomposition error, no look at the day itself)."""
    day = U["day"]
    idx = pd.date_range(day - pd.Timedelta(days=35), day, freq="1h", inclusive="left")
    H = series(S, U, n_ev, idx)
    th, sh, ev, act = H["th"].sum(axis=1), H["sh"].sum(axis=1), H["ev"].sum(axis=1), H["cons"].sum(axis=1)
    D = pd.DataFrame({"actual": act, "base": 0.0, "thermal": th, "ev": ev, "shiftable": sh, "routine": act - th - sh - ev}, index=idx)
    D.attrs["ev_sessions"] = {u: m6.sessions(H["ev"][u], H["ev"][u] > 0.3, cfg.tz) for u in H["ev"].columns if H["ev"][u].sum() > 0}
    F = flexibility.flexibility_by_hour(D, cfg)
    h = study_index(day).hour
    get = lambda c: F[c].reindex(h).values
    return dict(down_ev=get("down_ev_kw"), up_ev=get("up_ev_kw"), down_ne=get("down_kw") - get("down_ev_kw"), up_ne=get("up_nonev_kw"))


def true_up_cap(S, U, n_ev, cfg):
    """M5 cap rule on the true circuits of the last 35 days (kW that can enter each study hour)."""
    day = U["day"]
    idx = pd.date_range(day - pd.Timedelta(days=35), day, freq="1h", inclusive="left")
    H = series(S, U, n_ev, idx)
    D = pd.DataFrame({"thermal": H["th"].sum(axis=1), "shiftable": H["sh"].sum(axis=1)}, index=idx)
    _, _, cap = flexibility._short_cycle(D, ("thermal", "shiftable"), cfg)
    return cap[study_index(day).hour]


def ev_sessions(ev):
    """[(unit, start, length, energy, power)] of the 24 h window: runs of charging above 0.3 kW."""
    out = []
    for u in ev.columns:
        x, t = ev[u].values, 0
        while t < 24:
            if x[t] > 0.3:
                e = t
                while e < 24 and x[e] > 0.3:
                    e += 1
                out.append((u, t, e - t, float(x[t:e].sum()), float(x[t:e].max())))
                t = e
            else:
                t += 1
    return out


class TrueFlex:
    """What can really move in the study window, as a linear model. Delta(t) = new load - old load, summed over units."""

    def __init__(self, ev, flex, cap, cfg):
        self.ev, self.flex = ev, flex
        self.sess = ev_sessions(ev)
        self.dwell, self.S = cfg.ev_dwell_h, cfg.shift_window_h
        self.F = flex.sum(axis=1).values
        self.cap = cap
        self.var, n = [], 0                              # (kind, ...) of every variable
        for i, (u, s, L, E, p) in enumerate(self.sess):
            for t in range(s, min(24, s + max(self.dwell, L))):
                self.var.append(("ev", i, t))
        for a in range(24):
            for b in range(max(0, a - self.S), min(24, a + self.S + 1)):
                if a != b and self.F[a] > 1e-6:
                    self.var.append(("f", a, b))
        self.n = len(self.var)
        self.x0 = ev.iloc[:, :].values
        self.ev0 = np.zeros(24)
        for (u, s, L, E, p) in self.sess:
            self.ev0[s:s + L] += ev[u].values[s:s + L]

    def constraints(self):
        """Returns Dt (24 x n, Delta = Dt x - ev0), A_eq, b_eq, A_ub, b_ub, upper bounds."""
        n = self.n
        Dt, Aeq, Aub = sparse.lil_matrix((24, n)), sparse.lil_matrix((len(self.sess), n)), sparse.lil_matrix((48, n))
        ub = np.zeros(n)
        for j, v in enumerate(self.var):
            if v[0] == "ev":
                _, i, t = v
                Dt[t, j] += 1
                Aeq[i, j] = 1
                ub[j] = self.sess[i][4]
            else:
                _, a, b = v
                Dt[b, j] += 1
                Dt[a, j] -= 1
                Aub[a, j] = 1                            # out of hour a <= load there
                Aub[24 + b, j] = 1                       # into hour b <= cap
                ub[j] = np.inf
        beq = np.array([s[3] for s in self.sess])
        bub = np.r_[self.F, self.cap]
        return Dt.tocsr(), Aeq.tocsr(), beq, Aub.tocsr(), bub, ub

    def _solve(self, extra, c, Aub2=None, bub2=None, Aeq2=None, beq2=None):
        Dt, Aeq, beq, Aub, bub, ub = self.constraints()
        pad = lambda M: sparse.hstack([M, sparse.csr_matrix((M.shape[0], extra))])
        A_ub, b_ub = pad(Aub), bub
        if Aub2 is not None:
            A_ub, b_ub = sparse.vstack([A_ub, Aub2]), np.r_[bub, bub2]
        A_eq, b_eq = (pad(Aeq), beq) if len(beq) else (None, None)
        r = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=[(0, u) for u in ub] + [(None, None)] * extra, method="highs")
        if not r.success:
            raise RuntimeError(f"LP failed: {r.message}")
        return r.x

    def _motion_cost(self):
        return np.array([1e-4 * (1 + (abs(v[1] - v[2]) if v[0] == "f" else 0)) if v[0] == "f" else 0.0 for v in self.var])

    def min_peak(self, net):
        """Lowest peak the true flexibility allows (used by the tests as a physical bound). Returns the solution x."""
        Dt, *_ = self.constraints()
        A = sparse.hstack([Dt, sparse.csr_matrix(-np.ones((24, 1)))]).tocsr()
        # small preference for early EV charging keeps it unique; the peak is what counts
        c = np.r_[self._motion_cost() + np.array([1e-5 * v[2] if v[0] == "ev" else 0 for v in self.var]), 1.0]
        return self._solve(1, c, A, self.ev0 - net)[:-1]

    def deliver(self, want):
        """Requested change want(t) (kW, +up / -down) meets the true flexibility: closest deliverable. Returns x."""
        Dt, *_ = self.constraints()
        n = self.n
        G = sparse.hstack([Dt, -sparse.identity(24)]).tocsr()    # Delta - want <= e
        H = sparse.hstack([-Dt, -sparse.identity(24)]).tocsr()   # want - Delta <= e
        A = sparse.vstack([G, H])
        b = np.r_[want + self.ev0, -want - self.ev0]
        c = np.r_[self._motion_cost(), np.ones(24)]
        x = self._solve(24, c, A, b)
        return x[:n]

    def apply(self, x):
        """New gross load per unit from the solution x (DataFrame change on top of the old)."""
        add = pd.DataFrame(0.0, index=self.ev.index, columns=self.ev.columns)
        out_a, in_b = np.zeros(24), np.zeros(24)
        new_ev = {}
        for j, v in enumerate(self.var):
            if x[j] < 1e-9:
                continue
            if v[0] == "ev":
                new_ev.setdefault(v[1], np.zeros(24))[v[2]] += x[j]
            else:
                out_a[v[1]] += x[j]
                in_b[v[2]] += x[j]
        for i, (u, s, L, E, p) in enumerate(self.sess):
            old = np.zeros(24)
            old[s:s + L] = self.ev[u].values[s:s + L]
            add[u] += new_ev.get(i, np.zeros(24)) - old
        share_in = self.flex.mean(axis=0) / max(self.flex.mean(axis=0).sum(), 1e-9)
        for t in range(24):
            if self.F[t] > 1e-9:
                add.iloc[t] -= out_a[t] * self.flex.iloc[t].values / self.F[t]
            add.iloc[t] += in_b[t] * share_in.values
        return add


def plan(net, env, cfg):
    """Controller on an estimated envelope: minimise the substation peak. Same structure as the true model, so a request
    never asks to move load further than the method says it can move: non-EV within +-shift_window_h, EV to later hours
    inside ev_dwell_h. Returns the wanted change per hour (+up / -down)."""
    moves = [("ne", a, b) for a in range(24) for b in range(max(0, a - cfg.shift_window_h), min(24, a + cfg.shift_window_h + 1)) if a != b]
    moves += [("ev", a, b) for a in range(24) for b in range(a + 1, min(24, a + cfg.ev_dwell_h))]
    n = len(moves)
    D, O, I = sparse.lil_matrix((24, n)), sparse.lil_matrix((48, n)), sparse.lil_matrix((48, n))
    for j, (k, a, b) in enumerate(moves):
        D[b, j] += 1
        D[a, j] -= 1
        off = 0 if k == "ne" else 24
        O[off + a, j] = 1
        I[off + b, j] = 1
    A = sparse.vstack([sparse.hstack([D, sparse.csr_matrix(-np.ones((24, 1)))]), sparse.hstack([O, sparse.csr_matrix((48, 1))]),
                       sparse.hstack([I, sparse.csr_matrix((48, 1))])]).tocsr()
    pos = lambda v: np.maximum(np.asarray(v, dtype=float), 0.0)
    b_ub = np.r_[-net, pos(env["down_ne"]), pos(env["down_ev"]), pos(env["up_ne"]), pos(env["up_ev"])]
    c = np.r_[1e-4 * np.ones(n), 1.0]
    r = linprog(c, A_ub=A, b_ub=b_ub, bounds=[(0, None)] * n + [(None, None)], method="highs")
    if not r.success:
        raise RuntimeError(f"plan LP failed: {r.message}")
    return D.tocsr() @ r.x[:n]


def profiles(S, U, n_ev, case, cfg, envelope=None, p=1.0):
    """P, Q (kW, kvar, 24 study hours, per unit) for one case, plus info."""
    idx = study_index(U["day"])
    X = series(S, U, n_ev, idx)
    cons, sol = X["cons"].copy(), X["solar"]
    info = {}
    if case != "none":
        who = [u for u in X["ev"].columns if u in set(U["resp"][:int(round(p * len(U["resp"])))])]
        tf = TrueFlex(X["ev"][who], X["flex"][who], p * true_up_cap(S, U, n_ev, cfg), cfg)
        net = (cons - sol).sum(axis=1).values
        env = envelope if envelope is not None else (submeter_envelope if case == "submeter" else estimate_envelope)(S, U, n_ev, cfg)
        env = {k: p * v for k, v in env.items()}
        want = plan(net, env, cfg)
        x = tf.deliver(want)
        got = tf.constraints()[0] @ x - tf.ev0
        info = dict(requested_kwh=round(float(np.abs(want).sum() / 2), 1), delivered_kwh=round(float(np.abs(got).sum() / 2), 1),
                    est_down_ev_kw_sum=round(float(np.sum(env["down_ev"])), 1), est_down_ne_kw_sum=round(float(np.sum(env["down_ne"])), 1),
                    true_ev_kwh=round(float(tf.ev0.sum()), 1), true_flex_kwh=round(float(tf.F.sum()), 1))
        cons = cons + tf.apply(x).reindex(columns=cons.columns, fill_value=0.0)
    P = cons - sol
    return P, cons * PF_TAN, info


# ---------------------------------------------------------------------------------------------------- the twin
def lods(names):
    pts = [int(round(i * 54 / max(len(names) - 1, 1))) + 1 for i in range(len(names))]
    return {u: f"lod_{p:02d}" for u, p in zip(names, pts)}


def as_lod(df):
    m = lods(list(df.columns))
    return {m[u]: [float(v) for v in df[u].values] for u in df.columns}


class TwinRev:
    def __init__(self, url):
        self.url, self.runs = url.rstrip("/"), 0

    def __call__(self, P, Q):
        self.runs += 1
        body = json.dumps(dict(p_kw=as_lod(P), q_kvar=as_lod(Q))).encode()
        req = urllib.request.Request(f"{self.url}/power-flow", data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode())


class Local:
    def __init__(self, archive, kva):
        from lv_bfs import Feeder
        self.f, self.runs = Feeder(archive, kva), 0

    def __call__(self, P, Q):
        self.runs += 1
        return self.f.run(as_lod(P), as_lod(Q))


class LocalDPsim(Local):
    def __init__(self, archive, kva, workdir):
        from lv_bfs import DPsimFeeder
        self.f, self.runs = DPsimFeeder(archive, kva, workdir), 0


class TrafoOnly:
    """Transformer loading from the sum of the loads, no network (for sizing only)."""

    def __init__(self, kva):
        self.kva, self.runs = kva, 0

    def __call__(self, P, Q):
        self.runs += 1
        s = np.hypot(P.sum(axis=1).values, Q.sum(axis=1).values)
        return dict(trafo_pct=list(100 * s / self.kva), line_pct=[0.0] * 24, vmin_pu=[1.0] * 24, vmax_pu=[1.0] * 24)


def broken(r):
    """Limits broken in the hourly result of a power flow."""
    out = []
    if max(r["trafo_pct"]) > LIM["trafo"]:
        out.append("transformer")
    if max(r["line_pct"]) > LIM["line"]:
        out.append("cable")
    if min(r["vmin_pu"]) < LIM["v_min"]:
        out.append("undervoltage")
    if max(r["vmax_pu"]) > LIM["v_max"]:
        out.append("overvoltage")
    return out


def capacity(test, n_max=MAX_EV):
    """Largest N with no limit broken (bisection, assumes monotone in N); -1 if even N = 0 breaks a limit."""
    if test(0):
        return -1, test(0)
    if not test(n_max):
        return n_max, []
    lo, hi = 0, n_max
    while hi - lo > 1:
        m = (lo + hi) // 2
        lo, hi = (m, hi) if not test(m) else (lo, m)
    return lo, test(hi)


def run_scenario(S, U, backend, cfg, cases=("none", "submeter", "method"), p=1.0):
    """Capacity per case; results of (N, case) are cached."""
    res = {}
    for case in cases:
        cache, info = {}, {}

        def test(n):
            if n not in cache:
                P, Q, inf = profiles(S, U, n, case, cfg, p=p)
                r = backend(P, Q)
                cache[n], info[n] = broken(r), dict(inf, trafo_max=round(max(r["trafo_pct"]), 1), line_max=round(max(r["line_pct"]), 1),
                                                     vmin=round(min(r["vmin_pu"]), 4))
            return cache[n]

        cap, why = capacity(test)
        test(FIX_EV)
        res[case] = dict(capacity=cap, next_breaks=why, peak_at_fix_pct=info[FIX_EV]["trafo_max"], probes={str(k): v for k, v in sorted(info.items())})
    a, b, c = (res[k]["capacity"] for k in ("none", "submeter", "method")) if len(cases) == 3 else (res["none"]["capacity"], res["submeter"]["capacity"], None)
    pk = {k: float(res[k]["peak_at_fix_pct"]) for k in res}
    gain = pk["none"] - pk["submeter"]
    return dict(day=str(U["day"].date()), seed=U["seed"], participation=p, alpha=a, submeter=b, method=c, peaks_at_fix_pct=pk,
                peak_score=(round((pk["none"] - pk["method"]) / gain, 3) if "method" in pk and gain > 0 else None),
                score=(round((c - a) / (b - a), 3) if (c is not None and b > a and a >= 0) else None), cases=res)


def summary(rows):
    ok = [r for r in rows if r["score"] is not None]
    s = np.array([r["score"] for r in ok]) if ok else np.array([])
    out = dict(scenarios=len(rows), with_score=len(ok), alpha_below_zero=sum(r["alpha"] < 0 for r in rows),
               submeter_at_ceiling=sum(r["submeter"] >= MAX_EV for r in rows), method_at_ceiling=sum(r["method"] is not None and r["method"] >= MAX_EV for r in rows))
    p = [r["peak_score"] for r in rows if r.get("peak_score") is not None]
    if p:
        out.update(peak_score_median=round(float(np.median(p)), 3), peak_score_min=round(float(min(p)), 3), peak_score_max=round(float(max(p)), 3))
    if len(s):
        rng = np.random.default_rng(0)
        boot = [np.median(rng.choice(s, len(s))) for _ in range(2000)]
        out.update(score_median=round(float(np.median(s)), 3), score_min=round(float(s.min()), 3), score_max=round(float(s.max()), 3),
                   score_median_ci95=[round(float(q), 3) for q in np.quantile(boot, [0.025, 0.975])],
                   submeter_minus_method_median=float(np.median([r["submeter"] - r["method"] for r in ok])))
    return out


def run_risk(S, picks, backend, cfg, levels, parts):
    """Fixed numbers of EVs: which limits break, how often and for how long, per case. The envelope is computed once per
    scenario and N (participation only scales it)."""
    rows = []
    for d, s in picks:
        U = make_units(S, d, s)
        for n in levels:
            env = estimate_envelope(S, U, n, cfg)
            for p, case in [(1.0, "none")] + [(p, c) for p in parts for c in ("submeter", "method")]:
                P, Q, _ = profiles(S, U, n, case, cfg, envelope=env if case == "method" else None, p=p)
                r = backend(P, Q)
                over = np.array(r["trafo_pct"]) > LIM["trafo"], np.array(r["line_pct"]) > LIM["line"], np.array(r["vmin_pu"]) < LIM["v_min"], np.array(r["vmax_pu"]) > LIM["v_max"]
                rows.append(dict(day=str(d.date()), seed=s, n_ev=n, case=case, participation=p, broken=broken(r),
                                 hours_over=int(np.logical_or.reduce(over).sum()), trafo_max=round(max(r["trafo_pct"]), 1),
                                 line_max=round(max(r["line_pct"]), 1), vmin=round(min(r["vmin_pu"]), 4),
                                 kwh_over=round(float(np.clip(np.array(r["trafo_pct"]) - 100, 0, None).sum() * backend.kva / 100), 1)))
        print(f"{d.date()} seed {s} done, {backend.runs} power flows", flush=True)
    return rows


def risk_table(rows):
    """Per N, participation and case: share of scenarios with a broken limit, mean hours over, median peak."""
    out = []
    df = pd.DataFrame(rows)
    none = df[df.case == "none"]
    for (n, p, c), g in df[df.case != "none"].groupby(["n_ev", "participation", "case"]):
        out.append(dict(n_ev=int(n), participation=p, case=c, scenarios=len(g), share_broken=round(float((g.hours_over > 0).mean()), 3),
                        mean_hours_over=round(float(g.hours_over.mean()), 2), median_trafo_max=float(g.trafo_max.median()),
                        mean_kwh_over=round(float(g.kwh_over.mean()), 1)))
    for n, g in none.groupby("n_ev"):
        out.append(dict(n_ev=int(n), participation=0.0, case="none", scenarios=len(g), share_broken=round(float((g.hours_over > 0).mean()), 3),
                        mean_hours_over=round(float(g.hours_over.mean()), 2), median_trafo_max=float(g.trafo_max.median()),
                        mean_kwh_over=round(float(g.kwh_over.mean()), 1)))
    return sorted(out, key=lambda r: (r["n_ev"], r["participation"], r["case"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sizing", "pilot", "risk"])
    ap.add_argument("--data-dir", default=os.path.join(HERE, "..", "..", "flexibility", "data"))
    ap.add_argument("--homes", choices=["dev", "all"], default="dev", help="'all' opens the locked test homes")
    ap.add_argument("--ev-q", type=float, help="reference quantile of the EV detector (flexsub default if omitted)")
    ap.add_argument("--levels", type=int, nargs="+", default=[14, 28, 55], help="risk: numbers of EVs")
    ap.add_argument("--site-dir", help="a ready data folder instead (twinrev/data/synthetic_55); uses all its homes")
    ap.add_argument("-n", type=int, default=5, help="number of scenarios")
    ap.add_argument("--kva", type=float, nargs="+", default=[140, 160, 180, 200], help="sizing: candidates")
    ap.add_argument("--trafo-kva", type=float)
    ap.add_argument("--participation", type=float, nargs="+", default=[0.25, 0.5], help="share of homes that respond")
    ap.add_argument("--backend", choices=["twinrev", "local", "dpsim"], default="twinrev")
    ap.add_argument("--url", default="http://localhost:8001")
    ap.add_argument("--archive", help="local backend: cel3 archive from cim/make_lv_zip.py")
    ap.add_argument("--out", default=os.path.join(HERE, "results", "ev_capacity.json"))
    a = ap.parse_args()
    if a.ev_q is not None:                                                  # test of a setting; the method's code is not changed
        from flexsub import ev as m6
        _orig = m6.ev_home
        m6.ev_home = lambda y, **kw: _orig(y, **{**kw, "q": a.ev_q})
    S, cfg = load_site(a.data_dir, "all" if a.site_dir else a.homes, a.site_dir), config()
    print(f"homes {len(S['homes'])} ({a.homes}), EV homes {len(S['ev_homes'])}, data until {S['W'].index.max()}")
    picks = study_days(S, a.n)
    if a.cmd == "sizing":
        print("p, kVA | capacity per scenario (no flexibility / submeter), transformer only, no network")
        for p in a.participation:
            for kva in a.kva:
                rows = [run_scenario(S, make_units(S, d, s), TrafoOnly(kva), cfg, cases=("none", "submeter"), p=p) for d, s in picks]
                print(f"{p:.2f} {kva:5.0f} | " + "  ".join(f"{r['alpha']:>3}/{r['submeter']:<3}" for r in rows), flush=True)
        print("days: " + ", ".join(str(d.date()) for d, _ in picks))
        print(f"-1 = over the limit already with no EV at all. Pick a size with no -1 and a submeter value below {MAX_EV}.")
        return
    if not a.trafo_kva:
        raise SystemExit("--trafo-kva is required (must match the archive in TWIN-REV)")
    a.out = os.path.abspath(a.out)
    be = (TwinRev(a.url) if a.backend == "twinrev" else Local(a.archive, a.trafo_kva) if a.backend == "local"
          else LocalDPsim(a.archive, a.trafo_kva, os.path.abspath(a.out + f".dpsim{os.getpid()}")))
    if a.backend == "twinrev":
        with urllib.request.urlopen(f"{a.url.rstrip('/')}/health", timeout=10):
            pass
    if a.cmd == "risk":
        be.kva = a.trafo_kva
        rows = run_risk(S, picks, be, cfg, a.levels, a.participation)
        tab = risk_table(rows)
        for r in tab:
            print(r)
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        json.dump(dict(trafo_kva=a.trafo_kva, backend=a.backend, homes=a.homes, ev_q=a.ev_q, limits=LIM, table=tab, rows=rows), open(a.out, "w"), indent=1)
        print("wrote", a.out)
        return
    rows, t0 = [], time.time()
    for p in a.participation:
        part = []
        for d, s in picks:
            r = run_scenario(S, make_units(S, d, s), be, cfg, p=p)
            part.append(r)
            rows.append(r)
            print(f"p={p:.2f} {r['day']} seed {s}: none {r['alpha']}  submeter {r['submeter']}  method {r['method']}  score {r['score']}  "
                  f"peak@{FIX_EV} {r['peaks_at_fix_pct']} peak score {r['peak_score']}  [{(time.time() - t0) / 60:.1f} min, {be.runs} power flows]", flush=True)
            os.makedirs(os.path.dirname(a.out), exist_ok=True)
            json.dump(dict(trafo_kva=a.trafo_kva, backend=a.backend, homes=a.homes, limits=LIM, scenarios=rows), open(a.out, "w"), indent=1)
        print(f"p={p:.2f} summary:", json.dumps(summary(part)), flush=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
