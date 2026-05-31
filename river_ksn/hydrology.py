"""Hydrological analysis: flow direction and accumulation."""

import richdem as rd


def compute_flow_accumulation(dem: rd.rdarray) -> rd.rdarray:
    """Compute D-infinity flow accumulation.

    Args:
        dem: Filled DEM (should already have depressions filled).

    Returns:
        Flow accumulation array (number of upstream cells).
    """
    return rd.FlowAccumulation(dem, method="Dinf")
