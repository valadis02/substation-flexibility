import numpy as np
import pandas as pd
from flexsub import ev as ev_flex


def _T():
    return pd.DataFrame([dict(home="A", p=1.0, start_hour=18, win_end=28, energy_kwh=14.0, power_kw=7.0),
                         dict(home="B", p=0.5, start_hour=19, win_end=29, energy_kwh=6.6, power_kw=3.3)])


def test_envelope_energy_and_windows():
    E = ev_flex.envelope(_T())
    assert np.isclose(E.ev_kw.sum(), 14.0 + 0.5 * 6.6)          # expected energy is kept
    assert E.loc[18, "plugged"] == 1.0 and E.loc[29, "plugged"] == 0.0
    assert E.loc[18, "down_kw"] == 7.0                           # A can postpone its first hour


def test_plan_down_moves_energy_after_block():
    P, A = ev_flex.plan(_T(), (18, 21), "down")
    assert set(P.home) == {"A", "B"}
    assert np.allclose(A.after_kw.values[18:21], 0)              # nothing charges in the block
    assert np.isclose(A.after_kw.sum(), A.before_kw.sum())       # energy is moved, not lost
    assert A.after_kw.values[21:28].sum() > 0                    # rebound after the block


def test_plan_up_pulls_energy_into_block():
    P, A = ev_flex.plan(_T(), (23, 26), "up")
    assert A.change_kw.values[23:26].sum() > 0
    assert np.isclose(A.after_kw.sum(), A.before_kw.sum())


def test_stagger_lowers_rebound_peak():
    base = np.r_[np.full(21, 5.0), [8.0, 7.0, 3.0, 2.0, 2.0, 2.0, 2.0, 2.0], np.full(7, 3.0)]
    _, simple = ev_flex.plan(_T(), (18, 21), "down", base_kw=base, stagger=False)
    _, stag = ev_flex.plan(_T(), (18, 21), "down", base_kw=base, stagger=True)
    assert stag.total_after_kw.values[21:].max() < simple.total_after_kw.values[21:].max()
    assert np.isclose(stag.after_kw.sum(), stag.before_kw.sum())


def test_m5_envelope_includes_ev_and_m6_scales_it():
    """v0.10: EV sessions enter the M5 envelope; participation (M6) scales every column, EV included."""
    from flexsub import Config, flexibility
    cfg = Config(tz="UTC")
    idx = pd.date_range("2024-01-01", periods=24 * 10, freq="h", tz="UTC")
    D = pd.DataFrame({"actual": 2.0, "base": 0.5, "thermal": 0.5, "ev": 0.0, "shiftable": 0.5, "routine": 0.5}, index=idx)
    ev_on = (idx.hour >= 19) & (idx.hour < 21)
    D.loc[ev_on, "ev"] = 7.0; D.loc[ev_on, "actual"] += 7.0
    S = pd.DataFrame({"start": idx[(idx.hour == 19)], "hours": 2, "energy_kwh": 14.0, "power_kw": 7.0})
    D.attrs["ev_sessions"] = {"H1": S}
    F = flexibility.flexibility_by_hour(D, cfg)
    assert abs(F.loc[19, "down_ev_kw"] - 7.0) < 1e-9 and F.loc[20, "down_ev_kw"] > 6.9   # charging with room later
    assert F.loc[22, "up_ev_kw"] > 0 and F.loc[15, "up_ev_kw"] == 0                      # plugged after, not before
    assert np.allclose(F.down_kw, F.down_ev_kw + 1.0)                                      # 0.5 thermal + 0.5 appliances
    G = flexibility.apply_participation(F, 0.25)
    for c in ("down_kw", "down_ev_kw", "up_ev_kw", "up_kw"):
        assert np.allclose(G[c], 0.25 * F[c])
