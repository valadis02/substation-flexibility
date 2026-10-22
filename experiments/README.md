# Experiments

Conclusions of every test: `RESULTS.md`. Method changes: `docs/experiment_log.md`.

One folder or script per test of the plan (`docs/test_plan.pdf`). Status:

| Test | What | Data | Status |
|---|---|---|---|
| T1 | Baseline coverage / interval score, group size | REFIT, UK-DALE, Plegma, LCL | done on dev (v0.2, rerun v0.7); forecast weather + ACI open |
| T2 | Thermal part vs AC / heater circuits | Plegma, REFIT, Pecan (local) | v1-v3 done; dd_linear adopted (v0.5) |
| T3-EV | EV homes, charging hours, EV profile | Pecan Austin, Ithaca (local) | first run done |
| T3 | Shiftable part vs appliances; comparison with Ponocko & Milanovic and zero baseline | REFIT, Plegma, Pecan (local), UK-DALE | v1, v2 done; design A (data only) in code, B (profile bank) pending decision |
| T4 | Sensitivity of the envelope to remaining settings | REFIT, Pecan Austin/Ithaca | done (v0.7) |
| T5 | Ablations (no weather, no calibration, no M2/M3) | same | not started |
| T6 | Response test in a pilot | pilot | not started |

`run_synthetic_demo.py` only checks that the code runs on synthetic data with known components. It validates nothing about real data.

Rules (see the plan, section 6): keep a development split and a final test split that stays closed until the method is frozen; log every variant in `docs/experiment_log.md`.
