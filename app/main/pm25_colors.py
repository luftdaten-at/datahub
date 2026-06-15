"""
PM2.5 µg/m³ → RGB for map-consistent styling (matches EAQI bands in eaqi_pm.py).
"""

import math
from typing import Optional, Tuple

from main.eaqi_pm import PM25_COLOR_STEPS


def pm25_to_rgb(value: Optional[float]) -> Tuple[int, int, int]:
    """Return RGB for a PM2.5 value; missing/invalid → grey like the map."""
    if value is None:
        return (128, 128, 128)
    try:
        v = float(value)
    except (TypeError, ValueError):
        return (128, 128, 128)
    if math.isnan(v):
        return (128, 128, 128)
    if v < 0:
        v = 0.0
    for i in range(len(PM25_COLOR_STEPS) - 1):
        low, rgb = PM25_COLOR_STEPS[i]
        next_low, _ = PM25_COLOR_STEPS[i + 1]
        if low <= v < next_low:
            return rgb
    return PM25_COLOR_STEPS[-1][1]
