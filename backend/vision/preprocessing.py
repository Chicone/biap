import numpy as np
from PIL import Image


def to_grayscale(image: Image.Image | np.ndarray) -> np.ndarray:
    """
    Convert an image to grayscale NumPy array.
    """
    if isinstance(image, Image.Image):
        image = np.array(image.convert("L"))

    if image.ndim == 2:
        return image

    if image.ndim == 3:
        return np.mean(image[:, :, :3], axis=2).astype(image.dtype)

    raise ValueError(f"Unsupported image shape: {image.shape}")


def normalize_to_uint8(image: np.ndarray) -> np.ndarray:
    """
    Normalize an image array to uint8 range [0, 255].
    """
    image = image.astype(np.float32)

    min_value = image.min()
    max_value = image.max()

    if max_value == min_value:
        return np.zeros_like(image, dtype=np.uint8)

    normalized = (image - min_value) / (max_value - min_value)
    return (normalized * 255).astype(np.uint8)


def invert_image(image: np.ndarray) -> np.ndarray:
    """
    Invert a uint8 image.
    """
    if image.dtype != np.uint8:
        image = normalize_to_uint8(image)

    return 255 - image