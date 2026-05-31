import numpy as np
from river_ksn.ksn import calibrate_theta, compute_ksn


def test_calibrate_theta_perfect_power_law():
    """Fitting perfect power-law data should yield accurate theta and high R²."""
    np.random.seed(42)
    area = np.logspace(1, 4, 100)
    slope = 10.0 * (area ** (-0.5))
    mask = np.ones(len(area), dtype=bool)

    theta, r2 = calibrate_theta(area, slope, mask)
    assert np.isclose(theta, 0.5, atol=0.01), f"Got theta={theta}"
    assert r2 > 0.99, f"Got R²={r2}"


def test_calibrate_theta_ignores_invalid():
    """Fitting should ignore invalid values (zero or negative area/slope)."""
    area = np.array([0, -1, 100, 1000, 10000], dtype=np.float64)
    slope = np.array([1, 1, 3.16, 1.0, 0.316], dtype=np.float64)
    mask = np.array([True, True, True, True, True])
    theta, r2 = calibrate_theta(area, slope, mask)
    assert np.isclose(theta, 0.5, atol=0.01)


def test_compute_ksn_correct_formula():
    """ksn = S / A^(-theta)."""
    area = np.array([100.0, 1000.0, 10000.0], dtype=np.float64)
    slope = np.array([1.0, 1.0, 1.0], dtype=np.float64)
    channel_mask = np.array([True, True, True])

    theta = 0.5
    ksn = compute_ksn(slope, area, theta, channel_mask)
    expected = slope / (area ** (-theta))
    assert np.allclose(ksn, expected)


def test_compute_ksn_nan_outside_channels():
    """Non-channel cells should be NaN."""
    area = np.array([[10.0, 100.0], [1000.0, 10000.0]], dtype=np.float64)
    slope = np.array([[1.0, 1.0], [1.0, 1.0]], dtype=np.float64)
    channel_mask = np.array([[False, True], [True, False]])

    ksn = compute_ksn(slope, area, 0.45, channel_mask)
    assert np.isnan(ksn[0, 0])
    assert np.isnan(ksn[1, 1])
    assert not np.isnan(ksn[0, 1])
    assert not np.isnan(ksn[1, 0])
