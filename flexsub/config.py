from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class Config:
    """All tunable parameters of the method in one place (see docs/experiment_log.md for how changes are tracked)."""
    tz: str = "Europe/Athens"
    # M1 baseline
    quantiles: Tuple[float, float, float] = (0.05, 0.5, 0.95)
    calib_days: int = 14            # window of past days used for conformal calibration
    calib_quantile: float = 0.9     # target coverage of the calibrated band
    calib_min_samples: int = 72
    retrain_days: int = 1           # refit the quantile models every this many days (1 = daily, as in the method)
    gbm: dict = field(default_factory=lambda: dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                                   min_samples_leaf=20, l2_regularization=1.0, random_state=0))
    # M2 thermal
    neutral_temp: float = 20.0      # counterfactual temperature (deg C)
    cdd_base: float = 24.0
    hdd_base: float = 16.0
    # M3 decomposition
    night_hours: Tuple[int, int] = (2, 6)
    base_quantile: float = 0.1
    base_roll_days: int = 7
    event_threshold_kw: float = 0.4          # excess over expected load that counts as a discrete event
    meal_hours: Tuple[Tuple[int, int], ...] = ((12, 15), (18, 22))
    meal_weekdays_only: bool = True
    # M4 flexibility
    shift_window_h: int = 3         # energy can be moved from +-this many hours
    request_duration_h: int = 2     # length of the upward request block
    cap_quantile: float = 0.9       # power cap: observed extra draw of shiftable load at that hour
    # M5 participation
    participation: float = 1.0      # 1.0 = technical maximum (all homes respond)
    participation_scenarios: Tuple[float, ...] = (0.2, 0.3, 0.5)   # 0.2 ~ LCL dToU enrolment (1,119 of ~5,500)
    holidays: Tuple[str, ...] = ()  # ISO dates, e.g. ("2026-08-15",)
