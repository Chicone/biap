import numpy as np

from backend.vision.mask_utils import (
    binary_mask,
    is_binary_mask,
    mask_area,
)


def test_is_binary_mask():
    mask = np.array([[0, 1], [1, 0]])

    assert is_binary_mask(mask)


def test_is_not_binary_mask():
    mask = np.array([[0, 2], [1, 0]])

    assert not is_binary_mask(mask)


def test_binary_mask():
    mask = np.array([[0, 7], [15, 0]])

    binary = binary_mask(mask)

    assert np.array_equal(binary,
                          np.array([[0, 1],
                                    [1, 0]], dtype=np.uint8))


def test_mask_area():
    mask = np.array([[0, 1],
                     [1, 1]])

    assert mask_area(mask) == 3