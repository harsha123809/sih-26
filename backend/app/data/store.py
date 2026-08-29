"""In-memory application store. Swappable for MongoDB/Postgres later — the
API layer only talks to the functions below, never to module globals directly.
"""
from __future__ import annotations

from app.data.seed import AIS_TRACKS, RADAR_TRUTH_POSITIONS, SCENES, VESSELS
from app.models import AISPosition, Detection, Incident, Scene, VesselProfile

_detections: dict[str, Detection] = {}
_incidents: dict[str, Incident] = {}


_ingested_scenes: list[Scene] = []


def list_scenes() -> list[Scene]:
    """Seeded demo scenes plus anything ingested this session. Ingested
    scenes come first so a freshly uploaded product is easy to find."""
    return list(_ingested_scenes) + list(SCENES)


def get_scene(scene_id: str) -> Scene | None:
    return next((s for s in list_scenes() if s.id == scene_id), None)


def add_scene(scene: Scene) -> None:
    _ingested_scenes.insert(0, scene)


def list_vessels() -> list[VesselProfile]:
    return list(VESSELS)


def get_vessel(mmsi: str) -> VesselProfile | None:
    return next((v for v in VESSELS if v.mmsi == mmsi), None)


def get_ais_track(mmsi: str) -> list[AISPosition]:
    return AIS_TRACKS.get(mmsi, [])


def get_radar_truth(scene_id: str) -> dict | None:
    return RADAR_TRUTH_POSITIONS.get(scene_id)


def save_detection(detection: Detection) -> None:
    _detections[detection.id] = detection


def get_detection(detection_id: str) -> Detection | None:
    return _detections.get(detection_id)


def list_detections() -> list[Detection]:
    return list(_detections.values())


def detections_for_scene(scene_id: str) -> list[Detection]:
    return [d for d in _detections.values() if d.scene_id == scene_id]


def save_incident(incident: Incident) -> None:
    _incidents[incident.id] = incident


def get_incident(incident_id: str) -> Incident | None:
    return _incidents.get(incident_id)


def list_incidents() -> list[Incident]:
    return list(_incidents.values())


def incident_for_detection(detection_id: str) -> Incident | None:
    return next((i for i in _incidents.values() if i.detection_id == detection_id), None)
