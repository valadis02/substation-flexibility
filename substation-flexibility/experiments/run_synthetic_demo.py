"""Runs the pipeline on synthetic houses with known components and prints a summary. Use it to check the code after changes."""
import pandas as pd
from flexsub import Config, synthetic, pipeline, metrics

W, w, truth = synthetic.make(n_houses=8, days=75, seed=1)
cfg = Config()
days = pd.date_range("2026-09-01", "2026-09-08", freq="D", tz=cfg.tz)
res = pipeline.run(W, w, cfg, days)
R = res["baseline"].dropna(subset=["cal_lo"])
print("calibrated coverage:", round(metrics.coverage(R.actual, R.cal_lo, R.cal_hi), 3), "| interval score:", round(metrics.interval_score(R.actual, R.cal_lo, R.cal_hi), 3))
tt = truth["thermal"].copy(); tt.index = tt.index.tz_convert(cfg.tz)
th = res["thermal"].dropna()
print("thermal corr with truth:", round(float(th.corr(tt.reindex(th.index))), 3))
print(res["flexibility"].round(2).iloc[[3, 12, 18, 21]])
