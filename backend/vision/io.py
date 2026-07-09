from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


def load_image(image_path: str | Path) -> Image.Image:
    """
    Load an image from disk as a PIL Image.
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    return Image.open(path)


def load_image_as_array(image_path: str | Path) -> np.ndarray:
    """
    Load an image from disk and return it as a NumPy array.
    """
    image = load_image(image_path)
    return pil_to_numpy(image)


def load_mask(mask_path: str | Path) -> np.ndarray:
    """
    Load a segmentation mask from disk as a NumPy array.

    BBBC038 masks are usually stored as grayscale or binary images.
    """
    path = Path(mask_path)

    if not path.exists():
        raise FileNotFoundError(f"Mask not found: {path}")

    mask = Image.open(path)
    return np.array(mask)


def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """
    Convert a PIL image to a NumPy array.
    """
    return np.array(image)


def numpy_to_pil(array: np.ndarray) -> Image.Image:
    """
    Convert a NumPy array to a PIL image.
    """
    if array.dtype != np.uint8:
        array = array.astype(np.uint8)

    return Image.fromarray(array)


def is_grayscale(image: Image.Image | np.ndarray) -> bool:
    """
    Check whether an image is grayscale.
    """
    if isinstance(image, Image.Image):
        return image.mode in ("L", "I", "F")

    if image.ndim == 2:
        return True

    if image.ndim == 3 and image.shape[2] == 1:
        return True

    return False


def image_info(image: Image.Image | np.ndarray) -> dict[str, Any]:
    """
    Return basic image information.
    """
    if isinstance(image, Image.Image):
        return {
            "type": "PIL",
            "mode": image.mode,
            "width": image.width,
            "height": image.height,
            "size": image.size,
        }

    return {
        "type": "numpy",
        "shape": image.shape,
        "dtype": str(image.dtype),
        "ndim": image.ndim,
    }


def normalize_for_display(array: np.ndarray) -> np.ndarray:
  """
  Normalize grayscale or RGB image data to uint8 for browser display.

  This is especially important for 16-bit microscopy TIFF images.
  """
  array = np.asarray(array)

  if array.dtype == np.uint8:
    return array

  array = array.astype(np.float32)

  min_value = float(np.min(array))
  max_value = float(np.max(array))

  if max_value <= min_value:
    return np.zeros(array.shape, dtype=np.uint8)

  normalized = (array - min_value) / (max_value - min_value)
  normalized = normalized * 255.0

  return normalized.astype(np.uint8)