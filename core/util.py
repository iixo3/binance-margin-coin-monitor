from __future__ import annotations

from statistics import median


def robust_z(value: float, data: list) -> float:
    """Median/MAD-based z-score. Robust to fat tails / past spikes.

    Returns 0.0 if too little history or zero spread (avoids cold-start
    false positives).
    """
    if len(data) < 5:
        return 0.0
    med = median(data)
    mad = median([abs(x - med) for x in data])
    if mad == 0:
        return 0.0
    return 0.6745 * (value - med) / mad
