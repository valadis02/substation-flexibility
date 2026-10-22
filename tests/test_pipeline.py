import functools
import numpy as np
import pandas as pd
from flexsub import Config, synthetic, pipeline, metrics


@functools.lru_cache(maxsize=1)
def _run():
    W, w, truth = synthetic.make(n_houses=8, days=75, seed=1)
    cfg = Config(gbm=dict(max_iter=80, learning_rate=0.1, max_leaf_nodes=15, min_samples_leaf=20, l2_regularization=1.0, random_state=0))
    days = pd.date_range("2026-09-01", "2026-09-08", freq="D", tz=cfg.tz)
    return W, truth, cfg, pipeline.run(W, w, cfg, days)


def test_decomposition_sums_to_actual():
    _, _, _, res = _run()
    D = res["decomposition"]
    parts = D[["base", "thermal", "ev_shift", "ev_meal", "routine"]].sum(axis=1)
    assert np.allclose(parts, D["actual"], atol=1e-6)
    assert (D[["base", "thermal", "ev_shift", "ev_meal", "routine"]] >= -1e-9).all().all()


def test_flexibility_table_shape_and_signs():
    _, _, _, res = _run()
    F = res["flexibility"]
    assert len(F) == 24 and (F[["down_kw", "up_kw"]] >= 0).all().all()
    assert (res["flexibility_participation"]["down_kw"] <= F["down_kw"] + 1e-12).all()


def test_baseline_band_is_valid():
    _, _, _, res = _run()
    R = res["baseline"].dropna(subset=["cal_lo"])
    assert (R.cal_hi >= R.cal_lo).all()
    assert 0.0 <= metrics.coverage(R.actual, R.cal_lo, R.cal_hi) <= 1.0


def test_thermal_tracks_true_thermal_on_synthetic():
    """Sanity check only: with known ground truth the thermal part should correlate with the true thermal load."""
    W, truth, cfg, res = _run()
    th = res["thermal"].dropna()
    tt = truth["thermal"].copy(); tt.index = tt.index.tz_convert(cfg.tz)
    assert np.corrcoef(th, tt.reindex(th.index))[0, 1] > 0.5


def test_splits_disjoint():
    import numpy as np, pandas as pd
    from flexsub import splits
    idx = pd.date_range("2024-01-01", periods=1000, freq="h", tz="UTC")
    W = pd.DataFrame(np.random.default_rng(0).random((1000, 6)), index=idx, columns=[f"H{i}" for i in range(6)])
    s = splits.make({"x": W}, {"x": 2}, exclude={"x": ["H5"]})
    D, F = splits.development(W, "x", s), splits.final_test(W, "x", s)
    held = s["datasets"]["x"]["held_out_homes"]
    assert not set(held) & set(D.columns) and "H5" not in F.columns
    common = [h for h in D.columns]
    assert not (D[common].notna() & F[common].notna()).any().any()   # no hour of a dev home in both views
    assert abs(D[common].notna().mean().mean() - 0.8) < 0.01
