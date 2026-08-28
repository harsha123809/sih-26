export type OilClass =
  | "open_water"
  | "crude_oil"
  | "heavy_fuel_oil"
  | "look_alike"
  | "ship"
  | "land"
  | "unresolved";

export type ReliabilityVerdict =
  | "UNRELIABLE_LOW_WIND"
  | "DEGRADED_LOW"
  | "OPTIMAL"
  | "DEGRADED_HIGH"
  | "UNRELIABLE_HIGH_WIND";

export type VesselMatchStatus = "MATCHED" | "DARK_SHIP" | "SPOOFING_SUSPECTED";

export interface GeoJSONGeometry {
  type: string;
  coordinates: unknown;
}

export interface EnvironmentalConditions {
  wind_speed_ms: number;
  wind_dir_deg: number;
  sea_surface_temp_c: number;
  incidence_angle_deg: number;
  wave_height_m: number;
  precipitation_mm_hr: number;
  has_polarimetry: boolean;
  ocean_current_speed_ms: number;
  ocean_current_dir_deg: number;
}

export interface ReliabilityBlock {
  verdict: ReliabilityVerdict;
  reason: string;
  confidence_multiplier: number;
  suppressed: boolean;
  possible_rain_artefact: boolean;
}

export interface ClassProbabilities {
  open_water: number;
  crude_oil: number;
  heavy_fuel_oil: number;
  look_alike: number;
  ship: number;
  land: number;
}

export interface Scene {
  id: string;
  name: string;
  description: string;
  acquisition_time: string;
  bbox: [number, number, number, number];
  thumbnail_url: string | null;
  environment: EnvironmentalConditions;
  scenario_tag: string;
}

export interface VesselProfile {
  mmsi: string;
  name: string;
  vessel_type: string;
  gross_tonnage: number;
  bunker_fuel_type: string;
  cargo_type: string | null;
  cargo_capacity_m3: number | null;
  length_m: number;
}

export interface AISPosition {
  mmsi: string;
  timestamp: string;
  lat: number;
  lon: number;
  speed_knots: number;
  heading_deg: number;
}

export interface RadarTarget {
  id: string;
  lat: number;
  lon: number;
  estimated_length_m: number;
  snr_db: number;
}

export interface VesselTruthGapResult {
  radar_target: RadarTarget | null;
  claimed_ais: AISPosition | null;
  vessel_profile: VesselProfile | null;
  status: VesselMatchStatus;
  deception_index_m: number;
}

export interface Detection {
  id: string;
  scene_id: string;
  predicted_class: OilClass;
  class_probabilities: ClassProbabilities;
  area_m2: number;
  centroid: [number, number];
  polygon: GeoJSONGeometry;
  reliability: ReliabilityBlock;
  has_polarimetry: boolean;
  vv_vh_ratio_db: number;
  simulation_mode: boolean;
  timestamp: string;
}

export interface DriftConeFrame {
  hours_back: number;
  timestamp: string;
  polygon: GeoJSONGeometry;
  particle_spread_m: number;
}

export interface BacktrackResult {
  incident_id: string;
  hours_traced: number;
  particle_count: number;
  frames: DriftConeFrame[];
  origin_estimate: [number, number];
}

export interface AttributionCandidate {
  vessel: VesselProfile;
  spatiotemporal_overlap: number;
  cargo_compatibility: number;
  normalised_deception_index: number;
  behavioural_anomaly: number;
  exclusion_penalty: number;
  score: number;
  excluded: boolean;
  exclusion_reason: string | null;
  reasoning: string[];
}

export interface Incident {
  id: string;
  scene_id: string;
  detection_id: string;
  status: "OPEN" | "CONFIRMED" | "FALSE_POSITIVE";
  created_at: string;
  backtrack: BacktrackResult | null;
  candidates: AttributionCandidate[];
  truth_gap_results: VesselTruthGapResult[];
}

export interface AttributionResponse {
  candidates: AttributionCandidate[];
  truth_gap_results: VesselTruthGapResult[];
}
