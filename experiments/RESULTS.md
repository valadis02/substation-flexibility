# Experiments and conclusions

One section per test of the plan (`docs/test_plan.pdf`). Each section: question, setup, results, conclusions,
caveats, open items. Numbers come from the files in `experiments/results/`; every change to the method that a
result triggered is in `docs/experiment_log.md`. Everything below is on the **development split** unless stated;
the final split (`data/splits.json`, `data/processed/lcl/groups_meta.json`) has not been opened.

Method version at the time of each test is given in brackets.

## Design principle: data-driven parameters

The method should adapt to each substation with as few hand-set numbers as possible. Anything made automatic is
estimated only from the same substation's past data (never future data, never ground truth). Whatever stays fixed
is checked in T4: if results are insensitive we say so; if not, it has to become data-driven.

| Parameter | Now | How it becomes data-driven | Test |
|---|---|---|---|
| Neutral temperature, CDD/HDD bases | 20 / 24 / 16 C | heating and cooling balance points estimated from the substation's own load vs temperature | T2 |
| Meal hours | 12-15, 18-22 | the substation's own daily profile, or HETUS by country | T3 |
| Event threshold | 0.4 kW | relative to the substation's load distribution (0.4 kW means nothing at 500 homes) | T3 |
| Base-load hours | 02-06 | hours of minimum load in the data | T3 |
| Shift window | +-3 h | tolerance of delay from time-use and wet-appliance pilot studies | T3/T4 |
| Power cap | 90th percentile | stays a parameter; T4 checks the sensitivity | T4 |
| Calibration window | 14 days | Adaptive Conformal Inference adjusts it online | T1 (open) |
| Target coverage | 0.90 | user choice (a DSO may want 0.95); not a method parameter | - |
| Enrolment, response rate | 1.0 / scenarios | DSO input (enrolment); estimated from past events (response) | T6 |

---

## T1 - Baseline band (M1) [v0.2]

**Question.** Does the M1 band (quantile gradient boosting + conformal calibration) keep its nominal 90% coverage on
real data, and how wide is it for substations of different size?

**Setup.**
- Groups of N homes summed into a "substation" (an hour counts only if all members have data; LCL: >= 90% of members,
  sum scaled). Several random groups per N (fixed seed), median over groups reported.
- Data: REFIT (N = 1, 2, 5, 10, 14), UK-DALE (1, 2), Plegma (1, 2, 5), LCL Std-tariff homes (50, 150, 500).
- Rolling origin: each day predicted with data known at midnight; models refit every 7 days (method: daily);
  calibration window 14 days; first 42 days of each group are warm-up.
- Observed weather (ERA5 / homes' sensors), not forecast weather.
- Script: `experiments/t1_baseline.py`; table: `experiments/results/t1_dev.md`.

**Results** (median over groups; width, interval score and nMAE relative to mean load):

| Dataset | N | Coverage raw | Coverage calibrated | Band width | nMAE |
|---|---|---|---|---|---|
| REFIT | 1 | 0.79 | 0.894 | 1.35 | 0.35 |
| REFIT | 2 | 0.81 | 0.895 | 1.12 | 0.27 |
| REFIT | 5 | 0.76 | 0.895 | 0.98 | 0.25 |
| REFIT | 10 | 0.77 | 0.898 | 0.75 | 0.18 |
| REFIT | 14 | 0.76 | 0.902 | 0.65 | 0.16 |
| UK-DALE | 1 / 2 | 0.73 / 0.74 | 0.900 / 0.891 | 1.35 / 1.09 | 0.35 / 0.28 |
| Plegma | 1 / 2 / 5 | 0.82 / 0.77 / 0.76 | 0.896 / 0.895 / 0.892 | 2.55 / 2.01 / 1.38 | 0.68 / 0.55 / 0.36 |
| LCL | 50 | 0.79 | 0.899 | 0.41 | 0.095 |
| LCL | 150 | 0.78 | 0.896 | 0.30 | 0.067 |
| LCL | 500 | 0.77 | 0.898 | 0.23 | 0.051 |

**Conclusions.**
1. Calibration works: 0.89-0.90 coverage for every dataset and size, against 0.73-0.82 without it.
2. The band narrows with size but more slowly than for independent homes: x10 homes (50 -> 500) gives x0.56 width,
   not x0.32. A common-mode part (weather, day type, shared habits) does not average out.
3. At a typical secondary substation (~120-150 connections in Rome and Vienna, see `docs/references.md` section 6)
   the band is about +-15% of load and the median error about 7%.
4. What this means for flexibility: an average realised response of 50 W per home (LCL dynamic tariff) is ~12% of
   load at N = 500 if every home responds, ~2.5% at 20% enrolment. Responses of that size cannot be verified hour
   by hour at secondary-substation scale; only on average over many events. Estimating the potential does not
   depend on this (it comes from M2-M4), verifying a realised response does.
5. Plegma is about twice as hard as REFIT at equal N (AC-driven load and only a few months of history per home;
   T1 cannot separate the two).

**Caveats.** Observed weather makes the results optimistic (Haben et al. 2021). Plegma and UK-DALE homes overlap
little in time, so their larger groups were mostly skipped (fewer than 60 common days). "Guaranteed" coverage is not
yet justified: split conformal assumes exchangeable data.

**Open items (do not block T2).**
- Forecast weather instead of observed (historical-forecast archive covers only recent years, so Plegma only).
- Adaptive Conformal Inference (Gibbs & Candes 2021) to support a coverage guarantee under drift.
- Daily refit as in the method (7-day refit used for speed).

---

## T2 - Thermal part (M2) [v0.3, first run]

**Question.** Does the thermal part estimated from the aggregate and the weather (prediction with actual weather
minus prediction with a neutral temperature T0) match the measured AC load, and which T0 is right?

**Setup.** Plegma development homes (8 with AC, 2 without as negative control), one home at a time (Plegma homes
overlap too little in time for groups). Out-of-sample by leave-one-week-out. T0 swept 16-26 C in 0.5 C steps. Two
model variants: "full" (method features, incl. load lags) and "nolag" (calendar + weather only). Balance point from a
one-break V fit of daily mean load on daily mean temperature. Scripts: `experiments/t2_thermal.py`,
`experiments/t2_diag_clip.py`; tables: `experiments/results/t2_dev.md`.

**Results** (medians over AC homes, full model, T0 = 20):

| Season | Hourly corr. | Daily corr. | Thermal share error | Daily energy error / mean daily AC |
|---|---|---|---|---|
| all | 0.34 | 0.62 | -0.03 | 1.02 |
| cooling (May-Sep) | 0.31 | 0.61 | -0.11 | 0.89 |
| heating (Nov-Mar) | -0.02 | -0.07 | +0.01 | 1.59 |

- Homes differ a lot: daily correlation 0.6-0.76 in five homes (H02, H04, H05, H11, H12), 0.07-0.2 or negative in three.
- T0 hardly matters: every metric changes by about 0.01 across 16-26 C.
- Negative control: homes without AC get a thermal share of 9-15% (8.7% and 15.2% before clipping, 11-19% after).
- Clipping the hourly estimate at 0 adds 1-5 points of thermal share (positive bias from clipping noise).
- Per-home balance points mostly hit the edges of the search range (12 or 28 C): not identifiable per home.
- The "nolag" variant is not better (daily corr. 0.46-0.57).

**Conclusions.**
1. At single-home level with a few months of history, M2 tracks AC only roughly in summer (daily corr. ~0.6) and
   fails in winter. The daily energy error is about the size of the AC load itself.
2. The estimate is dominated by confounding, not by T0: with less than a year per home, temperature moves together with
   season, so anything seasonal (water heating, lighting, holidays, occupancy) is counted as thermal. That is why
   homes without AC get 9-15% and why T0 has almost no effect.
3. The question "which T0 is optimal" cannot be answered until the confounding is removed; it is not answered yet.
4. Clipping at 0 must go (or be applied only after aggregation over hours/days).

**Changes to test next (T2 v2).**
- Seasonality features kept fixed in the counterfactual (day of year, daylight hours), so the temperature effect is
  identified from hot vs cool days within the same season.
- No clipping of the hourly estimate.
- Two balance points (heating, cooling) estimated from the substation's data.
- Groups instead of single homes where Plegma allows (summer 2023, when most homes overlap), since a substation is an
  aggregate; and REFIT electric heaters for a winter check.
- Pecan Street (several years, hundreds of homes with AC) is the proper test once access is granted.
