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
    n_bins: int = 20,
) -> tuple[float, float]:
    """Calibrate concavity index (theta) via binned log-log linear regression.

    Fits: log(S) = log(ks) - theta * log(A)

    Uses binned regression: channel cells are grouped into equal-frequency
    bins by log(A), mean log(A) and mean log(S) are computed per bin,
    then linear regression is performed on the binned means.
    This is the standard approach in tectonic geomorphology (e.g., Wobus et
    al., 2006) and dramatically improves R² over per-cell regression.

    Args:
        area: Drainage area (flow accumulation in cell units).
        slope: Channel slope.
        channel_mask: Boolean mask of channel cells.
        n_bins: Number of bins for binned regression (default 20).

    Returns:
        Tuple of (theta, r_squared).
    """
    a = area[channel_mask]
    s = slope[channel_mask]

    valid = (a > 0) & (s > 0)
    log_a = np.log(a[valid])
    log_s = np.log(s[valid])

    if len(log_a) < 3:
        return 0.45, 0.0

    bins = np.percentile(log_a, np.linspace(0, 100, n_bins + 1))
    bin_centers = []
    bin_means = []
    for i in range(n_bins):
        in_bin = (log_a >= bins[i]) & (log_a <= bins[i + 1])
        if in_bin.sum() > 0:
            bin_centers.append(log_a[in_bin].mean())
            bin_means.append(log_s[in_bin].mean())

    if len(bin_centers) < 3:
        return 0.45, 0.0

    result = stats.linregress(bin_centers, bin_means)
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
