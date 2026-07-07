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

def measure_intensity(
  labels: np.ndarray,
  image: np.ndarray,
) -> list[dict]:
  """
  Measure intensity statistics for each labelled object.
  """
  measurements = []

  for region in regionprops(labels, intensity_image=image):
    intensity_values = region.intensity_image[region.image]

    measurements.append({
      "label": int(region.label),
      "mean_intensity": float(np.mean(intensity_values)),
      "median_intensity": float(np.median(intensity_values)),
      "min_intensity": float(np.min(intensity_values)),
      "max_intensity": float(np.max(intensity_values)),
      "std_intensity": float(np.std(intensity_values)),
      "integrated_intensity": float(np.sum(intensity_values)),
    })

  return measurements


def summarize_intensity(intensity_measurements: list[dict]) -> dict:
  """
  Compute summary statistics for intensity measurements.
  """
  if not intensity_measurements:
    return {
      "num_objects": 0,
      "mean_intensity": 0.0,
      "median_intensity": 0.0,
      "mean_integrated_intensity": 0.0,
    }

  mean_values = np.array(
    [item["mean_intensity"] for item in intensity_measurements],
    dtype=float,
  )

  integrated_values = np.array(
    [item["integrated_intensity"] for item in intensity_measurements],
    dtype=float,
  )

  return {
    "num_objects": len(intensity_measurements),
    "mean_intensity": float(np.mean(mean_values)),
    "median_intensity": float(np.median(mean_values)),
    "mean_integrated_intensity": float(np.mean(integrated_values)),
  }