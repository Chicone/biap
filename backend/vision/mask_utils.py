import numpy as np


def is_binary_mask(mask: np.ndarray) -> bool:
    """
    Return True if the mask contains only 0 and 1 values.
    """
    unique = np.unique(mask)
    return np.array_equal(unique, [0]) or \
           np.array_equal(unique, [1]) or \
           np.array_equal(unique, [0, 1])


def binary_mask(mask: np.ndarray) -> np.ndarray:
    """
    Convert any non-zero value to 1.
    """
    return (mask > 0).astype(np.uint8)


def mask_area(mask: np.ndarray) -> int:
    """
    Return the number of foreground pixels.
    """
    return int(np.sum(mask > 0))