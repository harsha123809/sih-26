"""SAR preprocessing utilities: speckle filtering, sigma0 calibration,
incidence-angle normalisation, and tiling with overlap/stitching.

These operate on real numpy arrays and are fully functional independent of
whether the model is running in SIMULATION_MODE — they are exercised by unit
tests and are what would run against real Sentinel-1 GRD products.
"""
from __future__ import annotations

import numpy as np


def lee_filter(img: np.ndarray, window: int = 7) -> np.ndarray:
    """Lee speckle filter: adaptive smoothing based on local statistics.
    Preserves edges better than a plain mean filter by weighting the local
    mean against the pixel value according to local coefficient of variation.
    """
    img = img.astype(np.float64)
    pad = window // 2
    padded = np.pad(img, pad, mode="reflect")
    out = np.empty_like(img)
    overall_var = float(np.var(img))
    for i in range(img.shape[0]):
        for j in range(img.shape[1]):
            patch = padded[i:i + window, j:j + window]
            local_mean = patch.mean()
            local_var = patch.var()
            if overall_var <= 1e-9:
                weight = 0.0
            else:
                weight = local_var / (local_var + overall_var)
            out[i, j] = local_mean + weight * (img[i, j] - local_mean)
    return out


def lee_filter_fast(img: np.ndarray, window: int = 7) -> np.ndarray:
    """Vectorised Lee filter using uniform_filter for local stats (production path)."""
    from scipy.ndimage import uniform_filter

    img = img.astype(np.float64)
    mean = uniform_filter(img, size=window)
    sq_mean = uniform_filter(img * img, size=window)
    local_var = np.clip(sq_mean - mean * mean, 0, None)
    overall_var = float(np.var(img))
    weight = local_var / (local_var + overall_var + 1e-9)
    return mean + weight * (img - mean)


def frost_filter(img: np.ndarray, window: int = 7, damping: float = 2.0) -> np.ndarray:
    """Frost filter: exponentially weighted local convolution, weight increases
    with local variance so heterogeneous (edge) regions stay sharp."""
    img = img.astype(np.float64)
    pad = window // 2
    padded = np.pad(img, pad, mode="reflect")
    out = np.empty_like(img)
    yy, xx = np.mgrid[-pad:pad + 1, -pad:pad + 1]
    dist = np.sqrt(xx ** 2 + yy ** 2)
    for i in range(img.shape[0]):
        for j in range(img.shape[1]):
            patch = padded[i:i + window, j:j + window]
            local_mean = patch.mean()
            local_var = patch.var()
            cv2 = local_var / (local_mean ** 2 + 1e-9)
            kernel = np.exp(-damping * cv2 * dist)
            kernel /= kernel.sum()
            out[i, j] = (kernel * patch).sum()
    return out


def calibrate_sigma0(dn: np.ndarray, calibration_lut: np.ndarray) -> np.ndarray:
    """Convert digital numbers to calibrated sigma0 in dB using a per-pixel
    calibration LUT (as provided in Sentinel-1 annotation XML)."""
    power = (dn.astype(np.float64) ** 2) / (calibration_lut ** 2 + 1e-9)
    return 10.0 * np.log10(np.clip(power, 1e-12, None))


def normalise_incidence_angle(sigma0_db: np.ndarray, incidence_deg: np.ndarray, reference_deg: float = 30.0) -> np.ndarray:
    """Gamma-nought style incidence angle normalisation so backscatter is
    comparable across the swath."""
    theta = np.radians(incidence_deg)
    ref = np.radians(reference_deg)
    correction_db = 10.0 * np.log10(np.clip(np.sin(theta) / np.sin(ref), 1e-6, None))
    return sigma0_db - correction_db


def compute_vv_vh_ratio_db(vv_db: np.ndarray, vh_db: np.ndarray) -> np.ndarray:
    """Compute VV/VH ratio in linear power space, then log-scale — the
    oil-type fingerprint channel."""
    vv_lin = 10 ** (vv_db / 10.0)
    vh_lin = 10 ** (vh_db / 10.0)
    ratio_lin = vv_lin / np.clip(vh_lin, 1e-9, None)
    return 10.0 * np.log10(np.clip(ratio_lin, 1e-9, None))


def tile_with_overlap(img: np.ndarray, tile_size: int = 512, overlap: int = 64) -> list[tuple[np.ndarray, tuple[int, int]]]:
    """Split a large scene into overlapping tiles for inference."""
    h, w = img.shape[-2:]
    stride = tile_size - overlap
    tiles = []
    for y in range(0, max(h - tile_size, 0) + 1, stride):
        for x in range(0, max(w - tile_size, 0) + 1, stride):
            tile = img[..., y:y + tile_size, x:x + tile_size]
            tiles.append((tile, (y, x)))
    return tiles


def stitch_tiles(tiles: list[tuple[np.ndarray, tuple[int, int]]], out_shape: tuple[int, ...], tile_size: int = 512, overlap: int = 64) -> np.ndarray:
    """Stitch overlapping tile predictions back together, averaging in the
    overlap regions (feathered blend)."""
    accum = np.zeros(out_shape, dtype=np.float64)
    weight = np.zeros(out_shape[-2:], dtype=np.float64)
    ramp = np.ones(tile_size)
    if overlap > 0:
        edge = np.linspace(0, 1, overlap)
        ramp[:overlap] = edge
        ramp[-overlap:] = edge[::-1]
    tile_weight = np.outer(ramp, ramp)

    for tile, (y, x) in tiles:
        th, tw = tile.shape[-2:]
        accum[..., y:y + th, x:x + tw] += tile * tile_weight[:th, :tw]
        weight[y:y + th, x:x + tw] += tile_weight[:th, :tw]

    weight = np.clip(weight, 1e-9, None)
    return accum / weight
