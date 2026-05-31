"""Export results to GeoTIFF and CSV."""

import csv

import numpy as np
import rasterio


def export_geotiff(
    array: np.ndarray,
    input_path: str,
    output_path: str,
    nodata: float = -9999.0,
) -> None:
    """Export a 2D array as a GeoTIFF.

    Inherits CRS, transform, and dimensions from the input DEM.

    Args:
        array: 2D array of values (NaN will be replaced with nodata).
        input_path: Path to the reference DEM for geospatial metadata.
        output_path: Path where the GeoTIFF will be written.
        nodata: Value to use for NaN/no-data cells.
    """
    with rasterio.open(input_path) as src:
        profile = src.profile.copy()

    profile.update(dtype="float32", nodata=nodata)
    out = np.where(np.isnan(array), nodata, array).astype("float32")

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(out, 1)


def export_csv(
    area: np.ndarray,
    slope: np.ndarray,
    ksn: np.ndarray,
    channel_mask: np.ndarray,
    output_path: str,
) -> None:
    """Export channel cell data as CSV.

    Args:
        area: Drainage area array.
        slope: Slope array.
        ksn: KSN array.
        channel_mask: Boolean mask of channel cells.
        output_path: Path where the CSV will be written.
    """
    rows, cols = np.where(channel_mask)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row", "col", "drainage_area", "slope", "ksn"])
        for r, c in zip(rows, cols):
            writer.writerow([r, c, area[r, c], slope[r, c], ksn[r, c]])
