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

---

## T2 v2 - Thermal part after fixes [v0.4]

**What changed.** Seasonal features (day of year, day length) kept fixed in the counterfactual; no clipping of the
hourly estimate; counterfactual from data = temperature clipped to heating/cooling balance points (Th, Tc) fitted on
the training fold (load and temperature only), compared with fixed T0 16-26 C. New ground truth: Pecan Street
(local only): Austin 20 homes 2018, Ithaca 20 homes May-Oct 2019, San Diego 19 homes (one year each). Truth for Pecan
= AC + furnace + electric heater circuits. Script: `experiments/t2_thermal_v2.py`; tables:
`experiments/results/t2_dev.md`.

**Results** (seasonal model, counterfactual from balance points, all seasons; groups = all development homes summed):

| Unit | Daily corr. | Hourly corr. | Thermal share est. / true | Daily energy error / true |
|---|---|---|---|---|
| Pecan Austin, group of 20 | **0.98** | 0.85 (summer 0.95) | 0.37 / 0.52 | 0.30 |
| Pecan Austin, single homes (median) | 0.95 | 0.86 | 0.40 / 0.55 | 0.34 |
| Pecan Ithaca, group of 20 (summer only) | 0.80 | 0.74 | 0.06 / 0.15 | 0.62 |
| Pecan Ithaca, single homes | 0.68 | 0.52 | 0.09 / 0.23 | 0.82 |
| Pecan San Diego, single homes | 0.72 | 0.44 | 0.09 / 0.24 | 0.78 |
| Plegma, group (>= 6 homes) | 0.90 | 0.68 | 0.09 / 0.15 | 0.48 |
| Plegma, single homes | 0.53 (0.63 with T0=20) | 0.23-0.36 | 0.07 / 0.14 | 1.16 |
| REFIT, homes with electric heaters | 0.26 | 0.03 | 0.02 / 0.06 | 0.98 |
| Controls (no AC/heater circuit): REFIT / Plegma | - | - | 0.01 / 0.10 | - |

Balance points from the data (groups): Austin Th 11 / Tc 19.5 C; Ithaca Tc 21 C; Plegma (Athens) Th 10 / Tc 26 C;
single homes San Diego median 13 / 18.5 C; REFIT heater homes Th 14.5-18 C.

Fixed T0 sweep (Pecan): results flat for T0 = 16-20 C and worse above ~20.5 C (daily error x1.5 at 23 C, x2-3 at
26 C). The data-driven band is as good as the best fixed T0, slightly better in Austin.

**Conclusions.**
1. The thermal part is clearly identifiable where it is large and the data cover a full season: Austin daily
   correlation 0.95-0.98. Aggregation helps a lot (Plegma 0.53 -> 0.90, Ithaca 0.68 -> 0.80).
2. **Systematic underestimation everywhere**: the estimated thermal share is 40-70% of the true one (Austin 0.37 vs
   0.52, Ithaca 0.06 vs 0.15, San Diego 0.09 vs 0.24, Plegma 0.09 vs 0.15). Most likely cause: a tree model cannot
   extrapolate, so for a July day in Texas at 20 C (never seen) it predicts the lowest-temperature load it has seen,
   which still contains AC. This is now the main weakness of M2.
3. Neutral temperature: with enough thermal signal it matters, but only above ~20 C; below that the result is flat.
   Setting it from the data (balance points) works at least as well as any fixed value, which removes one hand-set
   number. Athens households start cooling at a higher daily mean temperature (26 C) than the US homes (19.5-21 C).
4. Seasonal features changed little; the remaining false positives in Plegma controls (~10%) are most likely other
   weather-sensitive loads (fridge, water heater, fans), which M2 counts as "thermal" by definition. M2 estimates the
   weather-driven load, a superset of AC/heating; only the AC/heating part is flexible.
5. UK electric heaters are too small and irregular (6% of load) to be found from the aggregate (daily corr. 0.26).

**Next (T2 v3).** A counterfactual that can extrapolate: explicit degree-day terms (CDD/HDD above/below the fitted
balance points, by hour of day) estimated jointly with the boosting model on the residual, or a monotone/linear
thermal component; check that the share bias disappears on Austin and Ithaca groups.

---

## T2 v3 - Thermal part that can extrapolate [v0.5]

**What changed.** Four M2 variants on the same units and folds (leave-one-4-week-block-out, balance points from the
training blocks): `gbm_v2` (v0.4), `gbm_nolag` (same without load-history features), `dd_linear` (thermal = explicit
degree-day component above/below the balance points, slopes by 3-hour block, on top of an hour x day-type profile and
annual harmonics; ridge), `dd_hybrid` (same degree-day component, boosting for the rest). Module
`flexsub/thermal_dd.py`; script `experiments/t2_thermal_v3.py`; metrics in `outputs/t2/v3_metrics_*.csv`.

**Results** (share ratio = estimated / true thermal energy, target 1; groups):

| Group | gbm_v2 | gbm_nolag | dd_linear | dd_hybrid | Daily corr. (dd_linear) | Daily error (v2 -> dd_linear) |
|---|---|---|---|---|---|---|
| Pecan Austin (20 homes) | 0.70 | 0.82 | **0.89** | 0.87 | 0.98 | 0.30 -> 0.16 |
| Pecan Ithaca (20 homes, summer) | 0.42 | 0.68 | **0.98** | 0.82 | 0.83 | 0.59 -> 0.56 |
| Plegma (>= 6 homes) | 0.60 | 0.84 | 1.32 | 1.30 | 0.94 | 0.47 -> 0.51 |
| REFIT (14 homes; heaters in 3) | 1.82 | 3.72 | 13.3 | 10.8 | 0.25 | - |

Single homes (median share ratio, dd_linear vs v2): Austin 0.84 vs 0.67, San Diego 0.93 vs 0.37, Ithaca 1.23 vs
0.35 (unstable: half a year per home, ratios from 0.5 to 11), Plegma 2.5 vs 0.5.

Rejected: shrinking the band by 1-2 C fixed Austin (ratio 1.01) but made Plegma worse (1.5-1.7) - a hand-set number
that does not transfer.

**Conclusions.**
1. The underestimation was the tree model's inability to extrapolate: an explicit degree-day component removes most
   of it where the thermal load is real and large (Austin 0.70 -> 0.89, Ithaca 0.42 -> 0.98, San Diego homes
   0.37 -> 0.93) and halves the daily energy error in Austin, with the same daily correlation.
2. Adopted as M2 in v0.5 (`cfg.thermal_model = "dd_linear"`, `thermal.thermal_dd_loo`); `gbm` kept as an option.
3. It needs enough data: on single homes with half a year it is unstable, and it overestimates where the thermal load
   is small relative to everything else (Plegma 1.3, REFIT heaters). At group level, which is the target, it is stable
   where the thermal signal is real.
4. Plegma overestimation (1.3): checked whether water heaters and fridges explain it - they do not (their daily
   energy does not vary with temperature in these homes; slope ~0). The excess grows with temperature (correlation
   0.40), so the likely cause is weather-driven load outside the metered circuits (fans, unmetered AC units,
   occupancy on hot days). Plegma meters only selected appliances, so "true AC" is a lower bound there.
5. UK electric heaters (REFIT) cannot be estimated from the aggregate: 6% of energy, portable, irregular; every
   variant fails (daily corr. <= 0.26). This is a limit of the data, not of one model: small, irregular, weather-
   linked loads are inside the noise of the aggregate.

**Answers to the open points.**
- Point 5 (false "thermal" in homes without AC): M2 estimates the weather-driven load, which is the right quantity
  for a DSO (it is what changes with weather) but is larger than the flexible AC/heating part. What can be done:
  (a) state the definition explicitly; (b) use the DSO's or census data on AC / electric-heating ownership as a prior
  (no AC in the area -> thermal flexibility ~0); (c) report thermal flexibility only where the degree-day response is
  significantly different from zero (a test on the slopes), which removes small spurious responses.
- Point 6 (UK heaters): not solvable from aggregate data; report it as a limit. Large electric heating (storage
  heaters, heat pumps) behaves like AC in Austin and should be visible; HEAPO (Swiss heat pumps) could test this.

---

## T2 v4 - Definition and significance gate [v0.6]

**Definition (adopted).** M2 estimates the **weather-dependent load**: the part of the load that changes with
temperature beyond the substation's balance points. It includes heating and cooling but also anything else that
follows the weather; it is not "AC only". The old gradient-boosting M2 (v0.3-v0.4) is removed from the code;
`t2_thermal.py`, `t2_thermal_v2.py`, `t2_thermal_v3.py` are kept only as a record of those runs.

**Gate.** The cooling and/or heating side is kept only if the daily load rises significantly with degree-days
(daily regression on day of week, annual harmonics, CDD, HDD; Newey-West t > 2 on the training data); otherwise that
side is zero. Script `experiments/t2_thermal_v4.py`; table `experiments/results/t2_v4_dev.md`.

| Units (median) | Weather-dependent share without gate | With gate | True |
|---|---|---|---|
| REFIT homes without heaters | 0.205 | **0.024** | 0 |
| Plegma homes without AC | 0.342 | **0.206** | 0 |
| Pecan Ithaca homes without AC circuit | 0.248 | **0.102** | 0.041 |
| REFIT homes with heaters | 0.109 | 0.017 | 0.041 |
| Plegma AC homes (abs. share error) | 0.165 | **0.141** | - |
| Pecan Austin / San Diego AC homes | unchanged (0.48 / 0.24) | unchanged | 0.54 / 0.24 |
| Pecan Ithaca AC homes (daily corr.) | 0.73 | 0.52 | - |

**Conclusions.** The gate removes most false weather-dependent load where there is none (REFIT 0.21 -> 0.02) and does
not touch the units with a real response (Austin, San Diego). It costs a little in Ithaca (half a year per home, so
the test has little power). Adopted in v0.6. Remaining false share in Plegma homes without AC (0.21) is a real
temperature response of their load (fans, occupancy), which by the definition above is weather-dependent load.

---

## T3-EV - EV charging from hourly per-home data [v0.4, first run]

**Question.** Without sub-metering, can we tell which homes have an EV, when they charge, and how much EV energy a
substation draws by hour of day?

**Setup.** Pecan Street (local only, see data/README.md), development split: Austin (20 homes, 4 with EV) and Ithaca
(20 homes, 4 with EV). Detector: an hour is EV-like if the home's load exceeds its own same-hour median of the
previous 14 days by more than k kW (k = 1.5, 2.5, 3.5). Truth: car1/car2 circuits (charging = EV > 1 kW). Homes
selected as EV homes if their share of EV-like hours exceeds the midpoint of the EV / non-EV medians (a reporting cut,
not tuned per home). Script: `experiments/t3_ev.py`; tables: `experiments/results/t3_ev_dev.md`.

**Results** (k = 2.5 kW):

| | Austin | Ithaca |
|---|---|---|
| Which homes have an EV (AUC over homes) | 0.98 | 0.83 |
| When they charge (hourly precision / recall, median over EV homes) | 0.64 / 0.47 | 0.59 / 0.54 |
| EV energy by hour of day, group (correlation with truth) | 0.85 | 0.46 |
| EV energy, estimated / true | 1.16 | 1.24 |
| Peak charging hour, true / estimated | 22 / 22 | 7 / 18 |
| Session length, true / estimated (median hours) | 2 / 1 | 2 / 1 |

**Conclusions (indicative: only 4 EV homes per region).**
1. EV homes stand out clearly from hourly smart-meter data in Austin even with a crude rule; less so in Ithaca.
2. At substation level the Austin EV profile (evening, peak 22 h) and energy (+16%) are recovered.
3. Ithaca EVs charge mostly in the morning (07 h, probably on a timer) and the rule confuses evening loads
   (summer AC) with charging: the detector must not assume evening charging.
4. The rule splits sessions (1 h vs 2 h): consecutive EV-like hours need to be merged into sessions.
5. The circuit shows when a car charges, not how long it stays plugged in, so the flexibility window needs an
   assumption or literature (e.g. Electric Nation plug-in durations).

**Caveats.** Very few EV homes; one exploratory look before this test touched two held-out Austin homes (logged in
`docs/experiment_log.md`); nothing was tuned on it.

**Next.** Session-level detector (merge hours, require a plateau of roughly constant power), no fixed evening
assumption, data-driven k (relative to each home's load distribution); more EV homes would need the full Dataport.

---

## T3 - Discrete shiftable load (washing machine, dryer, dishwasher) and comparison with Ponocko & Milanovic [v0.5, first run]

**Question.** Can M3 find the shiftable appliance load of a group of homes without sub-metering, and how does that
compare with a Ponocko & Milanovic-style approach that uses sub-metered homes?

**Setup.** Development homes with sub-metered wet appliances (EV homes excluded): REFIT 13, Pecan Austin 16, Pecan
Ithaca 15, Plegma 10 (UK-DALE has too few). Random groups of 5 and 10 homes plus all homes. Estimates:
`m3_shift` (M3 events outside meal hours), `m3_all_events` (all M3 events), `transfer_1` (share profile by hour x day
type from ONE sub-metered home outside the group, ~5-10% sub-metering, as Ponocko & Milanovic 5%), `transfer_all`
(from all other homes of the dataset), `transfer_ext` (from the OTHER datasets only = public sub-metered data, no
sub-metering in the target network), and `zero` (no shiftable load) as reference. Metric AWFE p90 = 90th percentile of
|estimated - true shiftable share| per hour (Ponocko & Milanovic's metric). Script `experiments/t3_shiftable.py`;
table `experiments/results/t3_shiftable_dev.md`.

**Results** (largest group per dataset; AWFE p90, lower is better; energy ratio est./true):

| Dataset | zero | m3_shift | transfer_1 (1 sub-metered home) | transfer_ext (public data) | m3 energy ratio | transfer_ext energy ratio |
|---|---|---|---|---|---|---|
| REFIT (13) | 0.24 | 0.23 | 0.24 (N=10) | **0.20** | 1.07 | 0.37 |
| Pecan Austin (16) | 0.12 | 0.15 | 0.12 (N=10) | **0.085** | 1.84 | 1.34 |
| Pecan Ithaca (15) | 0.15 | 0.17 | 0.17 (N=10) | **0.10** | 1.55 | 0.84 |
| Plegma (5) | 0.18 | 0.53 | 0.16 | **0.13** | 4.5 | 1.11 |

**Conclusions.**
1. **AWFE needs a reference.** Predicting no shiftable load at all already gives AWFE 0.12-0.24, because the true
   share is small. Ponocko & Milanovic's 0.23 (0% sub-metering) and <0.1 (5%) cannot be compared with ours without
   this reference; we will report AWFE together with the zero baseline (skill = 1 - AWFE / AWFE_zero) and use their
   numbers only for orientation (their task is day-ahead forecasting of several category shares, ours is estimation).
2. **M3 events do not isolate shiftable appliances.** The excess-over-expected events also catch AC cycling, kettles,
   ovens, water heaters: energy is overestimated 1.5-4.5x (except REFIT, where it is ~1.0 by coincidence of small
   loads) and AWFE is no better than zero. Hour-by-hour correlation is low everywhere (0.04-0.5).
3. **Profiles from public sub-metered data work best**: `transfer_ext` beats zero and one sub-metered home in every
   dataset (AWFE 0.085-0.20), with no sub-metering in the target network. This changes the M3 design for the
   shiftable part: shiftable load = substation load x hour-of-day shiftable-share profile learnt from public
   sub-metered datasets (and time-use surveys), not event detection.
4. Energy level still differs between countries (REFIT 0.37, Austin 1.34): the share profile transfers better than
   the level. Country-level appliance statistics (e.g. annual kWh per washing machine / dryer, ownership) are the
   natural correction.

**Next (T3 v2).** M3 shiftable = public share profile x local load, level corrected by country appliance statistics
(ownership, kWh/year), optionally updated by the data where events are clearly appliance-like; report AWFE skill vs
zero; then T4 (sensitivity) and T5 (ablations) on the v0.5 method.

---

## T3 v2 - Two candidate designs for the shiftable part [v0.7]

Two designs are kept until one is chosen (decision with the team):
- **A - data only** (`shiftable.events_home`): per home, an hour is an appliance event if the load exceeds the
  home's own same-hour median of the previous 14 days by more than 3 robust standard deviations of its own excess,
  and the run is short (<= 3 h; longer runs are AC, EV, heating). Variant A2 first removes the home's
  weather-dependent load (M2). No sub-metering, no external data.
- **B - profile bank** (`shiftable.profile_estimate`, bank built by `scripts/build_profile_bank.py` from public
  sub-metered datasets): hour x day-type profile of the shiftable load taken from the bank and applied to the
  substation. Bank choice: mean / nearest load shape / similarity-weighted; level: share x load, kW per home x homes,
  or timing from the bank and level from design A.
Evaluated leave-one-dataset-out (the bank never contains the target dataset). Script `experiments/t3_shiftable_v2.py`;
tables `experiments/results/t3_shiftable_v2_dev.md` and `..._wh_dev.md`.

**Finding 1 - what counts as shiftable.** In Plegma every design overestimated 4.7x when the truth was washing
machine + dishwasher. The excess is the electric water heater (boiler): a short, large, discrete load, and a
classic flexible load (stored heat). Counting electric storage water heaters as shiftable (Plegma "boiler", Pecan
"waterheater"; not the UK-DALE gas boiler) brings Plegma to 1.2x. Adopted definition: shiftable = washing machine,
tumble dryer, dishwasher, electric storage water heater (EV separately).

**Results with that definition** (largest group per dataset; AWFE skill = 1 - AWFE / AWFE(zero), higher is better;
energy ratio est./true):

| Design | Austin | Ithaca | Plegma | REFIT |
|---|---|---|---|---|
| old M3 events (v0.6) | -0.22 (1.82) | 0.29 (0.58) | -0.01 (1.37) | 0.07 (1.08) |
| **A2 data only** | **0.23 (0.99)** | 0.23 (0.37) | **0.17 (1.21)** | 0.16 (1.15) |
| B bank, share x load | -0.34 (3.62) | **0.46 (0.76)** | 0.30 (0.71) | **0.38 (1.17)** |
| B bank, timing + level from A2 | **0.37 (0.99)** | 0.23 (0.37) | -0.41 (1.21) | 0.21 (1.15) |
| B bank, kW per home x homes | 0.18 (1.56) | 0.23 (0.36) | -1.05 (1.87) | -0.01 (1.58) |

**Conclusions.**
1. A2 (data only) is the only design that beats the zero reference in every dataset, with energy close to the truth
   except Ithaca (0.37: long water-heater runs are cut by the 3-hour limit). It replaces the old M3 events in the
   method (v0.7); meal-hour split, the 0.4 kW threshold and fixed night hours are gone (base hours = the home's own
   4 quietest hours).
2. The bank is better than A where its datasets resemble the target (Ithaca, REFIT, Plegma with share x load) and
   worse where they do not (Austin: US dryers vs UK/Greek bank). With 3-4 datasets in the bank, choosing by load
   shape did not beat the plain mean (the nearest dataset was usually UK-DALE with 3 homes). A larger bank is the
   condition for B; the code and the CC-BY bank (`data/profile_bank.json`: REFIT, UK-DALE, Plegma) are in place.
3. Hour-by-hour correlation stays low for every design (0.05-0.6): what is identifiable is the daily energy and the
   time-of-day profile of shiftable load, not individual hours. This is enough for flexibility envelopes (M4 works on
   the mean day), not for verifying single events.

**Next.** (a) Decide A or B with the team. (b) A: the 3-hour run limit is hand-set and hurts long water-heater
cycles - make it data-driven or test sensitivity (T4). (c) B: grow the bank (HES, IDEAL, ECO, GREEND, DEDDIAG, DRED,
AMPds) and add time-use timing (HETUS) per country.

---

## T3 v3 - Sensitivity of design A [v0.7]

Settings of the data-only events varied one at a time (others at max run 3 h, k = 3, window 14 days); truth incl.
electric water heaters. Script `experiments/t3_events_sensitivity.py`; table
`experiments/results/t3_events_sensitivity_dev.md`. Plegma enters only through groups of 5 (its homes overlap too
little in time for an all-homes group).

| Setting | AWFE skill, all homes (Austin / Ithaca / REFIT) | Energy ratio (Austin / Ithaca / REFIT) |
|---|---|---|
| max run 1 h | 0.20 / 0.12 / 0.12 | 0.47 / 0.16 / 0.48 |
| max run 2 h | 0.25 / 0.18 / 0.19 | 0.80 / 0.28 / 0.90 |
| **max run 3 h** | 0.23 / 0.23 / 0.16 | 0.99 / 0.37 / 1.15 |
| max run 4 h | 0.22 / 0.25 / 0.11 | 1.13 / 0.42 / 1.29 |
| max run 6 h | 0.15 / 0.27 / 0.05 | 1.30 / 0.49 / 1.47 |
| no limit | 0.09 / 0.28 / -0.01 | 1.49 / 0.61 / 1.61 |
| k = 2 / 2.5 / 3 / 4 | 0.16-0.27 / 0.20-0.25 / 0.15-0.17 | Austin 1.30 -> 0.76 |
| window 7 / 14 / 28 days | 7 days worse; 14 and 28 equal | - |

**Conclusions.**
1. The 3-hour limit sits on a plateau: 2-4 h give similar skill everywhere; below 2 h appliance cycles are cut
   (energy x0.5), above 4 h long non-appliance runs (AC, heating) leak in (REFIT energy x1.3-1.6, skill -> 0). Not a
   knife-edge choice, so it stays at 3 h; k = 3 and 14 days likewise sit in flat regions. No further tuning on the
   development data (that would fit it).
2. Ithaca is the exception: skill rises with longer runs but energy stays low (0.6 even without a limit) - its water
   heaters run long at low power, below the event threshold. Such loads are not "events"; they need their own
   treatment (next).
3. Groups of 5 homes in Austin have negative skill for every setting while all 16 homes are positive: at very small
   groups the estimate is unstable; the target (substations of 50+ homes) is the large-group regime.

**Next for design A.** (a) Long, low-power, regular loads (water heaters on timers, pumps): detect them as a
separate "regular block" component (same hours most days) instead of events. (b) Then T4/T5 on the full v0.7 method.

**Follow-up: why design A misses energy in Ithaca (checked before adding a new component).** Per home (development):
the missing energy is almost all one home (P950) whose water heater draws ~1.1 kW for 23.5 h a day (28 kWh/day,
about half of all shiftable energy in the group). An always-on load is indistinguishable from the base load without
sub-metering. Without that home the ratio is 0.69; the rest is small, irregular water heaters (0.3-0.4 kW when on,
3-8 h a day, day-to-day variation about twice their mean), i.e. inside the noise. Plegma water heaters (1.1-1.4 kW,
1-4 h) are found as events. Pecan's free files have no pool pumps. Conclusion: there is no regular "timer block"
pattern in these data to detect, so no separate component was added; always-on and very small loads remain a stated
limit of design A. If a dataset with timer-driven loads (night-tariff water heaters, storage heaters, pool pumps)
becomes available, the question should be reopened.

---

## T1 rerun on v0.7

M1 features changed (seasonal features added, hand-set CDD/HDD bases removed), so T1 was rerun on the same
development groups (`experiments/results/t1_dev_v07.md`). Results are practically unchanged: LCL 50/150/500 homes
coverage 0.898/0.896/0.896, band width 0.41/0.30/0.23, nMAE 0.095/0.067/0.050; REFIT 1 -> 14 homes coverage
0.893 -> 0.902, width 1.35 -> 0.66; Plegma 1/2/5 coverage 0.897/0.895/0.884. The T1 conclusions stand.

---

## T4 - Sensitivity of the flexibility envelope [v0.7]

**Setup.** Groups of all development homes that overlap in time (REFIT 13, Pecan Austin 16, Pecan Ithaca 15; EV homes
excluded). The estimated envelope (M2 + M3 + M4) is compared with a "true" envelope built the same way from the
measured AC/heating and shiftable circuits (same base, same allocation, same M4). Each remaining fixed setting varied
alone. Script `experiments/t4_sensitivity.py`; table `experiments/results/t4_dev.md`.

**Results** (default settings; error = mean |est. - true| over the 24 h of the envelope / mean load):

| | Austin | Ithaca | REFIT |
|---|---|---|---|
| Downward flexibility, est. / true | 0.83 | 0.58 | 0.85 |
| Downward error | 0.08 | 0.13 | 0.04 |
| Upward flexibility, est. / true | 0.99 | 1.23 | 1.15 |
| Upward error | 0.03 | 0.04 | 0.06 |
| Upward envelope, mean / load | 0.51 | 0.23 | 0.18 |

Effect of the settings:
- shift window 1 h vs 2-6 h: 1 h gives less upward flexibility; from 2 h on nothing changes (the power cap binds).
- request duration 1-4 h and cap quantile 0.8-0.95: change the size of the envelope a lot (Austin upward 0.36 ->
  0.58 of load for cap 0.8 -> 0.95) but not the estimated / true ratio (0.96-0.99 in Austin).
- base hours 2-6 and base quantile 0.05-0.2: no effect.

**Conclusions.**
1. The M4 settings (window, request duration, cap) are definitions of the product a DSO asks for (how long, how much
   risk), not estimation parameters: they scale estimate and truth together and do not affect accuracy. They become
   inputs chosen by the user, reported with the envelope. The base settings do not matter.
2. Accuracy is set by M2 and M3: downward flexibility is 0.58-0.85 of the true one (Ithaca lowest: the always-on water
   heater and small heaters of T3), upward within 0-23%.
3. Nothing in the method now depends on a hand-set number that changes the accuracy; the remaining fixed values sit in
   flat regions (T3 v3) or are user-facing definitions.

**Next.** T5 (ablations: without weather, without calibration, without M2, without M3) on v0.7.

**Like-for-like comparison with a Ponocko-style reference (same truth incl. water heaters, same groups).** AWFE p90,
lower is better; "1 sub-metered home" = share profile from one sub-metered home outside the group (~7-20% of the
group sub-metered), median over donor homes:

| Group | zero | 1 sub-metered home | Design A v0.7 | Design A v0.8 (no sub-metering) | Design B (bank, share x load) |
|---|---|---|---|---|---|
| Austin, 10 homes | 0.126 | 0.115 | 0.105 | **0.102** | 0.167 |
| Ithaca, 10 homes | 0.247 | 0.237 | 0.175 | 0.177 | **0.148** |
| REFIT, 10 homes | 0.239 | 0.240 | 0.234 | 0.220 | **0.155** |
| Plegma, 5 homes | 0.399 | 0.362 | 0.331 | 0.331 | **0.280** |

Design A is at least as good as the one-sub-metered-home reference in every dataset. This reference is a simplified
version of the sub-metering idea (one donor), not Ponocko & Milanovic's ANN with 5% of 1,000 homes sub-metered, and
their AWFE values come from their data and category set, so their 0.23 (0%) / <0.1 (5%) cannot be placed on this scale
directly; AWFE also depends strongly on the dataset (zero reference 0.12-0.40).

## T7 - Ponocko & Milanovic (2018) reproduced on CREST, and compared with ours [v0.7]

**Why.** Their published numbers (AWFE p90 0.23 at 0% sub-metering, <0.1 at 5%) are for their own CREST population,
their "controllable" category (wet appliances + cold appliances + water/space heating) and one test day; our method
does not estimate cold appliances, so their numbers cannot be placed next to ours directly. We rebuilt their setting
and ran both methods on the same homes.

**Data.** `scripts/crest_generate.py`: 1,000 synthetic UK homes (CREST / richardsonpy, UK occupancy mix of the paper),
60 days from 1 January, 1-minute P, Q (from the appliance power factors of the CREST table) and the six categories of
their Table I. A bug in richardsonpy (activity table read with 5 instead of 6 activities per occupancy level, so laundry
used the TV probabilities) made wet appliances 2-3x too frequent (13-14 kWh/day per home); the script patches it at run
time (8.8 kWh/day, UK level). A second, independent population (500 homes, seed 2) is used for their 0% case.

**Their method** (`flexsub/ponocko.py`): inputs P, Q per minute in p.u. of the monthly maximum; 44 log-sigmoid hidden
neurons, tan-sigmoid outputs, Bayesian regularization (Levenberg-Marquardt + MacKay, as MATLAB `trainbr`); trained on
the 7 days before the test day using the sub-metered homes; applied to the P, Q of all 1,000 homes. The paper quotes
n = N/(d ln N) for the hidden layer, which gives 547 for N = 7 x 1440, not 44; we use 44 as reported.
0% case: trained on the independent CREST population (their 0% uses UK statistics; same-model training data is the
most favourable version of it). AWFE (their eq. 9) = |estimate - truth| in p.u. of the average monthly load.

**Ours**: M3 design A per home from its hourly total load only (no sub-metering, no reactive power). It needs ~21
days of history per home, so test days are days 24, 28, ..., 52 (8 days); 3 random sub-metered subsets for 5/10/20%.

**Results** (median over test days and subsets of the AWFE p90; `experiments/results/t7_ponocko_crest.md`):

| Target | zero | Ours (0%) | Ponocko 0% (indep. CREST) | 5% | 10% | 20% | 100% |
|---|---|---|---|---|---|---|---|
| Wet appliances (CTIM1), hourly | 0.292 | 0.156 (0.13-0.19) | 0.043 | 0.103 (0.06-0.19) | 0.079 | 0.063 | 0.041 |
| Wet appliances, energy est/true | - | 1.50 | 0.99 | 1.23 | 1.17 | 1.11 | 1.00 |
| Their "controllable", 1-minute | 0.533 | - | 0.080 | 0.332 (0.15-0.54) | 0.164 | 0.115 | 0.079 |

**Conclusions.**
1. Their method is reproduced at 100% sub-metering (0.08 controllable, ~0.04 wet), but **their 5% result is not**:
   0.33 (0.15-0.54 across days and subsets) instead of <0.1; ~0.1 needs 20%. With 50 homes the training aggregate
   is much spikier than the 1,000-home aggregate it is applied to, so the network extrapolates.
2. Training on another population of the same model (our "0%") is as good as 100% sub-metering. On CREST this is
   expected (same generator), so it is an upper bound, not their 0.23; it does say that **transfer from a similar
   sub-metered population works when the populations match** - the idea of our design B (profile bank).
3. **Ours vs theirs on the common part (wet appliances):** ours with no sub-metering 0.156 is between zero (0.29) and
   their 5% (0.10): skill 0.47 vs 0.65. Ours overestimates energy x1.5: the events also catch other short spikes
   (kettle, oven, electric shower). On CREST - their home ground, with clean appliance signatures and reactive power -
   their 5% is better than ours; but their 5% is also unstable (0.06-0.19 across subsets) and far from the paper on the
   headline category.
4. To answer "closer to 0% or to 5%": on CREST, ours closes ~half of the gap between zero and their 5% for wet
   appliances, with no sub-metering and no reactive power.

**Robustness of the 5% result** (days 24, 32, 40, 48; AWFE p90, median and 10th-90th percentile over days x
subsets; `experiments/results/t7b_*.md`):

| Variant | Controllable 1-min, 5% | 10% | Wet appliances hourly, 5% | 10% |
|---|---|---|---|---|
| 10 random subsets | 0.26 (0.19-0.38) | 0.16 (0.12-0.20) | 0.11 (0.09-0.15) | 0.07 (0.06-0.10) |
| 5 subsets with the population's household-size mix | 0.26 (0.19-0.48) | 0.18 (0.13-0.28) | 0.11 (0.07-0.15) | 0.08 (0.06-0.10) |
| Best training (1,000 epochs, best of 3 initialisations) | 0.30 (0.24-0.47) | - | 0.10 (0.08-0.14) | - |
| Ours, no sub-metering | - | - | 0.17 (0.14-0.18) | |
| Zero | 0.58 | | 0.31 | |

5. The 5% result is robust to the subset (random or representative) and to the training: 0.26-0.30 for the headline
   category, never below 0.16 in 90% of the cases; the paper's <0.1 at 5% (and "5% close to 100%") is not reproduced.
   ~0.1 is reached between 10% and 20%. (Remaining differences we cannot remove: their own CREST population, one test
   day, MATLAB details not given in the paper.)
5b. Their own earlier paper (CIRED 2017 [10b], same idea, CREST, 1,000 homes) tested 20/50/80% and measures AWFE as a
   share of the load at that time step. In that unit their active controllable error is 0.05 at 100% and ~0.06 at 20%
   (their ~0.10 at 20% is for reactive load); they call 50% the optimal coverage for active and reactive together. In
   the same unit our reproduction gives 0.073 (100%), 0.074 (50%), 0.098 (20%), 0.135 (10%), 0.176 (5%) (T7c, 8 days).
   So our implementation is ~0.02-0.04 less accurate than theirs at high coverage and the gap grows as coverage falls;
   the 5% claim of [10] is the one furthest from what we get.
6. On wet appliances, ours (0.17) is above their 5% (0.11) and 10% (0.07): AWFE skill 0.45 vs 0.65 (5%), i.e. ours
   closes ~70% of the gap between zero and their 5%, without sub-metering and without reactive power.

**Next.** (a) Reduce the ~x1.5 overestimate of design A (separate kettle/oven/shower spikes, e.g. by duration within
the hour or time of day) and rerun T7; (b) design B on CREST with the bank built from REFIT/UK-DALE (real UK data,
not the same generator) - a fair 0% transfer; (c) T5 ablations.

## T3 v4 - Fewer false events in design A [v0.8]

**Problem.** On CREST design A overestimated wet-appliance energy x1.5 (T7). Diagnosis on the real development data
(`events_home`, A2): in 25-55% of the event hours no shiftable appliance runs (Austin 54%, Plegma 55%, REFIT 52%,
New York 37%, UK-DALE 25%); CREST is no different (58%). On real data the total energy came out ~right only because
the false events cancel missed cycles. False events: ordinary activity (cooking, heating) that happens on fewer than
half of the days at that hour, so the median of the same hour does not contain it. Neither run length nor "habit"
(how often the home has an event at that hour) separates them consistently across datasets; event size does (small
excess -> mostly false), but needs an absolute kWh threshold.

**Variants tested on the real development data only** (8 groups of 10 homes, Plegma 5; AWFE skill, change vs v0.7,
median [min, max] over groups): baseline quantile 0.6 / 0.7 instead of the median, k = 4 / 5, run <= 2 h, dropping events
below half the home's typical event size.

| Variant | Austin | New York | Plegma | REFIT |
|---|---|---|---|---|
| base = 60th percentile | +0.045 [+0.024, +0.076] | -0.008 [-0.015, 0.000] | +0.002 [-0.002, +0.041] | +0.034 [+0.026, +0.050] |
| base = 70th percentile | +0.082 | -0.033 | -0.012 | +0.038 |
| k = 4 | +0.034 | -0.021 | -0.014 | -0.005 |

The 60th percentile is the only variant that does not hurt any dataset; adopted in v0.8 (`shiftable.events_home`,
`base_quantile=0.6`; the median version is removed). It was then applied once to CREST, with no tuning there.

**Results v0.8.**
- Real data, full T3 v2 harness (largest group, AWFE skill v0.7 -> v0.8): Austin 0.228 -> 0.268, New York 0.229 ->
  0.210, Plegma 0.171 -> 0.172, REFIT 0.160 -> 0.212; energy ratio Austin 0.99 -> 0.83, REFIT 1.15 -> 1.01, Plegma 1.21
  -> 1.22, New York 0.37 -> 0.32 (New York stays low: the always-on water heater of T3 v3).
- CREST (T7 setting, wet appliances, hourly AWFE p90, days 24-52): 0.156 -> **0.088** (0.07-0.11), energy x1.5 ->
  x1.15. Ponocko & Milanovic: 5% 0.10-0.11, 10% 0.07-0.08.

**Conclusions.**
1. With no sub-metering and no reactive power, design A now estimates wet-appliance load on CREST between their 5%
   and 10% sub-metering. Their own CIRED 2017 version needs 20-50% for the headline category [10b].
2. On their headline "controllable" category (wet + cold + water/space heating), ours estimates only the wet part on
   CREST (no weather in CREST, so M2 finds nothing; cold appliances are not estimated): AWFE p90 0.245, about equal
   to their 5% (0.24-0.29 hourly) and worse than 10% (0.14-0.16). A fair comparison of total flexibility needs real
   weather-dependent data (Pecan Austin, as in their validation).
3. The New York loss (-0.02 skill) is small and within the spread of the other variants; noted, not hidden.

## T7c - Analogue of their Fig. 6 and Fig. 7, with our method [v0.8]

`experiments/t7c_figures.py`; figures in `experiments/results/figures/t7c_fig6_cdf.png` and `t7c_fig7_composition.png`;
table in `experiments/results/t7c_figures.md`. 1,000 CREST homes, 8 test days, one random sub-metered subset per
coverage. Space heating is given to our method as known (CREST has no weather; in real data M2 estimates it) - it is
small in CREST (~0.05 kWh/day per home, few homes own it). Cold appliances and water heaters are not given.

AWFE p90, hourly, p.u. of the average monthly load (median over days):

| Method | Controllable (wet + cold + water/space heating) | Wet appliances |
|---|---|---|
| zero | 0.515 | 0.292 |
| **Ours, 0% sub-metering** | **0.236** | **0.087** |
| Ponocko 5% | 0.264 | 0.115 |
| Ponocko 10% | 0.162 | 0.080 |
| Ponocko 20% | 0.091 | 0.059 |
| Ponocko 50% | 0.059 | 0.043 |
| Ponocko 100% | 0.061 | 0.041 |
| Ponocko 0%, trained on an independent CREST population (same model, upper bound) | 0.060 | 0.043 |

**Conclusions.**
1. Wet appliances: ours (no sub-metering) is between their 5% and 10%, and its CDF lies between theirs (Fig. 6, right).
2. Controllable: ours is slightly better than their 5% but well behind 10%; the remaining error is the parts ours does
   not estimate in CREST (cold appliances, water heaters), visible as the offset of our CDF (Fig. 6, left).
3. Their 100% has one bad test day (0.415): a single training run can fail; the paper shows one day only.
4. Fig. 7 (day 40): with 5% their composition is visually close, as in their paper, but misplaces RC/SMPS in the
   evening; our wet estimate follows the actual wet load closely.

## T8 - Final method (v0.8) on real data, real vs estimated [v0.8]

`experiments/t8_real_figures.py`, `t8_plot.py`; figures `experiments/results/figures/t8_fig_cdf.png`,
`t8_fig_days.png`; tables `experiments/results/t8_real.md`. Development data; groups = all development homes present
together (REFIT 13, Pecan Austin 16, Pecan New York 15). UK-DALE homes never overlap in time, so each is evaluated alone.
Truth: weather-dependent = AC / furnace / heaters (as in T4); shiftable = wet appliances + electric storage water
heaters. AWFE hourly, p.u. of the 30-day mean load of the group.

| Group | Part | Ours AWFE p90 | Zero AWFE p90 | Energy est./true |
|---|---|---|---|---|
| Pecan Austin (16) | flexible | **0.30** | 1.00 | 0.73 |
| | shiftable | 0.095 | 0.129 | 0.72 |
| | weather-dependent | 0.285 | 0.96 | 0.73 |
| Pecan New York (15) | flexible | **0.32** | 0.53 | 0.51 |
| | shiftable | 0.22 | 0.32 | 0.32 |
| | weather-dependent | 0.18 | 0.32 | 0.71 |
| REFIT (13) | flexible | **0.24** | 0.32 | 0.92 |
| | weather-dependent | 0.02 | 0.02 | 0 (gate: no weather load) |
| UK-DALE B1 (single home, 3.4 years) | flexible | 0.16 | 0.20 | 0.91 |
| UK-DALE B2, B5 (single homes, 73 / 99 days) | flexible | 0.19 / 0.22 | 0.02 / 0.08 | 0.81 / 0.93 |

**Ponocko-style ANN on the same groups, adapted to the data available** (hourly P only - no Q, no 1-minute data;
trained on the 7 days before each weekly test day; median of 3 draws; numbers only, not in the figures). AWFE p90 of
the flexible load, theirs vs ours on the same test days:

| Group | 1 sub-metered home | 20% | 50% | Ours (0%) |
|---|---|---|---|---|
| Pecan Austin | 0.40 | 0.24 | 0.18 | 0.31 |
| Pecan New York | 0.55 | 0.47 | 0.23 | 0.29 |
| REFIT | 0.44 | 0.29 | 0.21 | 0.23 |

**Conclusions.**
1. On real substations-in-miniature (13-16 homes) ours beats the zero estimate on every part, most where weather
   matters (Austin flexible 0.30 vs 1.00), and follows the daily shape (figures). It underestimates the level where
   load is weather-driven: Austin AC (0.73) and New York (0.51, the always-on water heater P950 of T3 v3).
2. Against the adapted Ponocko ANN, ours is better than 1 home and 20% sub-metered in all three groups and close to
   50% in REFIT; their 50% is better in Austin (AC) and New York. This version of their method lacks Q and 1-minute
   data, which they rely on, so it is a lower bound for their method, not a reproduction.
3. Single homes (UK-DALE): with a long record (B1) ours beats zero; with 2-3 months (B2, B5) false events dominate the
   90th percentile and zero is better. The method is meant for aggregates and needs history; this is the expected
   failure mode, reported, not hidden.

## T9 - EV charging and water heaters as flexible load [v0.9]

**Question.** v0.8 counts as flexible only weather-dependent load and short appliance cycles (<= 3 h), and T8 left EV
homes out. EV charging is central to OpenAIFlex. Can it be added from hourly smart-meter data alone, and what about
water heaters?

**Diagnosis (v0.8, per home).** EV energy caught as "appliance events": 9-54%; lost because sessions last > 3 h: 4-40%;
below the 3-sigma threshold: 11-62%. Greek resistive water heaters (Plegma, ~1.2 kW): 36-59% already caught.
New York water heaters are ~0.4 kW (heat-pump type), below any threshold; home P950 runs its water heater 98% of
hours at ~1.1 kW, which in the hourly total is indistinguishable from always-on load.

**Setup.** `experiments/t9_ev.py`. Groups: all development homes with sub-metered wet appliances present together,
EV homes included (Pecan Austin, Pecan New York, REFIT 13, Plegma). Truth: flexible = weather (AC/heating) +
shiftable (wet appliances + electric water heaters) + EV (car circuits). AWFE p90 as in T8.

| Flexible AWFE p90 | zero | v0.8 | all long runs as EV | EV k=1.5 | **EV k=2.5, gate 2% (v0.9)** |
|---|---|---|---|---|---|
| Pecan Austin | 1.07 | 0.327 | 0.293 | 0.256 (EV x1.85) | **0.292** (EV x0.90) |
| Pecan New York | 0.57 | 0.334 | 0.309 | 0.286 (EV x3.2) | **0.321** (EV x0.96) |
| REFIT (no EV) | 0.32 | 0.249 | 0.278 (false 5.3 kWh/day) | 0.264 | **0.249** (no false EV) |
| Plegma (no EV) | 0.87 | 0.312 | 0.312 | 0.366 | **0.312** (no false EV) |

Sensitivity of v0.9 (k 2-3.5 kW, gate 1-3%): flexible AWFE Austin 0.280-0.313, New York 0.307-0.328, REFIT and
Plegma unchanged at every setting. The EV energy itself is sensitive (est./true 0.2-1.8), so the EV level is the
weak part. As implemented in `flexsub` (decompose_substation): Austin 0.325 -> 0.288, New York 0.322 -> 0.310, EV
energy est./true 0.94 / 1.02.

**Which homes.** Austin: 4/4 EV homes found, 3 of 16 non-EV homes also pass the gate. New York: 2 of 3 EV homes in
the group found (the missed one charges at ~1.4 kW, level 1), 1 false. Group EV energy is right partly because misses
and false homes cancel.

**Conclusions.**
1. Adopted as v0.9: EV is a separate flexible part (`down_ev_kw` in the envelope). Flexible error improves where EVs
   exist and nothing changes where they do not.
2. k = 2.5 kW is physical (level-2 chargers 3.3-7.2 kW); the 2% gate was read off development data (T3-EV) and is
   flat between 1% and 3%.
3. Not solved, and probably not solvable from hourly totals alone: level-1 charging, heat-pump water heaters and
   always-on water heaters. If the DSO knows which customers have them (e.g. a night water-heating tariff, an EV
   register), that is an input, like participation.
4. Indicative: only 4 EV homes per region in the development data.
5. M4 still uses the same +-3 h window for EV as for appliances; EV energy can usually move across the whole night,
   so the upward EV flexibility is underestimated. Plug-in times are not in Pecan; needs another dataset or the
   literature.

## T9b / T9c - EV homes without false positives; actionable EV flexibility [v0.9]

**Data changes.** P950 (New York; water heater on 98% of hours, half of the home's load) excluded from the data
(`data/splits.json`, excluded). Heat-pump water heaters (Pecan water-heater circuits drawing < 1.5 kW when on) are a
category of their own: not in the flexible truth, reported separately (New York: 17 kWh/day for the group, not
estimated). Level-1 charging (~1.4 kW) is out of scope.

**False EV homes (T9b).** The 3 false Austin homes were residual air conditioning (hot afternoons), the New York one a
dryer. Added test: a charger draws flat power, so the median coefficient of variation of the hourly excess inside runs
of >= 2 h must be <= 0.14 (EV homes 0.08-0.13, false 0.15-0.22). Threshold set on Austin, checked on New York.
Result: Austin 4/4 EV homes, 0 false; New York 1/3 (P9053 is level 1; P1222 fails the test because a heater runs
next to the car), 0 false; REFIT, Plegma 0. Script `experiments/t9b_v09.py`, table `results/t9b_v09.md`.

| Flexible AWFE p90 | zero | v0.8 | v0.9 |
|---|---|---|---|
| Pecan Austin (20 homes) | 1.08 | 0.325 | **0.293** (EV energy x0.70) |
| Pecan New York (17, no P950) | 0.46 | 0.248 | 0.248 (EV energy x0.21) |
| REFIT, Plegma | | unchanged | unchanged |

**Actionable EV flexibility (T9c, `flexsub/ev_flex.py`, `pipeline.ev_day_ahead`).** For the day ahead, each EV home
is described by its detected sessions of the last 14 days (14 equally likely scenarios). Assumption: the car stays
plugged in for 10 h from the session start (hourly meters do not show departures). Output per hour: expected EV kW,
EVs plugged in, kW that can be postponed, kW that can be pulled in; and for a DSO request a plan per home ("P4767: no
charging 18-21, finish 21-23") with the aggregate before/after and the rebound.
Check against the car circuits, every development day (Austin 209, New York 133), request = the 3 busiest expected
hours (reduce) or 01-04 (increase):

| | predicted kW | real kW | ratio | day-to-day corr |
|---|---|---|---|---|
| Austin, reduce | 1.36 | 1.65 | 0.82 | 0.18 |
| New York, reduce | 0.47 | 0.61 | 0.77 | 0.11 |
| Austin, increase | 2.26 | <= 7.19 (energy that existed to move) | | |

First version (one "median session" per home) overstated the reduction x2.2; scenarios fixed it. Day-to-day
correlation is low: on average the plan is right, on a given day 4 cars are random. Dwell 6/10/14 h changes the
increase (more hours plugged) but not the reduce. Rejected: dropping non-flat sessions one by one (EV energy x0.22).
Open: estimated charging starts ~3 h earlier than the truth in Austin (peak 18-19 h vs 22 h) - other high loads in EV
homes are still counted as charging; the rebound right after a reduce block makes a new peak (the plan should stagger
it).

## T9d - M6: EV as its own module; plug-in windows; staggered rebound [v0.9]

**Structure.** EV is now M6 (`flexsub/ev.py`): detection, sessions, plug-in windows, day-ahead envelope and plan.
M4 is weather-dependent + appliances only; total flexibility = M4 + M6. M3 uses the M6 detector only to keep
charging hours out of the appliance events and the routine part.

**EV timing (Austin, charging estimated ~3 h early).** Cause: residual air conditioning on hot afternoons in EV homes
(7-49% of the detected EV energy per home). Tried and rejected, none improves: (a) accept hot-day sessions only at
the home's usual cool-day charging hours (kills P8156, which has 2 cool-day sessions); (b) temperature-matched
reference (same-hour level from the 10 days of closest temperature): unchanged; (c) session classifier trained on
public sub-metered homes, leave-one-home-out: energy recall 0.14-0.31 vs 0.35-0.83 for the rule. With 4+3 EV homes
this is the limit of the data; a learned classifier needs many more EV homes (full Pecan Dataport).

**Plug-in window.** Not observable in hourly data, so it is bounded. Household away-time from the home's own load
profile (morning drop) was tried: no clear away period in 4 of 7 homes, and 9-62% of the true charging falls in the
"away" hours (people leave, the car does not). Two windows kept: 'dwell' 10 h (default) and 'observed' (hours the
car has been seen charging on >= 2 of the last 28 days; safe floor). Script `experiments/t9d_ev_plan.py`, table
`results/t9d_ev_plan.md`:

| Reduce request (3 busiest EV hours) | window | predicted kW | real kW | predicted/real |
|---|---|---|---|---|
| Austin | dwell 10 h | 1.39 | 1.60 | 0.87 |
| Austin | observed | 0.65 | 1.18 | 0.55 |
| New York | dwell 10 h | 0.49 | 0.62 | 0.79 |
| New York | observed | 0.14 | 0.41 | 0.33 |

**Rebound.** Postponed energy is placed by valley filling on the expected substation load (non-EV same-hour mean of
the last 14 days + EV). Days on which the request creates a new substation peak after the block: Austin 27% -> 0%
(dwell), 22% -> 3% (observed); New York 6% -> 0%.

## T10 - Final figures, method v0.9 [v0.9]

`experiments/t10_final_figures.py` (T9 groups, EV homes included, P950 excluded): `figures/final_days.png`,
`figures/final_cdf.png`, `figures/m6_plan.png`. Flexible load, est./true energy: Austin 0.74, New York 0.79, REFIT
0.92, Plegma 0.94 - always under (main source: level of air conditioning, 0.76-0.84). T8 rerun with v0.9
(`results/t8_real_v09.md`, homes without EV): New York 0.315 -> 0.268 (P950 excluded); Ponocko-style ANN New York
1 home 0.63, 20% 0.56, 50% 0.23 vs ours 0.25; Austin and REFIT unchanged.

## T11 - Where the under-estimation comes from; REFIT over-estimation peaks [v0.9, diagnostics]

**Under-estimation (Austin 0.74, New York 0.79 of the flexible energy).**
- Weather part. Pecan "furnace" circuits are air handlers that also run on mild days (Austin 1.85 kW in the mildest
  month). The part of the true HVAC load that is there on days inside the balance-point band is 17% (Austin) and 52%
  (New York). It does not depend on temperature, so from hourly totals it is indistinguishable from base load. On the
  temperature-driven part only, Austin est./true = 0.91. Annual harmonics are not the cause (0.83 vs 0.85 without).
- Base allocated first takes 0.83 -> 0.76 of the Austin weather part (night AC in the quiet hours).
  Tried: base from the weather-removed load: Austin energy 0.74 -> 0.81 but hourly AWFE 0.293 -> 0.299, Plegma
  0.311 -> 0.497 (over 1.24). Rejected.
- Appliances in Austin EV homes 0.36 (non-EV homes 0.78): ~5 kW US dryers pass as charging in EV homes. Tried:
  EV only for runs >= 2 h: EV 0.70 -> 0.49, AWFE 0.293 -> 0.301. Rejected.

**REFIT peaks of over-estimation.** The largest are 5-8 kW for an hour in homes where none of the 9 sub-metered
circuits draws anything (e.g. H5 06-07 h, H3 18 h): unmetered loads (electric shower, immersion heater, cooking).
Part is real flexibility missing from the truth (immersion heaters), part is not (showers, cooking). Tried: a power
cap on appliance events (clip at 3 / 4 kW, drop > 4 kW): REFIT AWFE unchanged (0.242), New York slightly worse.
Rejected.

**Conclusion.** None of the four changes improves the hourly error without breaking another dataset. The remaining
under-estimation is mostly HVAC load that runs regardless of weather, missed EVs in New York, and level-1 charging.
