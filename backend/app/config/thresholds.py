"""Physics-gate thresholds. Kept out of code paths so operators can tune them
without touching model or scoring logic."""

WIND_UNRELIABLE_LOW = 1.5     # m/s — glassy water, indistinguishable from oil
WIND_DEGRADED_LOW_MAX = 3.0   # m/s
WIND_OPTIMAL_MAX = 10.0       # m/s
WIND_DEGRADED_HIGH_MAX = 14.0 # m/s — above this, unreliable (wave shadow / emulsification)

DEGRADED_LOW_CONFIDENCE_MULT = 0.5
DEGRADED_HIGH_CONFIDENCE_MULT = 0.6
DEGRADED_LOW_MIN_AREA_M2 = 5000.0

INCIDENCE_ANGLE_MIN = 20.0    # degrees
INCIDENCE_ANGLE_MAX = 45.0
INCIDENCE_DOWNGRADE_MULT = 0.7

RAIN_ARTEFACT_MM_HR = 2.0

# Attribution scoring weights (must sum to 1.0 excluding exclusion penalty)
WEIGHT_SPATIOTEMPORAL = 0.35
WEIGHT_CARGO_COMPAT = 0.30
WEIGHT_DECEPTION_INDEX = 0.15
WEIGHT_BEHAVIOURAL_ANOMALY = 0.15
WEIGHT_EXCLUSION_PENALTY = 0.05

# Truth Gap / spoofing
AIS_MATCH_RADIUS_M = 500.0
DARK_SHIP_RADIUS_M = 2000.0
DARK_SHIP_SILENCE_MINUTES = 60

# Back-tracking
DEFAULT_PARTICLE_COUNT = 5000
DEFAULT_WINDAGE_CRUDE = 0.03
DEFAULT_WINDAGE_HFO = 0.015  # heavier oil sits deeper, less wind-driven
EDDY_DIFFUSIVITY_M2_S = 10.0
DRIFT_CONE_PERCENTILE = 90
