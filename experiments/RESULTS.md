# Experiments and conclusions

One section per test of the plan (`docs/test_plan.pdf`). Each section: question, setup, results, conclusions,
caveats, open items. Numbers come from the files in `experiments/results/`; every change to the method that a
result triggered is in `docs/experiment_log.md`. Everything below is on the **development split** unless stated;
the final split (`data/splits.json`, `data/processed/lcl/groups_meta.json`) has not been opened.

Method version at the time of each test is given in brackets.

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

## T2 - Thermal part (M2) [planned, v0.3]

**Question.** Does the thermal part estimated from the aggregate and the weather (prediction with actual weather
minus prediction with neutral 20 C weather) match the measured AC / heating load?

**Setup (planned).**
- Ground truth: Plegma `ac_*` circuits (11 homes; split units, used for cooling and heating); REFIT electric
  heaters (houses 1, 9, 16) as a small UK check.
- Per home (N = 1) and for the groups Plegma allows (N = 2-5); M2 run leave-one-day-out on development data.
- Metrics: hourly and daily correlation with measured AC; daily energy error; share of thermal load in total vs
  true share (AWFE p90, as Ponocko & Milanovic); separately for cooling and heating months; peak-hour error.

**What we expect.**
- Good agreement on hot days and at the daily level (AC is clearly temperature-driven); weaker hour by hour
  (AC switching also depends on occupancy).
- Bias in winter: other weather-sensitive loads (boilers, lighting) will be counted as thermal.
- Mild days (few degrees from 20 C): thermal close to zero in both estimate and truth.
- If daily correlation is high but the level is biased, the fix is in the counterfactual (neutral temperature,
  CDD/HDD bases); if correlation is low, the model does not isolate weather and M2 needs rethinking.
