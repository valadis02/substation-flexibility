# Data

No raw data is committed (see `.gitignore`). Put local copies here, in `data/raw/`.

- **Public datasets with ground truth** (plan, section 4): Pecan Street Dataport (access request, non-commercial research), REFIT, UK-DALE, IDEAL, ECO.
- **Heron data is not used for tests** (no ground truth) and must not be committed (customer data).
- Weather: Open-Meteo archive endpoint (ERA5). Use the archive endpoint for history and keep hourly data in UTC.

Expected formats: long CSV `timestamp, house_id, consumption` in W (see `flexsub/data.py`), and the Open-Meteo CSV (3 header lines; time, temperature, humidity, cloud cover, shortwave radiation, is_day).
