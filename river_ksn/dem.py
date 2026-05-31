"""DEM loading and depression filling."""

import numpy as np
import rasterio
import richdem as rd


def load_dem(path: str) -> rd.rdarray:
    """Load a DEM from a GeoTIFF file.

    Args:
        path: Path to the GeoTIFF DEM file.

    Returns:
        RichDEM array with elevation data.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If the file cannot be read as a DEM.
    """
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float64)
        nodata = src.nodata if src.nodata is not None else -9999.0
    return rd.rdarray(data, no_data=nodata)


def fill_dem(dem: rd.rdarray) -> rd.rdarray:
    """Fill sinks/depressions in a DEM.

    Uses Wang & Liu (2006) algorithm via richdem.

    Args:
        dem: RichDEM array of elevation values.

    Returns:
        Filled DEM with same shape as input.
    """
    return rd.FillDepressions(dem, epsilon=True, in_place=False)
