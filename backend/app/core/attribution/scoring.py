"""Cargo-aware forensic attribution: for every vessel whose track intersects
the drift cone during the plausible release window, compute a weighted
plausibility score. Exclusion is a first-class result, not a discard —
ruling a vessel out on cargo grounds is exactly the "forensic" move that
separates this system from nearest-ship attribution.
"""
from __future__ import annotations

import math

from app.config import thresholds as t
from app.data import store
from app.models import (
    AttributionCandidate,
    OilClass,
    VesselMatchStatus,
    VesselProfile,
    VesselTruthGapResult,
)

# vessel_type -> plausible bunker fuel; used for the "own bunkers" compatibility rule.
_TYPICAL_BUNKER_BY_TYPE = {
    "Container Ship": "Heavy Fuel Oil",
    "Container Feeder": "Marine Diesel Oil",
    "Bulk Carrier": "Heavy Fuel Oil",
    "Crude Oil Tanker": "Heavy Fuel Oil",
    "Product Tanker": "Heavy Fuel Oil",
}

# vessel_type -> can plausibly carry crude oil as CARGO (not bunker).
_CAN_CARRY_CRUDE_CARGO = {"Crude Oil Tanker", "Product Tanker"}


def _cargo_compatibility(predicted_class: OilClass, vessel: VesselProfile) -> tuple[float, str, bool, str | None]:
    """Returns (compatibility_score, reasoning_line, excluded, exclusion_reason)."""
    if predicted_class == OilClass.HEAVY_FUEL_OIL:
        # HFO spills are frequently the vessel's OWN bunker fuel, not cargo —
        # almost any large commercial vessel is a plausible source.
        if vessel.bunker_fuel_type == "Heavy Fuel Oil":
            return (
                0.9,
                f"{vessel.name} bunkers Heavy Fuel Oil — its own fuel supply is a plausible "
                "source for an HFO slick regardless of cargo carried.",
                False, None,
            )
        return (
            0.2,
            f"{vessel.name} bunkers {vessel.bunker_fuel_type}, not HFO — low but non-zero "
            "compatibility (residual bilge contamination is possible).",
            False, None,
        )

    if predicted_class == OilClass.CRUDE_OIL:
        if vessel.cargo_type == "Crude Oil" and (vessel.cargo_capacity_m3 or 0) > 0:
            return (
                0.95,
                f"{vessel.name} is carrying Crude Oil cargo ({vessel.cargo_capacity_m3:.0f} m³ capacity) — "
                "high compatibility with the detected crude signature.",
                False, None,
            )
        if vessel.vessel_type not in _CAN_CARRY_CRUDE_CARGO:
            return (
                0.0,
                f"{vessel.name} is a {vessel.vessel_type} with no crude cargo capacity.",
                True,
                f"Vessel type '{vessel.vessel_type}' has no crude oil cargo capacity; "
                "detected pollutant is Crude Oil, not the vessel's own bunker fuel — ruled out.",
            )
        return (
            0.25,
            f"{vessel.name} is a {vessel.vessel_type} capable of carrying crude but not "
            "currently manifested as doing so — low compatibility.",
            False, None,
        )

    return (0.1, f"Detected class {predicted_class.value} has no strong cargo-compatibility signal for {vessel.name}.", False, None)


def _spatiotemporal_overlap(vessel_track_point: tuple[float, float] | None, cone_center: tuple[float, float]) -> float:
    if vessel_track_point is None:
        return 0.0
    dist_m = _haversine_m(vessel_track_point[0], vessel_track_point[1], cone_center[0], cone_center[1])
    # Decay: full score within 2km, ~0 beyond 60km.
    return max(0.0, math.exp(-dist_m / 20_000))


def _behavioural_anomaly(truth_gap: VesselTruthGapResult | None) -> tuple[float, str | None]:
    if truth_gap is None:
        return 0.0, None
    if truth_gap.status == VesselMatchStatus.SPOOFING_SUSPECTED:
        return 0.95, f"AIS spoofing detected: reported position is {truth_gap.deception_index_m:.0f} m from the radar-confirmed physical position."
    if truth_gap.status == VesselMatchStatus.DARK_SHIP:
        return 0.85, "Vessel is radar-visible but transmitting no AIS — dark for the relevant window."
    return 0.0, None


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def score_candidates(
    predicted_class: OilClass,
    origin_estimate_lonlat: list[float],
    candidate_mmsis: list[str],
    truth_gap_results: list[VesselTruthGapResult],
    detection_centroid_lonlat: list[float] | None = None,
) -> list[AttributionCandidate]:
    cone_center = (origin_estimate_lonlat[1], origin_estimate_lonlat[0])  # (lat, lon)
    detection_center = (
        (detection_centroid_lonlat[1], detection_centroid_lonlat[0])
        if detection_centroid_lonlat else cone_center
    )
    truth_gap_by_mmsi = {r.vessel_profile.mmsi: r for r in truth_gap_results if r.vessel_profile}

    candidates: list[AttributionCandidate] = []
    for mmsi in candidate_mmsis:
        vessel = store.get_vessel(mmsi)
        if vessel is None:
            continue
        track = store.get_ais_track(mmsi)
        point = (track[len(track) // 2].lat, track[len(track) // 2].lon) if track else None

        # A vessel present at the detection site AT ACQUISITION TIME is at
        # least as strong evidence as one merely near the fully-backtracked
        # (and increasingly uncertain) drift-cone origin — take the better
        # of the two rather than penalising a ship that was right there now.
        spatiotemporal = max(
            _spatiotemporal_overlap(point, detection_center),
            _spatiotemporal_overlap(point, cone_center),
        )
        cargo_score, cargo_line, excluded, exclusion_reason = _cargo_compatibility(predicted_class, vessel)
        truth_gap = truth_gap_by_mmsi.get(mmsi)
        deception_norm = min((truth_gap.deception_index_m / 50_000) if truth_gap else 0.0, 1.0)
        anomaly_score, anomaly_line = _behavioural_anomaly(truth_gap)
        exclusion_penalty = 1.0 if excluded else 0.0

        score = (
            t.WEIGHT_SPATIOTEMPORAL * spatiotemporal
            + t.WEIGHT_CARGO_COMPAT * cargo_score
            + t.WEIGHT_DECEPTION_INDEX * deception_norm
            + t.WEIGHT_BEHAVIOURAL_ANOMALY * anomaly_score
            - t.WEIGHT_EXCLUSION_PENALTY * exclusion_penalty
        )
        if excluded:
            score = 0.0

        if point:
            dist_detection = _haversine_m(point[0], point[1], *detection_center)
            dist_origin = _haversine_m(point[0], point[1], *cone_center)
            if dist_detection <= dist_origin:
                overlap_line = (
                    f"Spatiotemporal overlap: {spatiotemporal:.2f} — vessel AIS position was "
                    f"{dist_detection:.0f} m from the detection site at acquisition time."
                )
            else:
                overlap_line = (
                    f"Spatiotemporal overlap: {spatiotemporal:.2f} — vessel AIS position was "
                    f"{dist_origin:.0f} m from the back-tracked drift-cone origin estimate."
                )
        else:
            overlap_line = "No AIS track available for overlap analysis."

        reasoning = [overlap_line, cargo_line]
        if anomaly_line:
            reasoning.append(anomaly_line)
        if excluded:
            reasoning.append(f"EXCLUDED: {exclusion_reason}")

        candidates.append(AttributionCandidate(
            vessel=vessel,
            spatiotemporal_overlap=round(spatiotemporal, 3),
            cargo_compatibility=round(cargo_score, 3),
            normalised_deception_index=round(deception_norm, 3),
            behavioural_anomaly=round(anomaly_score, 3),
            exclusion_penalty=exclusion_penalty,
            score=round(max(score, 0.0), 3),
            excluded=excluded,
            exclusion_reason=exclusion_reason,
            reasoning=reasoning,
        ))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates
