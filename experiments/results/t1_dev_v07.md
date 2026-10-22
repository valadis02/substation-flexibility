
## lcl (development split, weather=yes, retrain every 7 d, seed 0)

Medians over groups. cov = share of hours inside the band (target 0.90 after calibration); width/IS/nMAE relative to mean load.

|   N |   groups |   hours |   mean_kw |   cov_raw |   cov_cal |   width_cal_rel |   is_cal_rel |   nmae_median |
|----:|---------:|--------:|----------:|----------:|----------:|----------------:|-------------:|--------------:|
|  50 |        5 |    8127 |    20.301 |     0.794 |     0.898 |           0.41  |        0.534 |         0.095 |
| 150 |        5 |    7749 |    61.05  |     0.787 |     0.896 |           0.299 |        0.392 |         0.067 |
| 500 |        3 |    8276 |   210.874 |     0.784 |     0.896 |           0.228 |        0.301 |         0.05  |

## refit (development split, weather=yes, retrain every 7 d, seed 0)

Medians over groups. cov = share of hours inside the band (target 0.90 after calibration); width/IS/nMAE relative to mean load.

|   N |   groups |   hours |   mean_kw |   cov_raw |   cov_cal |   width_cal_rel |   is_cal_rel |   nmae_median |
|----:|---------:|--------:|----------:|----------:|----------:|----------------:|-------------:|--------------:|
|   1 |        4 |  7498.5 |     0.407 |     0.804 |     0.893 |           1.345 |        2.63  |         0.356 |
|   2 |        4 |  7366.5 |     0.804 |     0.809 |     0.894 |           1.127 |        1.882 |         0.27  |
|   5 |        4 |  5420   |     2.661 |     0.751 |     0.895 |           1.005 |        1.502 |         0.248 |
|  10 |        4 |  4208   |     4.893 |     0.774 |     0.902 |           0.756 |        1.102 |         0.183 |
|  14 |        1 |  3640   |     6.688 |     0.767 |     0.902 |           0.659 |        0.95  |         0.158 |

## plegma (development split, weather=yes, retrain every 7 d, seed 0)

Medians over groups. cov = share of hours inside the band (target 0.90 after calibration); width/IS/nMAE relative to mean load.

|   N |   groups |   hours |   mean_kw |   cov_raw |   cov_cal |   width_cal_rel |   is_cal_rel |   nmae_median |
|----:|---------:|--------:|----------:|----------:|----------:|----------------:|-------------:|--------------:|
|   1 |        4 |  3267.5 |     0.299 |     0.812 |     0.897 |           2.514 |        4.582 |         0.688 |
|   2 |        3 |  1966   |     0.966 |     0.777 |     0.895 |           2.018 |        3.313 |         0.549 |
|   5 |        1 |  1157   |     2.173 |     0.75  |     0.884 |           1.393 |        2.228 |         0.364 |
