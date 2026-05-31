"""End-to-end pipeline orchestration for ksn calculation."""

import logging
import os
import sys

import numpy as np
import richdem as rd

from river_ksn.channel import auto_threshold, extract_channels
from river_ksn.dem import fill_dem, load_dem
from river_ksn.export import export_csv, export_geotiff
from river_ksn.hydrology import compute_flow_accumulation
from river_ksn.ksn import calibrate_theta, compute_ksn, compute_slope

logger = logging.getLogger(__name__)

DEFAULT_THETA = 0.45


def _to_array(arr):
    """Convert rdarray or ndarray to plain numpy array."""
    if isinstance(arr, np.ndarray):
        return arr
    if isinstance(arr, rd.rdarray):
        return np.asarray(arr, dtype=np.float64)
    return np.asarray(arr, dtype=np.float64)


def run_pipeline(
    input_path: str,
    output_dir: str = "./output",
    theta: float | None = None,
    threshold: float | None = None,
    intermediate: bool = False,
) -> None:
    """Run the full ksn calculation pipeline."""
    if not os.path.isfile(input_path):
        logger.error("DEM file not found: %s", input_path)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(input_path))[0]

    # 1. Load
    logger.info("Loading DEM: %s", input_path)
    dem = load_dem(input_path)

    # 2. Fill
    logger.info("Filling depressions...")
    dem_filled = fill_dem(dem)
    if intermediate:
        fp = os.path.join(output_dir, f"{stem}_filled.tif")
        export_geotiff(_to_array(dem_filled), input_path, fp)

    # 3. Flow accumulation
    logger.info("Computing D-infinity flow accumulation...")
    flow_accum = compute_flow_accumulation(dem_filled)
    fa = _to_array(flow_accum)
    logger.info("Flow accum range: %.0f - %.0f", fa.min(), fa.max())
    if intermediate:
        export_geotiff(fa, input_path, os.path.join(output_dir, f"{stem}_accum.tif"))

    # 4. Channel extraction
    if threshold is None:
        threshold = auto_threshold(fa)
        logger.info("Auto threshold: %.1f cells", threshold)
    else:
        logger.info("User threshold: %.1f cells", threshold)

    channel_mask = extract_channels(fa, threshold)
    n_channels = int(np.sum(channel_mask))
    logger.info("Channel cells: %d", n_channels)
    if n_channels == 0:
        logger.error(
            "No channel cells found with threshold %.0f. "
            "Try a lower --threshold value.",
            threshold,
        )
        sys.exit(1)

    # 5. Slope
    logger.info("Computing slope...")
    slope = compute_slope(dem_filled)
    sl = _to_array(slope)
    if intermediate:
        export_geotiff(sl, input_path, os.path.join(output_dir, f"{stem}_slope.tif"))

    # 6. Calibrate theta
    if theta is None:
        theta_fit, r2 = calibrate_theta(fa, sl, channel_mask)
        logger.info("Calibrated theta: %.4f (R²=%.4f)", theta_fit, r2)
        if r2 < 0.3:
            logger.warning(
                "R²=%.4f is low (< 0.3). Falling back to default theta=%.2f",
                r2,
                DEFAULT_THETA,
            )
            theta_ref = DEFAULT_THETA
        else:
            theta_ref = theta_fit
    else:
        theta_ref = theta
        logger.info("Using user-specified theta: %.4f", theta_ref)

    # 7. Compute ksn
    logger.info("Computing ksn (theta_ref=%.4f)...", theta_ref)
    ksn = compute_ksn(sl, fa, theta_ref, channel_mask)

    # 8. Export
    tif_path = os.path.join(output_dir, f"{stem}_ksn.tif")
    csv_path = os.path.join(output_dir, f"{stem}_ksn.csv")
    logger.info("Exporting ksn GeoTIFF: %s", tif_path)
    export_geotiff(ksn, input_path, tif_path)
    logger.info("Exporting ksn CSV: %s", csv_path)
    export_csv(fa, sl, ksn, channel_mask, csv_path)
    logger.info("Done.")
