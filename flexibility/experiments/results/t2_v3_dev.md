# T2 v3 (development; leave-one-4-week-block-out)

## Groups: share ratio (estimated / true thermal)

|                                      |   dd_hybrid |   dd_linear |   gbm_nolag |   gbm_v2 |
|:-------------------------------------|------------:|------------:|------------:|---------:|
| ('pecan_austin', 'group(20 homes)')  |       0.87  |       0.886 |       0.823 |    0.701 |
| ('pecan_newyork', 'group(20 homes)') |       0.822 |       0.98  |       0.676 |    0.421 |
| ('plegma', 'group(>=6 homes)')       |       1.299 |       1.317 |       0.842 |    0.6   |
| ('refit', 'group(14 homes)')         |      10.791 |      13.32  |       3.723 |    1.821 |

## Medians over units, all seasons

|                                           |   share_ratio |   corr_daily |   corr_hourly |   daily_err_rel |
|:------------------------------------------|--------------:|-------------:|--------------:|----------------:|
| ('pecan_austin', 'ac', 'dd_hybrid')       |         0.847 |        0.922 |         0.829 |           0.298 |
| ('pecan_austin', 'ac', 'dd_linear')       |         0.855 |        0.918 |         0.825 |           0.3   |
| ('pecan_austin', 'ac', 'gbm_nolag')       |         0.797 |        0.915 |         0.841 |           0.307 |
| ('pecan_austin', 'ac', 'gbm_v2')          |         0.674 |        0.927 |         0.845 |           0.36  |
| ('pecan_austin', 'control', 'dd_hybrid')  |         3.515 |        0.861 |         0.765 |           2.562 |
| ('pecan_austin', 'control', 'dd_linear')  |         3.729 |        0.862 |         0.77  |           2.771 |
| ('pecan_austin', 'control', 'gbm_nolag')  |         4.061 |        0.853 |         0.791 |           3.18  |
| ('pecan_austin', 'control', 'gbm_v2')     |         3.15  |        0.845 |         0.776 |           2.27  |
| ('pecan_california', 'ac', 'dd_hybrid')   |         0.841 |        0.762 |         0.464 |           0.702 |
| ('pecan_california', 'ac', 'dd_linear')   |         0.929 |        0.722 |         0.467 |           0.715 |
| ('pecan_california', 'ac', 'gbm_nolag')   |         0.493 |        0.64  |         0.419 |           0.78  |
| ('pecan_california', 'ac', 'gbm_v2')      |         0.369 |        0.664 |         0.438 |           0.797 |
| ('pecan_newyork', 'ac', 'dd_hybrid')      |         1.056 |        0.755 |         0.458 |           0.699 |
| ('pecan_newyork', 'ac', 'dd_linear')      |         1.163 |        0.728 |         0.454 |           0.883 |
| ('pecan_newyork', 'ac', 'gbm_nolag')      |         0.644 |        0.62  |         0.535 |           0.688 |
| ('pecan_newyork', 'ac', 'gbm_v2')         |         0.387 |        0.644 |         0.492 |           0.723 |
| ('pecan_newyork', 'control', 'dd_hybrid') |         3.915 |        0.332 |         0.134 |           3.695 |
| ('pecan_newyork', 'control', 'dd_linear') |         4.86  |        0.271 |         0.123 |           4.824 |
| ('pecan_newyork', 'control', 'gbm_nolag') |         1.501 |       -0.084 |        -0.044 |           1.854 |
| ('pecan_newyork', 'control', 'gbm_v2')    |         1.029 |       -0.082 |        -0.059 |           1.359 |
| ('plegma', 'ac', 'dd_hybrid')             |         1.956 |        0.433 |         0.234 |           2.243 |
| ('plegma', 'ac', 'dd_linear')             |         2.32  |        0.426 |         0.196 |           2.381 |
| ('plegma', 'ac', 'gbm_nolag')             |         0.665 |        0.559 |         0.204 |           1.191 |
| ('plegma', 'ac', 'gbm_v2')                |         0.545 |        0.347 |         0.146 |           1.206 |
| ('plegma', 'control', 'dd_hybrid')        |       nan     |      nan     |       nan     |         nan     |
| ('plegma', 'control', 'dd_linear')        |       nan     |      nan     |       nan     |         nan     |
| ('plegma', 'control', 'gbm_nolag')        |       nan     |      nan     |       nan     |         nan     |
| ('plegma', 'control', 'gbm_v2')           |       nan     |      nan     |       nan     |         nan     |
| ('refit', 'control', 'dd_hybrid')         |       nan     |      nan     |       nan     |         nan     |
| ('refit', 'control', 'dd_linear')         |       nan     |      nan     |       nan     |         nan     |
| ('refit', 'control', 'gbm_nolag')         |       nan     |      nan     |       nan     |         nan     |
| ('refit', 'control', 'gbm_v2')            |       nan     |      nan     |       nan     |         nan     |
| ('refit', 'heater', 'dd_hybrid')          |         2.34  |        0.214 |         0.039 |           2.779 |
| ('refit', 'heater', 'dd_linear')          |         2.551 |        0.186 |         0.034 |           2.841 |
| ('refit', 'heater', 'gbm_nolag')          |         1.335 |        0.136 |        -0.009 |           2.13  |
| ('refit', 'heater', 'gbm_v2')             |         0.496 |        0.162 |         0.013 |           1.343 |
