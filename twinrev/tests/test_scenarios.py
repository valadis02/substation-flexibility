"""Scenario construction on synthetic Austin-format data (no DPsim, no TWIN-REV needed).
    cd twinrev && python3 -m pytest -q tests
"""
import os, sys
import numpy as np
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "service"))
sys.path.insert(0, HERE)
import scenarios as SC
import grid as G
import make_synthetic_austin


@pytest.fixture(scope="module")
def S(tmp_path_factory):
    d = tmp_path_factory.mktemp("austin")
    make_synthetic_austin.main(str(d))
    return SC.load_site(str(d))


def test_units_fill_the_feeder(S):
    day = SC.extreme_days(S)["peak"]
    U = SC.units(S, day)
    assert len(U) == 55 and len({u for u, _, _ in U}) == 55
    assert [h for _, h, o in U[:25] if o == 0] == S["homes"]            # the real homes on the day come first
    assert all(o % 7 == 0 and o != 0 for _, _, o in U[25:])              # copies: same weekday, other weeks
    place = G.placement([u for u, _, _ in U])
    assert sorted(place.values()) == [f"lod_{i:02d}" for i in range(1, 56)]


def test_today_is_the_data(S):
    day = SC.extreme_days(S)["peak"]
    P, Q, info = SC.scenario(S, day)
    W = SC._day(S["W"], day)[S["homes"]].values - SC._day(S["solar"], day)[S["homes"]].values
    assert np.allclose(P[S["homes"]].values, W)
    assert info["added_ev"] == 0 and info["added_pv"] == 0 and info["units"] == 55


def test_more_evs_more_load_and_nested(S):
    day = SC.extreme_days(S)["peak"]
    P0, _, i0 = SC.scenario(S, day)
    P1, _, _ = SC.scenario(S, day, n_ev=i0["n_ev"] + 10)
    P2, _, _ = SC.scenario(S, day, n_ev=55)
    e0, e1, e2 = (p.sum().sum() for p in (P0, P1, P2))
    assert e0 < e1 < e2
    assert ((P2 - P1).values >= -1e-9).all()                             # seeded order: scenarios are nested


def test_pv_lowers_net_load_and_scale(S):
    day = SC.extreme_days(S)["pv"]
    P0, _, _ = SC.scenario(S, day)
    P1, _, _ = SC.scenario(S, day, n_pv=55)
    P2, _, _ = SC.scenario(S, day, n_pv=55, pv_scale=2.0)
    assert P1.sum(axis=1).min() < P0.sum(axis=1).min()
    assert P2.sum(axis=1).min() < P1.sum(axis=1).min()


def test_profile_rows_cover_every_load_point(S):
    day = SC.extreme_days(S)["peak"]
    P, Q, _ = SC.scenario(S, day, n_units=30)
    rows = G.profile_rows(P, Q, G.placement(list(P.columns)))
    assert len(rows) == 24 * 55 * 2
    lods_with_load = {r[1] for r in rows if r[4] == "active" and abs(r[5]) > 0}
    assert len(lods_with_load) == 30
    total_mw = sum(r[5] for r in rows if r[4] == "active" and r[0].hour == 18)
    assert total_mw == pytest.approx(P.iloc[18].sum() / 1000.0)
