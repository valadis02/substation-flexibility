# EV capacity experiment

How many EVs fit on the feeder before the first limit breaks: (a) no flexibility, (b) oracle, (c) the flexibility method.
The rules are at the top of `ev_capacity.py`; conclusions go in `RESULTS.md`.

Runs need the processed Pecan Street Austin data (local only) with `weather.csv.gz`, and `pip install scipy`.
Power flows go through `POST /power-flow` of the `twinrev-scenarios` service (TWIN-REV + DPsim). `lv_bfs.py` (`--backend local`)
is an offline power flow for tests only.

Output: `results/ev_capacity.json` (capacities and aggregate metrics, no household data).

Runs:
- `ev_q_check.py`: EV detection against the car circuits for several reference quantiles.
- `ev_capacity.py risk --ev-q 0.25`: limits broken at fixed numbers of EVs. `--ev-q` tests a setting without changing the method.
- `ev_capacity.py pilot`: EVs that fit before the first broken limit. `--site-dir ../data/synthetic_55` uses the synthetic set.
