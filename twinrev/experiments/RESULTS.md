# EV capacity experiment: results

## 2026-11-05: code check on synthetic data (not a result)
Invented homes, offline power flow, 250 kVA, 5 scenarios. It only shows that the code runs and how the design behaves.
- With 100 % response the oracle fits every car on the feeder at any useful transformer size: charging moves to the night and
  the peak stays the non-EV peak, so the count shows nothing.
- With 25-50 % response the capacities fall between 0 and 55 (e.g. none 7, oracle 21, method 20), so the comparison works.
- Two cars on one home switch off the method's EV detection (flat-power test), so N stays at one car per home.

## 2026-11-05: risk of breaking a limit, unseen synthetic homes (not a real-data result)
55 invented homes (seed 11; the setting was picked on seed 7), 200 kVA, DPsim run directly, 30 scenarios. Files: `results/risk_holdout_q*.json`.
| EVs | Response | No management | Method (q 0.25) | Method (q 0.6) | Oracle |
|---|---|---|---|---|---|
| 28 | 25 % | 83 % | 27 % | 43 % | 10 % |
| 28 | 50 % | 83 % | 0 % | 13 % | 0 % |
| 55 | 25 % | 100 % | 97 % | 100 % | 97 % |
| 55 | 50 % | 100 % | 73 % | 100 % | 27 % |
(share of scenarios with a broken limit; with 14 EVs none breaks.)
- EV detector, reference quantile 0.25 vs 0.6: 14/14 homes and energy x0.96 vs 1/14 and x0.04, no false homes. These cars charge on ~86 % of days, so the 0.6 reference contains the charging.
- 55 EVs, 25 % response: no fewer hours over a limit (4.67 -> 4.80), energy over the transformer limit -31 %.

## 2026-11-06: EV detector on real data (Austin, 20 development homes, 4 with a car)
| Reference quantile | EV homes found | False homes | Energy est / true |
|---|---|---|---|
| 0.6 (current) | 4/4 | 0 | 0.79 |
| 0.4 | 4/4 | 1 | 1.16 |
| 0.25 | 3/4 | 1 | 1.24 |

Conclusion: keep 0.6. The gain of 0.25 above came from synthetic cars that charge on 86 % of days. Few EV homes here, New York still open.

## 2026-11-06: final comparison, method v0.13 (220 kVA, 15 scenarios, offline power flow, checked against DPsim)
Share of scenarios with a broken limit, kWh per day over the transformer limit. Sub-metering = the M5 rule on the true circuits of the 35 days before.

Austin, 20 real development homes (4 with a car):
| EVs | Response | No management | Method v0.12 | Method v0.13 | Sub-metering |
|---|---|---|---|---|---|
| 28 | 25 % | 20 %, 2.3 | 13 %, 0.0 | 13 %, 0.0 | 20 %, 0.0 |
| 28 | 50 % | 20 %, 2.3 | 13 %, 0.0 | 7 %, 0.0 | 7 %, 0.0 |
| 55 | 25 % | 67 %, 22.2 | 53 %, 12.0 | 47 %, 10.0 | 20 %, 6.7 |
| 55 | 50 % | 67 %, 22.2 | 27 %, 4.3 | 20 %, 1.3 | 20 %, 0.4 |

New synthetic homes (seed 11):
| EVs | Response | No management | Method v0.12 | Method v0.13 | Sub-metering |
|---|---|---|---|---|---|
| 28 | 25 % | 40 %, 5.3 | 13 %, 1.0 | 0 %, 0.0 | 0 %, 0.0 |
| 28 | 50 % | 40 %, 5.3 | 7 %, 0.1 | 0 %, 0.0 | 0 %, 0.0 |
| 55 | 25 % | 100 %, 239 | 100 %, 197 | 100 %, 129 | 100 %, 131 |
| 55 | 50 % | 100 %, 239 | 93 %, 102 | 47 %, 22 | 40 %, 10.4 |

EV detection, v0.13: Austin 4/4, 0 false, energy x1.29; New York 3/4, 0 false, x1.05 (level-1 home missed); new synthetic 14/14, 0 false, x0.95.

Conclusion: on these Austin homes the method lowers the risk clearly at 50 % response and comes close to sub-metering. Rejected on the same homes: lower quantiles, two-group gate, trimmed CV, charger-rate first, paired 15-min steps. The gate and energy rule were tuned on the same homes; the locked test is still closed and New York risk was not run.
