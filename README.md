# substation-flexibility (`flexsub`)

Estimates the flexibility of a **substation** (a group of households) from **hourly smart-meter data of each home,
weather and calendar only**: no sub-metering, no demand-response signal, no NILM.

**Status: v0.9 (v0.8 + EV charging as flexible load and a day-ahead EV charging plan, see T9-T9c), research code.** All results so far are on development data (`data/splits.json`); the locked final test
(last 20% of time per home + held-out homes) is run once the method is frozen. Full record of experiments and
conclusions: `experiments/RESULTS.md`; one line per method version: `docs/experiment_log.md`; sources:
`docs/references.md`.

## Problem
A DSO deciding between reinforcement and flexibility needs, per area and hour, how many kW can go down or up, for how
long, and with what confidence. Existing methods need sub-metering in part of the homes (Ponocko & Milanovic 2017/2018:
20-50% in their first paper, 5% claimed in the second, not reproduced here), a DR signal, or cover only thermal load.

## Method (v0.9)
| Module | File | What it does |
|---|---|---|
| M1 baseline | `flexsub/baseline.py` | quantile gradient boosting (5/50/95%), conformal calibration, rolling origin; seasonal features, no hand-set temperatures |
| M2 weather-dependent load | `flexsub/thermal_dd.py`, `thermal.py` | degree-day component relative to balance points estimated from the substation's own data; kept only if significant (Newey-West t > 2) |
| M3 shiftable load | `flexsub/shiftable.py`, `decompose.py` | per home, after removing its weather load: load above the 60th percentile of the same hour over the previous 14 days by > 3 robust SD, runs <= 3 h |
| M4 flexibility envelope | `flexsub/flexibility.py` | down / up per hour; window, request duration and cap are user-facing product definitions |
| M5 participation | `flexsub/flexibility.py`, `pipeline.py` | default 1.0 (technical maximum); scenarios = enrolment x response, per substation |
| M6 EV charging | `flexsub/ev.py`, `pipeline.ev_day_ahead` | EV homes and sessions from hourly data (excess > 2.5 kW, flat charger power); day-ahead scenarios from the last 14 days; per-home plan for a DSO request (reduce / increase), rebound spread by valley filling. Total flexibility = M4 + M6 |

Parameters: `flexsub/config.py`. The remaining fixed values sit in flat regions of the sensitivity tests (T3 v3, T4)
or are product definitions.

## Main results (development data)
| Test | Result |
|---|---|
| T1 baseline band (LCL 50/150/500 homes) | coverage ~0.90 at target 0.90; width 0.41 / 0.30 / 0.23 of load |
| T2 weather-dependent load | share ratio est./true Austin 0.89, Ithaca 0.98; false weather load cut by the significance gate (REFIT 0.21 -> 0.02) |
| T3 shiftable load | AWFE skill vs zero 0.17-0.27 on real data without any sub-metering |
| T4 envelope | down est./true 0.58-0.85, up 0.99-1.23; settings change size, not accuracy |
| T7 vs Ponocko & Milanovic (CREST, 1,000 homes) | wet appliances: ours (0% sub-metering) 0.087 AWFE p90 vs their 5% 0.115 and 10% 0.080; their 5% headline (<0.1) not reproduced (0.26-0.33) |
| T8 real vs estimated (REFIT 13, Pecan Austin 16, New York 15 homes) | flexible-load AWFE p90 0.24-0.32 vs zero 0.32-1.00; better than a Ponocko-style ANN with 20% sub-metering (hourly P only) |
| T9-T9d EV (M6) | Austin 4/4 EV homes, New York 1/3, 0 false; flexible AWFE Austin 0.325 -> 0.293; day-ahead reduce plan predicted/real 0.87 (Austin), 0.79 (New York); new peak after a request 27% -> 0% of days with staggering |

## Quick start
```bash
pip install -r requirements.txt
pip install -e .
pytest -q                                            # synthetic sanity tests (~15 s)
python scripts/run_pipeline.py --help                # run the method on your own hourly data + weather
python experiments/t1_baseline.py refit             # any experiment; see the header of each script
```

## Data
`data/processed/` holds the prepared public datasets (REFIT, UK-DALE, Plegma, LCL groups); preparation scripts are in
`scripts/` and sources/licences in `data/README.md`. Pecan Street data is used locally only (its licence forbids
redistribution). CREST synthetic homes are regenerated with `scripts/crest_generate.py` (not committed).

## Layout
`flexsub/` code · `tests/` synthetic tests · `experiments/` one script per test + `RESULTS.md` · `docs/` test plan,
experiment log, references · `data/` processed public data and splits · `legacy/` first exploration scripts.

## License
Not chosen yet (decide with the lab before publishing).
