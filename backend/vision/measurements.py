import numpy as np
from skimage.measure import regionprops


def measure_regions(labels: np.ndarray) -> list[dict]:
    """
    Measure all labelled objects in an image.
    """
    measurements = []

    for region in regionprops(labels):
        measurements.append({
            "label": region.label,
            "area": region.area,
            "centroid": region.centroid,
        })

    return measurements