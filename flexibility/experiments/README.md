# Experiments

Conclusions of every test: `RESULTS.md`. Method changes: `docs/experiment_log.md`.

One folder or script per test of the plan (`docs/test_plan.pdf`). Status:

| Test | What | Data | Status |
|---|---|---|---|
| T1 | Baseline band (M1): coverage, width vs group size | REFIT, UK-DALE, Plegma, LCL | done on dev (v0.2, rerun v0.7); forecast weather + ACI open |
| T2 | Weather-dependent load (M2) vs AC / heater circuits | Plegma, REFIT, Pecan (local) | done; degree-day model with balance points and significance gate (v0.5-v0.6) |
| T3-EV | First look at EV charging | Pecan Austin, Ithaca (local) | done (v0.4); superseded by T9 |
| T3 | Appliance events (M3) vs appliances; Ponocko & Milanovic; zero baseline | REFIT, Plegma, Pecan (local), UK-DALE | done (v0.5-v0.8); design A (data only) in code, B (profile bank) pending decision |
| T4 | Sensitivity of the envelope to remaining settings | REFIT, Pecan Austin/Ithaca | done (v0.7) |
| T5 | Ablations (no weather, no calibration, no M2/M3) | same | not started |
| T6 | Response test in a pilot | pilot / LCL dToU | not started |
| T7 | Ponocko & Milanovic reproduced on CREST, compared with ours | CREST 1,000 homes | done (v0.7-v0.8) |
| T8 | Real vs estimated, Ponocko-style ANN on hourly P | REFIT, Pecan Austin/New York, UK-DALE | done (v0.8, rerun v0.9) |
| T9-T9d | EV charging (now M4): detection, flat-power gate, day-ahead check | Pecan (local) | done (v0.9) |
| T10 | Final figures | T9 groups | done (v0.9) |
| T11 | Diagnostics: under-estimation, REFIT peaks | T9 groups | done (v0.9), no method change |
| T12 | One envelope with EV inside (M5), participation for all (M6) | T9 groups | done (v0.10) |
| T13 | Explanatory figures for the method slides | Pecan Austin, REFIT | done (v0.10) |

`run_synthetic_demo.py` only checks that the code runs on synthetic data with known components. It validates nothing about real data.

Rules (see the plan, section 6): keep a development split and a final test split that stays closed until the method is frozen; log every variant in `docs/experiment_log.md`.
