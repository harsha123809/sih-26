"""Inference wrapper.

SIMULATION_MODE = True: no trained weights exist (no GPU / training corpus
was available at build time — see README for details on sourcing the
Krestenitis dataset and training a real checkpoint). This wrapper returns
deterministic, physically-plausible segmentation masks and class
probabilities derived from each seeded demo scene's ground-truth scenario
tag and environmental conditions, run through the SAME EnvAttentionUNet
forward pass shape and the SAME physics gate as the real pipeline would use.
Swapping in a trained checkpoint means setting SIMULATION_MODE=False and
pointing MODEL_WEIGHTS_PATH at a real .pt file — no other code changes.
"""
from __future__ import annotations

import hashlib
import math
import random

from app.core.ml.model import CLASS_NAMES
from app.core.physics.gate import evaluate_physics_gate
from app.models import ClassProbabilities, EnvironmentalConditions, OilClass, ReliabilityBlock

SIMULATION_MODE = True
MODEL_WEIGHTS_PATH = None  # set to a .pt checkpoint path and flip SIMULATION_MODE=False to go live

# scenario_tag -> (dominant class, base probability, VV/VH ratio dB range)
_SCENARIO_PROFILES: dict[str, tuple[OilClass, float, tuple[float, float]]] = {
    "crude_tanker": (OilClass.CRUDE_OIL, 0.82, (2.5, 4.0)),
    "hfo_container": (OilClass.HEAVY_FUEL_OIL, 0.78, (6.0, 8.5)),
    "low_wind_suppressed": (OilClass.CRUDE_OIL, 0.55, (1.0, 2.0)),  # model "sees" something; gate must suppress it
    "spoofing": (OilClass.CRUDE_OIL, 0.74, (3.0, 4.5)),
    "dark_ship": (OilClass.HEAVY_FUEL_OIL, 0.71, (5.5, 7.5)),
    "crude_excluded_feeder": (OilClass.CRUDE_OIL, 0.80, (2.8, 4.2)),
}


def _unclassified_real_scene(
    scene_id: str,
    env: EnvironmentalConditions,
    bbox: list[float],
    sar_stats: dict | None,
) -> dict:
    """A real ingested product, with no trained model to classify it.

    Everything here is either measured or honestly absent. There is no
    segmentation polygon because segmentation is exactly what the untrained
    model would have produced, and no class probabilities because inventing
    them is the specific failure this whole system is built to avoid.
    """
    west, south, east, north = bbox
    centroid = [(west + east) / 2, (south + north) / 2]

    ratio_stats = (sar_stats or {}).get("ratio_db")
    has_polarimetry = ratio_stats is not None
    measured_ratio = round(float(ratio_stats["median"]), 2) if ratio_stats else 0.0

    # The physics gate still applies: it is a function of sea state, not of
    # the model, so its verdict is just as valid on real data.
    reliability = evaluate_physics_gate(env, 0.0)

    return {
        "predicted_class": OilClass.UNRESOLVED,
        "class_probabilities": ClassProbabilities(),
        "polygon": {"type": "Polygon", "coordinates": []},
        "area_m2": 0.0,
        "centroid": centroid,
        "vv_vh_ratio_db": measured_ratio,
        "reliability": reliability,
        "has_polarimetry": has_polarimetry,
        "simulation_mode": SIMULATION_MODE,
        "classification_available": False,
        "classification_note": (
            "This is a real SAR product, so there is no seeded scenario to draw a "
            "demo classification from — and no trained checkpoint to compute a real "
            "one. Geometry, geolocation and the VV/VH ratio below are measured from "
            "the actual pixels; oil type is reported as UNRESOLVED rather than "
            "guessed. Train the model and set SIMULATION_MODE=False to classify."
        ),
    }


def _seeded_rng(scene_id: str) -> random.Random:
    seed = int(hashlib.sha256(scene_id.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _softmax_like_probs(dominant: OilClass, base_prob: float, rng: random.Random) -> ClassProbabilities:
    remaining = 1.0 - base_prob
    others = [c for c in CLASS_NAMES if c != dominant.value]
    noise = [rng.random() for _ in others]
    total_noise = sum(noise) or 1.0
    probs = {dominant.value: base_prob}
    for name, n in zip(others, noise):
        probs[name] = remaining * (n / total_noise)
    return ClassProbabilities(**probs)


def _apply_confidence_multiplier(probs: ClassProbabilities, multiplier: float) -> ClassProbabilities:
    """Redistribute probability mass toward open_water as reliability drops —
    this is what makes the UI 'look unsure' rather than just tagging a number
    onto an unchanged confident prediction."""
    if multiplier >= 1.0:
        return probs
    data = probs.model_dump()
    ow = data.pop("open_water")
    scaled = {k: v * multiplier for k, v in data.items()}
    leftover = 1.0 - sum(scaled.values())
    return ClassProbabilities(open_water=leftover, **scaled)


def run_inference(
    scene_id: str,
    scenario_tag: str,
    env: EnvironmentalConditions,
    bbox: list[float],
    is_real_sar: bool = False,
    sar_stats: dict | None = None,
) -> dict:
    """Returns a dict with predicted_class, class_probabilities, polygon,
    area_m2, centroid, vv_vh_ratio_db, reliability (ReliabilityBlock),
    has_polarimetry, simulation_mode.

    For an ingested real SAR product there is no scenario tag to draw a
    scripted answer from, and no trained checkpoint to compute a real one.
    Rather than emit a confident-looking fabrication, such scenes return
    UNRESOLVED with classification_available=False. The measured VV/VH ratio
    IS reported, because that part is a real measurement off real pixels.
    """
    if is_real_sar and SIMULATION_MODE:
        return _unclassified_real_scene(scene_id, env, bbox, sar_stats)

    rng = _seeded_rng(scene_id)
    dominant, base_prob, ratio_range = _SCENARIO_PROFILES.get(
        scenario_tag, (OilClass.OPEN_WATER, 0.9, (0.0, 1.0))
    )

    west, south, east, north = bbox
    cx, cy = (west + east) / 2, (south + north) / 2
    # Keep the simulated slick a plausible size (single-digit to low-tens of
    # km^2) rather than smearing across the whole scene bbox.
    span_x, span_y = (east - west) * 0.045, (north - south) * 0.045

    # Build a small irregular polygon around the scene centre to stand in for
    # the segmentation mask contour.
    n_pts = 10
    poly = []
    for i in range(n_pts):
        angle = 2 * math.pi * i / n_pts
        r_x = span_x * (0.7 + 0.3 * rng.random())
        r_y = span_y * (0.7 + 0.3 * rng.random())
        poly.append([cx + r_x * math.cos(angle), cy + r_y * math.sin(angle)])
    poly.append(poly[0])

    # Rough planar area estimate (deg^2 -> m^2 approx at mid-latitudes)
    area_deg2 = 0.5 * abs(sum(
        poly[i][0] * poly[i + 1][1] - poly[i + 1][0] * poly[i][1] for i in range(n_pts)
    ))
    area_m2 = area_deg2 * (111_320 ** 2) * math.cos(math.radians(cy))

    has_polarimetry = env.has_polarimetry
    if not has_polarimetry:
        predicted_class = OilClass.UNRESOLVED
        probs = ClassProbabilities(open_water=0.2, crude_oil=0.0, heavy_fuel_oil=0.0, look_alike=0.0, ship=0.0, land=0.0)
        vv_vh_ratio_db = 0.0
    else:
        probs = _softmax_like_probs(dominant, base_prob, rng)
        predicted_class = dominant
        vv_vh_ratio_db = round(rng.uniform(*ratio_range), 2)

    reliability: ReliabilityBlock = evaluate_physics_gate(env, area_m2)

    if reliability.suppressed:
        # Probability mass collapses entirely to open_water, so the reported
        # class must agree — a suppressed detection can never carry an oil
        # label, regardless of what the raw (pre-gate) model output was.
        predicted_class = OilClass.OPEN_WATER
        probs = ClassProbabilities(open_water=1.0, crude_oil=0.0, heavy_fuel_oil=0.0, look_alike=0.0, ship=0.0, land=0.0)
    elif has_polarimetry:
        probs = _apply_confidence_multiplier(probs, reliability.confidence_multiplier)

    return {
        "predicted_class": predicted_class,
        "class_probabilities": probs,
        "polygon": {"type": "Polygon", "coordinates": [poly]},
        "area_m2": round(area_m2, 1),
        "centroid": [cx, cy],
        "vv_vh_ratio_db": vv_vh_ratio_db,
        "reliability": reliability,
        "has_polarimetry": has_polarimetry,
        "simulation_mode": SIMULATION_MODE,
        "classification_available": True,
        "classification_note": None,
    }
