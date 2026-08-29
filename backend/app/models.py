"""Pydantic data models shared across the API."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class OilClass(str, Enum):
    OPEN_WATER = "open_water"
    CRUDE_OIL = "crude_oil"
    HEAVY_FUEL_OIL = "heavy_fuel_oil"
    LOOK_ALIKE = "look_alike"
    SHIP = "ship"
    LAND = "land"
    UNRESOLVED = "unresolved"


class ReliabilityVerdict(str, Enum):
    UNRELIABLE_LOW_WIND = "UNRELIABLE_LOW_WIND"
    DEGRADED_LOW = "DEGRADED_LOW"
    OPTIMAL = "OPTIMAL"
    DEGRADED_HIGH = "DEGRADED_HIGH"
    UNRELIABLE_HIGH_WIND = "UNRELIABLE_HIGH_WIND"


class VesselMatchStatus(str, Enum):
    MATCHED = "MATCHED"
    DARK_SHIP = "DARK_SHIP"
    SPOOFING_SUSPECTED = "SPOOFING_SUSPECTED"


class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any


class EnvironmentalConditions(BaseModel):
    wind_speed_ms: float
    wind_dir_deg: float
    sea_surface_temp_c: float
    incidence_angle_deg: float
    wave_height_m: float
    precipitation_mm_hr: float = 0.0
    has_polarimetry: bool = True
    ocean_current_speed_ms: float = 0.3
    ocean_current_dir_deg: float = 180.0


class ReliabilityBlock(BaseModel):
    verdict: ReliabilityVerdict
    reason: str
    confidence_multiplier: float
    suppressed: bool
    possible_rain_artefact: bool = False


class ClassProbabilities(BaseModel):
    open_water: float = 0.0
    crude_oil: float = 0.0
    heavy_fuel_oil: float = 0.0
    look_alike: float = 0.0
    ship: float = 0.0
    land: float = 0.0


class Scene(BaseModel):
    id: str
    name: str
    description: str
    acquisition_time: str
    bbox: list[float]  # [west, south, east, north]
    thumbnail_url: Optional[str] = None
    environment: EnvironmentalConditions
    scenario_tag: str
    # True when this scene came from an actual ingested SAR product rather
    # than the seeded demo fixtures. Real scenes have genuine geometry and
    # measured backscatter, but classification still requires trained weights
    # — so they report UNRESOLVED rather than a scripted answer.
    is_real_sar: bool = False
    sar_stats: Optional[dict] = None
    source_files: list[str] = Field(default_factory=list)


class VesselProfile(BaseModel):
    mmsi: str
    name: str
    vessel_type: str
    gross_tonnage: float
    bunker_fuel_type: str
    cargo_type: Optional[str] = None
    cargo_capacity_m3: Optional[float] = None
    length_m: float


class AISPosition(BaseModel):
    mmsi: str
    timestamp: str
    lat: float
    lon: float
    speed_knots: float
    heading_deg: float


class RadarTarget(BaseModel):
    id: str
    lat: float
    lon: float
    estimated_length_m: float
    snr_db: float


class VesselTruthGapResult(BaseModel):
    radar_target: Optional[RadarTarget]
    claimed_ais: Optional[AISPosition]
    vessel_profile: Optional[VesselProfile]
    status: VesselMatchStatus
    deception_index_m: float = 0.0


class Detection(BaseModel):
    id: str
    scene_id: str
    predicted_class: OilClass
    class_probabilities: ClassProbabilities
    area_m2: float
    centroid: list[float]  # [lon, lat]
    polygon: GeoJSONGeometry
    reliability: ReliabilityBlock
    has_polarimetry: bool
    vv_vh_ratio_db: float
    simulation_mode: bool = True
    timestamp: str
    # False on real ingested SAR, where no trained model exists to classify
    # with. The UI surfaces classification_note verbatim in that case instead
    # of rendering meaningless probability bars.
    classification_available: bool = True
    classification_note: Optional[str] = None


class DriftConeFrame(BaseModel):
    hours_back: float
    timestamp: str
    polygon: GeoJSONGeometry
    particle_spread_m: float


class BacktrackResult(BaseModel):
    incident_id: str
    hours_traced: int
    particle_count: int
    frames: list[DriftConeFrame]
    origin_estimate: list[float]  # [lon, lat]


class AttributionCandidate(BaseModel):
    vessel: VesselProfile
    spatiotemporal_overlap: float
    cargo_compatibility: float
    normalised_deception_index: float
    behavioural_anomaly: float
    exclusion_penalty: float
    score: float
    excluded: bool
    exclusion_reason: Optional[str] = None
    reasoning: list[str]


class Incident(BaseModel):
    id: str
    scene_id: str
    detection_id: str
    status: str = "OPEN"  # OPEN, CONFIRMED, FALSE_POSITIVE
    created_at: str
    backtrack: Optional[BacktrackResult] = None
    candidates: list[AttributionCandidate] = Field(default_factory=list)
    truth_gap_results: list[VesselTruthGapResult] = Field(default_factory=list)
