from __future__ import annotations

import numpy as np


# --------------------------------------------------
# BASE CONVICTION
# --------------------------------------------------

def compute_conviction(prob_3m: float | None = None, prob_6m: float | None = None) -> float:
    vals = []

    if prob_3m is not None:
        vals.append(abs(float(prob_3m) - 0.5) * 2.0)

    if prob_6m is not None:
        vals.append(abs(float(prob_6m) - 0.5) * 2.0)

    if not vals:
        return 0.0

    conviction = max(vals)
    return float(max(0.0, min(1.0, conviction)))


# --------------------------------------------------
# SCALING METHODS
# --------------------------------------------------

def scale_conviction(
    conviction: float,
    method: str = "linear",
    exponent: float = 1.5,
    logistic_k: float = 10.0,
    logistic_threshold: float = 0.3,
) -> float:

    conviction = float(max(0.0, min(1.0, conviction)))

    if method == "linear":
        return conviction

    elif method == "power":
        return conviction ** exponent

    elif method == "logistic":
        # sigmoid centered at threshold
        x = conviction - logistic_threshold
        return float(1.0 / (1.0 + np.exp(-logistic_k * x)))

    else:
        raise ValueError(f"Unknown conviction scaling method: {method}")