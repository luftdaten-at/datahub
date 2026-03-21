"""
PM2.5 µg/m³ → RGB for map-consistent styling (matches home.html colorStepsPM25 / getColorForPM).
"""

import math
from typing import Optional, Tuple

# (lower_bound_inclusive, (R, G, B)) — same thresholds as templates/home.html colorStepsPM25
PM25_COLOR_STEPS = [
    (0, (80, 240, 230)),
    (10, (80, 204, 170)),
    (20, (240, 230, 65)),
    (25, (255, 80, 80)),
    (50, (150, 0, 50)),
    (75, (125, 33, 129)),
]


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
