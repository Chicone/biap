import numpy as np

from backend.vision.measurements import measure_regions


def test_measure_regions():
    labels = np.array(
        [
            [0, 0, 1, 1],
            [0, 0, 1, 1],
            [2, 2, 0, 0],
            [2, 2, 0, 0],
        ],
        dtype=np.uint8,
    )

    regions = measure_regions(labels)

    assert len(regions) == 2

    assert regions[0]["label"] == 1
    assert regions[0]["area"] == 4

    assert regions[1]["label"] == 2
    assert regions[1]["area"] == 4