"""KSN (normalized channel steepness index) computation."""

import numpy as np
from scipy import stats


def compute_slope(dem: "rd.rdarray") -> np.ndarray:
    """Compute slope from DEM using richdem.

    Uses the 'slope_riserun' method.

    Args:
        dem: Filled DEM array.

    Returns:
        Slope array (rise/run).
    """
    import richdem as rd

    return np.array(rd.TerrainAttribute(dem, "slope_riserun"))


def calibrate_theta(
    area: np.ndarray,
    slope: np.ndarray,
    channel_mask: np.ndarray,
) -> tuple[float, float]:
    """Calibrate concavity index (theta) via log-log linear regression.

    Fits: log(S) = log(ks) - theta * log(A)

    Args:
        area: Drainage area (flow accumulation in cell units).
        slope: Channel slope.
        channel_mask: Boolean mask of channel cells.

    Returns:
        Tuple of (theta, r_squared).
    """
    a = area[channel_mask]
    s = slope[channel_mask]

    valid = (a > 0) & (s > 0) & np.isfinite(np.log(a)) & np.isfinite(np.log(s))
    log_a = np.log(a[valid])
    log_s = np.log(s[valid])

    if len(log_a) < 3:
        return 0.45, 0.0

    result = stats.linregress(log_a, log_s)
    theta = float(abs(result.slope))
    r_squared = float(result.rvalue**2)
    return theta, r_squared


def compute_ksn(
    slope: np.ndarray,
    area: np.ndarray,
    theta_ref: float,
    channel_mask: np.ndarray,
) -> np.ndarray:
    """Compute normalized channel steepness index.

    ksn = S / A^(-theta_ref)

    Args:
        slope: Slope array.
        area: Drainage area (flow accumulation in cell units).
        theta_ref: Reference concavity index.
        channel_mask: Boolean mask of channel cells.

    Returns:
        ksn array, NaN for non-channel cells.
    """
    ksn = np.full_like(slope, np.nan, dtype=np.float64)
    valid = channel_mask & (area > 0) & (slope > 0)
    ksn[valid] = slope[valid] / (area[valid] ** (-theta_ref))
    return ksn
