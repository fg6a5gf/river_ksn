"""End-to-end integration tests for the ksn pipeline."""

import csv
import os

import numpy as np
import rasterio
from river_ksn.pipeline import run_pipeline


def test_pipeline_synthetic_dem(tmp_path):
    """Run full pipeline on a synthetic DEM, verify output files exist and are valid."""
    output_dir = tmp_path / "output"
    size = 50
    dem_path = tmp_path / "dem.tif"

    xs = np.arange(size, dtype=np.float64).reshape(1, -1)
    ys = np.arange(size, dtype=np.float64).reshape(-1, 1)
    center = size / 2.0
    dist = np.sqrt((xs - center) ** 2 + (ys - center) ** 2)

    slope_x = (xs - center) * 2.0
    slope_y = (ys - center) * 2.0

    dem = 100.0 + slope_x + slope_y + dist * 0.5
    dem = dem.astype(np.float32)

    with rasterio.open(
        str(dem_path),
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=rasterio.transform.from_origin(0, 0, 30, 30),
    ) as dst:
        dst.write(dem, 1)

    run_pipeline(
        input_path=str(dem_path),
        output_dir=str(output_dir),
        theta=0.45,
        threshold=5,
        intermediate=True,
    )

    stem = "dem"
    for suffix in ["_ksn.tif", "_ksn.csv", "_filled.tif", "_accum.tif", "_slope.tif"]:
        path = output_dir / f"{stem}{suffix}"
        assert path.exists(), f"Missing: {path}"

    with rasterio.open(str(output_dir / "dem_ksn.tif")) as src:
        ksn_data = src.read(1)
        assert ksn_data.shape == (size, size)
        assert src.crs == "EPSG:4326"
        valid = ksn_data[ksn_data != src.nodata]
        assert len(valid) > 0, "No valid ksn values"

    with open(output_dir / "dem_ksn.csv", "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) > 0
        assert "ksn" in reader.fieldnames
        for row in rows:
            assert float(row["ksn"]) > 0, f"ksn should be positive, got {row['ksn']}"
