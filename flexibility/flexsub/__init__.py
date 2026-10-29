"""flexsub: substation-level flexibility estimation from aggregate smart-meter data (no sub-metering, no DR signal).

Status: research code, v0.10. Checked against sub-metered ground truth on development data only (experiments/RESULTS.md);
the locked final test has not been run.
"""
from .config import Config
__all__ = ["Config"]
__version__ = "0.10"
