# Experiments

Conclusions of every test: `RESULTS.md`. Method changes: `docs/experiment_log.md`.

One folder or script per test of the plan (`docs/test_plan.pdf`). Status:

| Test | What | Data | Status |
|---|---|---|---|
| T1 | Baseline coverage / interval score, forecast weather, group size | REFIT, UK-DALE, Plegma, LCL | done on dev (observed weather); forecast weather + ACI open |
| T2 | Thermal part vs AC / heater circuits | Plegma, REFIT, (Pecan Street) | v1 run (weak, confounded); v2 next |
| T3 | Shiftable part vs appliances; comparison with Ponocko & Milanovic (0% / 5% / 100%) and oracle | Pecan Street, REFIT, UK-DALE, IDEAL | not started |
| T4 | Sensitivity (threshold 0.4 kW, meal hours, window, cap) | same | not started |
| T5 | Ablations (no weather, no calibration, no M2/M3) | same | not started |
| T6 | Response test in a pilot | pilot | not started |

`run_synthetic_demo.py` only checks that the code runs on synthetic data with known components. It validates nothing about real data.

Rules (see the plan, section 6): keep a development split and a final test split that stays closed until the method is frozen; log every variant in `docs/experiment_log.md`.
