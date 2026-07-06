import numpy as np


def label_to_rgb(mask: np.ndarray, color=(255, 0, 0)) -> np.ndarray:
    """
    Convert a binary mask into a coloured RGB image.
    """
    rgb = np.zeros((*mask.shape, 3), dtype=np.uint8)

    rgb[mask > 0] = color

    return rgb


def blend_images(
    image: np.ndarray,
    overlay: np.ndarray,
    alpha: float = 0.5,
) -> np.ndarray:
    """
    Blend two RGB images together.
    """
    if image.shape != overlay.shape:
        raise ValueError("Images must have the same shape.")

    blended = (
        (1 - alpha) * image.astype(np.float32)
        + alpha * overlay.astype(np.float32)
    )

    return blended.astype(np.uint8)


def overlay_mask(
    image: np.ndarray,
    mask: np.ndarray,
    color=(255, 0, 0),
    alpha=0.5,
) -> np.ndarray:
    """
    Overlay a binary mask onto an RGB image.
    """
    overlay = label_to_rgb(mask, color)

    return blend_images(image, overlay, alpha)