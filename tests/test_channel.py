import numpy as np
from river_ksn.channel import auto_threshold, extract_channels


def test_auto_threshold_returns_reasonable_value():
    """Auto threshold should be within the range of flow accumulation values."""
    flow_accum = np.array(
        [
            [0, 0, 1, 2, 5],
            [0, 0, 3, 8, 20],
            [0, 0, 2, 6, 100],
        ],
        dtype=np.float64,
    )
    threshold = auto_threshold(flow_accum, percentile=80)
    expected = np.percentile(flow_accum[flow_accum > 0], 80)
    assert np.isclose(threshold, expected)
    assert threshold > 0


def test_extract_channels_returns_boolean_mask():
    """Channel extraction should return a boolean mask."""
    flow_accum = np.array(
        [
            [0, 0, 5, 10],
            [0, 3, 8, 15],
        ],
        dtype=np.float64,
    )
    mask = extract_channels(flow_accum, threshold=5)
    assert mask.dtype == bool
    assert mask.shape == (2, 4)
    assert mask[0, 2]
    assert mask[0, 3]
    assert mask[1, 2]
    assert mask[1, 3]
    assert not mask[0, 0]
    assert not mask[0, 1]
    assert not mask[1, 0]
    assert not mask[1, 1]
