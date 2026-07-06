from pathlib import Path

import numpy as np

from .io import load_image, pil_to_numpy

def get_ground_truth_masks(mask_directory: Path) -> list[Path]:
  return sorted(
    path for path in mask_directory.glob("*")
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
  )


def load_ground_truth_mask(mask_path: Path) -> np.ndarray:
  image = load_image(mask_path)
  return pil_to_numpy(image)


def merge_instance_masks(mask_directory: Path) -> np.ndarray:
  mask_paths = get_ground_truth_masks(mask_directory)

  if not mask_paths:
    raise FileNotFoundError(f"No masks found in {mask_directory}")

  merged_mask = None

  for mask_path in mask_paths:
    mask = load_ground_truth_mask(mask_path)
    binary = mask > 0

    if merged_mask is None:
      merged_mask = np.zeros(binary.shape, dtype=np.uint8)

    merged_mask[binary] = 1

  return merged_mask