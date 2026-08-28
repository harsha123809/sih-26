"""Seeded demo data: 6 scenes covering the required scenarios, with matching
AIS tracks, vessel profiles, and wind/current fields. All scenes sit along
Indian coastal waters (Arabian Sea / Bay of Bengal shipping lanes) so the map
view centres somewhere geographically coherent.
"""
from __future__ import annotations

from app.models import AISPosition, EnvironmentalConditions, Scene, VesselProfile

# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------

SCENES: list[Scene] = [
    Scene(
        id="scene-01-crude-tanker",
        name="Mumbai High Offshore — Crude Slick Near Laden Tanker",
        description=(
            "A confirmed crude oil slick detected in optimal wind conditions with a "
            "laden crude tanker transiting nearby on a matching AIS track."
        ),
        acquisition_time="2026-08-20T02:14:00Z",
        bbox=[70.6, 18.6, 71.4, 19.2],
        environment=EnvironmentalConditions(
            wind_speed_ms=6.2, wind_dir_deg=250, sea_surface_temp_c=28.4,
            incidence_angle_deg=34.0, wave_height_m=1.1, precipitation_mm_hr=0.0,
            has_polarimetry=True, ocean_current_speed_ms=0.35, ocean_current_dir_deg=200,
        ),
        scenario_tag="crude_tanker",
    ),
    Scene(
        id="scene-02-hfo-container",
        name="Gulf of Kutch — Heavy Fuel Oil Slick, Container Ship in Vicinity",
        description=(
            "A heavy fuel oil slick near a large container ship. No crude tanker is "
            "present — attribution must reason from bunker fuel compatibility, not cargo."
        ),
        acquisition_time="2026-08-21T21:40:00Z",
        bbox=[68.6, 22.1, 69.4, 22.7],
        environment=EnvironmentalConditions(
            wind_speed_ms=5.4, wind_dir_deg=290, sea_surface_temp_c=27.1,
            incidence_angle_deg=31.5, wave_height_m=0.9, precipitation_mm_hr=0.0,
            has_polarimetry=True, ocean_current_speed_ms=0.28, ocean_current_dir_deg=160,
        ),
        scenario_tag="hfo_container",
    ),
    Scene(
        id="scene-03-low-wind-suppressed",
        name="Goa Coastal Waters — Dark Patch Under Glassy Sea Conditions",
        description=(
            "A dark patch that a naive detector would flag as oil. Wind speed is 1.0 m/s: "
            "the Physics Gate must suppress this detection."
        ),
        acquisition_time="2026-08-22T14:05:00Z",
        bbox=[73.0, 15.1, 73.6, 15.6],
        environment=EnvironmentalConditions(
            wind_speed_ms=1.0, wind_dir_deg=210, sea_surface_temp_c=29.0,
            incidence_angle_deg=33.0, wave_height_m=0.2, precipitation_mm_hr=0.0,
            has_polarimetry=True, ocean_current_speed_ms=0.15, ocean_current_dir_deg=190,
        ),
        scenario_tag="low_wind_suppressed",
    ),
    Scene(
        id="scene-04-spoofing",
        name="Kochi Approaches — AIS Spoofing, 40 km Position Gap",
        description=(
            "A crude slick with a physical radar-visible tanker 40 km from where its "
            "AIS transponder claims it to be — a textbook spoofing event."
        ),
        acquisition_time="2026-08-23T19:55:00Z",
        bbox=[75.0, 9.1, 75.9, 9.9],
        environment=EnvironmentalConditions(
            wind_speed_ms=7.1, wind_dir_deg=230, sea_surface_temp_c=28.9,
            incidence_angle_deg=36.0, wave_height_m=1.3, precipitation_mm_hr=0.0,
            has_polarimetry=True, ocean_current_speed_ms=0.4, ocean_current_dir_deg=210,
        ),
        scenario_tag="spoofing",
    ),
    Scene(
        id="scene-05-dark-ship",
        name="Mangalore Offshore — Dark Ship, No AIS Transmission",
        description=(
            "A heavy fuel oil slick with a radar-visible vessel transmitting no AIS "
            "at all — fully dark for over an hour."
        ),
        acquisition_time="2026-08-24T03:22:00Z",
        bbox=[74.1, 12.5, 74.9, 13.1],
        environment=EnvironmentalConditions(
            wind_speed_ms=8.3, wind_dir_deg=260, sea_surface_temp_c=28.0,
            incidence_angle_deg=29.5, wave_height_m=1.6, precipitation_mm_hr=0.4,
            has_polarimetry=True, ocean_current_speed_ms=0.32, ocean_current_dir_deg=175,
        ),
        scenario_tag="dark_ship",
    ),
    Scene(
        id="scene-06-crude-excluded-feeder",
        name="Chennai Shipping Lane — Crude Slick, Nearby Vessel Ruled Out",
        description=(
            "A crude oil slick with only a small container feeder nearby — cargo-aware "
            "attribution must rule it out rather than default-blaming the nearest ship."
        ),
        acquisition_time="2026-08-25T10:12:00Z",
        bbox=[80.1, 12.9, 80.9, 13.5],
        environment=EnvironmentalConditions(
            wind_speed_ms=6.8, wind_dir_deg=100, sea_surface_temp_c=29.6,
            incidence_angle_deg=38.0, wave_height_m=1.0, precipitation_mm_hr=0.0,
            has_polarimetry=True, ocean_current_speed_ms=0.25, ocean_current_dir_deg=140,
        ),
        scenario_tag="crude_excluded_feeder",
    ),
]

# ---------------------------------------------------------------------------
# Vessel profiles (keyed by MMSI)
# ---------------------------------------------------------------------------

VESSELS: list[VesselProfile] = [
    VesselProfile(mmsi="431003001", name="MT Konkan Pride", vessel_type="Crude Oil Tanker",
                   gross_tonnage=85000, bunker_fuel_type="Heavy Fuel Oil", cargo_type="Crude Oil",
                   cargo_capacity_m3=130000, length_m=250),
    VesselProfile(mmsi="412345678", name="MSC Horizon Trader", vessel_type="Container Ship",
                   gross_tonnage=95000, bunker_fuel_type="Heavy Fuel Oil", cargo_type="Containerized Goods",
                   cargo_capacity_m3=None, length_m=300),
    VesselProfile(mmsi="440221100", name="SS Arabian Star", vessel_type="Bulk Carrier",
                   gross_tonnage=42000, bunker_fuel_type="Heavy Fuel Oil", cargo_type="Iron Ore",
                   cargo_capacity_m3=None, length_m=190),
    VesselProfile(mmsi="419876543", name="Global Voyager", vessel_type="Product Tanker",
                   gross_tonnage=38000, bunker_fuel_type="Heavy Fuel Oil", cargo_type="Crude Oil",
                   cargo_capacity_m3=50000, length_m=180),
    VesselProfile(mmsi="419012345", name="Silent Runner", vessel_type="Product Tanker",
                   gross_tonnage=29000, bunker_fuel_type="Heavy Fuel Oil", cargo_type="Heavy Fuel Oil",
                   cargo_capacity_m3=35000, length_m=165),
    VesselProfile(mmsi="477001122", name="Pacific Feeder", vessel_type="Container Feeder",
                   gross_tonnage=12000, bunker_fuel_type="Marine Diesel Oil", cargo_type="Containerized Goods",
                   cargo_capacity_m3=None, length_m=140),
]

# ---------------------------------------------------------------------------
# AIS tracks: a handful of timestamped positions per relevant vessel, close to
# each scene's bbox centre so map/track rendering and overlap scoring have
# realistic geometry to work with.
# ---------------------------------------------------------------------------


def _track(mmsi: str, base_lat: float, base_lon: float, heading: float, speed: float, base_time: str, n: int = 6) -> list[AISPosition]:
    import datetime as dt

    t0 = dt.datetime.fromisoformat(base_time.replace("Z", "+00:00"))
    positions = []
    for i in range(n):
        dt_hours = (i - n // 2) * 0.5
        dlat = (speed * 0.0008) * dt_hours
        dlon = (speed * 0.0008) * dt_hours * 1.1
        positions.append(AISPosition(
            mmsi=mmsi,
            timestamp=(t0 + dt.timedelta(hours=dt_hours)).isoformat().replace("+00:00", "Z"),
            lat=round(base_lat + dlat, 5),
            lon=round(base_lon + dlon, 5),
            speed_knots=round(speed, 1),
            heading_deg=heading,
        ))
    return positions


AIS_TRACKS: dict[str, list[AISPosition]] = {
    "431003001": _track("431003001", 18.95, 71.05, 245, 11.5, "2026-08-20T02:14:00Z"),
    "412345678": _track("412345678", 22.42, 68.95, 300, 16.0, "2026-08-21T21:40:00Z"),
    "440221100": _track("440221100", 15.34, 73.28, 180, 4.0, "2026-08-22T14:05:00Z"),
    # Spoofing: AIS claims a position ~40km from the true radar-detected position.
    "419876543": _track("419876543", 9.55, 75.15, 235, 12.0, "2026-08-23T19:55:00Z"),
    # "419012345" (Silent Runner) intentionally has NO AIS track — it is dark.
    "477001122": _track("477001122", 13.18, 80.62, 95, 14.5, "2026-08-25T10:12:00Z"),
}

# True physical (radar) positions used by the CFAR/truth-gap simulation,
# keyed by scene id. For the spoofing scene this is deliberately far from the
# AIS-claimed track above.
RADAR_TRUTH_POSITIONS: dict[str, dict] = {
    # These four sit well within AIS_MATCH_RADIUS_M (500 m) of the vessel's
    # mid-track AIS position, seeded above — i.e. AIS and radar agree, so the
    # Truth Gap analysis correctly reports MATCHED, not spoofing.
    "scene-01-crude-tanker": {"mmsi": "431003001", "lat": 18.949, "lon": 71.0485, "length_m": 250, "snr_db": 18.2},
    "scene-02-hfo-container": {"mmsi": "412345678", "lat": 22.419, "lon": 68.9485, "length_m": 300, "snr_db": 21.0},
    "scene-03-low-wind-suppressed": {"mmsi": "440221100", "lat": 15.339, "lon": 73.2785, "length_m": 190, "snr_db": 15.4},
    # ~40 km SW of the AIS-claimed 9.55N 75.15E position — the radar-visible
    # hull IS "Global Voyager" (419876543); its transponder is lying about
    # its position, not silent, which is what makes this spoofing rather
    # than a dark ship.
    "scene-04-spoofing": {"mmsi": "419876543", "lat": 9.29, "lon": 74.90, "length_m": 178, "snr_db": 19.6},
    "scene-05-dark-ship": {"mmsi": None, "lat": 12.83, "lon": 74.58, "length_m": 163, "snr_db": 17.1},
    "scene-06-crude-excluded-feeder": {"mmsi": "477001122", "lat": 13.179, "lon": 80.6185, "length_m": 140, "snr_db": 14.8},
}


def get_scene(scene_id: str) -> Scene | None:
    return next((s for s in SCENES if s.id == scene_id), None)


def get_vessel(mmsi: str) -> VesselProfile | None:
    return next((v for v in VESSELS if v.mmsi == mmsi), None)
