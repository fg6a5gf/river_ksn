import numpy as np
from river_ksn.dem import fill_dem, load_dem


def test_load_dem_returns_array(tmp_path):
    """load_dem should return a richdem/numpy array."""
    import rasterio

    dem_path = tmp_path / "test.tif"
    data = np.array(
        [
            [10.0, 11.0, 12.0],
            [9.0, 8.0, 13.0],
            [8.0, 7.0, 14.0],
        ],
        dtype=np.float32,
    )
    with rasterio.open(
        str(dem_path),
        "w",
        driver="GTiff",
        height=3,
        width=3,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=rasterio.transform.from_origin(0, 0, 1, 1),
    ) as dst:
        dst.write(data, 1)

    dem = load_dem(str(dem_path))
    assert dem.shape == (3, 3)
    assert np.allclose(dem, data)


def test_fill_dem_preserves_shape():
    """Filled DEM should preserve input shape."""
    import richdem as rd

    data = np.array(
        [
            [5.0, 5.0, 5.0],
            [5.0, 1.0, 5.0],
            [5.0, 5.0, 5.0],
        ],
        dtype=np.float64,
    )
    dem = rd.rdarray(data, no_data=-9999)
    filled = fill_dem(dem)
    assert filled.shape == (3, 3)
    assert np.all(filled >= data)
