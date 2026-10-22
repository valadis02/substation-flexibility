# Experiment log

One entry per cycle: hypothesis -> test -> result -> decision -> new version. Log all variants, not only the final one.

| Version | Date | Hypothesis | Change (module/param) | Test and data split | Result | Decision |
|---|---|---|---|---|---|---|
| v0.1 | 2026-10-21 | Starting point (ported from `legacy/` exploration) | none | synthetic sanity checks only | tests pass; no real-data validation | start T1 |
| v0.2 | 2026-10-22 | Infrastructure for real data | loaders (Plegma, REFIT, UK-DALE), locked split `data/splits.json`, features drop all-NaN columns and allow no weather, rows usable if target + 7-day lag exist (HGB handles other NaN), `retrain_days` (experiments use 7 for speed; the method stays 1) | none (no results yet) | - | run T1 on development data |
