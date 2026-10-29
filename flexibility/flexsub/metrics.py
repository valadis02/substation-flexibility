import numpy as np
import pandas as pd


def coverage(actual, lo, hi):
    return float(((actual >= lo) & (actual <= hi)).mean())


def interval_score(actual, lo, hi, alpha=0.1):
    """Gneiting & Raftery interval score (lower is better)."""
    w = hi - lo
    pen = (2 / alpha) * ((lo - actual).clip(lower=0) + (actual - hi).clip(lower=0))
    return float((w + pen).mean())


def mae(a, b):
    return float((a - b).abs().mean())


def awfe_p90(share_est, share_true):
    """Absolute weighting-factor error at the 90th percentile (Ponocko & Milanovic 2018): |share_est - share_true| in p.u."""
    return float(np.quantile((share_est - share_true).abs().dropna(), 0.9))
