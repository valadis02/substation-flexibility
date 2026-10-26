# T12 - v0.10: EV inside the M5 envelope, participation (M6) for all (development data)

## 1. Hourly flexible load (weather + appliances + EV): unchanged decomposition

| dataset       |   homes |   ev_homes_true |   ev_homes_found |   flexible_awfe_p90 |   energy_ratio |
|:--------------|--------:|----------------:|-----------------:|--------------------:|---------------:|
| pecan_austin  |      20 |               4 |                4 |               0.293 |          0.745 |
| pecan_newyork |      17 |               3 |                1 |               0.248 |          0.788 |
| refit         |      13 |               0 |                0 |               0.242 |          0.916 |
| plegma        |       3 |               0 |                0 |               0.311 |          0.942 |

## 2. Envelope per hour of the average day vs the same rule on the true decomposition

err = mean |est - true| / mean load; ratio = est / true over the day; true_mean = true envelope / mean load. 'v0.9 M4 alone' is compared with the true envelope of all flexible load (EV included).

| dataset       | variant         |   down_kw_err |   down_kw_ratio |   up_kw_err |   up_kw_ratio |   down_ev_kw_err |   down_ev_kw_ratio |   up_ev_kw_err |   up_ev_kw_ratio |   down_true_mean |   up_true_mean |
|:--------------|:----------------|--------------:|----------------:|------------:|--------------:|-----------------:|-------------------:|---------------:|-----------------:|-----------------:|---------------:|
| pecan_austin  | v0.9 M4 alone   |         0.106 |           0.793 |       0.085 |         0.862 |            0.029 |              0     |          0.094 |            0     |            0.51  |          0.597 |
| pecan_austin  | v0.10 sessions  |         0.082 |           0.839 |       0.027 |         0.976 |            0.011 |              0.813 |          0.027 |            0.725 |            0.51  |          0.597 |
| pecan_austin  | v0.10 same rule |         0.081 |           0.84  |       0.023 |         1.021 |            0.009 |              0.833 |        nan     |          nan     |            0.508 |          0.497 |
| pecan_newyork | v0.9 M4 alone   |         0.055 |           0.785 |       0.049 |         0.868 |            0.026 |              0     |          0.094 |            0     |            0.223 |          0.273 |
| pecan_newyork | v0.10 sessions  |         0.05  |           0.816 |       0.04  |         0.979 |            0.019 |              0.266 |          0.063 |            0.323 |            0.223 |          0.273 |
| pecan_newyork | v0.10 same rule |         0.056 |           0.79  |       0.051 |         1.238 |            0.027 |              0.208 |        nan     |          nan     |            0.231 |          0.197 |
| refit         | v0.9 M4 alone   |         0.035 |           0.925 |       0.06  |         1.178 |            0     |            nan     |          0     |          nan     |            0.123 |          0.157 |
| refit         | v0.10 sessions  |         0.035 |           0.925 |       0.06  |         1.178 |            0     |            nan     |          0     |          nan     |            0.123 |          0.157 |
| refit         | v0.10 same rule |         0.035 |           0.925 |       0.06  |         1.178 |            0     |            nan     |        nan     |          nan     |            0.123 |          0.157 |
| plegma        | v0.9 M4 alone   |         0.043 |           0.946 |       0.092 |         1.032 |            0     |            nan     |          0     |          nan     |            0.304 |          0.636 |
| plegma        | v0.10 sessions  |         0.043 |           0.946 |       0.092 |         1.032 |            0     |            nan     |          0     |          nan     |            0.304 |          0.636 |
| plegma        | v0.10 same rule |         0.043 |           0.946 |       0.092 |         1.032 |            0     |            nan     |        nan     |          nan     |            0.304 |          0.636 |

## 3. Participation 0.1: est / true

| dataset       | column   |   true_kw_day |   v09_ratio |   v10_ratio |
|:--------------|:---------|--------------:|------------:|------------:|
| pecan_austin  | down_kw  |        36.717 |       1.252 |       0.839 |
| pecan_austin  | up_kw    |        42.967 |       2.001 |       0.976 |
| pecan_newyork | down_kw  |         8.718 |       1.095 |       0.816 |
| pecan_newyork | up_kw    |        10.646 |       1.98  |       0.979 |
| refit         | down_kw  |         1.866 |       0.925 |       0.925 |
| refit         | up_kw    |         2.371 |       1.178 |       1.178 |
| plegma        | down_kw  |         0.604 |       0.946 |       0.946 |
| plegma        | up_kw    |         1.262 |       1.032 |       1.032 |
