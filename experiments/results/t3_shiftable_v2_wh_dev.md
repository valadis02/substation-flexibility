# T3 v2 (development; leave-one-dataset-out bank; water heaters counted as shiftable)

## Largest group per dataset

|                                              |   energy_ratio |   corr_hourly |   corr_profile |   awfe_p90 |   awfe_skill |
|:---------------------------------------------|---------------:|--------------:|---------------:|-----------:|-------------:|
| ('pecan_austin', 'A2_events_minus_weather')  |          0.826 |         0.068 |          0.582 |      0.09  |        0.268 |
| ('pecan_austin', 'A_events')                 |          0.879 |         0.057 |          0.584 |      0.094 |        0.227 |
| ('pecan_austin', 'B_mean_abs')               |          1.558 |         0.048 |          0.573 |      0.1   |        0.182 |
| ('pecan_austin', 'B_mean_levelA2')           |          0.826 |         0.048 |          0.573 |      0.075 |        0.389 |
| ('pecan_austin', 'B_mean_share')             |          3.623 |         0.032 |          0.564 |      0.164 |       -0.345 |
| ('pecan_austin', 'B_shape_abs')              |          1.217 |         0.037 |          0.455 |      0.095 |        0.227 |
| ('pecan_austin', 'B_shape_share')            |          3.033 |         0.03  |          0.521 |      0.154 |       -0.257 |
| ('pecan_austin', 'B_weighted_abs')           |          1.575 |         0.047 |          0.571 |      0.101 |        0.173 |
| ('pecan_austin', 'B_weighted_levelA2')       |          0.826 |         0.047 |          0.571 |      0.075 |        0.386 |
| ('pecan_austin', 'B_weighted_share')         |          3.618 |         0.032 |          0.563 |      0.164 |       -0.344 |
| ('pecan_austin', 'zero')                     |          0     |       nan     |        nan     |      0.122 |        0     |
| ('pecan_newyork', 'A2_events_minus_weather') |          0.323 |         0.597 |          0.914 |      0.208 |        0.21  |
| ('pecan_newyork', 'A_events')                |          0.316 |         0.573 |          0.924 |      0.211 |        0.2   |
| ('pecan_newyork', 'B_mean_abs')              |          0.364 |         0.421 |          0.826 |      0.203 |        0.228 |
| ('pecan_newyork', 'B_mean_levelA2')          |          0.323 |         0.421 |          0.826 |      0.21  |        0.204 |
| ('pecan_newyork', 'B_mean_share')            |          0.757 |         0.503 |          0.796 |      0.142 |        0.46  |
| ('pecan_newyork', 'B_shape_abs')             |          0.307 |         0.305 |          0.611 |      0.214 |        0.186 |
| ('pecan_newyork', 'B_shape_share')           |          0.785 |         0.397 |          0.65  |      0.18  |        0.316 |
| ('pecan_newyork', 'B_weighted_abs')          |          0.362 |         0.421 |          0.828 |      0.204 |        0.227 |
| ('pecan_newyork', 'B_weighted_levelA2')      |          0.323 |         0.421 |          0.828 |      0.209 |        0.208 |
| ('pecan_newyork', 'B_weighted_share')        |          0.747 |         0.501 |          0.794 |      0.144 |        0.452 |
| ('pecan_newyork', 'zero')                    |          0     |       nan     |        nan     |      0.263 |        0     |
| ('plegma', 'A2_events_minus_weather')        |          1.216 |         0.773 |          0.909 |      0.331 |        0.172 |
| ('plegma', 'A_events')                       |          1.229 |         0.755 |          0.91  |      0.331 |        0.17  |
| ('plegma', 'B_mean_abs')                     |          1.873 |         0.09  |          0.352 |      0.818 |       -1.048 |
| ('plegma', 'B_mean_levelA2')                 |          1.216 |         0.09  |          0.352 |      0.565 |       -0.415 |
| ('plegma', 'B_mean_share')                   |          0.711 |         0.517 |          0.622 |      0.28  |        0.3   |
| ('plegma', 'B_shape_abs')                    |          1.491 |         0.138 |          0.497 |      0.679 |       -0.7   |
| ('plegma', 'B_shape_share')                  |          0.811 |         0.537 |          0.678 |      0.268 |        0.33  |
| ('plegma', 'B_weighted_abs')                 |          2.015 |         0.105 |          0.391 |      0.854 |       -1.139 |
| ('plegma', 'B_weighted_levelA2')             |          1.216 |         0.105 |          0.391 |      0.552 |       -0.382 |
| ('plegma', 'B_weighted_share')               |          0.713 |         0.538 |          0.67  |      0.281 |        0.296 |
| ('plegma', 'transfer_1_submetered_home')     |        nan     |       nan     |        nan     |      0.362 |        0.093 |
| ('plegma', 'zero')                           |          0     |       nan     |        nan     |      0.399 |        0     |
| ('refit', 'A2_events_minus_weather')         |          1.011 |         0.554 |          0.87  |      0.189 |        0.212 |
| ('refit', 'A_events')                        |          1.014 |         0.554 |          0.87  |      0.189 |        0.214 |
| ('refit', 'B_mean_abs')                      |          1.575 |         0.382 |          0.808 |      0.242 |       -0.008 |
| ('refit', 'B_mean_levelA2')                  |          1.011 |         0.382 |          0.808 |      0.177 |        0.264 |
| ('refit', 'B_mean_share')                    |          1.168 |         0.588 |          0.835 |      0.149 |        0.382 |
| ('refit', 'B_shape_abs')                     |          0.947 |         0.27  |          0.578 |      0.222 |        0.075 |
| ('refit', 'B_shape_share')                   |          1.106 |         0.512 |          0.743 |      0.195 |        0.189 |
| ('refit', 'B_weighted_abs')                  |          1.584 |         0.383 |          0.809 |      0.245 |       -0.019 |
| ('refit', 'B_weighted_levelA2')              |          1.011 |         0.383 |          0.809 |      0.178 |        0.262 |
| ('refit', 'B_weighted_share')                |          1.164 |         0.591 |          0.84  |      0.149 |        0.378 |
| ('refit', 'zero')                            |          0     |       nan     |        nan     |      0.24  |        0     |

## All groups (median)

| method                     |   energy_ratio |   corr_profile |   awfe_skill |
|:---------------------------|---------------:|---------------:|-------------:|
| A2_events_minus_weather    |          0.721 |          0.856 |        0.148 |
| A_events                   |          0.777 |          0.857 |        0.139 |
| B_mean_abs                 |          1.3   |          0.757 |        0.126 |
| B_mean_levelA2             |          0.721 |          0.757 |        0.238 |
| B_mean_share               |          1.33  |          0.761 |        0.319 |
| B_shape_abs                |          1.037 |          0.573 |        0.111 |
| B_shape_share              |          1.327 |          0.642 |        0.111 |
| B_weighted_abs             |          1.313 |          0.757 |        0.126 |
| B_weighted_levelA2         |          0.721 |          0.757 |        0.238 |
| B_weighted_share           |          1.322 |          0.759 |        0.315 |
| transfer_1_submetered_home |        nan     |        nan     |        0.078 |
| zero                       |          0     |        nan     |        0     |

## Nearest dataset chosen by load shape

| dataset       | nearest   |
|:--------------|:----------|
| pecan_austin  | refit     |
| pecan_newyork | ukdale    |
| plegma        | refit     |
| refit         | ukdale    |
