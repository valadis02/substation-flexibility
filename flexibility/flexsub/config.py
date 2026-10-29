from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class Config:
    """All tunable parameters of the method in one place (see docs/experiment_log.md for how changes are tracked)."""
    tz: str = "Europe/Athens"
    latitude: float = 37.98          # for day length (seasonal feature)
    seasonal_features: bool = True   # day of year + day length; fixed in the thermal counterfactual (v0.4)
    # M1 baseline
    quantiles: Tuple[float, float, float] = (0.05, 0.5, 0.95)
    calib_days: int = 14            # window of past days used for conformal calibration
    calib_quantile: float = 0.9     # target coverage of the calibrated band
    calib_min_samples: int = 72
    retrain_days: int = 1           # refit the quantile models every this many days (1 = daily, as in the method)
    gbm: dict = field(default_factory=lambda: dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                                   min_samples_leaf=20, l2_regularization=1.0, random_state=0))
    # M2 thermal
    # M2 (weather-dependent load) has no hand-set temperatures: balance points are estimated from each substation's data
    # M3 decomposition
    base_hours: int = 4                      # number of the home's own lowest-load hours used for the base level
    base_quantile: float = 0.1
    base_roll_days: int = 7
    # M4 EV charging (flexsub.ev; enveloped in M5): excess over the same-hour reference > ev_k kW, any run length; home gate ev_gate
    ev_k: float = 2.5
    ev_gate: float = 0.02
    ev_max_cv: float = 0.14          # flat charging power (T9b)
    ev_dwell_h: int = 10             # plug-in window from session start (behavioural assumption, T9c); used by the M5 EV envelope
    ev_history_days: int = 14        # sessions used as day-ahead scenarios
    # M5 flexibility envelope (weather + appliances; EV uses its sessions, see flexsub.flexibility)
    shift_window_h: int = 3         # energy can be moved from +-this many hours
    request_duration_h: int = 2     # length of the upward request block
    cap_quantile: float = 0.9       # power cap: observed extra draw of flexible load at that hour and its two neighbours (T14)
    # M6 participation (applies to every flexible category, EV included)
    # M6 scenarios. The headline result is the technical maximum (every home, every event). Scenarios scale it by
    # enrolment x response rate (share of enrolled homes that actually respond to an event). Scenarios are only for
    # illustration (how it would look for a DSO) and comparison with realised responses in the literature.
    participation: float = 1.0      # technical maximum
    participation_scenarios: Tuple[Tuple[float, float], ...] = ((0.2, 0.5), (0.2, 1.0), (0.5, 0.5), (0.5, 1.0))
    # enrolment 0.2 ~ LCL dToU (1,119 of ~5,500); response rates are placeholders until T6 estimates them
    holidays: Tuple[str, ...] = ()  # ISO dates, e.g. ("2026-08-15",)
