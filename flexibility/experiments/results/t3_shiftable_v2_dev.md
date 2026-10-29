# T3 v2 (development; leave-one-dataset-out bank)

## Largest group per dataset

|                                              |   energy_ratio |   corr_hourly |   corr_profile |   awfe_p90 |   awfe_skill |
|:---------------------------------------------|---------------:|--------------:|---------------:|-----------:|-------------:|
| ('pecan_austin', 'A2_events_minus_weather')  |          1.002 |         0.068 |          0.574 |      0.094 |        0.225 |
| ('pecan_austin', 'A_events')                 |          1.047 |         0.055 |          0.567 |      0.1   |        0.18  |
| ('pecan_austin', 'B_mean_abs')               |          0.863 |         0.048 |          0.584 |      0.077 |        0.369 |
| ('pecan_austin', 'B_mean_levelA2')           |          1.002 |         0.048 |          0.584 |      0.08  |        0.342 |
| ('pecan_austin', 'B_mean_share')             |          2.133 |         0.037 |          0.607 |      0.104 |        0.145 |
| ('pecan_austin', 'B_shape_abs')              |          1.231 |         0.037 |          0.455 |      0.095 |        0.222 |
| ('pecan_austin', 'B_shape_share')            |          3.069 |         0.03  |          0.521 |      0.154 |       -0.267 |
| ('pecan_austin', 'B_weighted_abs')           |          0.88  |         0.048 |          0.582 |      0.077 |        0.367 |
| ('pecan_austin', 'B_weighted_levelA2')       |          1.002 |         0.048 |          0.582 |      0.08  |        0.345 |
| ('pecan_austin', 'B_weighted_share')         |          2.147 |         0.037 |          0.605 |      0.104 |        0.148 |
| ('pecan_austin', 'old_m3_events')            |          1.843 |         0.041 |          0.224 |      0.149 |       -0.229 |
| ('pecan_austin', 'zero')                     |          0     |       nan     |        nan     |      0.122 |        0     |
| ('pecan_newyork', 'A2_events_minus_weather') |          1.019 |         0.565 |          0.878 |      0.125 |        0.176 |
| ('pecan_newyork', 'A_events')                |          1.015 |         0.533 |          0.881 |      0.128 |        0.159 |
| ('pecan_newyork', 'B_mean_abs')              |          0.784 |         0.327 |          0.745 |      0.104 |        0.316 |
| ('pecan_newyork', 'B_mean_levelA2')          |          1.019 |         0.327 |          0.745 |      0.105 |        0.309 |
| ('pecan_newyork', 'B_mean_share')            |          1.461 |         0.394 |          0.698 |      0.118 |        0.224 |
| ('pecan_newyork', 'B_shape_abs')             |          0.848 |         0.261 |          0.585 |      0.118 |        0.225 |
| ('pecan_newyork', 'B_shape_share')           |          2.172 |         0.347 |          0.632 |      0.197 |       -0.293 |
| ('pecan_newyork', 'B_weighted_abs')          |          0.808 |         0.327 |          0.744 |      0.103 |        0.321 |
| ('pecan_newyork', 'B_weighted_levelA2')      |          1.019 |         0.327 |          0.744 |      0.106 |        0.306 |
| ('pecan_newyork', 'B_weighted_share')        |          1.516 |         0.392 |          0.696 |      0.122 |        0.198 |
| ('pecan_newyork', 'old_m3_events')           |          1.615 |         0.462 |          0.572 |      0.169 |       -0.111 |
| ('pecan_newyork', 'zero')                    |          0     |       nan     |        nan     |      0.152 |        0     |
| ('plegma', 'A2_events_minus_weather')        |          4.729 |         0.257 |          0.567 |      0.454 |       -3.049 |
| ('plegma', 'A_events')                       |          4.722 |         0.26  |          0.525 |      0.451 |       -3.024 |
| ('plegma', 'B_mean_abs')                     |          4.986 |         0.103 |          0.424 |      0.603 |       -4.38  |
| ('plegma', 'B_mean_levelA2')                 |          4.729 |         0.103 |          0.424 |      0.57  |       -4.087 |
| ('plegma', 'B_mean_share')                   |          2.06  |         0.219 |          0.518 |      0.133 |       -0.188 |
| ('plegma', 'B_shape_abs')                    |          5.788 |         0.118 |          0.541 |      0.654 |       -4.833 |
| ('plegma', 'B_shape_share')                  |          3.059 |         0.224 |          0.564 |      0.191 |       -0.706 |
| ('plegma', 'B_weighted_abs')                 |          5.102 |         0.112 |          0.452 |      0.593 |       -4.287 |
| ('plegma', 'B_weighted_levelA2')             |          4.729 |         0.112 |          0.452 |      0.549 |       -3.895 |
| ('plegma', 'B_weighted_share')               |          1.981 |         0.226 |          0.542 |      0.124 |       -0.107 |
| ('plegma', 'old_m3_events')                  |          5.169 |         0.202 |          0.474 |      0.492 |       -3.391 |
| ('plegma', 'zero')                           |          0     |       nan     |        nan     |      0.112 |        0     |
| ('refit', 'A2_events_minus_weather')         |          1.147 |         0.544 |          0.85  |      0.202 |        0.16  |
| ('refit', 'A_events')                        |          1.149 |         0.542 |          0.85  |      0.202 |        0.158 |
| ('refit', 'B_mean_abs')                      |          0.835 |         0.346 |          0.749 |      0.185 |        0.23  |
| ('refit', 'B_mean_levelA2')                  |          1.147 |         0.346 |          0.749 |      0.218 |        0.093 |
| ('refit', 'B_mean_share')                    |          0.597 |         0.571 |          0.836 |      0.17  |        0.292 |
| ('refit', 'B_shape_abs')                     |          0.947 |         0.27  |          0.578 |      0.222 |        0.075 |
| ('refit', 'B_shape_share')                   |          1.106 |         0.512 |          0.743 |      0.195 |        0.189 |
| ('refit', 'B_weighted_abs')                  |          0.846 |         0.346 |          0.748 |      0.187 |        0.223 |
| ('refit', 'B_weighted_levelA2')              |          1.147 |         0.346 |          0.748 |      0.218 |        0.092 |
| ('refit', 'B_weighted_share')                |          0.611 |         0.57  |          0.833 |      0.168 |        0.3   |
| ('refit', 'old_m3_events')                   |          1.076 |         0.48  |          0.669 |      0.224 |        0.07  |
| ('refit', 'zero')                            |          0     |       nan     |        nan     |      0.24  |        0     |

## All groups (median)

| method                  |   energy_ratio |   corr_profile |   awfe_skill |
|:------------------------|---------------:|---------------:|-------------:|
| A2_events_minus_weather |          1.021 |          0.835 |        0.105 |
| A_events                |          1.031 |          0.829 |        0.074 |
| B_mean_abs              |          0.81  |          0.703 |        0.243 |
| B_mean_levelA2          |          1.021 |          0.703 |        0.177 |
| B_mean_share            |          1.437 |          0.732 |        0.222 |
| B_shape_abs             |          1.053 |          0.562 |        0.125 |
| B_shape_share           |          1.531 |          0.601 |        0.075 |
| B_weighted_abs          |          0.842 |          0.7   |        0.237 |
| B_weighted_levelA2      |          1.021 |          0.7   |        0.174 |
| B_weighted_share        |          1.487 |          0.722 |        0.205 |
| old_m3_events           |          1.541 |          0.572 |       -0.114 |
| zero                    |          0     |        nan     |        0     |

## Nearest dataset chosen by load shape

| dataset       | nearest   |
|:--------------|:----------|
| pecan_austin  | refit     |
| pecan_newyork | ukdale    |
| plegma        | refit     |
| refit         | ukdale    |
