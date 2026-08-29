from __future__ import annotations

import datetime as dt
import math
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.evidence_export import build_evidence_bundle, build_evidence_pdf
from app.core.attribution.scoring import score_candidates
from app.core.geo.cfar import detect_and_cross_reference
from app.core.ml.infer import run_inference
from app.core.physics.backtrack import run_backtrack
from app.data import store
from app.models import (
    ClassProbabilities,
    Detection,
    EnvironmentalConditions,
    Incident,
    OilClass,
    ReliabilityVerdict,
    Scene,
)
from app.scenario_map import CANDIDATE_MMSIS_BY_SCENE

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok", "simulation_mode": True}


@router.get("/config/thresholds")
def config_thresholds():
    from app.config import thresholds as t
    return {
        "wind_bands_ms": {
            "unreliable_low_max": t.WIND_UNRELIABLE_LOW,
            "degraded_low_max": t.WIND_DEGRADED_LOW_MAX,
            "optimal_max": t.WIND_OPTIMAL_MAX,
            "degraded_high_max": t.WIND_DEGRADED_HIGH_MAX,
        },
        "confidence_multipliers": {
            "degraded_low": t.DEGRADED_LOW_CONFIDENCE_MULT,
            "degraded_high": t.DEGRADED_HIGH_CONFIDENCE_MULT,
        },
        "incidence_angle_deg": {"min": t.INCIDENCE_ANGLE_MIN, "max": t.INCIDENCE_ANGLE_MAX},
        "rain_artefact_mm_hr": t.RAIN_ARTEFACT_MM_HR,
        "attribution_weights": {
            "spatiotemporal": t.WEIGHT_SPATIOTEMPORAL,
            "cargo_compatibility": t.WEIGHT_CARGO_COMPAT,
            "deception_index": t.WEIGHT_DECEPTION_INDEX,
            "behavioural_anomaly": t.WEIGHT_BEHAVIOURAL_ANOMALY,
            "exclusion_penalty": t.WEIGHT_EXCLUSION_PENALTY,
        },
        "truth_gap": {
            "ais_match_radius_m": t.AIS_MATCH_RADIUS_M,
            "dark_ship_radius_m": t.DARK_SHIP_RADIUS_M,
            "dark_ship_silence_minutes": t.DARK_SHIP_SILENCE_MINUTES,
        },
        "backtrack": {
            "default_particle_count": t.DEFAULT_PARTICLE_COUNT,
            "windage_crude": t.DEFAULT_WINDAGE_CRUDE,
            "windage_hfo": t.DEFAULT_WINDAGE_HFO,
            "eddy_diffusivity_m2_s": t.EDDY_DIFFUSIVITY_M2_S,
        },
    }


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------

@router.get("/scenes", response_model=list[Scene])
def list_scenes():
    return store.list_scenes()


@router.post("/scenes/ingest", response_model=Scene)
def ingest_scene(scene: Scene):
    # Metadata-only ingestion (no raster). For a real product, use
    # POST /api/scenes/ingest-sar instead.
    existing = store.get_scene(scene.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Scene {scene.id} already exists")
    store.add_scene(scene)
    return scene


SAR_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sar"


@router.post("/scenes/ingest-sar", response_model=Scene)
async def ingest_sar(
    vv_file: UploadFile = File(..., description="Sentinel-1 GRD VV band (GeoTIFF)"),
    vh_file: UploadFile | None = File(None, description="Optional VH band (GeoTIFF)"),
    name: str = Form("Ingested SAR Scene"),
    acquisition_time: str | None = Form(None),
    wind_speed_ms: float = Form(...),
    wind_dir_deg: float = Form(0.0),
    sea_surface_temp_c: float = Form(28.0),
    incidence_angle_deg: float = Form(33.0),
    wave_height_m: float = Form(1.0),
    precipitation_mm_hr: float = Form(0.0),
):
    """Ingest a real Sentinel-1 GRD product.

    Wind speed is required, not optional: without it the physics gate cannot
    say whether a detection over this scene would be trustworthy, and an
    ungated detection is exactly what this system exists to avoid producing.
    Get it from ERA5/GFS reanalysis for the acquisition timestamp.
    """
    from app.core.ml.sentinel1 import load_sar_scene, render_thumbnail

    scene_id = f"sar-{uuid.uuid4().hex[:10]}"
    scene_dir = SAR_DATA_DIR / scene_id
    scene_dir.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    try:
        vv_path = scene_dir / f"vv{_suffix(vv_file.filename)}"
        await _save_upload(vv_file, vv_path)
        saved.append(str(vv_path))

        vh_path = None
        if vh_file is not None and vh_file.filename:
            vh_path = scene_dir / f"vh{_suffix(vh_file.filename)}"
            await _save_upload(vh_file, vh_path)
            saved.append(str(vh_path))

        sar = load_sar_scene(vv_path, vh_path)
    except ValueError as exc:
        shutil.rmtree(scene_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        shutil.rmtree(scene_dir, ignore_errors=True)
        raise HTTPException(
            status_code=422,
            detail=f"Could not read this as a geospatial raster: {exc}",
        )

    if not all(math.isfinite(v) for v in sar.bbox):
        shutil.rmtree(scene_dir, ignore_errors=True)
        raise HTTPException(
            status_code=422,
            detail=(
                "Product has no usable CRS/geotransform, so it cannot be placed on "
                "the map. Use a georeferenced (terrain-corrected) GRD product."
            ),
        )

    render_thumbnail(sar, scene_dir / "thumbnail.png")

    scene = Scene(
        id=scene_id,
        name=name,
        description=(
            f"Ingested Sentinel-1 product ({'dual-pol VV+VH' if sar.has_polarimetry else 'single-pol VV only'}), "
            f"{sar.width}x{sar.height} px after decimation, CRS {sar.crs}."
        ),
        acquisition_time=acquisition_time or (dt.datetime.utcnow().isoformat() + "Z"),
        bbox=[round(v, 6) for v in sar.bbox],
        thumbnail_url=f"/api/scenes/{scene_id}/thumbnail",
        environment=EnvironmentalConditions(
            wind_speed_ms=wind_speed_ms,
            wind_dir_deg=wind_dir_deg,
            sea_surface_temp_c=sea_surface_temp_c,
            incidence_angle_deg=incidence_angle_deg,
            wave_height_m=wave_height_m,
            precipitation_mm_hr=precipitation_mm_hr,
            has_polarimetry=sar.has_polarimetry,
        ),
        scenario_tag="ingested_real_sar",
        is_real_sar=True,
        sar_stats=sar.stats,
        source_files=saved,
    )
    store.add_scene(scene)
    return scene


@router.get("/scenes/{scene_id}/thumbnail")
def scene_thumbnail(scene_id: str):
    scene = store.get_scene(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    path = SAR_DATA_DIR / scene_id / "thumbnail.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No thumbnail for this scene")
    return FileResponse(path, media_type="image/png")


def _suffix(filename: str | None) -> str:
    if not filename:
        return ".tif"
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in (".tif", ".tiff", ".img", ".vrt") else ".tif"


async def _save_upload(upload: UploadFile, dest: Path) -> None:
    """Stream to disk in chunks — GRD products run to several GB."""
    with dest.open("wb") as fh:
        while chunk := await upload.read(1024 * 1024):
            fh.write(chunk)


class AnalyseRequest(BaseModel):
    apply_physics_gate: bool = True
    force_wind_speed_ms: float | None = None


@router.post("/scenes/{scene_id}/analyse", response_model=Detection)
def analyse_scene(scene_id: str, req: AnalyseRequest = AnalyseRequest()):
    scene = store.get_scene(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    env = scene.environment
    if req.force_wind_speed_ms is not None:
        env = env.model_copy(update={"wind_speed_ms": req.force_wind_speed_ms})

    result = run_inference(
        scene.id, scene.scenario_tag, env, scene.bbox,
        is_real_sar=scene.is_real_sar, sar_stats=scene.sar_stats,
    )

    # Turning the gate off shows raw model output; it cannot conjure a
    # classification where none exists, so a real SAR scene stays UNRESOLVED.
    if not req.apply_physics_gate and not scene.is_real_sar:
        # Raw, unfiltered model output — the UI must show a warning banner
        # alongside this. We recompute probabilities without the gate's
        # confidence multiplier by re-running with an always-optimal gate
        # override, but we KEEP the true reliability block so the frontend
        # can still tell the operator what the gate would have said.
        optimal_env = env.model_copy(update={"wind_speed_ms": 6.0, "incidence_angle_deg": 30.0, "precipitation_mm_hr": 0.0})
        raw = run_inference(scene.id, scene.scenario_tag, optimal_env, scene.bbox)
        result["class_probabilities"] = raw["class_probabilities"]
        result["predicted_class"] = raw["predicted_class"]

    detection = Detection(
        id=f"det-{uuid.uuid4().hex[:10]}",
        scene_id=scene.id,
        predicted_class=result["predicted_class"],
        class_probabilities=result["class_probabilities"],
        area_m2=result["area_m2"],
        centroid=result["centroid"],
        polygon=result["polygon"],
        reliability=result["reliability"],
        has_polarimetry=result["has_polarimetry"],
        vv_vh_ratio_db=result["vv_vh_ratio_db"],
        simulation_mode=result["simulation_mode"],
        timestamp=scene.acquisition_time,
        classification_available=result.get("classification_available", True),
        classification_note=result.get("classification_note"),
    )
    store.save_detection(detection)

    incident = Incident(
        id=f"inc-{detection.id}",
        scene_id=scene.id,
        detection_id=detection.id,
        status="OPEN",
        created_at=dt.datetime.utcnow().isoformat() + "Z",
    )
    store.save_incident(incident)

    return detection


# ---------------------------------------------------------------------------
# Detections
# ---------------------------------------------------------------------------

@router.get("/detections", response_model=list[Detection])
def list_detections(
    bbox: str | None = Query(None, description="west,south,east,north"),
    predicted_class: OilClass | None = None,
    min_confidence: float | None = None,
    reliability_verdict: ReliabilityVerdict | None = None,
):
    detections = store.list_detections()

    if predicted_class is not None:
        detections = [d for d in detections if d.predicted_class == predicted_class]
    if reliability_verdict is not None:
        detections = [d for d in detections if d.reliability.verdict == reliability_verdict]
    if min_confidence is not None:
        def top_prob(d: Detection) -> float:
            return max(d.class_probabilities.model_dump().values())
        detections = [d for d in detections if top_prob(d) >= min_confidence]
    if bbox is not None:
        west, south, east, north = (float(v) for v in bbox.split(","))
        detections = [d for d in detections if west <= d.centroid[0] <= east and south <= d.centroid[1] <= north]

    return detections


@router.get("/detections/{detection_id}", response_model=Detection)
def get_detection(detection_id: str):
    d = store.get_detection(detection_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    return d


# ---------------------------------------------------------------------------
# Incidents / attribution
# ---------------------------------------------------------------------------

class BacktrackRequest(BaseModel):
    hours: int = 72
    particle_count: int = 5000


@router.post("/incidents/{incident_id}/backtrack")
def backtrack_incident(incident_id: str, req: BacktrackRequest):
    incident = store.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    detection = store.get_detection(incident.detection_id)
    scene = store.get_scene(incident.scene_id)
    if detection is None or scene is None:
        raise HTTPException(status_code=404, detail="Underlying detection/scene missing")

    frames, origin = run_backtrack(
        centroid_lonlat=detection.centroid,
        env=scene.environment,
        predicted_class=detection.predicted_class,
        hours=req.hours,
        particle_count=req.particle_count,
        acquisition_time=scene.acquisition_time,
        seed=hash(incident_id) % (2**32),
    )

    from app.models import BacktrackResult
    incident.backtrack = BacktrackResult(
        incident_id=incident_id, hours_traced=req.hours, particle_count=req.particle_count,
        frames=frames, origin_estimate=origin,
    )
    store.save_incident(incident)
    return incident.backtrack


@router.get("/incidents/{incident_id}/attribution")
def get_attribution(incident_id: str):
    incident = store.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    detection = store.get_detection(incident.detection_id)
    scene = store.get_scene(incident.scene_id)
    if detection is None or scene is None:
        raise HTTPException(status_code=404, detail="Underlying detection/scene missing")

    truth_gap_results = detect_and_cross_reference(scene.id, scene.bbox)
    incident.truth_gap_results = truth_gap_results

    origin = incident.backtrack.origin_estimate if incident.backtrack else detection.centroid
    candidate_mmsis = CANDIDATE_MMSIS_BY_SCENE.get(scene.id, [])
    candidates = score_candidates(
        detection.predicted_class, origin, candidate_mmsis, truth_gap_results,
        detection_centroid_lonlat=detection.centroid,
    )
    incident.candidates = candidates
    store.save_incident(incident)

    return {"candidates": candidates, "truth_gap_results": truth_gap_results}


@router.get("/incidents/{incident_id}/evidence")
def get_evidence(incident_id: str, format: str = Query("json", pattern="^(json|pdf)$")):
    incident = store.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    detection = store.get_detection(incident.detection_id)
    scene = store.get_scene(incident.scene_id)
    if detection is None or scene is None:
        raise HTTPException(status_code=404, detail="Underlying detection/scene missing")

    if format == "pdf":
        pdf_bytes = build_evidence_pdf(scene, detection, incident)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{incident_id}-evidence.pdf"'},
        )

    return build_evidence_bundle(scene, detection, incident)


class StatusUpdateRequest(BaseModel):
    status: str  # CONFIRMED | FALSE_POSITIVE | OPEN


@router.patch("/incidents/{incident_id}/status", response_model=Incident)
def update_incident_status(incident_id: str, req: StatusUpdateRequest):
    incident = store.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if req.status not in ("CONFIRMED", "FALSE_POSITIVE", "OPEN"):
        raise HTTPException(status_code=400, detail="Invalid status")
    incident.status = req.status
    store.save_incident(incident)
    return incident


@router.get("/incidents", response_model=list[Incident])
def list_incidents():
    return store.list_incidents()


@router.get("/incidents/{incident_id}", response_model=Incident)
def get_incident(incident_id: str):
    incident = store.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


# ---------------------------------------------------------------------------
# Vessels / Truth Gap
# ---------------------------------------------------------------------------

@router.get("/scenes/{scene_id}/truth-gap")
def scene_truth_gap(scene_id: str):
    scene = store.get_scene(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return detect_and_cross_reference(scene_id, scene.bbox)


@router.get("/vessels/spoofing")
def vessels_spoofing():
    results = []
    for scene in store.list_scenes():
        for r in detect_and_cross_reference(scene.id, scene.bbox):
            if r.status.value in ("SPOOFING_SUSPECTED", "DARK_SHIP"):
                results.append({"scene_id": scene.id, "scene_name": scene.name, **r.model_dump()})
    return results


@router.get("/vessels")
def list_vessels():
    return store.list_vessels()


@router.get("/vessels/{mmsi}/track")
def vessel_track(mmsi: str):
    vessel = store.get_vessel(mmsi)
    if vessel is None:
        raise HTTPException(status_code=404, detail="Vessel not found")
    return {"vessel": vessel, "track": store.get_ais_track(mmsi)}
