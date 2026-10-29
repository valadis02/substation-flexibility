# T14 - stability of the M5 up cap (development data, rolling 35-day windows, step 7 days)

up_err = mean |est - true| / mean load; ratio = est / true over the day; peak = max est / max true; rough = mean |hour-to-hour change| / mean up; up_true = true up / mean load. q80 rules change the truth too.

| dataset   | rule     |   windows |   up_err |   ratio_median |   ratio_p10 |   ratio_p90 |   peak_median |   rough |   up_true |
|:----------|:---------|----------:|---------:|---------------:|------------:|------------:|--------------:|--------:|----------:|
| plegma    | bag      |        10 |    0.133 |          1.095 |       0.239 |       1.304 |         1.158 |   0.623 |     0.335 |
| plegma    | longwin  |        10 |    0.1   |          0.915 |       0.29  |       1.185 |         1.078 |   0.722 |     0.234 |
| plegma    | per_hour |        10 |    0.13  |          1.172 |       0.202 |       1.492 |         1.134 |   0.748 |     0.281 |
| plegma    | pool3    |        10 |    0.118 |          1.099 |       0.221 |       1.461 |         1.085 |   0.384 |     0.311 |
| plegma    | pool_q80 |        10 |    0.032 |          2.923 |       0.01  |      36.973 |         2.011 |   0.675 |     0.07  |
| plegma    | q80      |        10 |    0.046 |          1.639 |       0.487 |       6.295 |         1.168 |   0.869 |     0.08  |
| refit     | bag      |        29 |    0.052 |          1.157 |       1.047 |       1.281 |         1.272 |   0.287 |     0.142 |
| refit     | longwin  |        29 |    0.055 |          1.191 |       1.083 |       1.244 |         1.295 |   0.288 |     0.143 |
| refit     | per_hour |        29 |    0.058 |          1.156 |       1.054 |       1.287 |         1.314 |   0.339 |     0.142 |
| refit     | pool3    |        29 |    0.054 |          1.163 |       1.034 |       1.305 |         1.257 |   0.185 |     0.153 |
| refit     | pool_q80 |        29 |    0.031 |          1.094 |       0.802 |       1.206 |         1.296 |   0.211 |     0.084 |
| refit     | q80      |        29 |    0.035 |          1.046 |       0.853 |       1.188 |         1.151 |   0.379 |     0.077 |
