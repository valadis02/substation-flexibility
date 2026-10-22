# Data

No raw data is committed (see `.gitignore`). Put local copies in `data/raw/` (or anywhere and pass the path).

## Datasets for the tests (plan, section 4)

| Dataset | Ground truth | Loader | Notes |
|---|---|---|---|
| Plegma (Greece, 13 homes, 10 s, 07/2022-09/2023) | AC (11 homes), boiler (12), washing machine, dishwasher, fridge | `load_plegma` | No EV. 150-440 days per home. Weather = homes' external sensors (no cloud/radiation). CC BY 4.0 |
| REFIT (UK, 20 homes, ~8 s, 2013-2015) | washing machine, tumble dryer, dishwasher, electric heaters (houses 1, 9, 16) | `load_refit` | No AC/EV. Houses 11, 21: mains affected by PV. Appliance names from the README (see `flexsub/appliances.py`, read its notes on swaps). CC BY 4.0 |
| UK-DALE (UK, 5 homes, 6 s) | washing machine, dishwasher, washer dryer, electric heater (house 3) | `load_ukdale` | No AC/EV. Mains of building 1 are apparent power. CC BY 4.0 |
| CU-BEMS (Thailand, office building) | per-floor AC, lighting, plugs | not yet | Commercial, not residential |
| Pecan Street Dataport | HVAC, EV, water heater, dryer, dishwasher, ... | `load_pecan_street` (stub) | Access request sent; approval pending |

Heron data is not used for tests (no ground truth) and must not be committed (customer data).

## Processed data (committed)

`data/processed/<dataset>/` holds hourly kW (UTC, gzipped CSV): `mains.csv.gz`, `appliances_<home>.csv.gz`, and `weather.csv.gz` where the dataset has weather. Build it with `python scripts/prepare_data.py <plegma|refit|ukdale> <raw path>` and read it with `flexsub.data.load_processed`. Raw files stay out of git (too large).

Cite: Plegma (Athanasoulias et al., Scientific Data 2024), REFIT (Murray et al., 2015/2017), UK-DALE (Kelly & Knottenbelt, Scientific Data 2015).

## Weather for REFIT and UK-DALE (Open-Meteo, ERA5)

Open each URL in a browser (it downloads a CSV), then run `python scripts/add_weather.py <dataset> <csv>`.
`timezone=GMT` matters: the loader assumes UTC.

- REFIT (Loughborough, 52.77 N, 1.20 W): https://archive-api.open-meteo.com/v1/archive?latitude=52.77&longitude=-1.20&start_date=2013-09-01&end_date=2015-07-31&hourly=temperature_2m,relative_humidity_2m,cloud_cover,shortwave_radiation,is_day&timezone=GMT&format=csv
- UK-DALE (London, 51.51 N, 0.13 W; houses are in or near London, exact locations not published): https://archive-api.open-meteo.com/v1/archive?latitude=51.51&longitude=-0.13&start_date=2012-11-01&end_date=2017-05-01&hourly=temperature_2m,relative_humidity_2m,cloud_cover,shortwave_radiation,is_day&timezone=GMT&format=csv

Plegma ships its own (homes' external sensors); an Open-Meteo series for Athens can replace it later for a like-for-like comparison.

## Formats

- Loaders return `dict(W=hourly kW mains (UTC, one column per home), appliances={home: hourly kW per appliance}, ...)`.
- `load_long_csv`: long CSV `timestamp, house_id, consumption` in W.
- Weather: Open-Meteo archive endpoint (ERA5) for history, hourly in UTC; `load_openmeteo_csv` reads its CSV (3 header lines; time, temperature, humidity, cloud cover, shortwave radiation, is_day).
- Hours with too few samples are dropped, so the hourly index can have holes: reindex before using lags.
