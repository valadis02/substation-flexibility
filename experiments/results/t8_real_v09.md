# T8: method v0.9 (rerun, P950 excluded) on real data, development period

AWFE in p.u. of the 30-day mean load (UK-DALE: median over single homes).

|                                |   hours |   awfe_p90_all |   zero_p90_all |   awfe_p90_daily_median |   energy_ratio |    corr |
|:-------------------------------|--------:|---------------:|---------------:|------------------------:|---------------:|--------:|
| ('pecan_austin', 'flexible')   |    5064 |          0.302 |          0.999 |                   0.261 |          0.73  |   0.457 |
| ('pecan_austin', 'shiftable')  |    5058 |          0.095 |          0.129 |                   0.08  |          0.724 | nan     |
| ('pecan_austin', 'weather')    |    5058 |          0.285 |          0.96  |                   0.237 |          0.73  | nan     |
| ('pecan_newyork', 'flexible')  |    3364 |          0.268 |          0.47  |                   0.23  |          0.67  |   0.707 |
| ('pecan_newyork', 'shiftable') |    3359 |          0.177 |          0.274 |                   0.136 |          0.562 | nan     |
| ('pecan_newyork', 'weather')   |    3359 |          0.181 |          0.287 |                   0.148 |          0.756 | nan     |
| ('refit', 'flexible')          |    5241 |          0.242 |          0.315 |                   0.214 |          0.916 |   0.53  |
| ('refit', 'shiftable')         |    5241 |          0.242 |          0.305 |                   0.211 |          0.978 |   0.535 |
| ('refit', 'weather')           |    5241 |          0.019 |          0.019 |                   0.003 |          0     | nan     |
| ('ukdale', 'flexible')         |   33901 |          0.192 |          0.081 |                   0.1   |          0.909 |   0.718 |
| ('ukdale', 'shiftable')        |   33899 |          0.158 |          0.081 |                   0.064 |          0.909 |   0.578 |
| ('ukdale', 'weather')          |   33899 |          0     |          0     |                   0     |        nan     | nan     |

## Ponocko-style ANN adapted to hourly P only (numbers only)

|                                          |   homes |   ponocko_awfe_p90 |   ours_awfe_p90_same_days |
|:-----------------------------------------|--------:|-------------------:|--------------------------:|
| ('pecan_austin', 'flexible', '1 home')   |       1 |              0.398 |                     0.31  |
| ('pecan_austin', 'flexible', '20%')      |       3 |              0.238 |                     0.31  |
| ('pecan_austin', 'flexible', '50%')      |       8 |              0.178 |                     0.31  |
| ('pecan_austin', 'shiftable', '1 home')  |       1 |              0.16  |                     0.094 |
| ('pecan_austin', 'shiftable', '20%')     |       3 |              0.136 |                     0.094 |
| ('pecan_austin', 'shiftable', '50%')     |       8 |              0.096 |                     0.094 |
| ('pecan_austin', 'weather', '1 home')    |       1 |              0.405 |                     0.295 |
| ('pecan_austin', 'weather', '20%')       |       3 |              0.248 |                     0.295 |
| ('pecan_austin', 'weather', '50%')       |       8 |              0.17  |                     0.295 |
| ('pecan_newyork', 'flexible', '1 home')  |       1 |              0.628 |                     0.248 |
| ('pecan_newyork', 'flexible', '20%')     |       3 |              0.558 |                     0.248 |
| ('pecan_newyork', 'flexible', '50%')     |       7 |              0.234 |                     0.248 |
| ('pecan_newyork', 'shiftable', '1 home') |       1 |              0.812 |                     0.154 |
| ('pecan_newyork', 'shiftable', '20%')    |       3 |              0.436 |                     0.154 |
| ('pecan_newyork', 'shiftable', '50%')    |       7 |              0.206 |                     0.154 |
| ('pecan_newyork', 'weather', '1 home')   |       1 |              0.302 |                     0.187 |
| ('pecan_newyork', 'weather', '20%')      |       3 |              0.299 |                     0.187 |
| ('pecan_newyork', 'weather', '50%')      |       7 |              0.18  |                     0.187 |
| ('refit', 'flexible', '1 home')          |       1 |              0.442 |                     0.226 |
| ('refit', 'flexible', '20%')             |       3 |              0.293 |                     0.226 |
| ('refit', 'flexible', '50%')             |       6 |              0.206 |                     0.226 |
| ('refit', 'shiftable', '1 home')         |       1 |              0.42  |                     0.226 |
| ('refit', 'shiftable', '20%')            |       3 |              0.291 |                     0.226 |
| ('refit', 'shiftable', '50%')            |       6 |              0.205 |                     0.226 |
| ('refit', 'weather', '1 home')           |       1 |              0.098 |                     0.025 |
| ('refit', 'weather', '20%')              |       3 |              0.042 |                     0.025 |
| ('refit', 'weather', '50%')              |       6 |              0.039 |                     0.025 |
