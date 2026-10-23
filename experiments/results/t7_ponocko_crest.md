# T7: Ponocko & Milanovic (2018) vs ours on CREST (1000 homes, 8 test days)

Median over test days (and sub-metered draws) of the 90th-percentile AWFE (p.u. of the average monthly load).

|                                             |   awfe_p90_min |   awfe_p90_hour |   energy_ratio |
|:--------------------------------------------|---------------:|----------------:|---------------:|
| ('CTIM1', 'ours_M3_A', 0.0)                 |        nan     |           0.156 |          1.505 |
| ('CTIM1', 'ponocko', 0.05)                  |          0.11  |           0.103 |          1.227 |
| ('CTIM1', 'ponocko', 0.1)                   |          0.088 |           0.079 |          1.165 |
| ('CTIM1', 'ponocko', 0.2)                   |          0.073 |           0.063 |          1.109 |
| ('CTIM1', 'ponocko', 1.0)                   |          0.052 |           0.041 |          1.001 |
| ('CTIM1', 'ponocko_0pct_indep', 0.0)        |          0.055 |           0.043 |          0.993 |
| ('CTIM1', 'zero', nan)                      |          0.294 |           0.292 |        nan     |
| ('controllable', 'ponocko', 0.05)           |          0.332 |           0.323 |          1.148 |
| ('controllable', 'ponocko', 0.1)            |          0.164 |           0.149 |          1.072 |
| ('controllable', 'ponocko', 0.2)            |          0.115 |           0.099 |          1.021 |
| ('controllable', 'ponocko', 1.0)            |          0.079 |           0.061 |          1.004 |
| ('controllable', 'ponocko_0pct_indep', 0.0) |          0.08  |           0.06  |          0.97  |
| ('controllable', 'zero', nan)               |          0.533 |           0.515 |        nan     |
