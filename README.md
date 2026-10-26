# substation-flexibility (`flexsub`)

Estimates the flexibility of a **substation** (a group of households) from **hourly smart-meter data of each home,
weather and calendar only**: no sub-metering, no demand-response signal, no NILM.

**Status: v0.10 (EV is one flexible category inside a single envelope; participation applies to all of it, see T12), research code.** All results so far are on development data (`data/splits.json`); the locked final test
(last 20% of time per home + held-out homes) is run once the method is frozen. Full record of experiments and
conclusions: `experiments/RESULTS.md`; one line per method version: `docs/experiment_log.md`; sources:
`docs/references.md`.

## Problem
A DSO deciding between reinforcement and flexibility needs, per area and hour, how many kW can go down or up, for how
long, and with what confidence. Existing methods need sub-metering in part of the homes (Ponocko & Milanovic 2017/2018:
20-50% in their first paper, 5% claimed in the second, not reproduced here), a DR signal, or cover only thermal load.

## Method (v0.10)
| Module | File | What it does |
|---|---|---|
| M1 baseline | `flexsub/baseline.py` | quantile gradient boosting (5/50/95%), conformal calibration, rolling origin; seasonal features, no hand-set temperatures |
| M2 weather-dependent load | `flexsub/thermal_dd.py`, `thermal.py` | degree-day component relative to balance points estimated from the substation's own data; kept only if significant (Newey-West t > 2) |
| M3 decomposition per home | `flexsub/decompose.py`, `shiftable.py` | base (the home's 4 quietest hours), appliance events (after removing its weather load: load above the 60th percentile of the same hour over the previous 14 days by > 3 robust SD, runs <= 3 h; washing machine, dryer, dishwasher, resistive water heater) and routine; parts allocated base -> weather -> EV -> appliances -> routine, so they add up to the load |
| M4 EV charging | `flexsub/ev.py` | EV homes and sessions from hourly data (excess > 2.5 kW, any length, flat charger power); EV hours are kept out of the appliance events |
| M5 flexibility envelope | `flexsub/flexibility.py` | one envelope, down / up per hour, for weather + appliances + EV. Weather and appliances: short-cycle rule (window, request duration, cap = product definitions). EV: its sessions, plugged 10 h from the start; down = charging with room later, up = plugged cars not charging |
| M6 participation | `flexsub/flexibility.py`, `pipeline.py` | every column, EV included, x enrolment x response; default 1.0 (technical maximum) |

`pipeline.ev_day_ahead` (day-ahead EV scenarios and a per-home plan with valley filling) is a validation tool (T9d), not
part of the method's output.

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
| T8 real vs estimated, homes without EV (REFIT 13, Pecan Austin 16, New York 14 homes; v0.9 rerun) | flexible-load AWFE p90 0.24-0.30 vs zero 0.32-1.00; better than a Ponocko-style ANN with 20% sub-metering (hourly P only) |
| T9-T9d EV (now M4) | Austin 4/4 EV homes, New York 1/3, 0 false; flexible AWFE Austin 0.325 -> 0.293; day-ahead reduce plan predicted/real 0.87 (Austin), 0.79 (New York); new peak after a request 27% -> 0% of days with staggering |
| T12 one envelope incl. EV (v0.10) | envelope vs true, groups with EV homes: Austin down est./true 0.79 -> 0.84, up 0.86 -> 0.98; New York down 0.79 -> 0.82, up 0.87 -> 0.98; no-EV datasets unchanged; hourly flexible AWFE unchanged; at participation 0.1 v0.9 overstated up x2.0, v0.10 0.98 |

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
