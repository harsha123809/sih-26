"""Lagrangian back-tracking: seed particles inside the detected slick and
integrate backwards in time to estimate the release origin.

dx/dt = -(ocean_current + windage * wind_10m) + turbulent_diffusion

Run backwards (negative time step) because we are reconstructing where the
slick CAME FROM, not where it is going. The particle cloud spreads with each
step back — that widening IS the uncertainty and is surfaced as the growing
drift-cone radius, not smoothed away.
"""
from __future__ import annotations

import datetime as dt
import math
import random

from app.config import thresholds as t
from app.models import DriftConeFrame, EnvironmentalConditions, GeoJSONGeometry, OilClass

EARTH_RADIUS_M = 6_371_000.0


def _meters_to_deg(dy_m: float, dx_m: float, lat_deg: float) -> tuple[float, float]:
    dlat = dy_m / EARTH_RADIUS_M * (180 / math.pi)
    dlon = dx_m / (EARTH_RADIUS_M * math.cos(math.radians(lat_deg))) * (180 / math.pi)
    return dlat, dlon


def _velocity_field(env: EnvironmentalConditions, windage: float) -> tuple[float, float]:
    """Combined drift velocity (m/s, m/s) in (north, east) components."""
    cur_rad = math.radians(env.ocean_current_dir_deg)
    cur_n = env.ocean_current_speed_ms * math.cos(cur_rad)
    cur_e = env.ocean_current_speed_ms * math.sin(cur_rad)

    wind_rad = math.radians(env.wind_dir_deg)
    wind_n = env.wind_speed_ms * math.cos(wind_rad) * windage
    wind_e = env.wind_speed_ms * math.sin(wind_rad) * windage

    return cur_n + wind_n, cur_e + wind_e


def _rk4_step(lat: float, lon: float, vn: float, ve: float, dt_s: float) -> tuple[float, float]:
    """Single RK4 step for a (locally) constant velocity field. With a
    spatially-uniform field RK4 reduces to Euler, but the structure is kept
    so a spatially-varying current field can be substituted without touching
    the integration loop."""
    def deriv(_lat, _lon):
        return vn, ve

    k1n, k1e = deriv(lat, lon)
    k2n, k2e = deriv(lat, lon)
    k3n, k3e = deriv(lat, lon)
    k4n, k4e = deriv(lat, lon)

    avg_n = (k1n + 2 * k2n + 2 * k3n + k4n) / 6
    avg_e = (k1e + 2 * k2e + 2 * k3e + k4e) / 6

    dlat, dlon = _meters_to_deg(avg_n * dt_s, avg_e * dt_s, lat)
    return lat + dlat, lon + dlon


def _polygon_from_particles(points: list[tuple[float, float]], percentile: int) -> tuple[GeoJSONGeometry, float]:
    """Approximate a density contour with a convex-hull-like envelope scaled
    to the given percentile of particle distances from the centroid (a cheap
    stand-in for a true KDE contour, adequate for visualization)."""
    lat_c = sum(p[0] for p in points) / len(points)
    lon_c = sum(p[1] for p in points) / len(points)

    dists = sorted(
        math.hypot((p[0] - lat_c) * 111_320, (p[1] - lon_c) * 111_320 * math.cos(math.radians(lat_c)))
        for p in points
    )
    idx = min(int(len(dists) * percentile / 100), len(dists) - 1)
    radius_m = max(dists[idx], 50.0)

    n_pts = 24
    ring = []
    for i in range(n_pts):
        angle = 2 * math.pi * i / n_pts
        dlat, dlon = _meters_to_deg(radius_m * math.cos(angle), radius_m * math.sin(angle), lat_c)
        ring.append([lon_c + dlon, lat_c + dlat])
    ring.append(ring[0])

    return GeoJSONGeometry(type="Polygon", coordinates=[ring]), radius_m


def run_backtrack(
    centroid_lonlat: list[float],
    env: EnvironmentalConditions,
    predicted_class: OilClass,
    hours: int = 72,
    particle_count: int = t.DEFAULT_PARTICLE_COUNT,
    frame_interval_hours: float = 6.0,
    acquisition_time: str | None = None,
    seed: int | None = None,
) -> tuple[list[DriftConeFrame], list[float]]:
    windage = t.DEFAULT_WINDAGE_HFO if predicted_class == OilClass.HEAVY_FUEL_OIL else t.DEFAULT_WINDAGE_CRUDE
    vn, ve = _velocity_field(env, windage)
    # Backwards in time: reverse the advective velocity.
    vn, ve = -vn, -ve

    rng = random.Random(seed if seed is not None else 42)
    lon0, lat0 = centroid_lonlat
    particles = [(lat0, lon0) for _ in range(min(particle_count, 5000))]

    total_seconds = hours * 3600
    frame_seconds = frame_interval_hours * 3600
    n_frames = max(int(total_seconds / frame_seconds), 1)

    base_time = dt.datetime.fromisoformat((acquisition_time or dt.datetime.utcnow().isoformat() + "Z").replace("Z", "+00:00"))

    frames: list[DriftConeFrame] = []
    for frame_idx in range(1, n_frames + 1):
        elapsed_s = frame_idx * frame_seconds
        new_particles = []
        for lat, lon in particles:
            lat2, lon2 = _rk4_step(lat, lon, vn, ve, frame_seconds)
            # Turbulent diffusion: random-walk term, std dev grows with sqrt(time)
            sigma_m = math.sqrt(2 * t.EDDY_DIFFUSIVITY_M2_S * frame_seconds)
            dn = rng.gauss(0, sigma_m)
            de = rng.gauss(0, sigma_m)
            dlat, dlon = _meters_to_deg(dn, de, lat2)
            new_particles.append((lat2 + dlat, lon2 + dlon))
        particles = new_particles

        polygon, radius_m = _polygon_from_particles(particles, t.DRIFT_CONE_PERCENTILE)
        frame_time = base_time - dt.timedelta(seconds=elapsed_s)
        frames.append(DriftConeFrame(
            hours_back=round(elapsed_s / 3600, 1),
            timestamp=frame_time.isoformat().replace("+00:00", "Z"),
            polygon=polygon,
            particle_spread_m=round(radius_m, 1),
        ))

    lat_c = sum(p[0] for p in particles) / len(particles)
    lon_c = sum(p[1] for p in particles) / len(particles)
    origin_estimate = [round(lon_c, 5), round(lat_c, 5)]

    return frames, origin_estimate
