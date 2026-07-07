import numpy as np
from skimage.measure import regionprops

def measure_regions(labels: np.ndarray) -> list[dict]:
    """
    Measure all labelled objects in an image.
    """
    measurements = []

    for region in regionprops(labels):
        perimeter = region.perimeter

        if perimeter > 0:
            circularity = 4 * np.pi * region.area / (perimeter ** 2)
        else:
            circularity = 0.0

        measurements.append({
            "label": int(region.label),

            "area": float(region.area),
            "perimeter": float(perimeter),

            "centroid": {
                "row": float(region.centroid[0]),
                "col": float(region.centroid[1]),
            },

            "bbox": {
                "min_row": int(region.bbox[0]),
                "min_col": int(region.bbox[1]),
                "max_row": int(region.bbox[2]),
                "max_col": int(region.bbox[3]),
            },

            "major_axis_length": float(region.axis_major_length),
            "minor_axis_length": float(region.axis_minor_length),
            "eccentricity": float(region.eccentricity),
            "orientation": float(region.orientation),

            "solidity": float(region.solidity),
            "convex_area": float(region.convex_area),
            "equivalent_diameter": float(region.equivalent_diameter_area),

            "circularity": float(circularity),
        })

    return measurements


def summarize_regions(regions: list[dict]) -> dict:
  """
  Compute summary statistics for measured regions.
  """
  if not regions:
    return {
      "num_objects": 0,
      "mean_area": 0.0,
      "median_area": 0.0,
      "mean_circularity": 0.0,
      "mean_solidity": 0.0,
    }

  areas = np.array([region["area"] for region in regions], dtype=float)
  circularities = np.array(
    [region["circularity"] for region in regions],
    dtype=float,
  )
  solidities = np.array(
    [region["solidity"] for region in regions],
    dtype=float,
  )

  return {
    "num_objects": len(regions),
    "mean_area": float(np.mean(areas)),
    "median_area": float(np.median(areas)),
    "mean_circularity": float(np.mean(circularities)),
    "mean_solidity": float(np.mean(solidities)),
  }