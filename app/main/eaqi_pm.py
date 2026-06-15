"""
European Air Quality Index (EAQI) particulate-matter color bands.

Revised 1-hour bands per EEA European Air Quality Index (2025), based on
ETC HE Report 2024/17 and https://airindex.eea.europa.eu/

Each step is (lower_bound_inclusive µg/m³, RGB). Upper bound is the next step's
lower bound (exclusive), except the last band which has no upper limit.
"""

from typing import List, Tuple

ColorStep = Tuple[int, Tuple[int, int, int]]

RGB_GOOD = (80, 240, 230)
RGB_FAIR = (80, 204, 170)
RGB_MODERATE = (240, 230, 65)
RGB_POOR = (255, 80, 80)
RGB_VERY_POOR = (150, 0, 50)
RGB_EXTREMELY_POOR = (125, 33, 129)

# PM2.5 (1h): Good 0–5, Fair 6–15, Moderate 16–50, Poor 51–90, Very poor 91–140, >140
PM25_COLOR_STEPS: List[ColorStep] = [
    (0, RGB_GOOD),
    (6, RGB_FAIR),
    (16, RGB_MODERATE),
    (51, RGB_POOR),
    (91, RGB_VERY_POOR),
    (141, RGB_EXTREMELY_POOR),
]

# PM10 (1h): Good 0–15, Fair 16–45, Moderate 46–120, Poor 121–195, Very poor 196–270, >270
PM10_COLOR_STEPS: List[ColorStep] = [
    (0, RGB_GOOD),
    (16, RGB_FAIR),
    (46, RGB_MODERATE),
    (121, RGB_POOR),
    (196, RGB_VERY_POOR),
    (271, RGB_EXTREMELY_POOR),
]

# PM1 is not a separate EAQI pollutant; use PM2.5 bands (same as map legend).
PM1_COLOR_STEPS: List[ColorStep] = PM25_COLOR_STEPS
