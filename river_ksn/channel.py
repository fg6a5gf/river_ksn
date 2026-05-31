"""Channel network extraction from flow accumulation."""

import numpy as np


def auto_threshold(flow_accum: np.ndarray, percentile: float = 95.0) -> float:
    """Determine a flow accumulation threshold for channel initiation.

    Uses the specified percentile of non-zero flow accumulation values.

    Args:
        flow_accum: Flow accumulation array.
        percentile: Percentile to use (default 95).

    Returns:
        Threshold value in cell count units.
    """
    nonzero = flow_accum[flow_accum > 0]
    if len(nonzero) == 0:
        return 1.0
    return float(np.percentile(nonzero, percentile))


def extract_channels(flow_accum: np.ndarray, threshold: float) -> np.ndarray:
    """Extract channel cells based on flow accumulation threshold.

    Args:
        flow_accum: Flow accumulation array.
        threshold: Minimum flow accumulation for a cell to be considered channel.

    Returns:
        Boolean mask where True indicates a channel cell.
    """
    return flow_accum >= threshold
