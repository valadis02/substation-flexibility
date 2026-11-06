"""EV capacity experiment on synthetic data (no TWIN-REV): the rules that keep the comparison honest.
    cd twinrev && python3 -m pytest -q tests
"""
import os, sys
import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "experiments"))
sys.path.insert(0, HERE)
import ev_capacity as EC
import make_synthetic_austin


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    d = root / "processed" / EC.DATASET
    make_synthetic_austin.main(str(d))
    idx = pd.date_range("2018-01-01", "2019-01-02", freq="1h", tz="UTC", name="timestamp")
    doy, h = idx.dayofyear.values, idx.tz_convert(EC.TZ).hour.values
    t = 20 + 9 * np.sin(2 * np.pi * (doy - 110) / 365) + 6 * np.sin(2 * np.pi * (h - 9) / 24)
    pd.DataFrame(dict(temp=t, rh=50.0, cloud=30.0, rad=0.0, is_day=1), index=idx).to_csv(d / "weather.csv.gz")
    return EC.load_site(str(root), "all")


@pytest.fixture(scope="module")
def U(site):
    return EC.make_units(site, EC.study_days(site, 1)[0][0], 0)


def test_cars_are_nested_and_counted(site, U):
    idx = EC.study_index(U["day"])
    a, b = EC.series(site, U, 10, idx), EC.series(site, U, 30, idx)
    assert (b["cons"].sum().sum() >= a["cons"].sum().sum() - 1e-6)
    assert set(U["order"][:10]) <= set(U["order"][:30])
    assert (EC.series(site, U, 0, idx)["ev"].values == 0).all()


def _flex(site, U, n):
    cfg = EC.config()
    X = EC.series(site, U, n, EC.study_index(U["day"]))
    return X, EC.TrueFlex(X["ev"], X["flex"], EC.true_up_cap(site, U, n, cfg), cfg)


def test_energy_is_conserved(site, U):
    X, tf = _flex(site, U, 40)
    net = (X["cons"] - X["solar"]).sum(axis=1).values
    add = tf.apply(tf.min_peak(net))
    assert abs(add.values.sum()) < 1e-3
    assert (X["ev"].values + add.values).sum() > -1e-6


def test_overestimate_cannot_beat_the_physical_bound(site, U):
    X, tf = _flex(site, U, 40)
    net = (X["cons"] - X["solar"]).sum(axis=1).values
    best = (net + tf.apply(tf.min_peak(net)).sum(axis=1).values).max()
    cfg = EC.config()
    big = 1e4 * np.ones(24)
    want = EC.plan(net, dict(down_ev=big, up_ev=big, down_ne=big, up_ne=big), cfg)     # absurdly optimistic envelope
    got = (net + tf.apply(tf.deliver(want)).sum(axis=1).values).max()
    assert got >= best - 1e-3
    no = np.zeros(24)
    zero = EC.plan(net, dict(down_ev=no, up_ev=no, down_ne=no, up_ne=no), cfg)
    assert np.allclose(zero, 0)
    assert abs((net + tf.apply(tf.deliver(zero)).sum(axis=1).values).max() - net.max()) < 1e-3


def test_a_plan_with_the_true_envelope_gets_near_the_bound(site, U):
    X, tf = _flex(site, U, 40)
    net = (X["cons"] - X["solar"]).sum(axis=1).values
    best = (net + tf.apply(tf.min_peak(net)).sum(axis=1).values).max()
    env = dict(down_ev=X["ev"].sum(axis=1).values, up_ev=20 * X["ev"].max().sum() * np.ones(24), down_ne=tf.F, up_ne=tf.cap)
    got = (net + tf.apply(tf.deliver(EC.plan(net, env, EC.config()))).sum(axis=1).values).max()
    assert got < net.max() and got <= best + 0.15 * (net.max() - best)


def test_the_bound_lowers_the_peak(site, U):
    X, tf = _flex(site, U, 40)
    net = (X["cons"] - X["solar"]).sum(axis=1).values
    assert (net + tf.apply(tf.min_peak(net)).sum(axis=1).values).max() < net.max()


def test_non_responders_keep_their_habits(site, U):
    X = EC.series(site, U, 40, EC.study_index(U["day"]))
    P, _, _ = EC.profiles(site, U, 40, "submeter", EC.config(), p=0.25)
    who = set(U["resp"][:14])
    rest = [u for u in P.columns if u not in who]
    assert np.allclose(P[rest].values, (X["cons"] - X["solar"])[rest].values)
    P1, _, _ = EC.profiles(site, U, 40, "submeter", EC.config(), p=1.0)
    assert P1.sum(axis=1).max() <= P.sum(axis=1).max() + 1e-3


def test_submetering_envelope_lowers_the_peak(site, U):
    P0, _, _ = EC.profiles(site, U, 40, "none", EC.config())
    P1, _, _ = EC.profiles(site, U, 40, "submeter", EC.config(), p=0.5)
    assert P1.sum(axis=1).max() < P0.sum(axis=1).max()


def test_capacity_search():
    for true_cap in (-1, 0, 7, 54, EC.MAX_EV):
        cap, _ = EC.capacity(lambda n: ["x"] if n > true_cap else [])
        assert cap == true_cap
