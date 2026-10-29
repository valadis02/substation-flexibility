
## plegma, refit: dd_linear vs significance-gated (medians over units)

|                                    |   share_est |   share_true |   abs_share_err |   corr_daily |   daily_err_rel |   cooling_kept |   heating_kept |
|:-----------------------------------|------------:|-------------:|----------------:|-------------:|----------------:|---------------:|---------------:|
| ('plegma', 'ac', 'dd_gated')       |       0.254 |        0.144 |           0.141 |        0.624 |           1.168 |          1     |          0.917 |
| ('plegma', 'ac', 'dd_linear')      |       0.273 |        0.144 |           0.165 |        0.426 |           2.381 |          1     |          0.917 |
| ('plegma', 'control', 'dd_gated')  |       0.206 |        0     |           0.206 |      nan     |         nan     |          0.786 |          0     |
| ('plegma', 'control', 'dd_linear') |       0.342 |        0     |           0.342 |      nan     |         nan     |          0.786 |          0     |
| ('refit', 'control', 'dd_gated')   |       0.024 |        0     |           0.024 |      nan     |         nan     |          0     |          0.056 |
| ('refit', 'control', 'dd_linear')  |       0.205 |        0     |           0.205 |      nan     |         nan     |          0     |          0.056 |
| ('refit', 'heater', 'dd_gated')    |       0.017 |        0.041 |           0.026 |        0.056 |           1.098 |          0.5   |          0.031 |
| ('refit', 'heater', 'dd_linear')   |       0.109 |        0.041 |           0.079 |        0.186 |           2.841 |          0.5   |          0.031 |

## pecan_austin, pecan_newyork, pecan_california: dd_linear vs significance-gated (medians over units)

|                                           |   share_est |   share_true |   abs_share_err |   corr_daily |   daily_err_rel |   cooling_kept |   heating_kept |
|:------------------------------------------|------------:|-------------:|----------------:|-------------:|----------------:|---------------:|---------------:|
| ('pecan_austin', 'ac', 'dd_gated')        |       0.479 |        0.544 |           0.098 |        0.919 |           0.299 |          1     |          1     |
| ('pecan_austin', 'ac', 'dd_linear')       |       0.479 |        0.544 |           0.103 |        0.918 |           0.3   |          1     |          1     |
| ('pecan_austin', 'control', 'dd_gated')   |       0.367 |        0.098 |           0.268 |        0.862 |           2.771 |          1     |          1     |
| ('pecan_austin', 'control', 'dd_linear')  |       0.367 |        0.098 |           0.268 |        0.862 |           2.771 |          1     |          1     |
| ('pecan_california', 'ac', 'dd_gated')    |       0.235 |        0.243 |           0.049 |        0.722 |           0.716 |          1     |          0.091 |
| ('pecan_california', 'ac', 'dd_linear')   |       0.238 |        0.243 |           0.046 |        0.722 |           0.715 |          1     |          0.091 |
| ('pecan_newyork', 'ac', 'dd_gated')       |       0.201 |        0.215 |           0.096 |        0.517 |           0.738 |          1     |          0.583 |
| ('pecan_newyork', 'ac', 'dd_linear')      |       0.254 |        0.215 |           0.08  |        0.728 |           0.883 |          1     |          0.583 |
| ('pecan_newyork', 'control', 'dd_gated')  |       0.102 |        0.041 |           0.07  |       -0.07  |           1.985 |          0.833 |          0.5   |
| ('pecan_newyork', 'control', 'dd_linear') |       0.248 |        0.041 |           0.168 |        0.271 |           4.824 |          0.833 |          0.5   |
