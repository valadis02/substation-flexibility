
## pecan_austin (development split; detector: load > same-hour 14-day median + k kW)

### 1. Which homes have an EV (score = share of EV-like hours)

| dataset      |   k |   ev_homes |   other_homes |   auc |   score_ev_median |   score_other_median |
|:-------------|----:|-----------:|--------------:|------:|------------------:|---------------------:|
| pecan_austin | 1.5 |          4 |            16 | 1     |             0.118 |                0.032 |
| pecan_austin | 2.5 |          4 |            16 | 0.984 |             0.06  |                0.008 |
| pecan_austin | 3.5 |          4 |            16 | 0.953 |             0.02  |                0.001 |

### 2. When they charge (EV homes; median over homes)

|   k |   precision |   recall |
|----:|------------:|---------:|
| 1.5 |        0.44 |     0.72 |
| 2.5 |        0.64 |     0.47 |
| 3.5 |        0.77 |     0.2  |

### 3. EV energy by hour of day, group of development homes

| dataset      |   k |   homes_selected |   true_ev_homes_selected |   profile_corr |   energy_ratio |   true_peak_hour |   est_peak_hour |
|:-------------|----:|-----------------:|-------------------------:|---------------:|---------------:|-----------------:|----------------:|
| pecan_austin | 1.5 |                6 |                        4 |          0.805 |          2.062 |               22 |              22 |
| pecan_austin | 2.5 |                5 |                        4 |          0.851 |          1.16  |               22 |              22 |
| pecan_austin | 3.5 |                4 |                        3 |          0.815 |          0.519 |               22 |              19 |

### 4. Sessions (k = 2.5; median over EV homes)

| kind      |   sessions |   start_hour_median |   hours_median |   hours_p90 |
|:----------|-----------:|--------------------:|---------------:|------------:|
| estimated |      186.5 |                16.5 |              1 |         3.5 |
| true      |      269.5 |                18.5 |              2 |         4   |

## pecan_newyork (development split; detector: load > same-hour 14-day median + k kW)

### 1. Which homes have an EV (score = share of EV-like hours)

| dataset       |   k |   ev_homes |   other_homes |   auc |   score_ev_median |   score_other_median |
|:--------------|----:|-----------:|--------------:|------:|------------------:|---------------------:|
| pecan_newyork | 1.5 |          4 |            16 | 0.812 |             0.082 |                0.04  |
| pecan_newyork | 2.5 |          4 |            16 | 0.828 |             0.045 |                0.01  |
| pecan_newyork | 3.5 |          4 |            16 | 0.828 |             0.023 |                0.002 |

### 2. When they charge (EV homes; median over homes)

|   k |   precision |   recall |
|----:|------------:|---------:|
| 1.5 |        0.55 |     0.77 |
| 2.5 |        0.59 |     0.54 |
| 3.5 |        0.72 |     0.38 |

### 3. EV energy by hour of day, group of development homes

| dataset       |   k |   homes_selected |   true_ev_homes_selected |   profile_corr |   energy_ratio |   true_peak_hour |   est_peak_hour |
|:--------------|----:|-----------------:|-------------------------:|---------------:|---------------:|-----------------:|----------------:|
| pecan_newyork | 1.5 |                7 |                        3 |          0.413 |          2.165 |                7 |              18 |
| pecan_newyork | 2.5 |                5 |                        3 |          0.461 |          1.241 |                7 |              18 |
| pecan_newyork | 3.5 |                4 |                        2 |          0.459 |          0.696 |                7 |              18 |

### 4. Sessions (k = 2.5; median over EV homes)

| kind      |   sessions |   start_hour_median |   hours_median |   hours_p90 |
|:----------|-----------:|--------------------:|---------------:|------------:|
| estimated |      104   |                  16 |              1 |         2   |
| true      |       85.5 |                  17 |              2 |         3.2 |
