# Working agreement

- `main` always passes `pytest`. Work in short-lived feature branches (`feat/...`, `exp/...`) and merge back quickly; avoid long-lived forks of the method.
- Per-deployment differences (location for weather, timezone, calendar, thresholds) go in `Config`, not in code forks.
- Every change to the method (module or parameter) gets a line in `docs/experiment_log.md` with the data split used.
- Never commit raw or customer data. Heron data is excluded from tests.
- The final test split stays closed until the method is frozen (plan, section 6).
