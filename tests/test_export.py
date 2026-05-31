import csv

import numpy as np
from river_ksn.export import export_csv, export_geotiff


def test_export_geotiff_creates_file(tmp_path):
    """Exporting GeoTIFF should create a valid file."""
    import rasterio

    dem_path = tmp_path / "dem.tif"
    data = np.array(
        [
            [10, 20, 30],
            [15, 25, 35],
        ],
        dtype=np.float32,
    )
    with rasterio.open(
        str(dem_path),
        "w",
        driver="GTiff",
        height=2,
        width=3,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=rasterio.transform.from_origin(0, 0, 30, 30),
    ) as dst:
        dst.write(data, 1)

    ksn = np.array(
        [
            [np.nan, 50.0, np.nan],
            [60.0, np.nan, 70.0],
        ],
        dtype=np.float64,
    )

    out_path = tmp_path / "ksn.tif"
    export_geotiff(ksn, str(dem_path), str(out_path))

    assert out_path.exists()
    with rasterio.open(str(out_path)) as src:
        out_data = src.read(1)
        assert src.crs == "EPSG:4326"
        assert out_data[0, 0] == -9999.0
        assert out_data[0, 1] == 50.0


def test_export_csv_writes_correct_format(tmp_path):
    """CSV should contain correct columns and rows."""
    area = np.array([[100.0, 200.0], [300.0, 400.0]], dtype=np.float64)
    slope = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float64)
    ksn = np.array([[10.0, np.nan], [30.0, 40.0]], dtype=np.float64)
    channel_mask = np.array([[True, False], [True, True]])

    out_path = tmp_path / "ksn.csv"
    export_csv(area, slope, ksn, channel_mask, str(out_path))

    assert out_path.exists()
    with open(out_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert reader.fieldnames == ["row", "col", "drainage_area", "slope", "ksn"]
        assert len(rows) == 3

        assert float(rows[0]["row"]) == 0
        assert float(rows[0]["col"]) == 0
        assert float(rows[0]["ksn"]) == 10.0
