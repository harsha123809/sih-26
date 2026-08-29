"""Real Sentinel-1 GRD ingestion.

This is the path that replaces SIMULATION_MODE's seeded fixtures with actual
satellite data. Given a calibrated GRD GeoTIFF (VV, and optionally VH), it:

  * reads the raster decimated (a full GRD scene is ~25000x16000 px — reading
    it at full res to make a 512px thumbnail would be absurd),
  * converts amplitude/DN to sigma0 in dB,
  * computes the VV/VH ratio in linear power, log-scaled — the oil-type
    fingerprint the model's channel 2 expects,
  * derives a WGS84 bbox from the product's own CRS and geotransform,
  * renders a contrast-stretched PNG thumbnail for the evidence panel.

What this does NOT do is classify. That still needs trained weights (see
core/ml/infer.py). Real imagery gives real geometry, real geolocation and a
real VV/VH ratio; the oil-type call remains unavailable until the model is
trained, and the API reports it as such rather than guessing.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# Maximum edge length for the generated thumbnail, in pixels.
THUMBNAIL_MAX_EDGE = 768

# Percentile clip used to stretch SAR backscatter for display. Raw sigma0 has
# a long bright tail (ships, corner reflectors) that would otherwise crush all
# the ocean texture into a single dark value.
DISPLAY_CLIP_PERCENTILES = (2.0, 98.0)


@dataclass
class SarScene:
    """A real SAR product, loaded and preprocessed."""

    source_path: str
    width: int
    height: int
    bbox: list[float]  # [west, south, east, north] in WGS84
    crs: str
    has_polarimetry: bool
    vv_db: np.ndarray
    vh_db: np.ndarray | None = None
    ratio_db: np.ndarray | None = None
    stats: dict = field(default_factory=dict)


def _to_db(power: np.ndarray) -> np.ndarray:
    """Linear power -> dB, guarding the log against zeros/negatives."""
    return 10.0 * np.log10(np.clip(power, 1e-12, None))


def _dn_to_sigma0_db(dn: np.ndarray) -> np.ndarray:
    """Digital numbers -> sigma0 dB.

    A GRD product's DN relates to backscatter as sigma0 = DN^2 / A^2, where A
    comes from the product's calibration LUT. When a caller has already
    applied calibration (SNAP, pyroSAR, etc. — the common case for anything
    analysis-ready), values arrive as linear sigma0 or already in dB, so we
    detect that rather than blindly squaring.
    """
    finite = dn[np.isfinite(dn)]
    if finite.size == 0:
        return np.zeros_like(dn, dtype=np.float32)

    lo, hi = np.percentile(finite, [1, 99])

    # Already in dB: SAR backscatter over water sits roughly -35..0 dB, so a
    # meaningful share of negative values is the giveaway.
    if lo < -1.0 and hi < 30.0:
        return dn.astype(np.float32)

    # Linear sigma0 (roughly 0..1) rather than raw DN (typically 0..~10^3+).
    if hi <= 5.0:
        return _to_db(dn).astype(np.float32)

    # Raw DN: square it. Without the product's calibration LUT this is
    # uncalibrated, so it is fine for relative structure and display but the
    # absolute level is not physically meaningful.
    return _to_db(dn.astype(np.float64) ** 2).astype(np.float32)


def _decimated_shape(width: int, height: int, max_edge: int) -> tuple[int, int]:
    if max(width, height) <= max_edge:
        return height, width
    scale = max_edge / float(max(width, height))
    return max(int(height * scale), 1), max(int(width * scale), 1)


def _read_band(path: str | Path, max_edge: int) -> tuple[np.ndarray, dict]:
    """Read band 1 of a raster, decimated to at most `max_edge` on its long
    side, along with the metadata needed to geolocate it."""
    import rasterio
    from rasterio.warp import transform_bounds

    with rasterio.open(str(path)) as src:
        out_h, out_w = _decimated_shape(src.width, src.height, max_edge)
        data = src.read(1, out_shape=(out_h, out_w), masked=True)
        arr = np.ma.filled(data.astype(np.float64), np.nan)

        if src.crs is not None:
            west, south, east, north = transform_bounds(
                src.crs, "EPSG:4326", *src.bounds, densify_pts=21
            )
            crs_name = str(src.crs)
        else:
            # Ungeoreferenced product — the caller has to supply a bbox.
            west = south = east = north = float("nan")
            crs_name = "UNKNOWN"

        meta = {
            "full_width": src.width,
            "full_height": src.height,
            "read_width": out_w,
            "read_height": out_h,
            "bbox": [west, south, east, north],
            "crs": crs_name,
        }
    return arr, meta


def load_sar_scene(
    vv_path: str | Path,
    vh_path: str | Path | None = None,
    max_edge: int = 2048,
    apply_speckle_filter: bool = True,
) -> SarScene:
    """Load a Sentinel-1 GRD product into the form the model expects.

    `vh_path` is optional on purpose: single-polarisation products exist, and
    without VH there is no VV/VH ratio, so oil TYPE cannot be resolved. That
    propagates through as has_polarimetry=False rather than being papered over.
    """
    vv_raw, meta = _read_band(vv_path, max_edge)
    vv_db = _dn_to_sigma0_db(vv_raw)

    vh_db = None
    ratio_db = None
    if vh_path is not None:
        vh_raw, vh_meta = _read_band(vh_path, max_edge)
        if vh_raw.shape != vv_raw.shape:
            raise ValueError(
                f"VV and VH rasters have different shapes after decimation "
                f"({vv_raw.shape} vs {vh_raw.shape}). They must come from the "
                f"same product and grid."
            )
        vh_db = _dn_to_sigma0_db(vh_raw)

    if apply_speckle_filter:
        from app.core.ml.preprocessing import lee_filter_fast

        vv_db = _filter_preserving_nan(vv_db, lee_filter_fast)
        if vh_db is not None:
            vh_db = _filter_preserving_nan(vh_db, lee_filter_fast)

    if vh_db is not None:
        from app.core.ml.preprocessing import compute_vv_vh_ratio_db

        ratio_db = compute_vv_vh_ratio_db(vv_db, vh_db)

    stats = {
        "vv_db": _band_stats(vv_db),
        "vh_db": _band_stats(vh_db) if vh_db is not None else None,
        "ratio_db": _band_stats(ratio_db) if ratio_db is not None else None,
    }

    return SarScene(
        source_path=str(vv_path),
        width=meta["read_width"],
        height=meta["read_height"],
        bbox=meta["bbox"],
        crs=meta["crs"],
        has_polarimetry=vh_db is not None,
        vv_db=vv_db,
        vh_db=vh_db,
        ratio_db=ratio_db,
        stats=stats,
    )


def _filter_preserving_nan(arr: np.ndarray, fn) -> np.ndarray:
    """Speckle filters do not understand NaN (GRD products have no-data
    borders). Fill with the band mean, filter, then restore the NaNs so the
    border does not bleed a fabricated value into the image."""
    mask = ~np.isfinite(arr)
    if not mask.any():
        return fn(arr)
    fill = float(np.nanmean(arr)) if np.isfinite(arr).any() else 0.0
    filled = np.where(mask, fill, arr)
    out = fn(filled)
    out[mask] = np.nan
    return out


def _band_stats(arr: np.ndarray | None) -> dict | None:
    if arr is None:
        return None
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None
    p2, p50, p98 = np.percentile(finite, [2, 50, 98])
    return {
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
        "p2": float(p2),
        "median": float(p50),
        "p98": float(p98),
    }


def render_thumbnail(
    scene: SarScene,
    out_path: str | Path,
    max_edge: int = THUMBNAIL_MAX_EDGE,
) -> str:
    """Write a contrast-stretched PNG of the VV channel.

    This is a visualisation of real measured backscatter — a stretch applied
    for human legibility, not synthesised imagery.
    """
    from PIL import Image

    arr = scene.vv_db
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        raise ValueError("VV band contains no finite values; cannot render a thumbnail.")

    lo, hi = np.percentile(finite, DISPLAY_CLIP_PERCENTILES)
    if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
        lo, hi = float(np.min(finite)), float(np.max(finite))
    if hi <= lo:
        hi = lo + 1.0

    norm = (arr - lo) / (hi - lo)
    norm = np.clip(norm, 0.0, 1.0)
    # No-data becomes black rather than an arbitrary grey.
    norm = np.where(np.isfinite(norm), norm, 0.0)

    img = Image.fromarray((norm * 255).astype(np.uint8), mode="L")

    if max(img.size) > max_edge:
        scale = max_edge / float(max(img.size))
        img = img.resize(
            (max(int(img.width * scale), 1), max(int(img.height * scale), 1)),
            Image.LANCZOS,
        )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return str(out_path)


def build_model_input(scene: SarScene, wind_speed_ms: float) -> np.ndarray:
    """Assemble the 4-channel tensor the Env-Attention U-Net expects:
    [sigma0_VV_dB, sigma0_VH_dB, VV/VH_ratio_dB, wind_speed_map].

    When VH is absent, channels 1 and 2 are filled with a sentinel value and
    has_polarimetry is False, so downstream code reports oil type as
    UNRESOLVED instead of inventing a cross-pol signal that was never measured.
    """
    from app.core.ml.model import VH_SENTINEL_VALUE

    vv = np.nan_to_num(scene.vv_db, nan=0.0)
    if scene.has_polarimetry and scene.vh_db is not None and scene.ratio_db is not None:
        vh = np.nan_to_num(scene.vh_db, nan=0.0)
        ratio = np.nan_to_num(scene.ratio_db, nan=0.0)
    else:
        vh = np.full_like(vv, VH_SENTINEL_VALUE)
        ratio = np.full_like(vv, VH_SENTINEL_VALUE)

    wind = np.full_like(vv, float(wind_speed_ms))
    return np.stack([vv, vh, ratio, wind], axis=0).astype(np.float32)
