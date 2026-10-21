# substation-flexibility (`flexsub`)

Estimates the flexibility of a **substation** (a group of households) from **aggregate hourly smart-meter data, weather and calendar only**: no sub-metering, no demand-response signal, no NILM.

**Status: experimental. Not validated against ground truth.** The test plan is in `docs/test_plan.pdf`.

## Problem
A DSO deciding between reinforcement and flexibility needs, per area and hour, how many kW can go down or up, for how long, and with what confidence. Existing work needs sub-metering (Ponocko & Milanovic 2018; Wang et al., NREL), a DR signal, or covers only thermal load and only reductions (Albert & Rajagopal 2015; Dyson et al. 2014).

## Method (modules)
| Module | File | What it does |
|---|---|---|
| M1 baseline | `flexsub/baseline.py` | quantile regression (5/50/95%) + conformal calibration, rolling-origin |
| M2 thermal | `flexsub/thermal.py` | prediction with actual weather minus prediction with neutral weather (20 C), leave-one-day-out |
| M3 decomposition | `flexsub/decompose.py` | base / thermal / shiftable events / meal events / routine; parts sum to the load |
| M4 flexibility | `flexsub/flexibility.py` | down = shiftable load running; up = energy movable from +-3 h, capped by observed extra draw |
| M5 participation | `flexsub/flexibility.py` | scenario scaling (default 30%) |
| M6 substation | `flexsub/pipeline.py` | aggregate first, then apply M1-M5 |

All parameters are in `flexsub/config.py`. Many are assumptions (0.4 kW threshold, meal hours, +-3 h window, 30% participation); the tests are meant to show which ones must change.

## Quick start
```bash
pip install -r requirements.txt
pip install -e .
pytest -q                                  # synthetic sanity tests (~15 s)
python experiments/run_synthetic_demo.py
python scripts/run_pipeline.py --data "data/raw/*.csv" --weather data/weather.csv --start 2026-09-20 --end 2026-10-15
```

## Layout
`flexsub/` code · `tests/` synthetic tests · `experiments/` one script per test of the plan · `docs/` plan and experiment log · `data/` local data only (not committed) · `legacy/` first exploration scripts.

## License
Not chosen yet (decide with the lab before publishing).
