# T7: Ponocko & Milanovic (2018) vs ours on CREST (1000 homes, 4 test days)

Median over test days (and sub-metered draws) of the 90th-percentile AWFE (p.u. of the average monthly load).

|                                   |   awfe_p90_min |   awfe_p90_hour |   energy_ratio |
|:----------------------------------|---------------:|----------------:|---------------:|
| ('CTIM1', 'ours_M3_A', 0.0)       |        nan     |           0.171 |          1.508 |
| ('CTIM1', 'ponocko', 0.05)        |          0.114 |           0.105 |          1.262 |
| ('CTIM1', 'ponocko', 0.1)         |          0.091 |           0.083 |          1.162 |
| ('CTIM1', 'zero', nan)            |          0.33  |           0.308 |        nan     |
| ('controllable', 'ponocko', 0.05) |          0.262 |           0.244 |          1.107 |
| ('controllable', 'ponocko', 0.1)  |          0.178 |           0.157 |          1.046 |
| ('controllable', 'zero', nan)     |          0.58  |           0.562 |        nan     |
