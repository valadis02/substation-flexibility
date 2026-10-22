
## plegma (development split; leave-one-week-out; T0 grid 16.0-26.0 step 0.5)

Homes with AC; medians over homes. share_err = estimated - true thermal share of energy; daily_err_rel = mean |daily thermal - daily AC| / mean daily AC.

### T0 = 18

| variant   | season   |   corr_hourly |   corr_daily |   share_err |   daily_err_rel |
|:----------|:---------|--------------:|-------------:|------------:|----------------:|
| full      | all      |         0.337 |        0.607 |      -0.032 |           1.003 |
| full      | cooling  |         0.304 |        0.579 |      -0.115 |           0.91  |
| full      | heating  |        -0.023 |       -0.059 |       0.002 |           1.507 |
| nolag     | all      |         0.343 |        0.585 |       0.04  |           1.269 |
| nolag     | cooling  |         0.288 |        0.505 |       0.009 |           0.905 |
| nolag     | heating  |         0.022 |        0.129 |       0.063 |           1.544 |

### T0 = 20

| variant   | season   |   corr_hourly |   corr_daily |   share_err |   daily_err_rel |
|:----------|:---------|--------------:|-------------:|------------:|----------------:|
| full      | all      |         0.339 |        0.619 |      -0.028 |           1.018 |
| full      | cooling  |         0.311 |        0.61  |      -0.114 |           0.888 |
| full      | heating  |        -0.022 |       -0.068 |       0.01  |           1.593 |
| nolag     | all      |         0.339 |        0.564 |       0.054 |           1.278 |
| nolag     | cooling  |         0.285 |        0.459 |      -0.006 |           0.936 |
| nolag     | heating  |         0.006 |        0.074 |       0.071 |           2.333 |

### T0 = 22

| variant   | season   |   corr_hourly |   corr_daily |   share_err |   daily_err_rel |
|:----------|:---------|--------------:|-------------:|------------:|----------------:|
| full      | all      |         0.338 |        0.617 |      -0.026 |           1.022 |
| full      | cooling  |         0.304 |        0.606 |      -0.12  |           0.889 |
| full      | heating  |        -0.021 |       -0.069 |       0.018 |           1.57  |
| nolag     | all      |         0.332 |        0.569 |       0.006 |           1.162 |
| nolag     | cooling  |         0.289 |        0.454 |      -0.045 |           0.926 |
| nolag     | heating  |         0.035 |        0.092 |       0.062 |           1.955 |

### Best T0 by daily_err_rel

| variant   | season   |   t0 |   corr_hourly |   corr_daily |   share_err |   daily_err_rel |
|:----------|:---------|-----:|--------------:|-------------:|------------:|----------------:|
| full      | all      | 17   |         0.326 |        0.598 |      -0.031 |           0.912 |
| full      | cooling  | 20.5 |         0.305 |        0.603 |      -0.118 |           0.886 |
| full      | heating  | 18.5 |        -0.023 |       -0.057 |      -0.003 |           1.43  |
| nolag     | all      | 22   |         0.332 |        0.569 |       0.006 |           1.162 |
| nolag     | cooling  | 19.5 |         0.284 |        0.467 |       0.006 |           0.895 |
| nolag     | heating  | 18.5 |         0.019 |        0.103 |       0.039 |           1.225 |

### Balance point (one-break V fit on daily means)

| home   | has_ac   |   tb_aggregate |   tb_ac |   secs |
|:-------|:---------|---------------:|--------:|-------:|
| H02    | True     |          12    |   12    |     37 |
| H04    | True     |          12    |   12    |     78 |
| H05    | True     |          26.75 |   26.5  |     54 |
| H06    | False    |          28    |  nan    |     39 |
| H07    | True     |          17.5  |   28    |     77 |
| H08    | True     |          26    |   12    |     45 |
| H09    | False    |          23.5  |  nan    |     54 |
| H11    | True     |          22    |   23.25 |     34 |
| H12    | True     |          28    |   28    |     48 |
| H13    | True     |          22.25 |   26    |     62 |

### Negative control (homes without AC): estimated thermal share, by T0

|   t0 |   full |   nolag |
|-----:|-------:|--------:|
| 16   |  0.156 |   0.254 |
| 16.5 |  0.159 |   0.326 |
| 17   |  0.16  |   0.288 |
| 17.5 |  0.16  |   0.209 |
| 18   |  0.158 |   0.212 |
| 18.5 |  0.158 |   0.22  |
| 19   |  0.158 |   0.227 |
| 19.5 |  0.158 |   0.233 |
| 20   |  0.152 |   0.209 |
| 20.5 |  0.16  |   0.239 |
| 21   |  0.162 |   0.235 |
| 21.5 |  0.162 |   0.247 |
| 22   |  0.163 |   0.24  |
| 22.5 |  0.159 |   0.231 |
| 23   |  0.16  |   0.232 |
| 23.5 |  0.162 |   0.246 |
| 24   |  0.158 |   0.238 |
| 24.5 |  0.155 |   0.21  |
| 25   |  0.153 |   0.208 |
| 25.5 |  0.151 |   0.2   |
| 26   |  0.149 |   0.194 |

## v2 (pecan_austin): seasonal features, no clip, balance-point band (development split, leave-one-week-out)

Medians over units of each kind. 'v1' = method features as in T2 v1 (now without the clip); 'seasonal' = plus day of year and day length, fixed in the counterfactual; 'band' = temperature clipped to the balance points fitted on the training fold.

### pecan_austin, ac (20 units)

|                                    |   corr_hourly |   corr_daily |   share_est |   share_true |   share_err |   daily_err_rel |
|:-----------------------------------|--------------:|-------------:|------------:|-------------:|------------:|----------------:|
| ('seasonal', 'T0=20.0', 'all')     |         0.855 |        0.948 |       0.356 |        0.544 |      -0.189 |           0.342 |
| ('seasonal', 'T0=20.0', 'cooling') |         0.805 |        0.864 |       0.449 |        0.657 |      -0.203 |           0.324 |
| ('seasonal', 'T0=20.0', 'heating') |         0.554 |        0.75  |       0.062 |        0.188 |      -0.096 |           0.677 |
| ('seasonal', 'band', 'all')        |         0.856 |        0.949 |       0.384 |        0.544 |      -0.17  |           0.332 |
| ('seasonal', 'band', 'cooling')    |         0.805 |        0.866 |       0.481 |        0.657 |      -0.189 |           0.298 |
| ('seasonal', 'band', 'heating')    |         0.559 |        0.747 |       0.079 |        0.188 |      -0.099 |           0.69  |
| ('v1', 'T0=20.0', 'all')           |         0.849 |        0.943 |       0.347 |        0.544 |      -0.19  |           0.37  |
| ('v1', 'T0=20.0', 'cooling')       |         0.801 |        0.835 |       0.438 |        0.657 |      -0.226 |           0.352 |
| ('v1', 'T0=20.0', 'heating')       |         0.552 |        0.75  |       0.058 |        0.188 |      -0.095 |           0.67  |
| ('v1', 'band', 'all')              |         0.85  |        0.942 |       0.359 |        0.544 |      -0.179 |           0.356 |
| ('v1', 'band', 'cooling')          |         0.807 |        0.837 |       0.451 |        0.657 |      -0.209 |           0.338 |
| ('v1', 'band', 'heating')          |         0.562 |        0.744 |       0.081 |        0.188 |      -0.093 |           0.695 |

### pecan_austin, control (1 units)

|                                    |   corr_hourly |   corr_daily |   share_est |   share_true |   share_err |   daily_err_rel |
|:-----------------------------------|--------------:|-------------:|------------:|-------------:|------------:|----------------:|
| ('seasonal', 'T0=20.0', 'all')     |         0.783 |        0.851 |       0.301 |        0.098 |       0.203 |           2.236 |
| ('seasonal', 'T0=20.0', 'cooling') |         0.832 |        0.891 |       0.391 |        0.108 |       0.283 |           2.643 |
| ('seasonal', 'T0=20.0', 'heating') |         0.302 |        0.439 |       0.077 |        0.091 |      -0.014 |           0.663 |
| ('seasonal', 'band', 'all')        |         0.784 |        0.853 |       0.304 |        0.098 |       0.206 |           2.231 |
| ('seasonal', 'band', 'cooling')    |         0.832 |        0.891 |       0.391 |        0.108 |       0.283 |           2.643 |
| ('seasonal', 'band', 'heating')    |         0.322 |        0.476 |       0.089 |        0.091 |      -0.002 |           0.62  |
| ('v1', 'T0=20.0', 'all')           |         0.779 |        0.85  |       0.299 |        0.098 |       0.201 |           2.225 |
| ('v1', 'T0=20.0', 'cooling')       |         0.827 |        0.877 |       0.389 |        0.108 |       0.28  |           2.626 |
| ('v1', 'T0=20.0', 'heating')       |         0.306 |        0.487 |       0.082 |        0.091 |      -0.009 |           0.709 |
| ('v1', 'band', 'all')              |         0.779 |        0.85  |       0.302 |        0.098 |       0.204 |           2.218 |
| ('v1', 'band', 'cooling')          |         0.827 |        0.877 |       0.389 |        0.108 |       0.281 |           2.627 |
| ('v1', 'band', 'heating')          |         0.313 |        0.493 |       0.093 |        0.091 |       0.002 |           0.66  |

### Groups (all development homes summed), all metrics

| dataset      | unit            | model    | counterfactual   | season   |   hours |   corr_hourly |   corr_daily |   share_est |   share_true |   share_est_clipped |   daily_err_rel |   share_err |
|:-------------|:----------------|:---------|:-----------------|:---------|--------:|--------------:|-------------:|------------:|-------------:|--------------------:|----------------:|------------:|
| pecan_austin | group(20 homes) | v1       | T0=20.0          | all      |    6812 |         0.849 |        0.985 |       0.343 |        0.523 |               0.347 |           0.344 |      -0.179 |
| pecan_austin | group(20 homes) | v1       | T0=20.0          | cooling  |    3646 |         0.952 |        0.953 |       0.447 |        0.636 |               0.447 |           0.298 |      -0.189 |
| pecan_austin | group(20 homes) | v1       | T0=20.0          | heating  |    1990 |         0.772 |        0.883 |       0.056 |        0.22  |               0.072 |           0.744 |      -0.164 |
| pecan_austin | group(20 homes) | v1       | band             | all      |    6812 |         0.849 |        0.984 |       0.355 |        0.523 |               0.356 |           0.323 |      -0.168 |
| pecan_austin | group(20 homes) | v1       | band             | cooling  |    3646 |         0.952 |        0.953 |       0.454 |        0.636 |               0.454 |           0.288 |      -0.182 |
| pecan_austin | group(20 homes) | v1       | band             | heating  |    1990 |         0.779 |        0.868 |       0.083 |        0.22  |               0.085 |           0.625 |      -0.137 |
| pecan_austin | group(20 homes) | seasonal | T0=20.0          | all      |    6812 |         0.85  |        0.984 |       0.354 |        0.523 |               0.358 |           0.325 |      -0.169 |
| pecan_austin | group(20 homes) | seasonal | T0=20.0          | cooling  |    3646 |         0.95  |        0.948 |       0.46  |        0.636 |               0.46  |           0.278 |      -0.175 |
| pecan_austin | group(20 homes) | seasonal | T0=20.0          | heating  |    1990 |         0.769 |        0.879 |       0.05  |        0.22  |               0.066 |           0.773 |      -0.17  |
| pecan_austin | group(20 homes) | seasonal | band             | all      |    6812 |         0.85  |        0.984 |       0.367 |        0.523 |               0.368 |           0.3   |      -0.156 |
| pecan_austin | group(20 homes) | seasonal | band             | cooling  |    3646 |         0.95  |        0.95  |       0.468 |        0.636 |               0.468 |           0.266 |      -0.167 |
| pecan_austin | group(20 homes) | seasonal | band             | heating  |    1990 |         0.771 |        0.864 |       0.08  |        0.22  |               0.082 |           0.635 |      -0.14  |

### Sensitivity to fixed T0 (seasonal model, all seasons, AC/heater units): median daily_err_rel and share_err

| counterfactual   |   ('daily_err_rel', 'pecan_austin') |   ('share_err', 'pecan_austin') |   ('corr_daily', 'pecan_austin') |
|:-----------------|------------------------------------:|--------------------------------:|---------------------------------:|
| T0=16.0          |                               0.349 |                          -0.183 |                            0.949 |
| T0=16.5          |                               0.344 |                          -0.183 |                            0.948 |
| T0=17.0          |                               0.343 |                          -0.183 |                            0.948 |
| T0=17.5          |                               0.339 |                          -0.182 |                            0.948 |
| T0=18.0          |                               0.337 |                          -0.183 |                            0.948 |
| T0=18.5          |                               0.334 |                          -0.184 |                            0.948 |
| T0=19.0          |                               0.333 |                          -0.186 |                            0.948 |
| T0=19.5          |                               0.335 |                          -0.188 |                            0.948 |
| T0=20.0          |                               0.342 |                          -0.189 |                            0.948 |
| T0=20.5          |                               0.367 |                          -0.191 |                            0.948 |
| T0=21.0          |                               0.381 |                          -0.198 |                            0.948 |
| T0=21.5          |                               0.424 |                          -0.229 |                            0.946 |
| T0=22.0          |                               0.473 |                          -0.267 |                            0.944 |
| T0=22.5          |                               0.529 |                          -0.293 |                            0.944 |
| T0=23.0          |                               0.586 |                          -0.328 |                            0.94  |
| T0=23.5          |                               0.636 |                          -0.34  |                            0.936 |
| T0=24.0          |                               0.671 |                          -0.366 |                            0.934 |
| T0=24.5          |                               0.757 |                          -0.427 |                            0.928 |
| T0=25.0          |                               0.794 |                          -0.436 |                            0.926 |
| T0=25.5          |                               0.901 |                          -0.487 |                            0.916 |
| T0=26.0          |                               0.959 |                          -0.519 |                            0.905 |

### Balance points from the data (median over folds; IQR = spread across folds)

| dataset      | unit            | kind    |   Th_median |   Tc_median |   Th_iqr |   Tc_iqr |   secs |
|:-------------|:----------------|:--------|------------:|------------:|---------:|---------:|-------:|
| pecan_austin | P1642           | ac      |        17   |        17   |      0   |      0   |    113 |
| pecan_austin | P2335           | ac      |        11.5 |        19.5 |      0.5 |      0.5 |    117 |
| pecan_austin | P2818           | ac      |        10   |        20   |      0   |      0   |    109 |
| pecan_austin | P3039           | ac      |        10   |        13   |      0   |      0   |    122 |
| pecan_austin | P3456           | ac      |        17.5 |        21   |      0   |      0   |    115 |
| pecan_austin | P3538           | ac      |        14.5 |        21   |      3   |      0.5 |    107 |
| pecan_austin | P4031           | control |        17.5 |        20   |      0   |      0   |    108 |
| pecan_austin | P4767           | ac      |        12.5 |        20.5 |      0   |      0   |    108 |
| pecan_austin | P5746           | ac      |        10   |        21   |      0   |      0   |    114 |
| pecan_austin | P6139           | ac      |        14.5 |        22.5 |      0   |      0.5 |    107 |
| pecan_austin | P7536           | ac      |        10   |        20   |      0.5 |      0   |    110 |
| pecan_austin | P7719           | ac      |        10   |        18.5 |      0   |      0.5 |    112 |
| pecan_austin | P7901           | ac      |        10   |        19   |      0   |      0   |    113 |
| pecan_austin | P8156           | ac      |        13   |        16.5 |      0   |      0   |    113 |
| pecan_austin | P8386           | ac      |        15   |        22   |      0   |      0   |    121 |
| pecan_austin | P8565           | ac      |        12.5 |        12.5 |      0   |      0   |    116 |
| pecan_austin | P9019           | ac      |        19   |        21.5 |      0.5 |      0   |    114 |
| pecan_austin | P9160           | ac      |        12   |        20   |      0.5 |      0   |    109 |
| pecan_austin | P9278           | ac      |        11.5 |        23   |      0   |      0   |    100 |
| pecan_austin | P9922           | ac      |        10   |        10   |      0   |      0   |    107 |
| pecan_austin | group(20 homes) | ac      |        11   |        19.5 |      1   |      0.5 |    119 |

## v2 (pecan_newyork, pecan_california): seasonal features, no clip, balance-point band (development split, leave-one-week-out)

Medians over units of each kind. 'v1' = method features as in T2 v1 (now without the clip); 'seasonal' = plus day of year and day length, fixed in the counterfactual; 'band' = temperature clipped to the balance points fitted on the training fold.

### pecan_california, ac (19 units)

|                                    |   corr_hourly |   corr_daily |   share_est |   share_true |   share_err |   daily_err_rel |
|:-----------------------------------|--------------:|-------------:|------------:|-------------:|------------:|----------------:|
| ('seasonal', 'T0=20.0', 'all')     |         0.438 |        0.722 |       0.07  |        0.243 |      -0.168 |           0.779 |
| ('seasonal', 'T0=20.0', 'cooling') |         0.438 |        0.714 |       0.105 |        0.309 |      -0.22  |           0.752 |
| ('seasonal', 'T0=20.0', 'heating') |         0.031 |        0.097 |      -0.006 |        0.059 |      -0.069 |           1.401 |
| ('seasonal', 'band', 'all')        |         0.436 |        0.719 |       0.09  |        0.243 |      -0.116 |           0.776 |
| ('seasonal', 'band', 'cooling')    |         0.437 |        0.708 |       0.129 |        0.309 |      -0.191 |           0.76  |
| ('seasonal', 'band', 'heating')    |         0.057 |        0.101 |       0.015 |        0.059 |      -0.039 |           1.025 |
| ('v1', 'T0=20.0', 'all')           |         0.437 |        0.68  |       0.066 |        0.243 |      -0.15  |           0.831 |
| ('v1', 'T0=20.0', 'cooling')       |         0.442 |        0.702 |       0.094 |        0.309 |      -0.222 |           0.789 |
| ('v1', 'T0=20.0', 'heating')       |         0.083 |        0.175 |      -0.007 |        0.059 |      -0.065 |           1.574 |
| ('v1', 'band', 'all')              |         0.444 |        0.671 |       0.089 |        0.243 |      -0.117 |           0.799 |
| ('v1', 'band', 'cooling')          |         0.441 |        0.695 |       0.124 |        0.309 |      -0.2   |           0.775 |
| ('v1', 'band', 'heating')          |         0.065 |        0.16  |       0.023 |        0.059 |      -0.03  |           1.087 |

### pecan_newyork, ac (10 units)

|                                    |   corr_hourly |   corr_daily |   share_est |   share_true |   share_err |   daily_err_rel |
|:-----------------------------------|--------------:|-------------:|------------:|-------------:|------------:|----------------:|
| ('seasonal', 'T0=20.0', 'all')     |         0.517 |        0.695 |       0.061 |        0.215 |      -0.097 |           0.776 |
| ('seasonal', 'T0=20.0', 'cooling') |         0.517 |        0.695 |       0.061 |        0.215 |      -0.097 |           0.776 |
| ('seasonal', 'band', 'all')        |         0.527 |        0.695 |       0.076 |        0.215 |      -0.102 |           0.781 |
| ('seasonal', 'band', 'cooling')    |         0.527 |        0.695 |       0.076 |        0.215 |      -0.102 |           0.781 |
| ('v1', 'T0=20.0', 'all')           |         0.504 |        0.66  |       0.059 |        0.215 |      -0.097 |           0.735 |
| ('v1', 'T0=20.0', 'cooling')       |         0.504 |        0.66  |       0.059 |        0.215 |      -0.097 |           0.735 |
| ('v1', 'band', 'all')              |         0.546 |        0.677 |       0.07  |        0.215 |      -0.105 |           0.753 |
| ('v1', 'band', 'cooling')          |         0.546 |        0.677 |       0.07  |        0.215 |      -0.105 |           0.753 |

### pecan_newyork, control (11 units)

|                                    |   corr_hourly |   corr_daily |   share_est |   share_true |   share_err |   daily_err_rel |
|:-----------------------------------|--------------:|-------------:|------------:|-------------:|------------:|----------------:|
| ('seasonal', 'T0=20.0', 'all')     |        -0.031 |       -0.066 |       0.05  |        0.029 |      -0.011 |           1.308 |
| ('seasonal', 'T0=20.0', 'cooling') |        -0.031 |       -0.066 |       0.05  |        0.029 |      -0.011 |           1.308 |
| ('seasonal', 'band', 'all')        |        -0.028 |       -0.081 |       0.058 |        0.038 |       0.017 |           1.501 |
| ('seasonal', 'band', 'cooling')    |        -0.028 |       -0.081 |       0.058 |        0.038 |       0.017 |           1.501 |
| ('v1', 'T0=20.0', 'all')           |        -0.007 |       -0.083 |       0.038 |        0.029 |      -0.009 |           1.39  |
| ('v1', 'T0=20.0', 'cooling')       |        -0.007 |       -0.083 |       0.038 |        0.029 |      -0.009 |           1.39  |
| ('v1', 'band', 'all')              |         0.034 |        0.002 |       0.058 |        0.038 |       0.01  |           1.426 |
| ('v1', 'band', 'cooling')          |         0.034 |        0.002 |       0.058 |        0.038 |       0.01  |           1.426 |

### Groups (all development homes summed), all metrics

| dataset       | unit            | model    | counterfactual   | season   |   hours |   corr_hourly |   corr_daily |   share_est |   share_true |   share_est_clipped |   daily_err_rel |   share_err |
|:--------------|:----------------|:---------|:-----------------|:---------|--------:|--------------:|-------------:|------------:|-------------:|--------------------:|----------------:|------------:|
| pecan_newyork | group(20 homes) | v1       | T0=20.0          | all      |    3364 |         0.726 |        0.794 |       0.059 |        0.145 |               0.062 |           0.597 |      -0.086 |
| pecan_newyork | group(20 homes) | v1       | T0=20.0          | cooling  |    3364 |         0.726 |        0.794 |       0.059 |        0.145 |               0.062 |           0.597 |      -0.086 |
| pecan_newyork | group(20 homes) | v1       | band             | all      |    3364 |         0.73  |        0.791 |       0.056 |        0.145 |               0.057 |           0.621 |      -0.09  |
| pecan_newyork | group(20 homes) | v1       | band             | cooling  |    3364 |         0.73  |        0.791 |       0.056 |        0.145 |               0.057 |           0.621 |      -0.09  |
| pecan_newyork | group(20 homes) | seasonal | T0=20.0          | all      |    3364 |         0.735 |        0.798 |       0.057 |        0.145 |               0.06  |           0.613 |      -0.088 |
| pecan_newyork | group(20 homes) | seasonal | T0=20.0          | cooling  |    3364 |         0.735 |        0.798 |       0.057 |        0.145 |               0.06  |           0.613 |      -0.088 |
| pecan_newyork | group(20 homes) | seasonal | band             | all      |    3364 |         0.743 |        0.801 |       0.056 |        0.145 |               0.057 |           0.618 |      -0.089 |
| pecan_newyork | group(20 homes) | seasonal | band             | cooling  |    3364 |         0.743 |        0.801 |       0.056 |        0.145 |               0.057 |           0.618 |      -0.089 |

### Sensitivity to fixed T0 (seasonal model, all seasons, AC/heater units): median daily_err_rel and share_err

| counterfactual   |   ('daily_err_rel', 'pecan_california') |   ('daily_err_rel', 'pecan_newyork') |   ('share_err', 'pecan_california') |   ('share_err', 'pecan_newyork') |   ('corr_daily', 'pecan_california') |   ('corr_daily', 'pecan_newyork') |
|:-----------------|----------------------------------------:|-------------------------------------:|------------------------------------:|---------------------------------:|-------------------------------------:|----------------------------------:|
| T0=16.0          |                                   0.786 |                                0.735 |                              -0.124 |                           -0.081 |                                0.718 |                             0.694 |
| T0=16.5          |                                   0.773 |                                0.739 |                              -0.15  |                           -0.078 |                                0.722 |                             0.698 |
| T0=17.0          |                                   0.779 |                                0.737 |                              -0.145 |                           -0.078 |                                0.723 |                             0.698 |
| T0=17.5          |                                   0.78  |                                0.751 |                              -0.151 |                           -0.081 |                                0.723 |                             0.7   |
| T0=18.0          |                                   0.778 |                                0.759 |                              -0.15  |                           -0.081 |                                0.725 |                             0.702 |
| T0=18.5          |                                   0.776 |                                0.755 |                              -0.138 |                           -0.082 |                                0.723 |                             0.705 |
| T0=19.0          |                                   0.781 |                                0.765 |                              -0.148 |                           -0.084 |                                0.723 |                             0.701 |
| T0=19.5          |                                   0.776 |                                0.771 |                              -0.143 |                           -0.084 |                                0.722 |                             0.698 |
| T0=20.0          |                                   0.779 |                                0.776 |                              -0.168 |                           -0.097 |                                0.722 |                             0.695 |
| T0=20.5          |                                   0.865 |                                0.792 |                              -0.173 |                           -0.105 |                                0.722 |                             0.695 |
| T0=21.0          |                                   0.895 |                                0.803 |                              -0.188 |                           -0.109 |                                0.713 |                             0.695 |
| T0=21.5          |                                   0.972 |                                0.813 |                              -0.211 |                           -0.11  |                                0.699 |                             0.695 |
| T0=22.0          |                                   1.021 |                                0.84  |                              -0.221 |                           -0.111 |                                0.679 |                             0.691 |
| T0=22.5          |                                   1.082 |                                0.855 |                              -0.232 |                           -0.147 |                                0.602 |                             0.678 |
| T0=23.0          |                                   1.246 |                                0.954 |                              -0.311 |                           -0.203 |                                0.529 |                             0.667 |
| T0=23.5          |                                   1.409 |                                1.027 |                              -0.347 |                           -0.232 |                                0.53  |                             0.666 |
| T0=24.0          |                                   1.634 |                                1.333 |                              -0.367 |                           -0.321 |                                0.484 |                             0.67  |
| T0=24.5          |                                   1.768 |                                1.483 |                              -0.401 |                           -0.344 |                                0.495 |                             0.648 |
| T0=25.0          |                                   2.053 |                                1.601 |                              -0.447 |                           -0.392 |                                0.385 |                             0.624 |
| T0=25.5          |                                   2.088 |                                1.857 |                              -0.537 |                           -0.432 |                                0.293 |                             0.621 |
| T0=26.0          |                                   2.552 |                                1.968 |                              -0.655 |                           -0.513 |                                0.247 |                             0.584 |

### Balance points from the data (median over folds; IQR = spread across folds)

| dataset          | unit            | kind    |   Th_median |   Tc_median |   Th_iqr |   Tc_iqr |   secs |
|:-----------------|:----------------|:--------|------------:|------------:|---------:|---------:|-------:|
| pecan_newyork    | P142            | control |        10   |        10   |      0   |      0   |     49 |
| pecan_newyork    | P387            | control |        13   |        13.5 |      0   |      1   |     50 |
| pecan_newyork    | P914            | control |        12   |        24   |      0.5 |      0   |     46 |
| pecan_newyork    | P950            | ac      |        15.5 |        16.5 |      0   |      0   |     50 |
| pecan_newyork    | P1222           | control |        12.5 |        18.5 |      0   |      0   |     49 |
| pecan_newyork    | P1240           | ac      |        16   |        16.5 |      0.5 |      0   |     49 |
| pecan_newyork    | P1417           | ac      |        20   |        20.5 |      0.5 |      0.5 |     50 |
| pecan_newyork    | P2318           | control |        20.5 |        21   |      0.5 |      0   |     46 |
| pecan_newyork    | P2358           | control |        15.5 |        15.5 |      0.5 |      1   |     44 |
| pecan_newyork    | P3000           | ac      |        12   |        12   |      0   |      0   |     47 |
| pecan_newyork    | P3488           | ac      |        16   |        22   |      0   |      0   |     48 |
| pecan_newyork    | P3517           | ac      |        12.5 |        21.5 |      0   |      0   |     48 |
| pecan_newyork    | P3996           | control |        11.5 |        23.5 |      0.5 |      0   |     47 |
| pecan_newyork    | P4550           | control |        25   |        25   |      0   |      0   |     47 |
| pecan_newyork    | P5058           | ac      |        13   |        23.5 |      0   |      0   |     46 |
| pecan_newyork    | P5587           | ac      |        13   |        18.5 |      0   |      0   |     47 |
| pecan_newyork    | P5679           | ac      |        10   |        18   |      0   |      0   |     46 |
| pecan_newyork    | P5982           | control |        10   |        10   |      0   |      0   |     47 |
| pecan_newyork    | P5997           | control |        10.5 |        24   |      0   |      0   |     47 |
| pecan_newyork    | P9053           | control |        10.5 |        20.5 |      0   |      0   |     48 |
| pecan_newyork    | group(20 homes) | ac      |        13   |        21   |      0   |      0   |     47 |
| pecan_california | P1450           | ac      |        15.5 |        15.5 |      0   |      0   |    106 |
| pecan_california | P1524           | ac      |        10   |        17   |      0   |      0   |    109 |
| pecan_california | P2606           | ac      |        13.5 |        18.5 |      0   |      0.5 |    125 |
| pecan_california | P3687           | ac      |        11.5 |        16   |      0.5 |      0   |    117 |
| pecan_california | P3864           | ac      |        10   |        20.5 |      0   |      0   |    105 |
| pecan_california | P3938           | ac      |        16   |        21   |      0   |      0   |    103 |
| pecan_california | P4495           | ac      |        10   |        16   |      4   |      2   |    110 |
| pecan_california | P4934           | ac      |        11.5 |        21   |      0   |      0   |    111 |
| pecan_california | P5938           | ac      |        14.5 |        25   |      0.5 |      0   |    105 |
| pecan_california | P6377           | ac      |        13   |        15.5 |      0.5 |      0.5 |    105 |
| pecan_california | P6547           | ac      |        13.5 |        20.5 |      0   |      0   |    117 |
| pecan_california | P7062           | ac      |        10   |        19   |      0   |      0.5 |    109 |
| pecan_california | P8061           | ac      |        17   |        18.5 |      0.5 |      0   |    113 |
| pecan_california | P8342           | ac      |        17   |        18.5 |      0   |      0   |    105 |
| pecan_california | P8733           | ac      |        10   |        17.5 |      0   |      0   |    107 |
| pecan_california | P9213           | ac      |        10   |        19   |      0   |      0   |    102 |
| pecan_california | P9612           | ac      |        16.5 |        16.5 |      6.5 |      0.5 |    111 |
| pecan_california | P9775           | ac      |        17.5 |        19   |      0.5 |      0.5 |    108 |
| pecan_california | P9836           | ac      |        12.5 |        22   |      0   |      0   |    109 |

## v2 (plegma, refit): seasonal features, no clip, balance-point band (development split, leave-one-week-out)

Medians over units of each kind. 'v1' = method features as in T2 v1 (now without the clip); 'seasonal' = plus day of year and day length, fixed in the counterfactual; 'band' = temperature clipped to the balance points fitted on the training fold.

### plegma, ac (9 units)

|                                    |   corr_hourly |   corr_daily |   share_est |   share_true |   share_err |   daily_err_rel |
|:-----------------------------------|--------------:|-------------:|------------:|-------------:|------------:|----------------:|
| ('seasonal', 'T0=20.0', 'all')     |         0.395 |        0.685 |       0.09  |        0.138 |      -0.057 |           1.137 |
| ('seasonal', 'T0=20.0', 'cooling') |         0.38  |        0.568 |       0.072 |        0.205 |      -0.119 |           0.956 |
| ('seasonal', 'T0=20.0', 'heating') |         0.018 |        0.074 |       0.085 |        0.062 |      -0.035 |           1.25  |
| ('seasonal', 'band', 'all')        |         0.239 |        0.565 |       0.082 |        0.144 |      -0.087 |           1.027 |
| ('seasonal', 'band', 'cooling')    |         0.261 |        0.534 |       0.053 |        0.219 |      -0.16  |           0.973 |
| ('seasonal', 'band', 'heating')    |         0.064 |        0.359 |       0.048 |        0.062 |      -0.063 |           1.126 |
| ('v1', 'T0=20.0', 'all')           |         0.356 |        0.603 |       0.089 |        0.138 |      -0.053 |           1.182 |
| ('v1', 'T0=20.0', 'cooling')       |         0.341 |        0.61  |       0.09  |        0.205 |      -0.101 |           0.92  |
| ('v1', 'T0=20.0', 'heating')       |        -0.025 |       -0.014 |       0.094 |        0.062 |      -0.034 |           1.441 |
| ('v1', 'band', 'all')              |         0.267 |        0.562 |       0.082 |        0.144 |      -0.077 |           1.055 |
| ('v1', 'band', 'cooling')          |         0.286 |        0.606 |       0.078 |        0.219 |      -0.132 |           0.951 |
| ('v1', 'band', 'heating')          |        -0.003 |       -0.062 |       0.061 |        0.062 |      -0.047 |           1.125 |

### plegma, control (2 units)

|                                    |   corr_hourly |   corr_daily |   share_est |   share_true |   share_err |   daily_err_rel |
|:-----------------------------------|--------------:|-------------:|------------:|-------------:|------------:|----------------:|
| ('seasonal', 'T0=20.0', 'all')     |           nan |          nan |       0.1   |            0 |       0.1   |             nan |
| ('seasonal', 'T0=20.0', 'cooling') |           nan |          nan |       0.18  |            0 |       0.18  |             nan |
| ('seasonal', 'T0=20.0', 'heating') |           nan |          nan |      -0.089 |            0 |      -0.089 |             nan |
| ('seasonal', 'band', 'all')        |           nan |          nan |       0.103 |            0 |       0.103 |             nan |
| ('seasonal', 'band', 'cooling')    |           nan |          nan |       0.179 |            0 |       0.179 |             nan |
| ('seasonal', 'band', 'heating')    |           nan |          nan |      -0.075 |            0 |      -0.075 |             nan |
| ('v1', 'T0=20.0', 'all')           |           nan |          nan |       0.12  |            0 |       0.12  |             nan |
| ('v1', 'T0=20.0', 'cooling')       |           nan |          nan |       0.202 |            0 |       0.202 |             nan |
| ('v1', 'T0=20.0', 'heating')       |           nan |          nan |      -0.054 |            0 |      -0.054 |             nan |
| ('v1', 'band', 'all')              |           nan |          nan |       0.127 |            0 |       0.127 |             nan |
| ('v1', 'band', 'cooling')          |           nan |          nan |       0.208 |            0 |       0.208 |             nan |
| ('v1', 'band', 'heating')          |           nan |          nan |      -0.04  |            0 |      -0.04  |             nan |

### refit, control (2 units)

|                                    |   corr_hourly |   corr_daily |   share_est |   share_true |   share_err |   daily_err_rel |
|:-----------------------------------|--------------:|-------------:|------------:|-------------:|------------:|----------------:|
| ('seasonal', 'T0=20.0', 'all')     |           nan |          nan |       0.009 |            0 |       0.009 |             nan |
| ('seasonal', 'T0=20.0', 'cooling') |           nan |          nan |       0.009 |            0 |       0.009 |             nan |
| ('seasonal', 'T0=20.0', 'heating') |           nan |          nan |       0.017 |            0 |       0.017 |             nan |
| ('seasonal', 'band', 'all')        |           nan |          nan |       0.004 |            0 |       0.004 |             nan |
| ('seasonal', 'band', 'cooling')    |           nan |          nan |       0.002 |            0 |       0.002 |             nan |
| ('seasonal', 'band', 'heating')    |           nan |          nan |       0.012 |            0 |       0.012 |             nan |
| ('v1', 'T0=20.0', 'all')           |           nan |          nan |       0.023 |            0 |       0.023 |             nan |
| ('v1', 'T0=20.0', 'cooling')       |           nan |          nan |       0.009 |            0 |       0.009 |             nan |
| ('v1', 'T0=20.0', 'heating')       |           nan |          nan |       0.04  |            0 |       0.04  |             nan |
| ('v1', 'band', 'all')              |           nan |          nan |       0.021 |            0 |       0.021 |             nan |
| ('v1', 'band', 'cooling')          |           nan |          nan |       0.005 |            0 |       0.005 |             nan |
| ('v1', 'band', 'heating')          |           nan |          nan |       0.036 |            0 |       0.036 |             nan |

### refit, heater (3 units)

|                                    |   corr_hourly |   corr_daily |   share_est |   share_true |   share_err |   daily_err_rel |
|:-----------------------------------|--------------:|-------------:|------------:|-------------:|------------:|----------------:|
| ('seasonal', 'T0=20.0', 'all')     |         0.025 |        0.236 |       0.017 |        0.064 |      -0.028 |           0.985 |
| ('seasonal', 'T0=20.0', 'cooling') |         0.049 |        0.041 |      -0.002 |        0.029 |      -0.005 |           1.596 |
| ('seasonal', 'T0=20.0', 'heating') |         0.009 |        0.185 |       0.029 |        0.086 |      -0.045 |           0.943 |
| ('seasonal', 'band', 'all')        |         0.029 |        0.263 |       0.016 |        0.064 |      -0.017 |           0.981 |
| ('seasonal', 'band', 'cooling')    |        -0     |       -0.078 |      -0.002 |        0.029 |      -0.005 |           1.335 |
| ('seasonal', 'band', 'heating')    |         0.005 |        0.189 |       0.027 |        0.086 |      -0.024 |           0.95  |
| ('v1', 'T0=20.0', 'all')           |         0.042 |        0.251 |       0.028 |        0.064 |      -0.004 |           1.015 |
| ('v1', 'T0=20.0', 'cooling')       |         0.039 |        0.153 |       0.012 |        0.029 |      -0.008 |           1.653 |
| ('v1', 'T0=20.0', 'heating')       |         0.018 |        0.153 |       0.038 |        0.086 |      -0.006 |           0.991 |
| ('v1', 'band', 'all')              |         0.036 |        0.235 |       0.013 |        0.064 |      -0.004 |           1.059 |
| ('v1', 'band', 'cooling')          |         0.049 |        0.188 |       0.003 |        0.029 |      -0.006 |           1.623 |
| ('v1', 'band', 'heating')          |         0.018 |        0.117 |       0.02  |        0.086 |       0.003 |           1.002 |

### Plegma group (>= 6 homes present), all metrics

| model    | counterfactual   | season   |   hours |   corr_hourly |   corr_daily |   share_est |   share_true |   share_est_clipped |   daily_err_rel |   share_err |
|:---------|:-----------------|:---------|--------:|--------------:|-------------:|------------:|-------------:|--------------------:|----------------:|------------:|
| v1       | T0=20.0          | all      |    3314 |         0.681 |        0.885 |       0.096 |        0.151 |               0.112 |           0.513 |      -0.055 |
| v1       | T0=20.0          | cooling  |    2272 |         0.691 |        0.884 |       0.127 |        0.19  |               0.138 |           0.438 |      -0.063 |
| v1       | T0=20.0          | heating  |     336 |         0.164 |        0.095 |       0.009 |        0.063 |               0.042 |           1.346 |      -0.053 |
| v1       | band             | all      |    3314 |         0.687 |        0.894 |       0.091 |        0.151 |               0.093 |           0.479 |      -0.06  |
| v1       | band             | cooling  |    2272 |         0.69  |        0.891 |       0.124 |        0.19  |               0.124 |           0.431 |      -0.066 |
| v1       | band             | heating  |     336 |         0.017 |       -0.288 |       0.001 |        0.063 |               0.017 |           1.128 |      -0.062 |
| seasonal | T0=20.0          | all      |    3314 |         0.674 |        0.878 |       0.094 |        0.151 |               0.108 |           0.518 |      -0.057 |
| seasonal | T0=20.0          | cooling  |    2272 |         0.682 |        0.868 |       0.121 |        0.19  |               0.133 |           0.47  |      -0.068 |
| seasonal | T0=20.0          | heating  |     336 |         0.169 |        0.58  |       0.028 |        0.063 |               0.05  |           1.091 |      -0.035 |
| seasonal | band             | all      |    3314 |         0.683 |        0.896 |       0.091 |        0.151 |               0.092 |           0.476 |      -0.061 |
| seasonal | band             | cooling  |    2272 |         0.682 |        0.887 |       0.122 |        0.19  |               0.123 |           0.435 |      -0.068 |
| seasonal | band             | heating  |     336 |         0.111 |        0.732 |       0.009 |        0.063 |               0.015 |           0.947 |      -0.054 |

### Sensitivity to fixed T0 (seasonal model, all seasons, AC/heater units): median daily_err_rel and share_err

| counterfactual   |   ('daily_err_rel', 'plegma') |   ('daily_err_rel', 'refit') |   ('share_err', 'plegma') |   ('share_err', 'refit') |   ('corr_daily', 'plegma') |   ('corr_daily', 'refit') |
|:-----------------|------------------------------:|-----------------------------:|--------------------------:|-------------------------:|---------------------------:|--------------------------:|
| T0=16.0          |                         0.95  |                        1.701 |                    -0.101 |                   -0.104 |                      0.671 |                     0.204 |
| T0=16.5          |                         0.999 |                        1.709 |                    -0.073 |                   -0.104 |                      0.674 |                     0.196 |
| T0=17.0          |                         1.017 |                        1.595 |                    -0.069 |                   -0.101 |                      0.674 |                     0.22  |
| T0=17.5          |                         1.081 |                        0.963 |                    -0.051 |                   -0.019 |                      0.679 |                     0.255 |
| T0=18.0          |                         1.188 |                        0.983 |                    -0.066 |                   -0.009 |                      0.679 |                     0.263 |
| T0=18.5          |                         1.363 |                        0.971 |                    -0.08  |                   -0.013 |                      0.675 |                     0.267 |
| T0=19.0          |                         1.14  |                        0.967 |                    -0.063 |                   -0.022 |                      0.681 |                     0.275 |
| T0=19.5          |                         1.14  |                        0.972 |                    -0.06  |                   -0.025 |                      0.681 |                     0.266 |
| T0=20.0          |                         1.137 |                        0.985 |                    -0.057 |                   -0.028 |                      0.685 |                     0.236 |
| T0=20.5          |                         1.172 |                        0.98  |                    -0.062 |                   -0.024 |                      0.689 |                     0.235 |
| T0=21.0          |                         1.165 |                        1.054 |                    -0.054 |                   -0.046 |                      0.687 |                     0.223 |
| T0=21.5          |                         1.039 |                        1.052 |                    -0.045 |                   -0.046 |                      0.687 |                     0.228 |
| T0=22.0          |                         1.012 |                        1.123 |                    -0.043 |                   -0.055 |                      0.689 |                     0.239 |
| T0=22.5          |                         1.001 |                        1.124 |                    -0.042 |                   -0.055 |                      0.688 |                     0.24  |
| T0=23.0          |                         0.99  |                        1.124 |                    -0.044 |                   -0.055 |                      0.689 |                     0.24  |
| T0=23.5          |                         0.941 |                        1.124 |                    -0.044 |                   -0.055 |                      0.686 |                     0.24  |
| T0=24.0          |                         0.968 |                        1.124 |                    -0.045 |                   -0.055 |                      0.688 |                     0.24  |
| T0=24.5          |                         0.997 |                        1.124 |                    -0.049 |                   -0.055 |                      0.685 |                     0.24  |
| T0=25.0          |                         1.15  |                        1.124 |                    -0.057 |                   -0.055 |                      0.698 |                     0.24  |
| T0=25.5          |                         1.154 |                        1.124 |                    -0.057 |                   -0.055 |                      0.697 |                     0.24  |
| T0=26.0          |                         1.156 |                        1.124 |                    -0.059 |                   -0.055 |                      0.691 |                     0.24  |

### Balance points from the data (median over folds; IQR = spread across folds)

| dataset   | unit             | kind    |   Th_median |   Tc_median |   Th_iqr |   Tc_iqr |   secs |
|:----------|:-----------------|:--------|------------:|------------:|---------:|---------:|-------:|
| plegma    | H02              | ac      |        15   |        25   |     0    |      0   |     47 |
| plegma    | H04              | ac      |        11   |        25   |     0    |      0   |     97 |
| plegma    | H05              | ac      |       nan   |       nan   |   nan    |    nan   |     64 |
| plegma    | H06              | control |        15   |        26   |     0    |      1   |     49 |
| plegma    | H07              | ac      |        14.5 |        29   |     0    |      0   |     93 |
| plegma    | H08              | ac      |        16   |        27.5 |     0.5  |      0   |     57 |
| plegma    | H09              | control |        23   |        23   |     0    |      0.5 |     65 |
| plegma    | H11              | ac      |        20   |        22   |     0    |      0   |     42 |
| plegma    | H12              | ac      |        29.5 |        29.5 |     0    |      0   |     53 |
| plegma    | H13              | ac      |        18.5 |        26.5 |     0.12 |      0   |     96 |
| plegma    | group(>=6 homes) | ac      |        10   |        26   |     0    |      0   |     65 |
| refit     | H1               | heater  |        14.5 |        16   |     1    |      0.5 |    139 |
| refit     | H9               | heater  |        15   |        19.5 |     0    |      0   |    208 |
| refit     | H16              | heater  |        18   |        18   |     0    |      0   |   4862 |
| refit     | H3               | control |        18   |        22   |     0    |      0   |    861 |
| refit     | H5               | control |        21   |        21   |     0    |      0.5 |    172 |
