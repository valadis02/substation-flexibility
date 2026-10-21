# Legacy exploration scripts

Scripts from the first exploration on 10 Heron houses (Aug-Oct 2026). Kept for provenance only: they have hard-coded dates and assume the Heron CSV layout and an external `flexibility.py` (lab backend code, not included). Their logic was ported into `flexsub/`:

| Script | Ported to |
|---|---|
| `fc2.py`, `fc2b.py` | `flexsub/baseline.py`, `flexsub/features.py` |
| `fc3.py`, `opt3.py`, `opt3cal.py` | `flexsub/baseline.py`, `flexsub/thermal.py` |
| `decomp.py` | `flexsub/decompose.py` |
| `exp.py` | not ported (aggregation experiment; no longer tested, see plan) |
