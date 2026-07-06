import numpy as np
from skimage.measure import label
from skimage.filters import threshold_otsu

def threshold(image: np.ndarray, threshold_value: int = 128) -> np.ndarray:
    """
    Convert a grayscale image into a binary mask.
    """
    return (image >= threshold_value).astype(np.uint8)


def connected_components(mask: np.ndarray) -> np.ndarray:
  """
  Label each connected object in a binary mask.

  Background is labelled 0.
  Objects are labelled 1, 2, 3, ...
  """
  return label(mask)

def segment_otsu(
  image: np.ndarray,
  foreground: str = "bright",
  return_threshold: bool = False,
):
  t = threshold_otsu(image)

  if foreground == "dark":
    binary = (image <= t).astype(np.uint8)
  else:
    binary = (image >= t).astype(np.uint8)

  if return_threshold:
    return binary, float(t)

  return binary