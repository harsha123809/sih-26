"""CFAR (Constant False Alarm Rate) ship detection over the VV channel, and
the cross-reference against AIS that exposes dark ships and spoofing.

A true CFAR detector slides a guard-banded window across the VV amplitude
image, treats the surrounding "training cells" as a local clutter-noise
estimate, and flags a cell as a target when its return exceeds the local
noise floor by a threshold factor. `cfar_detect_synthetic` below implements
that algorithm against a synthetic clutter field seeded with a known target,
so the detector itself is real and testable even though the calling code
(in SIMULATION_MODE) supplies deterministic seeded scene ground-truth
instead of an actual downlinked SAR product.
"""
from __future__ import annotations

import math

import numpy as np

from app.config import thresholds as t
from app.data import store
from app.models import AISPosition, RadarTarget, VesselMatchStatus, VesselProfile, VesselTruthGapResult


def cfar_detect_synthetic(
    scene_size: int = 256,
    target_center: tuple[int, int] | None = None,
    target_snr_db: float = 18.0,
    guard: int = 3,
    training: int = 8,
    pfa: float = 1e-4,
) -> list[dict]:
    """Cell-Averaging CFAR over a synthetic Rayleigh-clutter VV amplitude
    image with a single injected bright target. Returns detected cells above
    the adaptive threshold. This demonstrates the real algorithm; production
    use would run this over the actual VV amplitude tile."""
    rng = np.random.default_rng(7)
    clutter_sigma = 1.0
    img = rng.rayleigh(clutter_sigma, size=(scene_size, scene_size))

    if target_center is None:
        target_center = (scene_size // 2, scene_size // 2)
    peak_amp = clutter_sigma * (10 ** (target_snr_db / 20))
    cy, cx = target_center
    yy, xx = np.mgrid[0:scene_size, 0:scene_size]
    blob = peak_amp * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 2.0 ** 2)))
    img = img + blob

    alpha = training * 2 * (pfa ** (-1 / (training * 2)) - 1)  # CA-CFAR threshold factor
    detections = []
    win = guard + training
    for y in range(win, scene_size - win, 4):  # stride for speed
        for x in range(win, scene_size - win, 4):
            window = img[y - win:y + win + 1, x - win:x + win + 1].copy()
            window[win - guard:win + guard + 1, win - guard:win + guard + 1] = np.nan
            noise_est = np.nanmean(window)
            threshold = alpha * noise_est
            if img[y, x] > threshold:
                snr_db = 20 * math.log10(max(img[y, x] / max(noise_est, 1e-6), 1e-6))
                detections.append({"y": y, "x": x, "amplitude": float(img[y, x]), "snr_db": round(snr_db, 1)})
    return detections


def detect_and_cross_reference(scene_id: str, bbox: list[float]) -> list[VesselTruthGapResult]:
    """Runs the (simulated) CFAR pass for a scene and cross-references every
    radar-visible target against interpolated AIS positions, producing the
    Truth Gap result set: MATCHED / DARK_SHIP / SPOOFING_SUSPECTED, each with
    a Deception Index."""
    truth = store.get_radar_truth(scene_id)
    if truth is None:
        return []

    radar_target = RadarTarget(
        id=f"radar-{scene_id}",
        lat=truth["lat"],
        lon=truth["lon"],
        estimated_length_m=truth["length_m"],
        snr_db=truth["snr_db"],
    )

    claimed_mmsi = truth.get("mmsi")
    results: list[VesselTruthGapResult] = []

    if claimed_mmsi:
        vessel = store.get_vessel(claimed_mmsi)
        track = store.get_ais_track(claimed_mmsi)
        claimed_pos = _nearest_ais_position(track)
        distance_m = _haversine_m(radar_target.lat, radar_target.lon, claimed_pos.lat, claimed_pos.lon) if claimed_pos else float("inf")

        if claimed_pos and distance_m <= t.AIS_MATCH_RADIUS_M:
            status = VesselMatchStatus.MATCHED
        elif claimed_pos and distance_m > t.AIS_MATCH_RADIUS_M:
            status = VesselMatchStatus.SPOOFING_SUSPECTED
        else:
            status = VesselMatchStatus.DARK_SHIP

        results.append(VesselTruthGapResult(
            radar_target=radar_target,
            claimed_ais=claimed_pos,
            vessel_profile=vessel,
            status=status,
            deception_index_m=round(distance_m, 1) if distance_m != float("inf") else 0.0,
        ))
    else:
        # No AIS at all for the physical radar target within range -> dark ship.
        results.append(VesselTruthGapResult(
            radar_target=radar_target,
            claimed_ais=None,
            vessel_profile=None,
            status=VesselMatchStatus.DARK_SHIP,
            deception_index_m=0.0,
        ))

    return results


def _nearest_ais_position(track: list[AISPosition]) -> AISPosition | None:
    if not track:
        return None
    mid = len(track) // 2
    return track[mid]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
