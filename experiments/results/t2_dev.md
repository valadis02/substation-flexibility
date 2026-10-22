
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
