"""The Physics Gate: a pure function that intercepts every model prediction
before it becomes a reported detection. An oil-spill classifier that ignores
sea-state physics will confidently label glassy water as oil and miss real
slicks in a rough sea — this module is what keeps the system honest.
"""
from __future__ import annotations

from app.config import thresholds as t
from app.models import EnvironmentalConditions, ReliabilityBlock, ReliabilityVerdict


def evaluate_physics_gate(env: EnvironmentalConditions, slick_area_m2: float) -> ReliabilityBlock:
    wind = env.wind_speed_ms
    possible_rain = env.precipitation_mm_hr > t.RAIN_ARTEFACT_MM_HR

    if wind < t.WIND_UNRELIABLE_LOW:
        block = ReliabilityBlock(
            verdict=ReliabilityVerdict.UNRELIABLE_LOW_WIND,
            reason=(
                f"Wind speed {wind:.1f} m/s is below {t.WIND_UNRELIABLE_LOW} m/s. "
                "Sea surface is glassy — natural low-wind sheens are visually and "
                "radiometrically indistinguishable from oil at this wind speed. "
                "Detection suppressed; confidence forced to 0."
            ),
            confidence_multiplier=0.0,
            suppressed=True,
            possible_rain_artefact=possible_rain,
        )
    elif wind > t.WIND_DEGRADED_HIGH_MAX:
        block = ReliabilityBlock(
            verdict=ReliabilityVerdict.UNRELIABLE_HIGH_WIND,
            reason=(
                f"Wind speed {wind:.1f} m/s exceeds {t.WIND_DEGRADED_HIGH_MAX} m/s. "
                "Slicks are broken up and undetectable above this threshold; dark "
                "regions in the scene are more likely wave shadow than oil. "
                "Detection suppressed; confidence forced to 0."
            ),
            confidence_multiplier=0.0,
            suppressed=True,
            possible_rain_artefact=possible_rain,
        )
    elif wind <= t.WIND_DEGRADED_LOW_MAX:
        area_ok = slick_area_m2 >= t.DEGRADED_LOW_MIN_AREA_M2
        block = ReliabilityBlock(
            verdict=ReliabilityVerdict.DEGRADED_LOW,
            reason=(
                f"Wind speed {wind:.1f} m/s is in the marginal low-wind band "
                f"({t.WIND_UNRELIABLE_LOW}-{t.WIND_DEGRADED_LOW_MAX} m/s). Confidence "
                "halved" + ("" if area_ok else f"; slick area {slick_area_m2:.0f} m² is "
                f"below the {t.DEGRADED_LOW_MIN_AREA_M2:.0f} m² minimum for this band, "
                "further degrading reliability") + "."
            ),
            confidence_multiplier=t.DEGRADED_LOW_CONFIDENCE_MULT if area_ok else 0.15,
            suppressed=False,
            possible_rain_artefact=possible_rain,
        )
    elif wind <= t.WIND_OPTIMAL_MAX:
        block = ReliabilityBlock(
            verdict=ReliabilityVerdict.OPTIMAL,
            reason=(
                f"Wind speed {wind:.1f} m/s is within the optimal detection band "
                f"({t.WIND_DEGRADED_LOW_MAX}-{t.WIND_OPTIMAL_MAX} m/s). Full confidence."
            ),
            confidence_multiplier=1.0,
            suppressed=False,
            possible_rain_artefact=possible_rain,
        )
    else:
        block = ReliabilityBlock(
            verdict=ReliabilityVerdict.DEGRADED_HIGH,
            reason=(
                f"Wind speed {wind:.1f} m/s is in the marginal high-wind band "
                f"({t.WIND_OPTIMAL_MAX}-{t.WIND_DEGRADED_HIGH_MAX} m/s). Oil begins "
                "emulsifying with seawater at this wind speed, weakening the dampening "
                "signature. Confidence reduced."
            ),
            confidence_multiplier=t.DEGRADED_HIGH_CONFIDENCE_MULT,
            suppressed=False,
            possible_rain_artefact=possible_rain,
        )

    if not (t.INCIDENCE_ANGLE_MIN <= env.incidence_angle_deg <= t.INCIDENCE_ANGLE_MAX) and not block.suppressed:
        block = block.model_copy(update={
            "confidence_multiplier": round(block.confidence_multiplier * t.INCIDENCE_DOWNGRADE_MULT, 4),
            "reason": block.reason + (
                f" Additionally, incidence angle {env.incidence_angle_deg:.1f}° is outside the "
                f"reliable {t.INCIDENCE_ANGLE_MIN}-{t.INCIDENCE_ANGLE_MAX}° range — downgraded one level."
            ),
        })

    if possible_rain and not block.suppressed:
        block = block.model_copy(update={
            "reason": block.reason + (
                f" Precipitation of {env.precipitation_mm_hr:.1f} mm/hr detected — "
                "flagged as a possible rain artefact; verify against optical imagery if available."
            ),
        })

    return block
