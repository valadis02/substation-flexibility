
## plegma (development split, weather=yes, retrain every 7 d, seed 0)

Medians over groups. cov = share of hours inside the band (target 0.90 after calibration); width/IS/nMAE relative to mean load.

|   N |   groups |   hours |   mean_kw |   cov_raw |   cov_cal |   width_cal_rel |   is_cal_rel |   nmae_median |
|----:|---------:|--------:|----------:|----------:|----------:|----------------:|-------------:|--------------:|
|   1 |        4 |  3267.5 |     0.299 |     0.815 |     0.896 |           2.546 |        4.615 |         0.684 |
|   2 |        3 |  1966   |     0.966 |     0.77  |     0.895 |           2.011 |        3.363 |         0.548 |
|   5 |        1 |  1157   |     2.173 |     0.764 |     0.892 |           1.381 |        2.18  |         0.359 |

## ukdale (development split, weather=yes, retrain every 7 d, seed 0)

Medians over groups. cov = share of hours inside the band (target 0.90 after calibration); width/IS/nMAE relative to mean load.

|   N |   groups |   hours |   mean_kw |   cov_raw |   cov_cal |   width_cal_rel |   is_cal_rel |   nmae_median |
|----:|---------:|--------:|----------:|----------:|----------:|----------------:|-------------:|--------------:|
|   1 |        4 |  2007.5 |     0.382 |     0.733 |     0.9   |           1.353 |        2.321 |         0.347 |
|   2 |        3 |  1463   |     0.726 |     0.738 |     0.891 |           1.094 |        1.765 |         0.282 |

## refit (development split, weather=yes, retrain every 7 d, seed 0)

Medians over groups. cov = share of hours inside the band (target 0.90 after calibration); width/IS/nMAE relative to mean load.

|   N |   groups |   hours |   mean_kw |   cov_raw |   cov_cal |   width_cal_rel |   is_cal_rel |   nmae_median |
|----:|---------:|--------:|----------:|----------:|----------:|----------------:|-------------:|--------------:|
|   1 |        4 |  7498.5 |     0.407 |     0.791 |     0.894 |           1.349 |        2.646 |         0.354 |
|   2 |        4 |  7366.5 |     0.804 |     0.807 |     0.895 |           1.116 |        1.872 |         0.269 |
|   5 |        4 |  5420   |     2.661 |     0.759 |     0.895 |           0.98  |        1.491 |         0.248 |
|  10 |        4 |  4208   |     4.893 |     0.767 |     0.898 |           0.75  |        1.103 |         0.181 |
|  14 |        1 |  3640   |     6.688 |     0.763 |     0.902 |           0.651 |        0.965 |         0.157 |

## lcl (development split, Std-tariff homes only, weather=yes, retrain every 7 d, seed 0)

Group sums precomputed by scripts/prepare_lcl.py (an hour counts if >= 90% of members have data). Medians over groups.

|   N |   groups |   hours |   mean_kw |   cov_raw |   cov_cal |   width_cal_rel |   is_cal_rel |   nmae_median |
|----:|---------:|--------:|----------:|----------:|----------:|----------------:|-------------:|--------------:|
|  50 |        5 |    8127 |    20.301 |     0.789 |     0.899 |           0.411 |        0.533 |         0.095 |
| 150 |        5 |    7749 |    61.05  |     0.78  |     0.896 |           0.298 |        0.388 |         0.067 |
| 500 |        3 |    8276 |   210.874 |     0.769 |     0.898 |           0.23  |        0.307 |         0.051 |
